import os
import tempfile
import uuid
import base64
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker


DB_PATH = os.path.join(tempfile.gettempdir(), "ks_los_v2_test.db")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["SQLITE_FALLBACK_URL"] = f"sqlite:///{DB_PATH}"
os.environ["DATABASE_URL"] = "postgresql+psycopg://invalid:invalid@localhost:1/invalid"

from src.shared.db import AuditEvent, Conversation, Loan, LoanDocument, LoanPhase, Message, get_engine, init_db, reset_db_for_tests

reset_db_for_tests()

from src.main import app


client = TestClient(app)


OFFICER_HEADERS = {"Authorization": "Bearer loan-officer-access"}

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


def test_v2_phase_detail_includes_knowledge_and_metrics():
    phases = client.get("/api/phases").json()
    assert len(phases) >= 1
    phase_id = phases[0]["id"]

    detail = client.get(f"/api/phases/{phase_id}/detail")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["phase"]["id"] == phase_id
    assert "knowledge" in payload
    assert isinstance(payload["knowledge"]["timeline"], str)
    assert isinstance(payload["knowledge"]["summary"], str)
    assert isinstance(payload["knowledge"]["activities"], list)
    assert isinstance(payload["knowledge"]["documents"], list)
    assert isinstance(payload["knowledge"]["stakeholders"], list)
    assert isinstance(payload["knowledge"]["bottlenecks"], list)
    assert "metrics" in payload
    assert isinstance(payload["metrics"]["loanCount"], int)
    assert isinstance(payload["metrics"]["conversationCount"], int)


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
    assert send_payload["approvalProbability"] is None
    assert isinstance(send_payload["loanRecommendations"], list)
    assert len(send_payload["loanRecommendations"]) >= 1

    send2 = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "loan amount: 350000 USD, my income is 10000 USD a month, im salaried"},
    )
    assert send2.status_code == 200
    send2_payload = send2.json()
    assert isinstance(send2_payload["approvalProbability"]["probability"], float)
    assert 0.0 <= send2_payload["approvalProbability"]["probability"] <= 1.0
    assert send2_payload["approvalProbability"]["band"] in {"low", "medium", "high"}
    assert isinstance(send2_payload["approvalProbability"]["topBlockers"], list)
    assert isinstance(send2_payload["approvalProbability"]["topActions"], list)
    assert len(send2_payload["approvalProbability"]["topBlockers"]) >= 1
    assert len(send2_payload["approvalProbability"]["topActions"]) >= 1
    assert send2_payload["intentAnalysis"]["intentSummary"]["loanAmount"] is not None
    assert send2_payload["intentAnalysis"]["intentSummary"]["monthlyIncome"] is not None

    send3 = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "no, i dont know my credit score"},
    )
    assert send3.status_code == 200
    send3_payload = send3.json()
    assert send3_payload["intentAnalysis"]["intentSummary"]["creditHistory"] == "unknown"

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


def test_v2_income_message_does_not_set_loan_amount():
    create = client.post("/api/conversations", json={})
    conv_id = create.json()["conversation"]["id"]

    send1 = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "I want a home loan to buy a house."})
    assert send1.status_code == 200

    send2 = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "income: 10000 usd/month, salaried, i dont know my credit score"},
    )
    assert send2.status_code == 200
    payload = send2.json()
    intent = payload["intentAnalysis"]["intentSummary"]
    assert intent["monthlyIncome"] is not None
    assert intent.get("loanAmount") is None
    assert intent.get("creditHistory") == "unknown"


def test_wp_v2_020_messages_list_is_deterministic():
    ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    conv_id = "conv-wp-v2-020-ordering"
    with _db_session() as db:
        db.add(Conversation(id=conv_id, status="active", chat_role="borrower"))
        db.add_all(
            [
                Message(id="a", conversation_id=conv_id, role="user", content="first", created_at=ts),
                Message(id="b", conversation_id=conv_id, role="user", content="second", created_at=ts),
            ]
        )
        db.commit()

    rows = client.get(f"/api/conversations/{conv_id}/messages").json()
    ids = [m["id"] for m in rows if m["conversationId"] == conv_id]
    assert ids[:2] == ["a", "b"]


def test_wp_v2_020_phases_list_is_deterministic():
    with _db_session() as db:
        db.add_all(
            [
                LoanPhase(id="a", name="WP-V2-020 A", description=None, sort_order=999, is_active=True),
                LoanPhase(id="b", name="WP-V2-020 B", description=None, sort_order=999, is_active=True),
            ]
        )
        db.commit()

    phases = client.get("/api/phases").json()
    ids = [p["id"] for p in phases]
    assert ids[-2:] == ["a", "b"]

    active = client.get("/api/phases/active").json()
    active_ids = [p["id"] for p in active]
    assert active_ids[-2:] == ["a", "b"]


