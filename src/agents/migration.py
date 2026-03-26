"""
Migration Utilities for KS-LOS v3.0

Helpers for migrating from the old orchestrator to the new agentic workflow.
"""

import warnings
from typing import Dict, Any, Optional
from datetime import datetime


def migrate_orchestrator_state(
    old_state: Any,
    session_id: str
) -> Any:
    """
    Migrate old orchestrator state to new agentic state.
    
    Args:
        old_state: Old OrchestratorState instance
        session_id: Session identifier
        
    Returns:
        New AgenticOrchestratorState instance
    """
    from src.agents.graph_state import (
        AgenticOrchestratorState,
        ConversationMode,
        Message,
    )
    
    warnings.warn(
        "migrate_orchestrator_state is a temporary migration helper. "
        "Update your code to use the new state schema directly.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Create new state
    new_state = AgenticOrchestratorState(
        session_id=session_id,
    )
    
    # Map old fields to new
    if hasattr(old_state, 'stage'):
        new_state.current_stage = old_state.stage.value if hasattr(old_state.stage, 'value') else old_state.stage
    
    if hasattr(old_state, 'captured_context'):
        new_state.captured_context = old_state.captured_context
    
    if hasattr(old_state, 'loan_snapshot'):
        new_state.loan_snapshot = old_state.loan_snapshot
    
    if hasattr(old_state, 'recommendations'):
        new_state.recommendations = old_state.recommendations
    
    if hasattr(old_state, 'documents_checklist'):
        new_state.documents_checklist = old_state.documents_checklist
    
    if hasattr(old_state, 'stp_checkpoints'):
        new_state.stp_checkpoints = old_state.stp_checkpoints
    
    if hasattr(old_state, 'application_id'):
        new_state.application_id = old_state.application_id
    
    # Set mode based on stage
    stage_value = new_state.current_stage
    if stage_value in ['intent_capture', 'financial_context', 'ready_for_metrics', 'ready_for_recommendation']:
        new_state.mode = ConversationMode.ADVISORY
    elif stage_value in ['applicant_identity', 'application_submitted']:
        new_state.mode = ConversationMode.APPLICATION
        new_state.application_submitted = (stage_value == 'application_submitted')
    else:
        new_state.mode = ConversationMode.COMPLETION
    
    return new_state


def create_migration_wrapper(old_orchestrator: Any):
    """
    Create a wrapper to make old orchestrator compatible with new workflow.
    
    This is a TEMPORARY solution for backward compatibility.
    
    Args:
        old_orchestrator: Old LNAIOrchestrator instance
        
    Returns:
        Wrapper function compatible with new workflow
    """
    warnings.warn(
        "create_migration_wrapper is a temporary compatibility layer. "
        "Update your code to use the new agentic workflow directly.",
        DeprecationWarning,
        stacklevel=2
    )
    
    def wrapper(session_id: str, message: str, **kwargs) -> Dict[str, Any]:
        """Wrapper function"""
        # Call old orchestrator
        result = old_orchestrator.process_message(message)
        
        # Convert to new format
        return {
            "response": result.get("response", ""),
            "metadata": result.get("metadata", {}),
            "deprecated": True,
            "migration_required": True,
        }
    
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# Deprecation Timeline
# ─────────────────────────────────────────────────────────────────────────────

DEPRECATION_TIMELINE = {
    "deprecated_in": "v2.5.0",
    "removal_version": "v3.0.0",
    "migration_deadline": "2026-06-30",
    "support_status": "security-fixes-only",
    "migration_guide": "https://github.com/ks-los/docs/migration-v3.md",
}


def check_deprecation_status() -> Dict[str, Any]:
    """
    Check deprecation status and timeline.
    
    Returns:
        Deprecation timeline dict
    """
    return DEPRECATION_TIMELINE.copy()


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "migrate_orchestrator_state",
    "create_migration_wrapper",
    "check_deprecation_status",
    "DEPRECATION_TIMELINE",
]
