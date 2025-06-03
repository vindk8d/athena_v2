"""
LLM Rate Limiter: Manages OpenAI API rate limits and model selection
"""

import asyncio
import time
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import hashlib
import logging

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    min_interval: float = 0.7  # Set to 0.7 seconds to support ~85 RPM (with safety buffer for 100 RPM limit)
    max_retries: int = 2  # Reduced retries for quota errors
    initial_backoff: float = 2.0
    max_backoff: float = 60.0  # Increased max backoff
    backoff_factor: float = 2.0
    cache_ttl: int = 3600  # Cache TTL in seconds
    max_batch_size: int = 3  # Reduced batch size
    batch_timeout: float = 5.0  # Increased batch timeout
    circuit_breaker_threshold: int = 3  # Number of consecutive quota errors before circuit breaker
    circuit_breaker_timeout: float = 300.0  # 5 minutes

class QuotaExceededError(Exception):
    """Raised when OpenAI quota is exceeded"""
    pass

class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass

class LLMRateLimiter:
    """
    Manages rate limiting and model selection for LLM calls.
    Implements exponential backoff, request queuing, response caching, and circuit breaker.
    """
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.light_model = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.4)
        self.heavy_model = ChatOpenAI(model_name="gpt-4", temperature=0.4)
        self.last_request_time: float = 0
        self.lock = asyncio.Lock()
        self.queue = asyncio.Queue()
        self._queue_processor_task = None
        self._response_cache: Dict[str, Tuple[str, float]] = {}  # hash -> (response, timestamp)
        self._batch_queue: List[Tuple[asyncio.Future, List[Any], bool]] = []
        self._batch_processor_task = None
        
        # Circuit breaker state
        self._quota_error_count = 0
        self._circuit_breaker_open = False
        self._circuit_breaker_opened_at = 0.0

    def _is_quota_error(self, error_str: str) -> bool:
        """Check if error is related to quota/billing"""
        quota_indicators = [
            "insufficient_quota",
            "quota exceeded",
            "billing",
            "exceeded your current quota"
        ]
        return any(indicator in error_str.lower() for indicator in quota_indicators)

    def _is_rate_limit_error(self, error_str: str) -> bool:
        """Check if error is a rate limit (not quota) error"""
        rate_limit_indicators = [
            "rate limit",
            "too many requests",
            "requests per minute",
            "requests per second", 
            "rate limited",
            "throttled"
        ]
        return any(indicator in error_str.lower() for indicator in rate_limit_indicators) and not self._is_quota_error(error_str)

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should open or close"""
        current_time = time.time()
        
        # Check if circuit breaker should reset
        if self._circuit_breaker_open:
            if current_time - self._circuit_breaker_opened_at > self.config.circuit_breaker_timeout:
                logger.info("Circuit breaker timeout reached, resetting...")
                self._circuit_breaker_open = False
                self._quota_error_count = 0
                return False
            return True
        
        # Check if circuit breaker should open
        if self._quota_error_count >= self.config.circuit_breaker_threshold:
            logger.warning(f"Circuit breaker opening due to {self._quota_error_count} consecutive quota errors")
            self._circuit_breaker_open = True
            self._circuit_breaker_opened_at = current_time
            return True
        
        return False

    def _get_fallback_response(self, message_content: str) -> str:
        """Generate a fallback response when OpenAI is unavailable"""
        # Simple pattern matching for common requests
        content_lower = message_content.lower()
        
        if any(word in content_lower for word in ["schedule", "meeting", "book", "appointment"]):
            return (
                "Hey! I'd love to help you schedule that meeting. 😊 I'm just taking a quick breather "
                "to handle some high demand, but I'll be back in a moment to help you out.\n\n"
                "While you wait, could you share:\n"
                "• What's the meeting about?\n"
                "• How long would you like it to be? (15, 30, 45, or 60 minutes)\n"
                "• Any preferred time that works for you?\n\n"
                "I'll make sure to get this scheduled for you as soon as I'm back at full speed! 🚀"
            )
        
        elif any(word in content_lower for word in ["hello", "hi", "start", "help"]):
            return (
                "Hi there! 👋 I'm Athena, your friendly digital assistant. I'm just taking a quick "
                "break to handle some high traffic, but I'm still here to help! I can assist you with:\n\n"
                "• Scheduling meetings and appointments\n"
                "• Managing your contact information\n"
                "• Coordinating calendar availability\n\n"
                "What can I help you with today? I'll be back at full speed in just a moment! ✨"
            )
        
        elif any(word in content_lower for word in ["cancel", "reschedule", "change"]):
            return (
                "I understand you need to make some changes to your schedule. I'm just taking a quick "
                "break to handle some high demand, but I want to make sure I help you with this! 😊\n\n"
                "Could you share what changes you'd like to make? I'll make sure to handle them as soon "
                "as I'm back at full speed. Your schedule is important to me! 📅"
            )
        
        else:
            return (
                "Hey! I'm just taking a quick breather to handle some high demand, but I'm still here "
                "to help! 😊 I can still assist you with basic tasks while I recover, and I'll be back "
                "at full speed in just a moment.\n\n"
                "What can I help you with? I'm all ears! 👂"
            )

    async def initialize(self):
        """Initialize the rate limiter and start the queue processors"""
        if self._queue_processor_task is None:
            self._queue_processor_task = asyncio.create_task(self._process_queue())
        if self._batch_processor_task is None:
            self._batch_processor_task = asyncio.create_task(self._process_batches())

    def _get_cache_key(self, messages: List[Any], use_heavy_model: bool) -> str:
        """Generate a cache key for the messages"""
        def serialize_message(m):
            if hasattr(m, 'model_dump'):
                return m.model_dump()
            elif hasattr(m, 'dict'):
                return m.dict()
            else:
                return str(m)
        message_str = json.dumps([serialize_message(m) for m in messages])
        return hashlib.md5(f"{message_str}:{use_heavy_model}".encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get a cached response if it exists and is not expired"""
        if cache_key in self._response_cache:
            response, timestamp = self._response_cache[cache_key]
            if time.time() - timestamp < self.config.cache_ttl:
                return response
            else:
                del self._response_cache[cache_key]
        return None

    def _cache_response(self, cache_key: str, response: str):
        """Cache a response with current timestamp"""
        self._response_cache[cache_key] = (response, time.time())

    async def _process_batches(self):
        """Process batched requests in the background"""
        while True:
            try:
                if self._batch_queue:
                    # Wait for batch timeout or max size
                    await asyncio.sleep(self.config.batch_timeout)
                    
                    # Process current batch
                    current_batch = self._batch_queue[:self.config.max_batch_size]
                    self._batch_queue = self._batch_queue[self.config.max_batch_size:]
                    
                    # Group by model type
                    light_requests = []
                    heavy_requests = []
                    for future, messages, use_heavy_model in current_batch:
                        if use_heavy_model:
                            heavy_requests.append((future, messages))
                        else:
                            light_requests.append((future, messages))
                    
                    # Process light model requests
                    if light_requests:
                        try:
                            responses = await self._make_batch_request(
                                [m for _, m in light_requests],
                                use_heavy_model=False
                            )
                            for (future, _), response in zip(light_requests, responses):
                                future.set_result(response)
                        except Exception as e:
                            for future, _ in light_requests:
                                future.set_exception(e)
                    
                    # Process heavy model requests
                    if heavy_requests:
                        try:
                            responses = await self._make_batch_request(
                                [m for _, m in heavy_requests],
                                use_heavy_model=True
                            )
                            for (future, _), response in zip(heavy_requests, responses):
                                future.set_result(response)
                        except Exception as e:
                            for future, _ in heavy_requests:
                                future.set_exception(e)
                
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error processing batch: {e}")

    async def _make_batch_request(
        self,
        messages_list: List[List[Any]],
        use_heavy_model: bool
    ) -> List[str]:
        """Make a batch request to the LLM"""
        # Check circuit breaker
        if self._check_circuit_breaker():
            raise CircuitBreakerError("Circuit breaker is open due to quota errors")
        
        async with self.lock:
            await self._wait_for_rate_limit()
            
            model = self.heavy_model if use_heavy_model else self.light_model
            responses = []
            
            for messages in messages_list:
                try:
                    response = await model.ainvoke(messages)
                    responses.append(response.content)
                    # Reset quota error count on successful request
                    self._quota_error_count = 0
                except Exception as e:
                    error_str = str(e)
                    if self._is_quota_error(error_str):
                        self._quota_error_count += 1
                        logger.error(f"Quota error in batch request: {e}")
                        raise QuotaExceededError(f"OpenAI quota exceeded: {e}")
                    elif self._is_rate_limit_error(error_str):
                        logger.warning(f"Rate limit hit in batch, waiting {self.config.min_interval} seconds")
                        await asyncio.sleep(self.config.min_interval)
                        response = await model.ainvoke(messages)
                        responses.append(response.content)
                    else:
                        raise
            
            self.last_request_time = time.time()
            return responses

    async def _process_queue(self):
        """Process queued requests in the background"""
        while True:
            try:
                future, messages, use_heavy_model = await self.queue.get()
                try:
                    result = await self._make_request(messages, use_heavy_model)
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
                finally:
                    self.queue.task_done()
            except Exception as e:
                print(f"Error processing queue: {e}")
            await asyncio.sleep(0.1)

    async def _wait_for_rate_limit(self):
        """Wait until enough time has passed since the last request"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.config.min_interval:
            wait_time = self.config.min_interval - time_since_last
            await asyncio.sleep(wait_time)

    async def _make_request(
        self,
        messages: List[Any],
        use_heavy_model: bool = False,
        priority: bool = True
    ) -> str:
        """
        Make an LLM request with rate limiting and exponential backoff.
        
        Args:
            messages: List of messages to send to the LLM
            use_heavy_model: Whether to use GPT-4 (True) or GPT-3.5 (False)
            priority: Whether this is a high-priority request that should bypass the queue
            
        Returns:
            The LLM response
        """
        # Check circuit breaker first
        if self._check_circuit_breaker():
            logger.warning("Circuit breaker is open, providing fallback response")
            # Extract message content for fallback
            message_content = ""
            for msg in messages:
                if hasattr(msg, 'content'):
                    message_content = msg.content
                    break
            return self._get_fallback_response(message_content)
        
        # Check cache first
        cache_key = self._get_cache_key(messages, use_heavy_model)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response

        # Always process user messages immediately (no batching/delays)
        if priority:
            async with self.lock:
                await self._wait_for_rate_limit()
                
                # Try the request with exponential backoff
                backoff = self.config.initial_backoff
                for attempt in range(self.config.max_retries + 1):
                    try:
                        model = self.heavy_model if use_heavy_model else self.light_model
                        response = await model.ainvoke(messages)
                        self.last_request_time = time.time()
                        
                        # Reset quota error count on successful request
                        self._quota_error_count = 0
                        
                        # Cache the response
                        self._cache_response(cache_key, response.content)
                        
                        return response.content
                        
                    except Exception as e:
                        error_str = str(e)
                        logger.error(f"Error in _make_request (attempt {attempt + 1}): {e}")
                        
                        if self._is_quota_error(error_str):
                            self._quota_error_count += 1
                            logger.error(f"Quota error detected (count: {self._quota_error_count}): {e}")
                            # Don't retry quota errors, raise immediately
                            raise QuotaExceededError(f"OpenAI quota exceeded: {e}")
                        
                        elif self._is_rate_limit_error(error_str):
                            if attempt < self.config.max_retries:
                                wait_time = min(backoff, self.config.max_backoff)
                                logger.warning(f"Rate limit hit, waiting {wait_time:.1f} seconds before retry")
                                await asyncio.sleep(wait_time)
                                backoff *= self.config.backoff_factor
                                continue
                            else:
                                logger.error(f"Max retries exceeded for rate limit: {e}")
                                raise
                        else:
                            # Other errors - don't retry
                            logger.error(f"Non-recoverable error: {e}")
                            raise
        else:
            # Queue low-priority requests
            future = asyncio.Future()
            await self.queue.put((future, messages, use_heavy_model))
            return await future

    async def extract_meeting_details(self, message: str) -> Dict[str, Any]:
        """
        Extract meeting details using the light model.
        """
        await self.initialize()  # Ensure queue processor is running
        
        system_prompt = """You are a meeting details extraction assistant. Extract meeting details from the user's message.
        Return a JSON object with the following fields:
        - topic: The meeting topic/purpose (string)
        - duration: Meeting duration in minutes (integer, must be divisible by 15)
        - time: Preferred meeting time (string in 12-hour format with AM/PM)
        
        If a field is not mentioned, set it to null.
        For duration, if user says "default", use 60 minutes.
        For time, extract the time mentioned in 12-hour format (e.g., "9:00 AM").
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ]
        
        try:
            response = await self._make_request(messages, use_heavy_model=False)
            import json
            return json.loads(response)
        except (QuotaExceededError, CircuitBreakerError) as e:
            logger.warning(f"Using fallback for meeting details extraction: {e}")
            # Fallback to regex for time extraction
            import re
            time_pattern = r'(?:at|by|around|about)?\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))'
            time_match = re.search(time_pattern, message, re.IGNORECASE)
            
            # Simple topic extraction
            topic = None
            topic_keywords = ["meeting", "call", "discussion", "session", "sync", "standup", "review"]
            for keyword in topic_keywords:
                if keyword in message.lower():
                    topic = f"{keyword.title()} discussion"
                    break
            
            # Duration extraction
            duration = None
            duration_patterns = [
                (r'(\d+)\s*(?:hour|hr)s?', lambda m: int(m.group(1)) * 60),
                (r'(\d+)\s*(?:minute|min)s?', lambda m: int(m.group(1))),
                (r'half\s*hour', lambda m: 30),
                (r'quarter\s*hour', lambda m: 15)
            ]
            for pattern, extractor in duration_patterns:
                match = re.search(pattern, message.lower())
                if match:
                    duration = extractor(match)
                    break
            
            return {
                "topic": topic,
                "duration": duration,
                "time": time_match.group(1) if time_match else None
            }
        except Exception as e:
            logger.error(f"extract_meeting_details: error={e}")
            return {"topic": None, "duration": None, "time": None}

    async def generate_response(
        self,
        messages: List[Any],
        use_heavy_model: bool = False,
        priority: bool = True
    ) -> str:
        """
        Generate a response using the specified model.
        
        Args:
            messages: List of messages to send to the LLM
            use_heavy_model: Whether to use GPT-4 (True) or GPT-3.5 (False)
            priority: Whether this is a high-priority request
            
        Returns:
            The generated response
        """
        await self.initialize()  # Ensure queue processor is running
        
        try:
            # For non-priority requests, add to batch queue
            if not priority:
                future = asyncio.Future()
                self._batch_queue.append((future, messages, use_heavy_model))
                return await future
            
            # Try the request with exponential backoff
            backoff = self.config.initial_backoff
            for attempt in range(self.config.max_retries + 1):
                try:
                    return await self._make_request(messages, use_heavy_model, priority)
                except Exception as e:
                    error_str = str(e)
                    if self._is_rate_limit_error(error_str):
                        if attempt < self.config.max_retries:
                            wait_time = min(backoff, self.config.max_backoff)
                            logger.warning(f"Rate limit hit, waiting {wait_time:.1f} seconds before retry")
                            await asyncio.sleep(wait_time)
                            backoff *= self.config.backoff_factor
                            continue
                    elif self._is_quota_error(error_str):
                        self._quota_error_count += 1
                        logger.error(f"Quota error detected (count: {self._quota_error_count}): {e}")
                        raise QuotaExceededError(f"OpenAI quota exceeded: {e}")
                    raise
            
            # If we get here, all retries failed
            raise Exception("Max retries exceeded")
            
        except (QuotaExceededError, CircuitBreakerError) as e:
            logger.warning(f"Using fallback response due to: {e}")
            # Extract message content for fallback
            message_content = ""
            for msg in messages:
                if hasattr(msg, 'content'):
                    message_content = msg.content
                    break
            return self._get_fallback_response(message_content)

    async def shutdown(self):
        """Shutdown the queue processor tasks if running."""
        for task in [self._queue_processor_task, self._batch_processor_task]:
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
        self._queue_processor_task = None
        self._batch_processor_task = None 