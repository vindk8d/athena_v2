import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, UTC
import types

# Import modules directly since global mocking is in place
from telegram import Update, User, Message, Chat
from src.bot.telegram_bot import AthenaTelegramBot
from src.utils.message_parser import ParsedUser, ParsedMessage
from src.database.supabase_client import SupabaseClient

@pytest.fixture
def mock_supabase_client():
    """Create a mock SupabaseClient."""
    mock = MagicMock()
    mock.get_contact_by_telegram_id = AsyncMock(return_value=None)
    mock.get_or_create_contact_by_telegram_id = AsyncMock(return_value={
        "id": "123",
        "telegram_id": "456",
        "name": "Test User",
        "full_name": "Test User"
    })
    mock.create_message = AsyncMock(return_value={
        "id": "789",
        "contact_id": "123",
        "sender": "user",
        "channel": "telegram",
        "content": "Hello",
        "status": "delivered",
        "created_at": datetime.now(UTC).isoformat()
    })
    return mock

@pytest.mark.asyncio
class TestAthenaTelegramBot:
    @pytest.fixture(autouse=True)
    def setup_bot(self, mock_supabase_client):
        with patch('src.bot.telegram_bot.SupabaseClient', return_value=mock_supabase_client), \
             patch('src.agent.athena_agent.AthenaAgent', MagicMock()):
            self.bot = AthenaTelegramBot()
            self.bot.db_client = mock_supabase_client
            self.bot.ai_agent = AsyncMock()
            self.bot.conversation_manager = AsyncMock()
            self.bot.send_message = AsyncMock(return_value=123)
            self.bot.message_parser = MagicMock()
            self.bot._get_active_conversation_count_today = AsyncMock(return_value=0)
            # Add bot to the application
            self.bot.application = MagicMock()
            self.bot.bot = MagicMock()
            self.bot.supabase = mock_supabase_client

    def make_update(self, text, user_id="1", username="testuser", is_bot=False):
        user = User(id=int(user_id), first_name="Test", is_bot=is_bot, username=username)
        chat = Chat(id=1, type="private")
        message = Message(message_id=1, date=None, chat=chat, text=text, from_user=user)
        message._bot = self.bot.bot  # Associate bot with message
        update = Update(update_id=1, message=message)
        return update

    @pytest.mark.asyncio
    async def test_start_command_new_user_under_limit(self):
        update = self.make_update("/start", user_id="2")
        context = MagicMock()
        parsed_user = ParsedUser(telegram_id="2", username="testuser", first_name="Test", last_name=None, full_name="Test", language_code="en", is_bot=False)
        parsed_message = ParsedMessage(message_id=1, text="/start", clean_text="/start", user=parsed_user, chat_id=1, timestamp=None, message_type="command", is_command=True, command="start", command_args=[])
        self.bot.message_parser.validate_and_parse = MagicMock(return_value=parsed_message)
        await self.bot.start_command(update, context)
        self.bot.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_start_command_new_user_over_limit(self):
        update = self.make_update("/start", user_id="3")
        context = MagicMock()
        self.bot._get_active_conversation_count_today = AsyncMock(return_value=10)
        parsed_user = ParsedUser(telegram_id="3", username="testuser", first_name="Test", last_name=None, full_name="Test", language_code="en", is_bot=False)
        parsed_message = ParsedMessage(message_id=1, text="/start", clean_text="/start", user=parsed_user, chat_id=1, timestamp=None, message_type="command", is_command=True, command="start", command_args=[])
        self.bot.message_parser.validate_and_parse = MagicMock(return_value=parsed_message)
        await self.bot.start_command(update, context)
        self.bot.send_message.assert_called()
        assert "maximum number of contacts" in self.bot.send_message.call_args[0][1]

    @pytest.mark.asyncio
    @patch("telegram.Message.reply_text", new_callable=AsyncMock)
    async def test_help_command(self, mock_reply_text):
        update = self.make_update("/help")
        context = MagicMock()
        parsed_user = ParsedUser(telegram_id="1", username="testuser", first_name="Test", last_name=None, full_name="Test", language_code="en", is_bot=False)
        parsed_message = ParsedMessage(message_id=1, text="/help", clean_text="/help", user=parsed_user, chat_id=1, timestamp=None, message_type="command", is_command=True, command="help", command_args=[])
        self.bot.message_parser.validate_and_parse = MagicMock(return_value=parsed_message)
        await self.bot.help_command(update, context)
        mock_reply_text.assert_called()

    @pytest.mark.asyncio
    @patch("telegram.Message.reply_text", new_callable=AsyncMock)
    async def test_cancel_command(self, mock_reply_text):
        update = self.make_update("/cancel")
        context = MagicMock()
        parsed_user = ParsedUser(telegram_id="1", username="testuser", first_name="Test", last_name=None, full_name="Test", language_code="en", is_bot=False)
        parsed_message = ParsedMessage(message_id=1, text="/cancel", clean_text="/cancel", user=parsed_user, chat_id=1, timestamp=None, message_type="command", is_command=True, command="cancel", command_args=[])
        self.bot.message_parser.validate_and_parse = MagicMock(return_value=parsed_message)
        await self.bot.cancel_command(update, context)
        mock_reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_handle_message_normal(self):
        update = self.make_update("Hello Athena")
        context = MagicMock()
        parsed_user = ParsedUser(telegram_id="1", username="testuser", first_name="Test", last_name=None, full_name="Test", language_code="en", is_bot=False)
        parsed_message = ParsedMessage(message_id=1, text="Hello Athena", clean_text="Hello Athena", user=parsed_user, chat_id=1, timestamp=None, message_type="text", is_command=False, command=None, command_args=[])
        self.bot.message_parser.validate_and_parse = MagicMock(return_value=parsed_message)
        self.bot.ai_agent.process_message = AsyncMock(return_value="Hi there\\\\!")
        await self.bot.handle_message(update, context)
        self.bot.send_message.assert_called_with(1, "Hi there\\\\\\!", parse_mode='MarkdownV2')

    @pytest.mark.asyncio
    async def test_handle_message_parse_error(self):
        update = self.make_update("bad input")
        context = MagicMock()
        self.bot.message_parser.validate_and_parse = MagicMock(side_effect=Exception("parse error"))
        await self.bot.handle_message(update, context)
        expected_text = "❌ Oops\\! 😅 I hit a small bump in the road while processing your message\\. I'm still here to help though\\! Could you try sending your message again? If you need any assistance, just type /help and I'll guide you through it\\! 💪"
        self.bot.send_message.assert_called_with(1, expected_text, parse_mode='MarkdownV2')

    @pytest.mark.asyncio
    async def test_handle_message_rate_limit(self):
        update = self.make_update("/start", user_id="11")
        context = MagicMock()
        self.bot._get_active_conversation_count_today = AsyncMock(return_value=10)
        parsed_user = ParsedUser(telegram_id="11", username="testuser", first_name="Test", last_name=None, full_name="Test", language_code="en", is_bot=False)
        parsed_message = ParsedMessage(message_id=1, text="/start", clean_text="/start", user=parsed_user, chat_id=1, timestamp=None, message_type="command", is_command=True, command="start", command_args=[])
        self.bot.message_parser.validate_and_parse = MagicMock(return_value=parsed_message)
        await self.bot.start_command(update, context)
        self.bot.send_message.assert_called()
        assert "maximum number of contacts" in self.bot.send_message.call_args[0][1]

