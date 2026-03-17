import uuid
import re
from typing import Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.routers.v2_auth import OFFICER_HEADER, OFFICER_TOKEN, require_officer_role
from src.shared.audit import log_audit
from src.shared.db import Conversation, Loan, LoanPhase, Message, LoanProductCatalog, get_db
from src.shared.metrics import request_counter, request_errors_total


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
        "approvalProbability": c.approval_probability,
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
    from src.api.routers.v2_phases_router import DEFAULT_PHASES

    existing_names = set(db.execute(select(LoanPhase.name)).scalars().all())
    phases_added = 0
    for p in DEFAULT_PHASES:
        if p["name"] in existing_names:
            continue
        phase_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ks-los:v2:phase:{p['name']}"))
        db.add(LoanPhase(id=phase_id, **p))
        phases_added += 1
    if phases_added:
        db.commit()


def _merge_intent(prev: Optional[dict], new: IntentSummary) -> dict:
    allowed = set(IntentSummary.model_fields.keys())
    base: dict = {k: v for k, v in (prev or {}).items() if k in allowed}
    for k, v in new.model_dump(exclude_none=True).items():
        if base.get(k) in (None, "", []):
            base[k] = v
    return base


def _recommend_products(db: Session, intent: dict) -> list[dict[str, Any]]:
    from src.api.routers.v2_catalog_products_router import _ensure_seeded as _ensure_products_seeded

    _ensure_products_seeded(db)
    purpose = (intent.get("purpose") or "").lower()
    category = None
    if purpose in {"home", "mortgage", "property"}:
        category = "home_loan"
    elif purpose in {"car", "auto", "vehicle"}:
        category = "auto_loan"
    elif purpose in {"personal", "education", "business", "debt_consolidation"}:
        category = "personal_loan"

    stmt = select(LoanProductCatalog).where(LoanProductCatalog.status == "active")
    if category is not None:
        stmt = stmt.where(LoanProductCatalog.category == category)

    rows = db.execute(stmt.order_by(LoanProductCatalog.created_at.asc())).scalars().all()
    items: list[dict[str, Any]] = []
    for p in rows[:2]:
        tenure = None
        if p.min_tenure_months is not None and p.max_tenure_months is not None:
            tenure = f"{p.min_tenure_months}-{p.max_tenure_months} months"
        elif p.max_tenure_months is not None:
            tenure = f"Up to {p.max_tenure_months} months"
        elif p.min_tenure_months is not None:
            tenure = f"From {p.min_tenure_months} months"
        else:
            tenure = "Flexible"

        features = list(p.features or [])
        eligibility = list(p.eligibility_criteria or [])
        approval_speed = "Standard"
        if p.category == "personal_loan":
            approval_speed = "Fast"
        if p.category == "auto_loan":
            approval_speed = "Quick"

        items.append(
            {
                "name": p.name,
                "type": p.category,
                "estimatedRate": p.base_interest_rate or "Varies",
                "estimatedEmi": "TBD",
                "tenure": tenure,
                "totalInterest": "TBD",
                "approvalSpeed": approval_speed,
                "pros": features[:3],
                "cons": eligibility[:3],
                "recommendation": p.description or "Recommended based on your stated intent.",
            }
        )
    return items


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


def _extract_income(text: str) -> Optional[str]:
    t = text.lower()
    m = re.search(r"\b(income|salary)\b\s*(is|=|:)?\s*(\$|₹|usd\s*)?\s*([\d,]+)", t)
    if not m:
        return None
    return m.group(4).replace(",", "")


def _extract_existing_debts(text: str) -> Optional[str]:
    t = text.lower()
    m = re.search(r"\b(debt|debts|outstanding|owe|balance)\b[\w\s]*?(\$|₹|usd\s*)?\s*([\d,]+)", t)
    if not m:
        return None
    return m.group(3).replace(",", "")


def _extract_tenure(text: str) -> Optional[str]:
    t = text.lower()
    m = re.search(r"\b(\d{1,3})\s*(years|year|yrs|yr|months|month|mos|mo)\b", t)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    if unit in {"years", "year", "yrs", "yr"}:
        return f"{n * 12} months"
    return f"{n} months"


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
    if intent.get("purpose") == "debt_consolidation" and not intent.get("existingDebts"):
        return "Confirm total outstanding debts and current monthly repayments."
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


