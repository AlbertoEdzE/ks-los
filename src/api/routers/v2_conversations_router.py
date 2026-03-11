import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.routers.v2_auth import OFFICER_HEADER, OFFICER_TOKEN, require_officer_role
from src.shared.db import Conversation, LoanPhase, Message, get_db


router = APIRouter(prefix="/api/conversations", tags=["v2_conversations"])


class CreateConversationRequest(BaseModel):
    chatRole: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    status: Optional[str] = None
    borrowerName: Optional[str] = None
    assignedOfficer: Optional[str] = None
    currentPhaseId: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str


def _serialize_conversation(c: Conversation) -> dict[str, Any]:
    return {
        "id": c.id,
        "borrowerName": c.borrower_name,
        "status": c.status,
        "chatRole": c.chat_role,
        "currentPhaseId": c.current_phase_id,
        "seriousnessScore": c.seriousness_score,
        "fitScore": c.fit_score,
        "intentSummary": c.intent_summary,
        "recommendedProducts": c.recommended_products,
        "nextConversationAngle": c.next_conversation_angle,
        "assignedOfficer": c.assigned_officer,
        "createdAt": c.created_at.isoformat() if c.created_at else None,
    }


def _serialize_message(m: Message) -> dict[str, Any]:
    return {
        "id": m.id,
        "conversationId": m.conversation_id,
        "role": m.role,
        "content": m.content,
        "metadata": m.metadata_json,
        "createdAt": m.created_at.isoformat() if m.created_at else None,
    }


def _ensure_phases_seeded(db: Session):
    exists = db.execute(select(LoanPhase.id).limit(1)).first()
    if exists is not None:
        return
    from src.api.routers.v2_phases_router import DEFAULT_PHASES

    for p in DEFAULT_PHASES:
        db.add(LoanPhase(**p))
    db.commit()


@router.post("")
def create_conversation(
    req: CreateConversationRequest,
    db: Session = Depends(get_db),
    x_officer_role: str | None = Header(default=None, alias=OFFICER_HEADER),
):
    wants_officer = (req.chatRole or "").lower() == "officer"
    if wants_officer and x_officer_role != OFFICER_TOKEN:
        raise HTTPException(status_code=403, detail="Officer access required")
    chat_role = "officer" if wants_officer else "borrower"

    _ensure_phases_seeded(db)
    phases = (
        db.execute(select(LoanPhase).where(LoanPhase.is_active.is_(True)).order_by(LoanPhase.sort_order.asc()))
        .scalars()
        .all()
    )

    conversation = Conversation(
        id=str(uuid.uuid4()),
        status="active",
        chat_role=chat_role,
        current_phase_id=phases[0].id if (chat_role == "borrower" and phases) else None,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    greeting = (
        "Hi — I’m your Loan Navigator. Tell me what you’re trying to achieve with this loan."
        if chat_role == "borrower"
        else "Officer mode enabled. Select a lead and tell me what you want to do next."
    )
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        role="assistant",
        content=greeting,
        metadata_json=None,
    )
    db.add(assistant_msg)
    db.commit()

    return {"conversation": _serialize_conversation(conversation), "greeting": greeting}


@router.get("")
def list_conversations(_: bool = Depends(require_officer_role), db: Session = Depends(get_db)):
    rows = db.execute(select(Conversation).order_by(Conversation.created_at.desc())).scalars().all()
    return [_serialize_conversation(c) for c in rows]


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _serialize_conversation(conv)


@router.patch("/{conversation_id}")
def patch_conversation(
    conversation_id: str,
    req: UpdateConversationRequest,
    _: bool = Depends(require_officer_role),
    db: Session = Depends(get_db),
):
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if req.status is not None:
        conv.status = req.status
    if req.borrowerName is not None:
        conv.borrower_name = req.borrowerName
    if req.assignedOfficer is not None:
        conv.assigned_officer = req.assignedOfficer
    if req.currentPhaseId is not None:
        conv.current_phase_id = req.currentPhaseId

    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _serialize_conversation(conv)


@router.get("/{conversation_id}/messages")
def list_messages(conversation_id: str, db: Session = Depends(get_db)):
    rows = (
        db.execute(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()))
        .scalars()
        .all()
    )
    return [_serialize_message(m) for m in rows]


@router.post("/{conversation_id}/messages")
def send_message(conversation_id: str, req: SendMessageRequest, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not req.content or not req.content.strip():
        raise HTTPException(status_code=400, detail="Content is required")

    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=req.content,
        metadata_json=None,
    )
    db.add(user_msg)
    db.commit()

    assistant_text = "Got it. I’ll ask a few quick questions to narrow down the best option for you."
    assistant_metadata = {
        "intentAnalysis": None,
        "loanRecommendations": None,
        "phaseAction": None,
        "loanAction": None,
    }
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_text,
        metadata_json=assistant_metadata,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return {
        "message": _serialize_message(assistant_msg),
        "intentAnalysis": None,
        "loanRecommendations": None,
        "phaseAction": None,
        "loanAction": None,
    }
