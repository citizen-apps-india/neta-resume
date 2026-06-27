"""Idempotent upsert helpers (Postgres INSERT ... ON CONFLICT DO UPDATE).

Every ingestion write goes through here so re-running a pipeline never duplicates rows.
Natural keys per table are documented in db/migrations/*.sql (the UNIQUE constraints).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import Table


def upsert(
    session: Session,
    table: Table,
    values: dict[str, Any],
    conflict_cols: list[str],
    update_cols: list[str] | None = None,
) -> Any:
    """Upsert one row keyed on conflict_cols; return the row id.

    update_cols defaults to every provided column except the conflict key.
    """
    if update_cols is None:
        update_cols = [c for c in values if c not in conflict_cols]

    stmt = insert(table).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=conflict_cols,
        set_={c: stmt.excluded[c] for c in update_cols},
    ).returning(table.c.id)
    return session.execute(stmt).scalar_one()
