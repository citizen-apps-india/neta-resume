"""Provenance helpers — every fact write must record where it came from.

A pipeline first records a `source_ref` (the native record in a source), then attaches that
source_ref_id to each domain fact it writes. This module centralizes that discipline.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import MetaData, Table
from sqlalchemy.orm import Session

from neta_ingest.config import settings
from neta_ingest.db.upsert import upsert

_meta = MetaData()


def _table(session: Session, name: str) -> Table:
    return Table(name, _meta, autoload_with=session.get_bind())


def record_source_ref(
    session: Session,
    *,
    source_code: str,
    native_id: str,
    native_url: str | None = None,
    raw_name: str | None = None,
    raw_payload_ref: str | None = None,
) -> int:
    """Upsert a source_ref row and return its id (the dedup key is (source_id, native_id))."""
    source = _table(session, "source")
    source_id = session.execute(
        source.select().with_only_columns(source.c.id).where(source.c.code == source_code)
    ).scalar_one()

    source_ref = _table(session, "source_ref")
    return upsert(
        session,
        source_ref,
        {
            "source_id": source_id,
            "native_id": native_id,
            "native_url": native_url,
            "raw_name": raw_name,
            "raw_payload_ref": raw_payload_ref,
        },
        conflict_cols=["source_id", "native_id"],
        update_cols=["native_url", "raw_name", "raw_payload_ref", "fetched_at"],
    )


def cache_raw(content: bytes, *, suffix: str = ".html") -> str:
    """Write a content-addressed snapshot to the raw_cache and return its relative path.

    The returned path is stored as source_ref.raw_payload_ref — a permanent provenance archive of
    exactly what each fact was derived from.
    """
    digest = hashlib.sha256(content).hexdigest()
    rel = f"{digest[:2]}/{digest}{suffix}"
    dest = Path(settings.raw_cache_dir) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(content)
    return rel
