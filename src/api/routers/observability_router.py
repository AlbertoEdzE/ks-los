from fastapi import APIRouter, Depends, Query
from typing import Dict, Any
import os
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.shared.auth import require_role
from src.shared.db import AuditEvent, get_db
from src.shared.metrics import (
    drift_runs_total,
    risk_inference_total,
    training_runs_total,
    v2_catalog_product_writes_total,
    v2_conversation_updates_total,
    v2_conversations_created_total,
    v2_loan_document_updates_total,
    v2_loans_created_total,
    v2_loans_updated_total,
    v2_messages_sent_total,
    v2_phase_actions_total,
    v2_underwriting_memo_total,
)

router = APIRouter(prefix="/observability", tags=["observability"])

def _sum_counter(counter) -> float:
    try:
        total = 0.0
        expected_sample_name = f"{counter._name}_total"
        for metric in counter.collect():
            for sample in metric.samples:
                if sample.name == expected_sample_name:
                    total += float(sample.value)
        return total
    except Exception:
        return 0.0

@router.get("/summary")
def summary(_: bool = Depends(require_role("operator"))) -> Dict[str, Any]:
    return {
        "training_runs": training_runs_total._value.get(),
        "drift_runs": drift_runs_total._value.get(),
        "risk_inferences": risk_inference_total._value.get(),
        "mlflow_url": os.getenv("MLFLOW_URL", "http://localhost:5000"),
        "drift_report_endpoint": "/training/drift/report",
        "v2_conversations_created": _sum_counter(v2_conversations_created_total),
        "v2_conversation_updates": _sum_counter(v2_conversation_updates_total),
        "v2_messages_sent": _sum_counter(v2_messages_sent_total),
        "v2_loans_created": _sum_counter(v2_loans_created_total),
        "v2_loans_updated": _sum_counter(v2_loans_updated_total),
        "v2_loan_document_updates": _sum_counter(v2_loan_document_updates_total),
        "v2_underwriting_memos": _sum_counter(v2_underwriting_memo_total),
        "v2_phase_actions": _sum_counter(v2_phase_actions_total),
        "v2_catalog_product_writes": _sum_counter(v2_catalog_product_writes_total),
    }


@router.get("/audit-events")
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    correlationId: str | None = Query(default=None),
    event: str | None = Query(default=None),
    status: str | None = Query(default=None),
    _: bool = Depends(require_role("operator")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    stmt = select(AuditEvent)
    if correlationId:
        stmt = stmt.where(AuditEvent.correlation_id == correlationId)
    if event:
        stmt = stmt.where(AuditEvent.event == event)
    if status:
        stmt = stmt.where(AuditEvent.status == status)
    rows = db.execute(stmt.order_by(AuditEvent.created_at.desc(), AuditEvent.id.asc()).limit(limit)).scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "event": r.event,
                "endpoint": r.endpoint,
                "status": r.status,
                "correlationId": r.correlation_id,
                "meta": r.meta,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }
