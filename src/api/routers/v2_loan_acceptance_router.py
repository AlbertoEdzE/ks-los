import re
import base64
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.routers.v2_auth import is_officer_request, require_viewer_role
from src.shared.audit import log_audit
from src.shared.db import Loan, LoanDocument, LoanPhase, Message, get_db
from src.shared.metrics import request_counter, request_errors_total

router = APIRouter(prefix="/api/loans", tags=["v2-acceptance"], dependencies=[Depends(require_viewer_role)])


class AcceptTermsRequest(BaseModel):
    signature: str = Field(..., description="data URL, e.g. data:image/png;base64,...")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat()


def _require_loan_access(
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
    if not conversation_id or not loan.conversation_id or conversation_id != loan.conversation_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return loan


def _decode_signature_data_url(data_url: str) -> tuple[bytes, str]:
    raw = (data_url or "").strip()
    if not raw.startswith("data:") or ";base64," not in raw:
        raise HTTPException(status_code=400, detail="Invalid signature format")
    head, b64 = raw.split(";base64,", 1)
    mime = head.replace("data:", "").strip().lower()
    if mime not in {"image/png", "image/jpeg"}:
        raise HTTPException(status_code=400, detail="Unsupported signature image type")
    try:
        decoded = base64.b64decode(b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 signature")
    if not decoded:
        raise HTTPException(status_code=400, detail="Empty signature")
    if len(decoded) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Signature payload too large")
    return decoded, mime


def _parse_amount(value: Optional[str]) -> float:
    raw = (value or "").strip()
    if not raw:
        return 0.0
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", raw.replace(",", ""))
    if not m:
        return 0.0
    try:
        return float(m.group(1))
    except Exception:
        return 0.0


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _score_grade(score: int) -> tuple[str, str, str]:
    if score >= 780:
        return "A", "Excellent", "low"
    if score >= 720:
        return "B", "Good", "medium_low"
    if score >= 660:
        return "C", "Fair", "medium"
    if score >= 600:
        return "D", "Weak", "high"
    return "E", "Poor", "very_high"


def _compute_bureau_report(loan: Loan) -> dict[str, Any]:
    income = _parse_amount(loan.monthly_income)
    debts = _parse_amount(loan.existing_debts)
    baseline = 700.0
    delta_income = _clamp((income / 1000.0) * 5.0, 0.0, 60.0)
    delta_debts = _clamp((debts / 1000.0) * 8.0, 0.0, 120.0)
    score_raw = baseline + delta_income - delta_debts
    seeded_credit = _parse_amount(loan.credit_score)
    if seeded_credit > 0:
        score_raw = seeded_credit
    score = int(round(_clamp(score_raw, 300.0, 850.0)))
    grade, grade_label, risk_level = _score_grade(score)
    ref = f"CRB-{loan.id[:8].upper()}-{uuid.uuid4().hex[:6].upper()}"
    return {
        "bureauName": "Caribbean Credit Bureau",
        "reportReference": ref,
        "score": score,
        "grade": grade,
        "gradeLabel": grade_label,
        "riskLevel": risk_level,
        "pulledAt": _now_iso(),
    }


def _compute_terms(loan: Loan, bureau_report: dict[str, Any]) -> dict[str, str]:
    score = int(bureau_report.get("score") or 700)
    principal = max(_parse_amount(loan.loan_amount), 0.0)
    n = int(_parse_amount(loan.tenure) or 60.0)
    n = max(12, min(n, 360))
    base_rate = 0.085
    risk_premium = 0.0
    if score < 600:
        risk_premium = 0.10
    elif score < 660:
        risk_premium = 0.06
    elif score < 720:
        risk_premium = 0.03
    elif score < 780:
        risk_premium = 0.01
    annual_rate = _clamp(base_rate + risk_premium, 0.06, 0.30)
    r = annual_rate / 12.0
    if principal <= 0:
        emi = 0.0
    elif r <= 0:
        emi = principal / float(n)
    else:
        k = (1.0 + r) ** float(n)
        emi = principal * r * k / (k - 1.0)

    currency = "XCD"
    rate_pct = f"{annual_rate * 100.0:.2f}%"
    tenure = f"{n} months"
    emi_text = f"{currency} {emi:,.2f}"
    return {"rate": rate_pct, "tenure": tenure, "emi": emi_text}


def _compute_affordability(loan: Loan, approval: dict[str, str]) -> dict[str, Any]:
    income = _parse_amount(loan.monthly_income)
    debts = _parse_amount(loan.existing_debts)
    emi = _parse_amount(approval.get("emi"))
    total_obligations = debts + emi
    foir = (total_obligations / income) if income > 0 else None
    affordability = {
        "monthlyIncome": loan.monthly_income,
        "existingDebts": loan.existing_debts,
        "proposedEmi": approval.get("emi"),
        "foir": float(foir) if isinstance(foir, float) else None,
        "assessmentAt": _now_iso(),
    }
    before = {"monthlyObligations": debts, "foir": (debts / income) if income > 0 else None}
    after = {"monthlyObligations": total_obligations, "foir": foir}
    liability_comparison = {"before": before, "after": after}
    return {"affordability": affordability, "liabilityComparison": liability_comparison}


def _stp_steps(loan: Loan, bureau_report: dict[str, Any], approval: dict[str, str], affordability: dict[str, Any]) -> list[dict[str, Any]]:
    score = int(bureau_report.get("score") or 0)
    foir = affordability.get("affordability", {}).get("foir")
    try:
        foir_val = float(foir) if foir is not None else None
    except Exception:
        foir_val = None

    checks = [
        ("U", "Identity & KYC verification", True),
        ("R", "Credit bureau score threshold", score >= 660),
        ("S-T", "Affordability (FOIR ≤ 0.50)", (foir_val is not None and foir_val <= 0.50)),
        ("P-Q", "Offer generation", True if approval.get("rate") and approval.get("emi") else False),
    ]
    out: list[dict[str, Any]] = []
    for rule_group, phase, passed_bool in checks:
        out.append({"ruleGroup": rule_group, "phase": phase, "passed": 1 if passed_bool else 0, "total": 1})
    return out


def _stp_audit_log(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in steps:
        out.append(
            {
                "ts": _now_iso(),
                "ruleGroup": s.get("ruleGroup"),
                "phase": s.get("phase"),
                "passed": s.get("passed"),
                "total": s.get("total"),
            }
        )
    return out


def _run_stp(db: Session, loan: Loan) -> dict[str, Any]:
    docs = (
        db.execute(select(LoanDocument).where(LoanDocument.loan_id == loan.id).order_by(LoanDocument.uploaded_at.desc(), LoanDocument.id.desc()))
        .scalars()
        .all()
    )
    has_identity = any((d.category or "").strip().lower() == "identity" for d in docs) or any(
        any(tok in ((d.document_type or "").strip().lower()) for tok in ["id", "passport", "national"]) for d in docs
    )
    has_income = any(((d.category or "").strip().lower()).startswith("income") for d in docs) or any(
        any(tok in ((d.document_type or "").strip().lower()) for tok in ["pay", "salary", "job", "bank_statement", "bank-stat", "statement"]) for d in docs
    )
    if not (has_identity and has_income and len(docs) >= 2):
        loan.stp_processing_status = "awaiting_documents"
        db.add(loan)
        db.commit()
        db.refresh(loan)
        return {"status": loan.stp_processing_status, "log": loan.stp_processing_log or []}

    bureau = _compute_bureau_report(loan)
    approval = _compute_terms(loan, bureau)
    aff = _compute_affordability(loan, approval)
    steps = _stp_steps(loan, bureau, approval, aff)
    audit = _stp_audit_log(steps)

    loan.interest_rate = approval.get("rate")
    loan.tenure = approval.get("tenure")
    loan.monthly_emi = approval.get("emi")
    loan.stp_processing_status = "awaiting_acceptance"
    loan.stp_processing_log = audit
    loan.stp_payload = {
        "stpApproved": True,
        "loanId": loan.id,
        "bureauReport": bureau,
        "stpSteps": steps,
        "audit": audit,
        "affordability": aff.get("affordability"),
        "liabilityComparison": aff.get("liabilityComparison"),
        "awaitingAcceptance": True,
        "approval": {**approval, "conditions": ["Subject to final document verification", "No material adverse changes before disbursement"]},
        "stpCompleted": False,
        "disbursement": None,
    }
    if (loan.status or "").lower() in {"draft", "submitted", "in-progress"}:
        loan.status = "approved"

    db.add(loan)
    db.commit()
    db.refresh(loan)
    return {"status": loan.stp_processing_status, "log": loan.stp_processing_log or []}


@router.post("/{loan_id}/stp-process")
def stp_process(
    loan_id: str,
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/loans/{id}/stp-process").inc()
    loan = _require_loan_access(
        db=db,
        loan_id=loan_id,
        conversation_id=x_conversation_id,
        x_api_key=x_api_key,
        authorization=authorization,
    )
    status_now = (loan.stp_processing_status or "").lower()
    if status_now in {"awaiting_acceptance", "completed", "processing"}:
        return {
            "status": loan.stp_processing_status,
            "log": loan.stp_processing_log or [],
            "disbursement": loan.disbursement,
            "payload": loan.stp_payload,
        }

    loan.stp_processing_status = "processing"
    loan.stp_processing_log = [{"ts": _now_iso(), "phase": "STP started", "passed": 0, "total": 0}]
    db.add(loan)
    db.commit()
    db.refresh(loan)

    result = _run_stp(db, loan)
    if (
        loan.conversation_id
        and (loan.stp_processing_status or "").lower() == "awaiting_acceptance"
        and isinstance(loan.stp_payload, dict)
    ):
        approval = loan.stp_payload.get("approval") if isinstance(loan.stp_payload.get("approval"), dict) else {}
        msg = Message(
            conversation_id=loan.conversation_id,
            role="assistant",
            content=(
                "Automated checks are complete. Your indicative offer is ready.\n\n"
                f"• **Interest Rate**: {approval.get('rate') or 'N/A'}\n"
                f"• **Tenure**: {approval.get('tenure') or 'N/A'}\n"
                f"• **Monthly EMI**: {approval.get('emi') or 'N/A'}\n\n"
                "If you agree, please accept the terms to authorize disbursement."
            ),
            metadata_json={
                "type": "stp_offer",
                "loanId": loan.id,
                "loanApplication": loan.stp_payload,
            },
        )
        db.add(msg)
        db.commit()
    log_audit(event="v2_stp_process", endpoint="/api/loans/{id}/stp-process", status="success", meta={"loanId": loan.id, "status": result.get("status")})
    return result


@router.get("/{loan_id}/stp-status")
def stp_status(
    loan_id: str,
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/loans/{id}/stp-status").inc()
    loan = _require_loan_access(
        db=db,
        loan_id=loan_id,
        conversation_id=x_conversation_id,
        x_api_key=x_api_key,
        authorization=authorization,
    )
    approval = (
        {"rate": loan.interest_rate, "tenure": loan.tenure, "emi": loan.monthly_emi}
        if loan.interest_rate or loan.tenure or loan.monthly_emi
        else None
    )
    return {
        "status": loan.stp_processing_status,
        "log": loan.stp_processing_log or [],
        "disbursement": loan.disbursement,
        "approval": approval,
        "payload": loan.stp_payload,
    }


@router.post("/{loan_id}/accept-terms")
def accept_terms(
    loan_id: str,
    payload: AcceptTermsRequest,
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/loans/{id}/accept-terms").inc()

    loan = _require_loan_access(
        db=db,
        loan_id=loan_id,
        conversation_id=x_conversation_id,
        x_api_key=x_api_key,
        authorization=authorization,
    )

    stp_status = (loan.stp_processing_status or "").strip().lower()
    if stp_status and stp_status != "awaiting_acceptance":
        request_errors_total.labels(endpoint="/api/loans/{id}/accept-terms").inc()
        raise HTTPException(status_code=400, detail="Loan is not awaiting acceptance")
    if not stp_status:
        bureau = _compute_bureau_report(loan)
        approval_calc = _compute_terms(loan, bureau)
        loan.interest_rate = approval_calc.get("rate")
        loan.tenure = approval_calc.get("tenure")
        loan.monthly_emi = approval_calc.get("emi")
        loan.stp_processing_status = "awaiting_acceptance"
        loan.stp_payload = {
            "stpApproved": True,
            "loanId": loan.id,
            "bureauReport": bureau,
            "awaitingAcceptance": True,
            "approval": {**approval_calc, "conditions": ["Subject to final document verification"]},
            "stpCompleted": False,
            "disbursement": None,
        }

    signature_bytes, signature_mime = _decode_signature_data_url(payload.signature)

    uploads_root = os.getenv("KS_LOS_UPLOAD_DIR", "data/uploads")
    sig_id = str(uuid.uuid4())
    ext = ".png" if signature_mime == "image/png" else ".jpg"
    loan_dir = os.path.join(uploads_root, "loans", loan.id, "terms-signatures")
    os.makedirs(loan_dir, exist_ok=True)
    sig_name = f"{sig_id}{ext}"
    sig_path = os.path.join(loan_dir, sig_name)
    with open(sig_path, "wb") as f:
        f.write(signature_bytes)

    disbursement_ref = f"DISB-{loan.id[:8].upper()}-{sig_id[:6].upper()}"
    disbursement = {
        "reference": disbursement_ref,
        "status": "disbursed",
        "amount": loan.loan_amount,
        "currency": "XCD",
        "method": "bank_transfer",
        "disbursedAt": _now_iso(),
    }

    approval = {
        "rate": loan.interest_rate,
        "tenure": loan.tenure,
        "emi": loan.monthly_emi,
    }

    loan.terms_accepted_at = _now_utc()
    loan.terms_signature_path = sig_path
    loan.terms_signature_mime = signature_mime
    loan.disbursement = disbursement
    loan.stp_processing_status = "completed"
    if (loan.status or "").lower() not in {"disbursed"}:
        loan.status = "disbursed"

    phase = (
        db.execute(
            select(LoanPhase)
            .where(LoanPhase.is_active.is_(True))
            .where(LoanPhase.name.ilike("%disburse%"))
            .order_by(LoanPhase.sort_order.asc(), LoanPhase.id.asc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if phase:
        loan.current_phase_id = phase.id

    db.add(loan)
    db.commit()
    db.refresh(loan)

    if loan.conversation_id:
        loan_application = {
            "success": True,
            "loanId": loan.id,
            "stpCompleted": True,
            "disbursement": disbursement,
            "approval": approval,
        }
        msg = Message(
            conversation_id=loan.conversation_id,
            role="assistant",
            content=(
                "Your loan terms have been accepted and funds have been credited to your account!\n\n"
                f"• **Amount**: {disbursement['amount']} ({disbursement['currency']})\n"
                f"• **Interest Rate**: {approval.get('rate') or 'N/A'}\n"
                f"• **Tenure**: {approval.get('tenure') or 'N/A'}\n"
                f"• **Monthly EMI**: {approval.get('emi') or 'N/A'}\n"
                f"• **Transaction Reference**: {disbursement_ref}\n\n"
                "You'll receive confirmations shortly."
            ),
            metadata_json={
                "loanApplication": loan_application,
                "type": "disbursement_confirmation",
                "disbursement": disbursement,
                "loanId": loan.id,
            },
        )
        db.add(msg)
        db.commit()

    log_audit(
        event="v2_accept_terms",
        endpoint="/api/loans/{id}/accept-terms",
        status="success",
        meta={"loanId": loan.id, "disbursementRef": disbursement_ref},
    )

    return {"success": True, "disbursement": disbursement, "approval": approval}
