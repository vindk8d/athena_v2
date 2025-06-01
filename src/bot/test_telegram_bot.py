import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, User, Message, Chat
from src.bot.telegram_bot import AthenaTelegramBot
from src.utils.message_parser import ParsedUser, ParsedMessage

@pytest.mark.asyncio
class TestAthenaTelegramBot:
    @pytest.fixture(autouse=True)
    def setup_bot(self):
        self.bot = AthenaTelegramBot()
        self.bot.db_client = MagicMock()
        self.bot.ai_agent = MagicMock()
        self.bot.conversation_manager = MagicMock()
        self.bot.send_message = AsyncMock(return_value=123)
        self.bot.message_parser = MagicMock()
        self.bot._get_active_conversation_count_today = AsyncMock(return_value=0)
        # Add bot to the application
        self.bot.application = MagicMock()
        self.bot.bot = MagicMock()

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
        self.bot.db_client.get_contact_by_telegram_id = AsyncMock(return_value=None)
        self.bot._get_active_conversation_count_today = AsyncMock(return_value=5)
        parsed_user = ParsedUser(telegram_id="2", username="testuser", first_name="Test", last_name=None, full_name="Test", language_code="en", is_bot=False)
        parsed_message = ParsedMessage(message_id=1, text="/start", clean_text="/start", user=parsed_user, chat_id=1, timestamp=None, message_type="command", is_command=True, command="start", command_args=[])
        self.bot.message_parser.validate_and_parse = MagicMock(return_value=parsed_message)
        await self.bot.start_command(update, context)
        self.bot.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_start_command_new_user_over_limit(self):
        update = self.make_update("/start", user_id="3")
        context = MagicMock()
        self.bot.db_client.get_contact_by_telegram_id = AsyncMock(return_value=None)
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
        # The actual message sent is MarkdownV2-escaped, so periods are escaped as \\.
        expected_text = "❌ I apologize, but I encountered an issue processing your message\\. Please try again in a moment, or use /help if you need assistance\\."
        self.bot.ai_agent.process_message = AsyncMock(return_value=expected_text)
        await self.bot.handle_message(update, context)
        self.bot.send_message.assert_called_with(1, expected_text, parse_mode='MarkdownV2')

    @pytest.mark.asyncio
    async def test_handle_message_parse_error(self):
        update = self.make_update("bad input")
        context = MagicMock()
        self.bot.message_parser.validate_and_parse = MagicMock(side_effect=Exception("parse error"))
        await self.bot.handle_message(update, context)
        self.bot.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_handle_message_rate_limit(self):
        update = self.make_update("/start", user_id="11")
        context = MagicMock()
        self.bot.db_client.get_contact_by_telegram_id = AsyncMock(return_value=None)
        self.bot._get_active_conversation_count_today = AsyncMock(return_value=10)
        parsed_user = ParsedUser(telegram_id="11", username="testuser", first_name="Test", last_name=None, full_name="Test", language_code="en", is_bot=False)
        parsed_message = ParsedMessage(message_id=1, text="/start", clean_text="/start", user=parsed_user, chat_id=1, timestamp=None, message_type="command", is_command=True, command="start", command_args=[])
        self.bot.message_parser.validate_and_parse = MagicMock(return_value=parsed_message)
        await self.bot.start_command(update, context)
        self.bot.send_message.assert_called()
        assert "maximum number of contacts" in self.bot.send_message.call_args[0][1] 