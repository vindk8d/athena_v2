"""
Google Calendar Integration for Athena Digital Executive Assistant.

This module provides Google Calendar API v3 integration for:
- Calendar availability checking
- Event creation and management
- OAuth 2.0 authentication flow
- Conflict prevention and scheduling
"""

import logging
import json
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any, Tuple
import pytz
from dataclasses import dataclass
import time
from functools import wraps

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Constants for retry logic
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 32  # seconds
QUOTA_EXCEEDED_ERROR = 429
RATE_LIMIT_ERROR = 403
INTERNAL_SERVER_ERROR = 500


def handle_api_errors(func):
    """
    Decorator to handle Google Calendar API errors with retries.
    
    Handles:
    - Quota exceeded (429)
    - Rate limiting (403)
    - Internal server errors (500)
    - Authentication errors
    - Network errors
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        retry_count = 0
        last_error = None
        
        while retry_count < MAX_RETRIES:
            try:
                return await func(*args, **kwargs)
            except HttpError as e:
                last_error = e
                status_code = e.resp.status if hasattr(e, 'resp') else None
                
                if status_code == QUOTA_EXCEEDED_ERROR:
                    logger.warning("Google Calendar API quota exceeded")
                    raise GoogleCalendarError("Calendar API quota exceeded. Please try again later.")
                
                elif status_code == RATE_LIMIT_ERROR:
                    logger.warning("Google Calendar API rate limit reached")
                    retry_delay = min(INITIAL_RETRY_DELAY * (2 ** retry_count), MAX_RETRY_DELAY)
                    time.sleep(retry_delay)
                    retry_count += 1
                    continue
                
                elif status_code == INTERNAL_SERVER_ERROR:
                    logger.warning("Google Calendar API internal server error")
                    retry_delay = min(INITIAL_RETRY_DELAY * (2 ** retry_count), MAX_RETRY_DELAY)
                    time.sleep(retry_delay)
                    retry_count += 1
                    continue
                
                elif status_code == 401:
                    logger.error("Google Calendar API authentication error")
                    raise GoogleCalendarAuth("Authentication failed. Please re-authenticate.")
                
                else:
                    logger.error(f"Google Calendar API error: {e}")
                    raise GoogleCalendarError(f"Calendar API error: {e}")
            
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                raise GoogleCalendarError(f"Unexpected error: {e}")
        
        if last_error:
            raise GoogleCalendarError(f"Failed after {MAX_RETRIES} retries: {last_error}")
    
    return wrapper


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    id: str
    summary: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    attendees: Optional[List[str]] = None
    location: Optional[str] = None


@dataclass
class AvailableSlot:
    """Represents an available time slot for scheduling."""
    start: datetime
    end: datetime
    duration_minutes: int


class GoogleCalendarError(Exception):
    """Base exception for Google Calendar operations."""
    pass


class GoogleCalendarAuth(Exception):
    """Exception for Google Calendar authentication issues."""
    pass


class GoogleCalendarClient:
    """
    Google Calendar API client for Athena.
    
    Handles calendar operations, availability checking, and event management.
    """
    
    def __init__(self):
        """Initialize the Google Calendar client."""
        self.settings = get_settings()
        self.service = None
        self.credentials = None
        
        # Default configuration
        self.default_timezone = 'America/New_York'  # Will be configurable via user preferences
        self.default_working_hours = (9, 17)  # 9 AM to 5 PM
        self.default_working_days = [0, 1, 2, 3, 4]  # Monday to Friday (0=Monday)
        self.default_buffer_minutes = 15  # Buffer time between meetings
        
        # Track API usage
        self._api_calls = 0
        self._last_reset = datetime.now(UTC)
        self._daily_quota_limit = 1000000  # Default daily quota limit
        self._quota_window = timedelta(days=1)
        
    def _get_credentials_from_file(self) -> Optional[Credentials]:
        """
        Load credentials from the credentials file specified in settings.
        
        Returns:
            Credentials object if found and valid, None otherwise
        """
        try:
            if not self.settings.google_calendar_credentials_file:
                logger.warning("No Google Calendar credentials file configured")
                return None
                
            with open(self.settings.google_calendar_credentials_file, 'r') as f:
                creds_data = json.load(f)
                
            credentials = Credentials.from_authorized_user_info(creds_data)
            
            # Refresh credentials if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                
            return credentials
            
        except FileNotFoundError:
            logger.error(f"Credentials file not found: {self.settings.google_calendar_credentials_file}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in credentials file: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            return None
    
    def _save_credentials_to_file(self, credentials: Credentials) -> bool:
        """
        Save credentials to the configured file.
        
        Args:
            credentials: Credentials object to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.settings.google_calendar_credentials_file:
                logger.error("No credentials file path configured")
                return False
                
            creds_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            with open(self.settings.google_calendar_credentials_file, 'w') as f:
                json.dump(creds_data, f, indent=2)
                
            logger.info("Credentials saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            return False
    
    async def authenticate(self, auth_code: Optional[str] = None) -> bool:
        """
        Authenticate with Google Calendar API.
        
        Args:
            auth_code: Optional authorization code from OAuth flow
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Try to load existing credentials
            self.credentials = self._get_credentials_from_file()
            
            if self.credentials and self.credentials.valid:
                logger.info("Using existing valid credentials")
                self.service = build('calendar', 'v3', credentials=self.credentials)
                return True
            
            # If we have an auth code, exchange it for credentials
            if auth_code:
                return await self._exchange_auth_code(auth_code)
            
            # No valid credentials and no auth code
            logger.warning("No valid credentials available. OAuth flow required.")
            return False
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise GoogleCalendarAuth(f"Authentication failed: {e}")
    
    async def _exchange_auth_code(self, auth_code: str) -> bool:
        """
        Exchange authorization code for credentials.
        
        Args:
            auth_code: Authorization code from OAuth flow
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.settings.google_calendar_client_secrets:
                raise GoogleCalendarAuth("No client secrets configured")
            
            # Create flow from client secrets
            flow = Flow.from_client_secrets_file(
                self.settings.google_calendar_client_secrets,
                scopes=['https://www.googleapis.com/auth/calendar'],
                redirect_uri=self.settings.google_calendar_redirect_uri or 'http://localhost:8080/callback'
            )
            
            # Exchange authorization code for credentials
            flow.fetch_token(code=auth_code)
            self.credentials = flow.credentials
            
            # Save credentials for future use
            self._save_credentials_to_file(self.credentials)
            
            # Initialize service
            self.service = build('calendar', 'v3', credentials=self.credentials)
            
            logger.info("OAuth authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Error exchanging auth code: {e}")
            raise GoogleCalendarAuth(f"Failed to exchange auth code: {e}")
    
    def get_auth_url(self) -> str:
        """
        Get the OAuth authorization URL for user authentication.
        
        Returns:
            Authorization URL string
        """
        try:
            if not self.settings.google_calendar_client_secrets:
                raise GoogleCalendarAuth("No client secrets configured")
            
            flow = Flow.from_client_secrets_file(
                self.settings.google_calendar_client_secrets,
                scopes=['https://www.googleapis.com/auth/calendar'],
                redirect_uri=self.settings.google_calendar_redirect_uri or 'http://localhost:8080/callback'
            )
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            return auth_url
            
        except Exception as e:
            logger.error(f"Error getting auth URL: {e}")
            raise GoogleCalendarAuth(f"Failed to get auth URL: {e}")
    
    @handle_api_errors
    async def get_calendar_list(self) -> List[Dict[str, Any]]:
        """
        Get list of user's calendars.
        
        Returns:
            List of calendar information dictionaries
        """
        if not self.service:
            raise GoogleCalendarError("Not authenticated. Call authenticate() first.")
        
        try:
            self._check_quota()
            calendars_result = self.service.calendarList().list().execute()
            self._increment_api_calls()
            calendars = calendars_result.get('items', [])
            
            return [
                {
                    'id': cal['id'],
                    'summary': cal['summary'],
                    'primary': cal.get('primary', False),
                    'access_role': cal.get('accessRole', 'reader')
                }
                for cal in calendars
            ]
            
        except HttpError as e:
            logger.error(f"HTTP error getting calendar list: {e}")
            raise GoogleCalendarError(f"Failed to get calendar list: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting calendar list: {e}")
            raise GoogleCalendarError(f"Failed to get calendar list: {e}")
    
    async def get_primary_calendar_id(self) -> str:
        """
        Get the primary calendar ID for the authenticated user.
        
        Returns:
            Primary calendar ID string
        """
        try:
            calendars = await self.get_calendar_list()
            
            for calendar in calendars:
                if calendar.get('primary', False):
                    return calendar['id']
            
            # Fallback to 'primary' if no calendar marked as primary
            return 'primary'
            
        except Exception as e:
            logger.error(f"Error getting primary calendar: {e}")
            return 'primary'  # Default fallback
    
    @handle_api_errors
    async def get_events(
        self,
        calendar_id: str = 'primary',
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 100
    ) -> List[CalendarEvent]:
        """
        Get events from the specified calendar within a time range.
        
        Args:
            calendar_id: Calendar ID to query (default: 'primary')
            time_min: Start time for event query (default: now)
            time_max: End time for event query (default: 30 days from now)
            max_results: Maximum number of events to return
            
        Returns:
            List of CalendarEvent objects
        """
        if not self.service:
            raise GoogleCalendarError("Not authenticated. Call authenticate() first.")
        
        try:
            self._check_quota()
            # Set default time range if not provided
            if time_min is None:
                time_min = datetime.now(UTC)
            if time_max is None:
                time_max = time_min + timedelta(days=30)
            
            # Ensure times are timezone-aware
            if time_min.tzinfo is None:
                time_min = time_min.replace(tzinfo=UTC)
            if time_max.tzinfo is None:
                time_max = time_max.replace(tzinfo=UTC)
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            self._increment_api_calls()
            events = events_result.get('items', [])
            calendar_events = []
            
            for event in events:
                # Parse start and end times
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                # Convert to datetime objects
                if 'T' in start:  # DateTime format
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                else:  # Date format (all-day event)
                    start_dt = datetime.fromisoformat(f"{start}T00:00:00+00:00")
                    end_dt = datetime.fromisoformat(f"{end}T00:00:00+00:00")
                
                # Extract attendees
                attendees = []
                if 'attendees' in event:
                    attendees = [attendee.get('email', '') for attendee in event['attendees']]
                
                calendar_events.append(CalendarEvent(
                    id=event['id'],
                    summary=event.get('summary', 'No Title'),
                    start=start_dt,
                    end=end_dt,
                    description=event.get('description'),
                    attendees=attendees,
                    location=event.get('location')
                ))
            
            return calendar_events
            
        except HttpError as e:
            logger.error(f"HTTP error getting events: {e}")
            raise GoogleCalendarError(f"Failed to get events: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting events: {e}")
            raise GoogleCalendarError(f"Failed to get events: {e}")
    
    async def check_availability(
        self,
        start_time: datetime,
        end_time: datetime,
        calendar_id: str = 'primary'
    ) -> bool:
        """
        Check if a time slot is available (no conflicting events).
        
        Args:
            start_time: Start time to check
            end_time: End time to check
            calendar_id: Calendar ID to check (default: 'primary')
            
        Returns:
            True if time slot is available, False if there are conflicts
        """
        try:
            # Get events in the specified time range
            events = await self.get_events(
                calendar_id=calendar_id,
                time_min=start_time - timedelta(minutes=5),  # Small buffer
                time_max=end_time + timedelta(minutes=5)
            )
            
            # Check for conflicts
            for event in events:
                # Skip declined events
                if hasattr(event, 'status') and event.status == 'cancelled':
                    continue
                
                # Check for time overlap
                if (start_time < event.end and end_time > event.start):
                    logger.info(f"Conflict found with event: {event.summary} ({event.start} - {event.end})")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            raise GoogleCalendarError(f"Failed to check availability: {e}")
    
    def _is_within_working_hours(
        self,
        start_time: datetime,
        end_time: datetime,
        working_hours: Tuple[int, int] = None,
        working_days: List[int] = None,
        timezone: str = None
    ) -> bool:
        """
        Check if a time slot is within working hours.
        
        Args:
            start_time: Start time to check
            end_time: End time to check
            working_hours: Tuple of (start_hour, end_hour) in 24-hour format
            working_days: List of working days (0=Monday, 6=Sunday)
            timezone: Timezone string (e.g., 'America/New_York')
            
        Returns:
            True if within working hours, False otherwise
        """
        if working_hours is None:
            working_hours = self.default_working_hours
        if working_days is None:
            working_days = self.default_working_days
        if timezone is None:
            timezone = self.default_timezone
        
        try:
            tz = pytz.timezone(timezone)
            
            # Convert times to the specified timezone
            local_start = start_time.astimezone(tz)
            local_end = end_time.astimezone(tz)
            
            # Check if days are working days
            start_weekday = local_start.weekday()
            end_weekday = local_end.weekday()
            
            if start_weekday not in working_days or end_weekday not in working_days:
                return False
            
            # Check if times are within working hours
            start_hour = local_start.hour + local_start.minute / 60
            end_hour = local_end.hour + local_end.minute / 60
            
            work_start, work_end = working_hours
            
            if start_hour < work_start or end_hour > work_end:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking working hours: {e}")
            return False
    
    async def find_available_slots(
        self,
        duration_minutes: int,
        start_date: datetime,
        end_date: datetime,
        calendar_id: str = 'primary',
        max_suggestions: int = 5,
        working_hours: Tuple[int, int] = None,
        working_days: List[int] = None,
        timezone: str = None,
        buffer_minutes: int = None
    ) -> List[AvailableSlot]:
        """
        Find available time slots for scheduling a meeting.
        
        Args:
            duration_minutes: Duration of the meeting in minutes
            start_date: Start date to search from
            end_date: End date to search until
            calendar_id: Calendar ID to check
            max_suggestions: Maximum number of suggestions to return
            working_hours: Working hours tuple (start_hour, end_hour)
            working_days: List of working days (0=Monday, 6=Sunday)
            timezone: Timezone for working hours
            buffer_minutes: Buffer time between meetings
            
        Returns:
            List of AvailableSlot objects
            
        Raises:
            GoogleCalendarError: If duration is not in 15-minute increments
        """
        # Validate duration is in 15-minute increments
        if duration_minutes % 15 != 0:
            raise GoogleCalendarError("Meeting duration must be in 15-minute increments")
        
        # Set default duration to 1 hour if not specified
        if duration_minutes <= 0:
            duration_minutes = 60
        
        if buffer_minutes is None:
            buffer_minutes = self.default_buffer_minutes
        
        try:
            # Get all events in the date range
            events = await self.get_events(
                calendar_id=calendar_id,
                time_min=start_date,
                time_max=end_date
            )
            
            available_slots = []
            current_time = start_date
            
            while current_time < end_date and len(available_slots) < max_suggestions:
                # Calculate potential end time
                potential_end = current_time + timedelta(minutes=duration_minutes)
                
                # Check if this is within working hours
                if not self._is_within_working_hours(
                    current_time, potential_end, working_hours, working_days, timezone
                ):
                    # Move to next working hour
                    current_time = self._next_working_time(current_time, working_hours, working_days, timezone)
                    continue
                
                # Check if this slot is available
                is_available = await self.check_availability(
                    current_time, potential_end, calendar_id
                )
                
                if is_available:
                    available_slots.append(AvailableSlot(
                        start=current_time,
                        end=potential_end,
                        duration_minutes=duration_minutes
                    ))
                    # Move past this slot plus buffer time
                    current_time = potential_end + timedelta(minutes=buffer_minutes)
                else:
                    # Find next available time after conflicts
                    current_time = self._next_available_time(current_time, events, buffer_minutes)
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Error finding available slots: {e}")
            raise GoogleCalendarError(f"Failed to find available slots: {e}")
    
    def _next_working_time(
        self,
        current_time: datetime,
        working_hours: Tuple[int, int] = None,
        working_days: List[int] = None,
        timezone: str = None
    ) -> datetime:
        """
        Find the next working time after the given time.
        
        Args:
            current_time: Current time
            working_hours: Working hours tuple
            working_days: Working days list
            timezone: Timezone string
            
        Returns:
            Next working datetime
        """
        if working_hours is None:
            working_hours = self.default_working_hours
        if working_days is None:
            working_days = self.default_working_days
        if timezone is None:
            timezone = self.default_timezone
        
        try:
            tz = pytz.timezone(timezone)
            local_time = current_time.astimezone(tz)
            
            work_start, work_end = working_hours
            
            # If current day is a working day and we're before work hours, start at work start
            if local_time.weekday() in working_days and local_time.hour < work_start:
                next_time = local_time.replace(hour=work_start, minute=0, second=0, microsecond=0)
                return next_time.astimezone(UTC)
            
            # Otherwise, find next working day at work start time
            days_ahead = 1
            while days_ahead <= 7:  # Don't search more than a week
                next_day = local_time + timedelta(days=days_ahead)
                if next_day.weekday() in working_days:
                    next_time = next_day.replace(hour=work_start, minute=0, second=0, microsecond=0)
                    return next_time.astimezone(UTC)
                days_ahead += 1
            
            # Fallback: return tomorrow at work start
            next_time = local_time + timedelta(days=1)
            next_time = next_time.replace(hour=work_start, minute=0, second=0, microsecond=0)
            return next_time.astimezone(UTC)
            
        except Exception as e:
            logger.error(f"Error finding next working time: {e}")
            return current_time + timedelta(hours=1)  # Fallback
    
    def _next_available_time(
        self,
        current_time: datetime,
        events: List[CalendarEvent],
        buffer_minutes: int
    ) -> datetime:
        """
        Find the next available time after conflicts.
        
        Args:
            current_time: Current time
            events: List of calendar events
            buffer_minutes: Buffer time in minutes
            
        Returns:
            Next available datetime
        """
        # Find the next event that conflicts with current time
        next_conflict_end = current_time
        
        for event in events:
            if event.start <= current_time < event.end:
                next_conflict_end = max(next_conflict_end, event.end)
        
        # Add buffer time
        return next_conflict_end + timedelta(minutes=buffer_minutes)
    
    @handle_api_errors
    async def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        location: Optional[str] = None,
        calendar_id: str = 'primary'
    ) -> str:
        """
        Create a new calendar event.
        
        Args:
            summary: Event title
            start_time: Event start time
            end_time: Event end time
            description: Event description
            attendees: List of attendee email addresses
            location: Event location
            calendar_id: Calendar ID to create event in
            
        Returns:
            Created event ID
        """
        if not self.service:
            raise GoogleCalendarError("Not authenticated. Call authenticate() first.")
        
        try:
            self._check_quota()
            # Prepare event data
            event_data = {
                'summary': summary,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': str(start_time.tzinfo) if start_time.tzinfo else 'UTC'
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': str(end_time.tzinfo) if end_time.tzinfo else 'UTC'
                }
            }
            
            if description:
                event_data['description'] = description
            
            if location:
                event_data['location'] = location
            
            if attendees:
                event_data['attendees'] = [{'email': email} for email in attendees]
            
            # Create the event
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()
            
            self._increment_api_calls()
            logger.info(f"Event created successfully: {event['id']}")
            return event['id']
            
        except HttpError as e:
            logger.error(f"HTTP error creating event: {e}")
            raise GoogleCalendarError(f"Failed to create event: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating event: {e}")
            raise GoogleCalendarError(f"Failed to create event: {e}")
    
    def _check_quota(self) -> None:
        """
        Check if we're within API quota limits.
        
        Raises:
            GoogleCalendarError: If quota is exceeded
        """
        now = datetime.now(UTC)
        
        # Reset counter if quota window has passed
        if now - self._last_reset > self._quota_window:
            self._api_calls = 0
            self._last_reset = now
        
        # Check if we're over quota
        if self._api_calls >= self._daily_quota_limit:
            raise GoogleCalendarError("Daily API quota exceeded. Please try again later.")
    
    def _increment_api_calls(self) -> None:
        """Increment the API call counter."""
        self._api_calls += 1 