"""
LNAI-Style Orchestrator Router for KS-LOS v2.0

This router provides an alternative conversation endpoint that uses
the LNAI orchestrator for structured, card-based conversations.
"""

import uuid
import os
from typing import Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.agents.orchestrator import get_orchestrator
from src.shared.db import Conversation, Message, get_db
from src.shared.metrics import request_counter, request_errors_total

router = APIRouter(prefix="/api/v2/conversations", tags=["lnai_orchestrator"])


class SendMessageRequest(BaseModel):
    content: str


class ChatResponse(BaseModel):
    message: dict[str, Any]
    metadata: Optional[dict[str, Any]] = None


def _serialize_message(m: Message) -> dict[str, Any]:
    return {
        "id": m.id,
        "conversationId": m.conversation_id,
        "role": m.role,
        "content": m.content,
        "createdAt": m.created_at.isoformat() if m.created_at else None,
        "metadata": m.metadata_json or {},
    }


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
async def send_message_lnai(
    conversation_id: str,
    req: SendMessageRequest,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    Send a message using LNAI-style orchestrator
    
    This endpoint uses the LNAI orchestrator for structured conversation flow
    with XML tags and card-based responses.
    """
    request_counter.labels(endpoint="/api/v2/conversations/{conversation_id}/messages").inc()
    
    conv = db.get(Conversation, conversation_id)
    if not conv:
        request_errors_total.labels(endpoint="/api/v2/conversations/{conversation_id}/messages").inc()
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Add user message to database
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=req.content,
        metadata_json={"source": "lnai_orchestrator"},
    )
    db.add(user_msg)
    db.commit()
    
    # Get or create orchestrator for this conversation
    orchestrator = get_orchestrator(conversation_id)
    
    # Process message through orchestrator
    try:
        result = orchestrator.process_message(req.content)
    except Exception as e:
        request_errors_total.labels(endpoint="/api/v2/conversations/{conversation_id}/messages").inc()
        raise HTTPException(status_code=500, detail=str(e))
    
    # Create assistant message
    assistant_text = result.get("response", "")
    metadata = result.get("metadata", {})
    
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_text,
        metadata_json={
            "source": "lnai_orchestrator",
            "stage": metadata.get("stage"),
            "loanSnapshot": metadata.get("loanSnapshot"),
            "loanRecommendations": metadata.get("loanRecommendations"),
            "documentsChecklist": metadata.get("documentsChecklist"),
            "stpCheckpoints": metadata.get("stpCheckpoints"),
            "loanApplication": metadata.get("loanApplication"),
        },
    )
    db.add(assistant_msg)
    db.commit()
    
    # Update conversation metadata if needed
    if metadata.get("loanApplication"):
        conv.intent_summary = {
            "stage": metadata.get("stage"),
            "applicationId": metadata.get("loanApplication", {}).get("id"),
        }
        db.add(conv)
        db.commit()
    
    return ChatResponse(
        message=_serialize_message(assistant_msg),
        metadata=metadata,
    )


@router.get("/{conversation_id}/orchestrator-state")
async def get_orchestrator_state(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    """Get current orchestrator state for a conversation"""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    orchestrator = get_orchestrator(conversation_id)
    
    return {
        "stage": orchestrator.state.stage.value,
        "capturedContext": orchestrator.state.captured_context.model_dump(),
        "loanSnapshot": orchestrator.state.loan_snapshot.model_dump() if orchestrator.state.loan_snapshot else None,
        "selectedRecommendation": orchestrator.state.selected_recommendation.model_dump() if orchestrator.state.selected_recommendation else None,
        "stpApproved": orchestrator.state.stp_approved,
        "termsAccepted": orchestrator.state.terms_accepted,
        "disbursementCompleted": orchestrator.state.disbursement_completed,
    }
