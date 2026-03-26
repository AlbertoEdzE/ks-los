import uuid
import re
import os
import json
import shutil
import subprocess
import tempfile
from typing import Any, Optional, Literal
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.api.routers.v2_auth import is_officer_request, require_officer_role, require_viewer_role
from src.config.llm import get_llm, is_ollama_available
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
borrower_router = APIRouter(prefix="/api/borrower", tags=["borrower"], dependencies=[Depends(require_viewer_role)])


class CreateConversationRequest(BaseModel):
    chatRole: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    status: Optional[str] = None
    borrowerName: Optional[str] = None
    assignedOfficer: Optional[str] = None
    currentPhaseId: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str


class CreateBorrowerApplicationRequest(BaseModel):
    borrowerName: str
    borrowerEmail: Optional[str] = None
    borrowerPhone: Optional[str] = None
    loanType: str
    loanAmount: str
    catalogProductCode: Optional[str] = None


class CreateBorrowerApplicationResponse(BaseModel):
    conversationId: str
    loan: dict[str, Any]


class IntentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: Optional[str] = None
    urgency: Optional[str] = None
    affordability: Optional[str] = None
    monthlyIncome: Optional[Any] = None  # Can be string or number from LLM
    existingDebts: Optional[Any] = None
    loanAmount: Optional[Any] = None
    propertyValue: Optional[Any] = None
    downPayment: Optional[Any] = None
    selectedPlan: Optional[str] = None
    preferredTenure: Optional[str] = None
    collateralAvailable: Optional[Any] = None
    employmentType: Optional[str] = None
    creditHistory: Optional[Any] = None
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
        if k == "selectedPlan":
            base[k] = v
            continue
        existing = base.get(k)
        if existing in (None, "", []):
            base[k] = v
            continue
        if isinstance(existing, str) and existing.strip().lower() in {"unknown", "not_known", "not known", "n/a", "na"}:
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

    rows = db.execute(stmt.order_by(LoanProductCatalog.code.asc(), LoanProductCatalog.id.asc())).scalars().all()
    items: list[dict[str, Any]] = []
    amount = _parse_amount_to_number(intent.get("loanAmount"))
    tenure_months = None
    if isinstance(intent.get("preferredTenure"), str):
        m = re.search(r"(\d+)\s*months", str(intent.get("preferredTenure")).lower())
        if m:
            tenure_months = int(m.group(1))
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

        rate_pct = None
        if isinstance(p.base_interest_rate, str):
            try:
                rate_pct = float(re.sub(r"[^0-9.]+", "", p.base_interest_rate))
            except Exception:
                rate_pct = None
        n = tenure_months
        if n is None:
            if p.max_tenure_months:
                n = int(p.max_tenure_months)
            elif p.min_tenure_months:
                n = int(p.min_tenure_months)
            else:
                n = 240 if (p.category == "home_loan") else 60
        est_emi = "TBD"
        total_interest = "TBD"
        if amount is not None and rate_pct is not None and n and n > 0:
            r = (rate_pct / 100.0) / 12.0
            try:
                factor = math.pow(1 + r, n)
                emi = (amount * r * factor) / (factor - 1) if factor > 1 and r > 0 else amount / n
                ti = emi * n - amount
                est_emi = f"${emi:,.0f}/mo"
                total_interest = f"${ti:,.0f}"
            except Exception:
                est_emi = "TBD"
                total_interest = "TBD"

        items.append(
            {
                "name": p.name,
                "type": p.category,
                "estimatedRate": p.base_interest_rate or "Varies",
                "estimatedEmi": est_emi,
                "tenure": tenure,
                "totalInterest": total_interest,
                "approvalSpeed": approval_speed,
                "pros": features[:3],
                "cons": eligibility[:3],
                "recommendation": p.description or "Recommended based on your stated intent.",
            }
        )
    return items


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
    has_explicit_loan_context = any(k in context for k in ["loan", "borrow", "mortgage", "finance", "financing"])
    has_property_context = any(k in context for k in ["property", "house", "home", "apartment", "condo", "valued", "value", "price"])
    has_loan_context = has_explicit_loan_context or ("mortgage" in context)
    has_income_context = any(k in context for k in ["income", "salary", "/month", "per month", "monthly"])
    if has_income_context and not has_loan_context and not has_currency:
        return None
    if has_property_context and not has_explicit_loan_context and not has_currency:
        return None
    raw = m.group(2).replace(",", "").replace(" ", "")
    unit = (m.group(3) or "").strip()
    if unit in {"k", "thousand"}:
        return f"{raw}k"
    if unit in {"m", "million"}:
        return f"{raw}m"
    return raw


def _extract_property_value(text: str) -> Optional[str]:
    t = text.lower()
    m = re.search(r"\b(property|house|home|apartment|condo)\b[^0-9]{0,40}\b(value|valued|price|priced|cost)\b[^0-9]{0,20}(\$|usd\s*)?\s*([\d,]+)", t)
    if m:
        return m.group(4).replace(",", "")
    m = re.search(r"\b(value|valued|price|priced|cost)\b[^0-9]{0,20}(\$|usd\s*)?\s*([\d,]+)", t)
    if m:
        return m.group(3).replace(",", "")
    m = re.search(r"\b(property|house|home|apartment|condo)\b[^0-9]{0,20}(\$|usd\s*)?\s*([\d,]+)", t)
    if m:
        return m.group(3).replace(",", "")
    return None


def _extract_down_payment(text: str) -> Optional[str]:
    t = text.lower().replace("downpayment", "down payment")
    m = re.search(r"\bdown\s+payment\b[^0-9%]{0,20}(\$|usd\s*)?\s*([\d,]+)", t)
    if m:
        return m.group(2).replace(",", "")
    m = re.search(r"\bdown\s+payment\b[^0-9%]{0,20}(\d{1,2})\s*%", t)
    if m:
        return f"{m.group(1)}%"
    return None


