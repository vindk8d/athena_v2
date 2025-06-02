"""Tests for user preferences management."""

import pytest
from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock, patch

from src.database.preferences import UserPreferences, PreferencesManager
from src.database.supabase_client import SupabaseClient


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = AsyncMock(spec=SupabaseClient)
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.execute.return_value = MagicMock(data=[{
        'id': 'test-id',
        'user_id': 'test-user',
        'working_hours_start': '09:00:00',
        'working_hours_end': '17:00:00',
        'working_days': [0, 1, 2, 3, 4],  # Monday-Friday
        'buffer_time_minutes': 15,
        'default_meeting_duration_minutes': 60,
        'timezone': 'UTC',
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z',
        'metadata': {'test': 'value'}
    }])
    return mock


@pytest.fixture
def preferences_manager(mock_supabase):
    """Create a PreferencesManager instance with a mock Supabase client."""
    return PreferencesManager(mock_supabase)


@pytest.mark.asyncio
async def test_get_preferences_success(preferences_manager, mock_supabase):
    """Test successful retrieval of user preferences."""
    preferences = await preferences_manager.get_preferences('test-user')
    
    assert preferences is not None
    assert isinstance(preferences, UserPreferences)
    assert preferences.id == 'test-id'
    assert preferences.user_id == 'test-user'
    assert preferences.working_hours_start == time(9, 0)
    assert preferences.working_hours_end == time(17, 0)
    assert preferences.working_days == [0, 1, 2, 3, 4]
    assert preferences.buffer_time_minutes == 15
    assert preferences.default_meeting_duration_minutes == 60
    assert preferences.timezone == 'UTC'
    assert isinstance(preferences.created_at, datetime)
    assert isinstance(preferences.updated_at, datetime)
    assert preferences.metadata == {'test': 'value'}
    
    mock_supabase.table.assert_called_once_with('user_preferences')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.eq.assert_called_once_with('user_id', 'test-user')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_preferences_not_found(preferences_manager, mock_supabase):
    """Test retrieval of non-existent preferences."""
    mock_supabase.execute.return_value = MagicMock(data=[])
    
    preferences = await preferences_manager.get_preferences('non-existent')
    
    assert preferences is None
    mock_supabase.table.assert_called_once_with('user_preferences')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.eq.assert_called_once_with('user_id', 'non-existent')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_preferences_create_new(preferences_manager, mock_supabase):
    """Test creating new preferences."""
    mock_supabase.execute.return_value = MagicMock(data=[])
    
    preferences = await preferences_manager.update_preferences(
        user_id='new-user',
        working_hours_start=time(10, 0),
        working_hours_end=time(18, 0),
        working_days=[1, 2, 3, 4, 5],  # Tuesday-Saturday
        buffer_time_minutes=30,
        default_meeting_duration_minutes=45,
        timezone='America/New_York'
    )
    
    assert preferences is not None
    assert isinstance(preferences, UserPreferences)
    assert preferences.working_hours_start == time(10, 0)
    assert preferences.working_hours_end == time(18, 0)
    assert preferences.working_days == [1, 2, 3, 4, 5]
    assert preferences.buffer_time_minutes == 30
    assert preferences.default_meeting_duration_minutes == 45
    assert preferences.timezone == 'America/New_York'
    
    mock_supabase.table.assert_called_with('user_preferences')
    mock_supabase.insert.assert_called_once()
    mock_supabase.execute.assert_called()


@pytest.mark.asyncio
async def test_update_preferences_update_existing(preferences_manager, mock_supabase):
    """Test updating existing preferences."""
    preferences = await preferences_manager.update_preferences(
        user_id='test-user',
        working_hours_start=time(8, 0),
        buffer_time_minutes=20
    )
    
    assert preferences is not None
    assert isinstance(preferences, UserPreferences)
    assert preferences.working_hours_start == time(8, 0)
    assert preferences.buffer_time_minutes == 20
    
    mock_supabase.table.assert_called_with('user_preferences')
    mock_supabase.update.assert_called_once()
    mock_supabase.eq.assert_called_with('user_id', 'test-user')
    mock_supabase.execute.assert_called()


