"""Application settings.

All configuration (including secrets) comes from the environment, never from source code.
In production the environment is populated from the platform secret store; locally from
`.env` (which is git-ignored - see `.env.example`).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CARESLOT_", env_file=".env", extra="ignore")

    environment: Literal["local", "test", "staging", "production"] = "local"
    database_url: str = "postgresql+psycopg://careslot:careslot@localhost:5432/careslot"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    return Settings()


__all__ = ["SecretStr", "Settings", "get_settings"]
