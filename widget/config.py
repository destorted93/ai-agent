from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

    DEBUG: bool = False
    PORT: int = 6002
    SERVICE_NAME: str = "widget"
    LOG_LEVEL: str = "INFO"

    TRANSCRIBE_URL: str = "http://127.0.0.1:6001/upload"


@lru_cache
def get_settings() -> Settings:
    return Settings()
