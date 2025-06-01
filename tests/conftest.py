"""
Shared pytest fixtures for Athena Digital Executive Assistant tests.
"""

import asyncio
import os
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Set test environment variables before importing app modules
os.environ["ENVIRONMENT"] = "testing"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test_anon_key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test_service_key"
os.environ["TELEGRAM_BOT_TOKEN"] = "test:telegram_token"
os.environ["OPENAI_API_KEY"] = "sk-test-openai-key"
os.environ["GOOGLE_CLIENT_ID"] = "test_google_client_id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test_google_client_secret"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from src.config.settings import Settings
    
    settings = Settings()
    # Override with test values
    settings._environment = "testing"
    settings._debug = True
    return settings


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    client = Mock()
    
    # Mock table operations
    table_mock = Mock()
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.execute.return_value = Mock(data=[])
    
    client.table.return_value = table_mock
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = Mock()
    
    # Mock chat completion response
    completion_mock = Mock()
    completion_mock.choices = [
        Mock(message=Mock(content="Hello! I'm Athena, your digital assistant."))
    ]
    
    client.chat.completions.create.return_value = completion_mock
    return client


@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot for testing."""
    bot = AsyncMock()
    
    # Mock common bot methods
    bot.send_message = AsyncMock(return_value=Mock(message_id=123))
    bot.get_me = AsyncMock(return_value=Mock(username="athena_test_bot"))
    bot.set_webhook = AsyncMock(return_value=True)
    bot.delete_webhook = AsyncMock(return_value=True)
    
    return bot


@pytest.fixture
def mock_google_calendar():
    """Mock Google Calendar service for testing."""
    service = Mock()
    
    # Mock calendar events
    events_mock = Mock()
    events_mock.list.return_value.execute.return_value = {
        "items": [
            {
                "id": "test_event_1",
                "summary": "Test Meeting",
                "start": {"dateTime": "2024-01-15T10:00:00Z"},
                "end": {"dateTime": "2024-01-15T11:00:00Z"}
            }
        ]
    }
    events_mock.insert.return_value.execute.return_value = {
        "id": "new_event_123",
        "htmlLink": "https://calendar.google.com/event?eid=test"
    }
    
    service.events.return_value = events_mock
    return service


@pytest.fixture
def sample_contact_data():
    """Sample contact data for testing."""
    return {
        "id": "test-contact-123",
        "name": "John Doe",
        "email": "john.doe@example.com",
        "telegram_id": "12345678",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {
        "id": "test-message-123",
        "contact_id": "test-contact-123",
        "sender": "user",
        "channel": "telegram",
        "content": "Hello, I'd like to schedule a meeting",
        "status": "received",
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_user_details():
    """Sample user details data for testing."""
    return {
        "id": "test-user-123",
        "user_id": "test-manager-456",
        "working_hours_start": "09:00",
        "working_hours_end": "17:00",
        "meeting_duration": 60,
        "buffer_time": 15,
        "telegram_id": "manager_telegram_123",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_telegram_update():
    """Sample Telegram update for testing."""
    return {
        "update_id": 123456789,
        "message": {
            "message_id": 123,
            "from": {
                "id": 12345678,
                "is_bot": False,
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe"
            },
            "chat": {
                "id": 12345678,
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe",
                "type": "private"
            },
            "date": 1703599200,
            "text": "Hello, I need to schedule a meeting"
        }
    }


@pytest.fixture
def sample_calendar_events():
    """Sample calendar events for testing."""
    now = datetime.utcnow()
    return [
        {
            "id": "event_1",
            "summary": "Existing Meeting 1",
            "start": {"dateTime": (now + timedelta(hours=1)).isoformat() + "Z"},
            "end": {"dateTime": (now + timedelta(hours=2)).isoformat() + "Z"}
        },
        {
            "id": "event_2", 
            "summary": "Existing Meeting 2",
            "start": {"dateTime": (now + timedelta(hours=4)).isoformat() + "Z"},
            "end": {"dateTime": (now + timedelta(hours=5)).isoformat() + "Z"}
        }
    ]


@pytest.fixture
def mock_langchain_agent():
    """Mock LangChain agent for testing."""
    agent = Mock()
    
    # Mock agent responses
    agent.run = Mock(return_value="Hello! I'm Athena. How can I help you today?")
    agent.invoke = Mock(return_value={"output": "I'd be happy to help schedule a meeting."})
    
    return agent


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    redis_client = Mock()
    
    # Mock Redis operations
    redis_client.get = Mock(return_value=None)
    redis_client.set = Mock(return_value=True)
    redis_client.delete = Mock(return_value=1)
    redis_client.exists = Mock(return_value=False)
    redis_client.expire = Mock(return_value=True)
    
    return redis_client


@pytest.fixture
async def async_client():
    """Async HTTP client for testing FastAPI endpoints."""
    from httpx import AsyncClient
    from src.api.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Pytest markers for easy test categorization
pytestmark = pytest.mark.asyncio 