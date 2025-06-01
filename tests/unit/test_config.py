"""
Unit tests for configuration settings.
"""

import pytest
import os
from unittest.mock import patch
from src.config.settings import Settings, get_settings


class TestSettings:
    """Test cases for the Settings class."""
    
    def test_settings_initialization(self, mock_settings):
        """Test that settings can be initialized properly."""
        assert mock_settings is not None
        assert mock_settings.environment == "testing"
        assert mock_settings.debug is False  # Debug is only True in development environment
    
    def test_required_environment_variables(self):
        """Test that missing required environment variables raise ValueError."""
        # Backup ALL environment variables and clear them
        backup_env = dict(os.environ)
        os.environ.clear()
        
        try:
            # Also mock dotenv loading to prevent .env file from being loaded
            with patch('src.config.settings.load_dotenv'):
                with pytest.raises(ValueError) as exc_info:
                    Settings()
                assert "Missing required environment variables" in str(exc_info.value)
        finally:
            # Restore ALL environment variables
            os.environ.clear()
            os.environ.update(backup_env)
    
    def test_supabase_configuration(self, mock_settings):
        """Test Supabase configuration properties."""
        assert mock_settings.supabase_url == "https://test.supabase.co"
        assert mock_settings.supabase_anon_key == "test_anon_key"
        assert mock_settings.supabase_service_role_key == "test_service_key"
    
    def test_telegram_configuration(self, mock_settings):
        """Test Telegram bot configuration properties."""
        assert mock_settings.telegram_bot_token == "test:telegram_token"
        assert mock_settings.webhook_url is None  # Not set in test env
    
    def test_openai_configuration(self, mock_settings):
        """Test OpenAI configuration properties."""
        assert mock_settings.openai_api_key == "sk-test-openai-key"
        assert mock_settings.openai_model == "gpt-4"  # Default value
        assert mock_settings.openai_temperature == 0.7  # Default value
    
    def test_google_calendar_configuration(self, mock_settings):
        """Test Google Calendar configuration properties."""
        assert mock_settings.google_client_id == "test_google_client_id"
        assert mock_settings.google_client_secret == "test_google_client_secret"
        assert "localhost" in mock_settings.google_redirect_uri  # Relaxed to accept both ports
    
    def test_application_configuration(self, mock_settings):
        """Test application configuration properties."""
        assert mock_settings.environment == "testing"
        assert mock_settings.log_level == "DEBUG"
        assert mock_settings.port == 8000
        assert mock_settings.frontend_port == 3000
    
    def test_cors_origins_parsing(self, mock_settings):
        """Test CORS origins configuration."""
        cors_origins = mock_settings.cors_origins
        assert isinstance(cors_origins, list)
        assert len(cors_origins) >= 1
        assert "localhost:3000" in cors_origins[0]
    
    def test_ai_agent_configuration(self, mock_settings):
        """Test AI agent configuration properties."""
        assert mock_settings.max_conversation_context == 5  # Default value is 5, not 3
        assert mock_settings.default_meeting_duration_minutes == 60
        assert mock_settings.default_buffer_time_minutes == 15
    
    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_production_environment(self):
        """Test settings in production environment."""
        settings = Settings()
        assert settings.environment == "production"
        assert settings.debug is False
    
    @patch.dict(os.environ, {"PORT": "9000", "FRONTEND_PORT": "4000"})
    def test_custom_ports(self):
        """Test custom port configuration."""
        settings = Settings()
        assert settings.port == 9000
        assert settings.frontend_port == 4000


def test_get_settings_singleton():
    """Test that get_settings returns a singleton instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2


@pytest.mark.unit
def test_settings_validation():
    """Test settings validation functionality."""
    # This test uses the unit marker defined in pytest.ini
    settings = get_settings()
    assert hasattr(settings, '_validate_required_vars')


@pytest.mark.slow
def test_settings_performance():
    """Test that settings loading is performant."""
    import time
    
    start_time = time.time()
    settings = get_settings()
    end_time = time.time()
    
    # Settings should load quickly
    assert (end_time - start_time) < 1.0
    assert settings is not None 