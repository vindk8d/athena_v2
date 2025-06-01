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
def athena_agent():
    agent = AthenaAgent()
    # Patch async dependencies
    agent.conversation_manager.get_conversation_context = AsyncMock(return_value=[])
    agent.db_client.get_contact_by_telegram_id = AsyncMock(return_value=None)
    return agent

@pytest.mark.asyncio
async def test_new_contact_state(athena_agent):
    """Test initial state for new contacts."""
    response = await athena_agent.process_message("Hello", "123456789")
    assert "I'm Athena" in response
    assert athena_agent.get_state("123456789") == "new_contact"

@pytest.mark.asyncio
async def test_returning_contact_state(athena_agent):
    """Test state for returning contacts."""
    athena_agent.db_client.get_contact_by_telegram_id = AsyncMock(return_value={"name": "John"})
    # Provide a parsed_message with user_name
    parsed_message = Mock()
    parsed_message.user = Mock()
    parsed_message.user.full_name = "John"
    parsed_message.user.telegram_id = "123456789"
    response = await athena_agent.process_message("Hello", "123456789", parsed_message=parsed_message)
    assert "Welcome back" in response
    assert athena_agent.get_state("123456789") == "returning_contact"

@pytest.mark.asyncio
async def test_contact_collection_prompt(athena_agent):
    """Test contact information collection prompts."""
    athena_agent.set_state("123456789", "collecting_info")
    response = await athena_agent.process_message("Hello", "123456789")
    assert "I still need" in response
    assert "name" in response.lower() or "email" in response.lower()

@pytest.mark.asyncio
async def test_meeting_scheduling_prompt(athena_agent):
    """Test meeting scheduling prompts."""
    athena_agent.set_state("123456789", "scheduling_meeting")
    with patch.object(AthenaAgent, "extract_meeting_details", new=AsyncMock(return_value={"topic": None, "duration": None, "time": None})):
        response = await athena_agent.process_message("I want to schedule a meeting", "123456789")
    assert "I'm helping you schedule a meeting" in response
    assert "what this meeting is about" in response.lower()

@pytest.mark.asyncio
async def test_confirmation_state(athena_agent):
    """Test confirmation state responses."""
    athena_agent.set_state("123456789", "confirmation")
    response = await athena_agent.process_message("Yes", "123456789")
    assert "Your meeting has been scheduled" in response

@pytest.mark.asyncio
async def test_state_transitions_from_returning_contact(athena_agent):
    """Test state transitions when user is a returning contact."""
    # Setup: Set initial state as returning_contact
    athena_agent.set_state("123456789", "returning_contact")
    with patch.object(AthenaAgent, "extract_meeting_details", new=AsyncMock(return_value={"topic": None, "duration": None, "time": None})):
        # Test 1: Scheduling intent should override returning_contact state
        intent_keywords = {"wants_meeting": True}
        response = await athena_agent.process_message(
            "I want to schedule a meeting",
            "123456789",
            intent_keywords=intent_keywords
        )
    assert athena_agent.get_state("123456789") == "scheduling_meeting"
    assert "I'm helping you schedule a meeting" in response

@pytest.mark.asyncio
async def test_state_transitions_from_scheduling_meeting(athena_agent):
    """Test state transitions when in scheduling_meeting state."""
    # Setup: Set initial state as scheduling_meeting
    athena_agent.set_state("123456789", "scheduling_meeting")
    with patch.object(AthenaAgent, "extract_meeting_details", new=AsyncMock(return_value={"topic": "project planning", "duration": None, "time": None})):
        # Test 1: Providing meeting details should stay in scheduling_meeting
        response = await athena_agent.process_message(
            "The meeting is about project planning",
            "123456789"
        )
    assert athena_agent.get_state("123456789") == "scheduling_meeting"
    assert "I know this meeting is about" in response

@pytest.mark.asyncio
async def test_state_transitions_from_collecting_info(athena_agent):
    """Test state transitions when in collecting_info state."""
    # Setup: Set initial state as collecting_info
    athena_agent.set_state("123456789", "collecting_info")

    # Test 1: Providing contact info should stay in collecting_info until complete
    response = await athena_agent.process_message(
        "My name is John Doe",
        "123456789"
    )
    assert athena_agent.get_state("123456789") == "collecting_info"
    assert "I still need" in response

