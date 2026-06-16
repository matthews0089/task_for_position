from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.email import router as email_router
from app.core.config import Settings, get_settings
from app.core.exceptions import TempMailError
from app.core.logging import configure_logging, get_logger
from app.services.temp_mail_service import TempMailService

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.automation.browser import BrowserManager
    from app.automation.tempail_client import TempailClient

    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("application startup", extra={"app_env": settings.app_env})

    browser_manager = BrowserManager(settings=settings)
    await browser_manager.start()

    app.state.settings = settings
    app.state.browser_manager = browser_manager
    app.state.tempail_client = TempailClient(browser_manager=browser_manager, settings=settings)
    app.state.temp_mail_service = TempMailService(client=app.state.tempail_client)

    try:
        yield
    finally:
        logger.info("application shutdown")
        await browser_manager.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Tempail Automation API",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.exception_handler(TempMailError)
    async def temp_mail_exception_handler(_: Request, exc: TempMailError) -> JSONResponse:
        logger.warning("temp mail error", extra={"code": exc.code, "detail": exc.detail})
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled application error", extra={"error": exc.__class__.__name__})
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "code": "INTERNAL_SERVER_ERROR"},
        )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(email_router, prefix="/api", tags=["email"])
    return app


app = create_app()
