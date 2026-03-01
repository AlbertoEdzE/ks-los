import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_generate_plan_and_execute_training():
    # Generate plan
    r = client.post("/training/plan", json={"rationale": "Periodic refresh"})
    assert r.status_code == 200
    plan = r.json()["plan"]
    assert "hyperparameters" in plan
    assert "n_samples" in plan
    # Execute training
    r2 = client.post("/training/execute", json=plan)
    assert r2.status_code == 200
    result = r2.json()["result"]
    assert "auc" in result
