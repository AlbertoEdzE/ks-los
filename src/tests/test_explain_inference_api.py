from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_explain_inference_works():
    gen = client.post("/scdg/generate", json={"age": 32, "territory": "ECCU", "scenario_type": "PRIME_ESTABLISHED"})
    assert gen.status_code == 200
    profile = gen.json()
    exp = client.post("/explain/inference", json={"profile": profile})
    assert exp.status_code == 200
    data = exp.json()
    assert "score" in data
    assert "feature_values" in data
