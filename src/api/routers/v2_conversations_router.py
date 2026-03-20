import uuid
import re
import os
import json
from typing import Any, Optional, Literal
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.api.routers.v2_auth import is_officer_request, require_officer_role, require_viewer_role
from src.config.llm import get_llm
from src.shared.audit import log_audit
from src.shared.db import Conversation, Loan, LoanDocument, LoanPhase, Message, LoanProductCatalog, get_db
from src.shared.metrics import (
    request_counter,
    request_errors_total,
    v2_conversations_created_total,
    v2_conversation_updates_total,
    v2_messages_sent_total,
)


router = APIRouter(prefix="/api/conversations", tags=["v2_conversations"], dependencies=[Depends(require_viewer_role)])


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
    recentDelinquencies12m: Optional[str] = None


class ApprovalProbabilityInputs(BaseModel):
    creditScore: Optional[int] = None
    monthlyIncome: Optional[float] = None
    existingDebts: Optional[float] = None
    loanAmount: Optional[float] = None
    dti: Optional[float] = None
    loanToIncome: Optional[float] = None


class ApprovalBlocker(BaseModel):
    title: str
    severity: Literal["low", "medium", "high"]
    detail: str


class ApprovalNextAction(BaseModel):
    title: str
    impact: Literal["low", "medium", "high"]
    detail: str


class ApprovalProbabilityNavigator(BaseModel):
    probability: float = Field(ge=0.0, le=1.0)
    band: Literal["low", "medium", "high"]
    topBlockers: list[ApprovalBlocker] = Field(default_factory=list, max_length=3)
    topActions: list[ApprovalNextAction] = Field(default_factory=list, max_length=3)
    inputsUsed: ApprovalProbabilityInputs
    method: str
    asOf: datetime


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
        existing = base.get(k)
        if existing in (None, "", []):
            base[k] = v
            continue
        if isinstance(existing, str) and existing.strip().lower() in {"unknown", "not_known", "not known", "n/a", "na"}:
            base[k] = v
    return base


def _extract_amount(text: str) -> Optional[str]:
    t = text.lower()
    m = re.search(r"\b(loan\s*amount|amount\s*needed|amount)\b\s*(is|=|:)?\s*(\$|usd\s*)?\s*([\d,]+)", t)
    if m:
        return m.group(4).replace(",", "")
    m = re.search(r"(\$|usd\s*)?\s*(\d{1,3}(?:[,\s]\d{3})+|\d+(?:\.\d+)?)\s*(k|m|million|thousand)?", t)
    if not m:
        return None
    start = max(0, m.start())
    end = min(len(t), m.end())
    token = t[start:end]
    before = t[max(0, start - 18) : start]
    after = t[end : min(len(t), end + 18)]
    context = f"{before} {after}"
    has_currency = ("$" in token) or ("usd" in token)
    has_loan_context = any(k in context for k in ["loan", "borrow", "mortgage", "home"])
    has_income_context = any(k in context for k in ["income", "salary", "/month", "per month", "monthly"])
    if has_income_context and not has_loan_context and not has_currency:
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
    if re.search(r"\b(no|none|zero)\s+(debt|debts|outstanding|dues)\b", t):
        return "0"
    m = re.search(r"\b(debt|debts|outstanding|owe|balance)\b[\w\s]*?(\$|₹|usd\s*)?\s*([\d,]+)", t)
    if not m:
        return None
    return m.group(3).replace(",", "")


def _is_yes(text: str) -> bool:
    t = text.strip().lower()
    return t in {"yes", "y", "yeah", "yep", "correct", "true"}


def _is_no(text: str) -> bool:
    t = text.strip().lower()
    return t in {"no", "n", "nope", "nah", "false"}


def _extract_recent_delinquencies_12m(text: str) -> Optional[str]:
    t = text.lower()
    if re.search(r"\b(no|none|never)\b[\w\s]{0,25}\b(late\s+payments?|collections?|delinquenc(?:y|ies))\b", t):
        return "no"
    if re.search(r"\b(yes|some|few)\b[\w\s]{0,25}\b(late\s+payments?|collections?|delinquenc(?:y|ies))\b", t):
        return "yes"
    return None


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

def _mentions_unknown_credit_score(text: str) -> bool:
    t = text.lower()
    if "credit" not in t or "score" not in t:
        return False
    if any(k in t for k in ["don't know", "dont know", "do not know", "not sure", "no idea", "unknown"]):
        return True
    if re.search(r"\b(i\s+)?(do\s+)?not\s+have\s+(a\s+)?credit\s+score\b", t):
        return True
    return False


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