def _build_borrower_assistant_reply(intent: dict) -> str:
    purpose = (intent.get("purpose") or "").strip()
    purpose_label = {
        "home": "a home loan",
        "car": "a car loan",
        "personal": "a personal loan",
        "business": "a business loan",
        "education": "an education loan",
        "debt_consolidation": "debt consolidation",
    }.get(purpose, "a loan")

    questions: list[str] = []

    if not purpose:
        questions.append("What’s the loan for (home, car, personal, business, or debt consolidation)?")

    if purpose == "debt_consolidation" and not intent.get("existingDebts"):
        questions.append("Roughly how much total outstanding debt do you want to consolidate, and what’s your current total monthly payment?")

    if not intent.get("loanAmount") and purpose != "debt_consolidation":
        questions.append("What loan amount are you considering (even an approximate range)?")

    if not intent.get("monthlyIncome"):
        questions.append("What’s your approximate monthly income?")

    if not intent.get("employmentType"):
        questions.append("Are you salaried or self-employed?")

    if not intent.get("creditHistory"):
        questions.append("Do you know your credit score (or a rough range)?")

    if not intent.get("preferredTenure"):
        questions.append("What tenure would you be comfortable with (e.g., 36 months, 5 years)?")

    if not questions:
        return "Thanks — I have enough to refine recommendations. Do you want the lowest EMI, lowest total interest, or fastest approval?"

    top = questions[:3]
    bullets = "\n".join([f"- {q}" for q in top])
    return f"Got it — for {purpose_label}, I just need a few quick details:\n\n{bullets}"


def analyze_intent_message(content: str, previous_intent: Optional[dict]) -> dict[str, Any]:
    amount = _extract_amount(content)
    income = _extract_income(content)
    credit = _extract_credit_score(content)
    debts = _extract_existing_debts(content)
    tenure = _extract_tenure(content)
    intent = IntentSummary(
        purpose=_infer_purpose(content),
        urgency=_infer_urgency(content),
        loanAmount=amount,
        monthlyIncome=income,
        employmentType=_infer_employment(content),
        creditHistory=credit,
        existingDebts=debts,
        preferredTenure=tenure,
    )
    merged = _merge_intent(previous_intent, intent)
    seriousness, fit = _compute_scores(merged)
    return {
        "intentSummary": merged,
        "seriousnessScore": seriousness,
        "fitScore": fit,
        "nextConversationAngle": _next_angle(merged),
    }


