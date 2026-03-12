import uuid
import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, ConfigDict
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


class IntentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: Optional[str] = None
    urgency: Optional[str] = None
    affordability: Optional[str] = None
    monthlyIncome: Optional[str] = None
    existingDebts: Optional[str] = None
    loanAmount: Optional[str] = None
    preferredTenure: Optional[str] = None
    collateralAvailable: Optional[str] = None
    employmentType: Optional[str] = None
    creditHistory: Optional[str] = None


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


def _merge_intent(prev: Optional[dict], new: IntentSummary) -> dict:
    base: dict = dict(prev or {})
    for k, v in new.model_dump(exclude_none=True).items():
        if base.get(k) in (None, "", []):
            base[k] = v
    return base


def _extract_amount(text: str) -> Optional[str]:
    t = text.lower()
    m = re.search(r"(\$|usd\s*)?\s*(\d{1,3}(?:[,\s]\d{3})+|\d+(?:\.\d+)?)\s*(k|m|million|thousand)?", t)
    if not m:
        return None
    raw = m.group(2).replace(",", "").replace(" ", "")
    unit = (m.group(3) or "").strip()
    if unit in {"k", "thousand"}:
        return f"{raw}k"
    if unit in {"m", "million"}:
        return f"{raw}m"
    return raw


def _extract_credit_score(text: str) -> Optional[str]:
    m = re.search(r"\b(3\d{2}|4\d{2}|5\d{2}|6\d{2}|7\d{2}|8[0-4]\d|850)\b", text)
    if not m:
        return None
    return m.group(1)


def _infer_urgency(text: str) -> Optional[str]:
    t = text.lower()
    if any(k in t for k in ["today", "asap", "urgent", "immediately", "this week", "deadline"]):
        return "high"
    if any(k in t for k in ["soon", "next week", "this month"]):
        return "medium"
    return None


def _infer_purpose(text: str) -> Optional[str]:
    t = text.lower()
    mapping = {
        "home": ["home", "mortgage", "house", "property"],
        "car": ["car", "vehicle", "auto"],
        "business": ["business", "working capital", "inventory", "startup"],
        "personal": ["personal", "medical", "education", "wedding", "travel"],
        "debt_consolidation": ["debt", "consolidat", "refinanc"],
    }
    for purpose, keys in mapping.items():
        if any(k in t for k in keys):
            return purpose
    return None


def _infer_employment(text: str) -> Optional[str]:
    t = text.lower()
    if any(k in t for k in ["salaried", "employed", "full-time", "full time", "paycheck"]):
        return "salaried"
    if any(k in t for k in ["self-employed", "self employed", "freelance", "contractor", "business owner"]):
        return "self-employed"
    return None


def _compute_scores(intent: dict) -> tuple[int, int]:
    completeness_fields = [
        "purpose",
        "loanAmount",
        "monthlyIncome",
        "creditHistory",
        "employmentType",
        "preferredTenure",
        "existingDebts",
        "collateralAvailable",
        "urgency",
    ]
    present = sum(1 for f in completeness_fields if intent.get(f))
    seriousness = min(100, 10 + present * 10)

    credit = intent.get("creditHistory")
    credit_score = None
    if isinstance(credit, str):
        try:
            credit_score = int(credit)
        except ValueError:
            credit_score = None
    if credit_score is None:
        fit = 55
    elif credit_score >= 760:
        fit = 85
    elif credit_score >= 720:
        fit = 75
    elif credit_score >= 680:
        fit = 65
    elif credit_score >= 620:
        fit = 50
    else:
        fit = 35
    return seriousness, fit


def _next_angle(intent: dict) -> str:
    if not intent.get("loanAmount"):
        return "Confirm desired loan amount and timeline."
    if not intent.get("purpose"):
        return "Clarify the loan purpose and preferred product type."
    if not intent.get("monthlyIncome"):
        return "Ask about monthly income and existing obligations."
    if not intent.get("creditHistory"):
        return "Ask for credit score range and any recent delinquencies."
    if not intent.get("preferredTenure"):
        return "Confirm preferred tenure and repayment comfort level."
    return "Validate documents, collateral, and eligibility constraints."


def analyze_intent_message(content: str, previous_intent: Optional[dict]) -> dict[str, Any]:
    amount = _extract_amount(content)
    credit = _extract_credit_score(content)
    intent = IntentSummary(
        purpose=_infer_purpose(content),
        urgency=_infer_urgency(content),
        loanAmount=amount,
        employmentType=_infer_employment(content),
        creditHistory=credit,
    )
    merged = _merge_intent(previous_intent, intent)
    seriousness, fit = _compute_scores(merged)
    return {
        "intentSummary": merged,
        "seriousnessScore": seriousness,
        "fitScore": fit,
        "nextConversationAngle": _next_angle(merged),
    }


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

    if conv.chat_role == "borrower":
        analysis = analyze_intent_message(req.content, conv.intent_summary)
        conv.intent_summary = analysis["intentSummary"]
        conv.seriousness_score = analysis["seriousnessScore"]
        conv.fit_score = analysis["fitScore"]
        conv.next_conversation_angle = analysis["nextConversationAngle"]
        db.add(conv)
        db.commit()
        db.refresh(conv)
    else:
        analysis = {
            "intentSummary": conv.intent_summary,
            "seriousnessScore": conv.seriousness_score,
            "fitScore": conv.fit_score,
            "nextConversationAngle": conv.next_conversation_angle,
        }

    assistant_text = "Got it. I’ll ask a few quick questions to narrow down the best option for you."
    assistant_metadata = {
        "intentAnalysis": analysis,
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
        "intentAnalysis": analysis,
        "loanRecommendations": None,
        "phaseAction": None,
        "loanAction": None,
    }
