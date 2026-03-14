from typing import Any, Optional, Literal, Annotated, Union
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.routers.v2_auth import require_officer_role
from src.shared.audit import log_audit
from src.shared.db import Loan, LoanProductCatalog, get_db
from src.shared.metrics import request_counter, request_errors_total


router = APIRouter(prefix="/api/loans", tags=["v2_loans"], dependencies=[Depends(require_officer_role)])

_DOC_STATUSES = {"missing", "submitted", "verified", "rejected"}


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


def _get_product_by_code(db: Session, code: str) -> Optional[LoanProductCatalog]:
    from src.api.routers.v2_catalog_products_router import _ensure_seeded as _ensure_products_seeded

    _ensure_products_seeded(db)
    return db.execute(select(LoanProductCatalog).where(LoanProductCatalog.code == code)).scalar_one_or_none()


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
    rows = db.execute(select(Loan).order_by(Loan.updated_at.desc(), Loan.created_at.desc())).scalars().all()
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
    return _serialize_loan(loan)


@router.post("/actions")
def execute_loan_actions(req: LoanActionsRequest, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/loans/actions").inc()
    actions = _validate_loan_actions(req.actions)
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
            continue

        if isinstance(a, UpdateLoanAction):
            loan = db.get(Loan, a.loanId)
            if not loan:
                request_errors_total.labels(endpoint="/api/loans/actions").inc()
                raise HTTPException(status_code=404, detail="Loan not found")
            _apply_patch(loan, a.patch, db)
            db.add(loan)
            db.commit()
            db.refresh(loan)
            results.append({"type": a.type, "loanId": loan.id})
            continue

        request_errors_total.labels(endpoint="/api/loans/actions").inc()
        raise HTTPException(status_code=400, detail="Unsupported action")

    log_audit(event="v2_loan_actions", endpoint="/api/loans/actions", status="success", meta={"count": len(results)})
    return {"results": results}




@router.patch("/{loan_id}")
def patch_loan(loan_id: str, req: PatchLoanRequest, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/loans/{loan_id}").inc()
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
    return _serialize_loan(loan)


@router.patch("/{loan_id}/documents")
def patch_loan_document(loan_id: str, req: PatchLoanDocumentRequest, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/loans/{loan_id}/documents").inc()
    if req.status not in _DOC_STATUSES:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents").inc()
        raise HTTPException(status_code=400, detail="Invalid document status")

    loan = db.get(Loan, loan_id)
    if not loan:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents").inc()
        log_audit(event="v2_loan_document_patch", endpoint="/api/loans/{loan_id}/documents", status="not_found", meta={"loanId": loan_id})
        raise HTTPException(status_code=404, detail="Loan not found")

    checklist = loan.document_checklist
    if not isinstance(checklist, dict) or not isinstance(checklist.get("items"), list):
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents").inc()
        raise HTTPException(status_code=400, detail="Loan has no document checklist")

    target = req.name.strip()
    if not target:
        request_errors_total.labels(endpoint="/api/loans/{loan_id}/documents").inc()
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
    return _serialize_loan(loan)
