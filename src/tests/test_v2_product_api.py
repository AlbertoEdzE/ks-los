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
    assert send_payload["intentAnalysis"]["intentSummary"]["purpose"] == "home"
    assert isinstance(send_payload["intentAnalysis"]["seriousnessScore"], int)
    assert isinstance(send_payload["intentAnalysis"]["fitScore"], int)
    assert isinstance(send_payload["intentAnalysis"]["nextConversationAngle"], str)

    msgs1 = client.get(f"/api/conversations/{conv_id}/messages")
    assert msgs1.status_code == 200
    msgs = msgs1.json()
    assert any(m["role"] == "user" for m in msgs)
    assert any(m["role"] == "assistant" for m in msgs)

    conv = client.get(f"/api/conversations/{conv_id}")
    assert conv.status_code == 200
    conv_payload = conv.json()
    assert conv_payload["intentSummary"] is not None
    assert conv_payload["seriousnessScore"] is not None
    assert conv_payload["fitScore"] is not None
    assert conv_payload["nextConversationAngle"] is not None


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


def test_v2_catalog_products_list_create_patch_requires_officer():
    list_no_officer = client.get("/api/catalog-products")
    assert list_no_officer.status_code == 403

    seeded = client.get("/api/catalog-products", headers=OFFICER_HEADERS)
    assert seeded.status_code == 200
    products = seeded.json()
    assert isinstance(products, list)
    assert len(products) >= 1

    create_no_officer = client.post(
        "/api/catalog-products",
        json={"name": "Test Product", "code": "TEST-001", "category": "test"},
    )
    assert create_no_officer.status_code == 403

    created = client.post(
        "/api/catalog-products",
        json={
            "name": "Test Product",
            "code": "TEST-001",
            "category": "test",
            "status": "draft",
            "requiredDocuments": ["Doc A"],
        },
        headers=OFFICER_HEADERS,
    )
    assert created.status_code == 200
    created_product = created.json()
    assert created_product["code"] == "TEST-001"
    assert created_product["requiredDocuments"] == ["Doc A"]

    patch_no_officer = client.patch(
        f"/api/catalog-products/{created_product['id']}",
        json={"status": "active"},
    )
    assert patch_no_officer.status_code == 403

    patched = client.patch(
        f"/api/catalog-products/{created_product['id']}",
        json={"status": "active", "minCreditScore": 720},
        headers=OFFICER_HEADERS,
    )
    assert patched.status_code == 200
    patched_product = patched.json()
    assert patched_product["status"] == "active"
    assert patched_product["minCreditScore"] == 720


def test_v2_seeding_is_idempotent_for_phases_and_products():
    phases1 = client.get("/api/phases").json()
    phases2 = client.get("/api/phases").json()
    assert len(phases1) == len(phases2)
    assert {p["id"] for p in phases1} == {p["id"] for p in phases2}

    products1 = client.get("/api/catalog-products", headers=OFFICER_HEADERS).json()
    products2 = client.get("/api/catalog-products", headers=OFFICER_HEADERS).json()
    assert len(products1) == len(products2)
    assert {p["id"] for p in products1} == {p["id"] for p in products2}


def test_wp_v2_007_admin_seed_v2_baseline_idempotent_and_reset():
    reset = client.post("/admin/seed/v2-baseline?reset=true", headers=OFFICER_HEADERS)
    assert reset.status_code == 200
    baseline = reset.json()
    assert baseline["phases_total"] >= 1
    assert baseline["products_total"] >= 1

    again = client.post("/admin/seed/v2-baseline", headers=OFFICER_HEADERS)
    assert again.status_code == 200
    payload2 = again.json()
    assert payload2["phases_total"] == baseline["phases_total"]
    assert payload2["products_total"] == baseline["products_total"]


def test_wp_v2_008_intent_summary_schema_rejects_unknown_fields():
    from pydantic import ValidationError
    from src.api.routers.v2_conversations_router import IntentSummary

    IntentSummary.model_validate({"purpose": "home"})

    try:
        IntentSummary.model_validate({"purpose": "home", "unknownKey": "x"})
        assert False, "Expected ValidationError"
    except ValidationError:
        assert True
