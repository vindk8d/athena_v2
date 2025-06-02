"""Tests for user preferences management."""

import pytest
from datetime import time
from unittest.mock import Mock, patch

from src.database.user_preferences import UserPreferencesManager, UserPreferences
from src.database.supabase_client import SupabaseClient


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    client = Mock(spec=SupabaseClient)
    return client


@pytest.fixture
def preferences_manager(mock_supabase):
    """Create a preferences manager with mocked Supabase client."""
    return UserPreferencesManager(mock_supabase)


@pytest.mark.asyncio
async def test_get_user_preferences(preferences_manager, mock_supabase):
    """Test getting user preferences."""
    # Mock response data
    mock_supabase.table().select().eq().execute.return_value.data = [{
        'user_id': 'test_user',
        'working_hours_start': '09:00:00',
        'working_hours_end': '17:00:00',
        'working_days': [0, 1, 2, 3, 4],
        'buffer_time_minutes': 15,
        'default_meeting_duration_minutes': 60,
        'timezone': 'America/New_York'
    }]
    
    prefs = await preferences_manager.get_user_preferences('test_user')
    
    assert prefs is not None
    assert prefs.user_id == 'test_user'
    assert prefs.working_hours_start == time(9, 0)
    assert prefs.working_hours_end == time(17, 0)
    assert prefs.working_days == [0, 1, 2, 3, 4]
    assert prefs.buffer_time_minutes == 15
    assert prefs.default_meeting_duration_minutes == 60
    assert prefs.timezone == 'America/New_York'


@pytest.mark.asyncio
async def test_get_user_preferences_not_found(preferences_manager, mock_supabase):
    """Test getting preferences for non-existent user."""
    mock_supabase.table().select().eq().execute.return_value.data = []
    
    prefs = await preferences_manager.get_user_preferences('test_user')
    
    assert prefs is None


@pytest.mark.asyncio
async def test_update_user_preferences_new(preferences_manager, mock_supabase):
    """Test creating new user preferences."""
    mock_supabase.table().select().eq().execute.return_value.data = []
    mock_supabase.table().insert().execute.return_value.data = [{'user_id': 'test_user'}]
    
    result = await preferences_manager.update_user_preferences(
        'test_user',
        working_hours_start=time(10, 0),
        working_hours_end=time(18, 0),
        working_days=[1, 2, 3, 4, 5],
        buffer_time_minutes=30,
        default_meeting_duration_minutes=45,
        timezone='Europe/London'
    )
    
    assert result is True
    mock_supabase.table().insert.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_preferences_existing(preferences_manager, mock_supabase):
    """Test updating existing user preferences."""
    # Mock existing preferences
    mock_supabase.table().select().eq().execute.return_value.data = [{
        'user_id': 'test_user',
        'working_hours_start': '09:00:00',
        'working_hours_end': '17:00:00',
        'working_days': [0, 1, 2, 3, 4],
        'buffer_time_minutes': 15,
        'default_meeting_duration_minutes': 60,
        'timezone': 'UTC'
    }]
    
    mock_supabase.table().update().eq().execute.return_value.data = [{'user_id': 'test_user'}]
    
    result = await preferences_manager.update_user_preferences(
        'test_user',
        working_hours_start=time(10, 0),
        buffer_time_minutes=30
    )
    
    assert result is True
    mock_supabase.table().update.assert_called_once()


@pytest.mark.asyncio
async def test_get_working_hours(preferences_manager, mock_supabase):
    """Test getting working hours."""
    mock_supabase.table().select().eq().execute.return_value.data = [{
        'user_id': 'test_user',
        'working_hours_start': '10:00:00',
        'working_hours_end': '18:00:00'
    }]
    
    start, end = await preferences_manager.get_working_hours('test_user')
    
    assert start == time(10, 0)
    assert end == time(18, 0)


@pytest.mark.asyncio
async def test_get_working_days(preferences_manager, mock_supabase):
    """Test getting working days."""
    mock_supabase.table().select().eq().execute.return_value.data = [{
        'user_id': 'test_user',
        'working_days': [1, 2, 3, 4, 5]
    }]
    
    days = await preferences_manager.get_working_days('test_user')
    
    assert days == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_get_buffer_time(preferences_manager, mock_supabase):
    """Test getting buffer time."""
    mock_supabase.table().select().eq().execute.return_value.data = [{
        'user_id': 'test_user',
        'buffer_time_minutes': 30
    }]
    
    buffer_time = await preferences_manager.get_buffer_time('test_user')
    
    assert buffer_time == 30


@pytest.mark.asyncio
async def test_get_default_meeting_duration(preferences_manager, mock_supabase):
    """Test getting default meeting duration."""
    mock_supabase.table().select().eq().execute.return_value.data = [{
        'user_id': 'test_user',
        'default_meeting_duration_minutes': 45
    }]
    
    duration = await preferences_manager.get_default_meeting_duration('test_user')
    
    assert duration == 45


@pytest.mark.asyncio
async def test_get_timezone(preferences_manager, mock_supabase):
    """Test getting timezone."""
    mock_supabase.table().select().eq().execute.return_value.data = [{
        'user_id': 'test_user',
        'timezone': 'Europe/London'
    }]
    
    tz = await preferences_manager.get_timezone('test_user')
    
    assert tz == 'Europe/London'


@pytest.mark.asyncio
async def test_error_handling(preferences_manager, mock_supabase):
    """Test error handling in preferences manager."""
    mock_supabase.table().select().eq().execute.side_effect = Exception("Test error")
    
    prefs = await preferences_manager.get_user_preferences('test_user')
    assert prefs is None
    
    result = await preferences_manager.update_user_preferences('test_user', working_hours_start=time(10, 0))
    assert result is False 