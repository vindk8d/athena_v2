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

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    min_interval: float = 20.0  # Minimum seconds between requests
    max_retries: int = 3
    initial_backoff: float = 1.0
    max_backoff: float = 32.0
    backoff_factor: float = 2.0
    cache_ttl: int = 3600  # Cache TTL in seconds
    max_batch_size: int = 5  # Maximum number of requests to batch
    batch_timeout: float = 2.0  # Maximum time to wait for batch in seconds

class LLMRateLimiter:
    """
    Manages rate limiting and model selection for LLM calls.
    Implements exponential backoff, request queuing, and response caching.
    """
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.light_model = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
        self.heavy_model = ChatOpenAI(model_name="gpt-4", temperature=0)
        self.last_request_time: float = 0
        self.lock = asyncio.Lock()
        self.queue = asyncio.Queue()
        self._queue_processor_task = None
        self._response_cache: Dict[str, Tuple[str, float]] = {}  # hash -> (response, timestamp)
        self._batch_queue: List[Tuple[asyncio.Future, List[Any], bool]] = []
        self._batch_processor_task = None

    async def initialize(self):
        """Initialize the rate limiter and start the queue processors"""
        if self._queue_processor_task is None:
            self._queue_processor_task = asyncio.create_task(self._process_queue())
        if self._batch_processor_task is None:
            self._batch_processor_task = asyncio.create_task(self._process_batches())

    def _get_cache_key(self, messages: List[Any], use_heavy_model: bool) -> str:
        """Generate a cache key for the messages"""
        message_str = json.dumps([m.dict() if hasattr(m, 'dict') else str(m) for m in messages])
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
        async with self.lock:
            await self._wait_for_rate_limit()
            
            model = self.heavy_model if use_heavy_model else self.light_model
            responses = []
            
            for messages in messages_list:
                try:
                    response = await model.ainvoke(messages)
                    responses.append(response.content)
                except Exception as e:
                    if "rate limit" in str(e).lower():
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
        # Check cache first
        cache_key = self._get_cache_key(messages, use_heavy_model)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response

        if not priority:
            # Queue low-priority requests
            future = asyncio.Future()
            await self.queue.put((future, messages, use_heavy_model))
            return await future

        async with self.lock:
            await self._wait_for_rate_limit()
            
            # Try the request with exponential backoff
            backoff = self.config.initial_backoff
            for attempt in range(self.config.max_retries):
                try:
                    model = self.heavy_model if use_heavy_model else self.light_model
                    response = await model.ainvoke(messages)
                    self.last_request_time = time.time()
                    
                    # Cache the response
                    self._cache_response(cache_key, response.content)
                    
                    return response.content
                except Exception as e:
                    if "rate limit" in str(e).lower() or "insufficient_quota" in str(e).lower():
                        if attempt < self.config.max_retries - 1:
                            wait_time = min(backoff, self.config.max_backoff)
                            print(f"[DEBUG] Rate limit hit, waiting {wait_time:.1f} seconds before retry")
                            await asyncio.sleep(wait_time)
                            backoff *= self.config.backoff_factor
                        else:
                            raise
                    else:
                        raise

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
        except Exception as e:
            print(f"[DEBUG] extract_meeting_details: error={e}")
            # Fallback to regex for time extraction
            import re
            time_pattern = r'(?:at|by|around|about)?\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))'
            time_match = re.search(time_pattern, message, re.IGNORECASE)
            if time_match:
                return {"topic": None, "duration": None, "time": time_match.group(1)}
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
        
        # For non-priority requests, add to batch queue
        if not priority:
            future = asyncio.Future()
            self._batch_queue.append((future, messages, use_heavy_model))
            return await future
        
        return await self._make_request(messages, use_heavy_model, priority)

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