import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

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
