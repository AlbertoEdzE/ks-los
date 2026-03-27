"""
V3 Agentic Conversations Router

This router uses the NEW LangGraph-based agentic workflow with:
- AdvisoryNode (Mode 1): Understanding & estimation
- ApplicationNode (Mode 2): Collection & submission
- CompletionNode (Mode 3): STP, acceptance, disbursement
- RepairNode: Conversation repair
- RAGNode: Policy-grounded responses
- EscalationNode: Human handoff

This replaces the old LNAI-style hardcoded flow.

Phase 1 Update: Uses database-backed state persistence instead of in-memory storage.
"""

import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from src.shared.db import get_db, Conversation, Message as DBMessage, V3ConversationState
from src.shared.state_persistence import get_or_create_state, update_state, get_state, delete_state
from src.shared.xml_parser import parse_llm_response
from src.agents.graph_state import (
    AgenticOrchestratorState,
    ConversationMode,
    create_initial_state,
    Message,
)
from src.agents.nodes.advisory_node import AdvisoryNode
from src.agents.nodes.application_node import ApplicationNode
from src.agents.nodes.completion_node import CompletionNode
from src.agents.nodes.repair_node import RepairNode
from src.agents.nodes.rag_node import RAGNode
from src.agents.nodes.escalation_node import EscalationNode
from src.shared.metrics import v2_messages_sent_total

router = APIRouter(prefix="/api/v3/conversations", tags=["v3_agentic_conversations"])


class V3ConversationRequest(BaseModel):
    """Request to create or get a conversation"""
    session_id: Optional[str] = None
    borrower_name: Optional[str] = None


class V3MessageRequest(BaseModel):
    """Request to send a message"""
    content: str
    # session_id removed - now comes from URL path parameter


class V3MessageResponse(BaseModel):
    """Response with message and metadata - compatible with both v2 and v3"""
    response: str
    session_id: str
    mode: str
    stage: str
    confidence: float
    metadata: Dict[str, Any] = {}
    # V2 compatibility fields
    message: Optional[Dict[str, Any]] = None


@router.post("/", response_model=Dict[str, Any])
async def create_conversation(request: V3ConversationRequest):
    """Create a new agentic conversation - returns v2-compatible format"""
    session_id = request.session_id or str(uuid.uuid4())
    state = get_or_create_state(session_id, request.borrower_name)
    
    # Return v2-compatible conversation object
    conversation = {
        "id": session_id,
        "borrowerName": request.borrower_name,
        "status": "active",
        "chatRole": "borrower",
        "currentPhaseId": None,
        "seriousnessScore": None,
        "fitScore": None,
        "intentSummary": None,
        "recommendedProducts": None,
        "nextConversationAngle": "Ask about loan purpose",
        "assignedOfficer": None,
        "userId": None,
        "createdAt": datetime.now().isoformat(),
    }
    
    return {"conversation": conversation}


