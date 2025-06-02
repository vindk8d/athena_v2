"""User preferences management for Athena Digital Executive Assistant."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, time
from dataclasses import dataclass
import pytz

from src.database.supabase_client import SupabaseClient
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """User preferences for scheduling and availability."""
    id: str
    user_id: str
    working_hours_start: time
    working_hours_end: time
    working_days: List[int]  # 0-6 for Monday-Sunday
    buffer_time_minutes: int
    default_meeting_duration_minutes: int
    timezone: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


class PreferencesManager:
    """Manages user preferences in the database."""
    
    MIN_BUFFER_TIME = 5  # Minimum buffer time in minutes
    MAX_BUFFER_TIME = 120  # Maximum buffer time in minutes
    MIN_MEETING_DURATION = 15  # Minimum meeting duration in minutes
    MAX_MEETING_DURATION = 480  # Maximum meeting duration in minutes (8 hours)
    
    def __init__(self, supabase_client: Optional[SupabaseClient] = None):
        """Initialize the preferences manager."""
        self.settings = get_settings()
        self.supabase = supabase_client or SupabaseClient()
    
    def validate_working_hours(self, start: time, end: time) -> Tuple[bool, str]:
        """
        Validate working hours.
        
        Args:
            start: Start time
            end: End time
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if start >= end:
            return False, "Working hours start time must be before end time"
        
        # Ensure at least 1 hour of working time
        if (end.hour - start.hour) < 1:
            return False, "Working hours must be at least 1 hour long"
        
        return True, ""
    
    def validate_working_days(self, days: List[int]) -> Tuple[bool, str]:
        """
        Validate working days.
        
        Args:
            days: List of working days (0-6 for Monday-Sunday)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not days:
            return False, "At least one working day must be specified"
        
        if not all(0 <= day <= 6 for day in days):
            return False, "Working days must be between 0 (Monday) and 6 (Sunday)"
        
        if len(set(days)) != len(days):
            return False, "Working days must be unique"
        
        return True, ""
    
    def validate_buffer_time(self, minutes: int) -> Tuple[bool, str]:
        """
        Validate buffer time.
        
        Args:
            minutes: Buffer time in minutes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(minutes, int):
            return False, "Buffer time must be an integer"
        
        if minutes < self.MIN_BUFFER_TIME:
            return False, f"Buffer time must be at least {self.MIN_BUFFER_TIME} minutes"
        
        if minutes > self.MAX_BUFFER_TIME:
            return False, f"Buffer time must not exceed {self.MAX_BUFFER_TIME} minutes"
        
        return True, ""
    
    def validate_meeting_duration(self, minutes: int) -> Tuple[bool, str]:
        """
        Validate meeting duration.
        
        Args:
            minutes: Meeting duration in minutes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(minutes, int):
            return False, "Meeting duration must be an integer"
        
        if minutes < self.MIN_MEETING_DURATION:
            return False, f"Meeting duration must be at least {self.MIN_MEETING_DURATION} minutes"
        
        if minutes > self.MAX_MEETING_DURATION:
            return False, f"Meeting duration must not exceed {self.MAX_MEETING_DURATION} minutes"
        
        if minutes % 15 != 0:
            return False, "Meeting duration must be in 15-minute increments"
        
        return True, ""
    
    def validate_timezone(self, timezone: str) -> Tuple[bool, str]:
        """
        Validate timezone.
        
        Args:
            timezone: Timezone string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            pytz.timezone(timezone)
            return True, ""
        except pytz.exceptions.UnknownTimeZoneError:
            return False, f"Invalid timezone: {timezone}"
    
    def validate_preferences(
        self,
        working_hours_start: Optional[time] = None,
        working_hours_end: Optional[time] = None,
        working_days: Optional[List[int]] = None,
        buffer_time_minutes: Optional[int] = None,
        default_meeting_duration_minutes: Optional[int] = None,
        timezone: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate all preference fields.
        
        Args:
            working_hours_start: Start time (optional)
            working_hours_end: End time (optional)
            working_days: List of working days (optional)
            buffer_time_minutes: Buffer time in minutes (optional)
            default_meeting_duration_minutes: Default meeting duration (optional)
            timezone: Timezone string (optional)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate working hours if both are provided
        if working_hours_start is not None and working_hours_end is not None:
            is_valid, error = self.validate_working_hours(working_hours_start, working_hours_end)
            if not is_valid:
                return False, error
        
        # Validate working days if provided
        if working_days is not None:
            is_valid, error = self.validate_working_days(working_days)
            if not is_valid:
                return False, error
        
        # Validate buffer time if provided
        if buffer_time_minutes is not None:
            is_valid, error = self.validate_buffer_time(buffer_time_minutes)
            if not is_valid:
                return False, error
        
        # Validate meeting duration if provided
        if default_meeting_duration_minutes is not None:
            is_valid, error = self.validate_meeting_duration(default_meeting_duration_minutes)
            if not is_valid:
                return False, error
        
        # Validate timezone if provided
        if timezone is not None:
            is_valid, error = self.validate_timezone(timezone)
            if not is_valid:
                return False, error
        
        return True, ""
    
    async def get_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """
        Get user preferences.
        
        Args:
            user_id: User ID to get preferences for
            
        Returns:
            UserPreferences object if found, None otherwise
        """
        try:
            response = await self.supabase.table('user_preferences').select('*').eq('user_id', user_id).execute()
            
            if not response.data:
                logger.warning(f"No preferences found for user {user_id}")
                return None
            
            data = response.data[0]
            return self._parse_preferences(data)
            
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")
            return None
    
    async def update_preferences(
        self,
        user_id: str,
        working_hours_start: Optional[time] = None,
        working_hours_end: Optional[time] = None,
        working_days: Optional[List[int]] = None,
        buffer_time_minutes: Optional[int] = None,
        default_meeting_duration_minutes: Optional[int] = None,
        timezone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[UserPreferences]:
        """
        Update user preferences.
        
        Args:
            user_id: User ID to update preferences for
            working_hours_start: New start time (optional)
            working_hours_end: New end time (optional)
            working_days: New working days list (optional)
            buffer_time_minutes: New buffer time in minutes (optional)
            default_meeting_duration_minutes: New default meeting duration (optional)
            timezone: New timezone (optional)
            metadata: New metadata (optional)
            
        Returns:
            Updated UserPreferences object if successful, None otherwise
        """
        try:
            # Validate all provided fields
            is_valid, error = self.validate_preferences(
                working_hours_start=working_hours_start,
                working_hours_end=working_hours_end,
                working_days=working_days,
                buffer_time_minutes=buffer_time_minutes,
                default_meeting_duration_minutes=default_meeting_duration_minutes,
                timezone=timezone
            )
            
            if not is_valid:
                logger.error(f"Invalid preferences: {error}")
                return None
            
            # Get current preferences
            current = await self.get_preferences(user_id)
            
            if not current:
                # Create new preferences with defaults
                data = {
                    'user_id': user_id,
                    'working_hours_start': working_hours_start.isoformat() if working_hours_start else '09:00:00',
                    'working_hours_end': working_hours_end.isoformat() if working_hours_end else '17:00:00',
                    'working_days': working_days or [0, 1, 2, 3, 4],  # Monday-Friday
                    'buffer_time_minutes': buffer_time_minutes or self.settings.default_buffer_time_minutes,
                    'default_meeting_duration_minutes': default_meeting_duration_minutes or self.settings.default_meeting_duration_minutes,
                    'timezone': timezone or 'UTC',
                    'metadata': metadata or {},
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                response = await self.supabase.table('user_preferences').insert(data).execute()
                
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
                if metadata is not None:
                    data['metadata'] = metadata
                
                data['updated_at'] = datetime.now().isoformat()
                
                if not data:
                    return current
                
                response = await self.supabase.table('user_preferences').update(data).eq('user_id', user_id).execute()
            
            if not response.data:
                logger.error(f"Failed to update preferences for user {user_id}")
                return None
            
            return self._parse_preferences(response.data[0])
            
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return None
    
    async def delete_preferences(self, user_id: str) -> bool:
        """
        Delete user preferences.
        
        Args:
            user_id: User ID to delete preferences for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.supabase.table('user_preferences').delete().eq('user_id', user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting preferences: {e}")
            return False
    
    async def get_all_preferences(self) -> List[UserPreferences]:
        """
        Get all user preferences.
        
        Returns:
            List of UserPreferences objects
        """
        try:
            response = await self.supabase.table('user_preferences').select('*').execute()
            
            if not response.data:
                return []
            
            return [self._parse_preferences(data) for data in response.data]
            
        except Exception as e:
            logger.error(f"Error getting all preferences: {e}")
            return []
    
    def _parse_preferences(self, data: Dict[str, Any]) -> UserPreferences:
        """
        Parse preferences data from database response.
        
        Args:
            data: Preferences data from database
            
        Returns:
            UserPreferences object
        """
        return UserPreferences(
            id=data['id'],
            user_id=data['user_id'],
            working_hours_start=time.fromisoformat(data['working_hours_start']),
            working_hours_end=time.fromisoformat(data['working_hours_end']),
            working_days=data['working_days'],
            buffer_time_minutes=data['buffer_time_minutes'],
            default_meeting_duration_minutes=data['default_meeting_duration_minutes'],
            timezone=data['timezone'],
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')),
            metadata=data.get('metadata', {})
        ) 