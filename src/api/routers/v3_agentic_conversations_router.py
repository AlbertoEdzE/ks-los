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
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.shared.db import get_db, Conversation, Message as DBMessage
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


# In-memory state store (replace with Redis/DB in production)
STATE_STORE: Dict[str, AgenticOrchestratorState] = {}


def get_or_create_state(session_id: str, borrower_name: Optional[str] = None) -> AgenticOrchestratorState:
    """Get or create agentic state for session"""
    if session_id not in STATE_STORE:
        STATE_STORE[session_id] = create_initial_state(session_id)
        if borrower_name:
            STATE_STORE[session_id].captured_context.borrower_name = borrower_name
    return STATE_STORE[session_id]


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
    response_text = last_message.content if last_message else "I'm processing your request..."
    
    # Track metrics (use correct label names)
    try:
        v2_messages_sent_total.labels(role="borrower", status="success").inc()
    except Exception:
        pass  # Metrics are optional, don't fail the request
    
    # Create v2-compatible message object for frontend compatibility
    # Frontend expects specific format for documents checklist
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
    
    assistant_message = {
        "id": f"msg-{datetime.now().timestamp()}",
        "conversationId": session_id,
        "role": "assistant",
        "content": response_text,
        "metadata": {
            "loan_snapshot": state.loan_snapshot.model_dump() if state.loan_snapshot else None,
            "recommendations": [r.model_dump() for r in state.recommendations] if state.recommendations else None,
            "documentsChecklist": docs_checklist_v2,  # V2 format for frontend
            "application_id": state.application_id,
            "stp_status": state.stp_status,
        },
        "createdAt": datetime.now().isoformat(),
    }
    
    return V3MessageResponse(
        response=response_text,
        session_id=session_id,
        mode=state.mode.value,
        stage=state.current_stage,
        confidence=state.get_average_confidence(),
        metadata={
            "loan_snapshot": state.loan_snapshot.model_dump() if state.loan_snapshot else None,
            "recommendations": [r.model_dump() for r in state.recommendations] if state.recommendations else None,
            "documentsChecklist": docs_checklist_v2,  # V2 format for frontend
            "application_id": state.application_id,
            "stp_status": state.stp_status,
            "escalation_needed": state.escalation_needed,
        },
        message=assistant_message,  # V2 compatibility
    )


@router.get("/{session_id}", response_model=Dict[str, Any])
async def get_conversation(session_id: str):
    """Get conversation state"""
    if session_id not in STATE_STORE:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    state = STATE_STORE[session_id]
    
    return {
        "session_id": session_id,
        "mode": state.mode.value,
        "stage": state.current_stage,
        "captured_context": state.captured_context.model_dump(),
        "confidence_scores": state.confidence_scores,
        "application_id": state.application_id,
        "stp_status": state.stp_status,
        "message_count": len(state.conversation_history),
    }


@router.delete("/{session_id}")
async def delete_conversation(session_id: str):
    """Delete conversation"""
    if session_id in STATE_STORE:
        del STATE_STORE[session_id]
    return {"deleted": True}


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = ["router"]
