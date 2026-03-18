import os
import tempfile
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select

DB_PATH = os.path.join(tempfile.gettempdir(), f"ks_los_wp_v2_019_{uuid.uuid4().hex}.db")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["SQLITE_FALLBACK_URL"] = f"sqlite:///{DB_PATH}"
os.environ["DATABASE_URL"] = "postgresql+psycopg://invalid:invalid@localhost:1/invalid"

from src.shared.db import AuditEvent, create_session, reset_db_for_tests

reset_db_for_tests()

from src.main import app

client = TestClient(app)
OFFICER_HEADERS = {"Authorization": "Bearer loan-officer-access"}


def _count_audit(event: str, status: str | None = None) -> int:
    db = create_session()
    try:
        stmt = select(func.count(AuditEvent.id)).where(AuditEvent.event == event)
        if status is not None:
            stmt = stmt.where(AuditEvent.status == status)
        return int(db.execute(stmt).scalar_one())
    finally:
        db.close()


def test_wp_v2_019_audit_and_metrics_evidence_for_v2_writes():
    seed = client.post("/admin/seed/v2-baseline?reset=true", headers=OFFICER_HEADERS)
    assert seed.status_code == 200

    before = _count_audit("v2_conversation_create", "success")
    created = client.post("/api/conversations", json={})
    assert created.status_code == 200
    after = _count_audit("v2_conversation_create", "success")
    assert after == before + 1
    conversation_id = created.json()["conversation"]["id"]

    before = _count_audit("v2_message_send", "invalid")
    invalid_msg = client.post(f"/api/conversations/{conversation_id}/messages", json={"content": ""})
    assert invalid_msg.status_code == 400
    after = _count_audit("v2_message_send", "invalid")
    assert after == before + 1

    before = _count_audit("v2_message_send", "success")
    ok_msg = client.post(f"/api/conversations/{conversation_id}/messages", json={"content": "hello"})
    assert ok_msg.status_code == 200
    after = _count_audit("v2_message_send", "success")
    assert after == before + 1

    phases = client.get("/api/phases").json()
    assert len(phases) >= 2
    before = _count_audit("v2_phase_actions", "invalid")
    reorder = client.post(
        "/api/phases/actions",
        headers=OFFICER_HEADERS,
        json={"actions": [{"type": "reorder_phases", "phaseIds": [phases[0]["id"]]}]},
    )
    assert reorder.status_code == 400
    after = _count_audit("v2_phase_actions", "invalid")
    assert after == before + 1

    before = _count_audit("v2_loan_create", "success")
    loan = client.post("/api/loans", headers=OFFICER_HEADERS, json={"borrowerName": "Ada", "loanType": "Home", "loanAmount": "100000"})
    assert loan.status_code == 200
    loan_id = loan.json()["id"]
    after = _count_audit("v2_loan_create", "success")
    assert after == before + 1

    before = _count_audit("v2_loan_document_patch", "invalid")
    invalid_doc = client.patch(
        f"/api/loans/{loan_id}/documents",
        headers=OFFICER_HEADERS,
        json={"name": "Any", "status": "BAD_STATUS"},
    )
    assert invalid_doc.status_code == 400
    after = _count_audit("v2_loan_document_patch", "invalid")
    assert after == before + 1

    before = _count_audit("v2_loan_actions", "not_found")
    missing = client.post(
        "/api/loans/actions",
        headers=OFFICER_HEADERS,
        json={"actions": [{"type": "update_loan", "loanId": "does-not-exist", "patch": {"status": "draft"}}]},
    )
    assert missing.status_code == 404
    after = _count_audit("v2_loan_actions", "not_found")
    assert after == before + 1

    metrics = client.get("/metrics").text
    assert 'v2_conversations_created_total{chat_role="borrower"}' in metrics
    assert 'v2_messages_sent_total{actor_role="unknown",chat_role="borrower",status="invalid"}' in metrics
    assert 'v2_messages_sent_total{actor_role="borrower",chat_role="borrower",status="success"}' in metrics
    assert 'v2_phase_actions_total{action="reorder_phases",status="invalid"}' in metrics
    assert 'v2_loans_created_total{source="endpoint"}' in metrics
    assert 'v2_loan_document_updates_total{status="invalid"}' in metrics


def test_wp_v2_019_observability_summary_exposes_v2_rollups():
    r = client.get("/observability/summary", headers=OFFICER_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "v2_conversations_created" in data
    assert "v2_messages_sent" in data
    assert "v2_loans_created" in data