def _extract_income(text: str) -> Optional[str]:
    t = text.lower()
    m = re.search(r"\b(income|salary)\b\s*(is|=|:)?\s*(\$|₹|usd\s*)?\s*([\d,]+)", t)
    if m:
        return m.group(4).replace(",", "")
    m2 = re.search(r"\b([\d,]+)\s*(?:usd|\$)\s*(?:/|per\s*)?\s*(?:month|mo)\b", t.replace("usd/", "usd /"))
    if m2:
        return m2.group(1).replace(",", "")
    m3 = re.search(r"\b([\d,]+)(?:usd|\$)\s*(?:/|per\s*)?\s*(?:month|mo)\b", t)
    if m3:
        return m3.group(1).replace(",", "")
    return None


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
    if intent.get("purpose") == "home":
        if not intent.get("propertyValue") and not intent.get("loanAmount"):
            return "Confirm the property's purchase price and whether you have a specific property in mind."
        if intent.get("propertyValue") and not intent.get("downPayment"):
            return "Confirm your estimated down payment amount (or percentage)."
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


def _extract_question_lines(text: str) -> list[str]:
    out: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        if "?" in line:
            out.append(line)
    return out


def _build_borrower_assistant_reply(db: Session, conversation_id: str, intent: dict) -> tuple[str, str]:
    purpose = (intent.get("purpose") or "").strip()
    purpose_label = {
        "home": "a home loan",
        "car": "a car loan",
        "personal": "a personal loan",
        "business": "a business loan",
        "education": "an education loan",
        "debt_consolidation": "debt consolidation",
    }.get(purpose, "a loan")

    def _fmt_usd(n: float) -> str:
        try:
            return f"${n:,.0f}"
        except Exception:
            return "$—"

    def _question_to_ask() -> str | None:
        if not purpose:
            return "What’s the loan for (home, car, personal, business, or debt consolidation)?"

        if purpose == "debt_consolidation" and not intent.get("existingDebts"):
            return "Roughly how much total debt do you want to consolidate, and what’s your current total monthly payment?"

        if purpose == "home":
            pv = _parse_amount_to_number(intent.get("propertyValue"))
            la = _parse_amount_to_number(intent.get("loanAmount"))
            if pv is None and la is None:
                return "What’s the home purchase price (rough estimate)? That’s the property price — not your salary."
            if intent.get("propertyValue") and not intent.get("downPayment"):
                return "What down payment do you expect to put in (amount or %)?"

        if not intent.get("loanAmount") and purpose not in {"debt_consolidation", "home"}:
            return "What loan amount are you considering (even an approximate range)?"

        if not intent.get("monthlyIncome"):
            return "What’s your monthly income (and currency), and do you have any existing monthly debt payments?"

        if not intent.get("employmentType"):
            return "Are you salaried or self-employed?"

        credit = intent.get("creditHistory")
        credit_norm = str(credit).strip().lower() if credit is not None else ""
        if not credit_norm:
            return "Do you know your credit score (or a rough range)? If not, say “unknown”."
        if credit_norm in {"unknown", "not_known", "not known", "n/a", "na"} and not intent.get("recentDelinquencies12m"):
            return "Have you had any late payments, collections, or delinquencies in the last 12 months?"

        if not intent.get("preferredTenure"):
            return "What tenure would you be comfortable with (e.g., 15, 20, or 30 years)?"

        return None

    question = _question_to_ask()
    if not question:
        return (
            "Thanks — I have enough to refine recommendations. Do you want the lowest EMI, lowest total interest, or fastest approval?",
            "heuristic_only",
        )

    assistant_rows = (
        db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.role == "assistant")
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(8)
        )
        .scalars()
        .all()
    )
    recently_asked: set[str] = set()
    for m in assistant_rows:
        recently_asked.update(_extract_question_lines(m.content or ""))

    if question in recently_asked:
        return (
            "Thanks — I have enough to refine recommendations. Do you want the lowest EMI, lowest total interest, or fastest approval?",
            "heuristic_only",
        )

    summary_bits: list[str] = []
    if purpose == "home":
        pv_num = _parse_amount_to_number(intent.get("propertyValue"))
        dp_raw = intent.get("downPayment")
        la_num = _parse_amount_to_number(intent.get("loanAmount"))
        if pv_num is not None and pv_num > 0:
            summary_bits.append(f"property price about {_fmt_usd(pv_num)}")
        if isinstance(dp_raw, str) and dp_raw.strip():
            summary_bits.append(f"down payment {dp_raw.strip()}")
        if la_num is not None and la_num > 0 and pv_num is not None and pv_num > 0:
            ltv = la_num / pv_num
            if 0 < ltv < 2:
                summary_bits.append(f"loan around {_fmt_usd(la_num)} (~{round(ltv * 100):.0f}% LTV)")

    opener = f"Got it — for {purpose_label}." if not summary_bits else f"Got it — for {purpose_label}, I have {', '.join(summary_bits)}."
    return (f"{opener} {question}", "heuristic_only")