@pytest.mark.asyncio
async def test_delete_preferences_success(preferences_manager, mock_supabase):
    """Test successful deletion of preferences."""
    success = await preferences_manager.delete_preferences('test-user')
    
    assert success is True
    mock_supabase.table.assert_called_once_with('user_preferences')
    mock_supabase.delete.assert_called_once()
    mock_supabase.eq.assert_called_once_with('user_id', 'test-user')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_preferences_success(preferences_manager, mock_supabase):
    """Test successful retrieval of all preferences."""
    mock_supabase.execute.return_value = MagicMock(data=[
        {
            'id': 'test-id-1',
            'user_id': 'test-user-1',
            'working_hours_start': '09:00:00',
            'working_hours_end': '17:00:00',
            'working_days': [0, 1, 2, 3, 4],
            'buffer_time_minutes': 15,
            'default_meeting_duration_minutes': 60,
            'timezone': 'UTC',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z',
            'metadata': {'test': 'value-1'}
        },
        {
            'id': 'test-id-2',
            'user_id': 'test-user-2',
            'working_hours_start': '10:00:00',
            'working_hours_end': '18:00:00',
            'working_days': [1, 2, 3, 4, 5],
            'buffer_time_minutes': 30,
            'default_meeting_duration_minutes': 45,
            'timezone': 'America/New_York',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z',
            'metadata': {'test': 'value-2'}
        }
    ])
    
    preferences_list = await preferences_manager.get_all_preferences()
    
    assert len(preferences_list) == 2
    assert all(isinstance(prefs, UserPreferences) for prefs in preferences_list)
    assert preferences_list[0].user_id == 'test-user-1'
    assert preferences_list[1].user_id == 'test-user-2'
    
    mock_supabase.table.assert_called_once_with('user_preferences')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_preferences_empty(preferences_manager, mock_supabase):
    """Test retrieval of preferences when none exist."""
    mock_supabase.execute.return_value = MagicMock(data=[])
    
    preferences_list = await preferences_manager.get_all_preferences()
    
    assert len(preferences_list) == 0
    mock_supabase.table.assert_called_once_with('user_preferences')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling(preferences_manager, mock_supabase):
    """Test error handling in preferences operations."""
    mock_supabase.execute.side_effect = Exception('Test error')
    
    # Test get_preferences error handling
    preferences = await preferences_manager.get_preferences('test-user')
    assert preferences is None
    
    # Test update_preferences error handling
    preferences = await preferences_manager.update_preferences(
        user_id='test-user',
        working_hours_start=time(8, 0)
    )
    assert preferences is None
    
    # Test delete_preferences error handling
    success = await preferences_manager.delete_preferences('test-user')
    assert success is False
    
    # Test get_all_preferences error handling
    preferences_list = await preferences_manager.get_all_preferences()
    assert len(preferences_list) == 0


def test_validate_working_hours():
    """Test working hours validation."""
    manager = PreferencesManager()
    
    # Valid cases
    assert manager.validate_working_hours(time(9, 0), time(17, 0))[0] is True
    assert manager.validate_working_hours(time(8, 30), time(16, 30))[0] is True
    
    # Invalid cases
    is_valid, error = manager.validate_working_hours(time(17, 0), time(9, 0))
    assert is_valid is False
    assert "must be before end time" in error
    
    is_valid, error = manager.validate_working_hours(time(9, 0), time(9, 30))
    assert is_valid is False
    assert "must be at least 1 hour long" in error


def test_validate_working_days():
    """Test working days validation."""
    manager = PreferencesManager()
    
    # Valid cases
    assert manager.validate_working_days([0, 1, 2, 3, 4])[0] is True  # Monday-Friday
    assert manager.validate_working_days([0, 6])[0] is True  # Monday and Sunday
    
    # Invalid cases
    is_valid, error = manager.validate_working_days([])
    assert is_valid is False
    assert "At least one working day must be specified" in error
    
    is_valid, error = manager.validate_working_days([0, 1, 7])
    assert is_valid is False
    assert "must be between 0 (Monday) and 6 (Sunday)" in error
    
    is_valid, error = manager.validate_working_days([0, 1, 1])
    assert is_valid is False
    assert "must be unique" in error


def test_validate_buffer_time():
    """Test buffer time validation."""
    manager = PreferencesManager()
    
    # Valid cases
    assert manager.validate_buffer_time(15)[0] is True
    assert manager.validate_buffer_time(30)[0] is True
    assert manager.validate_buffer_time(60)[0] is True
    
    # Invalid cases
    is_valid, error = manager.validate_buffer_time(4)
    assert is_valid is False
    assert f"must be at least {manager.MIN_BUFFER_TIME} minutes" in error
    
    is_valid, error = manager.validate_buffer_time(121)
    assert is_valid is False
    assert f"must not exceed {manager.MAX_BUFFER_TIME} minutes" in error
    
    is_valid, error = manager.validate_buffer_time("15")  # type: ignore
    assert is_valid is False
    assert "must be an integer" in error


