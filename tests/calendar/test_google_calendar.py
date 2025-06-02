"""Tests for Google Calendar OAuth functionality."""

import pytest
from datetime import datetime, timedelta, UTC, time
from unittest.mock import Mock, patch
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.errors import HttpError

from src.calendar.google_calendar import (
    GoogleCalendarClient,
    GoogleCalendarError,
    GoogleCalendarAuth,
    CalendarEvent,
    AvailableSlot,
    QUOTA_EXCEEDED_ERROR,
    RATE_LIMIT_ERROR,
    INTERNAL_SERVER_ERROR
)
from src.config.settings import get_settings


@pytest.fixture
def mock_credentials():
    """Mock Google OAuth credentials."""
    credentials = Mock(spec=Credentials)
    credentials.valid = True
    credentials.expired = False
    credentials.refresh_token = "mock_refresh_token"
    credentials.token = "mock_token"
    credentials.token_uri = "https://oauth2.googleapis.com/token"
    credentials.client_id = "mock_client_id"
    credentials.client_secret = "mock_client_secret"
    credentials.scopes = ["https://www.googleapis.com/auth/calendar"]
    return credentials


@pytest.fixture
def mock_flow():
    """Mock OAuth flow."""
    flow = Mock(spec=Flow)
    flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth", None)
    flow.fetch_token.return_value = None
    return flow


@pytest.fixture
def calendar_client():
    """Create a Google Calendar client instance."""
    return GoogleCalendarClient()


@pytest.mark.asyncio
async def test_authenticate_with_existing_credentials(calendar_client, mock_credentials):
    """Test authentication with existing valid credentials."""
    with patch.object(calendar_client, '_get_credentials_from_file', return_value=mock_credentials):
        with patch('googleapiclient.discovery.build') as mock_build:
            result = await calendar_client.authenticate()
            assert result is True
            assert calendar_client.credentials == mock_credentials
            mock_build.assert_called_once()


@pytest.mark.asyncio
async def test_authenticate_with_auth_code(calendar_client, mock_flow, mock_credentials):
    """Test authentication with authorization code."""
    with patch('google_auth_oauthlib.flow.Flow.from_client_secrets_file', return_value=mock_flow):
        with patch.object(calendar_client, '_save_credentials_to_file', return_value=True):
            with patch('googleapiclient.discovery.build'):
                mock_flow.credentials = mock_credentials
                result = await calendar_client.authenticate(auth_code="mock_auth_code")
                assert result is True
                assert calendar_client.credentials == mock_credentials


@pytest.mark.asyncio
async def test_authenticate_no_credentials_or_code(calendar_client):
    """Test authentication with no credentials or auth code."""
    with patch.object(calendar_client, '_get_credentials_from_file', return_value=None):
        result = await calendar_client.authenticate()
        assert result is False


def test_get_auth_url(calendar_client, mock_flow):
    """Test getting authorization URL."""
    with patch('google_auth_oauthlib.flow.Flow.from_client_secrets_file', return_value=mock_flow):
        auth_url = calendar_client.get_auth_url()
        assert auth_url == "https://accounts.google.com/o/oauth2/auth"
        mock_flow.authorization_url.assert_called_once()


@pytest.mark.asyncio
async def test_authenticate_error_handling(calendar_client):
    """Test error handling during authentication."""
    with patch.object(calendar_client, '_get_credentials_from_file', side_effect=Exception("Test error")):
        with pytest.raises(GoogleCalendarAuth) as exc_info:
            await calendar_client.authenticate()
        assert "Authentication failed" in str(exc_info.value)


def test_get_auth_url_error_handling(calendar_client):
    """Test error handling when getting auth URL."""
    with patch('google_auth_oauthlib.flow.Flow.from_client_secrets_file', side_effect=Exception("Test error")):
        with pytest.raises(GoogleCalendarAuth) as exc_info:
            calendar_client.get_auth_url()
        assert "Failed to get auth URL" in str(exc_info.value)


@pytest.mark.asyncio
async def test_exchange_auth_code_error_handling(calendar_client):
    """Test error handling when exchanging auth code."""
    with patch('google_auth_oauthlib.flow.Flow.from_client_secrets_file', side_effect=Exception("Test error")):
        with pytest.raises(GoogleCalendarAuth) as exc_info:
            await calendar_client._exchange_auth_code("mock_auth_code")
        assert "Failed to exchange auth code" in str(exc_info.value)


