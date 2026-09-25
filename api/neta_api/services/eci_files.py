"""ECI Files read service — a sourced, dated record of the Election Commission of India (2019-today).

The curated tables (`eci_file_entry`, `eci_file_person`, `eci_file_entry_person`, `eci_file_citation`) are a
small, editorially-loaded set (see `ingestion/neta_ingest/pipelines/curated/eci_files.py`), so every route
here loads its full filtered entry set in a handful of queries and assembles it in Python, the same shape as
`services/indicators.py`. `figures`/`details` are jsonb and come back from psycopg already as Python
list/dict; `topics`/`states` are native Postgres arrays and come back as Python lists.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

_ENTRY_COLUMNS = """
    id, area, kind, date, date_precision, title, summary, status, attributed_to,
    topics, states, figures, details, response_to, notes, check_status
"""


def _load_entries(db: Session, ids: list[str]) -> list[dict]:
    """Full EciEntry payloads for exactly these ids, in the given order (dedup, drops unknown ids)."""
    ordered = list(dict.fromkeys(ids))
    if not ordered:
        return []

    base_rows = db.execute(
        text(f"SELECT {_ENTRY_COLUMNS} FROM eci_file_entry WHERE id = ANY(:ids)"),
        {"ids": ordered},
    ).all()
    by_id = {r.id: r for r in base_rows}

    people_by_entry: dict[str, list[dict]] = defaultdict(list)
    for r in db.execute(
        text(
            """
            SELECT ep.entry_id, p.slug, p.name
            FROM eci_file_entry_person ep JOIN eci_file_person p ON p.slug = ep.person_slug
            WHERE ep.entry_id = ANY(:ids)
            ORDER BY p.name
            """
        ),
        {"ids": ordered},
    ):
        people_by_entry[r.entry_id].append({"slug": r.slug, "name": r.name})

    citations_by_entry: dict[str, list[dict]] = defaultdict(list)
    for r in db.execute(
        text(
            """
            SELECT c.entry_id, c.position, sr.native_url AS url, c.publisher, c.title, c.published,
                   c.tier, c.archive_url, c.quote
            FROM eci_file_citation c JOIN source_ref sr ON sr.id = c.source_ref_id
            WHERE c.entry_id = ANY(:ids)
            ORDER BY c.entry_id, c.position
            """
        ),
        {"ids": ordered},
    ):
        citations_by_entry[r.entry_id].append(
            {
                "position": r.position,
                "url": r.url,
                "publisher": r.publisher,
                "title": r.title,
                "published": r.published,
                "tier": r.tier,
                "archive_url": r.archive_url,
                "quote": r.quote,
            }
        )

    responses_by_entry: dict[str, list[dict]] = defaultdict(list)
    for r in db.execute(
        text(
            """
            SELECT response_to, id, title, date FROM eci_file_entry
            WHERE response_to = ANY(:ids)
            ORDER BY date ASC NULLS LAST, id ASC
            """
        ),
        {"ids": ordered},
    ):
        responses_by_entry[r.response_to].append({"id": r.id, "title": r.title, "date": r.date})

    out: list[dict] = []
    for eid in ordered:
        r = by_id.get(eid)
        if r is None:
            continue
        out.append(
            {
                "id": r.id,
                "area": r.area,
                "kind": r.kind,
                "date": r.date,
                "date_precision": r.date_precision,
                "title": r.title,
                "summary": r.summary,
                "status": r.status,
                "attributed_to": r.attributed_to,
                "topics": list(r.topics or []),
                "states": list(r.states or []),
                "figures": r.figures if r.figures is not None else [],
                "details": r.details if r.details is not None else {},
                "notes": r.notes,
                "check_status": r.check_status,
                "people": people_by_entry.get(eid, []),
                "response_to": r.response_to,
                "responses": responses_by_entry.get(eid, []),
                "citations": citations_by_entry.get(eid, []),
            }
        )
    return out


def _filtered_entry_ids(
    db: Session,
    *,
    topic: str | None,
    person: str | None,
    status: str | None,
    date_from: date | None,
    date_to: date | None,
) -> list[str]:
    params: dict = {}
    join = ""
    conds: list[str] = ["e.kind <> 'person'"]
    if person:
        join = "JOIN eci_file_entry_person ep ON ep.entry_id = e.id AND ep.person_slug = :person"
        params["person"] = person
    if topic:
        conds.append(":topic = ANY(e.topics)")
        params["topic"] = topic
    if status:
        conds.append("e.status = :status")
        params["status"] = status
    if date_from:
        conds.append("e.date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conds.append("e.date <= :date_to")
        params["date_to"] = date_to
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    rows = db.execute(
        text(f"SELECT e.id FROM eci_file_entry e {join} {where} ORDER BY e.date ASC NULLS LAST, e.id ASC"),  # noqa: S608
        params,
    ).all()
    return [r.id for r in rows]


def timeline(
    db: Session,
    *,
    topic: str | None = None,
    person: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """The filtered timeline (date asc, then id) with checked/unchecked counts for that view. The topic
    and people facets cover the whole record, so picking one filter never hides the other choices."""
    ids = _filtered_entry_ids(db, topic=topic, person=person, status=status, date_from=date_from, date_to=date_to)
    entries = _load_entries(db, ids)
    checked = sum(1 for e in entries if e["check_status"] == "checked")

    topics = [
        {"topic": r.topic, "count": r.n}
        for r in db.execute(
            text(
                "SELECT t AS topic, count(*) AS n FROM eci_file_entry, unnest(topics) AS t "
                "GROUP BY t ORDER BY n DESC, t"
            )
        )
    ]
    people = [
        {"slug": r.slug, "name": r.name, "count": r.n}
        for r in db.execute(
            text(
                "SELECT p.slug, p.name, count(ep.entry_id) AS n FROM eci_file_person p "
                "JOIN eci_file_entry_person ep ON ep.person_slug = p.slug "
                "GROUP BY p.slug, p.name ORDER BY n DESC, p.name"
            )
        )
    ]
    return {
        "entries": entries,
        "topics": topics,
        "people": people,
        "counts": {"checked": checked, "unchecked": len(entries) - checked},
    }


def people(db: Session) -> list[dict]:
    """One row per person: role + tenure from their profile entry's details, plus a linked-entry count."""
    rows = db.execute(
        text(
            """
            SELECT p.slug, p.name, prof.details,
                   (SELECT count(*) FROM eci_file_entry_person ep WHERE ep.person_slug = p.slug) AS entry_count
            FROM eci_file_person p
            LEFT JOIN eci_file_entry prof ON prof.id = p.profile_entry_id
            ORDER BY p.name
            """
        )
    ).all()
    out = []
    for r in rows:
        details = r.details or {}
        out.append(
            {
                "slug": r.slug,
                "name": r.name,
                "role": details.get("role"),
                "tenure": details.get("tenure") or [],
                "entry_count": r.entry_count,
            }
        )
    return out


def person_page(db: Session, slug: str) -> dict | None:
    """One person's profile entry (if any) + every entry that names them, timeline-ordered."""
    row = db.execute(
        text("SELECT slug, name, profile_entry_id FROM eci_file_person WHERE slug = :slug"),
        {"slug": slug},
    ).first()
    if row is None:
        return None

    profile = None
    if row.profile_entry_id:
        loaded = _load_entries(db, [row.profile_entry_id])
        profile = loaded[0] if loaded else None

    entry_ids = [
        r.entry_id
        for r in db.execute(
            text(
                """
                SELECT ep.entry_id
                FROM eci_file_entry_person ep JOIN eci_file_entry e ON e.id = ep.entry_id
                WHERE ep.person_slug = :slug
                ORDER BY e.date ASC NULLS LAST, e.id ASC
                """
            ),
            {"slug": slug},
        )
    ]
    entries = _load_entries(db, entry_ids)

    return {
        "person": {"slug": row.slug, "name": row.name, "profile": profile},
        "entries": entries,
    }


def entry(db: Session, entry_id: str) -> dict | None:
    loaded = _load_entries(db, [entry_id])
    return loaded[0] if loaded else None
