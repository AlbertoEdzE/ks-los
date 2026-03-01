import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_run_drift_and_fetch_report():
    r = client.post("/training/drift")
    assert r.status_code == 200
    data = r.json()
    assert "report_endpoint" in data
    r2 = client.get(data["report_endpoint"])
    assert r2.status_code == 200
    assert "<html" in r2.text or "<!DOCTYPE html" in r2.text