@pytest.mark.asyncio
async def test_find_available_slots_duration_validation(calendar_client):
    """Test meeting duration validation in find_available_slots."""
    start_date = datetime.now(UTC)
    end_date = start_date + timedelta(days=1)
    
    # Test invalid duration (not in 15-minute increments)
    with pytest.raises(GoogleCalendarError) as exc_info:
        await calendar_client.find_available_slots(
            duration_minutes=25,  # Not divisible by 15
            start_date=start_date,
            end_date=end_date
        )
    assert "Meeting duration must be in 15-minute increments" in str(exc_info.value)
    
    # Test zero duration (should default to 1 hour)
    with patch.object(calendar_client, 'get_events', return_value=[]):
        slots = await calendar_client.find_available_slots(
            duration_minutes=0,
            start_date=start_date,
            end_date=end_date
        )
        assert all(slot.duration_minutes == 60 for slot in slots)
    
    # Test valid duration
    with patch.object(calendar_client, 'get_events', return_value=[]):
        slots = await calendar_client.find_available_slots(
            duration_minutes=45,
            start_date=start_date,
            end_date=end_date
        )
        assert all(slot.duration_minutes == 45 for slot in slots)


@pytest.mark.asyncio
async def test_quota_exceeded_error(calendar_client):
    """Test handling of quota exceeded error."""
    mock_response = Mock()
    mock_response.status = QUOTA_EXCEEDED_ERROR
    
    with patch.object(calendar_client.service.events(), 'list', side_effect=HttpError(mock_response, b'')):
        with pytest.raises(GoogleCalendarError) as exc_info:
            await calendar_client.get_events()
        assert "quota exceeded" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_rate_limit_error_with_retry(calendar_client):
    """Test handling of rate limit error with retry."""
    mock_response = Mock()
    mock_response.status = RATE_LIMIT_ERROR
    
    # First call fails with rate limit, second succeeds
    with patch.object(calendar_client.service.events(), 'list',
                     side_effect=[HttpError(mock_response, b''), {'items': []}]):
        events = await calendar_client.get_events()
        assert events == []


@pytest.mark.asyncio
async def test_internal_server_error_with_retry(calendar_client):
    """Test handling of internal server error with retry."""
    mock_response = Mock()
    mock_response.status = INTERNAL_SERVER_ERROR
    
    # First call fails with internal error, second succeeds
    with patch.object(calendar_client.service.events(), 'list',
                     side_effect=[HttpError(mock_response, b''), {'items': []}]):
        events = await calendar_client.get_events()
        assert events == []


@pytest.mark.asyncio
async def test_authentication_error(calendar_client):
    """Test handling of authentication error."""
    mock_response = Mock()
    mock_response.status = 401
    
    with patch.object(calendar_client.service.events(), 'list', side_effect=HttpError(mock_response, b'')):
        with pytest.raises(GoogleCalendarAuth) as exc_info:
            await calendar_client.get_events()
        assert "authentication failed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_quota_tracking(calendar_client):
    """Test API quota tracking."""
    # Set a low quota limit for testing
    calendar_client._daily_quota_limit = 2
    
    # First call should succeed
    with patch.object(calendar_client.service.events(), 'list', return_value={'items': []}):
        await calendar_client.get_events()
    
    # Second call should succeed
    with patch.object(calendar_client.service.events(), 'list', return_value={'items': []}):
        await calendar_client.get_events()
    
    # Third call should fail with quota exceeded
    with patch.object(calendar_client.service.events(), 'list', return_value={'items': []}):
        with pytest.raises(GoogleCalendarError) as exc_info:
            await calendar_client.get_events()
        assert "quota exceeded" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_quota_reset(calendar_client):
    """Test quota counter reset after window."""
    # Set a low quota limit for testing
    calendar_client._daily_quota_limit = 1
    
    # First call should succeed
    with patch.object(calendar_client.service.events(), 'list', return_value={'items': []}):
        await calendar_client.get_events()
    
    # Second call should fail
    with patch.object(calendar_client.service.events(), 'list', return_value={'items': []}):
        with pytest.raises(GoogleCalendarError) as exc_info:
            await calendar_client.get_events()
        assert "quota exceeded" in str(exc_info.value).lower()
    
    # Move time forward past quota window
    calendar_client._last_reset = datetime.now(UTC) - timedelta(days=2)
    
    # Call should succeed again after reset
    with patch.object(calendar_client.service.events(), 'list', return_value={'items': []}):
        await calendar_client.get_events()


