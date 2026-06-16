from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="local", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    tempail_url: HttpUrl = Field(default="https://tempail.com/ua/", alias="TEMPAIL_URL")
    browser_headless: bool = Field(default=True, alias="BROWSER_HEADLESS")
    page_load_timeout: int = Field(default=30_000, alias="PAGE_LOAD_TIMEOUT")
    action_timeout: int = Field(default=10_000, alias="ACTION_TIMEOUT")
    inbox_poll_interval: float = Field(default=2.0, alias="INBOX_POLL_INTERVAL")
    retry_attempts: int = Field(default=3, alias="RETRY_ATTEMPTS")
    retry_delay_seconds: float = Field(default=0.75, alias="RETRY_DELAY_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