def test_wp_v2_020_audit_events_are_inspectable_and_ordered():
    ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    with _db_session() as db:
        db.add_all(
            [
                AuditEvent(
                    id="a",
                    event="wp_v2_020",
                    endpoint="/x",
                    status="success",
                    correlation_id="corr-1",
                    meta={"k": "v"},
                    created_at=ts,
                ),
                AuditEvent(
                    id="b",
                    event="wp_v2_020",
                    endpoint="/x",
                    status="success",
                    correlation_id="corr-2",
                    meta={"k": "v"},
                    created_at=ts,
                ),
            ]
        )
        db.commit()

    forbidden = client.get("/observability/audit-events")
    assert forbidden.status_code == 403

    res = client.get("/observability/audit-events?event=wp_v2_020", headers=OFFICER_HEADERS)
    assert res.status_code == 200
    payload = res.json()
    assert isinstance(payload.get("items"), list)
    ids = [e["id"] for e in payload["items"]]
    assert ids[:2] == ["a", "b"]

    res2 = client.get("/observability/audit-events?event=wp_v2_020&correlationId=corr-1", headers=OFFICER_HEADERS)
    assert res2.status_code == 200
    payload2 = res2.json()
    assert [e["id"] for e in payload2["items"]] == ["a"]


def test_v2_debt_consolidation_recommends_personal_loans():
    create = client.post("/api/conversations", json={})
    assert create.status_code == 200
    conv_id = create.json()["conversation"]["id"]

    send = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "I want to consolidate multiple debts into one EMI."},
    )
    assert send.status_code == 200
    payload = send.json()
    assert payload["message"]["role"] == "assistant"
    assert payload["intentAnalysis"]["intentSummary"]["purpose"] == "debt_consolidation"
    assert isinstance(payload["loanRecommendations"], list)
    assert len(payload["loanRecommendations"]) >= 1
    assert payload["loanRecommendations"][0]["type"] == "personal_loan"


def test_v2_borrower_chat_accepts_numeric_intent_values():
    create = client.post("/api/conversations", json={})
    assert create.status_code == 200
    conv_id = create.json()["conversation"]["id"]

    send = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Home loan. 10000usd/month. No debts."},
    )
    assert send.status_code == 200
    payload = send.json()
    summary = payload["intentAnalysis"]["intentSummary"]
    assert summary["purpose"] == "home"
    assert summary["monthlyIncome"] == "10000"


def test_v2_borrower_chat_converges_to_final_recommendation():
    create = client.post("/api/conversations", json={})
    assert create.status_code == 200
    conv_id = create.json()["conversation"]["id"]

    send1 = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "I want to buy a house."})
    assert send1.status_code == 200

    send2 = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "House price 35000 USD, down payment 10000."})
    assert send2.status_code == 200

    send3 = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "10000usd/month, no debts, 10 years."})
    assert send3.status_code == 200
    payload3 = send3.json()
    assert isinstance(payload3.get("loanRecommendations"), list)
    assert len(payload3["loanRecommendations"]) >= 1
    meta = payload3["message"]["metadata"]
    assert isinstance(meta.get("finalRecommendation"), dict)


def test_wp_v2_008_intent_summary_filters_unknown_keys():
    from src.api.routers.v2_conversations_router import IntentSummary, _merge_intent

    prev = {"purpose": "home", "evil": "x"}
    merged = _merge_intent(prev, IntentSummary(monthlyIncome="5000"))
    assert "evil" not in merged


def test_wp_v2_015_approval_probability_navigator_schema_is_stable():
    from src.api.routers.v2_conversations_router import _compute_approval_probability, ApprovalProbabilityNavigator

    payload = _compute_approval_probability(
        {
            "creditHistory": "750",
            "monthlyIncome": "5000",
            "existingDebts": "1000",
            "loanAmount": "150000",
        }
    )
    validated = ApprovalProbabilityNavigator.model_validate(payload)
    assert 0.0 <= float(validated.probability) <= 1.0
    assert validated.band in {"low", "medium", "high"}
    assert len(validated.topBlockers) <= 3
    assert len(validated.topActions) <= 3
    assert validated.method


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
    assert idx2 == idx1


