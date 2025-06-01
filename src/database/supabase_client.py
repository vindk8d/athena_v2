"""
Supabase Client for Athena Digital Executive Assistant.

Handles async CRUD operations for contacts, messages, and user_details tables.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from supabase import create_client, Client
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def _now_utc() -> str:
    """Return current UTC time as ISO string."""
    return datetime.utcnow().isoformat() + "Z"


class SupabaseClient:
    """
    Async Supabase client for Athena.
    Handles contacts, messages, and user_details operations.
    """
    def __init__(self):
        settings = get_settings()
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key or settings.supabase_anon_key
        )

    async def get_or_create_contact_by_telegram_id(self, telegram_id: str, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get or create a contact by Telegram ID.
        Args:
            telegram_id: Telegram user ID as string
            user_data: Optional dict with name, email, username, etc.
        Returns:
            Contact row as dict
        """
        # Try to find existing contact
        try:
            response = self.supabase.table("contacts").select("*").eq("telegram_id", telegram_id).execute()
            data = response.data
            if data and len(data) > 0:
                return data[0]
        except Exception as e:
            logger.error(f"Error fetching contact: {e}")
            # Continue to creation
        # Prepare new contact data
        contact = {
            "id": str(uuid.uuid4()),
            "telegram_id": telegram_id,
            "created_at": _now_utc(),
            "updated_at": _now_utc(),
        }
        if user_data:
            for key in ["name", "email", "username", "first_name", "last_name", "language_code"]:
                if key in user_data and user_data[key]:
                    contact[key] = user_data[key]
            # Prefer full_name or name
            if "full_name" in user_data and user_data["full_name"]:
                contact["name"] = user_data["full_name"]
        if "name" not in contact or not contact["name"]:
            contact["name"] = f"Telegram User {telegram_id}"
        # Insert new contact
        try:
            response = self.supabase.table("contacts").insert(contact).execute()
            data = response.data
            if data and len(data) > 0:
                return data[0]
            else:
                logger.error("Failed to insert new contact")
                raise Exception("Contact creation failed")
        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            raise

    async def create_message(self, contact_id: str, sender: str, channel: str, content: str, metadata: Optional[Dict[str, Any]] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new message row in the messages table.
        Args:
            contact_id: UUID of the contact
            sender: 'user' or 'assistant'
            channel: 'telegram'
            content: Message text
            metadata: Optional dict (will be stored as JSONB)
            status: Optional message status
        Returns:
            Message row as dict
        """
        message = {
            "id": str(uuid.uuid4()),
            "contact_id": contact_id,
            "sender": sender,
            "channel": channel,
            "content": content,
            "created_at": _now_utc(),
        }
        if metadata:
            message["metadata"] = metadata
        if status:
            message["status"] = status
        try:
            response = self.supabase.table("messages").insert(message).execute()
            data = response.data
            if data and len(data) > 0:
                return data[0]
            else:
                logger.error("Failed to insert new message")
                raise Exception("Message creation failed")
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            raise 