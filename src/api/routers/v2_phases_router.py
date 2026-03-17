from typing import Any, Optional, Literal, Annotated, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.api.routers.v2_auth import require_officer_role
from src.shared.audit import log_audit
from src.shared.db import Conversation, Loan, LoanPhase, get_db
from src.shared.metrics import request_counter, request_errors_total


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

_PHASE_KNOWLEDGE: dict[str, dict[str, Any]] = {
    "lead & inquiry": {
        "timeline": "Same day",
        "summary": "Initial borrower contact where the loan purpose, approximate amount, and basic eligibility signals are captured to determine next steps.",
        "activities": [
            "Capture borrower identity and contact preferences",
            "Confirm loan purpose and expected amount range",
            "Collect high-level income and employment details",
            "Record initial credit history signal (if available)",
            "Set expectations for application and document requirements",
        ],
        "documents": [
            "Government-issued ID (if available)",
            "Basic income proof (latest payslip / salary credit statement)",
        ],
        "stakeholders": [
            "Borrower",
            "Loan Officer / Relationship Manager",
        ],
        "bottlenecks": [
            "Incomplete borrower contact details",
            "Unclear loan purpose or amount range",
            "Borrower not ready to proceed with application",
        ],
    },
    "application submission": {
        "timeline": "1–3 days",
        "summary": "The borrower submits a formal application with core personal, financial, and loan request details required for downstream verification.",
        "activities": [
            "Complete application form and declarations",
            "Validate required fields and formatting",
            "Select product and indicative terms (where applicable)",
            "Create the initial loan record for processing",
        ],
        "documents": [
            "Application form / e-consent",
            "Address proof",
            "Income proof (payslips / bank statements)",
        ],
        "stakeholders": [
            "Borrower",
            "Loan Officer / Relationship Manager",
            "Operations / Intake team",
        ],
        "bottlenecks": [
            "Missing mandatory fields",
            "Mismatch between requested amount and basic eligibility",
            "Delays in borrower submission",
        ],
    },
    "document collection & kyc": {
        "timeline": "2–7 days",
        "summary": "KYC and supporting documents are gathered and validated to establish identity, income, and compliance readiness for verification and appraisal.",
        "activities": [
            "Collect required documents for the selected product",
            "Perform KYC verification checks",
            "Validate document authenticity and completeness",
            "Resolve discrepancies via borrower follow-up",
        ],
        "documents": [
            "Government-issued ID",
            "Address proof",
            "Bank statements",
            "Income proof (salary slips / tax returns)",
        ],
        "stakeholders": [
            "Borrower",
            "Loan Officer / Relationship Manager",
            "KYC / Compliance team",
        ],
        "bottlenecks": [
            "Document mismatch (name/address inconsistencies)",
            "Expired or illegible documents",
            "Slow borrower turnaround on missing items",
        ],
    },
    "verification & credit appraisal": {
        "timeline": "2–5 days",
        "summary": "Background verification and credit assessment determine creditworthiness using bureau inputs and internal verification outcomes.",
        "activities": [
            "Run credit bureau checks",
            "Verify employment and income consistency",
            "Confirm address and identity validation outcomes",
            "Compute preliminary risk indicators",
        ],
        "documents": [
            "Credit bureau report authorization",
            "Employment verification artifacts (where applicable)",
        ],
        "stakeholders": [
            "Borrower",
            "Verification team",
            "Credit / Risk analysts",
        ],
        "bottlenecks": [
            "Credit bureau delays or thin-file profiles",
            "Verification unable to confirm employment/address",
            "Discrepancies requiring rework",
        ],
    },
    "underwriting & credit decision": {
        "timeline": "2–7 days",
        "summary": "Underwriting evaluates the verified profile, applies policy rules, and issues a credit decision with conditions (if any).",
        "activities": [
            "Assess debt-to-income and affordability",
            "Apply underwriting policy rules and exceptions",
            "Review collateral/valuation inputs (if applicable)",
            "Approve, decline, or request additional conditions",
        ],
        "documents": [
            "Underwriting checklist",
            "Collateral valuation report (if applicable)",
        ],
        "stakeholders": [
            "Underwriting team",
            "Credit / Risk team",
            "Loan Officer / Relationship Manager",
        ],
        "bottlenecks": [
            "Policy exceptions requiring escalation",
            "Missing verification artifacts",
            "Valuation delays (secured lending)",
        ],
    },
    "conditional approval & offer": {
        "timeline": "1–3 days",
        "summary": "A conditional approval and offer are produced, capturing terms, conditions, and any remaining items required before final approval/disbursement.",
        "activities": [
            "Generate offer letter and term sheet",
            "Review conditions with borrower",
            "Capture acceptance and required acknowledgements",
            "Update the loan record with offered terms",
        ],
        "documents": [
            "Offer letter / term sheet",
            "Borrower acceptance / consent",
        ],
        "stakeholders": [
            "Borrower",
            "Loan Officer / Relationship Manager",
            "Operations team",
        ],
        "bottlenecks": [
            "Borrower delays in offer acceptance",
            "Terms negotiation and re-approval",
            "Missing acknowledgements/consents",
        ],
    },
    "security & legal documentation": {
        "timeline": "3–14 days",
        "summary": "Legal and security documentation is executed (where required), including collateral registration, to ensure enforceability prior to disbursement.",
        "activities": [
            "Prepare legal documentation pack",
            "Execute agreements and security documents",
            "Register collateral / lien (if applicable)",
            "Confirm fulfillment of legal conditions",
        ],
        "documents": [
            "Loan agreement",
            "Security documents (mortgage / charge)",
            "Insurance documents (if applicable)",
        ],
        "stakeholders": [
            "Borrower",
            "Legal team",
            "Operations team",
        ],
        "bottlenecks": [
            "Legal review iterations",
            "Collateral registration delays",
            "Missing signatures or incorrect paperwork",
        ],
    },
    "pre-disbursement checks": {
        "timeline": "1–3 days",
        "summary": "Final operational checks confirm all approval conditions are satisfied, documents are complete, and disbursement prerequisites are met.",
        "activities": [
            "Confirm all conditions are cleared",
            "Validate bank account and disbursement instructions",
            "Final compliance and sanctions screening (if required)",
            "Prepare disbursement authorization",
        ],
        "documents": [
            "Final checklist / sign-offs",
            "Disbursement instructions",
        ],
        "stakeholders": [
            "Operations team",
            "Compliance team",
            "Loan Officer / Relationship Manager",
        ],
        "bottlenecks": [
            "Pending conditions not cleared",
            "Account verification issues",
            "Operational queue delays",
        ],
    },
    "disbursement": {
        "timeline": "Same day",
        "summary": "Funds are released according to approved terms and recorded as disbursed, completing the origination workflow.",
        "activities": [
            "Execute disbursement transaction",
            "Confirm borrower receipt and settlement",
            "Update loan status and artifacts",
            "Initiate post-disbursement servicing handoff",
        ],
        "documents": [
            "Disbursement confirmation",
            "Repayment schedule",
        ],
        "stakeholders": [
            "Borrower",
            "Operations / Payments team",
            "Servicing team (handoff)",
        ],
        "bottlenecks": [
            "Bank settlement delays",
            "Incorrect disbursement instructions",
            "Last-minute compliance holds",
        ],
    },
}


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


