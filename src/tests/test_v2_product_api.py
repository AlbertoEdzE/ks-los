import os
import tempfile
import uuid

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
        json={"borrowerName": "Jane Doe", "status": "reviewing", "assignedOfficer": "officer-1"},
        headers=OFFICER_HEADERS,
    )
    assert patch.status_code == 200
    updated = patch.json()
    assert updated["borrowerName"] == "Jane Doe"
    assert updated["status"] == "reviewing"
    assert updated["assignedOfficer"] == "officer-1"

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
    assert "approvalProbability" in send_payload
    assert isinstance(send_payload["approvalProbability"]["probability"], float)
    assert 0.0 <= send_payload["approvalProbability"]["probability"] <= 1.0
    assert send_payload["approvalProbability"]["band"] in {"low", "medium", "high"}
    assert isinstance(send_payload["approvalProbability"]["topBlockers"], list)
    assert isinstance(send_payload["approvalProbability"]["topActions"], list)
    assert isinstance(send_payload["loanRecommendations"], list)
    assert len(send_payload["loanRecommendations"]) >= 1

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
    assert conv_payload["approvalProbability"] is not None
    assert isinstance(conv_payload["approvalProbability"]["probability"], float)
    assert isinstance(conv_payload["recommendedProducts"], list)
    assert len(conv_payload["recommendedProducts"]) >= 1
    first = conv_payload["recommendedProducts"][0]
    assert isinstance(first.get("name"), str)
    assert isinstance(first.get("type"), str)
    assert isinstance(first.get("estimatedRate"), str)
    assert isinstance(first.get("estimatedEmi"), str)
    assert isinstance(first.get("tenure"), str)
    assert isinstance(first.get("approvalSpeed"), str)
    assert isinstance(first.get("pros"), list)
    assert isinstance(first.get("cons"), list)
    assert isinstance(first.get("recommendation"), str)


def test_wp_v2_008_intent_summary_filters_unknown_keys():
    from src.api.routers.v2_conversations_router import analyze_intent_message

    prev = {"purpose": "home", "evil": "x"}
    res = analyze_intent_message("income is 5000", prev)
    assert "evil" not in res["intentSummary"]


def test_wp_v2_009_phase_progression_is_sequential_and_no_skips():
    phases_res = client.get("/api/phases/active")
    assert phases_res.status_code == 200
    phases = phases_res.json()
    assert len(phases) >= 4

    create = client.post("/api/conversations", json={})
    assert create.status_code == 200
    conv_id = create.json()["conversation"]["id"]

    conv0 = client.get(f"/api/conversations/{conv_id}").json()
    ids = [p["id"] for p in phases]
    idx0 = ids.index(conv0["currentPhaseId"])

    msg1 = "Home loan $300k. Income 8000. Salaried. Credit score 760."
    send1 = client.post(f"/api/conversations/{conv_id}/messages", json={"content": msg1})
    assert send1.status_code == 200
    conv1 = client.get(f"/api/conversations/{conv_id}").json()
    idx1 = ids.index(conv1["currentPhaseId"])
    assert idx1 == idx0 + 1

    send2 = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Adding more details."})
    assert send2.status_code == 200
    conv2 = client.get(f"/api/conversations/{conv_id}").json()
    idx2 = ids.index(conv2["currentPhaseId"])
    assert idx2 == idx1 + 1


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


def test_wp_v2_016_document_checklist_is_derived_from_catalog_product_and_persists():
    seeded = client.get("/api/catalog-products", headers=OFFICER_HEADERS)
    assert seeded.status_code == 200
    products = seeded.json()
    with_docs = [p for p in products if isinstance(p.get("requiredDocuments"), list) and len(p.get("requiredDocuments")) > 0]
    assert len(with_docs) >= 1
    product = with_docs[0]

    created = client.post(
        "/api/loans",
        json={
            "borrowerName": "Checklist Borrower",
            "loanType": "Home Loan",
            "loanAmount": "250000",
            "catalogProductCode": product["code"],
        },
        headers=OFFICER_HEADERS,
    )
    assert created.status_code == 200
    loan = created.json()
    assert loan["catalogProductCode"] == product["code"]
    assert loan["documentChecklist"] is not None
    checklist = loan["documentChecklist"]
    assert checklist["productCode"] == product["code"]

    names = [i["name"] for i in checklist["items"]]
    assert names == product["requiredDocuments"]
    assert all(i["status"] == "missing" for i in checklist["items"])

    first_doc = checklist["items"][0]["name"]
    updated = client.patch(
        f"/api/loans/{loan['id']}/documents",
        json={"name": first_doc, "status": "submitted"},
        headers=OFFICER_HEADERS,
    )
    assert updated.status_code == 200
    payload = updated.json()
    by_name = {i["name"]: i for i in payload["documentChecklist"]["items"]}
    assert by_name[first_doc]["status"] == "submitted"

    fetched = client.get(f"/api/loans/{loan['id']}", headers=OFFICER_HEADERS)
    assert fetched.status_code == 200
    fetched_payload = fetched.json()
    by_name_fetched = {i["name"]: i for i in fetched_payload["documentChecklist"]["items"]}
    assert by_name_fetched[first_doc]["status"] == "submitted"


