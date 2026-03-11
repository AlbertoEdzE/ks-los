from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.routers.v2_auth import require_officer_role
from src.shared.db import Loan, get_db


router = APIRouter(prefix="/api/loans", tags=["v2_loans"], dependencies=[Depends(require_officer_role)])


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
    currentPhaseId: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    conversationId: Optional[str] = None
    createdBy: Optional[str] = None


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
    rows = db.execute(select(Loan).order_by(Loan.updated_at.desc(), Loan.created_at.desc())).scalars().all()
    return [_serialize_loan(l) for l in rows]


@router.patch("/{loan_id}")
def patch_loan(loan_id: str, req: PatchLoanRequest, db: Session = Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if req.borrowerName is not None:
        loan.borrower_name = req.borrowerName
    if req.borrowerEmail is not None:
        loan.borrower_email = req.borrowerEmail
    if req.borrowerPhone is not None:
        loan.borrower_phone = req.borrowerPhone
    if req.loanType is not None:
        loan.loan_type = req.loanType
    if req.loanAmount is not None:
        loan.loan_amount = req.loanAmount
    if req.interestRate is not None:
        loan.interest_rate = req.interestRate
    if req.tenure is not None:
        loan.tenure = req.tenure
    if req.monthlyEmi is not None:
        loan.monthly_emi = req.monthlyEmi
    if req.purpose is not None:
        loan.purpose = req.purpose
    if req.employmentType is not None:
        loan.employment_type = req.employmentType
    if req.monthlyIncome is not None:
        loan.monthly_income = req.monthlyIncome
    if req.existingDebts is not None:
        loan.existing_debts = req.existingDebts
    if req.creditScore is not None:
        loan.credit_score = req.creditScore
    if req.collateral is not None:
        loan.collateral = req.collateral
    if req.downPayment is not None:
        loan.down_payment = req.downPayment
    if req.propertyValue is not None:
        loan.property_value = req.propertyValue
    if req.ltv is not None:
        loan.ltv = req.ltv
    if req.currentPhaseId is not None:
        loan.current_phase_id = req.currentPhaseId
    if req.status is not None:
        loan.status = req.status
    if req.notes is not None:
        loan.notes = req.notes
    if req.conversationId is not None:
        loan.conversation_id = req.conversationId
    if req.createdBy is not None:
        loan.created_by = req.createdBy

    db.add(loan)
    db.commit()
    db.refresh(loan)
    return _serialize_loan(loan)
