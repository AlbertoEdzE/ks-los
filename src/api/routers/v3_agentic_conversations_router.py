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
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from src.shared.db import get_db, Conversation, Loan, LoanPhase, Message as DBMessage, V3ConversationState
from src.shared.state_persistence import get_or_create_state, update_state, get_state, delete_state
from src.shared.xml_parser import parse_llm_response
from src.core.calculation_engines import compute_full_loan_metrics, assess_stp_eligibility, parse_numeric
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


class ConversationPatchRequest(BaseModel):
    borrowerName: Optional[str] = None
    assignedOfficer: Optional[str] = None
    status: Optional[str] = None


def _serialize_conversation(conversation: Conversation) -> Dict[str, Any]:
    return {
        "id": conversation.id,
        "borrowerName": conversation.borrower_name,
        "status": conversation.status,
        "chatRole": conversation.chat_role,
        "currentPhaseId": conversation.current_phase_id,
        "seriousnessScore": conversation.seriousness_score,
        "fitScore": conversation.fit_score,
        "intentSummary": conversation.intent_summary,
        "approvalProbability": conversation.approval_probability,
        "recommendedProducts": conversation.recommended_products,
        "nextConversationAngle": conversation.next_conversation_angle,
        "assignedOfficer": conversation.assigned_officer,
        "createdAt": conversation.created_at.isoformat() if conversation.created_at else None,
    }


def _resolve_phase_id(db: Session, phase_name: str) -> Optional[str]:
    row = (
        db.query(LoanPhase)
        .filter(func.lower(LoanPhase.name) == phase_name.strip().lower())
        .order_by(LoanPhase.sort_order.asc(), LoanPhase.id.asc())
        .first()
    )
    return row.id if row else None