@router.post("/{session_id}/messages", response_model=V3MessageResponse)
async def send_message(session_id: str, request: V3MessageRequest):
    """
    Send a message to the agentic conversation.
    
    This uses the NEW agentic workflow:
    1. Process through RepairNode (check for corrections/digressions)
    2. Process through RAGNode (policy questions)
    3. Process through appropriate mode node (Advisory/Application/Completion)
    4. Process through EscalationNode (if needed)
    """
    # session_id comes from path parameter now
    state = get_or_create_state(session_id)
    
    # Add user message to history
    state.add_message("user", request.content)
    
    # ──────────────────────────────────────────────────────────────────────
    # Agentic Processing Pipeline
    # ──────────────────────────────────────────────────────────────────────
    
    # Step 1: Repair Node (handle corrections, digressions)
    repair_node = RepairNode()
    state = repair_node.process(state)
    
    # Step 2: RAG Node (policy-grounded responses)
    # Note: Pass knowledge_base if available
    rag_node = RAGNode()
    state = rag_node.process(state)
    
    # Step 3: Mode-specific processing
    if state.mode == ConversationMode.ADVISORY:
        advisory_node = AdvisoryNode()
        state = advisory_node.process(state)
        
    elif state.mode == ConversationMode.APPLICATION:
        application_node = ApplicationNode()
        state = application_node.process(state)
        
    elif state.mode == ConversationMode.COMPLETION:
        completion_node = CompletionNode()
        state = completion_node.process(state)
    
    # Step 4: Escalation Node (check if human handoff needed)
    escalation_node = EscalationNode()
    state = escalation_node.process(state)
    
    # ──────────────────────────────────────────────────────────────────────
    # Extract response
    # ──────────────────────────────────────────────────────────────────────

    last_message = state.conversation_history[-1] if state.conversation_history else None
    raw_response_text = last_message.content if last_message else "I'm processing your request..."

    # Phase 1: Parse XML tags from LLM response to extract metadata
    # This is CRITICAL - the LLM returns XML-tagged JSON that needs to be parsed
    clean_response_text, parsed_metadata = parse_llm_response(raw_response_text)

    # Track metrics (use correct label names)
    try:
        v2_messages_sent_total.labels(role="borrower", status="success").inc()
    except Exception:
        pass  # Metrics are optional, don't fail the request

    # Create v2-compatible message object for frontend compatibility
    # Frontend expects:
    # - content: Clean text (XML tags stripped)
    # - metadata: Parsed JSON from XML tags
    docs_checklist_v2 = None
    if state.documents_checklist:
        # Convert from v3 format to v2 frontend format
        docs_checklist_v2 = {
            "identity": [
                {"name": doc["name"], "status": "required" if doc.get("required") else "optional", "description": doc.get("description", "")}
                for doc in state.documents_checklist.identity
            ] if state.documents_checklist.identity else [],
            "income": [
                {"name": doc["name"], "status": "required" if doc.get("required") else "optional", "description": doc.get("description", "")}
                for doc in state.documents_checklist.income
            ] if state.documents_checklist.income else [],
            "business": [
                {"name": doc["name"], "status": "required" if doc.get("required") else "optional", "description": doc.get("description", "")}
                for doc in state.documents_checklist.business
            ] if hasattr(state.documents_checklist, 'business') and state.documents_checklist.business else [],
            "property": [
                {"name": doc["name"], "status": "required" if doc.get("required") else "optional", "description": doc.get("description", "")}
                for doc in state.documents_checklist.property
            ] if hasattr(state.documents_checklist, 'property') and state.documents_checklist.property else [],
            "vehicle": [
                {"name": doc["name"], "status": "required" if doc.get("required") else "optional", "description": doc.get("description", "")}
                for doc in state.documents_checklist.vehicle
            ] if hasattr(state.documents_checklist, 'vehicle') and state.documents_checklist.vehicle else [],
        }

    # Merge parsed metadata with state-based metadata
    # Parsed metadata from XML takes precedence
    merged_metadata = {
        **parsed_metadata,  # XML-parsed metadata (intentAnalysis, loanSnapshot, etc.)
        "documentsChecklist": docs_checklist_v2,  # V2 format for frontend
        "application_id": state.application_id,
        "stp_status": state.stp_status,
    }

    # Add loan_snapshot and recommendations from state if not in parsed metadata
    if "loanSnapshot" not in parsed_metadata and state.loan_snapshot:
        merged_metadata["loanSnapshot"] = state.loan_snapshot.model_dump()
    
    if "loanRecommendations" not in parsed_metadata and state.recommendations:
        merged_metadata["loanRecommendations"] = [r.model_dump() for r in state.recommendations]

    assistant_message = {
        "id": f"msg-{datetime.now().timestamp()}",
        "conversationId": session_id,
        "role": "assistant",
        "content": clean_response_text,  # Clean text for display (XML stripped)
        "metadata": merged_metadata,  # Parsed metadata for UI cards
        "createdAt": datetime.now().isoformat(),
    }

    # Phase 1: Persist state to database AFTER processing
    # This ensures all state changes are saved before returning
    update_state(state)

    return V3MessageResponse(
        response=clean_response_text,  # Return clean text
        session_id=session_id,
        mode=state.mode.value,
        stage=state.current_stage,
        confidence=state.get_average_confidence(),
        metadata=merged_metadata,
        message=assistant_message,  # V2 compatibility
    )


@router.get("/{session_id}", response_model=Dict[str, Any])
async def get_conversation(session_id: str):
    """
    Get conversation state from database.
    
    Phase 1: Uses database-backed persistence instead of in-memory store.
    """
    state = get_state(session_id)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "session_id": session_id,
        "mode": state.mode.value,
        "stage": state.current_stage,
        "captured_context": state.captured_context.model_dump() if state.captured_context else None,
        "confidence_scores": state.confidence_scores,
        "application_id": state.application_id,
        "stp_status": state.stp_status,
        "message_count": len(state.conversation_history),
        "created_at": state.created_at.isoformat() if state.created_at else None,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
    }