@pytest.mark.asyncio
async def test_max_retries_exceeded(calendar_client):
    """Test behavior when max retries are exceeded."""
    mock_response = Mock()
    mock_response.status = RATE_LIMIT_ERROR
    
    # All calls fail with rate limit
    with patch.object(calendar_client.service.events(), 'list',
                     side_effect=[HttpError(mock_response, b'')] * 4):
        with pytest.raises(GoogleCalendarError) as exc_info:
            await calendar_client.get_events()
        assert "failed after" in str(exc_info.value).lower()
        assert "retries" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_check_availability_no_conflicts(calendar_client):
    """Test availability checking with no conflicts."""
    start_time = datetime.now(UTC)
    end_time = start_time + timedelta(hours=1)
    
    with patch.object(calendar_client, 'get_events', return_value=[]):
        is_available = await calendar_client.check_availability(start_time, end_time)
        assert is_available is True


@pytest.mark.asyncio
async def test_check_availability_with_conflict(calendar_client):
    """Test availability checking with a conflicting event."""
    start_time = datetime.now(UTC)
    end_time = start_time + timedelta(hours=1)
    
    # Create a conflicting event
    conflict_event = CalendarEvent(
        id="conflict_123",
        summary="Conflicting Meeting",
        start=start_time + timedelta(minutes=30),
        end=start_time + timedelta(hours=2)
    )
    
    with patch.object(calendar_client, 'get_events', return_value=[conflict_event]):
        is_available = await calendar_client.check_availability(start_time, end_time)
        assert is_available is False


@pytest.mark.asyncio
async def test_check_availability_with_buffer_time(calendar_client):
    """Test availability checking with buffer time between events."""
    start_time = datetime.now(UTC)
    end_time = start_time + timedelta(hours=1)
    buffer_minutes = 15
    
    # Create an event that ends exactly at buffer time before our slot
    event_before = CalendarEvent(
        id="before_123",
        summary="Meeting Before",
        start=start_time - timedelta(hours=1),
        end=start_time - timedelta(minutes=buffer_minutes)
    )
    
    # Create an event that starts exactly at buffer time after our slot
    event_after = CalendarEvent(
        id="after_123",
        summary="Meeting After",
        start=end_time + timedelta(minutes=buffer_minutes),
        end=end_time + timedelta(hours=1)
    )
    
    with patch.object(calendar_client, 'get_events', return_value=[event_before, event_after]):
        is_available = await calendar_client.check_availability(start_time, end_time)
        assert is_available is True


@pytest.mark.asyncio
async def test_find_available_slots_within_working_hours(calendar_client):
    """Test finding available slots within working hours."""
    start_date = datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)
    
    # Mock working hours (9 AM - 5 PM)
    working_hours = (9, 17)
    working_days = [0, 1, 2, 3, 4]  # Monday to Friday
    
    with patch.object(calendar_client, 'get_events', return_value=[]):
        slots = await calendar_client.find_available_slots(
            duration_minutes=60,
            start_date=start_date,
            end_date=end_date,
            working_hours=working_hours,
            working_days=working_days
        )
        
        assert len(slots) > 0
        for slot in slots:
            # Check if slot is within working hours
            slot_start = slot.start.astimezone(UTC)
            slot_end = slot.end.astimezone(UTC)
            assert slot_start.hour >= working_hours[0]
            assert slot_end.hour <= working_hours[1]
            assert slot_start.weekday() in working_days


@pytest.mark.asyncio
async def test_find_available_slots_with_existing_events(calendar_client):
    """Test finding available slots with existing events."""
    start_date = datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)
    
    # Create some existing events
    existing_events = [
        CalendarEvent(
            id="event1",
            summary="Morning Meeting",
            start=start_date + timedelta(hours=1),
            end=start_date + timedelta(hours=2)
        ),
        CalendarEvent(
            id="event2",
            summary="Afternoon Meeting",
            start=start_date + timedelta(hours=4),
            end=start_date + timedelta(hours=5)
        )
    ]
    
    with patch.object(calendar_client, 'get_events', return_value=existing_events):
        slots = await calendar_client.find_available_slots(
            duration_minutes=60,
            start_date=start_date,
            end_date=end_date
        )
        
        assert len(slots) > 0
        for slot in slots:
            # Verify slots don't overlap with existing events
            for event in existing_events:
                assert not (slot.start < event.end and slot.end > event.start)


@pytest.mark.asyncio
async def test_find_available_slots_with_buffer_time(calendar_client):
    """Test finding available slots with buffer time between events."""
    start_date = datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)
    buffer_minutes = 15
    
    # Create events with buffer time
    existing_events = [
        CalendarEvent(
            id="event1",
            summary="Morning Meeting",
            start=start_date + timedelta(hours=1),
            end=start_date + timedelta(hours=2)
        )
    ]
    
    with patch.object(calendar_client, 'get_events', return_value=existing_events):
        slots = await calendar_client.find_available_slots(
            duration_minutes=60,
            start_date=start_date,
            end_date=end_date,
            buffer_minutes=buffer_minutes
        )
        
        assert len(slots) > 0
        for slot in slots:
            # Verify slots respect buffer time
            for event in existing_events:
                assert (slot.end + timedelta(minutes=buffer_minutes) <= event.start or
                       slot.start >= event.end + timedelta(minutes=buffer_minutes))


