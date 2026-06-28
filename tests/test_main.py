import pytest
from unittest.mock import patch, MagicMock
import os
import main


@pytest.fixture(autouse=True)
def clean_env():
    """
    Saves and restores environment variables during tests.
    """
    old_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture(autouse=True)
def mock_load_dotenv():
    """
    Mocks load_dotenv to prevent loading the actual .env file during unit testing.
    """
    with patch("main.load_dotenv") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_app_builder():
    """
    Mocks ApplicationBuilder globally to prevent tests from hitting Telegram servers.
    """
    with patch("main.ApplicationBuilder") as mock_class:
        mock_builder = MagicMock()
        mock_app = MagicMock()
        mock_builder.token.return_value = mock_builder
        mock_builder.build.return_value = mock_app
        mock_class.return_value = mock_builder
        yield mock_class, mock_builder, mock_app


def test_main_missing_token():
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    os.environ["XAI_API_KEY"] = "test-key"
    os.environ["ALLOWED_CHAT_IDS"] = "123"
    
    with pytest.raises(ValueError) as exc_info:
        main.main()
    assert "TELEGRAM_BOT_TOKEN" in str(exc_info.value)


def test_main_missing_api_key():
    os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
    os.environ.pop("XAI_API_KEY", None)
    os.environ["ALLOWED_CHAT_IDS"] = "123"
    
    with pytest.raises(ValueError) as exc_info:
        main.main()
    assert "XAI_API_KEY" in str(exc_info.value)


def test_main_missing_chat_ids():
    os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
    os.environ["XAI_API_KEY"] = "test-key"
    os.environ.pop("ALLOWED_CHAT_IDS", None)
    
    with pytest.raises(ValueError) as exc_info:
        main.main()
    assert "ALLOWED_CHAT_IDS" in str(exc_info.value)


def test_main_invalid_dry_run():
    os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
    os.environ["XAI_API_KEY"] = "test-key"
    os.environ["ALLOWED_CHAT_IDS"] = "123"
    os.environ["DRY_RUN"] = "invalid"
    
    with pytest.raises(ValueError) as exc_info:
        main.main()
    assert "DRY_RUN" in str(exc_info.value)


@patch("main.setup_handlers")
def test_main_success(mock_setup, mock_app_builder):
    _, mock_builder, mock_app = mock_app_builder
    os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
    os.environ["XAI_API_KEY"] = "test-key"
    os.environ["ALLOWED_CHAT_IDS"] = "123"
    os.environ["DRY_RUN"] = "false"
    
    main.main()
    
    mock_builder.token.assert_called_once_with("test-token")
    mock_builder.build.assert_called_once()
    mock_setup.assert_called_once_with(mock_app)
    mock_app.run_polling.assert_called_once()