@router.delete("/{session_id}")
async def delete_conversation(session_id: str):
    """
    Delete conversation from database.
    
    Phase 1: Uses database-backed persistence instead of in-memory store.
    """
    success = delete_state(session_id)
    return {"deleted": success}


# =============================================================================
# Phase 2: Missing Core API Endpoints
# =============================================================================
# These endpoints are required by the frontend but were previously missing

@router.get("/{session_id}/messages", response_model=List[Dict[str, Any]])
async def get_messages(session_id: str, db: Session = Depends(get_db)):
    """
    Get all messages for a conversation.
    
    Phase 2 Implementation: Retrieves messages from both:
    1. V3 state conversation_history (primary source for v3 conversations)
    2. Database messages table (fallback for v2 conversations)
    
    Specification:
    - Precondition: session_id exists
    - Postcondition: Returns chronologically ordered message list
    - Returns empty list if no messages exist (not 404)
    
    Args:
        session_id: Conversation session identifier
        db: Database session
        
    Returns:
        List of messages in chronological order
    """
    try:
        # First, try to get messages from V3 state
        state = get_state(session_id)
        if state is not None and state.conversation_history:
            # Convert V3 state messages to frontend-compatible format
            result = [
                {
                    "id": f"msg-{idx}",
                    "conversationId": session_id,
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": msg.metadata or {},
                    "createdAt": msg.timestamp.isoformat() if hasattr(msg, 'timestamp') and msg.timestamp else None,
                }
                for idx, msg in enumerate(state.conversation_history)
            ]
            logger.debug(f"Retrieved {len(result)} messages from V3 state for session {session_id}")
            return result
        
        # Fallback: Query messages from database (for v2 conversations)
        messages = db.query(DBMessage).filter(
            DBMessage.conversation_id == session_id
        ).order_by(DBMessage.created_at.asc()).all()
        
        # Convert to frontend-compatible format
        result = [
            {
                "id": msg.id,
                "conversationId": msg.conversation_id,
                "role": msg.role,
                "content": msg.content,
                "metadata": msg.metadata_json or {},
                "createdAt": msg.created_at.isoformat(),
            }
            for msg in messages
        ]
        
        logger.debug(f"Retrieved {len(result)} messages from database for session {session_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving messages for session {session_id}: {e}")
        # Return empty list instead of failing
        return []


@router.get("/{session_id}/loan", response_model=Optional[Dict[str, Any]])
async def get_loan_for_conversation(session_id: str, db: Session = Depends(get_db)):
    """
    Get loan associated with a conversation.
    
    Phase 2 Implementation: Retrieves loan from database by conversation_id foreign key.
    
    Specification:
    - Precondition: session_id exists
    - Postcondition: 
        - 200 OK with loan object if loan exists
        - 200 OK with null if no loan associated (not 404)
    
    Args:
        session_id: Conversation session identifier
        db: Database session
        
    Returns:
        Loan object in V2-compatible format, or null if no loan exists
    """
    from src.shared.db import Loan
    
    try:
        # Query loan by conversation_id
        loan = db.query(Loan).filter(
            Loan.conversation_id == session_id
        ).first()
        
        if loan is None:
            logger.debug(f"No loan found for session {session_id}")
            return None
        
        # Convert to V2-compatible format for frontend
        result = {
            "id": loan.id,
            "borrowerName": loan.borrower_name,
            "borrowerEmail": loan.borrower_email,
            "borrowerPhone": loan.borrower_phone,
            "loanType": loan.loan_type,
            "loanAmount": loan.loan_amount,
            "interestRate": loan.interest_rate,
            "tenure": loan.tenure,
            "monthlyEmi": loan.monthly_emi,
            "purpose": loan.purpose,
            "employmentType": loan.employment_type,
            "monthlyIncome": loan.monthly_income,
            "existingDebts": loan.existing_debts,
            "creditScore": loan.credit_score,
            "collateral": loan.collateral,
            "downPayment": loan.down_payment,
            "propertyValue": loan.property_value,
            "ltv": loan.ltv,
            "currentPhaseId": loan.current_phase_id,
            "catalogProductCode": loan.catalog_product_code,
            "documentChecklist": loan.document_checklist,
            "underwritingMemo": loan.underwriting_memo,
            "stpProcessingStatus": loan.stp_processing_status,
            "stpProcessingLog": loan.stp_processing_log,
            "stpPayload": loan.stp_payload,
            "termsAcceptedAt": loan.terms_accepted_at.isoformat() if loan.terms_accepted_at else None,
            "termsSignaturePath": loan.terms_signature_path,
            "termsSignatureMime": loan.terms_signature_mime,
            "disbursement": loan.disbursement,
            "status": loan.status,
            "notes": loan.notes,
            "conversationId": loan.conversation_id,
            "createdBy": loan.created_by,
            "createdAt": loan.created_at.isoformat(),
            "updatedAt": loan.updated_at.isoformat(),
        }
        
        logger.debug(f"Retrieved loan {loan.id} for session {session_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving loan for session {session_id}: {e}")
        return None


