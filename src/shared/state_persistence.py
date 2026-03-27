"""
V3 Conversation State Persistence Layer

Phase 1 Implementation: Database-backed state persistence for v3 agentic conversations.

This module provides a repository pattern for persisting and retrieving
AgenticOrchestratorState from the database, replacing the in-memory STATE_STORE.

Formal Specification:
=====================

Invariants:
- save(state) → ∀ fields: retrieved.field = state.field (lossless storage)
- get(id) → state.session_id = id ∨ None (correct retrieval)
- delete(id) → ¬∃ state: state.session_id = id (complete deletion)
- Concurrent saves are serialized via database transactions

Safety Properties:
- Failed transactions are rolled back (atomicity)
- No partial writes (consistency)
- State survives server restarts (durability)

Usage:
======
    from src.shared.state_persistence import StatePersistenceLayer
    
    persistence = StatePersistenceLayer()
    
    # Save state
    success = persistence.save(state)
    
    # Retrieve state
    state = persistence.get(session_id)
    
    # Delete state
    success = persistence.delete(session_id)
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.shared.db import V3ConversationState, create_session
from src.agents.graph_state import (
    AgenticOrchestratorState,
    ConversationMode,
    create_initial_state,
    CapturedContext,
    LoanSnapshot,
    LoanRecommendation,
    DocumentsChecklist,
    STPCheckpoint,
    Message,
    PhaseTransition,
    DocumentWithExtraction,
    DiscrepancyFlag,
)
from src.agents.structured_parser import IntentAnalysis

logger = logging.getLogger(__name__)


def _parse_numeric_field(value) -> Optional[float]:
    """
    Parse numeric fields that may contain currency symbols or commas.
    
    Handles:
    - "$10,000" → 10000.0
    - "10000" → 10000.0
    - "$0" → 0.0
    - None → None
    - "" → None
    
    Args:
        value: Value to parse (string, number, or None)
        
    Returns:
        Float value or None if unparseable
    """
    if value is None or value == "":
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # Remove currency symbols, commas, and whitespace
        import re
        cleaned = re.sub(r'[,$\s]', '', value)
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse numeric field: {value}")
            return None
    
    return None


def _clean_numeric_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean numeric fields in a dictionary before Pydantic validation.
    
    Args:
        data: Dictionary with potential string numeric values
        
    Returns:
        Dictionary with numeric fields converted to float
    """
    if not isinstance(data, dict):
        return data
    
    # Fields that should be numeric (float or None)
    numeric_fields = [
        'monthly_income', 'loan_amount', 'property_value', 
        'down_payment', 'existing_debts', 'credit_score'
    ]
    
    cleaned = data.copy()
    for field in numeric_fields:
        if field in cleaned:
            cleaned[field] = _parse_numeric_field(cleaned[field])
    
    return cleaned


