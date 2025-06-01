"""
LLM Rate Limiter: Manages OpenAI API rate limits and model selection
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    min_interval: float = 20.0  # Minimum seconds between requests
    max_retries: int = 3
    initial_backoff: float = 1.0
    max_backoff: float = 32.0
    backoff_factor: float = 2.0

class LLMRateLimiter:
    """
    Manages rate limiting and model selection for LLM calls.
    Implements exponential backoff and request queuing.
    """
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.light_model = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
        self.heavy_model = ChatOpenAI(model_name="gpt-4", temperature=0)
        self.last_request_time: float = 0
        self.lock = asyncio.Lock()
        self.queue = asyncio.Queue()
        self._queue_processor_task = None

    async def initialize(self):
        """Initialize the rate limiter and start the queue processor"""
        if self._queue_processor_task is None:
            self._queue_processor_task = asyncio.create_task(self._process_queue())

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
        return await self._make_request(messages, use_heavy_model, priority)

    async def shutdown(self):
        """Shutdown the queue processor task if running."""
        if self._queue_processor_task is not None:
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._queue_processor_task = None 