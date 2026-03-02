from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_suggestions_toggle():
  r = client.get("/admin/config/suggestions_enabled")
  assert r.status_code == 200
  val = r.json()["value"]
  # Flip value
  s = client.post(f"/admin/config/suggestions_enabled?value={(not val)}")
  assert s.status_code == 200
  new_val = s.json()["value"]
  assert new_val != val
  # Flip back
  s2 = client.post(f"/admin/config/suggestions_enabled?value={val}")
  assert s2.status_code == 200
  back = s2.json()["value"]
  assert back == val