def _compute_approval_probability(intent: dict) -> dict[str, Any] | None:
    credit_score = _parse_amount_to_number(intent.get("creditHistory"))
    income = _parse_amount_to_number(intent.get("monthlyIncome"))
    debts = _parse_amount_to_number(intent.get("existingDebts"))
    loan_amount = _parse_amount_to_number(intent.get("loanAmount"))

    usable_signals = sum(1 for v in [credit_score, income, loan_amount] if v is not None)
    if usable_signals < 2:
        return None

    prob = 0.0
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

    payload = {
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
    try:
        validated = ApprovalProbabilityNavigator.model_validate(payload)
        return validated.model_dump(mode="json")
    except ValidationError:
        return payload


def _build_borrower_system_prompt(
    phases: list[LoanPhase],
    current_phase_id: Optional[str],
    catalog_products: list[dict[str, Any]],
) -> str:
    active_phases = [p for p in phases if bool(getattr(p, "is_active", False))]
    active_phases.sort(key=lambda p: (int(getattr(p, "sort_order", 0) or 0), str(getattr(p, "id", ""))))
    phase_lines: list[str] = []
    for i, p in enumerate(active_phases):
        is_current = str(getattr(p, "id", "")) == str(current_phase_id or "")
        phase_lines.append(f'  {i + 1}. "{p.name}" (ID: {p.id}){" ← CURRENT" if is_current else ""}')
    phase_list = "\n".join(phase_lines) if phase_lines else "  (No phases configured)"

    current_phase = next((p for p in active_phases if str(getattr(p, "id", "")) == str(current_phase_id or "")), None)
    current_phase_name = (getattr(current_phase, "name", "") or "").strip()
    current_phase_docs: list[str] = []
    if current_phase_name:
        try:
            from src.api.routers.v2_phases_router import _PHASE_KNOWLEDGE as _PHASE_KNOWLEDGE_V2

            key = current_phase_name.lower()
            knowledge = _PHASE_KNOWLEDGE_V2.get(key) if isinstance(_PHASE_KNOWLEDGE_V2, dict) else None
            docs = knowledge.get("documents") if isinstance(knowledge, dict) else None
            if isinstance(docs, list):
                current_phase_docs = [str(d).strip() for d in docs if isinstance(d, str) and d.strip()]
        except Exception:
            current_phase_docs = []

    phase_docs_block = ""
    if current_phase_name:
        phase_docs_block = f'CURRENT PHASE: "{current_phase_name}"\n'
        if current_phase_docs:
            phase_docs_block += "TYPICAL DOCUMENTS FOR THIS PHASE:\n"
            phase_docs_block += "\n".join([f"- {d}" for d in current_phase_docs])
            phase_docs_block += "\n"
        phase_docs_block += "\n"

    catalog_json = json.dumps(catalog_products[:24], ensure_ascii=False)
    return (
        "You are LoanAssist — a premium, intelligent loan advisor for a modern financial institution. "
        "You combine the warmth of a personal banker with the precision of a financial analyst.\n\n"
        "PERSONALITY & TONE:\n"
        "- Elegant, confident, and reassuring — like a private wealth advisor, not a call centre agent\n"
        "- Concise and respectful of the borrower's time — never dump a checklist of questions\n"
        "- Use refined language. Say \"Let's explore what works best for you\" not \"Please provide the following details\"\n"
        "- Be conversational and human. Mirror the borrower's energy — if they're brief, be brief. If they're detailed, match that depth.\n\n"
        "GREETING (first message only):\n"
        "- Keep it short, warm, and premium. Two to three sentences maximum.\n"
        "- Welcome them, briefly state you're here to find the right financing path, and invite them to share what's on their mind\n"
        "- Do NOT list questions or bullet points in the greeting. Let the conversation flow naturally.\n\n"
        "INTENT UNDERSTANDING & PROCESS INITIATION:\n"
        "From the borrower's VERY FIRST message, you must:\n"
        "1. Identify their core intent (home purchase, car loan, business expansion, education, medical, debt consolidation, personal needs, etc.)\n"
        "2. Gauge urgency from their language (words like \"urgent\", \"immediately\", \"next month\", \"planning\" etc.)\n"
        "3. Immediately acknowledge what you've understood and begin the relevant process\n"
        "4. Ask only 1-2 targeted follow-up questions per message — the ones that matter most for THEIR specific situation\n"
        "5. Never ask generic questions that don't apply to their case\n\n"
        "PROGRESSIVE INFORMATION GATHERING:\n"
        "- Gather details naturally across 2-4 exchanges, not all at once\n"
        "- Prioritize questions by what matters most for THEIR specific loan type\n"
        "- For home loans: property identified? → budget → down payment capacity → income\n"
        "- For personal loans: amount needed → timeline → income → existing obligations\n"
        "- For business loans: purpose → revenue → vintage → collateral\n"
        "- For education: institution → course cost → co-applicant → future earning potential\n\n"
        "RECOMMENDATIONS:\n"
        "- Provide loan options as soon as you have enough context (don't wait for perfect information)\n"
        "- Always frame options as trade-offs so the borrower can make an informed choice\n"
        "- If you can make recommendations, include them in <loan_recommendations> tags as a JSON array.\n"
        "- When you are confident about a single best choice, include a <final_recommendation> tag with JSON.\n\n"
        "AVAILABLE LOAN PRODUCTS CATALOG:\n"
        "Use these as your primary options when recommending. If none fit, explain why and ask a single clarifying question.\n"
        f"{catalog_json}\n\n"
        "INTENT ANALYSIS (include after EVERY user message):\n"
        "Include an <intent_analysis> block containing ONLY JSON, with null for unknown fields, and update progressively:\n"
        "<intent_analysis>\n"
        "{\n"
        '  "purpose": null,\n'
        '  "urgency": null,\n'
        '  "affordability": null,\n'
        '  "monthlyIncome": null,\n'
        '  "existingDebts": null,\n'
        '  "loanAmount": null,\n'
        '  "preferredTenure": null,\n'
        '  "collateralAvailable": null,\n'
        '  "employmentType": null,\n'
        '  "creditHistory": null,\n'
        '  "recentDelinquencies12m": null,\n'
        '  "seriousnessScore": null,\n'
        '  "fitScore": null,\n'
        '  "nextConversationAngle": null\n'
        "}\n"
        "</intent_analysis>\n\n"
        "RULES:\n"
        "- Never ask the borrower to TYPE government ID numbers, bank account numbers, or other sensitive identifiers\n"
        "- If a sensitive document is needed, ask them to UPLOAD it (do not ask them to paste identifiers into chat)\n"
        "- Request documents only when appropriate for the CURRENT phase; do not jump ahead (e.g., do not ask for title deeds during Application Submission)\n"
        "- Always be transparent that figures are estimates until formal processing\n"
        "- Use the borrower's currency if evident; otherwise default to USD\n"
        "- Keep responses concise — ideally under 150 words for conversational messages\n"
        "- Never ask the same question twice if it has already been answered\n\n"
        "DOCUMENT HANDLING:\n"
        "- When requesting documents, use the product's requiredDocuments names exactly as listed in the catalog.\n"
        "- If you don't know the product yet, use the CURRENT phase typical documents list and request only the minimum set.\n"
        "- Mention that documents can be uploaded securely using the upload panel in the chat.\n"
        f"{phase_docs_block}"
        "LOAN JOURNEY PHASES:\n"
        "The borrower's application progresses through these phases:\n"
        f"{phase_list}\n\n"
        "PHASE PROGRESSION:\n"
        "PHASE PROGRESSION:\n"
        "- Only advance one phase at a time\n"
        "- Only include <phase_update> when there's a genuine progression signal\n"
        '<phase_update>{"phaseId": "the_phase_id_to_advance_to"}</phase_update>\n'
    )



def _extract_first_json_object(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    return m.group(0).strip()

def _extract_tag_block(text: str, tag: str) -> tuple[Optional[str], str]:
    if not text:
        return (None, "")
    pattern = re.compile(rf"(?is)<{re.escape(tag)}>\s*([\s\S]*?)\s*</{re.escape(tag)}>")
    m = pattern.search(text)
    if not m:
        return (None, text.strip())
    inner = (m.group(1) or "").strip()
    cleaned = pattern.sub("", text).strip()
    return (inner, cleaned)

def _coerce_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        return v if v else None
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip() or None


def _normalize_purpose(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip().lower()
    if not v:
        return None
    if any(k in v for k in ["home", "mortgage", "property", "house", "flat", "apartment"]):
        return "home"
    if any(k in v for k in ["car", "auto", "vehicle"]):
        return "car"
    if "education" in v or "tuition" in v or "school" in v:
        return "education"
    if "business" in v or "sme" in v:
        return "business"
    if "debt" in v or "consolid" in v:
        return "debt_consolidation"
    if "personal" in v:
        return "personal"
    return None


def _normalize_employment(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip().lower()
    if not v:
        return None
    if "salar" in v or "employ" in v or "payroll" in v:
        return "salaried"
    if "self" in v or "freel" in v or "contract" in v or "business" in v:
        return "self-employed"
    return str(value).strip()


def _apply_llm_phase_update(db: Session, conversation: Conversation, desired_phase_id: str) -> bool:
    phases = (
        db.execute(select(LoanPhase).where(LoanPhase.is_active.is_(True)).order_by(LoanPhase.sort_order.asc(), LoanPhase.id.asc()))
        .scalars()
        .all()
    )
    if not phases:
        return False
    phase_ids = [p.id for p in phases]
    if conversation.current_phase_id not in phase_ids:
        conversation.current_phase_id = phases[0].id
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return False
    current_index = phase_ids.index(conversation.current_phase_id)
    next_index = min(len(phases) - 1, current_index + 1)
    if phase_ids[next_index] != desired_phase_id:
        return False
    conversation.current_phase_id = desired_phase_id
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return True


def _llm_borrower_chat_turn(db: Session, conversation: Conversation) -> dict[str, Any]:
    phases = (
        db.execute(select(LoanPhase).where(LoanPhase.is_active.is_(True)).order_by(LoanPhase.sort_order.asc(), LoanPhase.id.asc()))
        .scalars()
        .all()
    )
    from src.api.routers.v2_catalog_products_router import _ensure_seeded as _ensure_products_seeded

    _ensure_products_seeded(db)
    products = (
        db.execute(
            select(LoanProductCatalog)
            .where(LoanProductCatalog.status == "active")
            .order_by(LoanProductCatalog.category.asc(), LoanProductCatalog.code.asc(), LoanProductCatalog.id.asc())
        )
        .scalars()
        .all()
    )
    catalog_products: list[dict[str, Any]] = []
    for p in products:
        catalog_products.append(
            {
                "code": p.code,
                "name": p.name,
                "category": p.category,
                "description": p.description,
                "minAmount": p.min_amount,
                "maxAmount": p.max_amount,
                "minTenureMonths": p.min_tenure_months,
                "maxTenureMonths": p.max_tenure_months,
                "baseInterestRate": p.base_interest_rate,
                "maxInterestRate": p.max_interest_rate,
                "processingFeePercent": p.processing_fee_percent,
                "prepaymentPenalty": p.prepayment_penalty,
                "minCreditScore": p.min_credit_score,
                "maxLtv": p.max_ltv,
                "minIncome": p.min_income,
                "collateralRequired": p.collateral_required,
                "insuranceRequired": p.insurance_required,
                "requiredDocuments": p.required_documents,
            }
        )

    system_prompt = _build_borrower_system_prompt(phases, conversation.current_phase_id, catalog_products)
    active_loan = (
        db.execute(
            select(Loan)
            .where(Loan.conversation_id == conversation.id)
            .order_by(Loan.created_at.desc(), Loan.id.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if active_loan:
        docs = (
            db.execute(
                select(LoanDocument)
                .where(LoanDocument.loan_id == active_loan.id)
                .order_by(LoanDocument.uploaded_at.desc(), LoanDocument.id.desc())
            )
            .scalars()
            .all()
        )
        if docs:
            lines: list[str] = []
            for d in docs[:20]:
                dt = (d.document_type or d.category or "document").strip() or "document"
                status = (d.status or "").strip().lower() or "uploaded"
                meta = d.meta if isinstance(d.meta, dict) else {}
                extraction = meta.get("extraction") if isinstance(meta, dict) else None
                extracted = extraction if isinstance(extraction, dict) else {}
                ex_status = (extracted.get("status") or "").strip().lower() if isinstance(extracted.get("status"), str) else ""
                fields = extracted.get("fields") if isinstance(extracted.get("fields"), dict) else {}
                has_salary = bool(fields.get("salaryLines")) if isinstance(fields, dict) else False
                has_amounts = bool(fields.get("amounts")) if isinstance(fields, dict) else False
                signals = []
                if has_salary:
                    signals.append("salary_detected")
                if has_amounts:
                    signals.append("amounts_detected")
                if ex_status == "ok":
                    signals.append("text_extracted")
                line = f"- {dt}: {status}"
                if signals:
                    line += f" ({', '.join(signals)})"
                lines.append(line)

            system_prompt += (
                "\n\nUPLOADED DOCUMENTS (non-sensitive summary):\n"
                + "\n".join(lines)
                + "\n\nGUIDANCE:\n"
                "- If a document above is already uploaded, do not ask for it again.\n"
                "- Do not quote document contents verbatim. Only use high-level signals.\n"
            )
    rows = (
        db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        .scalars()
        .all()
    )
    combined_user_text = "\n".join([m.content for m in rows if m.role == "user" and isinstance(m.content, str) and m.content.strip()])
    history: list[Any] = [SystemMessage(content=system_prompt)]
    for m in rows[-16:]:
        if m.role == "user":
            history.append(HumanMessage(content=m.content or ""))
        elif m.role == "assistant":
            history.append(AIMessage(content=m.content or ""))
    llm_error: Optional[str] = None
    models_to_try: list[str] = []
    configured_model = str(os.getenv("OLLAMA_MODEL", "qwen2.5:7b")).strip()
    if configured_model:
        models_to_try.append(configured_model)
    fallback_model = str(os.getenv("OLLAMA_FALLBACK_MODEL", "llama3")).strip()
    if fallback_model and fallback_model not in models_to_try:
        models_to_try.append(fallback_model)

    raw: str = ""
    for idx, model_name in enumerate(models_to_try):
        try:
            llm = get_llm(temperature=0.4, model=model_name)
            response = llm.invoke(history)
            raw = (response.content or "").strip()
            if raw:
                llm_error = None
                break
            llm_error = f"Empty response from model '{model_name}'."
        except Exception as e:
            llm_error = str(e) or e.__class__.__name__
            if idx == 0:
                msg = llm_error.lower()
                model_missing = ("model" in msg and "not found" in msg) or ("no such model" in msg)
                if model_missing:
                    continue
            break

    if not raw:
        raise RuntimeError(llm_error or "AI engine returned an empty response.")

    intent_block, remaining = _extract_tag_block(raw, "intent_analysis")
    loan_recs_block, remaining = _extract_tag_block(remaining, "loan_recommendations")
    final_block, remaining = _extract_tag_block(remaining, "final_recommendation")
    phase_block, remaining2 = _extract_tag_block(remaining, "phase_update")
    assistant_text = remaining2.strip()
    if not assistant_text:
        assistant_text = remaining2.strip() or remaining.strip()
    if not assistant_text:
        raise RuntimeError("AI engine response contained no assistant text.")

    intent_obj: dict[str, Any] = {}
    if intent_block:
        intent_json = _extract_first_json_object(intent_block) or intent_block
        parsed = json.loads(intent_json)
        if isinstance(parsed, dict):
            intent_obj = parsed

    loan_recommendations: Optional[list[dict[str, Any]]] = None
    if loan_recs_block:
        try:
            parsed_recs = json.loads(loan_recs_block)
            if isinstance(parsed_recs, list):
                loan_recommendations = [r for r in parsed_recs if isinstance(r, dict)]
        except Exception:
            loan_recommendations = None

    final_recommendation: Optional[dict[str, Any]] = None
    if final_block:
        try:
            parsed_final = json.loads(_extract_first_json_object(final_block) or final_block)
            if isinstance(parsed_final, dict):
                final_recommendation = parsed_final
        except Exception:
            final_recommendation = None

    grounded_loan_amount = _extract_amount(combined_user_text)
    grounded_income = _extract_income(combined_user_text)
    grounded_credit = _extract_credit_score(combined_user_text)
    if grounded_credit is None and _mentions_unknown_credit_score(combined_user_text):
        grounded_credit = "unknown"
    grounded_employment = _infer_employment(combined_user_text)
    grounded_debts = _extract_existing_debts(combined_user_text)
    grounded_tenure = _extract_tenure(combined_user_text)
    grounded_delinq = _extract_recent_delinquencies_12m(combined_user_text)

    intent_summary = IntentSummary(
        purpose=_normalize_purpose(intent_obj.get("purpose")),
        urgency=_coerce_optional_str(intent_obj.get("urgency")),
        affordability=_coerce_optional_str(intent_obj.get("affordability")),
        monthlyIncome=_coerce_optional_str(grounded_income or intent_obj.get("monthlyIncome")),
        existingDebts=_coerce_optional_str(grounded_debts or intent_obj.get("existingDebts")),
        loanAmount=_coerce_optional_str(grounded_loan_amount or intent_obj.get("loanAmount")),
        preferredTenure=_coerce_optional_str(grounded_tenure or intent_obj.get("preferredTenure")),
        collateralAvailable=_coerce_optional_str(intent_obj.get("collateralAvailable")),
        employmentType=_normalize_employment(grounded_employment or intent_obj.get("employmentType")),
        creditHistory=_coerce_optional_str(grounded_credit),
        recentDelinquencies12m=_coerce_optional_str(grounded_delinq or intent_obj.get("recentDelinquencies12m")),
    )
    merged = _merge_intent(conversation.intent_summary if isinstance(conversation.intent_summary, dict) else None, intent_summary)
    seriousness = intent_obj.get("seriousnessScore")
    fit = intent_obj.get("fitScore")
    next_angle = intent_obj.get("nextConversationAngle")
    if not isinstance(seriousness, int) or not isinstance(fit, int) or not isinstance(next_angle, str) or not next_angle.strip():
        computed_seriousness, computed_fit = _compute_scores(merged)
        seriousness = computed_seriousness
        fit = computed_fit
        next_angle = _next_angle(merged)

    desired_phase_id = None
    if phase_block:
        phase_json = _extract_first_json_object(phase_block) or phase_block
        parsed_phase = json.loads(phase_json)
        if isinstance(parsed_phase, dict) and isinstance(parsed_phase.get("phaseId"), str):
            desired_phase_id = parsed_phase.get("phaseId")

    return {
        "assistantText": assistant_text,
        "intentSummary": merged,
        "seriousnessScore": seriousness,
        "fitScore": fit,
        "nextConversationAngle": next_angle,
        "desiredPhaseId": desired_phase_id,
        "loanRecommendations": loan_recommendations,
        "finalRecommendation": final_recommendation,
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
        db.execute(select(LoanPhase).where(LoanPhase.is_active.is_(True)).order_by(LoanPhase.sort_order.asc(), LoanPhase.id.asc()))
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
            .order_by(LoanProductCatalog.code.asc(), LoanProductCatalog.id.asc())
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
    name = (borrower_name or conversation.borrower_name or "").strip() or "Borrower"
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
            db.execute(select(LoanPhase).where(LoanPhase.is_active.is_(True)).order_by(LoanPhase.sort_order.asc(), LoanPhase.id.asc()))
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
            db.execute(select(LoanPhase).where(LoanPhase.is_active.is_(True)).order_by(LoanPhase.sort_order.asc(), LoanPhase.id.asc()))
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

    add_phase_match = re.search(r"(?i)\badd\s+phase\s+(.+)$", text)
    if add_phase_match:
        raw = add_phase_match.group(1).strip()
        phase_name = raw
        phase_description: Optional[str] = None
        if " - " in raw:
            left, right = raw.split(" - ", 1)
            phase_name = left.strip()
            phase_description = right.strip() or None
        if phase_name:
            try:
                from src.api.routers.v2_phases_router import PhaseActionsRequest, execute_phase_actions as _execute_phase_actions

                resp = _execute_phase_actions(
                    PhaseActionsRequest(
                        actions=[
                            {
                                "type": "add_phase",
                                "name": phase_name,
                                "description": phase_description,
                            }
                        ]
                    ),
                    db,
                )
                new_phase_id: Optional[str] = None
                if isinstance(resp, dict):
                    results = resp.get("results")
                    if isinstance(results, list) and results:
                        first = results[0] if isinstance(results[0], dict) else None
                        if first:
                            new_phase_id = first.get("phaseId") if isinstance(first.get("phaseId"), str) else None
                action_results.append(
                    {"type": "add_phase", "status": "success", "phaseId": new_phase_id, "phaseName": phase_name}
                )
            except Exception as e:
                action_results.append({"type": "add_phase", "status": "error", "phaseName": phase_name, "error": str(e)})

    toggle_phase_match = re.search(r"(?i)\b(activate|deactivate)\s+phase\s+(.+)$", text)
    if toggle_phase_match:
        verb = toggle_phase_match.group(1).strip().lower()
        target_name = toggle_phase_match.group(2).strip()
        if target_name:
            phases = db.execute(select(LoanPhase)).scalars().all()
            desired = next((p for p in phases if p.name.strip().lower() == target_name.strip().lower()), None)
            if not desired:
                action_results.append(
                    {"type": "set_phase_active", "status": "error", "phaseName": target_name, "error": f"Phase not found: {target_name}"}
                )
            else:
                is_active = verb == "activate"
                try:
                    from src.api.routers.v2_phases_router import PhaseActionsRequest, execute_phase_actions as _execute_phase_actions

                    _execute_phase_actions(
                        PhaseActionsRequest(actions=[{"type": "set_phase_active", "phaseId": desired.id, "isActive": is_active}]),
                        db,
                    )
                    action_results.append(
                        {
                            "type": "set_phase_active",
                            "status": "success",
                            "phaseId": desired.id,
                            "phaseName": desired.name,
                            "isActive": is_active,
                        }
                    )
                except Exception as e:
                    action_results.append({"type": "set_phase_active", "status": "error", "phaseId": desired.id, "phaseName": desired.name, "error": str(e)})

    reorder_match = re.search(r"(?i)\breorder\s+phases\s*(?:to:|:)?\s+(.+)$", text)
    if reorder_match:
        raw = reorder_match.group(1).strip()
        if raw:
            pieces = [p.strip() for p in re.split(r"\s*(?:>|,|\n)\s*", raw) if p.strip()]
            phases = db.execute(select(LoanPhase)).scalars().all()
            phases_by_name = {p.name.strip().lower(): p for p in phases}
            all_ids = [p.id for p in phases]
            selected_ids: list[str] = []
            unknown: list[str] = []
            for name in pieces:
                desired = phases_by_name.get(name.strip().lower())
                if not desired:
                    unknown.append(name)
                else:
                    selected_ids.append(desired.id)

            if unknown:
                action_results.append({"type": "reorder_phases", "status": "error", "error": f"Unknown phases: {', '.join(unknown)}"})
            elif len(selected_ids) != len(all_ids):
                action_results.append(
                    {
                        "type": "reorder_phases",
                        "status": "error",
                        "error": f"Reorder requires all phases ({len(all_ids)}). Got {len(selected_ids)}.",
                    }
                )
            elif set(selected_ids) != set(all_ids):
                action_results.append({"type": "reorder_phases", "status": "error", "error": "Reorder phase list must match existing phases exactly."})
            else:
                try:
                    from src.api.routers.v2_phases_router import PhaseActionsRequest, execute_phase_actions as _execute_phase_actions

                    _execute_phase_actions(PhaseActionsRequest(actions=[{"type": "reorder_phases", "phaseIds": selected_ids}]), db)
                    action_results.append({"type": "reorder_phases", "status": "success", "phaseIds": selected_ids})
                except Exception as e:
                    action_results.append({"type": "reorder_phases", "status": "error", "error": str(e)})

    if updates:
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    return {"conversationPatch": updates or None, "loanId": created_loan_id, "actionResults": action_results}


@router.post("")
def create_conversation(
    req: CreateConversationRequest,
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    request_counter.labels(endpoint="/api/conversations").inc()
    wants_officer = (req.chatRole or "").lower() == "officer"
    if wants_officer and not is_officer_request(x_api_key, authorization):
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
        db.execute(select(LoanPhase).where(LoanPhase.is_active.is_(True)).order_by(LoanPhase.sort_order.asc(), LoanPhase.id.asc()))
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
    v2_conversations_created_total.labels(chat_role=chat_role).inc()
    return {"conversation": _serialize_conversation(conversation), "greeting": greeting}


@router.get("")
def list_conversations(_: bool = Depends(require_officer_role), db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/conversations").inc()
    rows = db.execute(select(Conversation).order_by(Conversation.created_at.desc(), Conversation.id.asc())).scalars().all()
    return [_serialize_conversation(c) for c in rows]

@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    request_counter.labels(endpoint="/api/conversations/{conversation_id}").inc()
    conv = db.get(Conversation, conversation_id)
    if not conv:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}").inc()
        raise HTTPException(status_code=404, detail="Conversation not found")
    actor_is_officer = is_officer_request(x_api_key, authorization)
    if conv.chat_role == "officer" and not actor_is_officer:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}").inc()
        raise HTTPException(status_code=403, detail="Officer access required")
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
    for field in sorted(req.model_fields_set):
        if field == "status":
            v2_conversation_updates_total.labels(field="status").inc()
        elif field == "borrowerName":
            v2_conversation_updates_total.labels(field="borrower_name").inc()
        elif field == "assignedOfficer":
            v2_conversation_updates_total.labels(field="assigned_officer").inc()
        elif field == "currentPhaseId":
            v2_conversation_updates_total.labels(field="current_phase_id").inc()
    return _serialize_conversation(conv)


@router.get("/{conversation_id}/messages")
def list_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    request_counter.labels(endpoint="/api/conversations/{conversation_id}/messages").inc()
    conv = db.get(Conversation, conversation_id)
    if not conv:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/messages").inc()
        raise HTTPException(status_code=404, detail="Conversation not found")
    actor_is_officer = is_officer_request(x_api_key, authorization)
    if conv.chat_role == "officer" and not actor_is_officer:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/messages").inc()
        raise HTTPException(status_code=403, detail="Officer access required")
    rows = (
        db.execute(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc(), Message.id.asc()))
        .scalars()
        .all()
    )
    return [_serialize_message(m) for m in rows]


@router.post("/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    req: SendMessageRequest,
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
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
        v2_messages_sent_total.labels(chat_role="unknown", actor_role="unknown", status="not_found").inc()
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not req.content or not req.content.strip():
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/messages").inc()
        log_audit(
            event="v2_message_send",
            endpoint="/api/conversations/{conversation_id}/messages",
            status="invalid",
            meta={"conversationId": conversation_id, "error": "Content is required"},
        )
        v2_messages_sent_total.labels(chat_role=conv.chat_role, actor_role="unknown", status="invalid").inc()
        raise HTTPException(status_code=400, detail="Content is required")

    actor_is_officer = is_officer_request(x_api_key, authorization)
    if conv.chat_role == "officer" and not actor_is_officer:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/messages").inc()
        log_audit(
            event="v2_message_send",
            endpoint="/api/conversations/{conversation_id}/messages",
            status="forbidden",
            meta={"conversationId": conversation_id, "chatRole": conv.chat_role},
        )
        v2_messages_sent_total.labels(chat_role=conv.chat_role, actor_role="borrower", status="forbidden").inc()
        raise HTTPException(status_code=403, detail="Officer access required")
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=req.content,
        metadata_json={"actorRole": "officer"} if actor_is_officer else None,
    )
    db.add(user_msg)
    db.commit()

    assistant_text_override: Optional[str] = None
    assistant_engine_override: Optional[str] = None
    final_recommendation_override: Optional[dict[str, Any]] = None

    if conv.chat_role == "borrower" and not actor_is_officer:
        last_assistant_text = (
            db.execute(
                select(Message.content)
                .where(Message.conversation_id == conversation_id, Message.role == "assistant")
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        llm_turn: Optional[dict[str, Any]] = None
        llm_error_detail: Optional[str] = None
        try:
            llm_turn = _llm_borrower_chat_turn(db, conv)
        except Exception as e:
            llm_turn = None
            llm_error_detail = str(e) or e.__class__.__name__
        desired_phase_id: Optional[str] = None
        if llm_turn:
            analysis = {
                "intentSummary": llm_turn["intentSummary"],
                "seriousnessScore": llm_turn["seriousnessScore"],
                "fitScore": llm_turn["fitScore"],
                "nextConversationAngle": llm_turn["nextConversationAngle"],
            }
            assistant_text_override = llm_turn.get("assistantText")
            assistant_engine_override = "borrower_chatgpt_llm"
            desired_phase_id = llm_turn.get("desiredPhaseId")
            final_recommendation_override = llm_turn.get("finalRecommendation") if isinstance(llm_turn.get("finalRecommendation"), dict) else None
        else:
            request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/messages").inc()
            v2_messages_sent_total.labels(chat_role=conv.chat_role, actor_role="borrower", status="llm_unavailable").inc()
            base_url = str(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).strip()
            model_name = str(os.getenv("OLLAMA_MODEL", "qwen2.5:7b")).strip()
            detail_parts = [
                "AI engine unavailable.",
                f"OLLAMA_BASE_URL={base_url}",
                f"OLLAMA_MODEL={model_name}",
            ]
            if llm_error_detail:
                detail_parts.append(f"Reason: {llm_error_detail}")
            detail_parts.append("Ensure Ollama is running and the configured model is pulled.")
            raise HTTPException(status_code=503, detail=" ".join(detail_parts))

        conv.intent_summary = analysis["intentSummary"]
        conv.seriousness_score = analysis["seriousnessScore"]
        conv.fit_score = analysis["fitScore"]
        conv.next_conversation_angle = analysis["nextConversationAngle"]
        approval_probability = _compute_approval_probability(analysis["intentSummary"])
        conv.approval_probability = approval_probability
        llm_recs = llm_turn.get("loanRecommendations") if isinstance(llm_turn, dict) else None
        if isinstance(llm_recs, list):
            conv.recommended_products = llm_recs
        elif conv.recommended_products is None:
            conv.recommended_products = []
        db.add(conv)
        db.commit()
        db.refresh(conv)
        if desired_phase_id:
            _apply_llm_phase_update(db, conv, desired_phase_id)
        phase_action = apply_phase_guardrails(db, conv)
        try:
            existing_loan_id = (
                db.execute(select(Loan.id).where(Loan.conversation_id == conv.id).order_by(Loan.created_at.desc(), Loan.id.desc()).limit(1))
                .scalars()
                .first()
            )
            intent_now = analysis.get("intentSummary") if isinstance(analysis, dict) else None
            intent_obj_now = intent_now if isinstance(intent_now, dict) else {}
            if not existing_loan_id:
                amount = _coerce_optional_str(intent_obj_now.get("loanAmount"))
                tenure = _coerce_optional_str(intent_obj_now.get("preferredTenure"))
                if amount and tenure:
                    loan_type = _infer_loan_type("", intent_obj_now)
                    _create_loan_from_conversation(db, conv, conv.borrower_name, loan_type, amount)
            else:
                loan = db.get(Loan, existing_loan_id)
                if loan and loan.current_phase_id != conv.current_phase_id:
                    loan.current_phase_id = conv.current_phase_id
                    db.add(loan)
                    db.commit()
        except Exception:
            pass
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
    assistant_engine = "default"
    loan_action: Optional[dict[str, Any]] = None
    conversation_patch: Optional[dict[str, Any]] = None
    action_results: Optional[list[dict[str, Any]]] = None
    if actor_is_officer:
        assistant_engine = "officer_rules"
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
                elif a.get("status") == "success" and a.get("type") == "add_phase":
                    phase_name = a.get("phaseName") or "—"
                    lines.append(f"Added phase: {phase_name}.")
                elif a.get("status") == "success" and a.get("type") == "set_phase_active":
                    phase_name = a.get("phaseName") or a.get("phaseId") or "—"
                    is_active = bool(a.get("isActive"))
                    lines.append(f"{'Activated' if is_active else 'Deactivated'} phase: {phase_name}.")
                elif a.get("status") == "success" and a.get("type") == "reorder_phases":
                    lines.append("Reordered phases.")
                elif a.get("status") == "success" and a.get("type") == "update_lead":
                    fields = a.get("fields") if isinstance(a.get("fields"), list) else []
                    if fields:
                        lines.append(f"Updated lead fields: {', '.join(sorted([str(f) for f in fields]))}.")
                elif a.get("status") == "error":
                    err = a.get("error") or "Unknown error"
                    lines.append(f"Action failed: {a.get('type')}. {err}")
            if not lines:
                lines.append("Actions completed.")
        elif conversation_patch:
            lines.append(f"Updated lead fields: {', '.join(sorted(conversation_patch.keys()))}.")
        elif created_loan_id:
            lines.append(f"Created draft loan: {created_loan_id}.")
        else:
            lines.append("Officer note recorded. You can: assign officer, set status, move phase, create loan, or move loan phase.")
        assistant_text = "\n".join(lines)
    elif conv.chat_role == "borrower":
        if isinstance(assistant_text_override, str) and assistant_text_override.strip():
            assistant_text = assistant_text_override.strip()
            assistant_engine = str(assistant_engine_override or "borrower_chatgpt_llm")
        else:
            raise HTTPException(status_code=503, detail="AI engine unavailable.")
    assistant_metadata = {
        "actorRole": "officer_assistant" if actor_is_officer else None,
        "assistantEngine": assistant_engine,
        "intentAnalysis": analysis,
        "loanRecommendations": conv.recommended_products if (conv.chat_role == "borrower" and not actor_is_officer) else None,
        "approvalProbability": approval_probability,
        "phaseAction": phase_action,
        "loanAction": loan_action,
        "conversationPatch": conversation_patch,
        "actionResults": action_results,
        "finalRecommendation": final_recommendation_override if (conv.chat_role == "borrower" and not actor_is_officer) else None,
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
    v2_messages_sent_total.labels(chat_role=conv.chat_role, actor_role="officer" if actor_is_officer else "borrower", status="success").inc()
    return {
        "message": _serialize_message(assistant_msg),
        "intentAnalysis": analysis,
        "loanRecommendations": conv.recommended_products if (conv.chat_role == "borrower" and not actor_is_officer) else None,
        "approvalProbability": approval_probability,
        "phaseAction": phase_action,
        "loanAction": loan_action,
        "actionResults": action_results,
    }


@router.get("/{conversation_id}/loan")
def get_conversation_loan(conversation_id: str, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/conversations/{conversation_id}/loan").inc()
    conv = db.get(Conversation, conversation_id)
    if not conv:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/loan").inc()
        raise HTTPException(status_code=404, detail="Conversation not found")
    loan = (
        db.execute(select(Loan).where(Loan.conversation_id == conversation_id).order_by(Loan.created_at.desc(), Loan.id.desc()).limit(1))
        .scalars()
        .first()
    )
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found for conversation")
    try:
        from src.api.routers import v2_loans_router as loans_api

        if loan.catalog_product_code:
            product = loans_api._get_product_by_code(db, loan.catalog_product_code)
            next_checklist = loans_api._merge_checklist(
                loan.document_checklist,
                loan.catalog_product_code,
                product.required_documents if product else None,
            )
            if next_checklist != loan.document_checklist:
                loan.document_checklist = next_checklist
                db.add(loan)
                db.commit()
                db.refresh(loan)

        return loans_api._serialize_loan(loan)
    except Exception:
        return {
            "id": loan.id,
            "borrowerName": loan.borrower_name,
            "loanType": loan.loan_type,
            "loanAmount": loan.loan_amount,
            "catalogProductCode": loan.catalog_product_code,
            "documentChecklist": loan.document_checklist,
            "currentPhaseId": loan.current_phase_id,
            "status": loan.status,
            "conversationId": loan.conversation_id,
        }


def _normalize_doc_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


@router.post("/{conversation_id}/documents/upload")
async def upload_conversation_document(
    conversation_id: str,
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/conversations/{conversation_id}/documents/upload").inc()
    conv = db.get(Conversation, conversation_id)
    if not conv:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/documents/upload").inc()
        raise HTTPException(status_code=404, detail="Conversation not found")

    loan = (
        db.execute(select(Loan).where(Loan.conversation_id == conversation_id).order_by(Loan.created_at.desc(), Loan.id.desc()).limit(1))
        .scalars()
        .first()
    )
    if not loan:
        intent = conv.intent_summary if isinstance(conv.intent_summary, dict) else {}
        amount = _coerce_optional_str(intent.get("loanAmount"))
        if not amount:
            raise HTTPException(status_code=400, detail="Loan is not ready yet. Please confirm loan amount first.")
        loan_type = _infer_loan_type("", intent)
        loan_id = _create_loan_from_conversation(db, conv, conv.borrower_name, loan_type, amount)
        if not loan_id:
            raise HTTPException(status_code=400, detail="Unable to create a loan for this conversation yet.")
        loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    raw = await file.read()
    if not raw:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/documents/upload").inc()
        raise HTTPException(status_code=400, detail="Empty upload")

    target = (name or "").strip()
    if not target:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/documents/upload").inc()
        raise HTTPException(status_code=400, detail="Document name is required")

    try:
        from src.api.routers import v2_loans_router as loans_api

        uploads_root = os.getenv("KS_LOS_UPLOAD_DIR", "data/uploads")
        doc_id = str(uuid.uuid4())
        safe = loans_api._safe_filename(file.filename or "document")
        loan_dir = os.path.join(uploads_root, "loans", loan.id)
        os.makedirs(loan_dir, exist_ok=True)
        stored_name = f"{doc_id}-{safe}"
        stored_path = os.path.join(loan_dir, stored_name)
        with open(stored_path, "wb") as f:
            f.write(raw)

        now = loans_api._now_iso()
        extracted = loans_api._extract_text_from_upload(raw, file.content_type, file.filename)
        preview = extracted[:800] if extracted else ""
        upload_meta = {
            "id": doc_id,
            "fileName": file.filename,
            "storedName": stored_name,
            "contentType": file.content_type,
            "sizeBytes": len(raw),
            "sha256": loans_api._sha256_bytes(raw),
            "uploadedAt": now,
            "extractedPreview": preview,
        }

        checklist = loan.document_checklist if isinstance(loan.document_checklist, dict) else {"productCode": loan.catalog_product_code, "items": [], "asOf": now}
        items_in = checklist.get("items") if isinstance(checklist, dict) else None
        items = items_in if isinstance(items_in, list) else []
        updated_items: list[dict[str, Any]] = []
        matched = False
        norm_target = _normalize_doc_name(target)
        for item in items:
            if not isinstance(item, dict):
                continue
            item_name = str(item.get("name") or "")
            if item_name == target or (_normalize_doc_name(item_name) == norm_target and norm_target):
                updated_items.append({**item, "name": item_name or target, "status": "submitted", "updatedAt": now, "upload": upload_meta})
                matched = True
            else:
                updated_items.append({**item})
        if not matched:
            updated_items.append({"name": target, "status": "submitted", "updatedAt": now, "upload": upload_meta})

        loan.document_checklist = {**checklist, "items": updated_items, "asOf": now}
        db.add(loan)
        db.commit()
        db.refresh(loan)
        log_audit(
            event="v2_conversation_document_upload",
            endpoint="/api/conversations/{conversation_id}/documents/upload",
            status="success",
            meta={"conversationId": conversation_id, "loanId": loan.id, "document": target, "docId": doc_id},
        )
        return loans_api._serialize_loan(loan)
    except HTTPException:
        raise
    except Exception as e:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/documents/upload").inc()
        raise HTTPException(status_code=500, detail=str(e) or "Upload failed")


@router.post("/{conversation_id}/signature")
async def upload_conversation_signature(
    conversation_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/conversations/{conversation_id}/signature").inc()
    conv = db.get(Conversation, conversation_id)
    if not conv:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/signature").inc()
        raise HTTPException(status_code=404, detail="Conversation not found")
    loan = (
        db.execute(select(Loan).where(Loan.conversation_id == conversation_id).order_by(Loan.created_at.desc(), Loan.id.desc()).limit(1))
        .scalars()
        .first()
    )
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found for conversation")

    raw = await file.read()
    if not raw:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/signature").inc()
        raise HTTPException(status_code=400, detail="Empty upload")

    try:
        from src.api.routers import v2_loans_router as loans_api

        uploads_root = os.getenv("KS_LOS_UPLOAD_DIR", "data/uploads")
        doc_id = str(uuid.uuid4())
        safe = loans_api._safe_filename(file.filename or "signature.png")
        loan_dir = os.path.join(uploads_root, "loans", loan.id)
        os.makedirs(loan_dir, exist_ok=True)
        stored_name = f"{doc_id}-{safe}"
        stored_path = os.path.join(loan_dir, stored_name)
        with open(stored_path, "wb") as f:
            f.write(raw)

        now = loans_api._now_iso()
        upload_meta = {
            "id": doc_id,
            "fileName": file.filename,
            "storedName": stored_name,
            "contentType": file.content_type,
            "sizeBytes": len(raw),
            "sha256": loans_api._sha256_bytes(raw),
            "uploadedAt": now,
            "extractedPreview": "",
        }

        checklist = loan.document_checklist if isinstance(loan.document_checklist, dict) else {"productCode": loan.catalog_product_code, "items": [], "asOf": now}
        items_in = checklist.get("items") if isinstance(checklist, dict) else None
        items = items_in if isinstance(items_in, list) else []
        signature_name = "Signature"
        updated_items: list[dict[str, Any]] = []
        seen_sig = False
        for item in items:
            if not isinstance(item, dict):
                continue
            if str(item.get("name") or "") == signature_name:
                updated_items.append({**item, "status": "submitted", "updatedAt": now, "upload": upload_meta})
                seen_sig = True
            else:
                updated_items.append({**item})
        if not seen_sig:
            updated_items.append({"name": signature_name, "status": "submitted", "updatedAt": now, "upload": upload_meta})

        loan.document_checklist = {**checklist, "items": updated_items, "asOf": now}
        db.add(loan)
        db.commit()
        db.refresh(loan)
        log_audit(
            event="v2_conversation_signature_upload",
            endpoint="/api/conversations/{conversation_id}/signature",
            status="success",
            meta={"conversationId": conversation_id, "loanId": loan.id, "docId": doc_id},
        )
        return loans_api._serialize_loan(loan)
    except HTTPException:
        raise
    except Exception as e:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/signature").inc()
        raise HTTPException(status_code=500, detail=str(e) or "Upload failed")