@pytest.fixture
def telegram_bot(mock_supabase_client):
    """Create an AthenaTelegramBot instance with mocked dependencies."""
    with patch('src.bot.telegram_bot.SupabaseClient', return_value=mock_supabase_client), \
         patch('src.agent.athena_agent.AthenaAgent', MagicMock()), \
         patch('src.bot.telegram_bot.get_settings', return_value=MagicMock(
             telegram_bot_token="test_token",
             max_contacts=10
         )):
        bot = AthenaTelegramBot()
        bot.db_client = mock_supabase_client
        
        # Mock message parser
        bot.message_parser = MagicMock()
        bot.message_parser.parse_message = MagicMock(return_value=ParsedMessage(
            user=ParsedUser(
                telegram_id="456",
                username="testuser",
                first_name="Test",
                last_name="User",
                full_name="Test User",
                language_code="en",
                is_bot=False
            ),
            text="Hello",
            clean_text="Hello",
            message_id=123,
            chat_id=1,
            timestamp=datetime.now(UTC),
            message_type="text",
            is_command=False,
            command=None,
            command_args=[]
        ))
        
        return bot

@pytest.mark.asyncio
async def test_store_message_success(telegram_bot):
    """Test successful message storage."""
    result = await telegram_bot.store_message(
        telegram_id="456",
        sender="user",
        content="Hello",
        message_id=123
    )

    # Verify the result
    assert result["id"] == "789"
    assert result["sender"] == "user"
    assert result["status"] == "delivered"

    # Verify the calls
    telegram_bot.db_client.get_or_create_contact_by_telegram_id.assert_called_once_with("456")
    telegram_bot.db_client.create_message.assert_called_once_with(
        contact_id="123",
        sender="user",
        channel="telegram",
        content="Hello",
        metadata={"telegram_message_id": 123},
        status="delivered"
    )

