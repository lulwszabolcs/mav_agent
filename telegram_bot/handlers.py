import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import orchestrator.session_store as session_store
from orchestrator.state_machine import handle_message
from telegram_bot.messages import MSG_UNAUTHORIZED, MSG_ERROR

# Set up logging
logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /start command.
    """
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id

    try:
        # Reset the session for the chat if it exists.
        # This will also raise a PermissionError if the chat_id is not in ALLOWED_CHAT_IDS.
        session_store.delete(chat_id)
    except PermissionError:
        logger.warning(f"handlers | jogosulatlan hozzáférés /start paranccsal | chat_id={chat_id}")
        await update.message.reply_text(MSG_UNAUTHORIZED)
        return
    except Exception as e:
        logger.error(f"handlers | hiba a session törlésekor a /start parancsnál | chat_id={chat_id}: {e}", exc_info=True)
        await update.message.reply_text(MSG_ERROR)
        return

    text = (
        "Üdvözöllek! MÁV jegyfoglaló asszisztens vagyok.\n\n"
        "Írd le, milyen jegyet szeretnél, és én megveszem helyetted.\n"
        "Minden lépésnél megerősítést fogok kérni, mielőtt bármit csinálok.\n\n"
        'Példa: "Budapest Keletiből Pécsre holnap délután, 1 felnőtt, ablak mellé"'
    )
    await update.message.reply_text(text)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles standard text messages.
    """
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user_message = update.message.text

    logger.info(f"handlers | üzenet érkezett | chat_id={chat_id}")

    try:
        response = handle_message(chat_id, user_message)
    except PermissionError:
        logger.warning(f"handlers | jogosulatlan hozzáférés | chat_id={chat_id}")
        await update.message.reply_text(MSG_UNAUTHORIZED)
        return
    except Exception:
        logger.error(f"handlers | hiba történt | chat_id={chat_id}", exc_info=True)
        await update.message.reply_text(MSG_ERROR)
        return

    await update.message.reply_text(response)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global error handler for Telegram API errors.
    """
    logger.error(f"handlers | telegram hiba | {context.error}")


def setup_handlers(application: Application) -> None:
    """
    Registers the command, message, and error handlers with the application.
    """
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_error_handler(error_handler)