def analyze_intent_message(content: str, previous_intent: Optional[dict], last_assistant_text: Optional[str] = None) -> dict[str, Any]:
    amount = _extract_amount(content)
    income = _extract_income(content)
    credit = _extract_credit_score(content)
    if credit is None and _mentions_unknown_credit_score(content):
        credit = "unknown"
    debts = _extract_existing_debts(content)
    tenure = _extract_tenure(content)
    property_value = _extract_property_value(content)
    down_payment = _extract_down_payment(content)
    selected_plan = None
    c = content.lower()
    if "aggressive" in c:
        selected_plan = "aggressive"
    elif "balanced" in c:
        selected_plan = "balanced"
    elif "conservative" in c:
        selected_plan = "conservative"
    delinq = _extract_recent_delinquencies_12m(content)
    if delinq is None and last_assistant_text:
        if "late payments" in last_assistant_text.lower() and ("delinquenc" in last_assistant_text.lower() or "collections" in last_assistant_text.lower()):
            if _is_yes(content):
                delinq = "yes"
            elif _is_no(content):
                delinq = "no"
    derived_amount = amount
    if derived_amount is None and property_value and down_payment:
        pv = _parse_amount_to_number(property_value)
        if isinstance(down_payment, str) and down_payment.endswith("%") and pv is not None:
            try:
                pct = float(down_payment.strip("%")) / 100.0
                derived_amount = str(int(round(pv * (1.0 - pct))))
            except Exception:
                derived_amount = None
        else:
            dp = _parse_amount_to_number(down_payment)
            if pv is not None and dp is not None:
                derived_amount = str(int(round(max(0.0, pv - dp))))
    intent = IntentSummary(
        purpose=_infer_purpose(content),
        urgency=_infer_urgency(content),
        loanAmount=amount,
        propertyValue=property_value,
        downPayment=down_payment,
        selectedPlan=selected_plan,
        monthlyIncome=income,
        employmentType=_infer_employment(content),
        creditHistory=credit,
        existingDebts=debts,
        preferredTenure=tenure,
        recentDelinquencies12m=delinq,
    )
    if derived_amount is not None:
        intent.loanAmount = derived_amount
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
    s = re.sub(r"^(usd|xcd|ttd|jmd|gyd|eur|gbp|inr|cad|aud|mxn)", "", s)
    s = s.lstrip("$€£¥")
    s = re.sub(r"(usd|xcd|ttd|jmd|gyd|eur|gbp|inr|cad|aud|mxn)$", "", s)
    s = re.sub(r"[^0-9.km.]", "", s)
    if not s:
        return None
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
        "You are LoanAssist — a warm, intelligent loan advisor who makes borrowing feel like a guided conversation, not a form.\n\n"
        "YOUR PERSONALITY:\n"
        "- Warm and human — like a trusted financial friend, not a robot\n"
        "- One question at a time — NEVER ask two questions in one message\n"
        "- Acknowledge before asking — \"That's helpful, thanks! Now could you...\"\n"
        "- Match their energy — brief if they're brief, detailed if they're detailed\n"
        "- Celebrate progress — \"Perfect, that's exactly what I needed!\"\n\n"
        "FIRST MESSAGE (greeting only):\n"
        "- Keep it to 2-3 warm sentences\n"
        "- Welcome them and invite them to share what's on their mind\n"
        "- Example: \"Hi there! I'm your Loan Navigator. I'm here to help you find the right financing path — whether that's a new home, growing your business, or something else. What's on your mind today?\"\n\n"
        "CONVERSATION FLOW (STRICT ORDER - DO NOT SKIP):\n"
        "1. FIRST: Acknowledge their goal, ask for their NAME and TERRITORY (island)\n"
        "   Example: \"That's exciting! Before we dive in, may I ask who I'm speaking with and which island you're on?\"\n"
        "2. THEN: Ask about the property value OR loan amount (ONE at a time)\n"
        "3. THEN: Ask about down payment (if home loan) or timeline (if personal)\n"
        "4. THEN: Ask about employment type\n"
        "5. THEN: Ask about monthly income\n"
        "6. THEN: Ask about credit history\n"
        "NEVER skip ahead. NEVER combine questions.\n\n"
        "INFORMATION GATHERING (STRICT ORDER - DO NOT SKIP):\n"
        "1. FIRST: Name and Territory (island)\n"
        "2. THEN: Property value OR loan amount\n"
        "3. THEN: Down payment (if home loan) or timeline (if personal)\n"
        "4. THEN: Employment type\n"
        "5. THEN: Monthly income\n"
        "6. THEN: Credit history/score - MUST ASK BEFORE DOCUMENTS\n"
        "7. THEN: Documents (only AFTER all above info collected)\n"
        "NEVER skip ahead. NEVER ask for documents before credit score. NEVER combine questions.\n\n"
        "DOCUMENT REQUESTS (CRITICAL FORMAT):\n"
        "- When asking for a document, you MUST use this exact XML format:\n"
        '  `<document_request type="national_id">Your National ID or Passport</document_request>`\n'
        '  `<document_request type="job_letter">Employment Confirmation Letter</document_request>`\n'
        "- DO NOT just write text like 'please upload your ID' - USE THE XML TAG\n"
        "- The XML tag triggers a UI card with an Upload button\n"
        "- After the tag, add one sentence: 'You can upload this using the button above.'\n"
        "- Request ONE document at a time, not multiple\n"
        "- NEVER ask for documents BEFORE collecting credit score\n\n"
        "RECOMMENDATIONS:\n"
        "- ONLY show loan recommendation cards AFTER you have ALL of: purpose, loan amount (or property value), employment type, and monthly income\n"
        "- When showing loan options, DO NOT write numbered lists like '1. Option A, 2. Option B' in your text\n"
        "- Instead, mention that options are available and the UI will show them as cards\n"
        "- Use `<loan_recommendations>` XML tag with JSON array for UI cards\n"
        "- Example (ONLY when you have all required info): \"Based on your profile, I've prepared three loan paths for you. You'll see them as cards below - tap one to select.\"\n"
        "- If user asks for options but you're missing loan amount or property value, ask for that FIRST before showing cards\n"
        "- When user selects (says 'option 1', 'balanced', etc.), show `<loan_snapshot>` with selected details\n\n"
        "LOAN PRODUCTS CATALOG:\n"
        "Use these products when making recommendations. If none fit, explain why and ask ONE clarifying question.\n"
        f"{catalog_json}\n\n"
        "INTENT ANALYSIS (after EVERY message):\n"
        "Include an <intent_analysis> block with JSON. Update progressively as you learn more:\n"
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
        "CRITICAL RULES:\n"
        "- Keep messages under 100 words (except when explaining complex things)\n"
        "- Use contractions: \"I'm\", \"you're\", \"let's\", \"that's\"\n"
        "- NEVER ask two questions in one message — this is the #1 rule\n"
        "- Never say \"Please provide the following information\" — say \"Could you share...\" instead\n"
        "- If they've already answered something, don't ask again\n"
        "- Default to USD unless they mention another currency\n"
        "- Figures are estimates until formal processing — be transparent about this\n"
        "- ALWAYS collect name and territory BEFORE diving into financial details\n\n"
        "PHASE PROGRESSION:\n"
        "The borrower progresses through phases. Only advance one phase at a time when there's a clear signal.\n"
        f"{phase_list}\n"
        "Include <phase_update> only when there's genuine progression:\n"
        '<phase_update>{"phaseId": "the_phase_id_to_advance_to"}</phase_update>\n\n'
        f"{phase_docs_block}"
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


def _strip_think_blocks(text: str) -> str:
    if not text:
        return ""
    s = text
    s = re.sub(r"(?is)<think>[\s\S]*?</think>", "", s)
    s = re.sub(r"(?is)</think>", "", s)
    s = re.sub(r"(?is)<think>", "", s)
    return s.strip()

def _strip_emojis(text: str) -> str:
    if not text:
        return ""
    s = text
    s = re.sub(r"[\u200d\uFE0E\uFE0F]", "", s)
    s = re.sub(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF]", "", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()

def _maybe_append_credit_score_question(assistant_text: str, intent: dict, approval_probability: Any) -> str:
    credit = intent.get("creditHistory") if isinstance(intent, dict) else None
    credit_norm = str(credit).strip().lower() if credit is not None else ""
    missing_credit = not credit_norm or credit_norm in {"unknown", "not_known", "not known", "n/a", "na"}
    if not missing_credit:
        return assistant_text
    ap = approval_probability if isinstance(approval_probability, dict) else None
    blockers = ap.get("topBlockers") if isinstance(ap, dict) else None
    has_missing_blocker = False
    if isinstance(blockers, list):
        for b in blockers:
            if isinstance(b, dict) and str(b.get("title") or "").strip().lower() == "missing credit score":
                has_missing_blocker = True
                break
    if not has_missing_blocker:
        return assistant_text
    low = (assistant_text or "").lower()
    if "credit score" in low:
        return assistant_text
    return (assistant_text.rstrip() + " Do you know your credit score (or a rough range)? If not, say “unknown”.").strip()


def _dedupe_assistant_text(text: str) -> str:
    if not text:
        return ""

    def norm(line: str) -> str:
        return re.sub(r"\s+", " ", (line or "").strip()).lower()

    def norm_np(line: str) -> str:
        return re.sub(r"[^a-z0-9 ]+", "", norm(line))

    out: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if out and out[-1] == "":
                continue
            out.append("")
            continue

        if out and out[-1] and norm_np(line) == norm_np(out[-1]):
            continue

        if out and out[-1]:
            prev_np = norm_np(out[-1])
            cur_np = norm_np(line)
            if prev_np and cur_np.startswith(prev_np) and len(prev_np) >= 20:
                out[-1] = line.strip()
                continue

        out.append(line.strip())

    cleaned = "\n".join(out).strip()
    return cleaned


