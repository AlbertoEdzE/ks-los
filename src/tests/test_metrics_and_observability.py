import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)
OFFICER_HEADERS = {"x-officer-role": "loan-officer-access"}

def test_metrics_endpoint():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "requests_total" in r.text

def test_observability_summary():
    r = client.get("/observability/summary")
    assert r.status_code == 200
    data = r.json()
    assert "training_runs" in data
    assert "risk_inferences" in data
    assert "mlflow_url" in data


def test_v2_endpoints_emit_request_metrics():
    client.get("/api/phases")
    client.get("/api/catalog-products", headers=OFFICER_HEADERS)
    metrics = client.get("/metrics").text
    assert 'requests_total{endpoint="/api/phases"}' in metrics
    assert 'requests_total{endpoint="/api/catalog-products"}' in metrics


def test_v2_errors_emit_error_metrics():
    missing = client.get("/api/loans/does-not-exist", headers=OFFICER_HEADERS)
    assert missing.status_code == 404
    metrics = client.get("/metrics").text
    assert 'request_errors_total{endpoint="/api/loans/{loan_id}"}' in metrics
