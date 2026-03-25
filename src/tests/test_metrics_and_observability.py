import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)
OFFICER_HEADERS = {"Authorization": "Bearer loan-officer-access"}

def test_metrics_endpoint():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "requests_total" in r.text

def test_observability_summary():
    r = client.get("/observability/summary", headers=OFFICER_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "training_runs" in data
    assert "risk_inferences" in data
    assert "mlflow_url" in data


def test_v2_endpoints_emit_request_metrics():
    client.get("/api/phases")
    client.get("/api/catalog-products", headers=OFFICER_HEADERS)
    client.get("/api/conversations", headers=OFFICER_HEADERS)
    metrics = client.get("/metrics").text
    assert 'requests_total{endpoint="/api/phases"}' in metrics
    assert 'requests_total{endpoint="/api/catalog-products"}' in metrics
    assert 'requests_total{endpoint="/api/conversations"}' in metrics


def test_v2_errors_emit_error_metrics():
    missing = client.get("/api/loans/does-not-exist", headers=OFFICER_HEADERS)
    assert missing.status_code == 404
    metrics = client.get("/metrics").text
    assert 'request_errors_total{endpoint="/api/loans/{loan_id}"}' in metrics


def test_borrower_application_endpoints():
    created = client.post(
        "/api/borrower/applications",
        json={
            "borrowerName": "Test Borrower",
            "borrowerEmail": "test@example.com",
            "borrowerPhone": "555-0100",
            "loanType": "Home Loan",
            "loanAmount": "250000",
        },
    )
    assert created.status_code == 200
    payload = created.json()
    conv_id = payload.get("conversationId")
    loan = payload.get("loan") or {}
    loan_id = loan.get("id")
    assert isinstance(conv_id, str) and conv_id
    assert isinstance(loan_id, str) and loan_id

    listed = client.get("/api/borrower/applications", headers={"X-Conversation-ID": conv_id})
    assert listed.status_code == 200
    rows = listed.json()
    assert any(r.get("id") == loan_id for r in rows)

    fetched = client.get(f"/api/borrower/applications/{loan_id}", headers={"X-Conversation-ID": conv_id})
    assert fetched.status_code == 200
    assert fetched.json().get("id") == loan_id
