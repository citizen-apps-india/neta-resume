"""Central config: DB DSN, polite-scraping knobs, per-source toggles.

Reads from environment (prefix NETA_). See .env.example.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NETA_", env_file=".env", extra="ignore")

    # Postgres
    database_url: str = "postgresql+psycopg://neta:neta@localhost:5432/neta"
    # DSN for schema migrations (needs DDL/owner privileges). Falls back to database_url when unset.
    migrate_database_url: str | None = None

    # Polite scraping defaults (be a good citizen — MyNeta is non-commercial & unmetered).
    http_user_agent: str = "neta-resume/0.1 (non-commercial research; contact: sahil@magicweave.xyz)"
    http_min_delay_seconds: float = 1.0     # min gap between requests to the same host
    http_max_retries: int = 4
    http_timeout_seconds: float = 30.0

    # Where raw fetched HTML/PDF/JSON snapshots are cached (provenance archive; gitignored).
    raw_cache_dir: str = "data/raw_cache"

    # Entity-resolution thresholds (see docs/entity-resolution.md).
    er_auto_merge_score: float = 0.92
    er_auto_reject_score: float = 0.55      # between reject..merge => review queue

    # Severity rubric version stamped onto classified cases.
    severity_rule_version: str = "adr-v1"


settings = Settings()
