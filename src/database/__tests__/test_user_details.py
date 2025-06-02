"""Tests for user details management."""

import pytest
from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock, patch

from src.database.user_details import UserDetails, UserDetailsManager
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
def user_details_manager(mock_supabase):
    """Create a UserDetailsManager instance with a mock Supabase client."""
    return UserDetailsManager(mock_supabase)


@pytest.mark.asyncio
async def test_get_user_details_success(user_details_manager, mock_supabase):
    """Test successful retrieval of user details."""
    details = await user_details_manager.get_user_details('test-user')
    
    assert details is not None
    assert isinstance(details, UserDetails)
    assert details.id == 'test-id'
    assert details.user_id == 'test-user'
    assert details.working_hours_start == time(9, 0)
    assert details.working_hours_end == time(17, 0)
    assert details.working_days == [0, 1, 2, 3, 4]
    assert details.buffer_time_minutes == 15
    assert details.default_meeting_duration_minutes == 60
    assert details.timezone == 'UTC'
    assert isinstance(details.created_at, datetime)
    assert isinstance(details.updated_at, datetime)
    assert details.metadata == {'test': 'value'}
    
    mock_supabase.table.assert_called_once_with('user_details')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.eq.assert_called_once_with('user_id', 'test-user')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_details_not_found(user_details_manager, mock_supabase):
    """Test retrieval of non-existent user details."""
    mock_supabase.execute.return_value = MagicMock(data=[])
    
    details = await user_details_manager.get_user_details('non-existent')
    
    assert details is None
    mock_supabase.table.assert_called_once_with('user_details')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.eq.assert_called_once_with('user_id', 'non-existent')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_details_success(user_details_manager, mock_supabase):
    """Test successful creation of user details."""
    mock_supabase.execute.return_value = MagicMock(data=[])
    
    details = await user_details_manager.create_user_details(
        user_id='new-user',
        working_hours_start=time(10, 0),
        working_hours_end=time(18, 0),
        working_days=[1, 2, 3, 4, 5],  # Tuesday-Saturday
        buffer_time_minutes=30,
        default_meeting_duration_minutes=45,
        timezone='America/New_York'
    )
    
    assert details is not None
    assert isinstance(details, UserDetails)
    assert details.working_hours_start == time(10, 0)
    assert details.working_hours_end == time(18, 0)
    assert details.working_days == [1, 2, 3, 4, 5]
    assert details.buffer_time_minutes == 30
    assert details.default_meeting_duration_minutes == 45
    assert details.timezone == 'America/New_York'
    
    mock_supabase.table.assert_called_with('user_details')
    mock_supabase.insert.assert_called_once()
    mock_supabase.execute.assert_called()


@pytest.mark.asyncio
async def test_update_user_details_success(user_details_manager, mock_supabase):
    """Test successful update of user details."""
    details = await user_details_manager.update_user_details(
        user_id='test-user',
        working_hours_start=time(8, 0),
        buffer_time_minutes=20
    )
    
    assert details is not None
    assert isinstance(details, UserDetails)
    assert details.working_hours_start == time(8, 0)
    assert details.buffer_time_minutes == 20
    
    mock_supabase.table.assert_called_with('user_details')
    mock_supabase.update.assert_called_once()
    mock_supabase.eq.assert_called_with('user_id', 'test-user')
    mock_supabase.execute.assert_called()


@pytest.mark.asyncio
async def test_delete_user_details_success(user_details_manager, mock_supabase):
    """Test successful deletion of user details."""
    success = await user_details_manager.delete_user_details('test-user')
    
    assert success is True
    mock_supabase.table.assert_called_once_with('user_details')
    mock_supabase.delete.assert_called_once()
    mock_supabase.eq.assert_called_once_with('user_id', 'test-user')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_user_details_success(user_details_manager, mock_supabase):
    """Test successful retrieval of all user details."""
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
    
    details_list = await user_details_manager.get_all_user_details()
    
    assert len(details_list) == 2
    assert all(isinstance(details, UserDetails) for details in details_list)
    assert details_list[0].user_id == 'test-user-1'
    assert details_list[1].user_id == 'test-user-2'
    
    mock_supabase.table.assert_called_once_with('user_details')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_user_details_empty(user_details_manager, mock_supabase):
    """Test retrieval of user details when none exist."""
    mock_supabase.execute.return_value = MagicMock(data=[])
    
    details_list = await user_details_manager.get_all_user_details()
    
    assert len(details_list) == 0
    mock_supabase.table.assert_called_once_with('user_details')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling(user_details_manager, mock_supabase):
    """Test error handling in user details operations."""
    mock_supabase.execute.side_effect = Exception('Test error')
    
    # Test get_user_details error handling
    details = await user_details_manager.get_user_details('test-user')
    assert details is None
    
    # Test create_user_details error handling
    details = await user_details_manager.create_user_details(
        user_id='test-user',
        working_hours_start=time(9, 0),
        working_hours_end=time(17, 0)
    )
    assert details is None
    
    # Test update_user_details error handling
    details = await user_details_manager.update_user_details(
        user_id='test-user',
        working_hours_start=time(8, 0)
    )
    assert details is None
    
    # Test delete_user_details error handling
    success = await user_details_manager.delete_user_details('test-user')
    assert success is False
    
    # Test get_all_user_details error handling
    details_list = await user_details_manager.get_all_user_details()
    assert len(details_list) == 0


@pytest.mark.asyncio
async def test_validation_during_operations(user_details_manager, mock_supabase):
    """Test validation during user details operations."""
    # Test invalid working hours
    details = await user_details_manager.create_user_details(
        user_id='test-user',
        working_hours_start=time(17, 0),
        working_hours_end=time(9, 0)
    )
    assert details is None
    
    # Test invalid working days
    details = await user_details_manager.create_user_details(
        user_id='test-user',
        working_days=[0, 1, 7]
    )
    assert details is None
    
    # Test invalid buffer time
    details = await user_details_manager.create_user_details(
        user_id='test-user',
        buffer_time_minutes=4
    )
    assert details is None
    
    # Test invalid meeting duration
    details = await user_details_manager.create_user_details(
        user_id='test-user',
        default_meeting_duration_minutes=20
    )
    assert details is None
    
    # Test invalid timezone
    details = await user_details_manager.create_user_details(
        user_id='test-user',
        timezone='Invalid/Timezone'
    )
    assert details is None
    
    # Verify no database calls were made for invalid operations
    mock_supabase.table.assert_not_called()
    mock_supabase.insert.assert_not_called()
    mock_supabase.update.assert_not_called()
    mock_supabase.execute.assert_not_called()


@pytest.mark.asyncio
async def test_concurrent_operations(user_details_manager, mock_supabase):
    """Test concurrent operations on user details."""
    import asyncio
    
    # Create multiple update operations
    updates = [
        user_details_manager.update_user_details(
            user_id='test-user',
            working_hours_start=time(8, 0)
        ),
        user_details_manager.update_user_details(
            user_id='test-user',
            buffer_time_minutes=30
        ),
        user_details_manager.update_user_details(
            user_id='test-user',
            timezone='America/New_York'
        )
    ]
    
    # Execute updates concurrently
    results = await asyncio.gather(*updates)
    
    # Verify all updates were successful
    assert all(result is not None for result in results)
    assert mock_supabase.table.call_count == 3
    assert mock_supabase.update.call_count == 3
    assert mock_supabase.execute.call_count == 3 