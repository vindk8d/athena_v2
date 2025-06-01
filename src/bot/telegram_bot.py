"""
Telegram Bot Implementation for Athena Digital Executive Assistant.

This module handles all Telegram bot functionality including:
- Bot initialization and configuration
- Message handling and processing
- Webhook management
- User interaction flows
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, UTC
import pytz

from telegram import Update, Bot, BotCommand
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    CallbackQueryHandler
)
from telegram.error import TelegramError, NetworkError, TimedOut

from src.config.settings import get_settings
from src.database.supabase_client import SupabaseClient
from src.agent.athena_agent import AthenaAgent
from src.utils.conversation_manager import ConversationManager
from src.utils.message_parser import (
    get_message_parser, 
    validate_telegram_update,
    extract_user_id,
    ParsedMessage,
    MessageParseError
)
from src.utils.message_formatting import (
    format_info_message,
    format_error_message,
    format_confirmation_message,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class AthenaTelegramBot:
    """
    Main Telegram bot class for Athena Digital Executive Assistant.
    
    Handles all bot interactions, message processing, and integration
    with the AI agent and database systems.
    """
    
    def __init__(self):
        """Initialize the Athena Telegram bot."""
        self.settings = get_settings()
        self.db_client = SupabaseClient()
        self.ai_agent = AthenaAgent()
        self.conversation_manager = ConversationManager()
        self.message_parser = get_message_parser()
        
        # Initialize bot application
        self.application = None
        self.bot = None
        
        # Track active conversations
        self.active_conversations: Dict[int, Dict[str, Any]] = {}
        
    async def initialize(self) -> None:
        """Initialize the bot application and handlers."""
        try:
            if self.application is not None:
                logger.info("Bot application already initialized")
                return

            # Create bot application
            self.application = Application.builder().token(
                self.settings.telegram_bot_token
            ).build()
            
            self.bot = self.application.bot
            
            # Register command handlers
            self.application.add_handler(
                CommandHandler("start", self.start_command)
            )
            self.application.add_handler(
                CommandHandler("help", self.help_command)
            )
            self.application.add_handler(
                CommandHandler("cancel", self.cancel_command)
            )
            
            # Register message handler for all text messages
            self.application.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, 
                    self.handle_message
                )
            )
            
            # Register callback query handler for inline keyboards
            self.application.add_handler(
                CallbackQueryHandler(self.handle_callback_query)
            )
            
            # Set bot commands
            await self.set_bot_commands()
            
            # Initialize the application
            await self.application.initialize()
            
            logger.info("Athena Telegram bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    async def set_bot_commands(self) -> None:
        """Set the bot's command menu."""
        commands = [
            BotCommand("start", "Start conversation with Athena"),
            BotCommand("help", "Get help and available commands"),
            BotCommand("cancel", "Cancel current operation")
        ]
        
        try:
            await self.bot.set_my_commands(commands)
            logger.info("Bot commands set successfully")
        except TelegramError as e:
            logger.error(f"Failed to set bot commands: {e}")
    
    async def _get_active_conversation_count_today(self) -> int:
        """
        Count unique contacts who have sent messages today (UTC).
        """
        # Query messages table for unique contact_ids with messages today
        utc_now = datetime.now(UTC)
        start_of_day = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            # Use Supabase RPC or filter if available, else fallback to all messages
            response = self.db_client.supabase.table("messages").select("contact_id,created_at").gte("created_at", start_of_day.isoformat()).execute()
            contact_ids = set()
            for row in response.data:
                contact_ids.add(row["contact_id"])
            return len(contact_ids)
        except Exception as e:
            logger.error(f"Error counting active conversations: {e}")
            return 0
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command."""
        # Validate and parse the update
        if not validate_telegram_update(update):
            logger.warning("Invalid update received in start command")
            return
        
        parsed_message = self.message_parser.validate_and_parse(update)
        if not parsed_message:
            logger.warning("Failed to parse start command message")
            return
        
        user = parsed_message.user
        chat_id = parsed_message.chat_id
        
        logger.info(f"Start command received from user {user.telegram_id} ({user.full_name})")
        
        # Rate limiting: check if user is new and if limit is reached
        existing_contact = await self.db_client.get_contact_by_telegram_id(user.telegram_id)
        is_new_user = not existing_contact
        if is_new_user:
            active_count = await self._get_active_conversation_count_today()
            if active_count >= 10:
                limit_message = (
                    "I'm currently assisting the maximum number of contacts for today. "
                    "Please try again tomorrow or check back later. Thank you for your patience!"
                )
                msg = format_error_message(limit_message)
                await self.send_message(chat_id, msg["text"], parse_mode=msg["parse_mode"])
                return
        
        if existing_contact:
            # Returning user
            welcome_message = (
                f"Welcome back, {existing_contact['name']}! 👋\n\n"
                "I'm Athena, your digital executive assistant. "
                "I'm ready to help you schedule meetings and manage our conversations.\n\n"
                "How can I assist you today?"
            )
        else:
            # New user
            welcome_message = (
                "Hello! I'm Athena, your digital executive assistant. 🤖\n\n"
                "I help coordinate meetings and manage contacts through natural conversation. "
                "I can:\n"
                "• Collect your contact information\n"
                "• Schedule meetings based on calendar availability\n"
                "• Remember our previous conversations\n"
                "• Send calendar invitations\n\n"
                "To get started, may I have your name and email address?"
            )
        
        # Format and send welcome message
        msg = format_info_message(welcome_message)
        await self.send_message(chat_id, msg["text"], parse_mode=msg["parse_mode"])
        
        # Initialize conversation context
        self.active_conversations[chat_id] = {
            "user_id": user.telegram_id,
            "username": user.username,
            "full_name": user.full_name,
            "started_at": datetime.now(UTC),
            "context": "introduction" if not existing_contact else "general"
        }
        
        # Store the start command interaction
        await self.store_message(
            telegram_id=user.telegram_id,
            sender="user",
            content="/start",
            message_id=parsed_message.message_id
        )
        
        await self.store_message(
            telegram_id=user.telegram_id,
            sender="assistant",
            content=welcome_message
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command."""
        # Validate and parse the update
        if not validate_telegram_update(update):
            logger.warning("Invalid update received in help command")
            return
        
        parsed_message = self.message_parser.validate_and_parse(update)
        if not parsed_message:
            logger.warning("Failed to parse help command message")
            return
        
        help_message = (
            "🤖 *Athena Digital Executive Assistant*\n\n"
            "*Available Commands:*\n"
            "/start - Start or restart conversation\n"
            "/help - Show this help message\n"
            "/cancel - Cancel current operation\n\n"
            "*What I can do:*\n"
            "• Help you schedule meetings\n"
            "• Manage your contact information\n"
            "• Check calendar availability\n"
            "• Send meeting invitations\n"
            "• Remember our conversations\n\n"
            "*How to interact:*\n"
            "Just send me messages in natural language! "
            "I'll understand what you need and guide you through the process.\n\n"
            "*Examples:*\n"
            "• \"I'd like to schedule a meeting\"\n"
            "• \"My email is john@example.com\"\n"
            "• \"Let's meet for 1 hour tomorrow\"\n\n"
            "Feel free to ask me anything! 😊"
        )
        msg = format_info_message(help_message)
        await update.message.reply_text(msg["text"], parse_mode=msg["parse_mode"])
        
        # Store the help interaction
        await self.store_message(
            telegram_id=parsed_message.user.telegram_id,
            sender="user",
            content="/help",
            message_id=parsed_message.message_id
        )
        
        await self.store_message(
            telegram_id=parsed_message.user.telegram_id,
            sender="assistant",
            content=help_message
        )
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /cancel command."""
        # Validate and parse the update
        if not validate_telegram_update(update):
            logger.warning("Invalid update received in cancel command")
            return
        
        parsed_message = self.message_parser.validate_and_parse(update)
        if not parsed_message:
            logger.warning("Failed to parse cancel command message")
            return
        
        chat_id = parsed_message.chat_id
        
        # Clear conversation context
        if chat_id in self.active_conversations:
            del self.active_conversations[chat_id]
        
        cancel_message = (
            "Operation cancelled. ❌\n\n"
            "Feel free to start a new conversation anytime! "
            "Just send me a message or use /start."
        )
        msg = format_info_message(cancel_message)
        await update.message.reply_text(msg["text"], parse_mode=msg["parse_mode"])
        
        # Store the cancel interaction
        await self.store_message(
            telegram_id=parsed_message.user.telegram_id,
            sender="user",
            content="/cancel",
            message_id=parsed_message.message_id
        )
        
        await self.store_message(
            telegram_id=parsed_message.user.telegram_id,
            sender="assistant",
            content=cancel_message
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages with enhanced parsing and validation."""
        # Validate update first
        if not validate_telegram_update(update):
            logger.warning("Received invalid Telegram update")
            return
        
        # Parse and validate the message
        try:
            parsed_message = self.message_parser.validate_and_parse(update)
            if not parsed_message:
                logger.warning("Failed to parse incoming message")
                return
            
            user = parsed_message.user
            message_text = parsed_message.clean_text
            chat_id = parsed_message.chat_id
            
            logger.info(
                f"Processing message from {user.telegram_id} ({user.full_name}): "
                f"{message_text[:100]}..."
            )
            
            # Extract intent information
            intent_keywords = self.message_parser.extract_intent_keywords(message_text)
            logger.debug(f"Extracted intents: {intent_keywords}")
            
            # Store incoming message with parsed user information
            await self.store_message(
                telegram_id=user.telegram_id,
                sender="user",
                content=parsed_message.text,
                message_id=parsed_message.message_id,
                user_info=user
            )
            
            # Get conversation context
            conversation_context = await self.conversation_manager.get_conversation_context(
                telegram_id=user.telegram_id,
                limit=self.settings.max_conversation_context
            )
            
            # Process message with AI agent, including parsed information
            response = await self.ai_agent.process_message(
                message=message_text,
                telegram_id=user.telegram_id,
                conversation_context=conversation_context,
                parsed_message=parsed_message,
                intent_keywords=intent_keywords
            )
            
            # Send response back to user
            msg = format_info_message(response)
            await self.send_message(chat_id, msg["text"], parse_mode=msg["parse_mode"])
            
            # Store bot response
            await self.store_message(
                telegram_id=user.telegram_id,
                sender="assistant",
                content=response
            )
            
        except MessageParseError as e:
            logger.warning(f"Message parsing error: {e}")
            user_id = extract_user_id(update)
            if user_id:
                error_message = (
                    "I'm sorry, I had trouble understanding your message. "
                    "Please try rephrasing it or use /help for assistance."
                )
                msg = format_error_message(error_message)
                await self.send_message(update.effective_chat.id, msg["text"], parse_mode=msg["parse_mode"])
        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            error_message = (
                "I apologize, but I encountered an issue processing your message. "
                "Please try again in a moment, or use /help if you need assistance."
            )
            msg = format_error_message(error_message)
            await self.send_message(update.effective_chat.id, msg["text"], parse_mode=msg["parse_mode"])
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        user = query.from_user
        data = query.data
        
        logger.info(f"Callback query from {user.id}: {data}")
        
        # Acknowledge the callback query
        await query.answer()
        
        try:
            # Process callback based on data
            if data.startswith("schedule_"):
                await self.handle_schedule_callback(query, data)
            elif data.startswith("confirm_"):
                await self.handle_confirmation_callback(query, data)
            else:
                await query.edit_message_text("Unknown action. Please try again.")
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await query.edit_message_text(
                "Sorry, I couldn't process that action. Please try again."
            )
    
    async def handle_schedule_callback(self, query, data: str) -> None:
        """Handle scheduling-related callback queries."""
        # Implementation for scheduling callbacks
        # This will be expanded when integrating with calendar functionality
        await query.edit_message_text("Scheduling feature coming soon!")
    
    async def handle_confirmation_callback(self, query, data: str) -> None:
        """Handle confirmation-related callback queries."""
        # Implementation for confirmation callbacks
        await query.edit_message_text("Confirmation processed!")
    
    async def send_message(self, chat_id: int, text: str, max_retries: int = 2, **kwargs) -> Optional[int]:
        """
        Send a message to a specific chat with retry and improved error handling.
        Args:
            chat_id: Telegram chat ID
            text: Message text to send
            max_retries: Number of times to retry on transient errors
            **kwargs: Additional arguments for send_message
        Returns:
            Message ID if successful, None if failed
        """
        attempt = 0
        while attempt <= max_retries:
            try:
                message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    **kwargs
                )
                logger.info(f"Message sent to {chat_id}: {text[:50]}...")
                return message.message_id
            except TimedOut:
                logger.warning(f"Timeout sending message to {chat_id} (attempt {attempt+1}/{max_retries+1})")
            except NetworkError as e:
                logger.error(f"Network error sending message to {chat_id} (attempt {attempt+1}/{max_retries+1}): {e}")
            except TelegramError as e:
                logger.error(f"Telegram error sending message to {chat_id} (attempt {attempt+1}/{max_retries+1}): {e}")
                # TelegramError is often not transient, break
                break
            except Exception as e:
                logger.error(f"Unexpected error sending message to {chat_id}: {e}")
                break
            attempt += 1
            await asyncio.sleep(1)  # brief pause before retry
        # If we reach here, all attempts failed
        logger.error(f"Failed to deliver message to {chat_id} after {max_retries+1} attempts: {text[:100]}")
        # Optionally, notify user if possible (skip to avoid infinite loop)
        return None
    
    async def store_message(
        self, 
        telegram_id: str, 
        sender: str, 
        content: str,
        message_id: Optional[int] = None,
        user_info: Optional[Any] = None
    ) -> None:
        """
        Store a message in the database with enhanced user information.
        
        Args:
            telegram_id: Telegram user ID
            sender: Message sender ('user' or 'assistant')
            content: Message content
            message_id: Telegram message ID
            user_info: Parsed user information (ParsedUser object)
        """
        try:
            # Get or create contact with enhanced user information
            if user_info:
                contact = await self.db_client.get_or_create_contact_by_telegram_id(
                    telegram_id=telegram_id,
                    user_data={
                        'name': user_info.full_name,
                        'username': user_info.username,
                        'first_name': user_info.first_name,
                        'last_name': user_info.last_name,
                        'language_code': user_info.language_code
                    }
                )
            else:
                contact = await self.db_client.get_or_create_contact_by_telegram_id(telegram_id)
            
            # Store message with metadata
            metadata = {"telegram_message_id": message_id} if message_id else None
            
            await self.db_client.create_message(
                contact_id=contact['id'],
                sender=sender,
                channel="telegram",
                content=content,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
    
    async def set_webhook(self, webhook_url: str) -> bool:
        """
        Set the webhook URL for the bot.
        
        Args:
            webhook_url: The webhook URL to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = await self.bot.set_webhook(
                url=webhook_url,
                secret_token=self.settings.webhook_secret
            )
            
            if success:
                logger.info(f"Webhook set successfully: {webhook_url}")
            else:
                logger.error("Failed to set webhook")
                
            return success
            
        except TelegramError as e:
            logger.error(f"Error setting webhook: {e}")
            return False
    
    async def delete_webhook(self) -> bool:
        """
        Delete the current webhook.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            success = await self.bot.delete_webhook()
            
            if success:
                logger.info("Webhook deleted successfully")
            else:
                logger.error("Failed to delete webhook")
                
            return success
            
        except TelegramError as e:
            logger.error(f"Error deleting webhook: {e}")
            return False
    
    async def get_bot_info(self) -> Optional[Dict[str, Any]]:
        """
        Get bot information.
        
        Returns:
            Bot information dictionary or None if failed
        """
        try:
            bot_info = await self.bot.get_me()
            return {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "can_join_groups": bot_info.can_join_groups,
                "can_read_all_group_messages": bot_info.can_read_all_group_messages,
                "supports_inline_queries": bot_info.supports_inline_queries
            }
        except TelegramError as e:
            logger.error(f"Error getting bot info: {e}")
            return None
    
    async def start_polling(self) -> None:
        """Start the bot with polling (for development)."""
        if not self.application:
            await self.initialize()
        
        logger.info("Starting bot with polling...")
        await self.application.run_polling()
    
    async def shutdown(self) -> None:
        """Shutdown the bot gracefully."""
        if self.application:
            await self.application.shutdown()
            logger.info("Bot shutdown complete")


# Global bot instance
_bot_instance: Optional[AthenaTelegramBot] = None


def get_bot() -> AthenaTelegramBot:
    """Get the global bot instance."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = AthenaTelegramBot()
    return _bot_instance


async def main():
    """Main function for running the bot standalone."""
    bot = get_bot()
    await bot.initialize()
    
    # For development - use polling
    if get_settings().environment == "development":
        await bot.start_polling()
    else:
        logger.info("Bot initialized. Use webhook for production.")


if __name__ == "__main__":
    asyncio.run(main()) 