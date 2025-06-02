"""Tests for contact management operations."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.database.contacts import Contact, ContactManager
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
        'name': 'Test User',
        'email': 'test@example.com',
        'telegram_id': 'test-telegram',
        'phone': '+1234567890',
        'company': 'Test Company',
        'notes': 'Test notes',
        'last_interaction': '2024-01-01T00:00:00Z',
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z',
        'metadata': {'test': 'value'}
    }])
    return mock


@pytest.fixture
def contact_manager(mock_supabase):
    """Create a ContactManager instance with a mock Supabase client."""
    return ContactManager(mock_supabase)


@pytest.mark.asyncio
async def test_get_contact_success(contact_manager, mock_supabase):
    """Test successful retrieval of a contact."""
    contact = await contact_manager.get_contact('test-id')
    
    assert contact is not None
    assert isinstance(contact, Contact)
    assert contact.id == 'test-id'
    assert contact.user_id == 'test-user'
    assert contact.name == 'Test User'
    assert contact.email == 'test@example.com'
    assert contact.telegram_id == 'test-telegram'
    assert contact.phone == '+1234567890'
    assert contact.company == 'Test Company'
    assert contact.notes == 'Test notes'
    assert isinstance(contact.last_interaction, datetime)
    assert isinstance(contact.created_at, datetime)
    assert isinstance(contact.updated_at, datetime)
    assert contact.metadata == {'test': 'value'}
    
    mock_supabase.table.assert_called_once_with('contacts')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.eq.assert_called_once_with('id', 'test-id')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_contact_not_found(contact_manager, mock_supabase):
    """Test retrieval of non-existent contact."""
    mock_supabase.execute.return_value = MagicMock(data=[])
    
    contact = await contact_manager.get_contact('non-existent')
    
    assert contact is None
    mock_supabase.table.assert_called_once_with('contacts')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.eq.assert_called_once_with('id', 'non-existent')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_contact_by_telegram_id_success(contact_manager, mock_supabase):
    """Test successful retrieval of a contact by Telegram ID."""
    contact = await contact_manager.get_contact_by_telegram_id('test-telegram')
    
    assert contact is not None
    assert isinstance(contact, Contact)
    assert contact.telegram_id == 'test-telegram'
    
    mock_supabase.table.assert_called_once_with('contacts')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.eq.assert_called_once_with('telegram_id', 'test-telegram')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_contacts_by_user_success(contact_manager, mock_supabase):
    """Test successful retrieval of contacts by user ID."""
    mock_supabase.execute.return_value = MagicMock(data=[
        {
            'id': 'test-id-1',
            'user_id': 'test-user',
            'name': 'Test User 1',
            'email': 'test1@example.com',
            'telegram_id': 'test-telegram-1',
            'phone': '+1234567891',
            'company': 'Test Company 1',
            'notes': 'Test notes 1',
            'last_interaction': '2024-01-01T00:00:00Z',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z',
            'metadata': {'test': 'value-1'}
        },
        {
            'id': 'test-id-2',
            'user_id': 'test-user',
            'name': 'Test User 2',
            'email': 'test2@example.com',
            'telegram_id': 'test-telegram-2',
            'phone': '+1234567892',
            'company': 'Test Company 2',
            'notes': 'Test notes 2',
            'last_interaction': '2024-01-01T00:00:00Z',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z',
            'metadata': {'test': 'value-2'}
        }
    ])
    
    contacts = await contact_manager.get_contacts_by_user('test-user')
    
    assert len(contacts) == 2
    assert all(isinstance(contact, Contact) for contact in contacts)
    assert contacts[0].name == 'Test User 1'
    assert contacts[1].name == 'Test User 2'
    
    mock_supabase.table.assert_called_once_with('contacts')
    mock_supabase.select.assert_called_once_with('*')
    mock_supabase.eq.assert_called_once_with('user_id', 'test-user')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_contact_success(contact_manager, mock_supabase):
    """Test successful creation of a contact."""
    contact = await contact_manager.create_contact(
        user_id='test-user',
        name='New User',
        email='new@example.com',
        telegram_id='new-telegram',
        phone='+1234567890',
        company='New Company',
        notes='New notes',
        metadata={'new': 'value'}
    )
    
    assert contact is not None
    assert isinstance(contact, Contact)
    assert contact.name == 'New User'
    assert contact.email == 'new@example.com'
    assert contact.telegram_id == 'new-telegram'
    
    mock_supabase.table.assert_called_with('contacts')
    mock_supabase.insert.assert_called_once()
    mock_supabase.execute.assert_called()


@pytest.mark.asyncio
async def test_update_contact_success(contact_manager, mock_supabase):
    """Test successful update of a contact."""
    contact = await contact_manager.update_contact(
        contact_id='test-id',
        name='Updated User',
        email='updated@example.com',
        phone='+9876543210'
    )
    
    assert contact is not None
    assert isinstance(contact, Contact)
    assert contact.name == 'Updated User'
    assert contact.email == 'updated@example.com'
    assert contact.phone == '+9876543210'
    
    mock_supabase.table.assert_called_with('contacts')
    mock_supabase.update.assert_called_once()
    mock_supabase.eq.assert_called_with('id', 'test-id')
    mock_supabase.execute.assert_called()


@pytest.mark.asyncio
async def test_delete_contact_success(contact_manager, mock_supabase):
    """Test successful deletion of a contact."""
    success = await contact_manager.delete_contact('test-id')
    
    assert success is True
    mock_supabase.table.assert_called_once_with('contacts')
    mock_supabase.delete.assert_called_once()
    mock_supabase.eq.assert_called_once_with('id', 'test-id')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_last_interaction_success(contact_manager, mock_supabase):
    """Test successful update of last interaction timestamp."""
    success = await contact_manager.update_last_interaction('test-id')
    
    assert success is True
    mock_supabase.table.assert_called_once_with('contacts')
    mock_supabase.update.assert_called_once()
    mock_supabase.eq.assert_called_once_with('id', 'test-id')
    mock_supabase.execute.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling(contact_manager, mock_supabase):
    """Test error handling in contact operations."""
    mock_supabase.execute.side_effect = Exception('Test error')
    
    # Test get_contact error handling
    contact = await contact_manager.get_contact('test-id')
    assert contact is None
    
    # Test get_contact_by_telegram_id error handling
    contact = await contact_manager.get_contact_by_telegram_id('test-telegram')
    assert contact is None
    
    # Test get_contacts_by_user error handling
    contacts = await contact_manager.get_contacts_by_user('test-user')
    assert len(contacts) == 0
    
    # Test create_contact error handling
    contact = await contact_manager.create_contact(
        user_id='test-user',
        name='Test User',
        email='test@example.com',
        telegram_id='test-telegram'
    )
    assert contact is None
    
    # Test update_contact error handling
    contact = await contact_manager.update_contact('test-id', name='Updated User')
    assert contact is None
    
    # Test delete_contact error handling
    success = await contact_manager.delete_contact('test-id')
    assert success is False
    
    # Test update_last_interaction error handling
    success = await contact_manager.update_last_interaction('test-id')
    assert success is False 