import pytest
import time
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_reproduce_network_error_scenario():
    """
    Test scenario: count=100, Territory=ECCU, Archetype=standard.
    This mimics the user's reproduction steps.
    """
    payload = {
        "count": 100,
        "territory": "ECCU",
        "archetype": "standard",
        "seed": "0"
    }
    
    # 1. Start generation
    response = client.post("/admin/synthetic/generate", json=payload)
    assert response.status_code == 200, f"Failed to start generation: {response.text}"
    data = response.json()
    assert data["accepted"] is True
    
    # 2. Poll status until completion
    max_retries = 50
    completed = False
    
    for _ in range(max_retries):
        status_resp = client.get("/admin/synthetic/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        
        if status_data["status"] == "completed":
            completed = True
            break
        elif status_data["status"] == "error":
            pytest.fail(f"Generation failed with error: {status_data.get('message')}")
            
        time.sleep(0.5)
        
    assert completed, "Generation did not complete within timeout"
    
    # 3. Validate output
    validate_resp = client.post("/admin/synthetic/validate")
    assert validate_resp.status_code == 200
    validate_data = validate_resp.json()
    # Check for expected validation keys
    assert "total" in validate_data
    assert validate_data["total"] == 100
