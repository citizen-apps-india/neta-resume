"""Backend settings loaded from environment variables."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NETA_BACKEND_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://neta:neta@localhost:5432/neta"
    sql_echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    environment: Literal["development", "test", "production"] = "development"
    admin_auth_mode: Literal["disabled", "local_token"] = "disabled"
    admin_token: SecretStr | None = None
    admin_session_secret: SecretStr | None = None
    admin_actor: str = "local-operator"
    admin_session_ttl_seconds: int = Field(default=28800, ge=300, le=86400)
    admin_cookie_secure: bool = True

    @model_validator(mode="after")
    def validate_admin_auth(self) -> BackendSettings:
        if self.admin_auth_mode == "disabled":
            return self
        if self.environment == "production":
            raise ValueError(
                "local_token admin authentication is prohibited in production; "
                "keep the admin service private until OIDC is configured"
            )
        token = self.admin_token.get_secret_value() if self.admin_token else ""
        session_secret = (
            self.admin_session_secret.get_secret_value()
            if self.admin_session_secret
            else ""
        )
        if len(token) < 24:
            raise ValueError("NETA_BACKEND_ADMIN_TOKEN must contain at least 24 characters")
        if len(session_secret) < 32:
            raise ValueError(
                "NETA_BACKEND_ADMIN_SESSION_SECRET must contain at least 32 characters"
            )
        if not self.admin_actor.strip():
            raise ValueError("NETA_BACKEND_ADMIN_ACTOR cannot be empty")
        return self


settings = BackendSettings()
