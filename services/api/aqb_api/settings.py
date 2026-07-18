from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AQB_",
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    database_url: str = "sqlite:///./data/aqb.db"
    redis_url: str = "redis://127.0.0.1:6379/0"
    execution_mode: str = "local"
    storage_path: Path = Path("./data/artifacts")
    max_upload_bytes: int = 50 * 1024 * 1024
    max_extracted_bytes: int = 250 * 1024 * 1024
    agent_endpoint_allowlist: str = "localhost,127.0.0.1"
    encryption_key: str | None = Field(default=None, repr=False)
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"

    @property
    def allowlist(self) -> tuple[str, ...]:
        return tuple(value.strip() for value in self.agent_endpoint_allowlist.split(",") if value.strip())

    @property
    def allowed_origins(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
