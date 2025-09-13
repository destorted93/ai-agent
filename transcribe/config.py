from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

    DEBUG: bool = False
    PORT: int = 6001
    SERVICE_NAME: str = "transcribe"
    LOG_LEVEL: str = "INFO"

    MAX_CONTENT_LENGTH_MB: int = 25
    ALLOWED_EXTENSIONS: set[str] = Field(
        default_factory=lambda: {
            "flac",
            "mp3",
            "mp4",
            "mpeg",
            "mpga",
            "m4a",
            "ogg",
            "wav",
            "webm",
        }
    )
    ALLOWED_LANGS: set[str] = Field(
        default_factory=lambda: {"en", "ro", "ru", "de", "fr", "es"}
    )

    @field_validator("LOG_LEVEL")
    @classmethod
    def _log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        u = (v or "INFO").upper()
        return u if u in allowed else "INFO"

    @property
    def MAX_CONTENT_LENGTH(self) -> int:
        return self.MAX_CONTENT_LENGTH_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