@router.post("/{session_id}/loan", response_model=Dict[str, Any])
async def create_or_update_loan(
    session_id: str,
    loan_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Create or update loan for a conversation.
    
    Phase 2 Implementation: Creates or updates loan in database.
    
    Specification:
    - Precondition: session_id exists, loan_data is valid
    - Postcondition: Loan exists in database associated with conversation
    
    Args:
        session_id: Conversation session identifier
        loan_data: Loan data in V2-compatible format
        db: Database session
        
    Returns:
        Created/updated loan object
    """
    from src.shared.db import Loan
    from datetime import datetime
    
    try:
        # Check if loan already exists for this conversation
        existing_loan = db.query(Loan).filter(
            Loan.conversation_id == session_id
        ).first()
        
        if existing_loan:
            # Update existing loan
            for key, value in loan_data.items():
                # Map from camelCase to snake_case
                db_key = key.replace("camelCase", "snake_case").lower()
                if hasattr(existing_loan, db_key):
                    setattr(existing_loan, db_key, value)
            existing_loan.updated_at = datetime.now()
            db.commit()
            db.refresh(existing_loan)
            logger.info(f"Updated loan {existing_loan.id} for session {session_id}")
            loan = existing_loan
        else:
            # Create new loan
            new_loan = Loan(
                borrower_name=loan_data.get("borrowerName", "Unknown"),
                borrower_email=loan_data.get("borrowerEmail"),
                borrower_phone=loan_data.get("borrowerPhone"),
                loan_type=loan_data.get("loanType", "personal"),
                loan_amount=str(loan_data.get("loanAmount", "0")),
                interest_rate=str(loan_data.get("interestRate")),
                tenure=str(loan_data.get("tenure")),
                monthly_emi=str(loan_data.get("monthlyEmi")),
                purpose=loan_data.get("purpose"),
                employment_type=loan_data.get("employmentType"),
                monthly_income=str(loan_data.get("monthlyIncome")),
                existing_debts=str(loan_data.get("existingDebts")),
                credit_score=str(loan_data.get("creditScore")),
                collateral=loan_data.get("collateral"),
                down_payment=str(loan_data.get("downPayment")),
                property_value=str(loan_data.get("propertyValue")),
                ltv=str(loan_data.get("ltv")),
                current_phase_id=loan_data.get("currentPhaseId"),
                catalog_product_code=loan_data.get("catalogProductCode"),
                document_checklist=loan_data.get("documentChecklist"),
                underwriting_memo=loan_data.get("underwritingMemo"),
                stp_processing_status=loan_data.get("stpProcessingStatus"),
                stp_processing_log=loan_data.get("stpProcessingLog"),
                stp_payload=loan_data.get("stpPayload"),
                terms_accepted_at=datetime.fromisoformat(loan_data["termsAcceptedAt"]) if loan_data.get("termsAcceptedAt") else None,
                terms_signature_path=loan_data.get("termsSignaturePath"),
                terms_signature_mime=loan_data.get("termsSignatureMime"),
                disbursement=loan_data.get("disbursement"),
                status=loan_data.get("status", "draft"),
                notes=loan_data.get("notes"),
                conversation_id=session_id,
                created_by=loan_data.get("createdBy"),
            )
            db.add(new_loan)
            db.commit()
            db.refresh(new_loan)
            logger.info(f"Created loan {new_loan.id} for session {session_id}")
            loan = new_loan
        
        # Return loan in V2-compatible format
        return {
            "id": loan.id,
            "borrowerName": loan.borrower_name,
            "loanType": loan.loan_type,
            "loanAmount": loan.loan_amount,
            "status": loan.status,
            "conversationId": loan.conversation_id,
            "createdAt": loan.created_at.isoformat(),
            "updatedAt": loan.updated_at.isoformat(),
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating/updating loan for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save loan: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = ["router"]
