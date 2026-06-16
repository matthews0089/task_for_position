import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.exceptions import (
    BrowserUnavailableError,
    ElementNotFoundError,
    EmailNotFoundError,
    TempMailError,
)
from app.core.logging import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    delay_seconds: float,
    recover: Callable[[], Awaitable[None]] | None = None,
) -> T:
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except BrowserUnavailableError as exc:
            last_error = exc
            logger.warning(
                "browser operation failed; retrying",
                extra={"attempt": attempt, "error": str(exc)},
            )
            if recover:
                await recover()
        except ElementNotFoundError as exc:
            last_error = exc
            logger.warning(
                "page element missing; retrying",
                extra={"attempt": attempt, "code": exc.code},
            )
            if recover:
                await recover()
        except EmailNotFoundError:
            raise
        except TempMailError as exc:
            last_error = exc
            logger.warning(
                "temp mail operation failed; retrying",
                extra={"attempt": attempt, "code": exc.code},
            )

        if attempt < attempts:
            await asyncio.sleep(delay_seconds)

    if last_error:
        raise last_error
    raise RuntimeError("retry operation failed without an exception")
