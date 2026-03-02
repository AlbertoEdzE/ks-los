from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_suggestions_and_identity_and_progress():
    s = client.get("/chat/suggestions?prefix=Jo&limit=5")
    assert s.status_code == 200
    data = s.json()
    assert "items" in data
    i = client.post("/chat/identity", json={"name": "John", "surname": "Doe"})
    assert i.status_code == 200
    full = i.json()["full_name"]
    assert full == "John Doe"
    st = client.get(f"/chat/progress/stream?full_name={full}", headers={"Accept": "text/event-stream"})
    assert st.status_code == 200
