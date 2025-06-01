"""
Message Parser and Validator for Athena Digital Executive Assistant.

This module handles parsing and validation of incoming Telegram messages,
including user identification, content validation, and input sanitization.
"""

import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from telegram import Update, Message, User

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ParsedUser:
    """Structured user information extracted from Telegram."""
    telegram_id: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    language_code: Optional[str]
    is_bot: bool


@dataclass
class ParsedMessage:
    """Structured message information from Telegram."""
    message_id: int
    text: str
    clean_text: str  # Sanitized version
    user: ParsedUser
    chat_id: int
    timestamp: datetime
    message_type: str
    is_command: bool
    command: Optional[str]
    command_args: List[str]


class MessageParseError(Exception):
    """Custom exception for message parsing errors."""
    pass


class MessageValidator:
    """Validates incoming Telegram messages."""
    
    # Maximum message length
    MAX_MESSAGE_LENGTH = 4000
    
    # Minimum message length
    MIN_MESSAGE_LENGTH = 1
    
    # Allowed message types
    ALLOWED_MESSAGE_TYPES = {'text', 'command'}
    
    # Command pattern
    COMMAND_PATTERN = re.compile(r'^/([a-zA-Z0-9_]+)(?:\s+(.*))?$')
    
    # Text sanitization patterns
    URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')
    
    @classmethod
    def validate_message_content(cls, text: str) -> bool:
        """
        Validate message content for basic requirements.
        
        Args:
            text: Message text to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not text or not isinstance(text, str):
            return False
        
        # Check length constraints
        if len(text) < cls.MIN_MESSAGE_LENGTH or len(text) > cls.MAX_MESSAGE_LENGTH:
            return False
        
        # Check for non-printable characters (except common whitespace)
        if any(ord(char) < 32 and char not in '\n\r\t' for char in text):
            return False
        
        return True
    
    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Sanitize message text for safe processing.
        
        Args:
            text: Raw message text
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove leading/trailing whitespace
        sanitized = text.strip()
        
        # Replace multiple whitespace with single space
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Remove non-printable characters except common whitespace
        sanitized = ''.join(char for char in sanitized 
                          if ord(char) >= 32 or char in '\n\r\t')
        
        return sanitized
    
    @classmethod
    def extract_contact_info(cls, text: str) -> Dict[str, List[str]]:
        """
        Extract potential contact information from message text.
        
        Args:
            text: Message text to analyze
            
        Returns:
            Dictionary with extracted emails, phones, and URLs
        """
        return {
            'emails': cls.EMAIL_PATTERN.findall(text),
            'phones': [f"{g[0]}{g[1]}-{g[2]}-{g[3]}" for g in cls.PHONE_PATTERN.findall(text)],
            'urls': cls.URL_PATTERN.findall(text)
        }
    
    @classmethod
    def is_command(cls, text: str) -> bool:
        """
        Check if message is a Telegram command.
        
        Args:
            text: Message text
            
        Returns:
            True if message is a command
        """
        return bool(cls.COMMAND_PATTERN.match(text.strip()))
    
    @classmethod
    def parse_command(cls, text: str) -> tuple[Optional[str], List[str]]:
        """
        Parse command and arguments from message text.
        
        Args:
            text: Message text containing command
            
        Returns:
            Tuple of (command_name, arguments_list)
        """
        match = cls.COMMAND_PATTERN.match(text.strip())
        if not match:
            return None, []
        
        command = match.group(1).lower()
        args_text = match.group(2) or ""
        args = [arg.strip() for arg in args_text.split()] if args_text else []
        
        return command, args


class MessageParser:
    """Parses Telegram messages and extracts structured information."""
    
    def __init__(self):
        """Initialize the message parser."""
        self.validator = MessageValidator()
    
    def parse_user(self, telegram_user: User) -> ParsedUser:
        """
        Parse Telegram user information.
        
        Args:
            telegram_user: Telegram User object
            
        Returns:
            ParsedUser with structured user information
        """
        # Build full name
        name_parts = [
            telegram_user.first_name or "",
            telegram_user.last_name or ""
        ]
        full_name = " ".join(part for part in name_parts if part).strip()
        if not full_name:
            full_name = telegram_user.username or f"User{telegram_user.id}"
        
        return ParsedUser(
            telegram_id=str(telegram_user.id),
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            full_name=full_name,
            language_code=telegram_user.language_code,
            is_bot=telegram_user.is_bot
        )
    
    def parse_message(self, update: Update) -> Optional[ParsedMessage]:
        """
        Parse a Telegram update into structured message data.
        
        Args:
            update: Telegram Update object
            
        Returns:
            ParsedMessage if successful, None if invalid
            
        Raises:
            MessageParseError: If message parsing fails
        """
        try:
            # Validate update has a message
            if not update.message:
                logger.warning("Update has no message")
                return None
            
            message = update.message
            
            # Only process text messages
            if not message.text:
                logger.info(f"Ignoring non-text message from user {message.from_user.id}")
                return None
            
            # Validate message content
            if not self.validator.validate_message_content(message.text):
                logger.warning(f"Invalid message content from user {message.from_user.id}")
                raise MessageParseError("Invalid message content")
            
            # Parse user information
            if not message.from_user:
                logger.error("Message has no user information")
                raise MessageParseError("Missing user information")
            
            # Skip messages from bots
            if message.from_user.is_bot:
                logger.info(f"Ignoring message from bot {message.from_user.id}")
                return None
            
            parsed_user = self.parse_user(message.from_user)
            
            # Sanitize message text
            clean_text = self.validator.sanitize_text(message.text)
            
            # Determine message type and parse commands
            is_command = self.validator.is_command(clean_text)
            command = None
            command_args = []
            
            if is_command:
                command, command_args = self.validator.parse_command(clean_text)
                message_type = "command"
            else:
                message_type = "text"
            
            # Create parsed message
            parsed_message = ParsedMessage(
                message_id=message.message_id,
                text=message.text,
                clean_text=clean_text,
                user=parsed_user,
                chat_id=message.chat.id,
                timestamp=message.date,
                message_type=message_type,
                is_command=is_command,
                command=command,
                command_args=command_args
            )
            
            logger.info(
                f"Parsed {message_type} message from user {parsed_user.telegram_id} "
                f"({parsed_user.full_name}): {clean_text[:50]}..."
            )
            
            return parsed_message
            
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            raise MessageParseError(f"Failed to parse message: {e}")
    
    def extract_intent_keywords(self, text: str) -> Dict[str, bool]:
        """
        Extract intent keywords from message text.
        
        Args:
            text: Clean message text
            
        Returns:
            Dictionary of intent flags
        """
        text_lower = text.lower()
        
        # Meeting/scheduling keywords
        meeting_keywords = [
            'meeting', 'schedule', 'appointment', 'call', 'conference',
            'meet', 'time', 'calendar', 'available', 'book'
        ]
        
        # Contact information keywords
        contact_keywords = [
            'email', 'phone', 'contact', 'name', 'address'
        ]
        
        # Greeting keywords
        greeting_keywords = [
            'hello', 'hi', 'hey', 'good morning', 'good afternoon',
            'good evening', 'start', 'begin'
        ]
        
        # Help keywords
        help_keywords = [
            'help', 'assist', 'support', 'how', 'what', 'can you'
        ]
        
        return {
            'wants_meeting': any(keyword in text_lower for keyword in meeting_keywords),
            'providing_contact': any(keyword in text_lower for keyword in contact_keywords),
            'greeting': any(keyword in text_lower for keyword in greeting_keywords),
            'needs_help': any(keyword in text_lower for keyword in help_keywords),
            'has_email': bool(self.validator.EMAIL_PATTERN.search(text)),
            'has_phone': bool(self.validator.PHONE_PATTERN.search(text))
        }
    
    def validate_and_parse(self, update: Update) -> Optional[ParsedMessage]:
        """
        Convenience method that validates and parses a message.
        
        Args:
            update: Telegram Update object
            
        Returns:
            ParsedMessage if valid and successfully parsed, None otherwise
        """
        try:
            return self.parse_message(update)
        except MessageParseError as e:
            logger.warning(f"Message validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in message parsing: {e}")
            return None


# Global parser instance
_parser_instance: Optional[MessageParser] = None


def get_message_parser() -> MessageParser:
    """Get the global message parser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = MessageParser()
    return _parser_instance


