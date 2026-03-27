import re
from typing import Any, Optional, Literal, Annotated, Union
from datetime import datetime, timezone
import os
import uuid
import hashlib
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field, TypeAdapter, ValidationError, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.shared.auth import require_officer_role
from src.shared.audit import log_audit
from src.shared.db import Loan, LoanProductCatalog, get_db
from src.shared.metrics import (
    request_counter,
    request_errors_total,
    v2_loan_document_updates_total,
    v2_loans_created_total,
    v2_loans_updated_total,
    v2_underwriting_memo_total,
)


router = APIRouter(prefix="/api/loans", tags=["v2_loans"], dependencies=[Depends(require_officer_role)])

_DOC_STATUSES = {"missing", "submitted", "verified", "rejected"}

_MEMO_PROHIBITED_PATTERNS = [
    r"\bguarantee(?:d|s)?\b",
    r"\b(fully\s+)?approved\b",
    r"\bwill\s+be\s+approved\b",
    r"\b100%\b",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        key = v.strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _build_document_checklist(product_code: Optional[str], required_documents: Optional[list]) -> Optional[dict[str, Any]]:
    docs = _unique_ordered([str(d) for d in (required_documents or [])])
    if not docs and not product_code:
        return None
    now = _now_iso()
    return {
        "productCode": product_code,
        "items": [{"name": d, "status": "missing", "updatedAt": now} for d in docs],
        "asOf": now,
    }


def _merge_checklist(existing: Optional[dict[str, Any]], product_code: Optional[str], required_documents: Optional[list]) -> Optional[dict[str, Any]]:
    next_checklist = _build_document_checklist(product_code, required_documents)
    if existing is None or next_checklist is None:
        return next_checklist

    existing_items = existing.get("items") if isinstance(existing, dict) else None
    by_name: dict[str, dict[str, Any]] = {}
    if isinstance(existing_items, list):
        for item in existing_items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                by_name[name.strip()] = item

    merged_items: list[dict[str, Any]] = []
    for item in next_checklist["items"]:
        prev = by_name.get(item["name"])
        if isinstance(prev, dict) and prev.get("status") in _DOC_STATUSES:
            merged_items.append({**item, "status": prev["status"], "updatedAt": prev.get("updatedAt") or item["updatedAt"]})
        else:
            merged_items.append(item)

    return {**next_checklist, "items": merged_items}


def _safe_filename(name: str) -> str:
    base = (name or "").strip().replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", base)
    return base[:160] or "document"


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _extract_text_from_upload(raw: bytes, content_type: Optional[str], filename: Optional[str]) -> str:
    ct = (content_type or "").lower()
    name = (filename or "").lower()
    is_pdf = "pdf" in ct or name.endswith(".pdf")
    is_image = ct.startswith("image/") or bool(re.search(r"\.(png|jpe?g|bmp|gif|tiff?|webp)$", name))

    if is_pdf:
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(io.BytesIO(raw))
            parts: list[str] = []
            for page in reader.pages:
                t = page.extract_text() or ""
                if t.strip():
                    parts.append(t)
            return "\n".join(parts).strip()
        except Exception:
            return ""

    if is_image:
        try:
            from PIL import Image  # type: ignore
            import pytesseract  # type: ignore

            img = Image.open(io.BytesIO(raw))
            return (pytesseract.image_to_string(img) or "").strip()
        except Exception:
            return ""

    return ""


def _get_product_by_code(db: Session, code: str) -> Optional[LoanProductCatalog]:
    from src.api.routers.v2_catalog_products_router import _ensure_seeded as _ensure_products_seeded

    _ensure_products_seeded(db)
    return db.execute(select(LoanProductCatalog).where(LoanProductCatalog.code == code)).scalar_one_or_none()

def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", raw)
    if cleaned in {"", "-", ".", "-."}:
        return None
    try:
        return float(cleaned)
    except Exception:
        return None


def _format_money(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    try:
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        return f"{value:.2f}"
    except Exception:
        return str(value)


def _guardrail_validate_text(text: str) -> None:
    for pat in _MEMO_PROHIBITED_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            raise ValueError("Memo guardrail violation")


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    value: Optional[str] = None
    source: str


class MemoSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    bullets: list[str]
    evidence: list[EvidenceItem] = Field(default_factory=list)


class UnderwritingMemo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    loanId: str
    productCode: Optional[str] = None
    generatedAt: str
    method: str
    disclaimer: str
    flags: list[str]
    nextActions: list[str]
    sections: list[MemoSection]


def _generate_underwriting_memo(loan: Loan, product: Optional[LoanProductCatalog]) -> UnderwritingMemo:
    now = _now_iso()

    loan_amount = _parse_float(loan.loan_amount)
    monthly_income = _parse_float(loan.monthly_income)
    existing_debts = _parse_float(loan.existing_debts)
    credit_score = _parse_float(loan.credit_score)
    property_value = _parse_float(loan.property_value)
    stated_ltv = _parse_float(loan.ltv)

    computed_ltv: Optional[float] = None
    if stated_ltv is not None:
        computed_ltv = stated_ltv
    elif loan_amount is not None and property_value is not None and property_value > 0:
        computed_ltv = (loan_amount / property_value) * 100.0

    dti: Optional[float] = None
    if monthly_income is not None and monthly_income > 0 and existing_debts is not None:
        dti = (existing_debts / monthly_income) * 100.0

    required_docs = []
    missing_names: list[str] = []
    missing_docs = 0
    submitted_docs = 0
    verified_docs = 0
    rejected_docs = 0
    if isinstance(loan.document_checklist, dict) and isinstance(loan.document_checklist.get("items"), list):
        for item in loan.document_checklist["items"]:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            status = item.get("status")
            if isinstance(name, str) and name.strip():
                required_docs.append(name.strip())
            if status == "missing":
                missing_docs += 1
                if isinstance(name, str) and name.strip():
                    missing_names.append(name.strip())
            elif status == "submitted":
                submitted_docs += 1
            elif status == "verified":
                verified_docs += 1
            elif status == "rejected":
                rejected_docs += 1

    flags: list[str] = []
    next_actions: list[str] = []

    if credit_score is None:
        flags.append("Credit score not provided")
        next_actions.append("Collect credit score / bureau range")
    elif product and product.min_credit_score is not None and credit_score < float(product.min_credit_score):
        flags.append(f"Credit score below product minimum ({product.min_credit_score})")
        next_actions.append("Review alternative products or add mitigations (co-applicant / collateral)")

    if monthly_income is None:
        flags.append("Monthly income not provided")
        next_actions.append("Collect salary slips / income proof and confirm net monthly income")

    if computed_ltv is None:
        flags.append("LTV not computable (missing property value / LTV)")
        next_actions.append("Collect property value and compute LTV")
    elif product:
        max_ltv = _parse_float(product.max_ltv)
        if max_ltv is not None and computed_ltv > max_ltv:
            flags.append(f"LTV above product maximum ({max_ltv:.0f}%)")
            next_actions.append("Increase down payment or consider lower LTV product")

    if missing_docs > 0:
        flags.append(f"{missing_docs} required documents missing")
        next_actions.append("Request missing documents and update checklist")
    if rejected_docs > 0:
        flags.append(f"{rejected_docs} documents rejected")
        next_actions.append("Resolve rejected documents (re-upload / correction / verification)")

    snapshot_section = MemoSection(
        title="Borrower & Loan Snapshot",
        bullets=[
            f"Borrower: {loan.borrower_name or '—'}",
            f"Loan type: {loan.loan_type or '—'}",
            f"Requested amount: {_format_money(loan_amount) or loan.loan_amount or '—'}",
            f"Catalog product: {loan.catalog_product_code or '—'}",
        ],
        evidence=[
            EvidenceItem(field="borrowerName", value=loan.borrower_name, source="loans.borrower_name"),
            EvidenceItem(field="loanType", value=loan.loan_type, source="loans.loan_type"),
            EvidenceItem(field="loanAmount", value=loan.loan_amount, source="loans.loan_amount"),
            EvidenceItem(field="catalogProductCode", value=loan.catalog_product_code, source="loans.catalog_product_code"),
        ],
    )

    affordability_bullets: list[str] = [
        f"Monthly income: {_format_money(monthly_income) or loan.monthly_income or '—'}",
        f"Existing monthly debts: {_format_money(existing_debts) or loan.existing_debts or '—'}",
    ]
    if dti is not None:
        affordability_bullets.append(f"Debt-to-income (DTI): {dti:.1f}%")
    if credit_score is not None:
        affordability_bullets.append(f"Credit score (stated): {credit_score:.0f}")

    affordability_section = MemoSection(
        title="Affordability & Credit Signals",
        bullets=affordability_bullets,
        evidence=[
            EvidenceItem(field="monthlyIncome", value=loan.monthly_income, source="loans.monthly_income"),
            EvidenceItem(field="existingDebts", value=loan.existing_debts, source="loans.existing_debts"),
            EvidenceItem(field="creditScore", value=loan.credit_score, source="loans.credit_score"),
        ],
    )

    collateral_bullets: list[str] = [
        f"Property value: {_format_money(property_value) or loan.property_value or '—'}",
        f"Down payment: {loan.down_payment or '—'}",
        f"Loan-to-value (LTV): {f'{computed_ltv:.1f}%' if computed_ltv is not None else (loan.ltv or '—')}",
    ]
    collateral_section = MemoSection(
        title="Collateral & LTV",
        bullets=collateral_bullets,
        evidence=[
            EvidenceItem(field="propertyValue", value=loan.property_value, source="loans.property_value"),
            EvidenceItem(field="downPayment", value=loan.down_payment, source="loans.down_payment"),
            EvidenceItem(field="ltv", value=loan.ltv, source="loans.ltv"),
        ],
    )

    docs_section = MemoSection(
        title="Documents & Checklist Status",
        bullets=[
            f"Required documents: {len(required_docs)}",
            f"Missing: {missing_docs} · Submitted: {submitted_docs} · Verified: {verified_docs} · Rejected: {rejected_docs}",
        ]
        + ([f"Missing items: {', '.join(missing_names[:6])}"] if missing_names else []),
        evidence=[
            EvidenceItem(field="documentChecklist", value=str(loan.document_checklist.get("asOf")) if isinstance(loan.document_checklist, dict) else None, source="loans.document_checklist"),
        ],
    )

    risks_section = MemoSection(
        title="Risks & Mitigations (Preliminary)",
        bullets=(flags if flags else ["No material flags detected from currently available fields."]),
        evidence=[],
    )

    recommendation_text = (
        "This memo is a preliminary, rules-based underwriting summary to support officer workflow. "
        "It is not a credit decision and does not imply approval."
    )
    recommendation_section = MemoSection(
        title="Recommendation & Next Steps",
        bullets=[
            "Recommendation: proceed to underwriting review after resolving the highest-impact gaps.",
            *(_unique_ordered(next_actions) if next_actions else ["Confirm remaining borrower profile fields and document status."]),
        ],
        evidence=[],
    )

    memo = UnderwritingMemo(
        loanId=loan.id,
        productCode=loan.catalog_product_code,
        generatedAt=now,
        method="rules_v1",
        disclaimer=recommendation_text,
        flags=_unique_ordered(flags),
        nextActions=_unique_ordered(next_actions),
        sections=[
            MemoSection(
                title="Executive Summary",
                bullets=[
                    f"Generated at: {now}",
                    f"Scope: uses available loan fields and document checklist as evidence signals.",
                ],
                evidence=[],
            ),
            snapshot_section,
            affordability_section,
            collateral_section,
            docs_section,
            risks_section,
            recommendation_section,
        ],
    )

    full_text = memo.model_dump_json()
    _guardrail_validate_text(full_text)
    return memo


class CreateLoanRequest(BaseModel):
    borrowerName: str
    loanType: str
    loanAmount: str
    catalogProductCode: Optional[str] = None
    conversationId: Optional[str] = None
    createdBy: Optional[str] = None



class PatchLoanRequest(BaseModel):
    borrowerName: Optional[str] = None
    borrowerEmail: Optional[str] = None
    borrowerPhone: Optional[str] = None
    loanType: Optional[str] = None
    loanAmount: Optional[str] = None
    interestRate: Optional[str] = None
    tenure: Optional[str] = None
    monthlyEmi: Optional[str] = None
    purpose: Optional[str] = None
    employmentType: Optional[str] = None
    monthlyIncome: Optional[str] = None
    existingDebts: Optional[str] = None
    creditScore: Optional[str] = None
    collateral: Optional[str] = None
    downPayment: Optional[str] = None
    propertyValue: Optional[str] = None
    ltv: Optional[str] = None
    catalogProductCode: Optional[str] = None
    currentPhaseId: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    conversationId: Optional[str] = None
    createdBy: Optional[str] = None

class PatchLoanDocumentRequest(BaseModel):
    name: str
    status: str


class LoanActionsRequest(BaseModel):
    actions: list[dict[str, Any]]


class CreateLoanAction(BaseModel):
    type: Literal["create_loan"]
    borrowerName: str
    loanType: str
    loanAmount: str
    catalogProductCode: Optional[str] = None
    conversationId: Optional[str] = None
    createdBy: Optional[str] = None


class UpdateLoanAction(BaseModel):
    type: Literal["update_loan"]
    loanId: str
    patch: PatchLoanRequest


LoanAction = Annotated[Union[CreateLoanAction, UpdateLoanAction], Field(discriminator="type")]


def _validate_loan_actions(raw: list[dict[str, Any]]) -> list[LoanAction]:
    adapter = TypeAdapter(list[LoanAction])
    try:
        return adapter.validate_python(raw)
    except ValidationError as e:
        raise ValueError(e.errors())


def _apply_patch(loan: Loan, req: PatchLoanRequest, db: Session) -> Loan:
    fields = req.model_fields_set

    if "borrowerName" in fields:
        loan.borrower_name = req.borrowerName
    if "borrowerEmail" in fields:
        loan.borrower_email = req.borrowerEmail
    if "borrowerPhone" in fields:
        loan.borrower_phone = req.borrowerPhone
    if "loanType" in fields:
        loan.loan_type = req.loanType
    if "loanAmount" in fields:
        loan.loan_amount = req.loanAmount
    if "interestRate" in fields:
        loan.interest_rate = req.interestRate
    if "tenure" in fields:
        loan.tenure = req.tenure
    if "monthlyEmi" in fields:
        loan.monthly_emi = req.monthlyEmi
    if "purpose" in fields:
        loan.purpose = req.purpose
    if "employmentType" in fields:
        loan.employment_type = req.employmentType
    if "monthlyIncome" in fields:
        loan.monthly_income = req.monthlyIncome
    if "existingDebts" in fields:
        loan.existing_debts = req.existingDebts
    if "creditScore" in fields:
        loan.credit_score = req.creditScore
    if "collateral" in fields:
        loan.collateral = req.collateral
    if "downPayment" in fields:
        loan.down_payment = req.downPayment
    if "propertyValue" in fields:
        loan.property_value = req.propertyValue
    if "ltv" in fields:
        loan.ltv = req.ltv
    if "currentPhaseId" in fields:
        loan.current_phase_id = req.currentPhaseId

    if "catalogProductCode" in fields:
        if req.catalogProductCode:
            product = _get_product_by_code(db, req.catalogProductCode)
            loan.catalog_product_code = req.catalogProductCode
            loan.document_checklist = _merge_checklist(
                loan.document_checklist,
                req.catalogProductCode,
                product.required_documents if product else None,
            )
        else:
            loan.catalog_product_code = None
            loan.document_checklist = None

    if "status" in fields:
        loan.status = req.status
    if "notes" in fields:
        loan.notes = req.notes
    if "conversationId" in fields:
        loan.conversation_id = req.conversationId
    if "createdBy" in fields:
        loan.created_by = req.createdBy

    return loan



def _serialize_loan(l: Loan) -> dict[str, Any]:
    return {
        "id": l.id,
        "borrowerName": l.borrower_name,
        "borrowerEmail": l.borrower_email,
        "borrowerPhone": l.borrower_phone,
        "loanType": l.loan_type,
        "loanAmount": l.loan_amount,
        "interestRate": l.interest_rate,
        "tenure": l.tenure,
        "monthlyEmi": l.monthly_emi,
        "purpose": l.purpose,
        "employmentType": l.employment_type,
        "monthlyIncome": l.monthly_income,
        "existingDebts": l.existing_debts,
        "creditScore": l.credit_score,
        "collateral": l.collateral,
        "downPayment": l.down_payment,
        "propertyValue": l.property_value,
        "ltv": l.ltv,
        "catalogProductCode": l.catalog_product_code,
        "documentChecklist": l.document_checklist,
        "underwritingMemo": l.underwriting_memo,
        "stpProcessingStatus": l.stp_processing_status,
        "stpProcessingLog": l.stp_processing_log,
        "stpPayload": l.stp_payload,
        "termsAcceptedAt": l.terms_accepted_at.isoformat() if l.terms_accepted_at else None,
        "disbursement": l.disbursement,
        "currentPhaseId": l.current_phase_id,
        "status": l.status,
        "notes": l.notes,
        "conversationId": l.conversation_id,
        "createdBy": l.created_by,
        "createdAt": l.created_at.isoformat() if l.created_at else None,
        "updatedAt": l.updated_at.isoformat() if l.updated_at else None,
    }


@router.get("")
def list_loans(db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/loans").inc()
    rows = db.execute(select(Loan).order_by(Loan.updated_at.desc(), Loan.created_at.desc(), Loan.id.asc())).scalars().all()
    return [_serialize_loan(l) for l in rows]

@router.get("/{loan_id}")
def get_loan(loan_id: str, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/loans/{loan_id}").inc()
    loan = db.get(Loan, loan_id)
    if not loan:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}").inc()
        raise HTTPException(status_code=404, detail="Loan not found")
    return _serialize_loan(loan)


@router.post("")
def create_loan(req: CreateLoanRequest, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/loans").inc()
    product = _get_product_by_code(db, req.catalogProductCode) if req.catalogProductCode else None
    checklist = _build_document_checklist(req.catalogProductCode, product.required_documents if product else None)

    loan = Loan(
        borrower_name=req.borrowerName,
        loan_type=req.loanType,
        loan_amount=req.loanAmount,
        catalog_product_code=req.catalogProductCode,
        document_checklist=checklist,
        conversation_id=req.conversationId,
        created_by=req.createdBy,
        status="draft",
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    log_audit(
        event="v2_loan_create",
        endpoint="/api/loans",
        status="success",
        meta={"loanId": loan.id, "catalogProductCode": loan.catalog_product_code},
    )
    v2_loans_created_total.labels(source="endpoint").inc()
    return _serialize_loan(loan)


@router.post("/actions")
def execute_loan_actions(req: LoanActionsRequest, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/loans/actions").inc()
    try:
        actions = _validate_loan_actions(req.actions)
    except ValueError as e:
        request_errors_total.labels(endpoint="/api/loans/actions").inc()
        log_audit(event="v2_loan_actions", endpoint="/api/loans/actions", status="invalid", meta={"error": str(e)})
        raise HTTPException(status_code=400, detail="Invalid actions payload")
    results: list[dict[str, Any]] = []

    for a in actions:
        if isinstance(a, CreateLoanAction):
            product = _get_product_by_code(db, a.catalogProductCode) if a.catalogProductCode else None
            checklist = _build_document_checklist(a.catalogProductCode, product.required_documents if product else None)

            loan = Loan(
                borrower_name=a.borrowerName,
                loan_type=a.loanType,
                loan_amount=a.loanAmount,
                catalog_product_code=a.catalogProductCode,
                document_checklist=checklist,
                conversation_id=a.conversationId,
                created_by=a.createdBy,
                status="draft",
            )
            db.add(loan)
            db.commit()
            db.refresh(loan)
            results.append({"type": a.type, "loanId": loan.id})
            v2_loans_created_total.labels(source="actions").inc()
            continue

        if isinstance(a, UpdateLoanAction):
            loan = db.get(Loan, a.loanId)
            if not loan:
                request_errors_total.labels(endpoint="/api/loans/actions").inc()
                log_audit(event="v2_loan_actions", endpoint="/api/loans/actions", status="not_found", meta={"loanId": a.loanId})
                raise HTTPException(status_code=404, detail="Loan not found")
            changed_fields = set(a.patch.model_fields_set)
            _apply_patch(loan, a.patch, db)
            db.add(loan)
            db.commit()
            db.refresh(loan)
            results.append({"type": a.type, "loanId": loan.id})
            for field in sorted(changed_fields):
                if field == "status":
                    v2_loans_updated_total.labels(field="status").inc()
                elif field == "currentPhaseId":
                    v2_loans_updated_total.labels(field="current_phase_id").inc()
                elif field == "catalogProductCode":
                    v2_loans_updated_total.labels(field="catalog_product_code").inc()
                else:
                    v2_loans_updated_total.labels(field="other").inc()
            continue

        request_errors_total.labels(endpoint="/api/loans/actions").inc()
        log_audit(event="v2_loan_actions", endpoint="/api/loans/actions", status="invalid", meta={"actionType": getattr(a, "type", None)})
        raise HTTPException(status_code=400, detail="Unsupported action")

    log_audit(event="v2_loan_actions", endpoint="/api/loans/actions", status="success", meta={"count": len(results)})
    return {"results": results}




@router.patch("/{loan_id}")
def patch_loan(loan_id: str, req: PatchLoanRequest, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/loans/{loan_id}").inc()
    changed_fields = set(req.model_fields_set)
    loan = db.get(Loan, loan_id)
    if not loan:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}").inc()
        log_audit(event="v2_loan_patch", endpoint="/api/loans/{loan_id}", status="not_found", meta={"loanId": loan_id})
        raise HTTPException(status_code=404, detail="Loan not found")

    _apply_patch(loan, req, db)
    db.add(loan)
    db.commit()
    db.refresh(loan)
    log_audit(event="v2_loan_patch", endpoint="/api/loans/{loan_id}", status="success", meta={"loanId": loan_id})
    for field in sorted(changed_fields):
        if field == "status":
            v2_loans_updated_total.labels(field="status").inc()
        elif field == "currentPhaseId":
            v2_loans_updated_total.labels(field="current_phase_id").inc()
        elif field == "catalogProductCode":
            v2_loans_updated_total.labels(field="catalog_product_code").inc()
        else:
            v2_loans_updated_total.labels(field="other").inc()
    return _serialize_loan(loan)


@router.patch("/{loan_id}/documents")
def patch_loan_document(loan_id: str, req: PatchLoanDocumentRequest, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/loans/{loan_id}/documents").inc()
    if req.status not in _DOC_STATUSES:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents").inc()
        v2_loan_document_updates_total.labels(status="invalid").inc()
        log_audit(
            event="v2_loan_document_patch",
            endpoint="/api/loans/{loan_id}/documents",
            status="invalid",
            meta={"loanId": loan_id, "error": "Invalid document status", "statusValue": req.status},
        )
        raise HTTPException(status_code=400, detail="Invalid document status")

    loan = db.get(Loan, loan_id)
    if not loan:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents").inc()
        v2_loan_document_updates_total.labels(status="not_found").inc()
        log_audit(event="v2_loan_document_patch", endpoint="/api/loans/{loan_id}/documents", status="not_found", meta={"loanId": loan_id})
        raise HTTPException(status_code=404, detail="Loan not found")

    checklist = loan.document_checklist
    if not isinstance(checklist, dict) or not isinstance(checklist.get("items"), list):
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents").inc()
        v2_loan_document_updates_total.labels(status="invalid").inc()
        log_audit(
            event="v2_loan_document_patch",
            endpoint="/api/loans/{loan_id}/documents",
            status="invalid",
            meta={"loanId": loan_id, "error": "Loan has no document checklist"},
        )
        raise HTTPException(status_code=400, detail="Loan has no document checklist")

    target = req.name.strip()
    if not target:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents").inc()
        v2_loan_document_updates_total.labels(status="invalid").inc()
        log_audit(
            event="v2_loan_document_patch",
            endpoint="/api/loans/{loan_id}/documents",
            status="invalid",
            meta={"loanId": loan_id, "error": "Document name is required"},
        )
        raise HTTPException(status_code=400, detail="Document name is required")

    updated = False
    now = _now_iso()
    updated_items: list[dict[str, Any]] = []
    for item in checklist["items"]:
        if not isinstance(item, dict):
            continue
        if item.get("name") == target:
            updated_items.append({**item, "status": req.status, "updatedAt": now})
            updated = True
        else:
            updated_items.append({**item})

    if not updated:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents").inc()
        v2_loan_document_updates_total.labels(status="invalid").inc()
        log_audit(
            event="v2_loan_document_patch",
            endpoint="/api/loans/{loan_id}/documents",
            status="invalid",
            meta={"loanId": loan_id, "error": "Document not found in checklist", "document": target},
        )
        raise HTTPException(status_code=400, detail="Document not found in checklist")

    loan.document_checklist = {**checklist, "items": updated_items, "asOf": now}
    db.add(loan)
    db.commit()
    db.refresh(loan)
    log_audit(
        event="v2_loan_document_patch",
        endpoint="/api/loans/{loan_id}/documents",
        status="success",
        meta={"loanId": loan_id, "document": target, "statusValue": req.status},
    )
    v2_loan_document_updates_total.labels(status=req.status).inc()
    return _serialize_loan(loan)


@router.post("/{loan_id}/documents/upload")
async def upload_loan_document(
    loan_id: str,
    name: Annotated[str, Form()],
    file: UploadFile = File(...),
    extractedText: Annotated[Optional[str], Form()] = None,
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/loans/{loan_id}/documents/upload").inc()
    loan = db.get(Loan, loan_id)
    if not loan:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents/upload").inc()
        log_audit(event="v2_loan_document_upload", endpoint="/api/loans/{loan_id}/documents/upload", status="not_found", meta={"loanId": loan_id})
        raise HTTPException(status_code=404, detail="Loan not found")

    checklist = loan.document_checklist
    if not isinstance(checklist, dict) or not isinstance(checklist.get("items"), list):
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents/upload").inc()
        log_audit(
            event="v2_loan_document_upload",
            endpoint="/api/loans/{loan_id}/documents/upload",
            status="invalid",
            meta={"loanId": loan_id, "error": "Loan has no document checklist"},
        )
        raise HTTPException(status_code=400, detail="Loan has no document checklist")

    target = (name or "").strip()
    if not target:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents/upload").inc()
        log_audit(
            event="v2_loan_document_upload",
            endpoint="/api/loans/{loan_id}/documents/upload",
            status="invalid",
            meta={"loanId": loan_id, "error": "Document name is required"},
        )
        raise HTTPException(status_code=400, detail="Document name is required")

    raw = await file.read()
    if not raw:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents/upload").inc()
        log_audit(
            event="v2_loan_document_upload",
            endpoint="/api/loans/{loan_id}/documents/upload",
            status="invalid",
            meta={"loanId": loan_id, "error": "Empty upload"},
        )
        raise HTTPException(status_code=400, detail="Empty upload")

    uploads_root = os.getenv("KS_LOS_UPLOAD_DIR", "data/uploads")
    doc_id = str(uuid.uuid4())
    safe = _safe_filename(file.filename or "document")
    loan_dir = os.path.join(uploads_root, "loans", loan_id)
    os.makedirs(loan_dir, exist_ok=True)
    stored_name = f"{doc_id}-{safe}"
    stored_path = os.path.join(loan_dir, stored_name)
    with open(stored_path, "wb") as f:
        f.write(raw)

    now = _now_iso()
    extracted = (extractedText or "").strip()
    if not extracted:
        extracted = _extract_text_from_upload(raw, file.content_type, file.filename)
    preview = extracted[:800] if extracted else ""
    upload_meta = {
        "id": doc_id,
        "fileName": file.filename,
        "storedName": stored_name,
        "contentType": file.content_type,
        "sizeBytes": len(raw),
        "sha256": _sha256_bytes(raw),
        "uploadedAt": now,
        "extractedPreview": preview,
    }

    updated = False
    updated_items: list[dict[str, Any]] = []
    for item in checklist["items"]:
        if not isinstance(item, dict):
            continue
        if item.get("name") == target:
            updated_items.append({**item, "status": "submitted", "updatedAt": now, "upload": upload_meta})
            updated = True
        else:
            updated_items.append({**item})

    if not updated:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents/upload").inc()
        log_audit(
            event="v2_loan_document_upload",
            endpoint="/api/loans/{loan_id}/documents/upload",
            status="invalid",
            meta={"loanId": loan_id, "error": "Document not found in checklist", "document": target},
        )
        raise HTTPException(status_code=400, detail="Document not found in checklist")

    loan.document_checklist = {**checklist, "items": updated_items, "asOf": now}
    db.add(loan)
    db.commit()
    db.refresh(loan)
    log_audit(
        event="v2_loan_document_upload",
        endpoint="/api/loans/{loan_id}/documents/upload",
        status="success",
        meta={"loanId": loan_id, "document": target, "docId": doc_id},
    )
    v2_loan_document_updates_total.labels(status="submitted").inc()
    return _serialize_loan(loan)


@router.post("/{loan_id}/signature")
async def upload_loan_signature(
    loan_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/loans/{loan_id}/signature").inc()
    loan = db.get(Loan, loan_id)
    if not loan:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/signature").inc()
        log_audit(event="v2_loan_signature_upload", endpoint="/api/loans/{loan_id}/signature", status="not_found", meta={"loanId": loan_id})
        raise HTTPException(status_code=404, detail="Loan not found")

    checklist = loan.document_checklist
    if not isinstance(checklist, dict) or not isinstance(checklist.get("items"), list):
        checklist = {"productCode": loan.catalog_product_code, "items": [], "asOf": _now_iso()}

    raw = await file.read()
    if not raw:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/signature").inc()
        log_audit(event="v2_loan_signature_upload", endpoint="/api/loans/{loan_id}/signature", status="invalid", meta={"loanId": loan_id, "error": "Empty upload"})
        raise HTTPException(status_code=400, detail="Empty upload")

    uploads_root = os.getenv("KS_LOS_UPLOAD_DIR", "data/uploads")
    doc_id = str(uuid.uuid4())
    safe = _safe_filename(file.filename or "signature.png")
    loan_dir = os.path.join(uploads_root, "loans", loan_id)
    os.makedirs(loan_dir, exist_ok=True)
    stored_name = f"{doc_id}-{safe}"
    stored_path = os.path.join(loan_dir, stored_name)
    with open(stored_path, "wb") as f:
        f.write(raw)

    now = _now_iso()
    upload_meta = {
        "id": doc_id,
        "fileName": file.filename,
        "storedName": stored_name,
        "contentType": file.content_type,
        "sizeBytes": len(raw),
        "sha256": _sha256_bytes(raw),
        "uploadedAt": now,
        "extractedPreview": "",
    }

    signature_name = "Signature"
    items_in = checklist.get("items") if isinstance(checklist, dict) else None
    items = items_in if isinstance(items_in, list) else []
    updated_items: list[dict[str, Any]] = []
    seen_sig = False
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("name") == signature_name:
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
    log_audit(event="v2_loan_signature_upload", endpoint="/api/loans/{loan_id}/signature", status="success", meta={"loanId": loan_id, "docId": doc_id})
    v2_loan_document_updates_total.labels(status="submitted").inc()
    return _serialize_loan(loan)


@router.get("/{loan_id}/underwriting-memo")
def get_underwriting_memo(loan_id: str, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/loans/{loan_id}/underwriting-memo").inc()
    loan = db.get(Loan, loan_id)
    if not loan:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/underwriting-memo").inc()
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.underwriting_memo is None:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/underwriting-memo").inc()
        raise HTTPException(status_code=404, detail="Underwriting memo not found")
    return loan.underwriting_memo


@router.post("/{loan_id}/underwriting-memo")
def generate_underwriting_memo(loan_id: str, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/loans/{loan_id}/underwriting-memo").inc()
    loan = db.get(Loan, loan_id)
    if not loan:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/underwriting-memo").inc()
        log_audit(event="v2_underwriting_memo_generate", endpoint="/api/loans/{loan_id}/underwriting-memo", status="not_found", meta={"loanId": loan_id})
        v2_underwriting_memo_total.labels(status="not_found").inc()
        raise HTTPException(status_code=404, detail="Loan not found")

    product = _get_product_by_code(db, loan.catalog_product_code) if loan.catalog_product_code else None
    try:
        memo = _generate_underwriting_memo(loan, product)
    except Exception:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/underwriting-memo").inc()
        log_audit(event="v2_underwriting_memo_generate", endpoint="/api/loans/{loan_id}/underwriting-memo", status="error", meta={"loanId": loan_id})
        v2_underwriting_memo_total.labels(status="error").inc()
        raise HTTPException(status_code=500, detail="Failed to generate memo")

    loan.underwriting_memo = memo.model_dump()
    db.add(loan)
    db.commit()
    db.refresh(loan)
    log_audit(
        event="v2_underwriting_memo_generate",
        endpoint="/api/loans/{loan_id}/underwriting-memo",
        status="success",
        meta={"loanId": loan.id, "method": memo.method},
    )
    v2_underwriting_memo_total.labels(status="success").inc()
    return _serialize_loan(loan)
