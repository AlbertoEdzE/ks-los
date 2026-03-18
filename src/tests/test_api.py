from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from src.main import app

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

@patch("src.api.routers.agent_router.agent_app")
def test_chat_endpoint_success(mock_agent_app):
    """Test the chat endpoint with a successful response."""
    # Mock the graph response
    # endpoint calls await agent_app.ainvoke(inputs)
    mock_agent_app.ainvoke = AsyncMock()
    
    # Mock return value structure
    # model_dump is synchronous, so use MagicMock
    mock_profile = MagicMock()
    mock_profile.model_dump.return_value = {"name": "John Doe", "score": 750}
    
    # Simple object to mimic AIMessage
    class MockAIMessage:
        content = "Here is the profile..."
        
    mock_agent_app.ainvoke.return_value = {
        "messages": [
            {"type": "human", "content": "Generate a profile"},
            MockAIMessage()
        ],
        "credit_profile": mock_profile,
        "risk_score": 750.0,
        "risk_decision": "APPROVED",
        "risk_reasoning": "Score above 720",
        "advice": "Approve"
    }

    payload = {
        "message": "Generate a profile",
        "session_id": "test-session-123"
    }
    
    response = client.post("/agent/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "credit_profile" in data
    assert data["response"] == "Here is the profile..."
    assert data["credit_profile"]["name"] == "John Doe"
    assert data["risk_score"] == 750.0
    assert data["risk_decision"] == "APPROVED"

@patch("src.api.routers.agent_router.agent_app")
def test_chat_endpoint_error(mock_agent_app):
    """Test the chat endpoint handling internal errors."""
    mock_agent_app.ainvoke = AsyncMock()
    mock_agent_app.ainvoke.side_effect = Exception("Internal Graph Error")

    payload = {
        "message": "Crash me",
        "session_id": "test-session-error"
    }
    
    response = client.post("/agent/chat", json=payload)
    
    # Depending on how exception handlers are set up, this might be 500
    assert response.status_code == 500
    assert "detail" in response.json()

def test_chat_endpoint_invalid_payload():
    """Test the chat endpoint with missing required fields."""
    payload = {
        "session_id": "test-session-123"
        # Missing 'message'
    }
    
    response = client.post("/agent/chat", json=payload)
    
    assert response.status_code == 422
