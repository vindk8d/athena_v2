"""
ConversationManager for Athena Digital Executive Assistant.

Retrieves recent conversation history for context-aware AI responses.
"""
from typing import List, Dict, Any
from src.database.supabase_client import SupabaseClient

class ConversationManager:
    def __init__(self):
        self.db_client = SupabaseClient()

    async def get_conversation_context(self, telegram_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve the last N messages for a contact by Telegram ID, ordered chronologically.
        Returns a list of message dicts (oldest to newest).
        """
        # Look up contact
        contact = await self.db_client.get_contact_by_telegram_id(telegram_id)
        if not contact:
            return []
        contact_id = contact["id"]
        # Query messages
        try:
            response = self.db_client.supabase.table("messages") \
                .select("*") \
                .eq("contact_id", contact_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            messages = response.data or []
            # Return in chronological order (oldest to newest)
            return list(reversed(messages))
        except Exception as e:
            # Log error if needed
            return [] 