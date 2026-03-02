import json
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_generation_and_status_and_validate():
    r = client.post("/admin/synthetic/generate", json={"count": 10, "territory": "ECCU"})
    assert r.status_code == 200
    # Poll status until completed
    for _ in range(200):
        s = client.get("/admin/synthetic/status")
        assert s.status_code == 200
        data = s.json()
        assert "progress" in data
        if data["status"] in ("completed", "error"):
            break
    assert data["status"] == "completed"
    v = client.post("/admin/synthetic/validate")
    assert v.status_code == 200
    summary = v.json()
    assert summary["total"] == 10
    assert 0 <= summary["approval_rate"] <= 1