def _serialize_datetime_safe(obj: Any) -> Any:
    """
    Recursively convert datetime objects to ISO format strings for JSON serialization.
    
    This helper ensures all datetime objects in the state are converted to
    ISO-8601 format strings before database storage.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _serialize_datetime_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_datetime_safe(item) for item in obj]
    else:
        return obj


class StatePersistenceError(Exception):
    """Raised when state persistence operations fail."""
    pass


class StatePersistenceLayer:
    """
    Repository pattern implementation for V3 conversation state persistence.
    
    This class provides CRUD operations for AgenticOrchestratorState,
    with proper transaction management and error handling.
    
    Thread Safety:
    - Each method creates its own database session
    - Database handles concurrent access via row-level locking
    - Safe for multi-threaded environments
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize persistence layer.
        
        Args:
            db_session: Optional pre-existing database session.
                       If None, creates new session per operation.
        """
        self._db_session = db_session
    
    def _get_session(self) -> Session:
        """Get database session (existing or new)."""
        if self._db_session is not None:
            return self._db_session
        return create_session()
    
    def _should_close_session(self, session: Session) -> bool:
        """Check if we should close the session (we created it)."""
        return self._db_session is None
    
    def save(self, state: AgenticOrchestratorState) -> bool:
        """
        Save or update agentic state to database.
        
        Formal Specification:
        ---------------------
        Precondition: state is a valid AgenticOrchestratorState
        Postcondition: state exists in database with all fields preserved
        Side Effects: Updates updated_at timestamp
        
        Args:
            state: The agentic orchestrator state to persist
            
        Returns:
            True if save successful, False otherwise
            
        Raises:
            StatePersistenceError: If save operation fails
        """
        session = self._get_session()
        should_close = self._should_close_session(session)
        
        try:
            # Serialize state to database format
            db_state = self._serialize_state(state)
            
            # Check if record exists (upsert pattern)
            existing = session.query(V3ConversationState).filter(
                V3ConversationState.session_id == state.session_id
            ).first()
            
            if existing:
                # Update existing record
                for key, value in db_state.items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.now()
            else:
                # Insert new record
                new_state = V3ConversationState(**db_state)
                session.add(new_state)
            
            session.commit()
            logger.debug(f"Saved V3 state for session {state.session_id}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error saving V3 state: {e}")
            raise StatePersistenceError(f"Failed to save state: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error saving V3 state: {e}")
            raise StatePersistenceError(f"Failed to save state: {e}")
        finally:
            if should_close:
                session.close()
    
    def get(self, session_id: str) -> Optional[AgenticOrchestratorState]:
        """
        Retrieve agentic state from database.
        
        Formal Specification:
        ---------------------
        Precondition: session_id is a valid UUID string
        Postcondition: 
            - If state exists: returned state has session_id = input
            - If state doesn't exist: returns None
        
        Args:
            session_id: The session identifier to retrieve
            
        Returns:
            AgenticOrchestratorState if found, None otherwise
            
        Raises:
            StatePersistenceError: If retrieval operation fails
        """
        session = self._get_session()
        should_close = self._should_close_session(session)
        
        try:
            db_state = session.query(V3ConversationState).filter(
                V3ConversationState.session_id == session_id
            ).first()
            
            if db_state is None:
                return None
            
            # Deserialize database format to state
            state = self._deserialize_state(db_state)
            logger.debug(f"Retrieved V3 state for session {session_id}")
            return state
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving V3 state: {e}")
            raise StatePersistenceError(f"Failed to retrieve state: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving V3 state: {e}")
            raise StatePersistenceError(f"Failed to retrieve state: {e}")
        finally:
            if should_close:
                session.close()
    
    def delete(self, session_id: str) -> bool:
        """
        Delete agentic state from database.
        
        Formal Specification:
        ---------------------
        Precondition: session_id is a valid UUID string
        Postcondition: ¬∃ state in database: state.session_id = session_id
        
        Args:
            session_id: The session identifier to delete
            
        Returns:
            True if deleted, False if state didn't exist
        """
        session = self._get_session()
        should_close = self._should_close_session(session)
        
        try:
            result = session.query(V3ConversationState).filter(
                V3ConversationState.session_id == session_id
            ).delete()
            
            session.commit()
            
            if result > 0:
                logger.debug(f"Deleted V3 state for session {session_id}")
                return True
            else:
                logger.debug(f"No V3 state found for session {session_id}")
                return False
                
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error deleting V3 state: {e}")
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error deleting V3 state: {e}")
            return False
        finally:
            if should_close:
                session.close()
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[AgenticOrchestratorState]:
        """
        List all conversation states with pagination.
        
        Args:
            limit: Maximum number of states to return
            offset: Number of states to skip
            
        Returns:
            List of AgenticOrchestratorState objects
        """
        session = self._get_session()
        should_close = self._should_close_session(session)
        
        try:
            db_states = session.query(V3ConversationState).order_by(
                V3ConversationState.updated_at.desc()
            ).offset(offset).limit(limit).all()
            
            states = [self._deserialize_state(db_state) for db_state in db_states]
            logger.debug(f"Listed {len(states)} V3 states")
            return states
            
        except SQLAlchemyError as e:
            logger.error(f"Database error listing V3 states: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing V3 states: {e}")
            return []
        finally:
            if should_close:
                session.close()
    
    def _serialize_state(self, state: AgenticOrchestratorState) -> Dict[str, Any]:
        """
        Convert AgenticOrchestratorState to database-compatible dictionary.

        This method handles the serialization of complex Pydantic models
        to JSON-compatible dictionaries for database storage.
        """
        return {
            "session_id": state.session_id,
            "mode": state.mode.value,
            "current_stage": state.current_stage,

            # Borrower Context
            "captured_context": _serialize_datetime_safe(state.captured_context.model_dump()) if state.captured_context else None,
            "intent_analysis": _serialize_datetime_safe(state.intent_analysis.model_dump()) if state.intent_analysis else None,
            "confidence_scores": state.confidence_scores,

            # Loan Details
            "loan_snapshot": _serialize_datetime_safe(state.loan_snapshot.model_dump()) if state.loan_snapshot else None,
            "recommendations": [_serialize_datetime_safe(r.model_dump()) for r in state.recommendations] if state.recommendations else None,
            "selected_recommendation": _serialize_datetime_safe(state.selected_recommendation.model_dump()) if state.selected_recommendation else None,

            # Documents
            "documents_checklist": _serialize_datetime_safe(state.documents_checklist.model_dump()) if state.documents_checklist else None,
            "uploaded_documents": [_serialize_datetime_safe(d.model_dump()) for d in state.uploaded_documents] if state.uploaded_documents else None,

            # STP Processing
            "stp_checkpoints": [_serialize_datetime_safe(c.model_dump()) for c in state.stp_checkpoints] if state.stp_checkpoints else None,
            "stp_status": state.stp_status,
            "bureau_score": state.bureau_score,
            "stp_approved": state.stp_approved,
            "awaiting_acceptance": state.awaiting_acceptance,
            "terms_accepted": state.terms_accepted,

            # Phase Progression
            "current_phase_id": state.current_phase_id,
            "phase_history": [_serialize_datetime_safe(p.model_dump()) for p in state.phase_history] if state.phase_history else None,

            # Flags & Alerts
            "discrepancy_flags": [_serialize_datetime_safe(f.model_dump()) for f in state.discrepancy_flags] if state.discrepancy_flags else None,
            "requires_manual_review": state.requires_manual_review,
            "escalation_needed": state.escalation_needed,

            # Application State
            "application_id": state.application_id,
            "application_submitted": state.application_submitted,

            # Conversation History
            "conversation_history": [_serialize_datetime_safe(m.model_dump()) for m in state.conversation_history] if state.conversation_history else None,
        }
    
    def _deserialize_state(self, db_state: V3ConversationState) -> AgenticOrchestratorState:
        """
        Convert database record to AgenticOrchestratorState.

        This method handles the deserialization of JSON database fields
        back to Pydantic models.
        """
        # Reconstruct ConversationMode enum
        mode = ConversationMode(db_state.mode)

        # Reconstruct captured_context (with numeric field cleaning)
        captured_context = CapturedContext()
        if db_state.captured_context:
            # Clean numeric fields before validation
            cleaned_context = _clean_numeric_fields(db_state.captured_context)
            captured_context = CapturedContext.model_validate(cleaned_context)

        # Reconstruct intent_analysis (with numeric field cleaning)
        intent_analysis = None
        if db_state.intent_analysis:
            cleaned_intent = _clean_numeric_fields(db_state.intent_analysis)
            intent_analysis = IntentAnalysis.model_validate(cleaned_intent)

        # Reconstruct loan_snapshot (with numeric field cleaning)
        loan_snapshot = None
        if db_state.loan_snapshot:
            cleaned_snapshot = _clean_numeric_fields(db_state.loan_snapshot)
            loan_snapshot = LoanSnapshot.model_validate(cleaned_snapshot)
        
        # Reconstruct recommendations
        recommendations = []
        if db_state.recommendations:
            recommendations = [LoanRecommendation.model_validate(r) for r in db_state.recommendations]
        
        # Reconstruct selected_recommendation
        selected_recommendation = None
        if db_state.selected_recommendation:
            selected_recommendation = LoanRecommendation.model_validate(db_state.selected_recommendation)
        
        # Reconstruct documents_checklist
        documents_checklist = None
        if db_state.documents_checklist:
            documents_checklist = DocumentsChecklist.model_validate(db_state.documents_checklist)
        
        # Reconstruct uploaded_documents
        uploaded_documents = []
        if db_state.uploaded_documents:
            uploaded_documents = [DocumentWithExtraction.model_validate(d) for d in db_state.uploaded_documents]
        
        # Reconstruct stp_checkpoints
        stp_checkpoints = []
        if db_state.stp_checkpoints:
            stp_checkpoints = [STPCheckpoint.model_validate(c) for c in db_state.stp_checkpoints]
        
        # Reconstruct phase_history
        phase_history = []
        if db_state.phase_history:
            phase_history = [PhaseTransition.model_validate(p) for p in db_state.phase_history]
        
        # Reconstruct discrepancy_flags
        discrepancy_flags = []
        if db_state.discrepancy_flags:
            discrepancy_flags = [DiscrepancyFlag.model_validate(f) for f in db_state.discrepancy_flags]
        
        # Reconstruct conversation_history
        conversation_history = []
        if db_state.conversation_history:
            conversation_history = [Message.model_validate(m) for m in db_state.conversation_history]
        
        # Build and return state
        return AgenticOrchestratorState(
            session_id=db_state.session_id,
            mode=mode,
            current_stage=db_state.current_stage,
            captured_context=captured_context,
            intent_analysis=intent_analysis,
            confidence_scores=db_state.confidence_scores or {},
            loan_snapshot=loan_snapshot,
            recommendations=recommendations,
            selected_recommendation=selected_recommendation,
            documents_checklist=documents_checklist,
            uploaded_documents=uploaded_documents,
            stp_checkpoints=stp_checkpoints,
            stp_status=db_state.stp_status or "pending",
            bureau_score=db_state.bureau_score,
            stp_approved=db_state.stp_approved,
            awaiting_acceptance=db_state.awaiting_acceptance,
            terms_accepted=db_state.terms_accepted,
            current_phase_id=db_state.current_phase_id,
            phase_history=phase_history,
            discrepancy_flags=discrepancy_flags,
            requires_manual_review=db_state.requires_manual_review,
            escalation_needed=db_state.escalation_needed,
            application_id=db_state.application_id,
            application_submitted=db_state.application_submitted,
            conversation_history=conversation_history,
            created_at=db_state.created_at,
            updated_at=db_state.updated_at,
        )


# =============================================================================
# Convenience Functions (for backward compatibility with in-memory approach)
# =============================================================================

_persistence_instance: Optional[StatePersistenceLayer] = None


def get_persistence_layer() -> StatePersistenceLayer:
    """Get or create singleton persistence layer instance."""
    global _persistence_instance
    if _persistence_instance is None:
        _persistence_instance = StatePersistenceLayer()
    return _persistence_instance


def save_state(state: AgenticOrchestratorState) -> bool:
    """Convenience function to save state."""
    return get_persistence_layer().save(state)


def get_state(session_id: str) -> Optional[AgenticOrchestratorState]:
    """Convenience function to get state."""
    return get_persistence_layer().get(session_id)


def delete_state(session_id: str) -> bool:
    """Convenience function to delete state."""
    return get_persistence_layer().delete(session_id)


def get_or_create_state(session_id: str, borrower_name: Optional[str] = None) -> AgenticOrchestratorState:
    """
    Get existing state or create new one if not found.
    
    This is the primary entry point for the v3 router to get state,
    replacing the in-memory get_or_create_state function.
    
    Args:
        session_id: Session identifier
        borrower_name: Optional borrower name for new state
        
    Returns:
        Existing or newly created AgenticOrchestratorState
    """
    state = get_state(session_id)
    
    if state is None:
        # Create new state
        state = create_initial_state(session_id)
        if borrower_name:
            state.captured_context.borrower_name = borrower_name
        
        # Persist to database
        save_state(state)
        logger.info(f"Created new V3 state for session {session_id}")
    else:
        logger.debug(f"Retrieved existing V3 state for session {session_id}")
    
    return state


def update_state(state: AgenticOrchestratorState) -> bool:
    """
    Update state and persist to database.
    
    This should be called after any state modification to ensure
    persistence.
    
    Args:
        state: Modified state to persist
        
    Returns:
        True if successful
    """
    return save_state(state)
