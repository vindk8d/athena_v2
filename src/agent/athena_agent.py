"""
AthenaAgent: LangChain-powered Conversational AI Agent for Athena

Handles natural language understanding, context management, and OpenAI integration.
"""

from typing import Any, Dict, List, Optional
import re
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from src.database.supabase_client import SupabaseClient
from src.utils.conversation_manager import ConversationManager

class AthenaAgent:
    """
    Conversational AI agent for Athena, powered by LangChain and OpenAI.
    Handles message processing, context, and prompt management.
    """
    def __init__(self):
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)  # Changed to gpt-3.5-turbo
        self.db_client = SupabaseClient()
        self.conversation_manager = ConversationManager()
        self.user_states = {}  # {telegram_id: state}
        self.meeting_details = {}  # {telegram_id: {topic: str, duration: int, time: str}}

    async def extract_meeting_details(self, message: str) -> Dict[str, Any]:
        """
        Use LangChain/OpenAI to extract meeting details from user message.
        """
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
            response = await self.llm.ainvoke(messages)
            # Parse the response as JSON
            import json
            details = json.loads(response.content)
            return details
        except Exception as e:
            print(f"[DEBUG] extract_meeting_details: error={e}")
            return {"topic": None, "duration": None, "time": None}

    def update_meeting_details(self, telegram_id: str, new_details: Dict[str, Any]) -> None:
        """
        Update meeting details for a user, preserving existing information.
        """
        if telegram_id not in self.meeting_details:
            self.meeting_details[telegram_id] = {"topic": None, "duration": None, "time": None}
        
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
        # Use telegram_id from parsed_message if available
        if parsed_message and hasattr(parsed_message, "user") and hasattr(parsed_message.user, "telegram_id"):
            telegram_id = parsed_message.user.telegram_id
        if conversation_context is None:
            conversation_context = await self.conversation_manager.get_conversation_context(telegram_id, limit=5)
        is_returning = await self.check_contact_exists(telegram_id)
        user_name = getattr(parsed_message.user, "full_name", None) if parsed_message and hasattr(parsed_message, "user") else None
        print(f"[DEBUG] process_message: telegram_id={telegram_id}, is_returning={is_returning}, user_name={user_name}")
        
        # State management
        state = self.get_state(telegram_id)
        print(f"[DEBUG] process_message: initial state={state}")

        # Handle cancel intent
        if intent_keywords and intent_keywords.get("cancel"):
            self.set_state(telegram_id, "idle")
            self.meeting_details.pop(telegram_id, None)  # Clear meeting details
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
            # Extract meeting details using LangChain/OpenAI
            meeting_details = await self.extract_meeting_details(message)
            
            # Update stored meeting details
            self.update_meeting_details(telegram_id, meeting_details)
            
            # Check if we have all required information
            missing = self.get_missing_details(telegram_id)
            if missing:
                return self.build_meeting_info_prompt(telegram_id)
            
            # If we have all required information, show time options
            options = ["Tomorrow at 10:00 AM", "Tomorrow at 2:00 PM", "The day after at 11:00 AM"]
            return self.build_meeting_scheduling_prompt(options)
        if state == "confirmation":
            return "Your meeting has been scheduled! Here are the details:\n" + self.build_meeting_scheduling_prompt(["Your meeting details here"])
        return "I'm here to help you schedule meetings or update your contact info. How can I assist you today?"

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