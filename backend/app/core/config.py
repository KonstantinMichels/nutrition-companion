from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration with fail-closed production checks."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["local", "development", "test", "staging", "production"] = "development"
    database_url: str = (
        "postgresql+psycopg://nutrition_dev:nutrition_dev_only@localhost:5432/nutrition_companion"
    )
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    development_profile_id: UUID = UUID("00000000-0000-4000-8000-000000000001")
    use_development_profile_resolver: bool = True
    allow_insecure_local_http: bool = True
    public_api_url: HttpUrl = HttpUrl("http://localhost:8000")
    log_level: str = "INFO"
    technical_log_retention_days: int = Field(default=14, ge=1, le=90)

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_local(self) -> bool:
        return self.app_env in {"local", "development", "test"}

    @model_validator(mode="after")
    def reject_unsafe_non_local_configuration(self) -> Self:
        if self.is_local:
            return self

        if self.allow_insecure_local_http or self.public_api_url.scheme != "https":
            raise ValueError("Non-local environments require HTTPS and disallow insecure HTTP")
        if self.use_development_profile_resolver:
            raise ValueError(
                "The development profile resolver is forbidden outside local environments"
            )
        if "*" in self.parsed_cors_origins:
            raise ValueError("Wildcard CORS is forbidden outside local environments")

        lowered_database_url = self.database_url.lower()
        forbidden_markers = ("nutrition_dev", "dev_only", "localhost", "127.0.0.1")
        if any(marker in lowered_database_url for marker in forbidden_markers):
            raise ValueError(
                "Development database credentials or hosts are forbidden outside local environments"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
