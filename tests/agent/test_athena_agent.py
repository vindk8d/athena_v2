"""
Unit tests for AthenaAgent
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.agent.athena_agent import AthenaAgent

@pytest_asyncio.fixture
async def athena_agent():
    """Create an AthenaAgent instance for testing"""
    with patch('src.agent.athena_agent.SupabaseClient', autospec=True) as MockSupabaseClient, \
         patch('src.agent.athena_agent.ConversationManager', autospec=True) as MockConversationManager:
        # Mock async methods if needed
        mock_db = MockSupabaseClient.return_value
        mock_db.get_contact_by_telegram_id = AsyncMock(return_value=None)
        mock_convo = MockConversationManager.return_value
        mock_convo.get_conversation_context = AsyncMock(return_value=[])
        agent = AthenaAgent()
        await agent.initialize()
        return agent

@pytest.mark.asyncio
async def test_new_contact_state(athena_agent):
    """Test handling of new contact state"""
    response = await athena_agent.process_message(
        "Hello",
        "123",
        parsed_message=MagicMock(user=MagicMock(telegram_id="123", full_name="Test User"))
    )
    assert "I'm Athena" in response
    assert "Test User" in response

@pytest.mark.asyncio
async def test_returning_contact_state(athena_agent):
    """Test handling of returning contact state"""
    with patch.object(athena_agent, 'check_contact_exists', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        response = await athena_agent.process_message(
            "Hello",
            "123",
            parsed_message=MagicMock(user=MagicMock(telegram_id="123", full_name="Test User"))
        )
        assert "Welcome back" in response
        assert "Test User" in response

@pytest.mark.asyncio
async def test_contact_collection_prompt(athena_agent):
    """Test contact collection prompt"""
    response = await athena_agent.process_message(
        "I want to schedule a meeting",
        "123",
        intent_keywords={"wants_meeting": True}
    )
    assert "I'm helping you schedule a meeting" in response
    assert (
        "what this meeting is about" in response
        or "how long the meeting should be" in response
        or "when you'd like to have the meeting" in response
    )

@pytest.mark.asyncio
async def test_meeting_scheduling_prompt(athena_agent):
    """Test meeting scheduling prompt"""
    response = await athena_agent.process_message(
        "I want to schedule a meeting",
        "123",
        intent_keywords={"wants_meeting": True}
    )
    assert "I'm helping you schedule a meeting" in response
    assert (
        "what this meeting is about" in response
        or "how long the meeting should be" in response
        or "when you'd like to have the meeting" in response
    )

@pytest.mark.asyncio
async def test_confirmation_state(athena_agent):
    """Test confirmation state"""
    athena_agent.set_state("123", "confirmation")
    response = await athena_agent.process_message(
        "Yes, that works",
        "123"
    )
    assert "Your meeting has been scheduled" in response

@pytest.mark.asyncio
async def test_state_transitions_from_returning_contact(athena_agent):
    """Test state transitions from returning contact"""
    with patch.object(athena_agent, 'check_contact_exists', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        response = await athena_agent.process_message(
            "I want to schedule a meeting",
            "123",
            intent_keywords={"wants_meeting": True}
        )
        assert athena_agent.get_state("123") == "scheduling_meeting"
        assert "I'm helping you schedule a meeting" in response

@pytest.mark.asyncio
async def test_state_transitions_from_scheduling_meeting(athena_agent):
    """Test state transitions from scheduling meeting"""
    athena_agent.set_state("123", "scheduling_meeting")
    response = await athena_agent.process_message(
        "Cancel",
        "123",
        intent_keywords={"cancel": True}
    )
    assert athena_agent.get_state("123") == "idle"
    assert "cancelled" in response.lower()

@pytest.mark.asyncio
async def test_state_transitions_from_collecting_info(athena_agent):
    """Test state transitions from collecting info"""
    athena_agent.set_state("123", "collecting_info")
    response = await athena_agent.process_message(
        "My name is Test User and my email is test@example.com",
        "123",
        parsed_message=MagicMock(user=MagicMock(
            telegram_id="123",
            full_name="Test User",
            email="test@example.com"
        ))
    )
    assert "Thank you" in response

@pytest.mark.asyncio
async def test_state_persistence(athena_agent):
    """Test state persistence between messages"""
    athena_agent.set_state("123", "scheduling_meeting")
    response = await athena_agent.process_message(
        "What's my current state?",
        "123"
    )
    assert athena_agent.get_state("123") == "scheduling_meeting"

@pytest.mark.asyncio
async def test_state_reset_on_cancel(athena_agent):
    """Test state reset on cancel"""
    athena_agent.set_state("123", "scheduling_meeting")
    athena_agent.meeting_details["123"] = {"topic": "Test", "duration": 30, "time": "10:00 AM"}
    response = await athena_agent.process_message(
        "Cancel",
        "123",
        intent_keywords={"cancel": True}
    )
    assert athena_agent.get_state("123") == "idle"
    assert "123" not in athena_agent.meeting_details

@pytest.mark.asyncio
async def test_invalid_state_handling(athena_agent):
    """Test handling of invalid state"""
    athena_agent.set_state("123", "invalid_state")
    response = await athena_agent.process_message(
        "Hello",
        "123"
    )
    assert "I'm here to help" in response

@pytest.mark.asyncio
async def test_extract_meeting_details(athena_agent):
    """Test meeting details extraction"""
    with patch.object(athena_agent.llm_rate_limiter, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = '{"topic": "Test Meeting", "duration": 30, "time": "10:00 AM"}'
        details = await athena_agent.extract_meeting_details("Schedule a test meeting for 30 minutes at 10 AM")
        assert details["topic"] == "Test Meeting"
        assert details["duration"] == 30
        assert details["time"] == "10:00 AM"

@pytest.mark.asyncio
async def test_meeting_details_in_scheduling_state(athena_agent):
    """Test meeting details handling in scheduling state"""
    athena_agent.set_state("123", "scheduling_meeting")
    with patch.object(athena_agent.llm_rate_limiter, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = '{"topic": "Test Meeting", "duration": 30, "time": "10:00 AM"}'
        response = await athena_agent.process_message(
            "Schedule a test meeting for 30 minutes at 10 AM",
            "123"
        )
        assert "Here are some available meeting times" in response
        assert "Tomorrow at 10:00 AM" in response
        assert "Tomorrow at 2:00 PM" in response
        assert "The day after at 11:00 AM" in response

@pytest.mark.asyncio
async def test_meeting_details_error_handling(athena_agent):
    """Test error handling in meeting details extraction"""
    athena_agent.set_state("123", "scheduling_meeting")
    with patch.object(athena_agent.llm_rate_limiter, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = Exception("API Error")
        response = await athena_agent.process_message(
            "Schedule a meeting at 2 PM",
            "123"
        )
        assert "I'm helping you schedule a meeting" in response
        assert "2 PM" in response 