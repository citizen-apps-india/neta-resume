"""Shared dependencies: DB session, settings."""

from __future__ import annotations

from collections.abc import Iterator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool


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

# poolclass=NullPool: every request opens its own DBAPI connection and closes it for real when the
# request ends (get_db's `db.close()` below) instead of SQLAlchemy's default QueuePool, which keeps up to
# pool_size (5) + max_overflow (10) connections open and idle indefinitely — there is no pool_recycle or
# idle timeout configured, so once any request touched the DB the pool never gave a connection back.
#
# That default pool is exactly why Neon compute never autosuspended: Neon's serverless compute only stops
# billing CU-hours when it has ZERO connections — idle counts the same as busy. As long as the Render
# process held one pooled connection open, the meter ran 24/7 regardless of query volume, which is what
# drove the free-tier meter to ~95/100 CU-hrs for the month and is what exhausted the quota mid-migration
# in July. NullPool removes the one thing capable of holding a connection open past a single request.
#
# This is also the right shape for this DSN specifically: it already points at Neon's `-pooler` endpoint
# (pgbouncer, transaction-pooling mode) — see the statement_timeout comment below — so server-side pooling
# already exists; an app-level pool on top of it was redundant, not free insurance.
#
# pool_pre_ping is dropped along with QueuePool: it exists to catch a stale connection pulled back out of
# an idle pool before using it. NullPool never reuses a connection — every checkout is freshly connected —
# so there is nothing for pre-ping to catch, and keeping it would just add an extra round trip per request.
#
# Trade-off: every request now pays a fresh TCP+TLS+Postgres-protocol handshake to the pooler instead of
# reusing a warm connection (roughly single-digit-to-tens of ms on top of the query itself), and a request
# that lands after Neon has actually suspended the compute pays a cold start on top of that (typically well
# under a second, per Neon's docs, but not instant). For a low-traffic, read-only public API, that
# occasional extra latency is a better trade than compute that never sleeps.
engine = create_engine(settings.database_url, poolclass=NullPool, future=True)


# Cap any single statement at 15s so a runaway FTS/aggregate query can't pin a Neon connection; Postgres
# aborts the statement server-side and frees the backend. Issued as `SET LOCAL` at the start of EVERY
# transaction — NOT as a libpq `options` startup parameter (connect_args): Neon's pooled endpoint
# (pgbouncer) rejects the `options` startup parameter outright, which made every connection — and thus
# every DB endpoint — fail instantly in production while local/direct Postgres accepted it fine.
# SET LOCAL scopes to the transaction, the only scope that survives pgbouncer transaction pooling.
@event.listens_for(engine, "begin")
def _statement_timeout(conn) -> None:
    conn.exec_driver_sql("SET LOCAL statement_timeout = 15000")


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
