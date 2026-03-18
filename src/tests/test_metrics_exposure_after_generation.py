from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)
ADMIN_HEADERS = {"Authorization": "Bearer admin-access"}

def test_metrics_exposure_after_synthetic_generation():
    # Start a small generation
    start = client.post("/admin/synthetic/generate", headers=ADMIN_HEADERS, json={"count": 5, "territory": "ECCU", "archetype": "PRIME_ESTABLISHED"})
    assert start.status_code == 200
    # Poll until completed
    for _ in range(50):
        st = client.get("/admin/synthetic/status", headers=ADMIN_HEADERS).json()
        if st.get("status") == "completed":
            break
    # Fetch metrics and verify fairness counters exist
    m = client.get("/metrics")
    assert m.status_code == 200
    text = m.text
    assert "approvals_total" in text
    assert "declines_total" in text
