from typing import Protocol

from fastapi import Request

from app.services.temp_mail_service import TempMailService


class TempMailServiceProvider(Protocol):
    async def get_current_email(self) -> str:
        ...

    async def get_inbox(self):
        ...

    async def get_email_content(self, email_id: str):
        ...

    async def refresh_email(self) -> str:
        ...


def get_temp_mail_service(request: Request) -> TempMailService:
    return request.app.state.temp_mail_service
