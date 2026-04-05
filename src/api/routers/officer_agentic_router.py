"""
Officer Agentic Console Router (v3)

Provides officer-only endpoints to inspect the v3 agentic orchestrator state.
This is intended for an "officer console" UI that is integrated with the LOS
universe while keeping borrower flows unchanged.
"""

from __future__ import annotations

from typing import Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.shared.auth import require_officer_role
from src.shared.db import V3ConversationState, get_db


router = APIRouter(
    prefix="/api/officer/agentic",
    tags=["officer_agentic"],
    dependencies=[Depends(require_officer_role)],
)


def _safe_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return s or None
    return str(v).strip() or None


def _derive_borrower_name(state: V3ConversationState) -> Optional[str]:
    # Prefer captured context
    ctx = state.captured_context if isinstance(state.captured_context, dict) else {}
    for key in ("borrower_name", "name", "full_name", "borrowerName"):
        val = _safe_str(ctx.get(key))
        if val:
            return val

    # Try intent_analysis
    intent = state.intent_analysis if isinstance(state.intent_analysis, dict) else {}
    for key in ("borrower_name", "name", "full_name", "borrowerName"):
        val = _safe_str(intent.get(key))
        if val:
            return val

    # Fallback: parse conversation history (best-effort)
    hist = state.conversation_history if isinstance(state.conversation_history, list) else []
    for msg in reversed(hist[-50:]):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue
        content = _safe_str(msg.get("content")) or ""
        # naive extraction: "my name is X"
        lower = content.lower()
        if "my name is" in lower:
            idx = lower.find("my name is")
            tail = content[idx + len("my name is") :].strip()
            # take first 3 words
            parts = [p for p in tail.replace(".", " ").replace(",", " ").split() if p.strip()]
            if parts:
                return " ".join(parts[:3])
    return None


def _serialize_state_summary(state: V3ConversationState) -> dict[str, Any]:
    return {
        "sessionId": state.session_id,
        "applicationId": state.application_id,
        "mode": state.mode,
        "stage": state.current_stage,
        "borrowerName": _derive_borrower_name(state),
        "requiresManualReview": bool(state.requires_manual_review),
        "escalationNeeded": bool(state.escalation_needed),
        "stpStatus": state.stp_status,
        "updatedAt": state.updated_at.isoformat() if isinstance(state.updated_at, datetime) else None,
        "createdAt": state.created_at.isoformat() if isinstance(state.created_at, datetime) else None,
    }


@router.get("/sessions")
def list_agentic_sessions(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = (
        db.execute(select(V3ConversationState).order_by(V3ConversationState.updated_at.desc(), V3ConversationState.created_at.desc()))
        .scalars()
        .all()
    )
    return [_serialize_state_summary(s) for s in rows]


@router.get("/sessions/{session_id}")
def get_agentic_session(session_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    state = db.get(V3ConversationState, session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        **_serialize_state_summary(state),
        "capturedContext": state.captured_context,
        "intentAnalysis": state.intent_analysis,
        "confidenceScores": state.confidence_scores,
        "loanSnapshot": state.loan_snapshot,
        "recommendations": state.recommendations,
        "selectedRecommendation": state.selected_recommendation,
        "documentsChecklist": state.documents_checklist,
        "uploadedDocuments": state.uploaded_documents,
        "stpCheckpoints": state.stp_checkpoints,
        "bureauScore": state.bureau_score,
        "stpApproved": bool(state.stp_approved),
        "awaitingAcceptance": bool(state.awaiting_acceptance),
        "termsAccepted": bool(state.terms_accepted),
        "currentPhaseId": state.current_phase_id,
        "phaseHistory": state.phase_history,
        "discrepancyFlags": state.discrepancy_flags,
    }


@router.get("/sessions/{session_id}/messages")
def get_agentic_session_messages(session_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    state = db.get(V3ConversationState, session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    hist = state.conversation_history if isinstance(state.conversation_history, list) else []
    # Return as-is; UI will sanitize/format.
    return [m for m in hist if isinstance(m, dict)]

