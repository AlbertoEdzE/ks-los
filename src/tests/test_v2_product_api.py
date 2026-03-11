import os
import tempfile

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker


DB_PATH = os.path.join(tempfile.gettempdir(), "ks_los_v2_test.db")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["SQLITE_FALLBACK_URL"] = f"sqlite:///{DB_PATH}"
os.environ["DATABASE_URL"] = "postgresql+psycopg://invalid:invalid@localhost:1/invalid"

from src.shared.db import Loan, get_engine, init_db, reset_db_for_tests

reset_db_for_tests()

from src.main import app


client = TestClient(app)


OFFICER_HEADERS = {"x-officer-role": "loan-officer-access"}

def _db_session():
    init_db()
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def test_v2_phases_seed_and_list():
    res = client.get("/api/phases")
    assert res.status_code == 200
    phases = res.json()
    assert isinstance(phases, list)
    assert len(phases) >= 1
    assert phases[0]["sortOrder"] == 1

    res2 = client.get("/api/phases/active")
    assert res2.status_code == 200
    active = res2.json()
    assert len(active) >= 1
    assert all(p["isActive"] is True for p in active)


def test_v2_conversation_create_and_list_requires_officer():
    create = client.post("/api/conversations", json={})
    assert create.status_code == 200
    payload = create.json()
    assert "conversation" in payload
    assert "greeting" in payload
    conv_id = payload["conversation"]["id"]
    assert payload["conversation"]["chatRole"] == "borrower"
    assert payload["conversation"]["currentPhaseId"] is not None

    list_no_officer = client.get("/api/conversations")
    assert list_no_officer.status_code == 403

    list_officer = client.get("/api/conversations", headers=OFFICER_HEADERS)
    assert list_officer.status_code == 200
    conversations = list_officer.json()
    assert any(c["id"] == conv_id for c in conversations)


def test_v2_conversation_patch_and_messages_flow():
    create = client.post("/api/conversations", json={})
    conv_id = create.json()["conversation"]["id"]

    patch = client.patch(
        f"/api/conversations/{conv_id}",
        json={"borrowerName": "Jane Doe", "status": "reviewing"},
        headers=OFFICER_HEADERS,
    )
    assert patch.status_code == 200
    updated = patch.json()
    assert updated["borrowerName"] == "Jane Doe"
    assert updated["status"] == "reviewing"

    msgs0 = client.get(f"/api/conversations/{conv_id}/messages")
    assert msgs0.status_code == 200
    assert len(msgs0.json()) >= 1

    send = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "I want a home loan."})
    assert send.status_code == 200
    send_payload = send.json()
    assert send_payload["message"]["role"] == "assistant"

    msgs1 = client.get(f"/api/conversations/{conv_id}/messages")
    assert msgs1.status_code == 200
    msgs = msgs1.json()
    assert any(m["role"] == "user" for m in msgs)
    assert any(m["role"] == "assistant" for m in msgs)


def test_v2_loans_list_and_patch_requires_officer():
    with _db_session() as db:
        loan = Loan(borrower_name="John Smith", loan_type="Home Loan", loan_amount="250000", status="draft")
        db.add(loan)
        db.commit()
        db.refresh(loan)
        loan_id = loan.id

    list_no_officer = client.get("/api/loans")
    assert list_no_officer.status_code == 403

    list_officer = client.get("/api/loans", headers=OFFICER_HEADERS)
    assert list_officer.status_code == 200
    loans = list_officer.json()
    assert any(l["id"] == loan_id for l in loans)

    patch_no_officer = client.patch(f"/api/loans/{loan_id}", json={"status": "submitted"})
    assert patch_no_officer.status_code == 403

    patch_officer = client.patch(
        f"/api/loans/{loan_id}",
        json={"status": "submitted", "notes": "Docs pending"},
        headers=OFFICER_HEADERS,
    )
    assert patch_officer.status_code == 200
    updated = patch_officer.json()
    assert updated["id"] == loan_id
    assert updated["status"] == "submitted"
    assert updated["notes"] == "Docs pending"
