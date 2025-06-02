"""Tests for authentication manager."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.auth.auth_manager import AuthManager, AuthUser
from supabase import Client


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = AsyncMock(spec=Client)
    mock.auth = AsyncMock()
    return mock


@pytest.fixture
def auth_manager(mock_supabase):
    """Create an AuthManager instance with a mock Supabase client."""
    return AuthManager(mock_supabase)


@pytest.fixture
def mock_user_data():
    """Create mock user data for testing."""
    return {
        'id': 'test-user-id',
        'email': 'test@example.com',
        'phone': '+1234567890',
        'created_at': '2024-01-01T00:00:00Z',
        'last_sign_in_at': '2024-01-02T00:00:00Z',
        'role': 'authenticated',
        'user_metadata': {'name': 'Test User'}
    }


@pytest.mark.asyncio
async def test_sign_up_success(auth_manager, mock_supabase, mock_user_data):
    """Test successful user registration."""
    mock_supabase.auth.sign_up.return_value = MagicMock(user=mock_user_data)
    
    user, error = await auth_manager.sign_up(
        email='test@example.com',
        password='password123',
        phone='+1234567890'
    )
    
    assert user is not None
    assert isinstance(user, AuthUser)
    assert user.id == 'test-user-id'
    assert user.email == 'test@example.com'
    assert user.phone == '+1234567890'
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.last_sign_in_at, datetime)
    assert user.role == 'authenticated'
    assert user.metadata == {'name': 'Test User'}
    assert error is None
    
    mock_supabase.auth.sign_up.assert_called_once_with({
        'email': 'test@example.com',
        'password': 'password123',
        'phone': '+1234567890'
    })


@pytest.mark.asyncio
async def test_sign_up_failure(auth_manager, mock_supabase):
    """Test user registration failure."""
    mock_supabase.auth.sign_up.side_effect = Exception('Email already registered')
    
    user, error = await auth_manager.sign_up(
        email='test@example.com',
        password='password123'
    )
    
    assert user is None
    assert error == 'Email already registered'
    mock_supabase.auth.sign_up.assert_called_once()


@pytest.mark.asyncio
async def test_sign_in_success(auth_manager, mock_supabase, mock_user_data):
    """Test successful sign in."""
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(user=mock_user_data)
    
    user, error = await auth_manager.sign_in(
        email='test@example.com',
        password='password123'
    )
    
    assert user is not None
    assert isinstance(user, AuthUser)
    assert user.email == 'test@example.com'
    assert error is None
    
    mock_supabase.auth.sign_in_with_password.assert_called_once_with({
        'email': 'test@example.com',
        'password': 'password123'
    })


@pytest.mark.asyncio
async def test_sign_in_failure(auth_manager, mock_supabase):
    """Test sign in failure."""
    mock_supabase.auth.sign_in_with_password.side_effect = Exception('Invalid credentials')
    
    user, error = await auth_manager.sign_in(
        email='test@example.com',
        password='wrong_password'
    )
    
    assert user is None
    assert error == 'Invalid credentials'
    mock_supabase.auth.sign_in_with_password.assert_called_once()


@pytest.mark.asyncio
async def test_sign_in_with_phone_success(auth_manager, mock_supabase, mock_user_data):
    """Test successful sign in with phone."""
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(user=mock_user_data)
    
    user, error = await auth_manager.sign_in_with_phone(
        phone='+1234567890',
        password='password123'
    )
    
    assert user is not None
    assert isinstance(user, AuthUser)
    assert user.phone == '+1234567890'
    assert error is None
    
    mock_supabase.auth.sign_in_with_password.assert_called_once_with({
        'phone': '+1234567890',
        'password': 'password123'
    })


@pytest.mark.asyncio
async def test_sign_out_success(auth_manager, mock_supabase):
    """Test successful sign out."""
    success, error = await auth_manager.sign_out()
    
    assert success is True
    assert error is None
    mock_supabase.auth.sign_out.assert_called_once()


@pytest.mark.asyncio
async def test_sign_out_failure(auth_manager, mock_supabase):
    """Test sign out failure."""
    mock_supabase.auth.sign_out.side_effect = Exception('Network error')
    
    success, error = await auth_manager.sign_out()
    
    assert success is False
    assert error == 'Network error'
    mock_supabase.auth.sign_out.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_success(auth_manager, mock_supabase):
    """Test successful password reset request."""
    success, error = await auth_manager.reset_password('test@example.com')
    
    assert success is True
    assert error is None
    mock_supabase.auth.reset_password_for_email.assert_called_once_with('test@example.com')


@pytest.mark.asyncio
async def test_reset_password_failure(auth_manager, mock_supabase):
    """Test password reset request failure."""
    mock_supabase.auth.reset_password_for_email.side_effect = Exception('Email not found')
    
    success, error = await auth_manager.reset_password('nonexistent@example.com')
    
    assert success is False
    assert error == 'Email not found'
    mock_supabase.auth.reset_password_for_email.assert_called_once()


@pytest.mark.asyncio
async def test_update_password_success(auth_manager, mock_supabase):
    """Test successful password update."""
    success, error = await auth_manager.update_password('new_password123')
    
    assert success is True
    assert error is None
    mock_supabase.auth.update_user.assert_called_once_with({'password': 'new_password123'})


@pytest.mark.asyncio
async def test_update_email_success(auth_manager, mock_supabase):
    """Test successful email update."""
    success, error = await auth_manager.update_email('new@example.com')
    
    assert success is True
    assert error is None
    mock_supabase.auth.update_user.assert_called_once_with({'email': 'new@example.com'})


@pytest.mark.asyncio
async def test_update_phone_success(auth_manager, mock_supabase):
    """Test successful phone update."""
    success, error = await auth_manager.update_phone('+1987654321')
    
    assert success is True
    assert error is None
    mock_supabase.auth.update_user.assert_called_once_with({'phone': '+1987654321'})


@pytest.mark.asyncio
async def test_get_user_success(auth_manager, mock_supabase, mock_user_data):
    """Test successful user retrieval."""
    mock_supabase.auth.get_user.return_value = MagicMock(user=mock_user_data)
    
    user = await auth_manager.get_user()
    
    assert user is not None
    assert isinstance(user, AuthUser)
    assert user.id == 'test-user-id'
    assert user.email == 'test@example.com'
    mock_supabase.auth.get_user.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_not_authenticated(auth_manager, mock_supabase):
    """Test user retrieval when not authenticated."""
    mock_supabase.auth.get_user.return_value = MagicMock(user=None)
    
    user = await auth_manager.get_user()
    
    assert user is None
    mock_supabase.auth.get_user.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_success(auth_manager, mock_supabase):
    """Test successful session retrieval."""
    mock_session = {'access_token': 'test-token', 'refresh_token': 'refresh-token'}
    mock_supabase.auth.get_session.return_value = MagicMock(session=mock_session)
    
    session = await auth_manager.get_session()
    
    assert session == mock_session
    mock_supabase.auth.get_session.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_not_authenticated(auth_manager, mock_supabase):
    """Test session retrieval when not authenticated."""
    mock_supabase.auth.get_session.return_value = MagicMock(session=None)
    
    session = await auth_manager.get_session()
    
    assert session is None
    mock_supabase.auth.get_session.assert_called_once()


def test_parse_user(auth_manager, mock_user_data):
    """Test user data parsing."""
    user = auth_manager._parse_user(mock_user_data)
    
    assert isinstance(user, AuthUser)
    assert user.id == 'test-user-id'
    assert user.email == 'test@example.com'
    assert user.phone == '+1234567890'
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.last_sign_in_at, datetime)
    assert user.role == 'authenticated'
    assert user.metadata == {'name': 'Test User'}


def test_parse_user_minimal_data(auth_manager):
    """Test user data parsing with minimal data."""
    minimal_data = {
        'id': 'test-user-id',
        'email': 'test@example.com',
        'created_at': '2024-01-01T00:00:00Z'
    }
    
    user = auth_manager._parse_user(minimal_data)
    
    assert isinstance(user, AuthUser)
    assert user.id == 'test-user-id'
    assert user.email == 'test@example.com'
    assert user.phone is None
    assert isinstance(user.created_at, datetime)
    assert user.last_sign_in_at is None
    assert user.role == 'authenticated'
    assert user.metadata == {} 