"""
AthenaAgent: LangChain-powered Conversational AI Agent for Athena

Handles natural language understanding, context management, and OpenAI integration.
"""

from typing import Any, Dict, List, Optional
import re

# from langchain.chat_models import ChatOpenAI  # Uncomment when LangChain is configured
# from langchain.schema import HumanMessage, SystemMessage
from src.database.supabase_client import SupabaseClient
from src.utils.conversation_manager import ConversationManager

class AthenaAgent:
    """
    Conversational AI agent for Athena, powered by LangChain and OpenAI.
    Handles message processing, context, and prompt management.
    """
    def __init__(self):
        # self.llm = ChatOpenAI(model_name="gpt-4", temperature=0.7)  # Example
        self.db_client = SupabaseClient()
        self.conversation_manager = ConversationManager()
        self.user_states = {}  # {telegram_id: state}

    async def check_contact_exists(self, telegram_id: str) -> bool:
        """
        Check if a contact exists in Supabase by Telegram ID.
        """
        try:
            print(f"[DEBUG] check_contact_exists: calling get_contact_by_telegram_id with telegram_id={telegram_id}")
            contact = await self.db_client.get_contact_by_telegram_id(telegram_id)
            print(f"[DEBUG] check_contact_exists: result={contact}")
            return contact is not None
        except Exception as e:
            print(f"[DEBUG] check_contact_exists: exception={e}")
            return False

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

    def build_contact_collection_prompt(self, missing_fields: List[str]) -> str:
        field_map = {
            "name": "your name",
            "email": "your email address",
            "telegram_id": "your Telegram username or ID"
        }
        fields = ', '.join([field_map.get(f, f) for f in missing_fields])
        return (
            f"I still need {fields} to complete your contact information.\n"
            "Please provide the missing details so I can assist you further."
        )

    def build_meeting_scheduling_prompt(self, options: List[str]) -> str:
        options_text = '\n'.join([f"• {opt}" for opt in options])
        return (
            "Here are some available meeting times:\n"
            f"{options_text}\n"
            "Please let me know which one works best for you, or suggest another time."
        )

    def build_meeting_info_prompt(self, missing_fields: list) -> str:
        field_map = {
            "topic": "the meeting topic or purpose",
            "duration": "the meeting duration (in minutes, e.g., 30 or 60)",
            "time": "your preferred meeting time or availability"
        }
        fields = ', '.join([field_map.get(f, f) for f in missing_fields])
        return (
            f"To schedule your meeting, I still need {fields}.\n"
            "Please provide the missing details so I can suggest times and book your meeting."
        )

    def get_state(self, telegram_id: str) -> str:
        return self.user_states.get(telegram_id, "idle")

    def set_state(self, telegram_id: str, state: str):
        self.user_states[telegram_id] = state

    def validate_name(self, name: str) -> bool:
        return bool(name and 1 < len(name.strip()) <= 100)

    def validate_email(self, email: str) -> bool:
        pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        return bool(email and re.match(pattern, email))

    def validate_meeting_duration(self, duration: int) -> bool:
        return duration >= 15 and duration % 15 == 0

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
        Args:
            message: The user's message text
            telegram_id: Telegram user ID
            conversation_context: List of previous messages for context
            parsed_message: ParsedMessage object (optional)
            intent_keywords: Dict of detected intent flags (optional)
        Returns:
            AI-generated response as a string
        """
        # Use telegram_id from parsed_message if available
        if parsed_message and hasattr(parsed_message, "user") and hasattr(parsed_message.user, "telegram_id"):
            telegram_id = parsed_message.user.telegram_id
        if conversation_context is None:
            conversation_context = await self.conversation_manager.get_conversation_context(telegram_id, limit=5)
        is_returning = await self.check_contact_exists(telegram_id)
        user_name = getattr(parsed_message.user, "full_name", None) if parsed_message and hasattr(parsed_message, "user") else None
        print(f"[DEBUG] process_message: telegram_id={telegram_id}, is_returning={is_returning}, user_name={user_name}")
        # State management: only set if not already set to a meaningful value
        state = self.get_state(telegram_id)
        print(f"[DEBUG] process_message: initial state={state}")

        # Handle cancel intent
        if intent_keywords and intent_keywords.get("cancel"):
            self.set_state(telegram_id, "idle")
            state = "idle"

        # Always check for scheduling intent first
        elif intent_keywords and intent_keywords.get("wants_meeting"):
            self.set_state(telegram_id, "scheduling_meeting")
            state = "scheduling_meeting"
        # Always check for collecting_info intent
        elif intent_keywords and intent_keywords.get("providing_contact"):
            self.set_state(telegram_id, "collecting_info")
            state = "collecting_info"
        elif state in (None, "idle"):
            if intent_keywords:
                if not is_returning:
                    self.set_state(telegram_id, "new_contact")
                    state = "new_contact"
                else:
                    self.set_state(telegram_id, "returning_contact")
                    state = "returning_contact"
            else:
                if not is_returning:
                    self.set_state(telegram_id, "new_contact")
                    state = "new_contact"
                else:
                    self.set_state(telegram_id, "returning_contact")
                    state = "returning_contact"
        # Reset to idle if state is not recognized
        elif state not in [
            "idle", "new_contact", "returning_contact", "collecting_info", "scheduling_meeting", "confirmation"
        ]:
            self.set_state(telegram_id, "idle")
            state = "idle"
        # Always get the latest state
        state = self.get_state(telegram_id)
        print(f"[DEBUG] process_message: final state={state}")
        if state == "new_contact":
            return self.build_intro_prompt(user_name, returning=False)
        if state == "returning_contact":
            return self.build_intro_prompt(user_name, returning=True)
        if state == "collecting_info":
            name = getattr(parsed_message.user, "full_name", None) if parsed_message and hasattr(parsed_message, "user") else None
            email = getattr(parsed_message.user, "email", None) if parsed_message and hasattr(parsed_message, "user") else None
            telegram_id_val = getattr(parsed_message.user, "telegram_id", None) if parsed_message and hasattr(parsed_message, "user") else None
            missing = []
            if not name or not self.validate_name(name):
                missing.append("name")
            if not email or not self.validate_email(email):
                missing.append("email")
            if not telegram_id_val:
                missing.append("telegram_id")
            if missing:
                return self.build_contact_collection_prompt(missing)
            return "Thank you for providing your contact information!"
        if state == "scheduling_meeting":
            topic = getattr(parsed_message, "topic", None) if parsed_message else None
            duration = getattr(parsed_message, "duration", None) if parsed_message else None
            time = getattr(parsed_message, "time", None) if parsed_message else None
            missing = []
            if not topic:
                missing.append("topic")
            if not duration or not self.validate_meeting_duration(duration):
                missing.append("duration")
            if not time:
                missing.append("time")
            if missing:
                return self.build_meeting_info_prompt(missing)
            options = ["Tomorrow at 10:00 AM", "Tomorrow at 2:00 PM", "The day after at 11:00 AM"]
            return self.build_meeting_scheduling_prompt(options)
        if state == "confirmation":
            return "Your meeting has been scheduled! Here are the details:\n" + self.build_meeting_scheduling_prompt(["Your meeting details here"])
        return "I'm here to help you schedule meetings or update your contact info. How can I assist you today?" 