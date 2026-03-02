import pytest
from fastapi.testclient import TestClient
from src.main import app
import redis
from unittest.mock import MagicMock, patch

client = TestClient(app)

def test_suggestions_endpoint_no_prefix():
    # Mock Redis to avoid actual connection or pre-seed data
    with patch('src.api.routers.chat_support_router.r') as mock_redis:
        # Mock get returning None to trigger generation
        mock_redis.get.return_value = None
        
        response = client.get("/chat/suggestions")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        items = data["items"]
        assert len(items) > 0
        # Check structure
        first = items[0]
        assert "label" in first
        assert "text" in first
        assert "(" in first["label"] # Check for territory in label

def test_suggestions_endpoint_with_prefix():
    with patch('src.api.routers.chat_support_router.r') as mock_redis:
        # Mock lrange for autocomplete
        mock_redis.lrange.return_value = ["Ana Garcia", "Bob Smith"]
        
        response = client.get("/chat/suggestions?prefix=Ana")
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        assert "Ana Garcia" in items

def test_progress_stream():
    with patch('src.api.routers.chat_support_router.r'):
        response = client.get("/chat/progress/stream?full_name=TestUser")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        # TestClient typically consumes the stream into text
        text = response.text
        assert "data: " in text
        assert "database_lookup" in text
        assert "aggregation" in text
