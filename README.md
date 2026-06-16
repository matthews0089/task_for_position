# Tempail Automation API

Python/FastAPI service that automates [tempail.com](https://tempail.com/ua/) temporary email through Playwright and exposes a small JSON REST API.

## Stack

- Python 3.12
- FastAPI
- Playwright async with Chromium
- Pydantic v2 and pydantic-settings
- uvicorn
- Docker and docker-compose
- structured JSON logging
- pytest

## Architecture

```text
app/
  main.py                         FastAPI app, lifespan, exception handlers
  core/                           settings, logging, custom exceptions
  api/                            routes, schemas, dependencies
  services/temp_mail_service.py   business use cases
  automation/                     Playwright browser/session/tempail details
  utils/retry.py                  async retry helper
tests/                            API tests with mocked service
```

The API layer does not know about Playwright. Browser automation is isolated in `app/automation/tempail_client.py`; the business-facing service is `app/services/temp_mail_service.py`.

One browser/context/page is reused during the application lifetime. If Playwright reports a stale or unavailable browser, the operation is retried and the browser is recreated.

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000/health
```

## Docker Run

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

Creating `.env` from `.env.example` is optional; compose uses sensible defaults and lets `.env` override them.

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `APP_ENV` | `local` | Application environment name. |
| `LOG_LEVEL` | `INFO` | Logging level. |
| `TEMPAIL_URL` | `https://tempail.com/ua/` | Tempail page URL. |
| `BROWSER_HEADLESS` | `true` | Run Chromium in headless mode. |
| `PAGE_LOAD_TIMEOUT` | `30000` | Page navigation/load timeout in milliseconds. |
| `ACTION_TIMEOUT` | `10000` | Element/action timeout in milliseconds. |
| `INBOX_POLL_INTERVAL` | `2.0` | Polling interval reserved for inbox monitoring workflows. |
| `RETRY_ATTEMPTS` | `3` | Retry attempts for unstable browser actions. |
| `RETRY_DELAY_SECONDS` | `0.75` | Delay between retries. |

## API Examples

Health:

```bash
curl http://localhost:8000/health
```

Current temporary email:

```bash
curl http://localhost:8000/api/email
```

Inbox:

```bash
curl http://localhost:8000/api/inbox
```

Full email:

```bash
curl http://localhost:8000/api/email/message-1
```

Refresh temporary email:

```bash
curl -X POST http://localhost:8000/api/email/refresh
```

## Error Format

All API errors are JSON:

```json
{
  "detail": "Human readable error",
  "code": "TEMP_MAIL_UNAVAILABLE"
}
```

Common codes:

- `EMAIL_NOT_FOUND`
- `BROWSER_UNAVAILABLE`
- `ELEMENT_NOT_FOUND`
- `TEMP_MAIL_TIMEOUT`
- `TEMP_MAIL_UNAVAILABLE`
- `INTERNAL_SERVER_ERROR`

## Tests

```bash
pytest
```

Tests use FastAPI dependency overrides and mocked services. They do not open a browser or call the real tempail.com site.

## Important Note

tempail.com is an external JS-rendered website. If the site changes its DOM, selectors in `app/automation/selectors.py` may require updates. The API is designed to return stable JSON errors instead of leaking Playwright stack traces to clients.

tempail.com can also enable anti-bot verification for automated browser sessions. When that happens, the service returns `TEMP_MAIL_UNAVAILABLE` in the standard JSON error format. This is expected behavior for a dependency outside of the application's control. API contracts are covered by tests and mocked service dependencies, so the project can be reviewed without relying on live tempail.com availability.
