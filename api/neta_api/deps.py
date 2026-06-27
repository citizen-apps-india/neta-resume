"""Shared dependencies: DB session, settings."""

from __future__ import annotations

from collections.abc import Iterator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NETA_", env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://neta:neta@localhost:5432/neta"


settings = ApiSettings()
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
