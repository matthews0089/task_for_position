import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_temp_mail_service
from app.api.schemas import EmailContent, InboxEmail
from app.core.exceptions import EmailNotFoundError
from app.main import create_app


class MockTempMailService:
    async def get_current_email(self) -> str:
        return "demo@tempail.com"

    async def get_inbox(self) -> list[InboxEmail]:
        return [
            InboxEmail(
                id="message-1",
                sender="sender@example.com",
                subject="Hello",
                time="10:30",
            )
        ]

    async def get_email_content(self, email_id: str) -> EmailContent:
        if email_id != "message-1":
            raise EmailNotFoundError(f"Email with id '{email_id}' was not found")
        return EmailContent(
            id=email_id,
            sender="sender@example.com",
            subject="Hello",
            timestamp="2026-06-16 10:30",
            body="Full message body",
        )

    async def refresh_email(self) -> str:
        return "fresh@tempail.com"


class EmptyInboxService(MockTempMailService):
    async def get_inbox(self) -> list[InboxEmail]:
        return []


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_temp_mail_service] = lambda: MockTempMailService()
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_email_success(client: TestClient) -> None:
    response = client.get("/api/email")

    assert response.status_code == 200
    assert response.json() == {"email": "demo@tempail.com"}


def test_empty_inbox() -> None:
    app = create_app()
    app.dependency_overrides[get_temp_mail_service] = lambda: EmptyInboxService()
    client = TestClient(app)

    response = client.get("/api/inbox")

    assert response.status_code == 200
    assert response.json() == []


def test_email_not_found(client: TestClient) -> None:
    response = client.get("/api/email/unknown")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Email with id 'unknown' was not found",
        "code": "EMAIL_NOT_FOUND",
    }


def test_refresh_email(client: TestClient) -> None:
    response = client.post("/api/email/refresh")

    assert response.status_code == 200
    assert response.json() == {"email": "fresh@tempail.com"}