def test_wp_v2_020_document_ocr_endpoint_accepts_uploads():
    import shutil
    from pathlib import Path

    created = client.post("/api/conversations", json={})
    assert created.status_code == 200
    conv_id = created.json()["conversation"]["id"]

    root = Path(__file__).resolve().parents[2]
    png_path = root / "data" / "passport-example.png"
    pdf_path = root / "data" / "job-letter.pdf"

    with open(png_path, "rb") as f:
        r = client.post(
            f"/api/conversations/{conv_id}/documents/ocr",
            files={"file": (png_path.name, f, "image/png")},
            data={"label": "Passport"},
        )
    if shutil.which("tesseract"):
        assert r.status_code == 200
        payload = r.json()
        assert payload.get("engine") == "tesseract"
        assert payload.get("fileName") == png_path.name
        assert "preview" in payload
    else:
        assert r.status_code == 501

    with open(pdf_path, "rb") as f:
        r2 = client.post(
            f"/api/conversations/{conv_id}/documents/ocr",
            files={"file": (pdf_path.name, f, "application/pdf")},
            data={"label": "Job Letter"},
        )
    if shutil.which("pdftotext"):
        assert r2.status_code == 200
        payload2 = r2.json()
        assert payload2.get("engine") == "pdftotext"
        assert payload2.get("fileName") == pdf_path.name
        assert "preview" in payload2
    else:
        assert r2.status_code == 501


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


def test_wp_v2_017_underwriting_memo_generates_persists_and_has_guardrails():
    created = client.post(
        "/api/loans",
        json={
            "borrowerName": "Memo Borrower",
            "loanType": "Home Loan",
            "loanAmount": "250000",
            "catalogProductCode": "HL-PUR-001",
            "monthlyIncome": "8000",
            "existingDebts": "1500",
            "creditScore": "750",
            "propertyValue": "400000",
        },
        headers=OFFICER_HEADERS,
    )
    assert created.status_code == 200
    loan = created.json()
    loan_id = loan["id"]

    generated = client.post(f"/api/loans/{loan_id}/underwriting-memo", headers=OFFICER_HEADERS)
    assert generated.status_code == 200
    updated = generated.json()
    assert updated["id"] == loan_id
    assert updated["underwritingMemo"] is not None
    memo = updated["underwritingMemo"]
    assert memo["loanId"] == loan_id
    assert memo["method"] == "rules_v1"
    assert isinstance(memo.get("sections"), list)
    assert len(memo["sections"]) >= 3
    assert "disclaimer" in memo and isinstance(memo["disclaimer"], str)

    import json as _json

    text = _json.dumps(memo).lower()
    assert "guarantee" not in text
    assert "will be approved" not in text
    assert "100%" not in text

    fetched = client.get(f"/api/loans/{loan_id}/underwriting-memo", headers=OFFICER_HEADERS)
    assert fetched.status_code == 200
    fetched_memo = fetched.json()
    assert fetched_memo["loanId"] == loan_id
    assert fetched_memo["generatedAt"] == memo["generatedAt"]

    fetched_loan = client.get(f"/api/loans/{loan_id}", headers=OFFICER_HEADERS)
    assert fetched_loan.status_code == 200
    fetched_payload = fetched_loan.json()
    assert fetched_payload["underwritingMemo"]["loanId"] == loan_id


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


def test_wp_v2_019_error_envelope_includes_correlation_id():
    cid = "test-correlation-id-123"
    r = client.get(
        "/api/loans/does-not-exist",
        headers={**OFFICER_HEADERS, "X-Correlation-ID": cid},
    )
    assert r.status_code == 404
    payload = r.json()
    assert "detail" in payload
    assert payload["correlationId"] == cid
    assert r.headers.get("X-Correlation-ID") == cid


