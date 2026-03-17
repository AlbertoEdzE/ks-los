from typing import Any, Optional, Literal, Annotated, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.routers.v2_auth import require_officer_role
from src.shared.audit import log_audit
from src.shared.db import LoanPhase, get_db
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