class PhaseActionsRequest(BaseModel):
    actions: list[dict[str, Any]]


class AddPhaseAction(BaseModel):
    type: Literal["add_phase"]
    name: str
    description: Optional[str] = None


class SetPhaseActiveAction(BaseModel):
    type: Literal["set_phase_active"]
    phaseId: str
    isActive: bool


class ReorderPhasesAction(BaseModel):
    type: Literal["reorder_phases"]
    phaseIds: list[str]


PhaseAction = Annotated[Union[AddPhaseAction, SetPhaseActiveAction, ReorderPhasesAction], Field(discriminator="type")]


def _validate_phase_actions(raw: list[dict[str, Any]]) -> list[PhaseAction]:
    adapter = TypeAdapter(list[PhaseAction])
    try:
        return adapter.validate_python(raw)
    except ValidationError as e:
        raise ValueError(e.errors())


@router.get("")
def list_phases(db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/phases").inc()
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
    request_counter.labels(endpoint="/api/phases/active").inc()
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


@router.get("/{phase_id}/detail")
def get_phase_detail(phase_id: str, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/phases/{phase_id}/detail").inc()
    _ensure_seeded(db)
    phase = db.get(LoanPhase, phase_id)
    if not phase:
        request_errors_total.labels(endpoint="/api/phases/{phase_id}/detail").inc()
        raise HTTPException(status_code=404, detail="Phase not found")

    key = (phase.name or "").strip().lower()
    knowledge = _PHASE_KNOWLEDGE.get(key) or {
        "timeline": "Varies",
        "summary": phase.description or "—",
        "activities": [],
        "documents": [],
        "stakeholders": [],
        "bottlenecks": [],
    }

    loan_count = db.execute(select(func.count(Loan.id)).where(Loan.current_phase_id == phase_id)).scalar_one()
    conversation_count = db.execute(select(func.count(Conversation.id)).where(Conversation.current_phase_id == phase_id)).scalar_one()

    return {
        "phase": {
            "id": phase.id,
            "name": phase.name,
            "description": phase.description,
            "sortOrder": phase.sort_order,
            "isActive": phase.is_active,
            "color": phase.color,
            "icon": phase.icon,
            "createdAt": phase.created_at.isoformat() if phase.created_at else None,
            "updatedAt": phase.updated_at.isoformat() if phase.updated_at else None,
        },
        "knowledge": knowledge,
        "metrics": {"loanCount": int(loan_count or 0), "conversationCount": int(conversation_count or 0)},
    }


@router.post("/actions", dependencies=[Depends(require_officer_role)])
def execute_phase_actions(req: PhaseActionsRequest, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/phases/actions").inc()
    _ensure_seeded(db)
    actions = _validate_phase_actions(req.actions)
    results: list[dict[str, Any]] = []

    for a in actions:
        if isinstance(a, AddPhaseAction):
            max_order = db.execute(select(LoanPhase.sort_order).order_by(LoanPhase.sort_order.desc()).limit(1)).scalar_one_or_none() or 0
            phase = LoanPhase(
                name=a.name,
                description=a.description,
                sort_order=max_order + 1,
                is_active=True,
            )
            db.add(phase)
            db.commit()
            db.refresh(phase)
            results.append({"type": a.type, "phaseId": phase.id, "name": phase.name, "isActive": True, "sortOrder": phase.sort_order})
            continue

        if isinstance(a, SetPhaseActiveAction):
            phase = db.get(LoanPhase, a.phaseId)
            if not phase:
                request_errors_total.labels(endpoint="/api/phases/actions").inc()
                log_audit(
                    event="v2_phase_actions",
                    endpoint="/api/phases/actions",
                    status="not_found",
                    meta={"phaseId": a.phaseId},
                )
                raise HTTPException(status_code=404, detail="Phase not found")
            phase.is_active = a.isActive
            db.add(phase)
            db.commit()
            results.append({"type": a.type, "phaseId": phase.id, "isActive": phase.is_active})
            continue

        if isinstance(a, ReorderPhasesAction):
            rows = db.execute(select(LoanPhase)).scalars().all()
            phases_by_id = {p.id: p for p in rows}
            if len(a.phaseIds) != len(phases_by_id):
                request_errors_total.labels(endpoint="/api/phases/actions").inc()
                raise HTTPException(status_code=400, detail="phaseIds must include all phases")
            if set(a.phaseIds) != set(phases_by_id.keys()):
                request_errors_total.labels(endpoint="/api/phases/actions").inc()
                raise HTTPException(status_code=400, detail="phaseIds must match existing phases")

            for idx, pid in enumerate(a.phaseIds, start=1):
                phases_by_id[pid].sort_order = idx
                db.add(phases_by_id[pid])
            db.commit()
            results.append({"type": a.type, "phaseIds": a.phaseIds})
            continue

        request_errors_total.labels(endpoint="/api/phases/actions").inc()
        raise HTTPException(status_code=400, detail="Unsupported action")

    log_audit(event="v2_phase_actions", endpoint="/api/phases/actions", status="success", meta={"count": len(actions)})
    return {"ok": True, "results": results}
