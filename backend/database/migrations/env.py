"""Alembic environment for the async control-plane backend."""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from neta_backend.config import settings
from neta_backend.database.base import Base
from neta_backend.database.models import __all__ as all_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
MANAGED_TABLES = {
    "pipeline_source_state",
    "pipeline_source_config_revision",
    "pipeline_run_request",
    "pipeline_run",
    "pipeline_audit_event",
}


def _database_url() -> str:
    url = os.getenv("NETA_BACKEND_DATABASE_URL", settings.database_url)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url.replace("+psycopg2", "+asyncpg").replace("+psycopg", "+asyncpg")


config.set_main_option("sqlalchemy.url", _database_url())


def _include_name(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    """Keep Alembic autogeneration scoped to backend-owned tables."""
    del parent_names
    if type_ == "table":
        return bool(name and name in MANAGED_TABLES)
    return True


def _include_object(
    object_: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    del object_, reflected, compare_to
    if type_ == "table":
        return bool(name and name in MANAGED_TABLES)
    return True


def _configure(connection: Connection | None = None, *, url: str | None = None) -> None:
    context.configure(
        connection=connection,
        url=url,
        target_metadata=target_metadata,
        include_name=_include_name,
        include_object=_include_object,
        compare_type=True,
        compare_server_default=True,
        literal_binds=connection is None,
        dialect_opts={"paramstyle": "named"} if connection is None else None,
    )


def run_migrations_offline() -> None:
    _configure(url=config.get_main_option("sqlalchemy.url"))
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
