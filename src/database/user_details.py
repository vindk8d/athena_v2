"""User details management for Athena Digital Executive Assistant."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, time
from dataclasses import dataclass

from src.database.supabase_client import SupabaseClient
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class UserDetails:
    """User details and preferences."""
    id: str
    user_id: str
    working_hours_start: time
    working_hours_end: time
    meeting_duration: int
    buffer_time: int
    telegram_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


class UserDetailsManager:
    """Manages user details in the database."""
    
    def __init__(self, supabase_client: Optional[SupabaseClient] = None):
        """Initialize the user details manager."""
        self.settings = get_settings()
        self.supabase = supabase_client or SupabaseClient()
    
    async def get_user_details(self, user_id: str) -> Optional[UserDetails]:
        """
        Get user details from the database.
        
        Args:
            user_id: User ID to get details for
            
        Returns:
            UserDetails object if found, None otherwise
        """
        try:
            response = await self.supabase.table('user_details').select('*').eq('user_id', user_id).execute()
            
            if not response.data:
                logger.warning(f"No details found for user {user_id}")
                return None
            
            data = response.data[0]
            
            # Parse working hours
            working_hours_start = time.fromisoformat(data['working_hours_start'])
            working_hours_end = time.fromisoformat(data['working_hours_end'])
            
            return UserDetails(
                id=data['id'],
                user_id=data['user_id'],
                working_hours_start=working_hours_start,
                working_hours_end=working_hours_end,
                meeting_duration=data.get('meeting_duration', self.settings.default_meeting_duration_minutes),
                buffer_time=data.get('buffer_time', self.settings.default_buffer_time_minutes),
                telegram_id=data.get('telegram_id'),
                created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')),
                metadata=data.get('metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Error getting user details: {e}")
            return None
    
    async def update_user_details(
        self,
        user_id: str,
        working_hours_start: Optional[time] = None,
        working_hours_end: Optional[time] = None,
        meeting_duration: Optional[int] = None,
        buffer_time: Optional[int] = None,
        telegram_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update user details in the database.
        
        Args:
            user_id: User ID to update
            working_hours_start: New start time
            working_hours_end: New end time
            meeting_duration: New meeting duration in minutes
            buffer_time: New buffer time in minutes
            telegram_id: New Telegram ID
            metadata: New metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current details
            current = await self.get_user_details(user_id)
            
            if not current:
                # Create new details
                data = {
                    'user_id': user_id,
                    'working_hours_start': working_hours_start.isoformat() if working_hours_start else '09:00:00',
                    'working_hours_end': working_hours_end.isoformat() if working_hours_end else '17:00:00',
                    'meeting_duration': meeting_duration or self.settings.default_meeting_duration_minutes,
                    'buffer_time': buffer_time or self.settings.default_buffer_time_minutes,
                    'telegram_id': telegram_id,
                    'metadata': metadata or {},
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                response = await self.supabase.table('user_details').insert(data).execute()
                
            else:
                # Update existing details
                data = {}
                
                if working_hours_start is not None:
                    data['working_hours_start'] = working_hours_start.isoformat()
                if working_hours_end is not None:
                    data['working_hours_end'] = working_hours_end.isoformat()
                if meeting_duration is not None:
                    data['meeting_duration'] = meeting_duration
                if buffer_time is not None:
                    data['buffer_time'] = buffer_time
                if telegram_id is not None:
                    data['telegram_id'] = telegram_id
                if metadata is not None:
                    data['metadata'] = metadata
                
                data['updated_at'] = datetime.now().isoformat()
                
                if data:
                    response = await self.supabase.table('user_details').update(data).eq('user_id', user_id).execute()
                else:
                    return True  # No changes to make
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error updating user details: {e}")
            return False
    
    async def delete_user_details(self, user_id: str) -> bool:
        """
        Delete user details from the database.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.supabase.table('user_details').delete().eq('user_id', user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting user details: {e}")
            return False
    
    async def get_all_user_details(self) -> List[UserDetails]:
        """
        Get all user details from the database.
        
        Returns:
            List of UserDetails objects
        """
        try:
            response = await self.supabase.table('user_details').select('*').execute()
            
            if not response.data:
                return []
            
            return [
                UserDetails(
                    id=data['id'],
                    user_id=data['user_id'],
                    working_hours_start=time.fromisoformat(data['working_hours_start']),
                    working_hours_end=time.fromisoformat(data['working_hours_end']),
                    meeting_duration=data.get('meeting_duration', self.settings.default_meeting_duration_minutes),
                    buffer_time=data.get('buffer_time', self.settings.default_buffer_time_minutes),
                    telegram_id=data.get('telegram_id'),
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')),
                    metadata=data.get('metadata', {})
                )
                for data in response.data
            ]
            
        except Exception as e:
            logger.error(f"Error getting all user details: {e}")
            return [] 