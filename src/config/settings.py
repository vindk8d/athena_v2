"""
Athena Digital Executive Assistant - Configuration Settings
Manages all environment variables and application configuration.
"""

import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        """Initialize settings by loading environment variables."""
        # Load environment variables from .env file
        env_path = Path(__file__).parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)
        
        # Validate required environment variables
        self._validate_required_vars()
    
    def _validate_required_vars(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = [
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY", 
            "SUPABASE_SERVICE_ROLE_KEY",
            "TELEGRAM_BOT_TOKEN",
            "OPENAI_API_KEY",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_CALENDAR_CREDENTIALS_FILE"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
    
    # Supabase Configuration
    @property
    def supabase_url(self) -> str:
        """Supabase project URL."""
        return os.getenv("SUPABASE_URL", "")
    
    @property
    def supabase_anon_key(self) -> str:
        """Supabase anonymous key for client operations."""
        return os.getenv("SUPABASE_ANON_KEY", "")
    
    @property
    def supabase_service_role_key(self) -> str:
        """Supabase service role key for admin operations."""
        return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Telegram Bot Configuration
    @property
    def telegram_bot_token(self) -> str:
        """Telegram bot token."""
        return os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    @property
    def telegram_webhook_url(self) -> str:
        """Telegram webhook URL."""
        return os.getenv("TELEGRAM_WEBHOOK_URL", "")
    
    @property
    def webhook_url(self) -> Optional[str]:
        """Telegram webhook URL for production."""
        return os.getenv("WEBHOOK_URL")
    
    @property
    def webhook_secret(self) -> Optional[str]:
        """Webhook secret for security."""
        return os.getenv("WEBHOOK_SECRET")
    
    # OpenAI Configuration
    @property
    def openai_api_key(self) -> str:
        """OpenAI API key."""
        return os.getenv("OPENAI_API_KEY", "")
    
    # Google Calendar Configuration
    @property
    def google_client_id(self) -> str:
        """Google OAuth client ID."""
        return os.getenv("GOOGLE_CLIENT_ID", "")
    
    @property
    def google_client_secret(self) -> str:
        """Google OAuth client secret."""
        return os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    @property
    def google_redirect_uri(self) -> str:
        """Google OAuth redirect URI."""
        return os.getenv("GOOGLE_REDIRECT_URI", f"http://localhost:{self.frontend_port}/auth/callback/google")
    
    @property
    def google_calendar_credentials_file(self) -> str:
        """Path to Google Calendar credentials file."""
        return os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials/google_calendar_credentials.json")
    
    @property
    def google_calendar_client_secrets(self) -> str:
        """Path to Google Calendar client secrets file."""
        return os.getenv("GOOGLE_CALENDAR_CLIENT_SECRETS", "credentials/google_calendar_client_secrets.json")
    
    @property
    def google_calendar_redirect_uri(self) -> str:
        """Google Calendar OAuth redirect URI."""
        return os.getenv("GOOGLE_CALENDAR_REDIRECT_URI", f"http://localhost:{self.frontend_port}/auth/callback/google/calendar")
    
    # Application Configuration
    @property
    def environment(self) -> str:
        """Application environment (development, staging, production)."""
        return os.getenv("ENVIRONMENT", "development")
    
    @property
    def log_level(self) -> str:
        """Logging level."""
        return os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def port(self) -> int:
        """Backend API server port."""
        return int(os.getenv("PORT", "8000"))
    
    @property
    def frontend_port(self) -> int:
        """Frontend development server port."""
        return int(os.getenv("FRONTEND_PORT", "3000"))
    
    @property
    def debug(self) -> bool:
        """Enable debug mode."""
        return self.environment.lower() == "development"
    
    # Database Configuration
    @property
    def database_pool_size(self) -> int:
        """Database connection pool size."""
        return int(os.getenv("DATABASE_POOL_SIZE", "10"))
    
    # AI Agent Configuration
    @property
    def max_conversation_context(self) -> int:
        """Maximum number of messages to include in conversation context."""
        return int(os.getenv("MAX_CONVERSATION_CONTEXT", "5"))
    
    @property
    def openai_model(self) -> str:
        """OpenAI model to use."""
        return os.getenv("OPENAI_MODEL", "gpt-4")
    
    @property
    def openai_temperature(self) -> float:
        """OpenAI temperature setting."""
        return float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # Calendar Configuration
    @property
    def default_meeting_duration_minutes(self) -> int:
        """Default meeting duration in minutes."""
        return int(os.getenv("DEFAULT_MEETING_DURATION_MINUTES", "60"))
    
    @property
    def default_buffer_time_minutes(self) -> int:
        """Default buffer time between meetings in minutes."""
        return int(os.getenv("DEFAULT_BUFFER_TIME_MINUTES", "15"))
    
    # Security Configuration
    @property
    def jwt_secret_key(self) -> str:
        """JWT secret key for session management."""
        return os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
    
    @property
    def cors_origins(self) -> List[str]:
        """Allowed CORS origins."""
        origins = os.getenv("CORS_ORIGINS", f"http://localhost:{self.frontend_port}")
        return [origin.strip() for origin in origins.split(",")]


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings 