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
