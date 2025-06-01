import pytest
from unittest.mock import Mock, patch
from src.agent.athena_agent import AthenaAgent

@pytest.fixture
def mock_supabase_client():
    return Mock()

@pytest.fixture
def mock_conversation_manager():
    return Mock()

@pytest.fixture
def athena_agent(mock_supabase_client, mock_conversation_manager):
    agent = AthenaAgent()
    agent.db_client = mock_supabase_client
    agent.conversation_manager = mock_conversation_manager
    return agent

@pytest.mark.asyncio
async def test_new_contact_state(athena_agent):
    # Simulate new contact
    athena_agent.db_client.get_contact_by_telegram_id.return_value = None
    response = await athena_agent.process_message("Hello", "123456789")
    assert "Hello! I'm Athena" in response
    assert athena_agent.get_state("123456789") == "new_contact"

@pytest.mark.asyncio
async def test_returning_contact_state(athena_agent):
    # Simulate returning contact
    athena_agent.db_client.get_contact_by_telegram_id.return_value = {"name": "John"}
    response = await athena_agent.process_message("Hi again", "123456789")
    assert "Welcome back, John" in response
    assert athena_agent.get_state("123456789") == "returning_contact"

@pytest.mark.asyncio
async def test_contact_collection_prompt(athena_agent):
    # Simulate missing contact info
    athena_agent.set_state("123456789", "collecting_info")
    response = await athena_agent.process_message("My name is John", "123456789")
    assert "I still need your email address" in response

@pytest.mark.asyncio
async def test_meeting_scheduling_prompt(athena_agent):
    # Simulate meeting scheduling
    athena_agent.set_state("123456789", "scheduling_meeting")
    response = await athena_agent.process_message("I want to schedule a meeting", "123456789")
    assert "To schedule your meeting, I still need" in response

@pytest.mark.asyncio
async def test_confirmation_state(athena_agent):
    # Simulate confirmation
    athena_agent.set_state("123456789", "confirmation")
    response = await athena_agent.process_message("Confirm", "123456789")
    assert "Your meeting has been scheduled" in response 