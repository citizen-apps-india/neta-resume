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
    admin_auth_mode: Literal["disabled", "local_token", "github_oidc"] = "disabled"
    admin_token: SecretStr | None = None
    admin_session_secret: SecretStr | None = None
    admin_actor: str = "local-operator"
    admin_session_ttl_seconds: int = Field(default=28800, ge=300, le=86400)
    admin_cookie_secure: bool = True

    # GitHub OAuth (authorization code flow), for `admin_auth_mode == "github_oidc"`. This is the
    # only mode permitted in production alongside "disabled" — see `validate_admin_auth` below.
    admin_github_client_id: str | None = None
    admin_github_client_secret: SecretStr | None = None
    admin_github_redirect_uri: str | None = None
    # Comma-separated GitHub logins allowed to sign in, e.g. "octocat,ana-dev".
    admin_github_allowed_logins: str = ""
    admin_github_allowed_org: str | None = None
    # Optional team slug within admin_github_allowed_org; if unset, org membership alone suffices.
    admin_github_allowed_team: str | None = None

    @property
    def github_allowed_logins(self) -> frozenset[str]:
        return frozenset(
            login.strip().lower()
            for login in self.admin_github_allowed_logins.split(",")
            if login.strip()
        )

    @model_validator(mode="after")
    def validate_admin_auth(self) -> BackendSettings:
        if self.admin_auth_mode == "disabled":
            return self

        if self.admin_auth_mode == "local_token" and self.environment == "production":
            raise ValueError(
                "local_token admin authentication is prohibited in production; "
                "use github_oidc or keep the admin service disabled"
            )

        session_secret = (
            self.admin_session_secret.get_secret_value() if self.admin_session_secret else ""
        )
        if len(session_secret) < 32:
            raise ValueError(
                "NETA_BACKEND_ADMIN_SESSION_SECRET must contain at least 32 characters"
            )
        if not self.admin_actor.strip():
            raise ValueError("NETA_BACKEND_ADMIN_ACTOR cannot be empty")

        if self.admin_auth_mode == "local_token":
            token = self.admin_token.get_secret_value() if self.admin_token else ""
            if len(token) < 24:
                raise ValueError("NETA_BACKEND_ADMIN_TOKEN must contain at least 24 characters")

        if self.admin_auth_mode == "github_oidc":
            client_secret = (
                self.admin_github_client_secret.get_secret_value()
                if self.admin_github_client_secret
                else ""
            )
            if not self.admin_github_client_id or not self.admin_github_client_id.strip():
                raise ValueError(
                    "NETA_BACKEND_ADMIN_GITHUB_CLIENT_ID is required for github_oidc"
                )
            if not client_secret:
                raise ValueError(
                    "NETA_BACKEND_ADMIN_GITHUB_CLIENT_SECRET is required for github_oidc"
                )
            if not self.admin_github_redirect_uri or not self.admin_github_redirect_uri.strip():
                raise ValueError(
                    "NETA_BACKEND_ADMIN_GITHUB_REDIRECT_URI is required for github_oidc"
                )
            has_org = bool(self.admin_github_allowed_org and self.admin_github_allowed_org.strip())
            if not self.github_allowed_logins and not has_org:
                raise ValueError(
                    "github_oidc requires NETA_BACKEND_ADMIN_GITHUB_ALLOWED_LOGINS or "
                    "NETA_BACKEND_ADMIN_GITHUB_ALLOWED_ORG so an allowlist restricts sign-in"
                )
        return self


settings = BackendSettings()
