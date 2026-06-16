from playwright.async_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    async_playwright,
)

from app.core.config import Settings
from app.core.exceptions import BrowserUnavailableError, TempMailTimeoutError
from app.core.logging import get_logger

logger = get_logger(__name__)


class BrowserManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def start(self) -> None:
        if self._browser and self._browser.is_connected():
            return

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._settings.browser_headless
            )
            self._context = await self._browser.new_context(locale="uk-UA")
            self._context.set_default_timeout(self._settings.action_timeout)
            self._context.set_default_navigation_timeout(self._settings.page_load_timeout)
            self._page = await self._context.new_page()
            logger.info("browser started")
        except PlaywrightError as exc:
            logger.error("browser failed to start", extra={"error": str(exc)})
            await self.stop()
            raise BrowserUnavailableError("Unable to start browser session") from exc

    async def stop(self) -> None:
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except PlaywrightError as exc:
            logger.warning("browser shutdown issue", extra={"error": str(exc)})
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None

    async def get_page(self) -> Page:
        if not self._browser or not self._browser.is_connected() or not self._context:
            logger.warning("browser session is stale; recreating")
            await self.recreate()

        if not self._page or self._page.is_closed():
            if not self._context:
                raise BrowserUnavailableError()
            self._page = await self._context.new_page()

        return self._page

    async def recreate(self) -> None:
        logger.warning("recreating browser session")
        await self.stop()
        await self.start()

    async def safe_goto(self, url: str) -> Page:
        page = await self.get_page()
        try:
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self._settings.page_load_timeout,
            )
            return page
        except PlaywrightError as exc:
            if "Timeout" in str(exc):
                raise TempMailTimeoutError("Temporary mail page load timed out") from exc
            raise BrowserUnavailableError("Unable to load temporary mail page") from exc