def _sync_phase(db: Session, session_id: str, state: AgenticOrchestratorState) -> None:
    conv = db.get(Conversation, session_id)
    if conv is None:
        conv = Conversation(
            id=session_id,
            borrower_name=state.captured_context.borrower_name if state.captured_context else None,
            status="active",
            chat_role="borrower",
            next_conversation_angle="Ask about loan purpose",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    loan = (
        db.query(Loan)
        .filter(Loan.conversation_id == session_id)
        .order_by(Loan.created_at.desc(), Loan.id.desc())
        .first()
    )

    desired_phase_name: Optional[str] = None
    if loan and (loan.stp_processing_status or "").strip().lower() in {"awaiting_acceptance", "awaiting-acceptance"}:
        desired_phase_name = "Conditional Approval & Offer"
    elif loan and (loan.stp_processing_status or "").strip().lower() in {"processing", "approved"}:
        desired_phase_name = "Underwriting & Credit Decision"
    elif loan and (loan.stp_processing_status or "").strip().lower() in {"awaiting_documents", "awaiting-documents"}:
        desired_phase_name = "Document Collection & KYC"
    elif state.mode == ConversationMode.APPLICATION:
        desired_phase_name = "Application Submission"
    elif state.mode == ConversationMode.COMPLETION:
        desired_phase_name = "Document Collection & KYC" if state.documents_checklist else "Verification & Credit Appraisal"
    else:
        desired_phase_name = "Lead & Inquiry"

    phase_id = _resolve_phase_id(db, desired_phase_name) if desired_phase_name else None
    if phase_id and conv.current_phase_id != phase_id:
        conv.current_phase_id = phase_id
        db.add(conv)
    if loan and phase_id and loan.current_phase_id != phase_id:
        loan.current_phase_id = phase_id
        db.add(loan)
    db.commit()


def _as_record(v: Any) -> Optional[Dict[str, Any]]:
    return v if isinstance(v, dict) else None


def _extract_intent_summary(parsed_metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    intent = _as_record(parsed_metadata.get("intentAnalysis"))
    if not intent:
        return None
    summary = _as_record(intent.get("intentSummary"))
    if summary:
        return summary
    return intent


def _build_loan_data_from_state(state: AgenticOrchestratorState) -> Dict[str, Any]:
    ctx = state.captured_context
    if ctx is None:
        return {}
    loan_data: Dict[str, Any] = {}
    if ctx.borrower_name:
        loan_data["borrower_name"] = ctx.borrower_name
    if ctx.email:
        loan_data["borrower_email"] = ctx.email
    if ctx.phone:
        loan_data["borrower_phone"] = ctx.phone
    if ctx.purpose:
        loan_data["purpose"] = ctx.purpose
        loan_data["loan_type"] = ctx.purpose
    if ctx.loan_amount is not None:
        loan_data["loan_amount"] = ctx.loan_amount
    if ctx.monthly_income is not None:
        loan_data["monthly_income"] = ctx.monthly_income
    if ctx.existing_debts is not None:
        loan_data["existing_debts"] = ctx.existing_debts
    if ctx.employment_type:
        loan_data["employment_type"] = ctx.employment_type
    if ctx.credit_score is not None:
        loan_data["credit_score"] = ctx.credit_score
    if ctx.property_value is not None:
        loan_data["property_value"] = ctx.property_value
    if ctx.down_payment is not None:
        loan_data["down_payment"] = ctx.down_payment
    if ctx.loan_tenure_years is not None:
        loan_data["tenure"] = f"{ctx.loan_tenure_years} years"
    if ctx.collateral_available:
        loan_data["collateral"] = ctx.collateral_available
    return loan_data


def _build_loan_data_from_history(state: AgenticOrchestratorState) -> Dict[str, Any]:
    msgs = getattr(state, "conversation_history", None)
    if not isinstance(msgs, list) or not msgs:
        return {}

    user_texts: list[str] = []
    for m in msgs:
        try:
            if getattr(m, "role", None) == "user" and isinstance(getattr(m, "content", None), str):
                user_texts.append(m.content)
        except Exception:
            continue

    combined = " ".join(user_texts).strip()
    if not combined:
        return {}

    low = combined.lower()
    out: Dict[str, Any] = {}

    if "home" in low or "mortgage" in low:
        out["loan_type"] = "home"
        out["purpose"] = "home"
    elif "vehicle" in low or "car" in low or "auto" in low:
        out["loan_type"] = "vehicle"
        out["purpose"] = "vehicle"
    elif "business" in low:
        out["loan_type"] = "business"
        out["purpose"] = "business"
    elif "personal" in low:
        out["loan_type"] = "personal"
        out["purpose"] = "personal"

    if "salaried" in low or "salary" in low:
        out["employment_type"] = "salaried"
    elif "self employed" in low or "self-employed" in low or "freelance" in low or "contractor" in low:
        out["employment_type"] = "self-employed"

    nums = [float(n.replace(",", "")) for n in re.findall(r"(\d[\d,]*)", combined)]
    if nums:
        out["loan_amount"] = nums[0]
    if len(nums) >= 2:
        out["monthly_income"] = nums[1]
    if len(nums) >= 3:
        out["existing_debts"] = nums[2]

    tenure_match = re.search(r"(?:tenure|term)\s*[:=]?\s*(\d[\d,\.]*)\s*(years?|yrs?|months?|mos?)?", low)
    if tenure_match:
        raw_num = tenure_match.group(1)
        unit = tenure_match.group(2) or ""
        unit = unit.strip().lower()
        if unit.startswith("y"):
            out["tenure"] = f"{raw_num} years"
        elif unit.startswith("m"):
            out["tenure"] = f"{raw_num} months"
        else:
            out["tenure"] = raw_num
    else:
        years_match = re.search(r"(\d[\d,\.]*)\s*(years?|yrs?)", low)
        months_match = re.search(r"(\d[\d,\.]*)\s*(months?|mos?)", low)
        if years_match:
            out["tenure"] = f"{years_match.group(1)} years"
        elif months_match:
            out["tenure"] = f"{months_match.group(1)} months"

    return out


def _should_compute_snapshot(loan_data: Dict[str, Any]) -> bool:
    principal = parse_numeric(loan_data.get("loan_amount"))
    monthly_income = parse_numeric(loan_data.get("monthly_income"))
    return principal > 0 and monthly_income > 0


def _should_compute_stp(loan_data: Dict[str, Any]) -> bool:
    principal = parse_numeric(loan_data.get("loan_amount"))
    monthly_income = parse_numeric(loan_data.get("monthly_income"))
    employment = str(loan_data.get("employment_type") or "").strip()
    return principal > 0 and monthly_income > 0 and bool(employment)


def _ensure_conversation_row(db: Session, session_id: str, state: AgenticOrchestratorState) -> Conversation:
    conv = db.get(Conversation, session_id)
    if conv is not None:
        return conv
    conv = Conversation(
        id=session_id,
        borrower_name=state.captured_context.borrower_name if state.captured_context else None,
        status="active",
        chat_role="borrower",
        next_conversation_angle="Ask about loan purpose",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _ensure_loan_row(db: Session, session_id: str, loan_data: Dict[str, Any], docs_checklist_v2: Optional[Dict[str, Any]]) -> Loan:
    existing = (
        db.query(Loan)
        .filter(Loan.conversation_id == session_id)
        .order_by(Loan.created_at.desc(), Loan.id.desc())
        .first()
    )

    def _set_if_present(attr: str, value: Any):
        if value is None:
            return
        if isinstance(value, str) and not value.strip():
            return
        if hasattr(existing, attr):
            setattr(existing, attr, value)

    if existing is None:
        existing = Loan(
            borrower_name=str(loan_data.get("borrower_name") or "Unknown"),
            borrower_email=loan_data.get("borrower_email"),
            borrower_phone=loan_data.get("borrower_phone"),
            loan_type=str(loan_data.get("loan_type") or loan_data.get("purpose") or "personal"),
            loan_amount=str(loan_data.get("loan_amount") or "0"),
            interest_rate=str(loan_data.get("interest_rate") or loan_data.get("interestRate") or ""),
            tenure=str(loan_data.get("tenure") or ""),
            monthly_income=str(loan_data.get("monthly_income") or ""),
            existing_debts=str(loan_data.get("existing_debts") or ""),
            credit_score=str(loan_data.get("credit_score") or ""),
            employment_type=loan_data.get("employment_type"),
            purpose=loan_data.get("purpose"),
            collateral=loan_data.get("collateral"),
            down_payment=str(loan_data.get("down_payment") or ""),
            property_value=str(loan_data.get("property_value") or ""),
            ltv=str(loan_data.get("ltv") or ""),
            document_checklist=docs_checklist_v2,
            conversation_id=session_id,
            status="draft",
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    _set_if_present("borrower_name", str(loan_data.get("borrower_name") or existing.borrower_name))
    _set_if_present("borrower_email", loan_data.get("borrower_email"))
    _set_if_present("borrower_phone", loan_data.get("borrower_phone"))
    _set_if_present("loan_type", str(loan_data.get("loan_type") or loan_data.get("purpose") or existing.loan_type))

    amount = loan_data.get("loan_amount")
    if amount is not None and parse_numeric(amount) > 0:
        existing.loan_amount = str(amount)

    income = loan_data.get("monthly_income")
    if income is not None and parse_numeric(income) > 0:
        existing.monthly_income = str(income)

    debts = loan_data.get("existing_debts")
    if debts is not None and parse_numeric(debts) >= 0:
        existing.existing_debts = str(debts)

    _set_if_present("interest_rate", str(loan_data.get("interest_rate") or loan_data.get("interestRate") or existing.interest_rate))
    _set_if_present("tenure", str(loan_data.get("tenure") or existing.tenure))
    _set_if_present("credit_score", str(loan_data.get("credit_score") or existing.credit_score))
    _set_if_present("employment_type", loan_data.get("employment_type"))
    _set_if_present("purpose", loan_data.get("purpose"))
    _set_if_present("collateral", loan_data.get("collateral"))
    _set_if_present("down_payment", str(loan_data.get("down_payment") or existing.down_payment))
    _set_if_present("property_value", str(loan_data.get("property_value") or existing.property_value))
    _set_if_present("ltv", str(loan_data.get("ltv") or existing.ltv))

    if docs_checklist_v2 is not None and existing.document_checklist != docs_checklist_v2:
        existing.document_checklist = docs_checklist_v2

    if existing.status in {"", None}:
        existing.status = "draft"
    db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


@router.get("/", response_model=List[Dict[str, Any]])
async def list_conversations(db: Session = Depends(get_db)):
    rows = (
        db.query(Conversation)
        .order_by(Conversation.created_at.desc(), Conversation.id.asc())
        .all()
    )
    return [_serialize_conversation(r) for r in rows]


@router.post("/", response_model=Dict[str, Any])
async def create_conversation(request: V3ConversationRequest, db: Session = Depends(get_db)):
    """Create a new agentic conversation - returns v2-compatible format"""
    session_id = request.session_id or str(uuid.uuid4())
    state = get_or_create_state(session_id, request.borrower_name)
    
    existing = db.get(Conversation, session_id)
    if existing is None:
        existing = Conversation(
            id=session_id,
            borrower_name=request.borrower_name,
            status="active",
            chat_role="borrower",
            next_conversation_angle="Ask about loan purpose",
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
    else:
        if request.borrower_name and not existing.borrower_name:
            existing.borrower_name = request.borrower_name
            db.add(existing)
            db.commit()
            db.refresh(existing)
    
    return {"conversation": _serialize_conversation(existing)}


@router.post("/{session_id}/messages", response_model=V3MessageResponse)
async def send_message(
    session_id: str,
    request: V3MessageRequest,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="x-idempotency-key"),
):
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

    key = (idempotency_key or "").strip() or None
    is_duplicate = False
    if key and state.conversation_history:
        last_hist = state.conversation_history[-1]
        if (
            last_hist.role == "assistant"
            and isinstance(last_hist.metadata, dict)
            and last_hist.metadata.get("idempotency_key") == key
        ):
            is_duplicate = True

    if not is_duplicate:
        state.add_message("user", request.content)
    
    # ──────────────────────────────────────────────────────────────────────
    # Agentic Processing Pipeline
    # ──────────────────────────────────────────────────────────────────────
    
    # Step 1: Repair Node (handle corrections, digressions)
    if not is_duplicate:
        repair_node = RepairNode()
        state = repair_node.process(state)
    
    # Step 2: RAG Node (policy-grounded responses)
    # Note: Pass knowledge_base if available
    if not is_duplicate:
        rag_node = RAGNode()
        state = rag_node.process(state)
    
    # Step 3: Mode-specific processing
    if not is_duplicate and state.mode == ConversationMode.ADVISORY:
        advisory_node = AdvisoryNode()
        state = advisory_node.process(state)
        
    elif not is_duplicate and state.mode == ConversationMode.APPLICATION:
        def _create_or_update_loan(loan_data: Dict[str, Any]):
            existing = (
                db.query(Loan)
                .filter(Loan.conversation_id == session_id)
                .order_by(Loan.created_at.desc(), Loan.id.desc())
                .first()
            )
            if existing is None:
                existing = Loan(
                    borrower_name=str(loan_data.get("borrower_name") or "Unknown"),
                    borrower_email=loan_data.get("borrower_email"),
                    borrower_phone=loan_data.get("borrower_phone"),
                    loan_type=str(loan_data.get("loan_type") or "personal"),
                    loan_amount=str(loan_data.get("loan_amount") or "0"),
                    purpose=loan_data.get("purpose"),
                    employment_type=loan_data.get("employment_type"),
                    monthly_income=str(loan_data.get("monthly_income") or ""),
                    existing_debts=str(loan_data.get("existing_debts") or ""),
                    conversation_id=session_id,
                    status="submitted",
                )
                db.add(existing)
                db.commit()
                db.refresh(existing)
            else:
                existing.borrower_name = str(loan_data.get("borrower_name") or existing.borrower_name)
                existing.borrower_email = loan_data.get("borrower_email") or existing.borrower_email
                existing.borrower_phone = loan_data.get("borrower_phone") or existing.borrower_phone
                existing.loan_type = str(loan_data.get("loan_type") or existing.loan_type)
                existing.loan_amount = str(loan_data.get("loan_amount") or existing.loan_amount)
                existing.purpose = loan_data.get("purpose") or existing.purpose
                existing.employment_type = loan_data.get("employment_type") or existing.employment_type
                if loan_data.get("monthly_income") is not None:
                    existing.monthly_income = str(loan_data.get("monthly_income"))
                if loan_data.get("existing_debts") is not None:
                    existing.existing_debts = str(loan_data.get("existing_debts"))
                existing.conversation_id = session_id
                if existing.status in {"draft", ""}:
                    existing.status = "submitted"
                db.add(existing)
                db.commit()
                db.refresh(existing)
            return {"id": existing.id}

        application_node = ApplicationNode(create_loan_callback=_create_or_update_loan)
        state = application_node.process(state)
        
    elif not is_duplicate and state.mode == ConversationMode.COMPLETION:
        completion_node = CompletionNode()
        state = completion_node.process(state)
    
    # Step 4: Escalation Node (check if human handoff needed)
    if not is_duplicate:
        escalation_node = EscalationNode()
        state = escalation_node.process(state)
    
    # ──────────────────────────────────────────────────────────────────────
    # Extract response
    # ──────────────────────────────────────────────────────────────────────

    last_message = state.conversation_history[-1] if state.conversation_history else None
    if (not is_duplicate) and key and last_message and last_message.role == "assistant":
        meta = last_message.metadata if isinstance(last_message.metadata, dict) else {}
        meta["idempotency_key"] = key
        last_message.metadata = meta
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
        "application_id": state.application_id,
        "stp_status": state.stp_status,
    }

    last_meta = last_message.metadata if last_message and isinstance(last_message.metadata, dict) else {}
    if (
        docs_checklist_v2 is not None
        and ("documentsChecklist" not in merged_metadata)
        and ("documents_checklist" in last_meta)
    ):
        merged_metadata["documentsChecklist"] = docs_checklist_v2
    if "loanSnapshot" not in merged_metadata and "loan_snapshot" in last_meta:
        merged_metadata["loanSnapshot"] = last_meta.get("loan_snapshot")
    if "loanRecommendations" not in merged_metadata and "recommendations" in last_meta:
        merged_metadata["loanRecommendations"] = last_meta.get("recommendations")
    if "selectedRecommendation" not in merged_metadata and "selected_recommendation" in last_meta:
        merged_metadata["selectedRecommendation"] = last_meta.get("selected_recommendation")
    if "awaitingAcceptance" not in merged_metadata and "awaiting_acceptance" in last_meta:
        merged_metadata["awaitingAcceptance"] = bool(last_meta.get("awaiting_acceptance"))

    loan = (
        db.query(Loan)
        .filter(Loan.conversation_id == session_id)
        .order_by(Loan.created_at.desc(), Loan.id.desc())
        .first()
    )
    if loan:
        merged_metadata["loanId"] = loan.id
        if docs_checklist_v2 is not None and loan.document_checklist != docs_checklist_v2:
            loan.document_checklist = docs_checklist_v2
            db.add(loan)
            db.commit()
            db.refresh(loan)

    # Calculate and attach deterministic metrics if not already present
    try:
        if "calculatedMetrics" not in merged_metadata:
            loan_data: dict[str, Any] = {}
            if loan is not None:
                loan_data = {
                    "id": loan.id,
                    "borrower_name": loan.borrower_name,
                    "borrower_email": loan.borrower_email,
                    "borrower_phone": loan.borrower_phone,
                    "loan_type": loan.loan_type,
                    "loan_amount": loan.loan_amount,
                    "interest_rate": loan.interest_rate,
                    "tenure": loan.tenure,
                    "monthly_income": loan.monthly_income,
                    "existing_debts": loan.existing_debts,
                    "credit_score": loan.credit_score,
                    "employment_type": loan.employment_type,
                    "purpose": loan.purpose,
                    "collateral": loan.collateral,
                    "down_payment": loan.down_payment,
                    "property_value": loan.property_value,
                    "ltv": loan.ltv,
                }
                fallback_state = _build_loan_data_from_state(state)
                if fallback_state:
                    for k, v in fallback_state.items():
                        cur = loan_data.get(k)
                        if cur in (None, ""):
                            loan_data[k] = v
                        elif k in ("loan_amount", "monthly_income") and parse_numeric(cur) <= 0:
                            loan_data[k] = v
                intent_summary = _extract_intent_summary(parsed_metadata) or {}
                if intent_summary:
                    inferred = {
                        "loan_type": str(intent_summary.get("purpose") or intent_summary.get("loan_type") or "personal"),
                        "loan_amount": intent_summary.get("loanAmount") or intent_summary.get("loan_amount"),
                        "monthly_income": intent_summary.get("monthlyIncome") or intent_summary.get("monthly_income"),
                        "existing_debts": intent_summary.get("existingDebts") or intent_summary.get("existing_debts"),
                        "credit_score": intent_summary.get("creditHistory") or intent_summary.get("credit_history"),
                        "employment_type": intent_summary.get("employmentType") or intent_summary.get("employment_type"),
                        "tenure": intent_summary.get("preferredTenure") or intent_summary.get("preferred_tenure"),
                        "property_value": intent_summary.get("propertyValue") or intent_summary.get("property_value"),
                        "down_payment": intent_summary.get("downPayment") or intent_summary.get("down_payment"),
                        "collateral": intent_summary.get("collateralAvailable") or intent_summary.get("collateral_available"),
                    }
                    for k, v in inferred.items():
                        if v is None or v == "":
                            continue
                        cur = loan_data.get(k)
                        if cur in (None, ""):
                            loan_data[k] = v
                        elif k in ("loan_amount", "monthly_income") and parse_numeric(cur) <= 0:
                            loan_data[k] = v
                fallback_hist = _build_loan_data_from_history(state)
                if fallback_hist:
                    for k, v in fallback_hist.items():
                        cur = loan_data.get(k)
                        if cur in (None, ""):
                            loan_data[k] = v
                        elif k in ("loan_amount", "monthly_income") and parse_numeric(cur) <= 0:
                            loan_data[k] = v
            else:
                loan_data = _build_loan_data_from_state(state)
                if not loan_data:
                    intent_summary = _extract_intent_summary(parsed_metadata) or {}
                    if intent_summary:
                        loan_data = {
                            "loan_type": str(intent_summary.get("purpose") or "personal"),
                            "loan_amount": intent_summary.get("loanAmount") or intent_summary.get("loan_amount"),
                            "monthly_income": intent_summary.get("monthlyIncome") or intent_summary.get("monthly_income"),
                            "existing_debts": intent_summary.get("existingDebts") or intent_summary.get("existing_debts"),
                            "credit_score": intent_summary.get("creditHistory") or intent_summary.get("credit_history"),
                            "employment_type": intent_summary.get("employmentType") or intent_summary.get("employment_type"),
                            "tenure": intent_summary.get("preferredTenure") or intent_summary.get("preferred_tenure"),
                            "property_value": intent_summary.get("propertyValue") or intent_summary.get("property_value"),
                            "down_payment": intent_summary.get("downPayment") or intent_summary.get("down_payment"),
                            "collateral": intent_summary.get("collateralAvailable") or intent_summary.get("collateral_available"),
                        }
                if loan_data:
                    fallback = _build_loan_data_from_history(state)
                    if fallback:
                        for k, v in fallback.items():
                            cur = loan_data.get(k)
                            if k not in loan_data or cur in (None, ""):
                                loan_data[k] = v
                            elif k in ("loan_amount", "monthly_income") and parse_numeric(cur) <= 0:
                                loan_data[k] = v
                else:
                    loan_data = _build_loan_data_from_history(state)
            if loan_data:
                calculated: Dict[str, Any] = {}
                stp = None
                if _should_compute_stp(loan_data):
                    stp = assess_stp_eligibility(loan_data)
                    calculated["stpTier"] = stp.tier
                    calculated["stp_tier"] = stp.tier
                    calculated["stpReasons"] = stp.reasons
                    calculated["stp_reasons"] = stp.reasons

                snapshot = None
                if _should_compute_snapshot(loan_data):
                    snapshot = compute_full_loan_metrics(loan_data)
                    approval_pct = snapshot.credit_risk.approval_probability
                    approval_prob = approval_pct / 100.0 if isinstance(approval_pct, (int, float)) else None
                    calculated.update(
                        {
                            "computedAt": snapshot.computed_at,
                            "emi": snapshot.emi.emi,
                            "totalInterest": snapshot.emi.total_interest,
                            "totalRepayment": snapshot.emi.total_repayment,
                            "apr": snapshot.apr.apr,
                            "foir": snapshot.affordability.foir,
                            "dti": snapshot.affordability.dti,
                            "dscr": snapshot.affordability.dscr,
                            "incomeSurplus": snapshot.affordability.income_surplus,
                            "ltv": snapshot.collateral.ltv,
                            "collateralCoverage": snapshot.collateral.collateral_coverage_ratio,
                            "approvalProbability": approval_prob,
                            "approval_probability": approval_pct,
                            "riskGrade": snapshot.credit_risk.risk_grade,
                            "risk_grade": snapshot.credit_risk.risk_grade,
                            "sanctionReadinessScore": snapshot.credit_risk.sanction_readiness_score,
                            "sanction_readiness_score": snapshot.credit_risk.sanction_readiness_score,
                            "eligibilityScore": snapshot.credit_risk.eligibility_score,
                            "eligibility_score": snapshot.credit_risk.eligibility_score,
                            "policyDeviationCount": snapshot.credit_risk.policy_deviation_count,
                            "policy_deviation_count": snapshot.credit_risk.policy_deviation_count,
                            "compensatingFactorCount": snapshot.credit_risk.compensating_factor_count,
                            "compensating_factor_count": snapshot.credit_risk.compensating_factor_count,
                            "delinquencyRiskSignal": snapshot.credit_risk.delinquency_risk_signal,
                            "delinquency_risk_signal": snapshot.credit_risk.delinquency_risk_signal,
                            "dropOffRiskSignal": snapshot.credit_risk.drop_off_risk_signal,
                            "drop_off_risk_signal": snapshot.credit_risk.drop_off_risk_signal,
                        }
                    )

                if calculated:
                    merged_metadata["calculatedMetrics"] = calculated

                if snapshot is not None:
                    loan = _ensure_loan_row(db, session_id, loan_data, docs_checklist_v2)
                    merged_metadata["loanId"] = loan.id
                    conv = _ensure_conversation_row(db, session_id, state)
                    if conv.borrower_name is None and state.captured_context and state.captured_context.borrower_name:
                        conv.borrower_name = state.captured_context.borrower_name
                    if state.captured_context and state.captured_context.seriousness_score is not None:
                        conv.seriousness_score = state.captured_context.seriousness_score
                    if state.captured_context and state.captured_context.fit_score is not None:
                        conv.fit_score = state.captured_context.fit_score
                    intent_summary = _extract_intent_summary(merged_metadata) or {}
                    if conv.seriousness_score is None and isinstance(intent_summary.get("seriousnessScore"), int):
                        conv.seriousness_score = int(intent_summary["seriousnessScore"])
                    if conv.fit_score is None and isinstance(intent_summary.get("fitScore"), int):
                        conv.fit_score = int(intent_summary["fitScore"])
                    next_angle = intent_summary.get("nextConversationAngle")
                    if isinstance(next_angle, str) and next_angle.strip():
                        conv.next_conversation_angle = next_angle.strip()
                    if isinstance(intent_summary, dict) and intent_summary:
                        conv.intent_summary = intent_summary
                    loan_recs = merged_metadata.get("loanRecommendations")
                    if isinstance(loan_recs, list) and loan_recs:
                        conv.recommended_products = loan_recs
                    approval_prob = calculated.get("approvalProbability")
                    if isinstance(approval_prob, (int, float)):
                        conv.approval_probability = {"probability": float(approval_prob), "computedAt": snapshot.computed_at}
                    db.add(conv)
                    db.commit()
                    db.refresh(conv)
    except Exception as e:
        logger.warning(f"Failed to compute calculated metrics for session {session_id}: {e}")

    try:
        conv = _ensure_conversation_row(db, session_id, state)
        intent_summary = _extract_intent_summary(merged_metadata) or {}

        if conv.borrower_name is None and state.captured_context and state.captured_context.borrower_name:
            conv.borrower_name = state.captured_context.borrower_name

        if state.captured_context and state.captured_context.seriousness_score is not None:
            conv.seriousness_score = state.captured_context.seriousness_score
        if state.captured_context and state.captured_context.fit_score is not None:
            conv.fit_score = state.captured_context.fit_score

        if conv.seriousness_score is None and isinstance(intent_summary.get("seriousnessScore"), int):
            conv.seriousness_score = int(intent_summary["seriousnessScore"])
        if conv.fit_score is None and isinstance(intent_summary.get("fitScore"), int):
            conv.fit_score = int(intent_summary["fitScore"])

        next_angle = intent_summary.get("nextConversationAngle")
        if isinstance(next_angle, str) and next_angle.strip():
            conv.next_conversation_angle = next_angle.strip()

        if isinstance(intent_summary, dict) and intent_summary:
            conv.intent_summary = intent_summary

        loan_recs = merged_metadata.get("loanRecommendations")
        if isinstance(loan_recs, list) and loan_recs:
            conv.recommended_products = loan_recs

        db.add(conv)
    except Exception as e:
        logger.warning(f"Failed to update conversation fields for session {session_id}: {e}")

    _sync_phase(db, session_id, state)

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
async def get_conversation(session_id: str, db: Session = Depends(get_db)):
    """
    Get conversation metadata in a v2-compatible format.
    """
    conv = db.get(Conversation, session_id)
    if conv is None:
        state = get_state(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conv = Conversation(
            id=session_id,
            borrower_name=state.captured_context.borrower_name if state.captured_context else None,
            status="active",
            chat_role="borrower",
            next_conversation_angle="Ask about loan purpose",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
    return _serialize_conversation(conv)


@router.patch("/{session_id}", response_model=Dict[str, Any])
async def patch_conversation(session_id: str, payload: ConversationPatchRequest, db: Session = Depends(get_db)):
    conv = db.get(Conversation, session_id)
    if conv is None:
        conv = Conversation(id=session_id)
        db.add(conv)
        db.commit()
        db.refresh(conv)
    if payload.borrowerName is not None:
        conv.borrower_name = payload.borrowerName
    if payload.assignedOfficer is not None:
        conv.assigned_officer = payload.assignedOfficer
    if payload.status is not None:
        conv.status = payload.status
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _serialize_conversation(conv)


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
        loan = (
            db.query(Loan)
            .filter(Loan.conversation_id == session_id)
            .order_by(Loan.created_at.desc(), Loan.id.desc())
            .first()
        )
        loan_id = loan.id if loan else None

        state = get_state(session_id)

        docs_checklist_v2 = None
        if state is not None and state.documents_checklist:
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
                ] if hasattr(state.documents_checklist, "business") and state.documents_checklist.business else [],
                "property": [
                    {"name": doc["name"], "status": "required" if doc.get("required") else "optional", "description": doc.get("description", "")}
                    for doc in state.documents_checklist.property
                ] if hasattr(state.documents_checklist, "property") and state.documents_checklist.property else [],
                "vehicle": [
                    {"name": doc["name"], "status": "required" if doc.get("required") else "optional", "description": doc.get("description", "")}
                    for doc in state.documents_checklist.vehicle
                ] if hasattr(state.documents_checklist, "vehicle") and state.documents_checklist.vehicle else [],
            }

        state_msgs: list[dict[str, Any]] = []
        if state is not None and state.conversation_history:
            for idx, msg in enumerate(state.conversation_history):
                if msg.role == "assistant":
                    clean_text, parsed = parse_llm_response(msg.content)
                    meta: dict[str, Any] = {}
                    if isinstance(parsed, dict):
                        meta.update(parsed)
                    if isinstance(msg.metadata, dict):
                        if "loan_snapshot" in msg.metadata and "loanSnapshot" not in meta:
                            meta["loanSnapshot"] = msg.metadata.get("loan_snapshot")
                        if "recommendations" in msg.metadata and "loanRecommendations" not in meta:
                            meta["loanRecommendations"] = msg.metadata.get("recommendations")
                        if "selected_recommendation" in msg.metadata:
                            meta["selectedRecommendation"] = msg.metadata.get("selected_recommendation")
                        if "awaiting_acceptance" in msg.metadata:
                            meta["awaitingAcceptance"] = bool(msg.metadata.get("awaiting_acceptance"))
                        if "calculatedMetrics" in msg.metadata and "calculatedMetrics" not in meta:
                            meta["calculatedMetrics"] = msg.metadata.get("calculatedMetrics")
                    if (
                        docs_checklist_v2 is not None
                        and isinstance(msg.metadata, dict)
                        and "documents_checklist" in msg.metadata
                    ):
                        meta["documentsChecklist"] = docs_checklist_v2
                    if loan_id:
                        meta["loanId"] = loan_id
                    meta["application_id"] = state.application_id if state else None
                    meta["stp_status"] = state.stp_status if state else None
                    state_msgs.append(
                        {
                            "id": f"v3-msg-{idx}",
                            "conversationId": session_id,
                            "role": msg.role,
                            "content": clean_text,
                            "metadata": meta,
                            "createdAt": msg.timestamp.isoformat() if msg.timestamp else None,
                        }
                    )
                else:
                    meta = msg.metadata if isinstance(msg.metadata, dict) else {}
                    if loan_id:
                        meta = {**meta, "loanId": loan_id}
                    state_msgs.append(
                        {
                            "id": f"v3-msg-{idx}",
                            "conversationId": session_id,
                            "role": msg.role,
                            "content": msg.content,
                            "metadata": meta,
                            "createdAt": msg.timestamp.isoformat() if msg.timestamp else None,
                        }
                    )
        
        messages = db.query(DBMessage).filter(
            DBMessage.conversation_id == session_id
        ).order_by(DBMessage.created_at.asc()).all()
        
        db_msgs = [
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
        
        merged = state_msgs + db_msgs
        merged.sort(key=lambda m: (m.get("createdAt") or "", m.get("id") or ""))
        logger.debug(f"Retrieved {len(merged)} messages for session {session_id}")
        return merged
        
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
