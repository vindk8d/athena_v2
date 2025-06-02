"""
Integration tests for the API endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Mock all critical dependencies before any imports
patcher_create_client = patch('src.database.supabase_client.create_client', MagicMock())
patcher_supabase_client = patch('src.database.supabase_client.SupabaseClient', MagicMock())
patcher_settings = patch('src.bot.telegram_bot.get_settings', MagicMock(return_value=MagicMock(
    telegram_bot_token="test_token",
    max_contacts=10
)))
patcher_bot = patch('src.bot.telegram_bot.AthenaTelegramBot', MagicMock())
patcher_handler = patch('src.api.webhook_handler.WebhookHandler', MagicMock())

# Start patches before importing anything
patcher_create_client.start()
patcher_supabase_client.start()
patcher_settings.start()
patcher_bot.start()
patcher_handler.start()

try:
    from fastapi.testclient import TestClient
    from src.api.main import app

    @pytest.fixture
    def test_client():
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    def test_health_check(test_client):
        """Test the health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_telegram_webhook_success(test_client):
        """Test successful webhook processing"""
        response = test_client.post("/webhook", json={"message": {"text": "test"}})
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_telegram_webhook_error(test_client):
        """Test webhook error handling"""
        response = test_client.post("/webhook", json={"invalid": "update"})
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_telegram_webhook_invalid_json(test_client):
        """Test webhook handling with invalid JSON."""
        response = test_client.post("/webhook", content="invalid json")
        assert response.status_code == 422  # FastAPI returns 422 for invalid JSON

    def test_telegram_webhook_missing_body(test_client):
        """Test webhook handling with missing request body."""
        response = test_client.post("/webhook")
        assert response.status_code == 422  # FastAPI returns 422 for missing body

finally:
    # Stop patches
    patcher_create_client.stop()
    patcher_supabase_client.stop()
    patcher_settings.stop()
    patcher_bot.stop()
    patcher_handler.stop() 