import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.agent.athena_agent import AthenaAgent

@pytest.fixture(autouse=True)
def patch_dependencies():
    with patch('src.agent.athena_agent.SupabaseClient', Mock()), \
         patch('src.agent.athena_agent.ConversationManager', Mock()):
        yield

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
    agent.conversation_manager.get_conversation_context = AsyncMock(return_value=[])
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
    athena_agent.db_client.get_contact_by_telegram_id = AsyncMock(return_value={"name": "John"})
    # Provide a parsed_message with a user that has a full_name and a real telegram_id
    parsed_message = Mock()
    parsed_message.user = Mock()
    parsed_message.user.full_name = "John"
    parsed_message.user.telegram_id = "123456789"
    response = await athena_agent.process_message("Hi again", "123456789", parsed_message=parsed_message)
    assert "Welcome back, John" in response
    assert athena_agent.get_state("123456789") == "returning_contact"

@pytest.mark.asyncio
async def test_contact_collection_prompt(athena_agent):
    # Simulate missing contact info
    athena_agent.set_state("123456789", "collecting_info")
    # Provide intent_keywords to trigger collecting_info state
    intent_keywords = {"providing_contact": True}
    # Provide a parsed_message with a user that has a name and telegram_id, but no email
    parsed_message = Mock()
    parsed_message.user = Mock()
    parsed_message.user.full_name = "John"
    parsed_message.user.telegram_id = "123456789"
    parsed_message.user.email = None
    response = await athena_agent.process_message("My name is John", "123456789", intent_keywords=intent_keywords, parsed_message=parsed_message)
    assert "I still need your email address" in response

@pytest.mark.asyncio
async def test_meeting_scheduling_prompt(athena_agent):
    # Simulate meeting scheduling
    athena_agent.set_state("123456789", "scheduling_meeting")
    # Provide intent_keywords to trigger scheduling_meeting state
    intent_keywords = {"wants_meeting": True}
    response = await athena_agent.process_message("I want to schedule a meeting", "123456789", intent_keywords=intent_keywords)
    assert "To schedule your meeting, I still need" in response

@pytest.mark.asyncio
async def test_confirmation_state(athena_agent):
    # Simulate confirmation
    athena_agent.set_state("123456789", "confirmation")
    response = await athena_agent.process_message("Confirm", "123456789")
    assert "Your meeting has been scheduled" in response 