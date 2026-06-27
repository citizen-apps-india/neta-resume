"""Resolve a raw party string/alias to a canonical party_id via party_alias.

Critical for switch detection: 'TMC' and 'All India Trinamool Congress' must map to one party, else a
spelling change reads as a fake switch. Unknown aliases should be logged for manual triage, not silently
dropped.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def resolve_party_id(session: Session, raw: str) -> int | None:
    """Look up canonical party_id by exact canonical name / abbr / alias (case-insensitive)."""
    if not raw:
        return None
    row = session.execute(
        text(
            """
            SELECT p.id FROM party p
            LEFT JOIN party_alias a ON a.party_id = p.id
            WHERE lower(p.canonical_name) = lower(:raw)
               OR lower(p.abbr)           = lower(:raw)
               OR lower(a.alias)          = lower(:raw)
            LIMIT 1
            """
        ),
        {"raw": raw.strip()},
    ).first()
    return row[0] if row else None


def resolve_or_create_party_id(session: Session, raw: str) -> int | None:
    """Resolve a party, auto-creating it if unknown so party data is never silently dropped.

    Newly created parties use the raw source string as canonical_name and register it as an alias.
    These should be reviewed/merged later (many are spelling variants of an existing party).
    """
    if not raw or not raw.strip():
        return None
    existing = resolve_party_id(session, raw)
    if existing is not None:
        return existing
    party_id = session.execute(
        text("INSERT INTO party (canonical_name, is_active) VALUES (:n, true) RETURNING id"),
        {"n": raw.strip()},
    ).scalar_one()
    session.execute(
        text(
            "INSERT INTO party_alias (party_id, alias, source) VALUES (:pid, :a, 'auto-ingest') "
            "ON CONFLICT (party_id, alias) DO NOTHING"
        ),
        {"pid": party_id, "a": raw.strip()},
    )
    return party_id
