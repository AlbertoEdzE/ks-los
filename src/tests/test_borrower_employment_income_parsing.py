from fastapi.testclient import TestClient

from src.main import app
from src.agents.graph_state import create_initial_state
from src.agents.structured_parser import IntentAnalysis
from src.agents.agent_tools.intent_extractor import IntentExtractionResult


def test_borrower_combined_employment_and_income_message_is_parsed(monkeypatch):
    client = TestClient(app)
    session_id = "test-session-employment-income"
    state = create_initial_state(session_id=session_id)

    def fake_get_or_create_state(_session_id: str):
        assert _session_id == session_id
        return state

    def fake_update_state(_state):
        return True

    def fake_intent_run(self, conversation_history, session_id=None):
        last_user = ""
        for m in reversed(conversation_history):
            if m.get("role") == "user":
                last_user = m.get("content") or ""
                break
        lower = last_user.lower()

        ctx = IntentAnalysis()
        if "home loan" in lower or "buy a house" in lower:
            ctx.purpose = "home_purchase"
        if lower.strip() == "alberto":
            ctx.borrower_name = "Alberto"
        return IntentExtractionResult(context=ctx, confidence=0.9, field_confidence={}).model_dump_json()

    monkeypatch.setattr("src.api.routers.v3_agentic_conversations_router.get_or_create_state", fake_get_or_create_state)
    monkeypatch.setattr("src.api.routers.v3_agentic_conversations_router.update_state", fake_update_state)
    monkeypatch.setattr("src.agents.agent_tools.intent_extractor.IntentExtractorTool._run", fake_intent_run)

    resp = client.post(f"/api/v3/conversations/{session_id}/messages", json={"content": "I want a home loan to buy a house."})
    assert resp.status_code == 200

    resp = client.post(f"/api/v3/conversations/{session_id}/messages", json={"content": "Alberto"})
    assert resp.status_code == 200

    resp = client.post(f"/api/v3/conversations/{session_id}/messages", json={"content": "350000, 23%"})
    assert resp.status_code == 200

    resp = client.post(f"/api/v3/conversations/{session_id}/messages", json={"content": "employeed, 10000"})
    assert resp.status_code == 200
    data = resp.json()
    text = (data.get("response") or "").lower()

    assert "monthly income" not in text
    assert ("looking to borrow" in text) or ("loan repayments" in text) or ("monthly commitments" in text)

