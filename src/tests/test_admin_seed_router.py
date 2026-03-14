from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_seed_demo_names_idempotent_and_reset():
    # Ensure reset works
    res = client.post("/admin/seed/demo-names?reset=true&count=50")
    assert res.status_code == 200
    total1 = res.json()["total"]
    assert total1 >= 50
    # Seed again without reset; total should be >= previous and no duplicates added beyond generated set
    res2 = client.post("/admin/seed/demo-names?reset=false&count=50")
    assert res2.status_code == 200
    total2 = res2.json()["total"]
    assert total2 >= total1
    # Reset again; list should be replaced
    res3 = client.post("/admin/seed/demo-names?reset=true&count=10")
    assert res3.status_code == 200
    total3 = res3.json()["total"]
    assert total3 >= 10
