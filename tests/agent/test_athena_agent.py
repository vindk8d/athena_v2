"""
Unit tests for AthenaAgent
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.agent.athena_agent import AthenaAgent
import time
import asyncio
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

@pytest_asyncio.fixture
async def athena_agent():
    """Create an AthenaAgent instance for testing"""
    with patch('src.agent.athena_agent.SupabaseClient') as MockSupabaseClient, \
         patch('src.agent.athena_agent.ConversationManager') as MockConversationManager:
        # Mock async methods if needed
        mock_db = MockSupabaseClient.return_value
        mock_db.get_contact_by_telegram_id = AsyncMock(return_value=None)
        mock_convo = MockConversationManager.return_value
        mock_convo.get_conversation_context = AsyncMock(return_value=[])
        agent = AthenaAgent()
        # Override rate limiter config for testing
        agent.llm_rate_limiter.config.min_interval = 0.1  # 100ms for faster tests
        agent.llm_rate_limiter.config.max_retries = 1
        agent.llm_rate_limiter.config.initial_backoff = 0.1
        agent.llm_rate_limiter.config.max_backoff = 0.2
        await agent.initialize()
        yield agent
        await agent.llm_rate_limiter.shutdown()

@pytest.mark.asyncio
async def test_new_contact_state(athena_agent):
    """Test handling of new contact state"""
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "Hello Test User! I'm Athena, your digital executive assistant. How can I assist you today?"
        response = await athena_agent.process_message(
            "Hello",
            "123",
            parsed_message=MagicMock(user=MagicMock(telegram_id="123", full_name="Test User"))
        )
        assert "Athena" in response
        assert "Test User" in response

@pytest.mark.asyncio
async def test_returning_contact_state(athena_agent):
    """Test handling of returning contact state"""
    with patch.object(athena_agent, 'check_contact_exists', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
            mock_generate_response.return_value = "Welcome back, Test User! I'm Athena, your digital executive assistant. How can I assist you today?"
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
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "I'll help you schedule a meeting. Could you please tell me what this meeting is about?"
        response = await athena_agent.process_message(
            "I want to schedule a meeting",
            "123",
            intent_keywords={"wants_meeting": True}
        )
        assert "schedule" in response.lower()
        assert "meeting" in response.lower()

@pytest.mark.asyncio
async def test_meeting_scheduling_prompt(athena_agent):
    """Test meeting scheduling prompt"""
    athena_agent.set_state("123", "scheduling_meeting")
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "I'll help you schedule a meeting. Could you please tell me what this meeting is about?"
        response = await athena_agent.process_message(
            "I want to schedule a meeting",
            "123",
            intent_keywords={"wants_meeting": True}
        )
        assert "schedule" in response.lower()
        assert "meeting" in response.lower()

@pytest.mark.asyncio
async def test_confirmation_state(athena_agent):
    """Test confirmation state"""
    athena_agent.set_state("123", "confirmation")
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "Great! I've scheduled your meeting for tomorrow at 2 PM."
        response = await athena_agent.process_message(
            "Yes, that works",
            "123"
        )
        assert "scheduled" in response.lower()

@pytest.mark.asyncio
async def test_state_transitions_from_returning_contact(athena_agent):
    """Test state transitions from returning contact"""
    with patch.object(athena_agent, 'check_contact_exists', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
            mock_generate_response.return_value = "I'll help you schedule a meeting. Could you please tell me what this meeting is about?"
            response = await athena_agent.process_message(
                "I want to schedule a meeting",
                "123",
                intent_keywords={"wants_meeting": True}
            )
            assert athena_agent.get_state("123") == "scheduling_meeting"
            assert "schedule" in response.lower()
            assert "meeting" in response.lower()

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
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "Thank you for providing your information. I've updated your contact details."
        response = await athena_agent.process_message(
            "My name is Test User and my email is test@example.com",
            "123",
            parsed_message=MagicMock(user=MagicMock(
                telegram_id="123",
                full_name="Test User",
                email="test@example.com"
            ))
        )
        assert "thank you" in response.lower()

@pytest.mark.asyncio
async def test_state_persistence(athena_agent):
    """Test state persistence between messages"""
    athena_agent.set_state("123", "scheduling_meeting")
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "I'm still helping you schedule a meeting. What would you like to discuss?"
        response = await athena_agent.process_message(
            "What's my current state?",
            "123"
        )
        assert athena_agent.get_state("123") == "scheduling_meeting"
        assert "schedule" in response.lower()
        assert "meeting" in response.lower()

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
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "I'm here to help. What would you like to do?"
        response = await athena_agent.process_message(
            "Hello",
            "123"
        )
        assert "help" in response.lower()

@pytest.mark.asyncio
async def test_extract_meeting_details(athena_agent):
    """Test meeting details extraction"""
    with patch.object(athena_agent.llm_rate_limiter, 'generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = '{"topic": "Test Meeting", "duration": 30, "time": "10:00 AM"}'
        details = await athena_agent.extract_meeting_details("Schedule a test meeting for 30 minutes at 10 AM")
        assert details["topic"] == "Test Meeting"
        assert details["duration"] == 30
        assert details["time"] == "10:00 AM"

@pytest.mark.asyncio
async def test_meeting_details_in_scheduling_state(athena_agent):
    """Test meeting details handling in scheduling state"""
    athena_agent.set_state("123", "scheduling_meeting")
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "I understand you want to schedule a test meeting for 30 minutes at 10 AM. Let me help you with that."
        response = await athena_agent.process_message(
            "Schedule a test meeting for 30 minutes at 10 AM",
            "123"
        )
        assert "schedule" in response.lower()
        assert "meeting" in response.lower()

@pytest.mark.asyncio
async def test_meeting_details_error_handling(athena_agent):
    """Test error handling in meeting details extraction"""
    athena_agent.set_state("123", "scheduling_meeting")
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.side_effect = Exception("API Error")
        with pytest.raises(Exception) as excinfo:
            await athena_agent.process_message(
                "Schedule a meeting at 2 PM",
                "123"
            )
        assert "API Error" in str(excinfo.value)

@pytest.mark.asyncio
async def test_rate_limit_compliance_during_conversation(athena_agent):
    """Test rate limit compliance during conversation"""
    messages = [
        "Hello, I'd like to schedule a meeting",
        "It's about project planning",
        "Let's make it 45 minutes",
        "How about tomorrow at 2 PM?",
        "Yes, that works for me"
    ]
    request_times = []
    
    async def mock_generate_response(*args, **kwargs):
        await asyncio.sleep(athena_agent.llm_rate_limiter.config.min_interval)
        request_times.append(time.time())
        return "I understand you want to schedule a meeting."
    
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', mock_generate_response):
        for message in messages:
            await athena_agent.process_message(message, "123")
        
        for i in range(1, len(request_times)):
            time_diff = request_times[i] - request_times[i-1]
            assert time_diff >= athena_agent.llm_rate_limiter.config.min_interval, \
                f"Request interval {time_diff:.2f}s is less than minimum {athena_agent.llm_rate_limiter.config.min_interval}s"

@pytest.mark.asyncio
async def test_concurrent_request_handling(athena_agent):
    """Test handling of concurrent requests"""
    async def make_request(message):
        return await athena_agent.process_message(message, "123")
    
    async def mock_generate_response(*args, **kwargs):
        await asyncio.sleep(athena_agent.llm_rate_limiter.config.min_interval)
        return "I understand you want to schedule a meeting."
    
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', mock_generate_response):
        tasks = [
            make_request("Schedule a meeting"),
            make_request("What's my current state?"),
            make_request("Cancel the meeting")
        ]
        responses = await asyncio.gather(*tasks)
        
        assert all("meeting" in response.lower() for response in responses)

@pytest.mark.asyncio
async def test_response_caching(athena_agent):
    """Test response caching with different system prompts (states)"""
    cache_hits = 0
    
    async def mock_make_request(*args, **kwargs):
        nonlocal cache_hits
        print(f"_make_request called with args: {args}, kwargs: {kwargs}")
        cache_hits += 1
        return "I understand you want to schedule a meeting."
    async def mock_make_batch_request(messages_list, use_heavy_model):
        nonlocal cache_hits
        print(f"_make_batch_request called with messages_list: {messages_list}, use_heavy_model: {use_heavy_model}")
        cache_hits += len(messages_list)
        return ["I understand you want to schedule a meeting."] * len(messages_list)
    
    with patch.object(athena_agent.llm_rate_limiter, '_make_request', mock_make_request), \
         patch.object(athena_agent.llm_rate_limiter, '_make_batch_request', mock_make_batch_request):
        # First request
        response1 = await athena_agent.process_message("Schedule a meeting", "123")
        # Second request with same message
        response2 = await athena_agent.process_message("Schedule a meeting", "123")
        
        assert response1 == response2
        assert cache_hits == 2  # Two unique requests due to different system prompts/states

@pytest.mark.asyncio
async def test_rate_limit_backoff(athena_agent):
    """Test rate limit backoff behavior"""
    retry_count = 0
    
    async def mock_generate_response(*args, **kwargs):
        nonlocal retry_count
        if retry_count == 0:
            retry_count += 1
            raise Exception("rate limit exceeded")
        return "I understand you want to schedule a meeting."
    
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', mock_generate_response):
        with pytest.raises(Exception) as excinfo:
            await athena_agent.process_message("Schedule a meeting", "123")
        assert "rate limit exceeded" in str(excinfo.value)
        assert retry_count == 1

@pytest.mark.asyncio
async def test_batch_processing(athena_agent):
    """Test batch processing of requests"""
    async def mock_generate_response(*args, **kwargs):
        await asyncio.sleep(athena_agent.llm_rate_limiter.config.min_interval)
        return "I understand you want to schedule a meeting."
    
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', mock_generate_response):
        async def make_non_priority_request(message):
            # Remove priority argument, as process_message does not accept it
            return await athena_agent.process_message(message, "123")
        
        tasks = [
            make_non_priority_request("Schedule a meeting"),
            make_non_priority_request("What's my current state?"),
            make_non_priority_request("Cancel the meeting")
        ]
        responses = await asyncio.gather(*tasks)
        
        assert all("meeting" in response.lower() for response in responses) 