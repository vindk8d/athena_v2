"""Contact management for Athena Digital Executive Assistant."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from src.database.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


@dataclass
class Contact:
    """Contact information."""
    id: str
    user_id: str
    name: str
    email: str
    telegram_id: str
    phone: Optional[str]
    company: Optional[str]
    notes: Optional[str]
    last_interaction: datetime
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


class ContactManager:
    """Manages contacts in the database."""
    
    def __init__(self, supabase_client: Optional[SupabaseClient] = None):
        """Initialize the contact manager."""
        self.supabase = supabase_client or SupabaseClient()
    
    async def get_contact(self, contact_id: str) -> Optional[Contact]:
        """
        Get a contact by ID.
        
        Args:
            contact_id: Contact ID to get
            
        Returns:
            Contact object if found, None otherwise
        """
        try:
            response = await self.supabase.table('contacts').select('*').eq('id', contact_id).execute()
            
            if not response.data:
                logger.warning(f"No contact found with ID {contact_id}")
                return None
            
            data = response.data[0]
            return self._parse_contact(data)
            
        except Exception as e:
            logger.error(f"Error getting contact: {e}")
            return None
    
    async def get_contact_by_telegram_id(self, telegram_id: str) -> Optional[Contact]:
        """
        Get a contact by Telegram ID.
        
        Args:
            telegram_id: Telegram ID to search for
            
        Returns:
            Contact object if found, None otherwise
        """
        try:
            response = await self.supabase.table('contacts').select('*').eq('telegram_id', telegram_id).execute()
            
            if not response.data:
                logger.warning(f"No contact found with Telegram ID {telegram_id}")
                return None
            
            data = response.data[0]
            return self._parse_contact(data)
            
        except Exception as e:
            logger.error(f"Error getting contact by Telegram ID: {e}")
            return None
    
    async def get_contacts_by_user(self, user_id: str) -> List[Contact]:
        """
        Get all contacts for a user.
        
        Args:
            user_id: User ID to get contacts for
            
        Returns:
            List of Contact objects
        """
        try:
            response = await self.supabase.table('contacts').select('*').eq('user_id', user_id).execute()
            
            if not response.data:
                return []
            
            return [self._parse_contact(data) for data in response.data]
            
        except Exception as e:
            logger.error(f"Error getting contacts by user: {e}")
            return []
    
    async def create_contact(
        self,
        user_id: str,
        name: str,
        email: str,
        telegram_id: str,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Contact]:
        """
        Create a new contact.
        
        Args:
            user_id: User ID to associate with the contact
            name: Contact name
            email: Contact email
            telegram_id: Contact Telegram ID
            phone: Contact phone number (optional)
            company: Contact company (optional)
            notes: Contact notes (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Created Contact object if successful, None otherwise
        """
        try:
            now = datetime.now().isoformat()
            data = {
                'user_id': user_id,
                'name': name,
                'email': email,
                'telegram_id': telegram_id,
                'phone': phone,
                'company': company,
                'notes': notes,
                'last_interaction': now,
                'created_at': now,
                'updated_at': now,
                'metadata': metadata or {}
            }
            
            response = await self.supabase.table('contacts').insert(data).execute()
            
            if not response.data:
                logger.error("Failed to create contact")
                return None
            
            return self._parse_contact(response.data[0])
            
        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            return None
    
    async def update_contact(
        self,
        contact_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        telegram_id: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Contact]:
        """
        Update an existing contact.
        
        Args:
            contact_id: Contact ID to update
            name: New name (optional)
            email: New email (optional)
            telegram_id: New Telegram ID (optional)
            phone: New phone number (optional)
            company: New company (optional)
            notes: New notes (optional)
            metadata: New metadata (optional)
            
        Returns:
            Updated Contact object if successful, None otherwise
        """
        try:
            data = {}
            
            if name is not None:
                data['name'] = name
            if email is not None:
                data['email'] = email
            if telegram_id is not None:
                data['telegram_id'] = telegram_id
            if phone is not None:
                data['phone'] = phone
            if company is not None:
                data['company'] = company
            if notes is not None:
                data['notes'] = notes
            if metadata is not None:
                data['metadata'] = metadata
            
            data['updated_at'] = datetime.now().isoformat()
            
            if not data:
                return await self.get_contact(contact_id)
            
            response = await self.supabase.table('contacts').update(data).eq('id', contact_id).execute()
            
            if not response.data:
                logger.error(f"Failed to update contact {contact_id}")
                return None
            
            return self._parse_contact(response.data[0])
            
        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            return None
    
    async def delete_contact(self, contact_id: str) -> bool:
        """
        Delete a contact.
        
        Args:
            contact_id: Contact ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.supabase.table('contacts').delete().eq('id', contact_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting contact: {e}")
            return False
    
    async def update_last_interaction(self, contact_id: str) -> bool:
        """
        Update the last interaction timestamp for a contact.
        
        Args:
            contact_id: Contact ID to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'last_interaction': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            response = await self.supabase.table('contacts').update(data).eq('id', contact_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating last interaction: {e}")
            return False
    
    def _parse_contact(self, data: Dict[str, Any]) -> Contact:
        """
        Parse contact data from database response.
        
        Args:
            data: Contact data from database
            
        Returns:
            Contact object
        """
        return Contact(
            id=data['id'],
            user_id=data['user_id'],
            name=data['name'],
            email=data['email'],
            telegram_id=data['telegram_id'],
            phone=data.get('phone'),
            company=data.get('company'),
            notes=data.get('notes'),
            last_interaction=datetime.fromisoformat(data['last_interaction'].replace('Z', '+00:00')),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')),
            metadata=data.get('metadata', {})
        ) 