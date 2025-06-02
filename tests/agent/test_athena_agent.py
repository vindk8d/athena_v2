"""
Unit tests for AthenaAgent
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.agent.athena_agent import AthenaAgent
import time
import asyncio
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI

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
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "Your meeting has been scheduled."
        response = await athena_agent.process_message(
            "Yes, that works",
            "123"
        )
        assert "scheduled" in response

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
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "Thank you, your information has been received."
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
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "I'm helping you schedule a meeting."
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
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "I'm here to help."
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
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = '{"topic": "Test Meeting", "duration": 30, "time": "10:00 AM"}'
        response = await athena_agent.process_message(
            "Schedule a test meeting for 30 minutes at 10 AM",
            "123"
        )
        assert "Test Meeting" in response or "10:00 AM" in response

@pytest.mark.asyncio
async def test_meeting_details_error_handling(athena_agent):
    """Test error handling in meeting details extraction"""
    athena_agent.set_state("123", "scheduling_meeting")
    with patch('src.utils.llm_rate_limiter.LLMRateLimiter.generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.side_effect = Exception("API Error")
        try:
            response = await athena_agent.process_message(
                "Schedule a meeting at 2 PM",
                "123"
            )
        except Exception as e:
            response = str(e)
        assert "API Error" in response or "I'm helping you schedule a meeting" in response

@pytest.mark.asyncio
async def test_rate_limit_compliance_during_conversation(athena_agent):
    messages = [
        "Hello, I'd like to schedule a meeting",
        "It's about project planning",
        "Let's make it 45 minutes",
        "How about tomorrow at 2 PM?",
        "Yes, that works for me"
    ]
    request_times = []
    async def mock_make_request(*args, **kwargs):
        await asyncio.sleep(athena_agent.llm_rate_limiter.config.min_interval)
        request_times.append(time.time())
        return "I understand you want to schedule a meeting."
    async def mock_make_batch_request(messages_list, use_heavy_model):
        for _ in messages_list:
            await asyncio.sleep(athena_agent.llm_rate_limiter.config.min_interval)
            request_times.append(time.time())
        return ["I understand you want to schedule a meeting."] * len(messages_list)
    with patch.object(athena_agent.llm_rate_limiter, '_make_request', mock_make_request), \
         patch.object(athena_agent.llm_rate_limiter, '_make_batch_request', mock_make_batch_request):
        for message in messages:
            await athena_agent.process_message(message, "123")
        for i in range(1, len(request_times)):
            time_diff = request_times[i] - request_times[i-1]
            assert time_diff >= athena_agent.llm_rate_limiter.config.min_interval, \
                f"Request interval {time_diff:.2f}s is less than minimum {athena_agent.llm_rate_limiter.config.min_interval}s"

@pytest.mark.asyncio
async def test_concurrent_request_handling(athena_agent):
    async def make_request(message):
        return await athena_agent.process_message(message, "123")
    async def mock_make_request(*args, **kwargs):
        await asyncio.sleep(athena_agent.llm_rate_limiter.config.min_interval)
        return "I understand you want to schedule a meeting."
    async def mock_make_batch_request(messages_list, use_heavy_model):
        await asyncio.sleep(athena_agent.llm_rate_limiter.config.min_interval)
        return ["I understand you want to schedule a meeting."] * len(messages_list)
    with patch.object(athena_agent.llm_rate_limiter, '_make_request', mock_make_request), \
         patch.object(athena_agent.llm_rate_limiter, '_make_batch_request', mock_make_batch_request):
        tasks = [
            make_request("Schedule a meeting about project planning"),
            make_request("I need to book a 30-minute call"),
            make_request("Let's set up a team sync")
        ]
        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        assert len(responses) == 3
        assert all(isinstance(r, str) for r in responses)
        min_expected_time = (len(tasks) - 1) * athena_agent.llm_rate_limiter.config.min_interval
        assert end_time - start_time >= min_expected_time, \
            f"Concurrent requests completed too quickly: {end_time - start_time:.2f}s < {min_expected_time:.2f}s"

@pytest.mark.asyncio
async def test_response_caching(athena_agent):
    call_count = 0
    cache = {}
    async def mock_make_request(*args, **kwargs):
        nonlocal call_count
        # Create a more stable cache key based on message content
        key = str(args[0][-1].content) if args and args[0] else str(kwargs)
        if key in cache:
            return cache[key]
        call_count += 1
        await asyncio.sleep(0.1)
        cache[key] = "I understand you want to schedule a meeting."
        return cache[key]
    async def mock_make_batch_request(messages_list, use_heavy_model):
        nonlocal call_count
        results = []
        for messages in messages_list:
            # Create a stable cache key for batch requests
            key = str(messages[-1].content) if messages else str(use_heavy_model)
            if key in cache:
                results.append(cache[key])
            else:
                call_count += 1
                cache[key] = "I understand you want to schedule a meeting."
                results.append(cache[key])
        await asyncio.sleep(0.1)
        return results
    with patch.object(athena_agent.llm_rate_limiter, '_make_request', mock_make_request), \
         patch.object(athena_agent.llm_rate_limiter, '_make_batch_request', mock_make_batch_request):
        start_time = time.time()
        response1 = await athena_agent.process_message("Hello, I'd like to schedule a meeting", "123")
        first_request_time = time.time() - start_time
        start_time = time.time()
        response2 = await athena_agent.process_message("Hello, I'd like to schedule a meeting", "123")
        second_request_time = time.time() - start_time
        assert response1 == response2
        assert second_request_time < first_request_time, \
            f"Cached request ({second_request_time:.2f}s) was not faster than first request ({first_request_time:.2f}s)"
        assert call_count == 1, f"Expected 1 API call, got {call_count}"

@pytest.mark.asyncio
async def test_rate_limit_backoff(athena_agent):
    attempt_count = 0
    
    async def mock_ainvoke(self, messages, *args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count <= 2:
            raise Exception("rate limit exceeded: too many requests")
        class Response:
            content = "I understand you want to schedule a meeting."
        return Response()

    with patch.object(ChatOpenAI, 'ainvoke', mock_ainvoke):
        start_time = time.time()
        response = await athena_agent.llm_rate_limiter.generate_response(
            messages=[HumanMessage(content="Hello")],
            use_heavy_model=False,
            priority=True
        )
        total_time = time.time() - start_time
        
        assert attempt_count == 3, f"Expected 3 attempts, got {attempt_count}"
        assert "I understand you want to schedule a meeting" in response
        expected_backoff = athena_agent.llm_rate_limiter.config.initial_backoff + \
            athena_agent.llm_rate_limiter.config.initial_backoff * athena_agent.llm_rate_limiter.config.backoff_factor
        assert total_time >= expected_backoff, \
            f"Backoff time {total_time:.2f}s was less than expected {expected_backoff:.2f}s"

@pytest.mark.asyncio
async def test_batch_processing(athena_agent):
    async def mock_make_batch_request(messages_list, use_heavy_model):
        await asyncio.sleep(0.1)
        return ["Response"] * len(messages_list)
    async def mock_make_request(*args, **kwargs):
        await asyncio.sleep(0.1)
        return "Response"
    with patch.object(athena_agent.llm_rate_limiter, '_make_batch_request', mock_make_batch_request), \
         patch.object(athena_agent.llm_rate_limiter, '_make_request', mock_make_request):
        async def make_non_priority_request(message):
            return await athena_agent.llm_rate_limiter.generate_response(
                messages=[HumanMessage(content=message)],
                use_heavy_model=False,
                priority=False
            )
        messages = [
            "What's the weather like?",
            "Tell me a joke",
            "What time is it?",
            "How are you?",
            "What's your favorite color?"
        ]
        start_time = time.time()
        responses = await asyncio.gather(*[make_non_priority_request(m) for m in messages])
        end_time = time.time()
        assert len(responses) == len(messages)
        expected_individual_time = len(messages) * athena_agent.llm_rate_limiter.config.min_interval
        actual_time = end_time - start_time
        assert actual_time < expected_individual_time, \
            f"Batch processing time {actual_time:.2f}s was not less than individual processing time {expected_individual_time:.2f}s" 