def test_wp_v2_019_audit_events_persist_for_v2_writes():
    cid = "test-correlation-id-audit-1"
    create = client.post(
        "/api/loans",
        json={
            "borrowerName": "Audit Test Borrower",
            "loanType": "Home Loan",
            "loanAmount": "250000",
            "catalogProductCode": "HL-PUR-001",
        },
        headers={**OFFICER_HEADERS, "X-Correlation-ID": cid},
    )
    assert create.status_code == 200
    loan_id = create.json()["id"]

    with _db_session() as db:
        rows = (
            db.execute(
                select(AuditEvent).where(
                    AuditEvent.correlation_id == cid,
                    AuditEvent.event == "v2_loan_create",
                    AuditEvent.status == "success",
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) >= 1
        assert rows[-1].meta is not None
        assert rows[-1].meta.get("loanId") == loan_id


def test_ui2_documents_endpoints_roundtrip_and_enforce_conversation_scoping():
    create = client.post("/api/conversations", json={})
    assert create.status_code == 200
    conv_id = create.json()["conversation"]["id"]
    create2 = client.post("/api/conversations", json={})
    assert create2.status_code == 200
    other_conv_id = create2.json()["conversation"]["id"]

    with _db_session() as db:
        loan = Loan(
            borrower_name="UI2 Borrower",
            loan_type="Home Loan",
            loan_amount="250000",
            status="draft",
            conversation_id=conv_id,
        )
        db.add(loan)
        db.commit()
        db.refresh(loan)
        loan_id = loan.id

    list_denied = client.get(f"/api/documents/loan/{loan_id}")
    assert list_denied.status_code == 403
    list_wrong_conv = client.get(f"/api/documents/loan/{loan_id}", headers={"X-Conversation-ID": other_conv_id})
    assert list_wrong_conv.status_code == 403

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/aa2x0QAAAAASUVORK5CYII=",
        validate=True,
    )

    upload = client.post(
        "/api/documents/upload",
        data={"loanId": loan_id, "category": "identity", "documentType": "national_id"},
        files={"file": ("id.png", png_bytes, "image/png")},
        headers={"X-Conversation-ID": conv_id},
    )
    assert upload.status_code == 200
    doc = upload.json()
    assert doc["loanId"] == loan_id
    assert doc["category"] == "identity"
    assert doc["documentType"] == "national_id"
    assert "filePath" not in doc

    listed = client.get(f"/api/documents/loan/{loan_id}", headers={"X-Conversation-ID": conv_id})
    assert listed.status_code == 200
    docs = listed.json()
    assert len(docs) == 1
    doc_id = docs[0]["id"]

    download_wrong_conv = client.get(f"/api/documents/{doc_id}/download", headers={"X-Conversation-ID": other_conv_id})
    assert download_wrong_conv.status_code == 403

    downloaded = client.get(f"/api/documents/{doc_id}/download", headers={"X-Conversation-ID": conv_id})
    assert downloaded.status_code == 200
    assert downloaded.headers.get("content-type") in {"image/png", "image/png; charset=utf-8"}
    assert downloaded.content == png_bytes

    deleted = client.delete(f"/api/documents/{doc_id}", headers={"X-Conversation-ID": conv_id})
    assert deleted.status_code == 200
    assert deleted.json().get("success") is True

    listed2 = client.get(f"/api/documents/loan/{loan_id}", headers={"X-Conversation-ID": conv_id})
    assert listed2.status_code == 200
    assert listed2.json() == []


def test_ui2_documents_review_requires_officer_and_persists_status_and_note():
    create = client.post("/api/conversations", json={})
    assert create.status_code == 200
    conv_id = create.json()["conversation"]["id"]

    with _db_session() as db:
        loan = Loan(
            borrower_name="UI2 Borrower",
            loan_type="Home Loan",
            loan_amount="250000",
            status="draft",
            conversation_id=conv_id,
        )
        db.add(loan)
        db.commit()
        db.refresh(loan)
        loan_id = loan.id

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/aa2x0QAAAAASUVORK5CYII=",
        validate=True,
    )
    upload = client.post(
        "/api/documents/upload",
        data={"loanId": loan_id, "category": "identity", "documentType": "national_id"},
        files={"file": ("id.png", png_bytes, "image/png")},
        headers={"X-Conversation-ID": conv_id},
    )
    assert upload.status_code == 200
    doc_id = upload.json()["id"]

    denied = client.patch(f"/api/documents/{doc_id}/review", json={"status": "approved", "reviewNote": "ok"})
    assert denied.status_code == 403

    reviewed = client.patch(
        f"/api/documents/{doc_id}/review",
        json={"status": "approved", "reviewNote": "ok"},
        headers=OFFICER_HEADERS,
    )
    assert reviewed.status_code == 200
    payload = reviewed.json()
    assert payload["id"] == doc_id
    assert payload["status"] == "approved"
    assert payload["reviewNote"] == "ok"