def _parse_amount_to_number(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str):
        return None
    s = v.strip().lower().replace(",", "").replace(" ", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(k|m)?", s)
    if not m:
        return None
    base = float(m.group(1))
    unit = m.group(2)
    if unit == "k":
        return base * 1_000.0
    if unit == "m":
        return base * 1_000_000.0
    return base


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _compute_approval_probability(intent: dict) -> dict[str, Any]:
    credit_score = _parse_amount_to_number(intent.get("creditHistory"))
    income = _parse_amount_to_number(intent.get("monthlyIncome"))
    debts = _parse_amount_to_number(intent.get("existingDebts"))
    loan_amount = _parse_amount_to_number(intent.get("loanAmount"))

    prob = 0.55
    blockers: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []

    if credit_score is None:
        blockers.append({"title": "Missing credit score", "severity": "high", "detail": "Credit score not provided yet."})
        actions.append({"title": "Share credit score range", "impact": "high", "detail": "Provide an estimated credit score or bureau range."})
    else:
        if credit_score >= 760:
            prob += 0.25
        elif credit_score >= 720:
            prob += 0.18
        elif credit_score >= 680:
            prob += 0.10
        elif credit_score >= 620:
            prob -= 0.05
        else:
            prob -= 0.20
            blockers.append({"title": "Low credit score", "severity": "high", "detail": f"Credit score appears low ({int(credit_score)})."})
            actions.append({"title": "Improve credit hygiene", "impact": "high", "detail": "Pay on time, reduce utilization, and resolve delinquencies."})

    dti = None
    if income is None:
        blockers.append({"title": "Missing income", "severity": "medium", "detail": "Monthly income not provided yet."})
        actions.append({"title": "Provide income proof", "impact": "high", "detail": "Share pay slips or bank statements to validate affordability."})
    else:
        if debts is not None and income > 0:
            dti = debts / income
            if dti > 0.6:
                prob -= 0.15
                blockers.append({"title": "High debt burden", "severity": "high", "detail": f"Debt-to-income is high ({dti:.0%})."})
                actions.append({"title": "Reduce outstanding debts", "impact": "high", "detail": "Pay down revolving balances or consolidate to reduce obligations."})
            elif dti > 0.4:
                prob -= 0.08
                blockers.append({"title": "Elevated obligations", "severity": "medium", "detail": f"Debt-to-income is moderate ({dti:.0%})."})
                actions.append({"title": "Lower monthly obligations", "impact": "medium", "detail": "Reduce monthly payments to improve affordability."})
            elif dti < 0.2:
                prob += 0.05

    loan_to_income = None
    if loan_amount is not None and income is not None and income > 0:
        loan_to_income = loan_amount / (income * 12.0)
        if loan_to_income > 10:
            prob -= 0.12
            blockers.append(
                {"title": "Requested amount high vs income", "severity": "medium", "detail": "Requested loan size may be aggressive relative to income."}
            )
            actions.append({"title": "Consider smaller amount or longer tenure", "impact": "medium", "detail": "Adjust request to fit affordability constraints."})
        elif loan_to_income > 7:
            prob -= 0.06

    prob = _clamp(prob, 0.05, 0.95)
    if prob >= 0.70:
        band = "high"
    elif prob >= 0.45:
        band = "medium"
    else:
        band = "low"

    return {
        "probability": round(prob, 4),
        "band": band,
        "topBlockers": blockers[:3],
        "topActions": actions[:3],
        "inputsUsed": {
            "creditScore": int(credit_score) if isinstance(credit_score, (int, float)) else None,
            "monthlyIncome": income,
            "existingDebts": debts,
            "loanAmount": loan_amount,
            "dti": round(dti, 4) if isinstance(dti, (int, float)) else None,
            "loanToIncome": round(loan_to_income, 4) if isinstance(loan_to_income, (int, float)) else None,
        },
        "method": "heuristic_v1",
        "asOf": datetime.now(timezone.utc).isoformat(),
    }


def _desired_phase_index(intent: dict) -> int:
    if intent.get("purpose") and intent.get("loanAmount"):
        if intent.get("employmentType") and intent.get("monthlyIncome"):
            if intent.get("creditHistory"):
                return 3
            return 2
        return 1
    return 0


def apply_phase_guardrails(db: Session, conversation: Conversation) -> dict[str, Any] | None:
    phases = (
        db.execute(select(LoanPhase).where(LoanPhase.is_active.is_(True)).order_by(LoanPhase.sort_order.asc()))
        .scalars()
        .all()
    )
    if not phases:
        return None

    phase_ids = [p.id for p in phases]
    if conversation.current_phase_id not in phase_ids:
        conversation.current_phase_id = phases[0].id
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return None

    current_index = phase_ids.index(conversation.current_phase_id)
    desired_index = min(len(phases) - 1, _desired_phase_index(conversation.intent_summary or {}))
    if desired_index <= current_index:
        return None

    next_index = min(current_index + 1, desired_index)
    from_phase = phases[current_index]
    to_phase = phases[next_index]
    conversation.current_phase_id = to_phase.id
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return {
        "fromPhaseId": from_phase.id,
        "toPhaseId": to_phase.id,
        "reason": "sequential_guardrail",
    }


def _extract_amount_text(text: str) -> Optional[str]:
    candidates = re.findall(r"(?i)(?:usd|xcd|ec\$|\$)?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|m)?", text)
    if not candidates:
        return None
    raw, suffix = candidates[0]
    cleaned = raw.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if suffix:
        s = suffix.lower()
        if s == "k":
            value *= 1_000
        elif s == "m":
            value *= 1_000_000
    if value.is_integer():
        return str(int(value))
    return str(value)


def _infer_loan_type(text: str, intent: Optional[dict]) -> str:
    lower = text.lower()
    if any(k in lower for k in ["home", "mortgage", "property"]):
        return "Home Loan"
    if any(k in lower for k in ["car", "auto", "vehicle"]):
        return "Car Loan"
    if any(k in lower for k in ["personal", "debt"]):
        return "Personal Loan"
    if any(k in lower for k in ["business", "sme"]):
        return "Business Loan"
    if any(k in lower for k in ["education", "school", "tuition"]):
        return "Education Loan"

    purpose = ((intent or {}).get("purpose") or "").lower().strip()
    if purpose in {"home", "mortgage", "property"}:
        return "Home Loan"
    if purpose in {"car", "auto", "vehicle"}:
        return "Car Loan"
    if purpose in {"personal", "education", "business", "debt_consolidation"}:
        return "Personal Loan"
    return "Loan"


def _loan_catalog_category(loan_type: str) -> Optional[str]:
    t = loan_type.lower()
    if "home" in t or "mortgage" in t:
        return "home_loan"
    if "car" in t or "auto" in t or "vehicle" in t:
        return "auto_loan"
    if "personal" in t or "debt" in t:
        return "personal_loan"
    return None


def _maybe_pick_catalog_code(db: Session, loan_type: str) -> Optional[str]:
    category = _loan_catalog_category(loan_type)
    if not category:
        return None
    from src.api.routers.v2_catalog_products_router import _ensure_seeded as _ensure_products_seeded

    _ensure_products_seeded(db)
    row = (
        db.execute(
            select(LoanProductCatalog)
            .where(LoanProductCatalog.status == "active")
            .where(LoanProductCatalog.category == category)
            .order_by(LoanProductCatalog.created_at.asc())
        )
        .scalars()
        .first()
    )
    return row.code if row else None


def _create_loan_from_conversation(
    db: Session,
    conversation: Conversation,
    borrower_name: Optional[str],
    loan_type: str,
    loan_amount: Optional[str],
) -> Optional[str]:
    name = (borrower_name or conversation.borrower_name or "").strip()
    if not name:
        return None
    amount = (loan_amount or "").strip()
    if not amount:
        return None

    catalog_code = _maybe_pick_catalog_code(db, loan_type)
    product = None
    checklist = None
    if catalog_code:
        from src.api.routers.v2_loans_router import _build_document_checklist, _get_product_by_code

        product = _get_product_by_code(db, catalog_code)
        checklist = _build_document_checklist(catalog_code, product.required_documents if product else None)

    intent = conversation.intent_summary if isinstance(conversation.intent_summary, dict) else {}
    loan = Loan(
        borrower_name=name,
        loan_type=loan_type,
        loan_amount=amount,
        purpose=intent.get("purpose") if isinstance(intent, dict) else None,
        employment_type=intent.get("employmentType") if isinstance(intent, dict) else None,
        monthly_income=intent.get("monthlyIncome") if isinstance(intent, dict) else None,
        existing_debts=intent.get("existingDebts") if isinstance(intent, dict) else None,
        credit_score=intent.get("creditHistory") if isinstance(intent, dict) else None,
        tenure=intent.get("preferredTenure") if isinstance(intent, dict) else None,
        catalog_product_code=catalog_code,
        document_checklist=checklist,
        conversation_id=conversation.id,
        current_phase_id=conversation.current_phase_id,
        status="draft",
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan.id


def _apply_officer_directives(db: Session, conversation: Conversation, content: str) -> dict[str, Any]:
    text = content.strip()
    lower = text.lower()
    updates: dict[str, Any] = {}
    action_results: list[dict[str, Any]] = []
    created_loan_id: Optional[str] = None
    phase_target: Optional[str] = None

    assign_match = re.search(r"(?i)\b(?:assign|set)\s+officer\s+(?:to\s+)?(.+)$", text)
    if assign_match:
        officer = assign_match.group(1).strip()
        if officer:
            conversation.assigned_officer = officer
            updates["assignedOfficer"] = officer
            action_results.append({"type": "update_lead", "status": "success", "fields": ["assignedOfficer"]})

    status_match = re.search(r"(?i)\b(?:set|mark)\s+status\s+(?:to\s+)?(active|reviewing|qualified|closed)\b", text)
    if status_match:
        status = status_match.group(1).strip().lower()
        conversation.status = status
        updates["status"] = status
        action_results.append({"type": "update_lead", "status": "success", "fields": ["status"], "value": status})

    phase_match = re.search(r"(?i)\b(?:move|advance)\s+(?:to\s+)?phase\s+(.+)$", text)
    if phase_match:
        phase_label = phase_match.group(1).strip()
        if phase_label:
            phase_target = phase_label

    move_loan_match = re.search(r"(?i)\b(?:move|advance)\s+loan\s+([0-9a-f\\-]{20,64})\s+(?:to\s+)?phase\s+(.+)$", text)
    move_loan_id: Optional[str] = None
    move_loan_phase: Optional[str] = None
    if move_loan_match:
        move_loan_id = move_loan_match.group(1).strip()
        move_loan_phase = move_loan_match.group(2).strip()

    if "create loan" in lower or "open loan" in lower:
        name_match = re.search(r"(?i)\bfor\s+([a-z0-9][a-z0-9\s\-']{1,80})\b", text)
        borrower_name = name_match.group(1).strip() if name_match else (conversation.borrower_name or "Unknown")
        fallback_amount = (conversation.intent_summary or {}).get("loanAmount") if isinstance(conversation.intent_summary, dict) else None
        amount = _extract_amount_text(text) or fallback_amount or "250000"
        loan_type = _infer_loan_type(text, conversation.intent_summary if isinstance(conversation.intent_summary, dict) else None)
        catalog_code = _maybe_pick_catalog_code(db, loan_type)
        try:
            from src.api.routers.v2_loans_router import CreateLoanRequest, create_loan as _create_loan_endpoint

            created = _create_loan_endpoint(
                CreateLoanRequest(
                    borrowerName=borrower_name,
                    loanType=loan_type,
                    loanAmount=str(amount),
                    catalogProductCode=catalog_code,
                    conversationId=conversation.id,
                    createdBy="officer-chat",
                ),
                db,
            )
            created_loan_id = created.get("id") if isinstance(created, dict) else None
            action_results.append(
                {"type": "create_loan", "status": "success", "loanId": created_loan_id, "catalogProductCode": catalog_code}
            )
        except Exception as e:
            action_results.append({"type": "create_loan", "status": "error", "error": str(e)})

    if phase_target:
        phases = (
            db.execute(select(LoanPhase).where(LoanPhase.is_active.is_(True)).order_by(LoanPhase.sort_order.asc()))
            .scalars()
            .all()
        )
        desired = next((p for p in phases if p.name.strip().lower() == phase_target.strip().lower()), None)
        if desired:
            conversation.current_phase_id = desired.id
            updates["currentPhaseId"] = desired.id
            action_results.append({"type": "update_lead", "status": "success", "fields": ["currentPhaseId"], "value": desired.id})
        else:
            action_results.append({"type": "update_lead", "status": "error", "error": f"Phase not found: {phase_target}"})

    if move_loan_id and move_loan_phase:
        phases = (
            db.execute(select(LoanPhase).where(LoanPhase.is_active.is_(True)).order_by(LoanPhase.sort_order.asc()))
            .scalars()
            .all()
        )
        desired = next((p for p in phases if p.name.strip().lower() == move_loan_phase.strip().lower()), None)
        if not desired:
            action_results.append({"type": "move_loan_phase", "status": "error", "loanId": move_loan_id, "error": f"Phase not found: {move_loan_phase}"})
        else:
            try:
                from src.api.routers.v2_loans_router import PatchLoanRequest, patch_loan as _patch_loan_endpoint

                updated = _patch_loan_endpoint(move_loan_id, PatchLoanRequest(currentPhaseId=desired.id), db)
                action_results.append(
                    {
                        "type": "move_loan_phase",
                        "status": "success",
                        "loanId": move_loan_id,
                        "currentPhaseId": desired.id,
                        "phaseName": desired.name,
                        "loan": updated,
                    }
                )
            except Exception as e:
                action_results.append({"type": "move_loan_phase", "status": "error", "loanId": move_loan_id, "error": str(e)})

    if updates:
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    return {"conversationPatch": updates or None, "loanId": created_loan_id, "actionResults": action_results}


@router.post("")
def create_conversation(
    req: CreateConversationRequest,
    db: Session = Depends(get_db),
    x_officer_role: str | None = Header(default=None, alias=OFFICER_HEADER),
):
    request_counter.labels(endpoint="/api/conversations").inc()
    wants_officer = (req.chatRole or "").lower() == "officer"
    if wants_officer and x_officer_role != OFFICER_TOKEN:
        request_errors_total.labels(endpoint="/api/conversations").inc()
        log_audit(
            event="v2_conversation_create",
            endpoint="/api/conversations",
            status="forbidden",
            meta={"chatRole": req.chatRole},
        )
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

    log_audit(
        event="v2_conversation_create",
        endpoint="/api/conversations",
        status="success",
        meta={"conversationId": conversation.id, "chatRole": chat_role},
    )
    return {"conversation": _serialize_conversation(conversation), "greeting": greeting}


@router.get("")
def list_conversations(_: bool = Depends(require_officer_role), db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/conversations").inc()
    rows = db.execute(select(Conversation).order_by(Conversation.created_at.desc())).scalars().all()
    return [_serialize_conversation(c) for c in rows]

@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/conversations/{conversation_id}").inc()
    conv = db.get(Conversation, conversation_id)
    if not conv:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}").inc()
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _serialize_conversation(conv)


@router.patch("/{conversation_id}")
def patch_conversation(
    conversation_id: str,
    req: UpdateConversationRequest,
    _: bool = Depends(require_officer_role),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/conversations/{conversation_id}").inc()
    conv = db.get(Conversation, conversation_id)
    if not conv:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}").inc()
        log_audit(
            event="v2_conversation_patch",
            endpoint="/api/conversations/{conversation_id}",
            status="not_found",
            meta={"conversationId": conversation_id},
        )
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
    log_audit(
        event="v2_conversation_patch",
        endpoint="/api/conversations/{conversation_id}",
        status="success",
        meta={"conversationId": conversation_id},
    )
    return _serialize_conversation(conv)


@router.get("/{conversation_id}/messages")
def list_messages(conversation_id: str, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/conversations/{conversation_id}/messages").inc()
    rows = (
        db.execute(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()))
        .scalars()
        .all()
    )
    return [_serialize_message(m) for m in rows]


@router.post("/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    req: SendMessageRequest,
    db: Session = Depends(get_db),
    x_officer_role: str | None = Header(default=None, alias=OFFICER_HEADER),
):
    request_counter.labels(endpoint="/api/conversations/{conversation_id}/messages").inc()
    conv = db.get(Conversation, conversation_id)
    if not conv:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/messages").inc()
        log_audit(
            event="v2_message_send",
            endpoint="/api/conversations/{conversation_id}/messages",
            status="not_found",
            meta={"conversationId": conversation_id},
        )
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not req.content or not req.content.strip():
        raise HTTPException(status_code=400, detail="Content is required")

    if x_officer_role is not None and x_officer_role != OFFICER_TOKEN:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/messages").inc()
        raise HTTPException(status_code=403, detail="Officer access required")

    actor_is_officer = x_officer_role == OFFICER_TOKEN
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=req.content,
        metadata_json={"actorRole": "officer"} if actor_is_officer else None,
    )
    db.add(user_msg)
    db.commit()

    if conv.chat_role == "borrower" and not actor_is_officer:
        analysis = analyze_intent_message(req.content, conv.intent_summary)
        conv.intent_summary = analysis["intentSummary"]
        conv.seriousness_score = analysis["seriousnessScore"]
        conv.fit_score = analysis["fitScore"]
        conv.next_conversation_angle = analysis["nextConversationAngle"]
        approval_probability = _compute_approval_probability(analysis["intentSummary"])
        conv.approval_probability = approval_probability
        conv.recommended_products = _recommend_products(db, analysis["intentSummary"])
        db.add(conv)
        db.commit()
        db.refresh(conv)
        phase_action = apply_phase_guardrails(db, conv)
    else:
        analysis = {
            "intentSummary": conv.intent_summary,
            "seriousnessScore": conv.seriousness_score,
            "fitScore": conv.fit_score,
            "nextConversationAngle": conv.next_conversation_angle,
        }
        approval_probability = conv.approval_probability
        phase_action = None

    assistant_text = "Got it. I’ll ask a few quick questions to narrow down the best option for you."
    loan_action: Optional[dict[str, Any]] = None
    conversation_patch: Optional[dict[str, Any]] = None
    action_results: Optional[list[dict[str, Any]]] = None
    if actor_is_officer:
        applied = _apply_officer_directives(db, conv, req.content)
        conversation_patch = applied.get("conversationPatch")
        created_loan_id = applied.get("loanId")
        action_results = applied.get("actionResults") if isinstance(applied.get("actionResults"), list) else None
        if action_results:
            first_loan = next((a for a in action_results if a.get("status") == "success" and a.get("loanId")), None)
            if first_loan and first_loan.get("loanId"):
                loan_action = {"type": first_loan.get("type"), "loanId": first_loan.get("loanId")}
        if not loan_action and created_loan_id:
            loan_action = {"type": "create_loan", "loanId": created_loan_id}
        lines: list[str] = []
        if action_results:
            for a in action_results:
                if a.get("status") == "success" and a.get("type") == "create_loan" and a.get("loanId"):
                    lines.append(f"Created draft loan: {a.get('loanId')}.")
                elif a.get("status") == "success" and a.get("type") == "move_loan_phase" and a.get("loanId"):
                    phase_name = a.get("phaseName") or a.get("currentPhaseId") or "—"
                    lines.append(f"Moved loan {a.get('loanId')} to phase {phase_name}.")
                elif a.get("status") == "success" and a.get("type") == "update_lead":
                    fields = a.get("fields") if isinstance(a.get("fields"), list) else []
                    if fields:
                        lines.append(f"Updated lead fields: {', '.join(sorted([str(f) for f in fields]))}.")
                elif a.get("status") == "error":
                    err = a.get("error") or "Unknown error"
                    lines.append(f"Action failed: {a.get('type')}. {err}")
        elif conversation_patch:
            lines.append(f"Updated lead fields: {', '.join(sorted(conversation_patch.keys()))}.")
        elif created_loan_id:
            lines.append(f"Created draft loan: {created_loan_id}.")
        else:
            lines.append("Officer note recorded. You can: assign officer, set status, move phase, create loan, or move loan phase.")
        assistant_text = "\n".join(lines)
    elif conv.chat_role == "borrower":
        assistant_text = _build_borrower_assistant_reply(analysis["intentSummary"])
    assistant_metadata = {
        "actorRole": "officer_assistant" if actor_is_officer else None,
        "intentAnalysis": analysis,
        "loanRecommendations": conv.recommended_products if (conv.chat_role == "borrower" and not actor_is_officer) else None,
        "approvalProbability": approval_probability,
        "phaseAction": phase_action,
        "loanAction": loan_action,
        "conversationPatch": conversation_patch,
        "actionResults": action_results,
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

    log_audit(
        event="v2_message_send",
        endpoint="/api/conversations/{conversation_id}/messages",
        status="success",
        meta={"conversationId": conversation_id, "chatRole": conv.chat_role, "actorRole": "officer" if actor_is_officer else "borrower"},
    )
    return {
        "message": _serialize_message(assistant_msg),
        "intentAnalysis": analysis,
        "loanRecommendations": conv.recommended_products if (conv.chat_role == "borrower" and not actor_is_officer) else None,
        "approvalProbability": approval_probability,
        "phaseAction": phase_action,
        "loanAction": loan_action,
        "actionResults": action_results,
    }
