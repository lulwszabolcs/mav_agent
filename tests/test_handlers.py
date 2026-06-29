from telegram import Update
from telegram.ext import ContextTypes, Application
from telegram_bot.handlers import (
    start_handler,
    message_handler,
    error_handler,
    setup_handlers,
)
from telegram_bot.messages import MSG_UNAUTHORIZED, MSG_ERROR

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.anyio
@patch("telegram_bot.handlers.session_store.delete")
async def test_start_handler_success(mock_delete):
    update = MagicMock(spec=Update)
    update.effective_chat.id = 123456
    update.message = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    await start_handler(update, context)
    
    mock_delete.assert_called_once_with(123456)
    update.message.reply_text.assert_called_once()
    args, _ = update.message.reply_text.call_args
    assert "Üdvözöllek! MÁV jegyfoglaló asszisztens vagyok." in args[0]


@pytest.mark.anyio
@patch("telegram_bot.handlers.session_store.delete")
async def test_start_handler_unauthorized(mock_delete):
    mock_delete.side_effect = PermissionError("Access denied")
    
    update = MagicMock(spec=Update)
    update.effective_chat.id = 999999
    update.message = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    await start_handler(update, context)
    
    mock_delete.assert_called_once_with(999999)
    update.message.reply_text.assert_called_once_with(MSG_UNAUTHORIZED)


@pytest.mark.anyio
@patch("telegram_bot.handlers.session_store.delete")
async def test_start_handler_error(mock_delete):
    mock_delete.side_effect = Exception("DB connection error")
    
    update = MagicMock(spec=Update)
    update.effective_chat.id = 123456
    update.message = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    await start_handler(update, context)
    
    mock_delete.assert_called_once_with(123456)
    update.message.reply_text.assert_called_once_with(MSG_ERROR)


@pytest.mark.anyio
@patch("telegram_bot.handlers.handle_message")
async def test_message_handler_success(mock_handle_message):
    mock_handle_message.return_value = "Response text"
    
    update = MagicMock(spec=Update)
    update.effective_chat.id = 123456
    update.message = AsyncMock()
    update.message.text = "Hello bot"
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    await message_handler(update, context)
    
    mock_handle_message.assert_called_once_with(123456, "Hello bot")
    update.message.reply_text.assert_called_once_with("Response text")


@pytest.mark.anyio
@patch("telegram_bot.handlers.handle_message")
async def test_message_handler_permission_error(mock_handle_message):
    mock_handle_message.side_effect = PermissionError("Access denied")
    
    update = MagicMock(spec=Update)
    update.effective_chat.id = 123456
    update.message = AsyncMock()
    update.message.text = "Hello bot"
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    await message_handler(update, context)
    
    mock_handle_message.assert_called_once_with(123456, "Hello bot")
    update.message.reply_text.assert_called_once_with(MSG_UNAUTHORIZED)


@pytest.mark.anyio
@patch("telegram_bot.handlers.handle_message")
async def test_message_handler_generic_error(mock_handle_message):
    mock_handle_message.side_effect = Exception("DB Connection lost")
    
    update = MagicMock(spec=Update)
    update.effective_chat.id = 123456
    update.message = AsyncMock()
    update.message.text = "Hello bot"
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    await message_handler(update, context)
    
    mock_handle_message.assert_called_once_with(123456, "Hello bot")
    update.message.reply_text.assert_called_once_with(MSG_ERROR)


@pytest.mark.anyio
async def test_error_handler():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.error = Exception("API timeout")
    
    # Just verify it does not raise exceptions
    await error_handler(object(), context)


def test_setup_handlers():
    app = MagicMock(spec=Application)
    
    setup_handlers(app)
    
    assert app.add_handler.call_count == 2
    app.add_error_handler.assert_called_once_with(error_handler)