def test_wp_v2_013_loan_action_validator_rejects_invalid_payload():
    from src.api.routers.v2_loans_router import _validate_loan_actions

    try:
        _validate_loan_actions([{"type": "create_loan", "borrowerName": "Alice"}])
        assert False, "Expected validator to reject missing required fields"
    except ValueError as e:
        issues = e.args[0]
        assert any("loanType" in tuple(err.get("loc", ())) for err in issues)
        assert any("loanAmount" in tuple(err.get("loc", ())) for err in issues)


def test_wp_v2_013_execute_loan_actions_create_and_update():
    no_officer = client.post(
        "/api/loans/actions",
        json={"actions": [{"type": "create_loan", "borrowerName": "Alice", "loanType": "Home Loan", "loanAmount": "250000"}]},
    )
    assert no_officer.status_code == 403

    phases = client.get("/api/phases/active").json()
    assert len(phases) >= 1
    phase_id = phases[0]["id"]

    created = client.post(
        "/api/loans/actions",
        json={"actions": [{"type": "create_loan", "borrowerName": "Alice", "loanType": "Home Loan", "loanAmount": "250000"}]},
        headers=OFFICER_HEADERS,
    )
    assert created.status_code == 200
    created_payload = created.json()
    loan_id = created_payload["results"][0]["loanId"]

    updated = client.post(
        "/api/loans/actions",
        json={"actions": [{"type": "update_loan", "loanId": loan_id, "patch": {"status": "submitted", "currentPhaseId": phase_id}}]},
        headers=OFFICER_HEADERS,
    )
    assert updated.status_code == 200

    unassigned = client.post(
        "/api/loans/actions",
        json={"actions": [{"type": "update_loan", "loanId": loan_id, "patch": {"currentPhaseId": None}}]},
        headers=OFFICER_HEADERS,
    )
    assert unassigned.status_code == 200

    loans = client.get("/api/loans", headers=OFFICER_HEADERS).json()
    by_id = {l["id"]: l for l in loans}
    assert by_id[loan_id]["status"] == "submitted"
    assert by_id[loan_id]["currentPhaseId"] is None


def test_wp_v2_014_phase_action_validator_rejects_invalid_payload():
    from src.api.routers.v2_phases_router import _validate_phase_actions

    try:
        _validate_phase_actions([{"type": "add_phase"}])
        assert False, "Expected validator to reject missing required fields"
    except ValueError as e:
        issues = e.args[0]
        assert any("name" in tuple(err.get("loc", ())) for err in issues)


def test_wp_v2_014_execute_phase_actions_create_toggle_and_reorder():
    no_officer = client.post(
        "/api/phases/actions",
        json={"actions": [{"type": "add_phase", "name": "QA Phase"}]},
    )
    assert no_officer.status_code == 403

    phases_before = client.get("/api/phases").json()
    ids_before = [p["id"] for p in phases_before]

    created = client.post(
        "/api/phases/actions",
        json={"actions": [{"type": "add_phase", "name": "QA Phase", "description": "Test-only phase"}]},
        headers=OFFICER_HEADERS,
    )
    assert created.status_code == 200

    phases_after = client.get("/api/phases").json()
    ids_after = [p["id"] for p in phases_after]
    new_ids = [pid for pid in ids_after if pid not in set(ids_before)]
    assert len(new_ids) == 1
    new_phase_id = new_ids[0]

    deactivate = client.post(
        "/api/phases/actions",
        json={"actions": [{"type": "set_phase_active", "phaseId": new_phase_id, "isActive": False}]},
        headers=OFFICER_HEADERS,
    )
    assert deactivate.status_code == 200

    active = client.get("/api/phases/active").json()
    assert all(p["id"] != new_phase_id for p in active)

    reactivate = client.post(
        "/api/phases/actions",
        json={"actions": [{"type": "set_phase_active", "phaseId": new_phase_id, "isActive": True}]},
        headers=OFFICER_HEADERS,
    )
    assert reactivate.status_code == 200

    phases_for_reorder = client.get("/api/phases").json()
    ids_for_reorder = [p["id"] for p in phases_for_reorder]
    assert new_phase_id in ids_for_reorder
    assert len(ids_for_reorder) >= 2

    ids_swapped = ids_for_reorder[:]
    ids_swapped[-1], ids_swapped[-2] = ids_swapped[-2], ids_swapped[-1]

    reorder = client.post(
        "/api/phases/actions",
        json={"actions": [{"type": "reorder_phases", "phaseIds": ids_swapped}]},
        headers=OFFICER_HEADERS,
    )
    assert reorder.status_code == 200

    phases_reordered = client.get("/api/phases").json()
    ids_reordered = [p["id"] for p in phases_reordered]
    assert ids_reordered[-2:] == ids_swapped[-2:]

    restore = client.post(
        "/api/phases/actions",
        json={"actions": [{"type": "reorder_phases", "phaseIds": ids_for_reorder}]},
        headers=OFFICER_HEADERS,
    )
    assert restore.status_code == 200


