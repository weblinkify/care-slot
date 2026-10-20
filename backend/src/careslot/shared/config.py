"""Application settings.

All configuration (including secrets) comes from the environment, never from source code.
In production the environment is populated from the platform secret store; locally from
`.env` (which is git-ignored - see `.env.example`).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CARESLOT_", env_file=".env", extra="ignore")

    environment: Environment = "local"
    database_url: str = "postgresql+psycopg://careslot:careslot@localhost:5433/careslot"
    log_level: LogLevel = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    # OTLP/HTTP collector base URL, e.g. http://jaeger:4318. Unset: traces are not exported.
    otel_exporter_endpoint: str | None = None

    # Authentication. Outside local/test the public key MUST be provided (fail fast).
    jwt_issuer: str = "careslot-mock-idp"
    jwt_audience: str = "careslot-api"
    jwt_public_key: str | None = None
    idp_private_key: SecretStr | None = None

    # Column encryption (shared.crypto). "v1:<b64>,v2:<b64>" - last entry is active.
    keks: SecretStr | None = None
    blind_index_key: SecretStr | None = None

    # Storage limitation: booking data is deleted this long after the appointment ended.
    # (The booking service is not the medical record; clinical notes have their own, much
    # longer statutory retention in the patient record system.)
    retention_appointment_days: int = Field(default=730, ge=30)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, value: object) -> object:
        # Reject typos at startup instead of when logging is first configured.
        return value.upper() if isinstance(value, str) else value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def allows_ephemeral_keys(self) -> bool:
        """Local/test may generate throwaway keys; everywhere else keys must be provided."""
        return self.environment in ("local", "test")


@lru_cache
def get_settings() -> Settings:
    return Settings()
