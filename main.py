import os
import logging

# Set up global logging configuration at the very beginning
if not os.path.exists("logs"):
    os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log", encoding="utf-8")
    ]
)

# Package imports
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder
from telegram_bot.handlers import setup_handlers

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Main entry point for starting the Telegram bot application.
    """
    # 1. Load env file
    load_dotenv()

    # 2. Check and validate environment variables
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    xai_api_key = os.getenv("XAI_API_KEY")
    allowed_chat_ids = os.getenv("ALLOWED_CHAT_IDS")
    dry_run = os.getenv("DRY_RUN", "true")

    if not telegram_bot_token:
        raise ValueError("A TELEGRAM_BOT_TOKEN környezeti változó hiányzik!")
    if not xai_api_key:
        raise ValueError("A XAI_API_KEY környezeti változó hiányzik!")
    if not allowed_chat_ids:
        raise ValueError("A ALLOWED_CHAT_IDS környezeti változó hiányzik!")
    if dry_run not in ("true", "false"):
        raise ValueError("A DRY_RUN értéke csak 'true' vagy 'false' lehet!")

    # 3. Log start mode
    logger.info(f"main | dry_run={dry_run} módban indul az alkalmazás")

    # 4. Build application
    application = ApplicationBuilder().token(telegram_bot_token).build()

    # 5. Register handlers
    setup_handlers(application)

    # 6. Log readiness
    logger.info("main | Telegram bot elindult, várom az üzeneteket...")

    # 7. Start polling
    application.run_polling()


if __name__ == "__main__":
    main()
