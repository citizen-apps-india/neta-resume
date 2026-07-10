"""Shared dependencies: DB session, settings."""

from __future__ import annotations

from collections.abc import Iterator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NETA_", env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://neta:neta@localhost:5432/neta"
    # Comma-separated browser origins allowed to call the API (CORS). Dev default is the Next.js dev
    # server; in prod set NETA_ALLOWED_ORIGINS to the deployed web origin(s), e.g.
    # "https://neta-resume.in,https://www.neta-resume.in". Kept a str (not list) so a plain env value
    # parses without JSON quoting; use `.cors_origins` for the split list.
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = ApiSettings()
# Cap any single statement at 15s so a runaway FTS/aggregate query can't pin a Neon connection. Passed as a
# libpq option on connect (psycopg3); Postgres aborts the statement server-side and frees the backend.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    connect_args={"options": "-c statement_timeout=15000"},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
