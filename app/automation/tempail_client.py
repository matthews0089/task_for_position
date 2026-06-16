import asyncio
import hashlib
import re
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from playwright.async_api import Error as PlaywrightError, Locator, Page

from app.api.schemas import EmailContent, InboxEmail
from app.automation import selectors
from app.automation.browser import BrowserManager
from app.core.config import Settings
from app.core.exceptions import (
    ElementNotFoundError,
    EmailNotFoundError,
    TempMailError,
)
from app.core.logging import get_logger
from app.utils.retry import retry_async

logger = get_logger(__name__)
T = TypeVar("T")


class TempailClient:
    def __init__(self, browser_manager: BrowserManager, settings: Settings) -> None:
        self._browser_manager = browser_manager
        self._settings = settings
        self._lock = asyncio.Lock()

    async def get_current_email(self) -> str:
        return await self.with_retry(self.fetch_current_email)

    async def get_inbox(self) -> list[InboxEmail]:
        return await self.with_retry(self.fetch_inbox)

    async def get_email_content(self, email_id: str) -> EmailContent:
        return await self.with_retry(lambda: self.fetch_email_content(email_id))

    async def refresh_email(self) -> str:
        return await self.with_retry(self.fetch_refreshed_email)

    async def with_retry(self, operation: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            return await retry_async(
                operation,
                attempts=self._settings.retry_attempts,
                delay_seconds=self._settings.retry_delay_seconds,
                recover=self._browser_manager.recreate,
            )

    async def ensure_page(self) -> Page:
        page = await self._browser_manager.safe_goto(str(self._settings.tempail_url))
        await page.wait_for_load_state(
            "networkidle",
            timeout=self._settings.page_load_timeout,
        )
        await self.raise_for_bot_challenge(page)
        return page

    async def fetch_current_email(self) -> str:
        page = await self.ensure_page()
        await self.wait_for_email_presence(page)
        email = await self.extract_email_from_page()
        logger.info("current email extracted")
        return email

    async def fetch_inbox(self) -> list[InboxEmail]:
        page = await self.ensure_page()

        for text in selectors.EMPTY_INBOX_TEXTS:
            if await page.get_by_text(re.compile(text, re.IGNORECASE)).count() > 0:
                return []

        rows: list[Locator] = []
        for selector in selectors.INBOX_ROW_SELECTORS:
            locator = page.locator(selector)
            count = await locator.count()
            if count > 0:
                rows = [locator.nth(index) for index in range(count)]
                break

        if not rows:
            return []

        emails: list[InboxEmail] = []
        for index, row in enumerate(rows):
            raw_text = (await row.inner_text()).strip()
            if not raw_text or any(
                text in raw_text.lower() for text in selectors.EMPTY_INBOX_TEXTS
            ):
                continue

            parts = [part.strip() for part in raw_text.splitlines() if part.strip()]
            sender = parts[0] if len(parts) > 0 else ""
            subject = parts[1] if len(parts) > 1 else raw_text
            time = parts[2] if len(parts) > 2 else ""
            row_id = await row.get_attribute("data-email-id") or await row.get_attribute(
                "data-id"
            )
            email_id = row_id or self.stable_id(f"{index}:{raw_text}")
            emails.append(
                InboxEmail(id=email_id, sender=sender, subject=subject, time=time)
            )

        return emails

    async def fetch_email_content(self, email_id: str) -> EmailContent:
        page = await self.ensure_page()
        row = await self.find_email_row(email_id)
        if not row:
            raise EmailNotFoundError(f"Email with id '{email_id}' was not found")

        raw_row_text = (await row.inner_text()).strip()
        row_parts = [part.strip() for part in raw_row_text.splitlines() if part.strip()]
        await row.click()
        await page.wait_for_load_state(
            "networkidle",
            timeout=self._settings.page_load_timeout,
        )

        body = await self.extract_email_body()
        sender = row_parts[0] if len(row_parts) > 0 else ""
        subject = row_parts[1] if len(row_parts) > 1 else ""
        timestamp = row_parts[2] if len(row_parts) > 2 else ""

        return EmailContent(
            id=email_id,
            sender=sender,
            subject=subject,
            timestamp=timestamp,
            body=body,
        )

    async def fetch_refreshed_email(self) -> str:
        page = await self.ensure_page()
        refresh_button = await self.first_visible_locator(selectors.REFRESH_SELECTORS)
        if not refresh_button:
            raise ElementNotFoundError("Refresh control was not found on tempail page")

        previous_email = await self.extract_email_from_page(required=False)
        await refresh_button.click()
        await page.wait_for_timeout(750)
        email = await self.wait_for_email_change(previous_email)
        if previous_email and email == previous_email:
            logger.warning(
                "email value did not change after refresh control; recreating session"
            )
            await self._browser_manager.recreate()
            email = await self.fetch_current_email()
        logger.info("email refreshed")
        return email

    async def find_email_row(self, email_id: str) -> Locator | None:
        inbox = await self.fetch_inbox()
        expected = {item.id for item in inbox}
        if email_id not in expected:
            return None

        page = await self._browser_manager.get_page()
        for selector in selectors.INBOX_ROW_SELECTORS:
            locator = page.locator(selector)
            count = await locator.count()
            for index in range(count):
                row = locator.nth(index)
                raw_text = (await row.inner_text()).strip()
                row_id = await row.get_attribute(
                    "data-email-id"
                ) or await row.get_attribute("data-id")
                candidate_id = row_id or self.stable_id(f"{index}:{raw_text}")
                if candidate_id == email_id:
                    return row
        return None

    async def extract_email_from_page(self, *, required: bool = True) -> str:
        page = await self._browser_manager.get_page()

        for selector in selectors.EMAIL_SELECTORS:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            value = (
                await locator.get_attribute("value")
                or await locator.get_attribute("data-email")
                or await locator.inner_text()
            )
            email = self.find_email(value or "")
            if email:
                return email

        body_text = await page.locator("body").inner_text(
            timeout=self._settings.action_timeout
        )
        email = self.find_email(body_text)
        if email:
            return email

        if required:
            raise ElementNotFoundError("Temporary email address was not found on tempail page")
        return ""

    async def wait_for_email_presence(self, page: Page) -> None:
        try:
            await page.wait_for_function(
                r"""() => {
                    const input = document.querySelector(
                        '#eposta_adres, #email, input[type="email"]',
                    );
                    const text = `${input?.value || ''} ${document.body?.innerText || ''}`;
                    return /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/.test(text);
                }""",
                timeout=self._settings.action_timeout,
            )
        except PlaywrightError as exc:
            raise ElementNotFoundError(
                "Temporary email address was not found on tempail page"
            ) from exc

    async def raise_for_bot_challenge(self, page: Page) -> None:
        body_text = (
            await page.locator("body").inner_text(timeout=self._settings.action_timeout)
        ).lower()
        if "not a robot" in body_text or "verify that you are not a robot" in body_text:
            raise TempMailError(
                "Tempail requires bot verification; temporary mail is currently unavailable",
                code="TEMP_MAIL_UNAVAILABLE",
                status_code=503,
            )

    async def extract_email_body(self) -> str:
        for selector in selectors.EMAIL_BODY_SELECTORS:
            locator = await self.first_visible_locator((selector,))
            if not locator:
                continue
            if selector == "iframe":
                frame = await locator.element_handle()
                content_frame = await frame.content_frame() if frame else None
                if content_frame:
                    text = (await content_frame.locator("body").inner_text()).strip()
                    if text:
                        return text
            else:
                text = (await locator.inner_text()).strip()
                if text:
                    return text

        page = await self._browser_manager.get_page()
        text = (await page.locator("body").inner_text()).strip()
        if not text:
            raise ElementNotFoundError("Email body was not found")
        return text

    async def wait_for_email_change(self, previous_email: str) -> str:
        deadline = time.monotonic() + (self._settings.action_timeout / 1000)
        last_email = ""

        while time.monotonic() < deadline:
            last_email = await self.extract_email_from_page(required=False)
            if last_email and last_email != previous_email:
                return last_email
            await asyncio.sleep(0.5)

        return last_email or previous_email

    async def first_visible_locator(self, selector_group: tuple[str, ...]) -> Locator | None:
        page = await self._browser_manager.get_page()
        for selector in selector_group:
            locator = page.locator(selector).first
            try:
                if await locator.count() > 0 and await locator.is_visible(timeout=1_000):
                    return locator
            except PlaywrightError:
                continue
        return None

    @staticmethod
    def find_email(text: str) -> str | None:
        match = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text,
        )
        return match.group(0) if match else None

    @staticmethod
    def stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