def test_ui2_accept_terms_persists_disbursement_and_emits_message():
    create = client.post("/api/conversations", json={})
    assert create.status_code == 200
    conv_id = create.json()["conversation"]["id"]
    create2 = client.post("/api/conversations", json={})
    assert create2.status_code == 200
    other_conv_id = create2.json()["conversation"]["id"]

    with _db_session() as db:
        loan = Loan(
            borrower_name="UI2 Borrower",
            loan_type="Home Loan",
            loan_amount="250000",
            status="draft",
            conversation_id=conv_id,
        )
        db.add(loan)
        db.commit()
        db.refresh(loan)
        loan_id = loan.id

    signature_data_url = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/aa2x0QAAAAASUVORK5CYII="
    )
    accepted = client.post(
        f"/api/loans/{loan_id}/accept-terms",
        json={"signature": signature_data_url},
        headers={"X-Conversation-ID": conv_id},
    )
    assert accepted.status_code == 200
    payload = accepted.json()
    assert payload["success"] is True
    assert "disbursement" in payload
    assert payload["disbursement"]["status"] == "disbursed"
    assert payload["disbursement"]["amount"] == "250000"
    assert "approval" in payload

    with _db_session() as db:
        refreshed = db.get(Loan, loan_id)
        assert refreshed is not None
        assert refreshed.terms_accepted_at is not None
        assert refreshed.terms_signature_path is not None
        assert refreshed.disbursement is not None

        msgs = (
            db.execute(select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at.desc(), Message.id.desc()))
            .scalars()
            .all()
        )
        assert any(
            m.metadata_json
            and isinstance(m.metadata_json.get("loanApplication"), dict)
            and m.metadata_json["loanApplication"].get("stpCompleted") is True
            and m.metadata_json["loanApplication"].get("disbursement") is not None
            for m in msgs
        )

    denied = client.post(
        f"/api/loans/{loan_id}/accept-terms",
        json={"signature": signature_data_url},
        headers={"X-Conversation-ID": other_conv_id},
    )
    assert denied.status_code == 403


def test_ui2_stp_process_emits_offer_message_and_status_payload():
    create = client.post("/api/conversations", json={})
    assert create.status_code == 200
    conv_id = create.json()["conversation"]["id"]

    with _db_session() as db:
        loan = Loan(
            borrower_name="UI2 STP Borrower",
            loan_type="Home Loan",
            loan_amount="250000",
            status="draft",
            conversation_id=conv_id,
            monthly_income="8000",
            existing_debts="1500",
            credit_score="750",
        )
        db.add(loan)
        db.commit()
        db.refresh(loan)
        loan_id = loan.id

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/aa2x0QAAAAASUVORK5CYII=",
        validate=True,
    )
    upload = client.post(
        "/api/documents/upload",
        data={"loanId": loan_id, "category": "identity", "documentType": "national_id"},
        files={"file": ("id.png", png_bytes, "image/png")},
        headers={"X-Conversation-ID": conv_id},
    )
    assert upload.status_code == 200
    upload2 = client.post(
        "/api/documents/upload",
        data={"loanId": loan_id, "category": "income_salaried", "documentType": "job_letter"},
        files={"file": ("job-letter.pdf", png_bytes, "application/pdf")},
        headers={"X-Conversation-ID": conv_id},
    )
    assert upload2.status_code == 200

    processed = client.post(f"/api/loans/{loan_id}/stp-process", headers={"X-Conversation-ID": conv_id})
    assert processed.status_code == 200
    processed_payload = processed.json()
    assert processed_payload["status"] in {"awaiting_acceptance", "awaiting_documents"}

    status = client.get(f"/api/loans/{loan_id}/stp-status", headers={"X-Conversation-ID": conv_id})
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["status"] in {"awaiting_acceptance", "awaiting_documents"}
    assert isinstance(status_payload.get("log"), list)
    if status_payload["status"] == "awaiting_acceptance":
        assert isinstance(status_payload.get("payload"), dict)
        assert status_payload["payload"].get("awaitingAcceptance") is True
        assert isinstance(status_payload["payload"].get("stpSteps"), list)
        assert isinstance(status_payload["payload"].get("approval"), dict)

    with _db_session() as db:
        refreshed = db.get(Loan, loan_id)
        assert refreshed is not None
        assert (refreshed.stp_processing_status or "").lower() in {"awaiting_acceptance", "awaiting_documents"}
        if (refreshed.stp_processing_status or "").lower() == "awaiting_acceptance":
            assert refreshed.stp_payload is not None
            assert refreshed.interest_rate is not None
            assert refreshed.tenure is not None
            assert refreshed.monthly_emi is not None

        msgs = (
            db.execute(select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at.desc(), Message.id.desc()))
            .scalars()
            .all()
        )
        if (refreshed.stp_processing_status or "").lower() == "awaiting_acceptance":
            assert any(
                m.metadata_json
                and m.metadata_json.get("type") == "stp_offer"
                and isinstance(m.metadata_json.get("loanApplication"), dict)
                and m.metadata_json["loanApplication"].get("awaitingAcceptance") is True
                for m in msgs
            )