def _limit_questions_in_text(text: str, max_questions: int = 2) -> str:
    if not text:
        return ""
    if max_questions <= 0:
        return text.strip()

    out: list[str] = []
    q_count = 0
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            out.append("")
            continue

        if q_count >= max_questions:
            if "?" in line:
                continue
            if line.strip().startswith(("-", "•")):
                continue
            out.append(line)
            continue

        if "?" not in line:
            out.append(line)
            continue

        q_in_line = line.count("?")
        if q_count + q_in_line <= max_questions:
            out.append(line)
            q_count += q_in_line
            continue

        remaining = max_questions - q_count
        if remaining <= 0:
            continue
        cut = -1
        start = 0
        for _ in range(remaining):
            cut = line.find("?", start)
            if cut == -1:
                break
            start = cut + 1
        if cut != -1:
            out.append(line[: cut + 1].rstrip())
            q_count = max_questions
        else:
            out.append(line)
            q_count = max_questions

    return "\n".join(out).strip()


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
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[LLM] Conversation has {len(rows)} messages, combined user text: {combined_user_text[:200]}...")
    
    history: list[Any] = [SystemMessage(content=system_prompt)]
    for m in rows[-16:]:
        if m.role == "user":
            history.append(HumanMessage(content=m.content or ""))
        elif m.role == "assistant":
            history.append(AIMessage(content=m.content or ""))
    
    logger.info(f"[LLM] Sending {len(history)} messages to LLM (system + {len(rows[-16:])} history)")
    llm_error: Optional[str] = None
    models_to_try: list[str] = []
    configured_model = str(os.getenv("OLLAMA_MODEL")).strip() if os.getenv("OLLAMA_MODEL") else None
    if configured_model:
        models_to_try.append(configured_model)
    fallback_model = str(os.getenv("OLLAMA_FALLBACK_MODEL", "llama3")).strip()
    if fallback_model and fallback_model not in models_to_try:
        models_to_try.append(fallback_model)

    raw: str = ""
    for idx, model_name in enumerate(models_to_try):
        logger.info(f"[LLM] Trying model: {model_name}")
        try:
            llm = get_llm(temperature=0.4, model=model_name)
            response = llm.invoke(history)
            raw = (response.content or "").strip()
            logger.info(f"[LLM] Raw response ({len(raw)} chars): {raw[:500]}...")
            if raw:
                llm_error = None
                break
            llm_error = f"Empty response from model '{model_name}'."
        except Exception as e:
            llm_error = str(e) or e.__class__.__name__
            logger.error(f"[LLM] Model {model_name} failed: {llm_error}")
            if idx == 0:
                msg = llm_error.lower()
                model_missing = ("model" in msg and "not found" in msg) or ("no such model" in msg)
                if model_missing:
                    continue
            break

    if not raw:
        logger.error(f"[LLM] All models failed, last error: {llm_error}")
        raise RuntimeError(llm_error or "AI engine returned an empty response.")

    intent_block, remaining = _extract_tag_block(raw, "intent_analysis")
    loan_recs_block, remaining = _extract_tag_block(remaining, "loan_recommendations")
    final_block, remaining = _extract_tag_block(remaining, "final_recommendation")
    phase_block, remaining2 = _extract_tag_block(remaining, "phase_update")
    assistant_text = remaining2.strip()
    if not assistant_text:
        assistant_text = remaining2.strip() or remaining.strip()
    assistant_text = _strip_think_blocks(assistant_text)
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
    grounded_property_value = _extract_property_value(combined_user_text)
    grounded_down_payment = _extract_down_payment(combined_user_text)
    grounded_selected_plan = None
    combined_lower = combined_user_text.lower()
    if "aggressive" in combined_lower:
        grounded_selected_plan = "aggressive"
    elif "balanced" in combined_lower:
        grounded_selected_plan = "balanced"
    elif "conservative" in combined_lower:
        grounded_selected_plan = "conservative"
    grounded_income = _extract_income(combined_user_text)
    grounded_credit = _extract_credit_score(combined_user_text)
    if grounded_credit is None and _mentions_unknown_credit_score(combined_user_text):
        grounded_credit = "unknown"
    grounded_employment = _infer_employment(combined_user_text)
    grounded_debts = _extract_existing_debts(combined_user_text)
    grounded_tenure = _extract_tenure(combined_user_text)
    grounded_delinq = _extract_recent_delinquencies_12m(combined_user_text)
    derived_amount = grounded_loan_amount
    if derived_amount is None and grounded_property_value and grounded_down_payment:
        pv = _parse_amount_to_number(grounded_property_value)
        if isinstance(grounded_down_payment, str) and grounded_down_payment.endswith("%") and pv is not None:
            try:
                pct = float(grounded_down_payment.strip("%")) / 100.0
                derived_amount = str(int(round(pv * (1.0 - pct))))
            except Exception:
                derived_amount = None
        else:
            dp = _parse_amount_to_number(grounded_down_payment)
            if pv is not None and dp is not None:
                derived_amount = str(int(round(max(0.0, pv - dp))))

    intent_summary = IntentSummary(
        purpose=_normalize_purpose(intent_obj.get("purpose")),
        urgency=_coerce_optional_str(intent_obj.get("urgency")),
        affordability=_coerce_optional_str(intent_obj.get("affordability")),
        monthlyIncome=_coerce_optional_str(grounded_income or intent_obj.get("monthlyIncome")),
        existingDebts=_coerce_optional_str(grounded_debts or intent_obj.get("existingDebts")),
        loanAmount=_coerce_optional_str(derived_amount or grounded_loan_amount or intent_obj.get("loanAmount")),
        propertyValue=_coerce_optional_str(grounded_property_value or intent_obj.get("propertyValue")),
        downPayment=_coerce_optional_str(grounded_down_payment or intent_obj.get("downPayment")),
        selectedPlan=_coerce_optional_str(grounded_selected_plan or intent_obj.get("selectedPlan")),
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


def _desired_phase_index(intent: dict, latest_user_text: Optional[str] = None) -> int:
    idx = 0
    amount_signal = intent.get("loanAmount") or intent.get("propertyValue")
    if intent.get("purpose") and amount_signal:
        idx = 1

    t = (latest_user_text or "").lower()
    docs_signal = (
        bool(re.search(r"\bupload(?:ed|ing)?\b", t))
        or bool(re.search(r"\bdocuments?\b", t))
        or bool(re.search(r"\bpassport\b", t))
        or bool(re.search(r"\bkyc\b", t))
        or bool(re.search(r"\bid\b", t))
        or ".pdf" in t
        or ".png" in t
        or ".jpg" in t
        or ".jpeg" in t
        or "bank statement" in t
        or "pay slip" in t
        or "payslip" in t
        or "job letter" in t
    )
    if docs_signal:
        idx = max(idx, 2)

    return idx


def apply_phase_guardrails(db: Session, conversation: Conversation, latest_user_text: Optional[str] = None) -> dict[str, Any] | None:
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
    desired_index = min(len(phases) - 1, _desired_phase_index(conversation.intent_summary or {}, latest_user_text=latest_user_text))
    if desired_index < current_index:
        from_phase = phases[current_index]
        to_phase = phases[desired_index]
        conversation.current_phase_id = to_phase.id
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return {
            "fromPhaseId": from_phase.id,
            "toPhaseId": to_phase.id,
            "reason": "clamp_backwards",
        }
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


@router.post("/{conversation_id}/documents/ocr")
async def ocr_document(
    conversation_id: str,
    file: UploadFile = File(...),
    label: str | None = Form(default=None),
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    request_counter.labels(endpoint="/api/conversations/{conversation_id}/documents/ocr").inc()
    conv = db.get(Conversation, conversation_id)
    if not conv:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/documents/ocr").inc()
        raise HTTPException(status_code=404, detail="Conversation not found")

    actor_is_officer = is_officer_request(x_api_key, authorization)
    if conv.chat_role == "officer" and not actor_is_officer:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/documents/ocr").inc()
        raise HTTPException(status_code=403, detail="Officer access required")

    raw = await file.read()
    if len(raw) > 15_000_000:
        request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/documents/ocr").inc()
        raise HTTPException(status_code=413, detail="File too large")

    original_name = file.filename or "upload"
    ext = os.path.splitext(original_name)[1].lower()
    content_type = (file.content_type or "").lower()
    is_pdf = content_type == "application/pdf" or ext == ".pdf"

    engine = None
    extracted = ""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext or (".pdf" if is_pdf else ".bin")) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        if is_pdf:
            if not shutil.which("pdftotext"):
                request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/documents/ocr").inc()
                raise HTTPException(status_code=501, detail="pdftotext not available on server")
            proc = subprocess.run(
                ["pdftotext", "-layout", "-enc", "UTF-8", tmp_path, "-"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            if proc.returncode != 0:
                request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/documents/ocr").inc()
                raise HTTPException(status_code=500, detail=(proc.stderr.decode("utf-8", errors="replace") or "OCR failed"))
            extracted = proc.stdout.decode("utf-8", errors="replace")
            engine = "pdftotext"
        else:
            if not shutil.which("tesseract"):
                request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/documents/ocr").inc()
                raise HTTPException(status_code=501, detail="tesseract not available on server")
            proc = subprocess.run(
                ["tesseract", tmp_path, "stdout", "-l", "eng"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=45,
            )
            if proc.returncode != 0:
                request_errors_total.labels(endpoint="/api/conversations/{conversation_id}/documents/ocr").inc()
                raise HTTPException(status_code=500, detail=(proc.stderr.decode("utf-8", errors="replace") or "OCR failed"))
            extracted = proc.stdout.decode("utf-8", errors="replace")
            engine = "tesseract"
    finally:
        try:
            if tmp_path:
                os.unlink(tmp_path)
        except Exception:
            pass

    extracted = extracted.replace("\x0c", "").strip()
    lines = [ln.strip() for ln in extracted.splitlines() if ln.strip()]
    preview = " • ".join(lines[:5]) if lines else ""

    return {
        "fileName": original_name,
        "label": label or original_name,
        "contentType": file.content_type,
        "engine": engine,
        "text": extracted,
        "preview": preview,
    }


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
        if not os.getenv("PYTEST_CURRENT_TEST") and is_ollama_available():
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
            if last_assistant_text and isinstance(assistant_text_override, str):
                def _norm(s: str) -> str:
                    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
                same = _norm(assistant_text_override) == _norm(last_assistant_text or "")
                if not same:
                    prev_qs = set(_extract_question_lines(last_assistant_text or ""))
                    curr_qs = set(_extract_question_lines(assistant_text_override))
                    same = len(prev_qs) > 0 and prev_qs == curr_qs
                if same:
                    assistant_text_override, assistant_engine_override = _build_borrower_assistant_reply(db, conversation_id, analysis["intentSummary"])
        else:
            analysis = analyze_intent_message(req.content, conv.intent_summary, last_assistant_text=last_assistant_text)
            assistant_engine_override = "borrower_rules_fallback"

        conv.intent_summary = analysis["intentSummary"]
        conv.seriousness_score = analysis["seriousnessScore"]
        conv.fit_score = analysis["fitScore"]
        conv.next_conversation_angle = analysis["nextConversationAngle"]
        approval_probability = _compute_approval_probability(analysis["intentSummary"])
        conv.approval_probability = approval_probability
        llm_recs = llm_turn.get("loanRecommendations") if isinstance(llm_turn, dict) else None
        if isinstance(llm_recs, list):
            conv.recommended_products = llm_recs
        else:
            heuristic = _recommend_products(db, analysis["intentSummary"] if isinstance(analysis, dict) else {})
            if heuristic:
                conv.recommended_products = heuristic
            elif conv.recommended_products is None:
                conv.recommended_products = []
        db.add(conv)
        db.commit()
        db.refresh(conv)
        if desired_phase_id:
            _apply_llm_phase_update(db, conv, desired_phase_id)
        phase_action = apply_phase_guardrails(db, conv, latest_user_text=req.content)
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
            assistant_text, assistant_engine = _build_borrower_assistant_reply(db, conversation_id, analysis["intentSummary"])
        intent_dict = analysis.get("intentSummary") if isinstance(analysis, dict) else {}
        intent_dict = intent_dict if isinstance(intent_dict, dict) else {}
        assistant_text = _strip_emojis(assistant_text)
        
        # CRITICAL: Remove document requests if credit score not yet collected
        # This ensures proper conversation order
        has_credit = bool(intent_dict.get("creditHistory"))
        if not has_credit:
            # Strip document_request tags from response if credit not collected
            assistant_text = re.sub(r'<document_request[^>]*>[^<]*</document_request>', '', assistant_text, flags=re.IGNORECASE)
            assistant_text = re.sub(r'\n\s*You can upload.*paperclip.*\n?', '', assistant_text, flags=re.IGNORECASE)
            assistant_text = assistant_text.strip()

        assistant_text = _dedupe_assistant_text(_limit_questions_in_text(_strip_think_blocks(assistant_text), max_questions=2))
    loan_recommendation_cards: Optional[list[dict[str, Any]]] = None
    selected_recommendation: Optional[dict[str, Any]] = None
    loan_snapshot: Optional[dict[str, Any]] = None
    # CRITICAL: When showing recommendations, REMOVE credit score questions
    # Credit should be collected AFTER user selects a loan option
    # Note: loan_recommendation_cards is computed below, but we check it here after it's set
    try:
        intent_obj = analysis.get("intentSummary") if isinstance(analysis, dict) else {}
        intent_dict = intent_obj if isinstance(intent_obj, dict) else {}
        purpose = str(intent_dict.get("purpose") or "").strip().lower()
        income_num = _parse_amount_to_number(intent_dict.get("monthlyIncome"))
        has_income = income_num is not None
        employment = str(intent_dict.get("employmentType") or "").strip()
        has_employment = bool(employment)
        credit = intent_dict.get("creditHistory")
        credit_norm = str(credit).strip().lower() if credit is not None else ""
        has_credit = bool(credit_norm)
        home_ok = True
        if purpose == "home":
            home_ok = _parse_amount_to_number(intent_dict.get("propertyValue")) is not None and _parse_amount_to_number(intent_dict.get("downPayment")) is not None
        la = _parse_amount_to_number(intent_dict.get("loanAmount"))
        pv = _parse_amount_to_number(intent_dict.get("propertyValue"))
        dp_raw = intent_dict.get("downPayment")
        dp = None
        if isinstance(dp_raw, str) and dp_raw.endswith("%") and pv is not None:
            try:
                pct = float(dp_raw.strip("%")) / 100.0
                dp = pv * pct
            except Exception:
                dp = None
        else:
            dp = _parse_amount_to_number(dp_raw)
        if pv is None and la is not None:
            pv = la
        if la is not None and pv is not None and dp is not None and la > pv and purpose == "home":
            la = max(0.0, pv - dp)

        rate_pct = None
        recs = conv.recommended_products if isinstance(conv.recommended_products, list) else []
        if recs and isinstance(recs[0], dict):
            er = recs[0].get("estimatedRate")
            if isinstance(er, str):
                try:
                    rate_pct = float(re.sub(r"[^0-9.]+", "", er))
                except Exception:
                    rate_pct = None
        if rate_pct is None:
            rate_pct = 8.4

        # Show recommendations when we have basic financial info (credit can come after)
        # For home loans, property value and down payment are optional - we can estimate with just loan amount
        ready_for_recommendations = bool(purpose) and la is not None and la > 0 and has_income and has_employment
        if ready_for_recommendations and rate_pct is not None:
            def _calc(amount: float, annual_rate_pct: float, tenure_years: int) -> tuple[float, float, float]:
                n = max(1, tenure_years * 12)
                r = (annual_rate_pct / 100.0) / 12.0
                factor = math.pow(1 + r, n)
                emi = (amount * r * factor) / (factor - 1) if factor > 1 and r > 0 else amount / n
                total = emi * n
                return (emi, total - amount, total)

            option_defs = [
                ("Aggressive Plan", "aggressive", max(0.1, rate_pct - 0.25), 15),
                ("Balanced Plan", "balanced", max(0.1, rate_pct), 20),
                ("Conservative Plan", "conservative", max(0.1, rate_pct + 0.5), 30),
            ]
            cards: list[dict[str, Any]] = []
            for name, t, rate, yrs in option_defs:
                emi, ti, tr = _calc(float(la), float(rate), int(yrs))
                cards.append(
                    {
                        "name": name,
                        "type": t,
                        "interest_rate": float(round(rate, 2)),
                        "tenure_years": int(yrs),
                        "monthly_emi": float(round(emi, 2)),
                        "total_interest": float(round(ti, 2)),
                        "total_repayment": float(round(tr, 2)),
                        "pros": [],
                        "cons": [],
                        "recommended": t == "balanced",
                    }
                )
            loan_recommendation_cards = cards

            # CRITICAL: When showing recommendations, REMOVE credit score questions
            # Credit should be collected AFTER user selects a loan option
            if loan_recommendation_cards and not selected_recommendation:
                # Remove credit score questions from recommendation messages
                assistant_text = re.sub(r'\s*Do you know your credit score.*$', '', assistant_text, flags=re.IGNORECASE | re.MULTILINE)
                assistant_text = re.sub(r'\s*If not, say.*unknown.*$', '', assistant_text, flags=re.IGNORECASE | re.MULTILINE)
                assistant_text = re.sub(r'\s*Would you like to start by looking.*$', '', assistant_text, flags=re.IGNORECASE | re.MULTILINE)
                assistant_text = assistant_text.strip()
                
                # If using heuristic mode, add a message about the cards being shown
                if assistant_engine == "heuristic_only":
                    assistant_text = assistant_text.rstrip('.')
                    if assistant_text:
                        assistant_text = f"{assistant_text}. Based on your profile, I've prepared three loan paths for you. You'll see them as cards below — tap one to select."
                    else:
                        assistant_text = "Based on your profile, I've prepared three loan paths for you. You'll see them as cards below — tap one to select."

        selection_key = ""
        if isinstance(req.content, str):
            c = req.content.lower()
            if "aggressive" in c:
                selection_key = "aggressive"
            elif "balanced" in c:
                selection_key = "balanced"
            elif "conservative" in c:
                selection_key = "conservative"
        if not selection_key and isinstance(intent_dict.get("selectedPlan"), str):
            selection_key = str(intent_dict.get("selectedPlan") or "").strip().lower()
        if selection_key and loan_recommendation_cards:
            selected_recommendation = next((r for r in loan_recommendation_cards if r.get("type") == selection_key), None)

        if selected_recommendation:
            loan_recommendation_cards = None
            if purpose == "home" and (pv is None or dp is None):
                loan_snapshot = None
            else:
                loan_amt = float(la) if la is not None else 0.0
                prop_val = float(pv) if pv is not None else float(loan_amt)
                down = float(dp) if dp is not None else 0.0
                ltv_pct = ((loan_amt / prop_val) * 100.0) if prop_val > 0 else 100.0
                loan_snapshot = {
                    "loan_amount": loan_amt,
                    "down_payment": down,
                    "property_value": prop_val,
                    "estimated_emi": float(selected_recommendation["monthly_emi"]),
                    "tenure_years": float(selected_recommendation["tenure_years"]),
                    "interest_rate": float(selected_recommendation["interest_rate"]),
                    "total_interest": float(selected_recommendation["total_interest"]),
                    "total_repayment": float(selected_recommendation["total_repayment"]),
                    "ltv_ratio": float(round(ltv_pct, 1)),
                    "currency": "USD",
                }
    except Exception:
        loan_recommendation_cards = None
        selected_recommendation = None
        loan_snapshot = None
    final_recommendation = None
    if conv.chat_role == "borrower" and not actor_is_officer:
        if isinstance(final_recommendation_override, dict):
            final_recommendation = final_recommendation_override
        elif isinstance(selected_recommendation, dict):
            final_recommendation = selected_recommendation
        else:
            intent_obj = analysis.get("intentSummary") if isinstance(analysis, dict) else {}
            intent_dict = intent_obj if isinstance(intent_obj, dict) else {}
            has_amount = _parse_amount_to_number(intent_dict.get("loanAmount")) is not None
            has_income = _parse_amount_to_number(intent_dict.get("monthlyIncome")) is not None
            has_tenure = isinstance(intent_dict.get("preferredTenure"), str) and bool(str(intent_dict.get("preferredTenure") or "").strip())
            purpose = str(intent_dict.get("purpose") or "").strip().lower()
            home_ok = True
            if purpose == "home":
                home_ok = _parse_amount_to_number(intent_dict.get("propertyValue")) is not None and _parse_amount_to_number(intent_dict.get("downPayment")) is not None
            recs = conv.recommended_products if isinstance(conv.recommended_products, list) else []
            if purpose and has_amount and has_income and has_tenure and home_ok and recs:
                first = recs[0]
                if isinstance(first, dict):
                    final_recommendation = first
    assistant_metadata = {
        "actorRole": "officer_assistant" if actor_is_officer else None,
        "assistantEngine": assistant_engine,
        "intentAnalysis": analysis,
        "loanRecommendations": loan_recommendation_cards if loan_recommendation_cards else None,
        "selectedRecommendation": selected_recommendation,
        "loanSnapshot": loan_snapshot,
        "approvalProbability": approval_probability,
        "phaseAction": phase_action,
        "loanAction": loan_action,
        "conversationPatch": conversation_patch,
        "actionResults": action_results,
        "finalRecommendation": final_recommendation,
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


def _default_required_documents(loan_type: str) -> list[str]:
    lt = (loan_type or "").strip().lower()
    docs = [
        "National ID or Passport",
        "Proof of Address",
        "Last 3 Payslips",
        "Last 6 Months Bank Statements",
    ]
    if any(k in lt for k in ["home", "property", "mortgage"]):
        docs += [
            "Agreement / Contract of Sale",
            "Property Valuation Report",
            "Title Search / Deed",
        ]
    if any(k in lt for k in ["auto", "car", "vehicle"]):
        docs += [
            "Dealer Quotation / Pro-forma Invoice",
            "Vehicle Registration (if used)",
        ]
    return docs


def _require_borrower_conversation(
    *,
    db: Session,
    conversation_id: Optional[str],
    x_api_key: Optional[str],
    authorization: Optional[str],
) -> Conversation:
    if not conversation_id:
        raise HTTPException(status_code=400, detail="X-Conversation-ID header required")
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if is_officer_request(x_api_key, authorization):
        return conv
    if conv.id != conversation_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return conv


def _require_borrower_loan_access(
    *,
    db: Session,
    loan_id: str,
    conversation_id: Optional[str],
    x_api_key: Optional[str],
    authorization: Optional[str],
) -> Loan:
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    if is_officer_request(x_api_key, authorization):
        return loan
    if not conversation_id or not loan.conversation_id or loan.conversation_id != conversation_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return loan


@borrower_router.get("/applications")
def list_borrower_applications(
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/borrower/applications").inc()
    conv = _require_borrower_conversation(db=db, conversation_id=x_conversation_id, x_api_key=x_api_key, authorization=authorization)
    rows = (
        db.execute(select(Loan).where(Loan.conversation_id == conv.id).order_by(Loan.updated_at.desc(), Loan.created_at.desc(), Loan.id.desc()))
        .scalars()
        .all()
    )
    from src.api.routers import v2_loans_router as loans_api

    return [loans_api._serialize_loan(l) for l in rows]


@borrower_router.get("/applications/{loan_id}")
def get_borrower_application(
    loan_id: str,
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/borrower/applications/{loan_id}").inc()
    loan = _require_borrower_loan_access(
        db=db, loan_id=loan_id, conversation_id=x_conversation_id, x_api_key=x_api_key, authorization=authorization
    )
    from src.api.routers import v2_loans_router as loans_api

    return loans_api._serialize_loan(loan)


@borrower_router.post("/applications", response_model=CreateBorrowerApplicationResponse)
def create_borrower_application(
    req: CreateBorrowerApplicationRequest,
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/borrower/applications").inc()

    conv_id = x_conversation_id
    conv = db.get(Conversation, conv_id) if conv_id else None
    if not conv:
        conv = Conversation(id=str(uuid.uuid4()), borrower_name=req.borrowerName, status="active", chat_role="borrower")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id

    if not is_officer_request(x_api_key, authorization) and x_conversation_id and conv.id != x_conversation_id:
        request_errors_total.labels(endpoint="/api/borrower/applications").inc()
        raise HTTPException(status_code=403, detail="Not authorized")

    from src.api.routers import v2_loans_router as loans_api

    product = loans_api._get_product_by_code(db, req.catalogProductCode) if req.catalogProductCode else None
    required_docs = product.required_documents if product and isinstance(product.required_documents, list) else _default_required_documents(req.loanType)
    checklist = loans_api._build_document_checklist(req.catalogProductCode, required_docs)

    loan = Loan(
        borrower_name=req.borrowerName,
        borrower_email=req.borrowerEmail,
        borrower_phone=req.borrowerPhone,
        loan_type=req.loanType,
        loan_amount=req.loanAmount,
        catalog_product_code=req.catalogProductCode,
        document_checklist=checklist,
        conversation_id=conv_id,
        status="draft",
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    log_audit(
        event="borrower_application_created",
        endpoint="/api/borrower/applications",
        status="success",
        meta={"conversationId": conv_id, "loanId": loan.id},
    )
    return {"conversationId": conv_id, "loan": loans_api._serialize_loan(loan)}