@pytest.mark.asyncio
async def test_state_persistence(athena_agent):
    """Test that state persists between messages."""
    # Set initial state
    athena_agent.set_state("123456789", "scheduling_meeting")
    with patch.object(AthenaAgent, "extract_meeting_details", new=AsyncMock(return_value={"topic": None, "duration": None, "time": None})):
        # Send a message without changing state
        response = await athena_agent.process_message(
            "Hello",
            "123456789"
        )
    assert athena_agent.get_state("123456789") == "scheduling_meeting"

@pytest.mark.asyncio
async def test_state_reset_on_cancel(athena_agent):
    """Test that state resets on cancel intent."""
    # Set initial state
    athena_agent.set_state("123456789", "scheduling_meeting")
    
    # Send cancel intent
    intent_keywords = {"cancel": True}
    with patch.object(AthenaAgent, "extract_meeting_details", new=AsyncMock(return_value={"topic": None, "duration": None, "time": None})):
        response = await athena_agent.process_message(
            "Cancel",
            "123456789",
            intent_keywords=intent_keywords
        )
    assert athena_agent.get_state("123456789") == "idle"

@pytest.mark.asyncio
async def test_invalid_state_handling(athena_agent):
    """Test handling of invalid states."""
    # Set invalid state
    athena_agent.set_state("123456789", "invalid_state")
    
    # Send a message
    response = await athena_agent.process_message(
        "Hello",
        "123456789"
    )
    assert athena_agent.get_state("123456789") == "idle"

@pytest.mark.asyncio
async def test_extract_meeting_details(athena_agent):
    """Test meeting details extraction."""
    # Patch OpenAI call to avoid real API usage
    with patch.object(AthenaAgent, "extract_meeting_details", new=AsyncMock(return_value={"topic": "project sync", "duration": 45, "time": "3:00 PM"})):
        details = await athena_agent.extract_meeting_details(
            "Let's have a 45-minute sync about the project at 3 PM"
        )
        assert details["topic"] == "project sync"
        assert details["duration"] == 45
        assert "3:00 PM" in details["time"]
    with patch.object(AthenaAgent, "extract_meeting_details", new=AsyncMock(return_value={"topic": "project planning", "duration": None, "time": None})):
        details = await athena_agent.extract_meeting_details(
            "The meeting is about project planning"
        )
        assert details["topic"] == "project planning"
        assert details["duration"] is None
        assert details["time"] is None

@pytest.mark.asyncio
async def test_meeting_details_in_scheduling_state(athena_agent):
    """Test meeting details extraction in scheduling_meeting state."""
    # Setup: Set state to scheduling_meeting
    athena_agent.set_state("123456789", "scheduling_meeting")
    with patch.object(AthenaAgent, "extract_meeting_details", new=AsyncMock(return_value={"topic": "project sync", "duration": 45, "time": "3:00 PM"})):
        # Test 1: Complete meeting details
        response = await athena_agent.process_message(
            "Let's have a 45-minute sync about the project at 3 PM",
            "123456789"
        )
        assert "Here are some available meeting times" in response
    # Clear meeting details for the user before the next subtest
    athena_agent.meeting_details["123456789"] = {"topic": None, "duration": None, "time": None}
    with patch.object(AthenaAgent, "extract_meeting_details", new=AsyncMock(return_value={"topic": "project planning", "duration": None, "time": None})):
        # Test 2: Partial details
        response = await athena_agent.process_message(
            "The meeting is about project planning",
            "123456789"
        )
        assert "I know this meeting is about" in response
        assert "I still need to know" in response

@pytest.mark.asyncio
async def test_meeting_details_error_handling(athena_agent):
    """Test error handling in meeting details extraction."""
    # Setup: Set state to scheduling_meeting
    athena_agent.set_state("123456789", "scheduling_meeting")
    with patch.object(AthenaAgent, "extract_meeting_details", new=AsyncMock(return_value={"topic": None, "duration": None, "time": None})):
        # Test error handling
        response = await athena_agent.process_message(
            "Let's schedule a meeting",
            "123456789"
        )
    assert "I'm helping you schedule a meeting" in response
    assert "what this meeting is about" in response.lower() 