def test_validate_meeting_duration():
    """Test meeting duration validation."""
    manager = PreferencesManager()
    
    # Valid cases
    assert manager.validate_meeting_duration(15)[0] is True
    assert manager.validate_meeting_duration(30)[0] is True
    assert manager.validate_meeting_duration(60)[0] is True
    assert manager.validate_meeting_duration(120)[0] is True
    
    # Invalid cases
    is_valid, error = manager.validate_meeting_duration(14)
    assert is_valid is False
    assert f"must be at least {manager.MIN_MEETING_DURATION} minutes" in error
    
    is_valid, error = manager.validate_meeting_duration(481)
    assert is_valid is False
    assert f"must not exceed {manager.MAX_MEETING_DURATION} minutes" in error
    
    is_valid, error = manager.validate_meeting_duration(20)
    assert is_valid is False
    assert "must be in 15-minute increments" in error
    
    is_valid, error = manager.validate_meeting_duration("30")  # type: ignore
    assert is_valid is False
    assert "must be an integer" in error


def test_validate_timezone():
    """Test timezone validation."""
    manager = PreferencesManager()
    
    # Valid cases
    assert manager.validate_timezone('UTC')[0] is True
    assert manager.validate_timezone('America/New_York')[0] is True
    assert manager.validate_timezone('Europe/London')[0] is True
    
    # Invalid cases
    is_valid, error = manager.validate_timezone('Invalid/Timezone')
    assert is_valid is False
    assert "Invalid timezone" in error


def test_validate_preferences():
    """Test comprehensive preferences validation."""
    manager = PreferencesManager()
    
    # Valid cases
    assert manager.validate_preferences(
        working_hours_start=time(9, 0),
        working_hours_end=time(17, 0),
        working_days=[0, 1, 2, 3, 4],
        buffer_time_minutes=15,
        default_meeting_duration_minutes=30,
        timezone='UTC'
    )[0] is True
    
    # Invalid working hours
    is_valid, error = manager.validate_preferences(
        working_hours_start=time(17, 0),
        working_hours_end=time(9, 0)
    )
    assert is_valid is False
    assert "must be before end time" in error
    
    # Invalid working days
    is_valid, error = manager.validate_preferences(
        working_days=[0, 1, 7]
    )
    assert is_valid is False
    assert "must be between 0 (Monday) and 6 (Sunday)" in error
    
    # Invalid buffer time
    is_valid, error = manager.validate_preferences(
        buffer_time_minutes=4
    )
    assert is_valid is False
    assert f"must be at least {manager.MIN_BUFFER_TIME} minutes" in error
    
    # Invalid meeting duration
    is_valid, error = manager.validate_preferences(
        default_meeting_duration_minutes=20
    )
    assert is_valid is False
    assert "must be in 15-minute increments" in error
    
    # Invalid timezone
    is_valid, error = manager.validate_preferences(
        timezone='Invalid/Timezone'
    )
    assert is_valid is False
    assert "Invalid timezone" in error


@pytest.mark.asyncio
async def test_update_preferences_validation(preferences_manager, mock_supabase):
    """Test validation during preferences update."""
    # Test invalid working hours
    preferences = await preferences_manager.update_preferences(
        user_id='test-user',
        working_hours_start=time(17, 0),
        working_hours_end=time(9, 0)
    )
    assert preferences is None
    
    # Test invalid working days
    preferences = await preferences_manager.update_preferences(
        user_id='test-user',
        working_days=[0, 1, 7]
    )
    assert preferences is None
    
    # Test invalid buffer time
    preferences = await preferences_manager.update_preferences(
        user_id='test-user',
        buffer_time_minutes=4
    )
    assert preferences is None
    
    # Test invalid meeting duration
    preferences = await preferences_manager.update_preferences(
        user_id='test-user',
        default_meeting_duration_minutes=20
    )
    assert preferences is None
    
    # Test invalid timezone
    preferences = await preferences_manager.update_preferences(
        user_id='test-user',
        timezone='Invalid/Timezone'
    )
    assert preferences is None
    
    # Verify no database calls were made for invalid updates
    mock_supabase.table.assert_not_called()
    mock_supabase.insert.assert_not_called()
    mock_supabase.update.assert_not_called()
    mock_supabase.execute.assert_not_called() 