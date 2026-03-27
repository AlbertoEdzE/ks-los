from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app
from src.agents.graph_state import create_initial_state

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_security_headers_present_on_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "no-referrer"
    assert response.headers.get("Permissions-Policy") is not None
    assert response.headers.get("X-Correlation-ID") is not None

def test_v3_create_conversation_success():
    response = client.post(
        "/api/v3/conversations/",
        json={"session_id": "test-session-123", "borrower_name": "Jane Doe"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversation" in data
    assert data["conversation"]["id"] == "test-session-123"
    assert data["conversation"]["borrowerName"] == "Jane Doe"


def test_v3_send_message_success():
    session_id = "test-session-v3-send"
    state = create_initial_state(session_id=session_id)

    def advisory_process(s):
        s.add_message("assistant", "Stub response")
        return s

    with patch("src.api.routers.v3_agentic_conversations_router.get_or_create_state", return_value=state), patch(
        "src.api.routers.v3_agentic_conversations_router.update_state", return_value=True
    ), patch("src.api.routers.v3_agentic_conversations_router.RepairNode") as MockRepairNode, patch(
        "src.api.routers.v3_agentic_conversations_router.RAGNode"
    ) as MockRAGNode, patch(
        "src.api.routers.v3_agentic_conversations_router.AdvisoryNode"
    ) as MockAdvisoryNode, patch(
        "src.api.routers.v3_agentic_conversations_router.EscalationNode"
    ) as MockEscalationNode:
        for node_cls in (MockRepairNode, MockRAGNode, MockEscalationNode):
            node = MagicMock()
            node.process.side_effect = lambda s: s
            node_cls.return_value = node

        advisory_node = MagicMock()
        advisory_node.process.side_effect = advisory_process
        MockAdvisoryNode.return_value = advisory_node

        response = client.post(
            f"/api/v3/conversations/{session_id}/messages",
            json={"content": "Hello"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["response"] == "Stub response"
    assert data["mode"] == "advisory"
