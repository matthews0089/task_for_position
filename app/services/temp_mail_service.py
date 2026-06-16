from typing import TYPE_CHECKING

from app.api.schemas import EmailContent, InboxEmail
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.automation.tempail_client import TempailClient

logger = get_logger(__name__)


class TempMailService:
    def __init__(self, client: "TempailClient") -> None:
        self._client = client

    async def get_current_email(self) -> str:
        email = await self._client.get_current_email()
        logger.info("current email fetched")
        return email

    async def get_inbox(self) -> list[InboxEmail]:
        emails = await self._client.get_inbox()
        if not emails:
            logger.warning("empty inbox")
        else:
            logger.info("inbox fetched", extra={"count": len(emails)})
        return emails

    async def get_email_content(self, email_id: str) -> EmailContent:
        email = await self._client.get_email_content(email_id)
        logger.info("email content fetched", extra={"email_id": email_id})
        return email

    async def refresh_email(self) -> str:
        email = await self._client.refresh_email()
        logger.info("email generated")
        return email
