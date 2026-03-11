from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.shared.db import LoanPhase, get_db


router = APIRouter(prefix="/api/phases", tags=["v2_phases"])


DEFAULT_PHASES = [
    {
        "name": "Lead & Inquiry",
        "description": "Initial contact and inquiry from the borrower",
        "sort_order": 1,
        "color": "#60a5fa",
        "icon": "user-plus",
    },
    {
        "name": "Application Submission",
        "description": "Formal loan application submitted by the borrower",
        "sort_order": 2,
        "color": "#34d399",
        "icon": "file-text",
    },
    {
        "name": "Document Collection & KYC",
        "description": "Gathering required documents and completing KYC verification",
        "sort_order": 3,
        "color": "#fbbf24",
        "icon": "folder-open",
    },
    {
        "name": "Verification & Credit Appraisal",
        "description": "Background verification and credit score appraisal",
        "sort_order": 4,
        "color": "#f97316",
        "icon": "search",
    },
    {
        "name": "Underwriting & Credit Decision",
        "description": "Risk assessment and credit decision by the underwriting team",
        "sort_order": 5,
        "color": "#a78bfa",
        "icon": "shield-check",
    },
    {
        "name": "Conditional Approval & Offer",
        "description": "Conditional approval issued with loan terms and offer letter",
        "sort_order": 6,
        "color": "#2dd4bf",
        "icon": "check-circle",
    },
    {
        "name": "Security & Legal Documentation",
        "description": "Legal documentation, mortgage registration, and security creation",
        "sort_order": 7,
        "color": "#ec4899",
        "icon": "scale",
    },
    {
        "name": "Pre-Disbursement Checks",
        "description": "Final checks before funds are disbursed",
        "sort_order": 8,
        "color": "#14b8a6",
        "icon": "clipboard-check",
    },
    {
        "name": "Disbursement",
        "description": "Loan amount disbursed to the borrower's account",
        "sort_order": 9,
        "color": "#22c55e",
        "icon": "banknote",
    },
]


_seeded = False


def _ensure_seeded(db: Session):
    global _seeded
    if _seeded:
        return
    existing = db.execute(select(LoanPhase.id).limit(1)).first()
    if existing is None:
        for p in DEFAULT_PHASES:
            db.add(LoanPhase(**p))
        db.commit()
    _seeded = True


@router.get("")
def list_phases(db: Session = Depends(get_db)):
    _ensure_seeded(db)
    rows = db.execute(select(LoanPhase).order_by(LoanPhase.sort_order.asc())).scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "sortOrder": r.sort_order,
            "isActive": r.is_active,
            "color": r.color,
            "icon": r.icon,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
            "updatedAt": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


@router.get("/active")
def list_active_phases(db: Session = Depends(get_db)):
    _ensure_seeded(db)
    rows = (
        db.execute(
            select(LoanPhase).where(LoanPhase.is_active.is_(True)).order_by(LoanPhase.sort_order.asc())
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "sortOrder": r.sort_order,
            "isActive": r.is_active,
            "color": r.color,
            "icon": r.icon,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
            "updatedAt": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]

