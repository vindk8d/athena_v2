"""User preferences management for Athena Digital Executive Assistant."""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import time
from dataclasses import dataclass

from src.database.supabase_client import SupabaseClient
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """User preferences for calendar and scheduling."""
    user_id: str
    working_hours_start: time
    working_hours_end: time
    working_days: List[int]  # 0=Monday, 6=Sunday
    buffer_time_minutes: int
    default_meeting_duration_minutes: int
    timezone: str


class UserPreferencesManager:
    """Manages user preferences in the database."""
    
    def __init__(self, supabase_client: Optional[SupabaseClient] = None):
        """Initialize the preferences manager."""
        self.settings = get_settings()
        self.supabase = supabase_client or SupabaseClient()
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """
        Get user preferences from the database.
        
        Args:
            user_id: User ID to get preferences for
            
        Returns:
            UserPreferences object if found, None otherwise
        """
        try:
            response = await self.supabase.table('user_details').select('*').eq('user_id', user_id).execute()
            
            if not response.data:
                logger.warning(f"No preferences found for user {user_id}")
                return None
            
            data = response.data[0]
            
            # Parse working hours
            working_hours_start = time.fromisoformat(data['working_hours_start'])
            working_hours_end = time.fromisoformat(data['working_hours_end'])
            
            # Parse working days
            working_days = data.get('working_days', [0, 1, 2, 3, 4])  # Default to Mon-Fri
            
            return UserPreferences(
                user_id=user_id,
                working_hours_start=working_hours_start,
                working_hours_end=working_hours_end,
                working_days=working_days,
                buffer_time_minutes=data.get('buffer_time_minutes', self.settings.default_buffer_time_minutes),
                default_meeting_duration_minutes=data.get(
                    'default_meeting_duration_minutes',
                    self.settings.default_meeting_duration_minutes
                ),
                timezone=data.get('timezone', 'UTC')
            )
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return None
    
    async def update_user_preferences(
        self,
        user_id: str,
        working_hours_start: Optional[time] = None,
        working_hours_end: Optional[time] = None,
        working_days: Optional[List[int]] = None,
        buffer_time_minutes: Optional[int] = None,
        default_meeting_duration_minutes: Optional[int] = None,
        timezone: Optional[str] = None
    ) -> bool:
        """
        Update user preferences in the database.
        
        Args:
            user_id: User ID to update preferences for
            working_hours_start: Start of working hours
            working_hours_end: End of working hours
            working_days: List of working days (0=Monday, 6=Sunday)
            buffer_time_minutes: Buffer time between meetings
            default_meeting_duration_minutes: Default meeting duration
            timezone: User's timezone
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current preferences
            current = await self.get_user_preferences(user_id)
            
            if not current:
                # Create new preferences
                data = {
                    'user_id': user_id,
                    'working_hours_start': working_hours_start.isoformat() if working_hours_start else '09:00:00',
                    'working_hours_end': working_hours_end.isoformat() if working_hours_end else '17:00:00',
                    'working_days': working_days or [0, 1, 2, 3, 4],
                    'buffer_time_minutes': buffer_time_minutes or self.settings.default_buffer_time_minutes,
                    'default_meeting_duration_minutes': default_meeting_duration_minutes or self.settings.default_meeting_duration_minutes,
                    'timezone': timezone or 'UTC'
                }
                
                response = await self.supabase.table('user_details').insert(data).execute()
                
            else:
                # Update existing preferences
                data = {}
                
                if working_hours_start is not None:
                    data['working_hours_start'] = working_hours_start.isoformat()
                if working_hours_end is not None:
                    data['working_hours_end'] = working_hours_end.isoformat()
                if working_days is not None:
                    data['working_days'] = working_days
                if buffer_time_minutes is not None:
                    data['buffer_time_minutes'] = buffer_time_minutes
                if default_meeting_duration_minutes is not None:
                    data['default_meeting_duration_minutes'] = default_meeting_duration_minutes
                if timezone is not None:
                    data['timezone'] = timezone
                
                if data:
                    response = await self.supabase.table('user_details').update(data).eq('user_id', user_id).execute()
                else:
                    return True  # No changes to make
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            return False
    
    async def get_working_hours(self, user_id: str) -> Tuple[time, time]:
        """
        Get user's working hours.
        
        Args:
            user_id: User ID to get working hours for
            
        Returns:
            Tuple of (start_time, end_time)
        """
        prefs = await self.get_user_preferences(user_id)
        
        if prefs:
            return (prefs.working_hours_start, prefs.working_hours_end)
        
        # Default to 9 AM - 5 PM
        return (time(9, 0), time(17, 0))
    
    async def get_working_days(self, user_id: str) -> List[int]:
        """
        Get user's working days.
        
        Args:
            user_id: User ID to get working days for
            
        Returns:
            List of working days (0=Monday, 6=Sunday)
        """
        prefs = await self.get_user_preferences(user_id)
        
        if prefs:
            return prefs.working_days
        
        # Default to Monday-Friday
        return [0, 1, 2, 3, 4]
    
    async def get_buffer_time(self, user_id: str) -> int:
        """
        Get user's buffer time between meetings.
        
        Args:
            user_id: User ID to get buffer time for
            
        Returns:
            Buffer time in minutes
        """
        prefs = await self.get_user_preferences(user_id)
        
        if prefs:
            return prefs.buffer_time_minutes
        
        return self.settings.default_buffer_time_minutes
    
    async def get_default_meeting_duration(self, user_id: str) -> int:
        """
        Get user's default meeting duration.
        
        Args:
            user_id: User ID to get default duration for
            
        Returns:
            Default meeting duration in minutes
        """
        prefs = await self.get_user_preferences(user_id)
        
        if prefs:
            return prefs.default_meeting_duration_minutes
        
        return self.settings.default_meeting_duration_minutes
    
    async def get_timezone(self, user_id: str) -> str:
        """
        Get user's timezone.
        
        Args:
            user_id: User ID to get timezone for
            
        Returns:
            Timezone string
        """
        prefs = await self.get_user_preferences(user_id)
        
        if prefs:
            return prefs.timezone
        
        return 'UTC' 