@pytest.mark.asyncio
async def test_create_event_with_attendees(calendar_client):
    """Test creating an event with attendees."""
    start_time = datetime.now(UTC)
    end_time = start_time + timedelta(hours=1)
    attendees = ["test1@example.com", "test2@example.com"]
    
    mock_event = {
        'id': 'test_event_123',
        'summary': 'Test Meeting',
        'start': {'dateTime': start_time.isoformat()},
        'end': {'dateTime': end_time.isoformat()},
        'attendees': [{'email': email} for email in attendees]
    }
    
    with patch.object(calendar_client.service.events(), 'insert', return_value=mock_event):
        event_id = await calendar_client.create_event(
            summary="Test Meeting",
            start_time=start_time,
            end_time=end_time,
            attendees=attendees
        )
        
        assert event_id == 'test_event_123'
        calendar_client.service.events().insert.assert_called_once()


@pytest.mark.asyncio
async def test_create_event_with_location_and_description(calendar_client):
    """Test creating an event with location and description."""
    start_time = datetime.now(UTC)
    end_time = start_time + timedelta(hours=1)
    location = "Conference Room A"
    description = "Test meeting description"
    
    mock_event = {
        'id': 'test_event_123',
        'summary': 'Test Meeting',
        'start': {'dateTime': start_time.isoformat()},
        'end': {'dateTime': end_time.isoformat()},
        'location': location,
        'description': description
    }
    
    with patch.object(calendar_client.service.events(), 'insert', return_value=mock_event):
        event_id = await calendar_client.create_event(
            summary="Test Meeting",
            start_time=start_time,
            end_time=end_time,
            location=location,
            description=description
        )
        
        assert event_id == 'test_event_123'
        calendar_client.service.events().insert.assert_called_once()


@pytest.mark.asyncio
async def test_get_events_with_time_range(calendar_client):
    """Test getting events within a specific time range."""
    start_time = datetime.now(UTC)
    end_time = start_time + timedelta(days=7)
    
    mock_events = [
        {
            'id': 'event1',
            'summary': 'Event 1',
            'start': {'dateTime': (start_time + timedelta(days=1)).isoformat()},
            'end': {'dateTime': (start_time + timedelta(days=1, hours=1)).isoformat()}
        },
        {
            'id': 'event2',
            'summary': 'Event 2',
            'start': {'dateTime': (start_time + timedelta(days=2)).isoformat()},
            'end': {'dateTime': (start_time + timedelta(days=2, hours=1)).isoformat()}
        }
    ]
    
    with patch.object(calendar_client.service.events(), 'list', return_value={'items': mock_events}):
        events = await calendar_client.get_events(
            time_min=start_time,
            time_max=end_time
        )
        
        assert len(events) == 2
        assert all(isinstance(event, CalendarEvent) for event in events)
        assert all(event.start >= start_time and event.end <= end_time for event in events)


@pytest.mark.asyncio
async def test_get_events_with_all_day_events(calendar_client):
    """Test getting events including all-day events."""
    start_time = datetime.now(UTC)
    end_time = start_time + timedelta(days=7)
    
    mock_events = [
        {
            'id': 'event1',
            'summary': 'Regular Event',
            'start': {'dateTime': (start_time + timedelta(days=1)).isoformat()},
            'end': {'dateTime': (start_time + timedelta(days=1, hours=1)).isoformat()}
        },
        {
            'id': 'event2',
            'summary': 'All Day Event',
            'start': {'date': (start_time + timedelta(days=2)).strftime('%Y-%m-%d')},
            'end': {'date': (start_time + timedelta(days=3)).strftime('%Y-%m-%d')}
        }
    ]
    
    with patch.object(calendar_client.service.events(), 'list', return_value={'items': mock_events}):
        events = await calendar_client.get_events(
            time_min=start_time,
            time_max=end_time
        )
        
        assert len(events) == 2
        assert all(isinstance(event, CalendarEvent) for event in events)
        
        # Verify all-day event times
        all_day_event = next(event for event in events if event.summary == 'All Day Event')
        assert all_day_event.start.hour == 0
        assert all_day_event.start.minute == 0
        assert all_day_event.end.hour == 0
        assert all_day_event.end.minute == 0 