@pytest.mark.asyncio
async def test_store_message_with_user_info(telegram_bot):
    """Test message storage with user info."""
    user_info = types.SimpleNamespace(
        first_name="Test",
        last_name="User",
        username="testuser",
        full_name="Test User",
        language_code="en"
    )
    result = await telegram_bot.store_message(
        telegram_id="456",
        sender="user",
        content="Hello",
        message_id=123,
        user_info=user_info
    )

    # Verify the calls
    telegram_bot.db_client.get_or_create_contact_by_telegram_id.assert_called_once_with(
        telegram_id="456",
        user_data={
            'name': user_info.full_name,
            'username': user_info.username,
            'first_name': user_info.first_name,
            'last_name': user_info.last_name,
            'language_code': user_info.language_code
        }
    )

@pytest.mark.asyncio
async def test_store_message_contact_creation_error(telegram_bot):
    """Test handling of contact creation errors."""
    telegram_bot.db_client.get_or_create_contact_by_telegram_id = AsyncMock(
        side_effect=Exception("Contact creation failed")
    )

    with pytest.raises(Exception, match="Contact creation failed"):
        await telegram_bot.store_message(
            telegram_id="456",
            sender="user",
            content="Hello",
            message_id=123
        )

@pytest.mark.asyncio
async def test_store_message_message_creation_error(telegram_bot):
    """Test handling of message creation errors."""
    telegram_bot.db_client.create_message = AsyncMock(
        side_effect=Exception("Message creation failed")
    )

    with pytest.raises(Exception, match="Message creation failed"):
        await telegram_bot.store_message(
            telegram_id="456",
            sender="user",
            content="Hello",
            message_id=123
        )

@pytest.mark.asyncio
async def test_store_message_sender_validation(telegram_bot):
    """Test sender validation in message storage."""
    # Test with different sender values
    for sender in ["user", "assistant", "USER", "ASSISTANT", "  user  ", "  assistant  "]:
        result = await telegram_bot.store_message(
            telegram_id="456",
            sender=sender,
            content="Hello",
            message_id=123
        )
        assert result["sender"] in ["user", "assistant"]

    # Test with invalid sender
    telegram_bot.db_client.create_message = AsyncMock(side_effect=ValueError("Invalid sender value"))
    with pytest.raises(ValueError, match="Invalid sender value"):
        await telegram_bot.store_message(
            telegram_id="456",
            sender="invalid_sender",
            content="Hello",
            message_id=123
        ) 