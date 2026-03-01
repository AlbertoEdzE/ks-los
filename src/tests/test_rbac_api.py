import os
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture(autouse=True)
def set_api_keys_env(monkeypatch):
    monkeypatch.setenv("API_KEYS", "opkey:operator,viewkey:viewer,adminkey:admin")
    monkeypatch.setenv("ENFORCE_RBAC", "1")
    # reload API_KEYS in module
    from src.shared import auth
    prev = auth.ENFORCE_RBAC
    auth.API_KEYS = auth._load_api_keys()
    auth.ENFORCE_RBAC = True
    yield
    auth.ENFORCE_RBAC = prev

def test_training_requires_operator_key():
    client = TestClient(app)
    r = client.post("/training/plan", json={"rationale": "test"})
    assert r.status_code == 401
    r2 = client.post("/training/plan", json={"rationale": "test"}, headers={"X-API-Key": "opkey"})
    assert r2.status_code == 200

def test_explain_allows_viewer_key():
    client = TestClient(app)
    # Build minimal profile
    profile = {
        "metadata": {"source":"synthetic","query_timestamp":"2024-01-01T00:00:00","territory":"AG","consent_token":"t","synthetic_archetype":"PRIME_ESTABLISHED","synthetic_seed_hash":"h"},
        "identity": {"full_name":"a","date_of_birth":"1990-01-01","national_id_hash":"h","address":{"line1":"x","city":"c","territory":"Antigua and Barbuda","territory_code":"AG"}},
        "summary": {"credit_score":700,"score_band":"GOOD","total_accounts":3,"open_accounts":3,"closed_accounts":0,"total_credit_limit_xcd":10000,"total_current_balance_xcd":2000,"utilization_ratio":0.2,"total_past_due_xcd":0,"months_oldest_account":60,"months_newest_account":6,"derogatory_marks":0,"thin_file":False},
        "payment_behavior": {"on_time_payments_pct":0.9,"late_30_days_count":0,"late_60_days_count":0,"late_90_plus_days_count":0,"charge_offs":0,"collections":0,"worst_payment_status_ever":"OK","payment_history_24m":"1"*24},
        "trade_lines": [],
        "inquiries": [],
        "flags": {"has_bankruptcy":False,"has_foreclosure":False,"has_active_collections":False,"is_deceased":False,"fraud_alert":False}
    }
    r = client.post("/explain/inference", json={"profile": profile}, headers={"X-API-Key": "viewkey"})
    assert r.status_code == 200
