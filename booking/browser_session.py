import os
import json
import re
import logging
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

# Load environment variables
load_dotenv()

# Named logger
logger = logging.getLogger("browser_session")

# Configuration constants
AUTH_STATE_PATH = Path("data/auth_state.json")
DEFAULT_TIMEOUT = 15000   # 15 seconds in milliseconds
VIEWPORT = {"width": 1280, "height": 800}
MAV_URL = os.getenv("MAV_URL", "https://jegy.mav.hu")


class BrowserSession:
    """
    Manages the Playwright browser lifecycle, handles auth state, and provides
    access to the page object for booking automation.
    """

    def __init__(self) -> None:
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self) -> Page:
        # Determine headless and slow_mo modes
        headless_env = os.getenv("HEADLESS", "false").lower()
        if headless_env == "true":
            headless = True
            slow_mo = 0
        else:
            headless = False
            slow_mo = 1000

        logger.info(f"browser_session | böngésző indítása | headless={headless}")

        # Start Playwright and browser
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            slow_mo=slow_mo
        )

        # Get default user agent by temporarily opening a page
        temp_page = await self.browser.new_page()
        raw_user_agent = await temp_page.evaluate("navigator.userAgent")
        await temp_page.close()

        # Clean the user agent string by removing 'Playwright' and its version
        cleaned_user_agent = re.sub(r'Playwright/\S+', '', raw_user_agent)
        cleaned_user_agent = " ".join(cleaned_user_agent.split())

        # Create browser context with configurations
        self.context = await self.browser.new_context(
            viewport=VIEWPORT,
            user_agent=cleaned_user_agent,
            locale="hu-HU"
        )
        self.context.set_default_timeout(DEFAULT_TIMEOUT)

        # Load auth state if it exists
        await self.load_auth_state(self.context)

        # Navigate to the target page
        self.page = await self.context.new_page()
        logger.info(f"browser_session | navigáció | url={MAV_URL}")
        await self.page.goto(MAV_URL)

        return self.page

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        logger.info("browser_session | böngésző leállítása")
        try:
            if self.context:
                await self.save_auth_state(self.context)
        except Exception as e:
            logger.error(f"Error saving auth state: {e}")
        finally:
            # Safely close resources even if exceptions occurred during execution or saving
            try:
                if self.context:
                    await self.context.close()
            except Exception:
                pass
            try:
                if self.browser:
                    await self.browser.close()
            except Exception:
                pass
            try:
                if self.playwright:
                    await self.playwright.stop()
            except Exception:
                pass

    async def load_auth_state(self, context: BrowserContext) -> None:
        """
        Loads saved session cookies into the browser context if the file exists.
        """
        if AUTH_STATE_PATH.exists():
            try:
                cookies = json.loads(AUTH_STATE_PATH.read_text(encoding="utf-8"))
                await context.add_cookies(cookies)
                logger.info("browser_session | auth state betöltve")
            except Exception as e:
                logger.error(f"Error loading auth state file: {e}")
        else:
            logger.info("browser_session | nincs mentett auth state")

    async def save_auth_state(self, context: BrowserContext) -> None:
        """
        Saves session cookies from the browser context to a JSON file.
        """
        try:
            cookies = await context.cookies()
            AUTH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            AUTH_STATE_PATH.write_text(
                json.dumps(cookies, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            logger.info("browser_session | auth state mentve")
        except Exception as e:
            logger.error(f"Failed to save auth state: {e}")
