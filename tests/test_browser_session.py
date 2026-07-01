import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from booking.browser_session import BrowserSession, AUTH_STATE_PATH


@pytest.mark.anyio
@patch("booking.browser_session.async_playwright")
@patch("booking.browser_session.Path.exists")
@patch("booking.browser_session.Path.read_text")
async def test_browser_session_flow_no_auth(mock_read_text, mock_exists, mock_async_playwright):
    # Setup mocks for Playwright browser context
    mock_exists.return_value = False
    
    mock_playwright = MagicMock()
    mock_async_playwright.return_value.start = AsyncMock(return_value=mock_playwright)
    
    mock_browser = MagicMock()
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    
    mock_temp_page = MagicMock()
    mock_temp_page.evaluate = AsyncMock(return_value="Mozilla/5.0 Playwright/1.40.0 Chrome/120.0.0")
    mock_temp_page.close = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_temp_page)
    
    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    
    mock_context = MagicMock()
    mock_context.set_default_timeout = MagicMock()
    mock_context.close = AsyncMock()
    mock_context.cookies = AsyncMock(return_value=[{"name": "test_cookie", "value": "val"}])
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()
    mock_playwright.stop = AsyncMock()

    with patch("booking.browser_session.Path.write_text") as mock_write_text, \
         patch("booking.browser_session.Path.mkdir") as mock_mkdir:
        
        async with BrowserSession() as page:
            assert page == mock_page
            mock_playwright.chromium.launch.assert_called_once_with(headless=False, slow_mo=1000)
            mock_browser.new_context.assert_called_once()
            
            # Verify user agent was cleaned
            kwargs = mock_browser.new_context.call_args[1]
            assert "Playwright" not in kwargs["user_agent"]
            assert kwargs["user_agent"] == "Mozilla/5.0 Chrome/120.0.0"
            assert kwargs["locale"] == "hu-HU"
            
            mock_page.goto.assert_called_once_with("https://jegy.mav.hu")
        
        # Verify save_auth_state was triggered during exit
        mock_write_text.assert_called_once()
        mock_context.cookies.assert_called_once()