# Utility functions for common operations

def validate_telegram_update(update: Update) -> bool:
    """
    Quick validation of Telegram update.
    
    Args:
        update: Telegram Update object
        
    Returns:
        True if update is valid for processing
    """
    if not update or not update.message:
        return False
    
    message = update.message
    if not message.text or not message.from_user:
        return False
    
    # Skip bot messages
    if message.from_user.is_bot:
        return False
    
    return MessageValidator.validate_message_content(message.text)


def extract_user_id(update: Update) -> Optional[str]:
    """
    Extract user ID from Telegram update.
    
    Args:
        update: Telegram Update object
        
    Returns:
        User ID as string, or None if not available
    """
    if not update or not update.message or not update.message.from_user:
        return None
    
    return str(update.message.from_user.id)


def is_text_message(update: Update) -> bool:
    """
    Check if update contains a text message.
    
    Args:
        update: Telegram Update object
        
    Returns:
        True if update contains text message
    """
    return (update and 
            update.message and 
            update.message.text and 
            not update.message.from_user.is_bot)


# Export main classes and functions
__all__ = [
    'MessageParser',
    'MessageValidator', 
    'ParsedMessage',
    'ParsedUser',
    'MessageParseError',
    'get_message_parser',
    'validate_telegram_update',
    'extract_user_id',
    'is_text_message'
] 