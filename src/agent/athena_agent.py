"""
AthenaAgent: LangChain-powered Conversational AI Agent for Athena

Handles natural language understanding, context management, and OpenAI integration.
"""

from typing import Any, Dict, List, Optional
import re
import json
from langchain.schema import SystemMessage, HumanMessage
from src.database.supabase_client import SupabaseClient
from src.utils.conversation_manager import ConversationManager
from src.utils.llm_rate_limiter import LLMRateLimiter, RateLimitConfig

class AthenaAgent:
    """
    Conversational AI agent for Athena, powered by LangChain and OpenAI.
    Handles message processing, context, and prompt management.
    """
    def __init__(self):
        self.llm_rate_limiter = LLMRateLimiter(
            config=RateLimitConfig(
                min_interval=1.0,  # Reduced to 1 second for webhook responsiveness
                max_retries=1,  # Reduced retries to prevent webhook timeouts
                initial_backoff=1.0,  # Reduced backoff
                max_backoff=5.0,  # Much reduced max backoff  
                backoff_factor=1.5,  # Reduced backoff factor
                cache_ttl=1800,  # Reduced cache to 30 minutes
                max_batch_size=1,  # DISABLED BATCHING - process immediately
                batch_timeout=0.1,  # Minimal batch timeout (effectively disabled)
                circuit_breaker_threshold=5,  # Increased threshold to be less sensitive
                circuit_breaker_timeout=60.0  # Reduced to 1 minute timeout
            )
        )
        self.db_client = SupabaseClient()
        self.conversation_manager = ConversationManager()
        self.user_states = {}  # {telegram_id: state}
        self.meeting_details = {}  # {telegram_id: {topic: str, duration: int, time: str}}
        self._initialized = False

    async def initialize(self):
        """Initialize the agent and its components"""
        if not self._initialized:
            await self.llm_rate_limiter.initialize()
            self._initialized = True

    def _should_use_heavy_model(self, message: str, state: str) -> bool:
        """
        Determine if we should use GPT-4 based on message complexity and state.
        
        Args:
            message: The user's message
            state: Current conversation state
            
        Returns:
            bool: True if GPT-4 should be used
        """
        # Use GPT-4 for complex states
        if state in ["scheduling_meeting", "collecting_info"]:
            return True
            
        # Use GPT-4 for complex queries
        complex_patterns = [
            r"schedule.*meeting",
            r"plan.*meeting",
            r"set up.*call",
            r"organize.*session",
            r"arrange.*discussion",
            r"book.*appointment",
            r"reschedule",
            r"cancel.*meeting",
            r"change.*time",
            r"modify.*schedule"
        ]
        
        if any(re.search(pattern, message.lower()) for pattern in complex_patterns):
            return True
            
        # Use GPT-4 for error recovery
        if state == "error_recovery":
            return True
            
        # Default to GPT-3.5 for simple interactions
        return False

    def _is_priority_request(self, state: str) -> bool:
        """
        Determine if a request should be treated as high priority.
        
        Args:
            state: Current conversation state
            
        Returns:
            bool: True if request is high priority
        """
        # High priority states
        priority_states = [
            "error_recovery",
            "scheduling_meeting",
            "collecting_info"
        ]
        
        return state in priority_states

    async def extract_meeting_details(self, message: str) -> Dict[str, Any]:
        """
        Use LLMRateLimiter to extract meeting details from user message.
        """
        await self.initialize()
        
        # Use GPT-4 for meeting details extraction as it's more accurate
        messages = [
            SystemMessage(content="Extract meeting details from the user's message. Return a JSON object with topic, duration (in minutes), and time fields."),
            HumanMessage(content=message)
        ]
        
        response = await self.llm_rate_limiter.generate_response(
            messages=messages,
            use_heavy_model=True,  # Always use GPT-4 for meeting details
            priority=True  # High priority to maintain conversation flow
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"topic": None, "duration": None, "time": None}

    async def process_message(
        self,
        message: str,
        telegram_id: str,
        conversation_context: Optional[List[Dict[str, Any]]] = None,
        parsed_message: Optional[Any] = None,
        intent_keywords: Optional[Dict[str, bool]] = None
    ) -> str:
        """
        Process a user message and return the AI's response.
        """
        await self.initialize()

        # Use telegram_id from parsed_message if available
        if parsed_message and hasattr(parsed_message, "user") and hasattr(parsed_message.user, "telegram_id"):
            telegram_id = parsed_message.user.telegram_id
            
        if conversation_context is None:
            conversation_context = await self.conversation_manager.get_conversation_context(telegram_id, limit=5)
            
        is_returning = await self.check_contact_exists(telegram_id)
        user_name = getattr(parsed_message.user, "full_name", None) if parsed_message and hasattr(parsed_message, "user") else None
        
        # State management
        state = self.get_state(telegram_id)

        # Handle cancel intent - no LLM needed
        if intent_keywords and intent_keywords.get("cancel"):
            self.set_state(telegram_id, "idle")
            self.meeting_details.pop(telegram_id, None)  # Clear meeting details
            return "I've cancelled the current operation. How can I help you?"

        # Handle obvious intents without LLM
        if intent_keywords and intent_keywords.get("wants_meeting"):
            self.set_state(telegram_id, "scheduling_meeting")
            return self.build_meeting_info_prompt(telegram_id)
        elif intent_keywords and intent_keywords.get("providing_contact"):
            self.set_state(telegram_id, "collecting_info")
            return self.build_contact_collection_prompt(["name", "email"])

        # Determine if we should use GPT-4
        use_heavy_model = self._should_use_heavy_model(message, state)
        
        # Determine if this is a priority request
        priority = self._is_priority_request(state)

        # Build conversation context
        messages = self.build_conversation_messages(
            message=message,
            state=state,
            is_returning=is_returning,
            user_name=user_name,
            conversation_context=conversation_context
        )

        # Get response from LLM
        response = await self.llm_rate_limiter.generate_response(
            messages=messages,
            use_heavy_model=use_heavy_model,
            priority=priority
        )

        # Update state based on response
        self._update_state_from_response(telegram_id, response)

        return response

    def _update_state_from_response(self, telegram_id: str, response: str):
        """
        Update conversation state based on LLM response.
        """
        state = self.get_state(telegram_id)
        
        # State transition logic
        if state == "idle":
            if "schedule" in response.lower() or "meeting" in response.lower():
                self.set_state(telegram_id, "scheduling_meeting")
        elif state == "scheduling_meeting":
            if "confirmed" in response.lower() or "scheduled" in response.lower():
                self.set_state(telegram_id, "idle")
        elif state == "collecting_info":
            if "thank you" in response.lower() or "received" in response.lower():
                self.set_state(telegram_id, "idle")

    def build_conversation_messages(
        self,
        message: str,
        state: str,
        is_returning: bool,
        user_name: Optional[str],
        conversation_context: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Build the conversation messages for the LLM.
        """
        messages = []
        
        # Add system message based on state
        if state == "scheduling_meeting":
            messages.append(SystemMessage(content=(
                "You are helping schedule a meeting. Be friendly and conversational while gathering "
                "meeting details. Use natural language and occasional emojis to make the conversation "
                "more engaging. Focus on understanding the user's needs and confirming the schedule. "
                "Be proactive in suggesting optimal meeting durations and times if the user is unsure."
            )))
        elif state == "collecting_info":
            messages.append(SystemMessage(content=(
                "You are collecting contact information. Be warm and professional while gathering "
                "name and email. Use natural language and make the user feel comfortable sharing "
                "their information. Explain why you need each piece of information if asked."
            )))
        else:
            messages.append(SystemMessage(content=(
                "You are Athena, the executive assistant for Vin Perez, a senior manager. "
                "Be friendly but professional and direct to the point. Focus on efficiency "
                "while maintaining a warm, approachable demeanor. Use clear, concise language "
                "and avoid unnecessary pleasantries. Remember previous interactions and maintain "
                "context of conversations. Your primary goal is to help manage Vin's schedule, "
                "meetings, and communications effectively."
            )))
        
        # Add conversation context
        for ctx in conversation_context:
            if ctx["sender"] == "user":
                messages.append(HumanMessage(content=ctx["content"]))
            else:
                messages.append(SystemMessage(content=ctx["content"]))
        
        # Add current message
        messages.append(HumanMessage(content=message))
        
        return messages

    def get_state(self, telegram_id: str) -> str:
        """Get the current state for a user."""
        return self.user_states.get(telegram_id, "idle")

    def set_state(self, telegram_id: str, state: str):
        """Set the state for a user."""
        self.user_states[telegram_id] = state

    async def check_contact_exists(self, telegram_id: str) -> bool:
        """Check if a contact exists in the database."""
        contact = await self.db_client.get_contact_by_telegram_id(telegram_id)
        return bool(contact)

    def build_meeting_info_prompt(self, telegram_id: str) -> str:
        """Build a prompt for collecting meeting information."""
        return "I'll help you schedule a meeting. Please provide:\n1. Topic or purpose\n2. Preferred duration\n3. Preferred time"

    def build_contact_collection_prompt(self, fields: List[str]) -> str:
        """Build a prompt for collecting contact information."""
        return f"Please provide your {', '.join(fields)}."

    def update_meeting_details(self, telegram_id: str, new_details: Dict[str, Any]) -> None:
        """
        Update meeting details for a user, preserving existing information.
        """
        if telegram_id not in self.meeting_details:
            self.meeting_details[telegram_id] = {"topic": None, "duration": None, "time": None}
        
        # Only update fields that are not None in new_details
        for key, value in new_details.items():
            if value is not None:
                self.meeting_details[telegram_id][key] = value

    def get_missing_details(self, telegram_id: str) -> List[str]:
        """
        Get list of missing meeting details for a user.
        """
        if telegram_id not in self.meeting_details:
            return ["topic", "duration", "time"]
        
        details = self.meeting_details[telegram_id]
        return [key for key, value in details.items() if value is None]

    def build_meeting_info_prompt(self, telegram_id: str) -> str:
        """
        Build a friendly prompt asking for missing meeting details.
        """
        missing = self.get_missing_details(telegram_id)
        if not missing:
            return "Great! I have all the details I need. Let me check the calendar for available times."

        field_map = {
            "topic": "what this meeting is about",
            "duration": "how long the meeting should be (in minutes, e.g., 30 or 60)",
            "time": "when you'd like to have the meeting"
        }
        
        # Get existing details for context
        details = self.meeting_details.get(telegram_id, {})
        context = []
        if details.get("topic"):
            context.append(f"I know this meeting is about: {details['topic']}")
        if details.get("duration"):
            context.append(f"The meeting duration will be: {details['duration']} minutes")
        if details.get("time"):
            context.append(f"You're available at: {details['time']}")

        # Build the prompt
        prompt = "I'm helping you schedule a meeting. "
        if context:
            prompt += " ".join(context) + ". "
        
        if len(missing) == 1:
            prompt += f"Could you please let me know {field_map[missing[0]]}?"
        else:
            missing_fields = [field_map[m] for m in missing]
            prompt += f"I still need to know {', '.join(missing_fields[:-1])} and {missing_fields[-1]}."
        
        return prompt

    def build_intro_prompt(self, user_name: Optional[str] = None, returning: bool = False) -> str:
        if returning and user_name:
            return (
                f"Welcome back, {user_name}! 👋\n"
                "I'm Athena, your digital executive assistant.\n"
                "How can I assist you today?"
            )
        elif user_name:
            return (
                f"Hello {user_name}! I'm Athena, your digital executive assistant.\n"
                "I help coordinate meetings and manage contacts through natural conversation.\n"
                "How can I assist you today?"
            )
        else:
            return (
                "Hello! I'm Athena, your digital executive assistant. 🤖\n"
                "I help coordinate meetings and manage contacts through natural conversation.\n"
                "How can I assist you today?"
            )

    def validate_name(self, name: str) -> bool:
        return bool(name and 1 < len(name.strip()) <= 100)

    def validate_email(self, email: str) -> bool:
        pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        return bool(email and re.match(pattern, email))

    def validate_meeting_duration(self, duration: int) -> bool:
        return duration >= 15 and duration % 15 == 0 