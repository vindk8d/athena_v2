"""Authentication manager for Supabase Auth integration."""

import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class AuthUser:
    """User authentication data."""
    id: str
    email: str
    phone: Optional[str]
    created_at: datetime
    last_sign_in_at: Optional[datetime]
    role: str
    metadata: Dict[str, Any]


class AuthManager:
    """Manages user authentication with Supabase."""
    
    def __init__(self, supabase_client: Optional[Client] = None):
        """Initialize the authentication manager."""
        self.settings = get_settings()
        self.supabase = supabase_client or self._create_supabase_client()
    
    def _create_supabase_client(self) -> Client:
        """Create a Supabase client with proper configuration."""
        options = ClientOptions(
            schema='public',
            auto_refresh_token=True,
            persist_session=True,
            detect_session_in_url=True
        )
        
        return create_client(
            self.settings.supabase_url,
            self.settings.supabase_anon_key,
            options=options
        )
    
    async def sign_up(self, email: str, password: str, phone: Optional[str] = None) -> Tuple[Optional[AuthUser], Optional[str]]:
        """
        Sign up a new user.
        
        Args:
            email: User's email address
            password: User's password
            phone: User's phone number (optional)
            
        Returns:
            Tuple of (AuthUser object if successful, error message if failed)
        """
        try:
            data = {'email': email, 'password': password}
            if phone:
                data['phone'] = phone
            
            response = await self.supabase.auth.sign_up(data)
            
            if not response.user:
                return None, "Failed to create user"
            
            return self._parse_user(response.user), None
            
        except Exception as e:
            logger.error(f"Error signing up user: {e}")
            return None, str(e)
    
    async def sign_in(self, email: str, password: str) -> Tuple[Optional[AuthUser], Optional[str]]:
        """
        Sign in an existing user.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            Tuple of (AuthUser object if successful, error message if failed)
        """
        try:
            response = await self.supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            if not response.user:
                return None, "Invalid credentials"
            
            return self._parse_user(response.user), None
            
        except Exception as e:
            logger.error(f"Error signing in user: {e}")
            return None, str(e)
    
    async def sign_in_with_phone(self, phone: str, password: str) -> Tuple[Optional[AuthUser], Optional[str]]:
        """
        Sign in a user with phone number.
        
        Args:
            phone: User's phone number
            password: User's password
            
        Returns:
            Tuple of (AuthUser object if successful, error message if failed)
        """
        try:
            response = await self.supabase.auth.sign_in_with_password({
                'phone': phone,
                'password': password
            })
            
            if not response.user:
                return None, "Invalid credentials"
            
            return self._parse_user(response.user), None
            
        except Exception as e:
            logger.error(f"Error signing in user with phone: {e}")
            return None, str(e)
    
    async def sign_out(self) -> Tuple[bool, Optional[str]]:
        """
        Sign out the current user.
        
        Returns:
            Tuple of (success boolean, error message if failed)
        """
        try:
            await self.supabase.auth.sign_out()
            return True, None
        except Exception as e:
            logger.error(f"Error signing out user: {e}")
            return False, str(e)
    
    async def reset_password(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Send a password reset email.
        
        Args:
            email: User's email address
            
        Returns:
            Tuple of (success boolean, error message if failed)
        """
        try:
            await self.supabase.auth.reset_password_for_email(email)
            return True, None
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False, str(e)
    
    async def update_password(self, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Update the current user's password.
        
        Args:
            new_password: New password
            
        Returns:
            Tuple of (success boolean, error message if failed)
        """
        try:
            await self.supabase.auth.update_user({'password': new_password})
            return True, None
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return False, str(e)
    
    async def update_email(self, new_email: str) -> Tuple[bool, Optional[str]]:
        """
        Update the current user's email.
        
        Args:
            new_email: New email address
            
        Returns:
            Tuple of (success boolean, error message if failed)
        """
        try:
            await self.supabase.auth.update_user({'email': new_email})
            return True, None
        except Exception as e:
            logger.error(f"Error updating email: {e}")
            return False, str(e)
    
    async def update_phone(self, new_phone: str) -> Tuple[bool, Optional[str]]:
        """
        Update the current user's phone number.
        
        Args:
            new_phone: New phone number
            
        Returns:
            Tuple of (success boolean, error message if failed)
        """
        try:
            await self.supabase.auth.update_user({'phone': new_phone})
            return True, None
        except Exception as e:
            logger.error(f"Error updating phone: {e}")
            return False, str(e)
    
    async def get_user(self) -> Optional[AuthUser]:
        """
        Get the current authenticated user.
        
        Returns:
            AuthUser object if authenticated, None otherwise
        """
        try:
            response = await self.supabase.auth.get_user()
            if not response.user:
                return None
            return self._parse_user(response.user)
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def get_session(self) -> Optional[Dict[str, Any]]:
        """
        Get the current session.
        
        Returns:
            Session data if authenticated, None otherwise
        """
        try:
            response = await self.supabase.auth.get_session()
            return response.session
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
    
    def _parse_user(self, user_data: Dict[str, Any]) -> AuthUser:
        """
        Parse user data from Supabase response.
        
        Args:
            user_data: User data from Supabase
            
        Returns:
            AuthUser object
        """
        return AuthUser(
            id=user_data['id'],
            email=user_data['email'],
            phone=user_data.get('phone'),
            created_at=datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00')),
            last_sign_in_at=datetime.fromisoformat(user_data['last_sign_in_at'].replace('Z', '+00:00')) if user_data.get('last_sign_in_at') else None,
            role=user_data.get('role', 'authenticated'),
            metadata=user_data.get('user_metadata', {})
        ) 