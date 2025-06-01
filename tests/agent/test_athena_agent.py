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

@pytest.mark.asyncio
async def test_state_transitions_from_returning_contact(athena_agent):
    """Test state transitions when user is a returning contact."""
    # Setup: Set initial state as returning_contact
    athena_agent.set_state("123456789", "returning_contact")
    
    # Test 1: Scheduling intent should override returning_contact state
    intent_keywords = {"wants_meeting": True}
    response = await athena_agent.process_message(
        "I want to schedule a meeting",
        "123456789",
        intent_keywords=intent_keywords
    )
    assert athena_agent.get_state("123456789") == "scheduling_meeting"
    assert "To schedule your meeting" in response
    
    # Test 2: Providing contact info should transition to collecting_info
    athena_agent.set_state("123456789", "returning_contact")
    intent_keywords = {"providing_contact": True}
    response = await athena_agent.process_message(
        "My email is test@example.com",
        "123456789",
        intent_keywords=intent_keywords
    )
    assert athena_agent.get_state("123456789") == "collecting_info"
    assert "I still need" in response

@pytest.mark.asyncio
async def test_state_transitions_from_scheduling_meeting(athena_agent):
    """Test state transitions when in scheduling_meeting state."""
    # Setup: Set initial state as scheduling_meeting
    athena_agent.set_state("123456789", "scheduling_meeting")
    
    # Test 1: Providing meeting details should stay in scheduling_meeting
    response = await athena_agent.process_message(
        "The meeting is about project planning",
        "123456789"
    )
    assert athena_agent.get_state("123456789") == "scheduling_meeting"
    assert "To schedule your meeting" in response
    
    # Test 2: Providing all meeting details should show time options
    parsed_message = type('ParsedMessage', (), {
        'topic': 'Project Planning',
        'duration': 60,
        'time': 'tomorrow'
    })
    response = await athena_agent.process_message(
        "Let's meet tomorrow for 1 hour about project planning",
        "123456789",
        parsed_message=parsed_message
    )
    assert "Here are some available meeting times" in response

@pytest.mark.asyncio
async def test_state_transitions_from_collecting_info(athena_agent):
    """Test state transitions when collecting contact information."""
    # Setup: Set initial state as collecting_info
    athena_agent.set_state("123456789", "collecting_info")
    
    # Test 1: Providing partial contact info should stay in collecting_info
    parsed_message = type('ParsedMessage', (), {
        'user': type('User', (), {
            'full_name': 'Test User',
            'email': None,
            'telegram_id': '123456789'
        })
    })
    response = await athena_agent.process_message(
        "My name is Test User",
        "123456789",
        parsed_message=parsed_message
    )
    assert athena_agent.get_state("123456789") == "collecting_info"
    assert "I still need" in response
    
    # Test 2: Providing complete contact info should show confirmation
    parsed_message = type('ParsedMessage', (), {
        'user': type('User', (), {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'telegram_id': '123456789'
        })
    })
    response = await athena_agent.process_message(
        "My email is test@example.com",
        "123456789",
        parsed_message=parsed_message
    )
    assert "Thank you for providing your contact information" in response

@pytest.mark.asyncio
async def test_state_persistence(athena_agent):
    """Test that states persist correctly between messages."""
    # Test 1: State should persist for same user
    athena_agent.set_state("123456789", "scheduling_meeting")
    assert athena_agent.get_state("123456789") == "scheduling_meeting"
    
    # Test 2: Different users should have different states
    athena_agent.set_state("987654321", "collecting_info")
    assert athena_agent.get_state("123456789") == "scheduling_meeting"
    assert athena_agent.get_state("987654321") == "collecting_info"

@pytest.mark.asyncio
async def test_state_reset_on_cancel(athena_agent):
    """Test that state resets to idle on cancel command."""
    # Setup: Set various states
    athena_agent.set_state("123456789", "scheduling_meeting")
    athena_agent.set_state("987654321", "collecting_info")
    
    # Test cancel command
    intent_keywords = {"cancel": True}
    await athena_agent.process_message(
        "/cancel",
        "123456789",
        intent_keywords=intent_keywords
    )
    assert athena_agent.get_state("123456789") == "idle"

@pytest.mark.asyncio
async def test_invalid_state_handling(athena_agent):
    """Test handling of invalid or unexpected states."""
    # Test 1: Invalid state should default to idle
    athena_agent.set_state("123456789", "invalid_state")
    response = await athena_agent.process_message(
        "Hello",
        "123456789"
    )
    assert athena_agent.get_state("123456789") == "idle"
    assert "How can I assist you today" in response
    
    # Test 2: None state should be handled gracefully
    athena_agent.user_states["123456789"] = None
    response = await athena_agent.process_message(
        "Hello",
        "123456789"
    )
    assert athena_agent.get_state("123456789") in ["new_contact", "returning_contact"] 