def test_wp_v2_012_loans_have_null_or_phase_ids_for_pipeline_grouping():
    phases = client.get("/api/phases/active").json()
    assert len(phases) >= 2
    phase_id = phases[0]["id"]

    with _db_session() as db:
        loan_phase = Loan(
            borrower_name="Phase Loan",
            loan_type="Home Loan",
            loan_amount="250000",
            status="draft",
            current_phase_id=phase_id,
        )
        loan_unassigned = Loan(
            borrower_name="Unassigned Loan",
            loan_type="Home Loan",
            loan_amount="250000",
            status="draft",
            current_phase_id=None,
        )
        loan_unknown = Loan(
            borrower_name="Unknown Phase Loan",
            loan_type="Home Loan",
            loan_amount="250000",
            status="draft",
            current_phase_id="non-existent-phase",
        )
        db.add_all([loan_phase, loan_unassigned, loan_unknown])
        db.commit()
        db.refresh(loan_phase)
        db.refresh(loan_unassigned)
        db.refresh(loan_unknown)
        ids = {loan_phase.id, loan_unassigned.id, loan_unknown.id}

    loans = client.get("/api/loans", headers=OFFICER_HEADERS).json()
    by_id = {l["id"]: l for l in loans if l["id"] in ids}
    assert by_id[loan_phase.id]["currentPhaseId"] == phase_id
    assert by_id[loan_unassigned.id]["currentPhaseId"] is None
    assert by_id[loan_unknown.id]["currentPhaseId"] == "non-existent-phase"


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
    def _phase_id(name: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ks-los:v2:phase:{name}"))

    def _product_id(code: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ks-los:v2:product:{code}"))

    from src.api.routers.v2_phases_router import DEFAULT_PHASES
    from src.api.routers.v2_catalog_products_router import DEFAULT_PRODUCTS

    reset = client.post("/admin/seed/v2-baseline?reset=true", headers=OFFICER_HEADERS)
    assert reset.status_code == 200
    baseline = reset.json()
    assert baseline["phases_total"] >= 1
    assert baseline["products_total"] >= 1
    assert baseline["phases_added"] >= 1
    assert baseline["products_added"] >= 1

    phases = client.get("/api/phases").json()
    phases_by_name = {p["name"]: p for p in phases}
    for p in DEFAULT_PHASES:
        seeded = phases_by_name.get(p["name"])
        assert seeded is not None
        assert seeded["id"] == _phase_id(p["name"])

    products = client.get("/api/catalog-products", headers=OFFICER_HEADERS).json()
    products_by_code = {p["code"]: p for p in products}
    for p in DEFAULT_PRODUCTS:
        seeded = products_by_code.get(p["code"])
        assert seeded is not None
        assert seeded["id"] == _product_id(p["code"])

    again = client.post("/admin/seed/v2-baseline", headers=OFFICER_HEADERS)
    assert again.status_code == 200
    payload2 = again.json()
    assert payload2["phases_total"] == baseline["phases_total"]
    assert payload2["products_total"] == baseline["products_total"]
    assert payload2["phases_added"] == 0
    assert payload2["products_added"] == 0


def test_wp_v2_008_intent_summary_schema_rejects_unknown_fields():
    from pydantic import ValidationError
    from src.api.routers.v2_conversations_router import IntentSummary

    IntentSummary.model_validate({"purpose": "home"})

    try:
        IntentSummary.model_validate({"purpose": "home", "unknownKey": "x"})
        assert False, "Expected ValidationError"
    except ValidationError:
        assert True
