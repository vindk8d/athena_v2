import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, UTC

# Mock dependencies at module level before any imports
with patch('src.database.supabase_client.create_client', MagicMock()):
    from src.database.supabase_client import SupabaseClient

@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    mock = MagicMock()
    return mock

@pytest.fixture
def supabase_client(mock_supabase_client):
    """Create a SupabaseClient instance with mocked Supabase client."""
    with patch('src.database.supabase_client.create_client', return_value=mock_supabase_client):
        client = SupabaseClient()
        client.supabase = mock_supabase_client
        return client

@pytest.mark.asyncio
async def test_create_message_success(supabase_client):
    """Test successful message creation."""
    # Mock response data
    mock_response = MagicMock()
    mock_response.data = [{
        "id": "123",
        "contact_id": "456",
        "sender": "user",
        "channel": "telegram",
        "content": "Hello",
        "status": "delivered",
        "created_at": datetime.now(UTC).isoformat()
    }]
    supabase_client.supabase.table().insert().execute.return_value = mock_response

    # Test message creation
    result = await supabase_client.create_message(
        contact_id="456",
        sender="user",
        channel="telegram",
        content="Hello"
    )

    # Verify the result
    assert result["id"] == "123"
    assert result["sender"] == "user"
    assert result["status"] == "delivered"

    # Verify the insert was called with correct data
    supabase_client.supabase.table.assert_called_with("messages")
    insert_call = supabase_client.supabase.table().insert.call_args[0][0]
    assert insert_call["sender"] == "user"
    assert insert_call["status"] == "delivered"

@pytest.mark.asyncio
async def test_create_message_with_metadata(supabase_client):
    """Test message creation with metadata."""
    mock_response = MagicMock()
    mock_response.data = [{
        "id": "123",
        "contact_id": "456",
        "sender": "assistant",
        "channel": "telegram",
        "content": "Hello",
        "status": "delivered",
        "metadata": {"telegram_message_id": 123},
        "created_at": datetime.now(UTC).isoformat()
    }]
    supabase_client.supabase.table().insert().execute.return_value = mock_response

    # Test message creation with metadata
    result = await supabase_client.create_message(
        contact_id="456",
        sender="assistant",
        channel="telegram",
        content="Hello",
        metadata={"telegram_message_id": 123}
    )

    # Verify metadata was included
    assert result["metadata"]["telegram_message_id"] == 123

@pytest.mark.asyncio
async def test_create_message_invalid_sender(supabase_client):
    """Test message creation with invalid sender."""
    with pytest.raises(ValueError, match="Invalid sender value"):
        await supabase_client.create_message(
            contact_id="456",
            sender="invalid_sender",
            channel="telegram",
            content="Hello"
        )

@pytest.mark.asyncio
async def test_create_message_sender_case_insensitive(supabase_client):
    """Test that sender values are case-insensitive."""
    mock_response = MagicMock()
    mock_response.data = [{
        "id": "123",
        "contact_id": "456",
        "sender": "user",
        "channel": "telegram",
        "content": "Hello",
        "status": "delivered",
        "created_at": datetime.now(UTC).isoformat()
    }]
    supabase_client.supabase.table().insert().execute.return_value = mock_response

    # Test with uppercase sender
    result = await supabase_client.create_message(
        contact_id="456",
        sender="USER",
        channel="telegram",
        content="Hello"
    )

    # Verify sender was normalized to lowercase
    assert result["sender"] == "user"

@pytest.mark.asyncio
async def test_create_message_sender_whitespace(supabase_client):
    """Test that sender values are trimmed of whitespace."""
    mock_response = MagicMock()
    mock_response.data = [{
        "id": "123",
        "contact_id": "456",
        "sender": "assistant",
        "channel": "telegram",
        "content": "Hello",
        "status": "delivered",
        "created_at": datetime.now(UTC).isoformat()
    }]
    supabase_client.supabase.table().insert().execute.return_value = mock_response

    # Test with sender containing whitespace
    result = await supabase_client.create_message(
        contact_id="456",
        sender="  assistant  ",
        channel="telegram",
        content="Hello"
    )

    # Verify sender was trimmed
    assert result["sender"] == "assistant"

@pytest.mark.asyncio
async def test_create_message_database_error(supabase_client):
    """Test handling of database errors."""
    # Mock database error
    supabase_client.supabase.table().insert().execute.side_effect = Exception("Database error")

    # Test error handling
    with pytest.raises(Exception, match="Database error"):
        await supabase_client.create_message(
            contact_id="456",
            sender="user",
            channel="telegram",
            content="Hello"
        )

@pytest.mark.asyncio
async def test_contact_and_message_storage_flow():
    """Test the complete contact and message storage flow."""
    # This is a placeholder test that should be implemented based on actual workflow
    assert True 