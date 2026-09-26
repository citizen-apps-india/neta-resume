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
    id, area, kind, date, date_precision, title, summary, status, lane, attributed_to,
    topics, states, figures, details, response_to, notes, check_status
"""

_COMPACT_COLUMNS = "id, date, date_precision, title, status, lane, check_status"

_STAGE_ORDER = ("before", "draft", "final", "appeals_filed", "appeals_pending", "restored")


def _load_entries(db: Session, ids: list[str], *, compact: bool = False) -> list[dict]:
    """EciEntry (or, compact, EciEntryCompact) payloads for exactly these ids, in the given order
    (dedup, drops unknown ids). Compact skips the citations/responses queries entirely — the dots on
    the lane timeline never need them."""
    ordered = list(dict.fromkeys(ids))
    if not ordered:
        return []

    base_rows = db.execute(
        text(f"SELECT {_COMPACT_COLUMNS if compact else _ENTRY_COLUMNS} FROM eci_file_entry WHERE id = ANY(:ids)"),
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

    if compact:
        out: list[dict] = []
        for eid in ordered:
            r = by_id.get(eid)
            if r is None:
                continue
            out.append(
                {
                    "id": r.id,
                    "date": r.date,
                    "date_precision": r.date_precision,
                    "title": r.title,
                    "status": r.status,
                    "lane": r.lane,
                    "check_status": r.check_status,
                    "people": people_by_entry.get(eid, []),
                }
            )
        return out

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

    out = []
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
                "lane": r.lane,
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
    lane: str | None,
    date_from: date | None,
    date_to: date | None,
    state: str | None,
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
    if lane:
        conds.append("e.lane = :lane")
        params["lane"] = lane
    if date_from:
        conds.append("e.date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conds.append("e.date <= :date_to")
        params["date_to"] = date_to
    if state:
        # An unknown slug resolves to no name, so the state condition can never match — same as an
        # unknown person: an empty `entries` list, not a 404.
        region_name = db.execute(
            text("SELECT name FROM eci_file_region WHERE slug = :slug"), {"slug": state}
        ).scalar_one_or_none()
        conds.append(":state_name = ANY(e.states)")
        params["state_name"] = region_name
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
    lane: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    state: str | None = None,
    fields: str | None = None,
) -> dict:
    """The filtered timeline (date asc, then id) with checked/unchecked counts for that view. The topic,
    people, lane and state facets cover the whole record, so picking one filter never hides the other
    choices. `fields="compact"` skips citations/responses — just enough to draw the lane timeline's dots.
    """
    ids = _filtered_entry_ids(
        db,
        topic=topic,
        person=person,
        status=status,
        lane=lane,
        date_from=date_from,
        date_to=date_to,
        state=state,
    )
    entries = _load_entries(db, ids, compact=fields == "compact")
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
    lanes = [
        {"lane": r.lane, "count": r.n}
        for r in db.execute(
            text("SELECT lane, count(*) AS n FROM eci_file_entry GROUP BY lane ORDER BY n DESC, lane")
        )
    ]
    states = [
        {"slug": r.slug, "name": r.name, "count": r.n}
        for r in db.execute(
            text(
                """
                SELECT r.slug, r.name, count(*) AS n
                FROM eci_file_entry e, unnest(e.states) AS s
                JOIN eci_file_region r ON r.name = s
                GROUP BY r.slug, r.name
                ORDER BY n DESC, r.name
                """
            )
        )
    ]
    return {
        "entries": entries,
        "topics": topics,
        "people": people,
        "lanes": lanes,
        "states": states,
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


def summary(db: Session) -> dict:
    """The front page's headline stats (from the curated eci_file_headline table), key moments (the
    full entries named in eci_file_key_moment) and record-wide counts."""
    headline = [
        {
            "value": r.value,
            "label": r.label,
            "source_label": r.source_label,
            "source_url": r.source_url,
            "entry_id": r.entry_id,
        }
        for r in db.execute(
            text(
                "SELECT position, value, label, source_label, source_url, entry_id "
                "FROM eci_file_headline ORDER BY position"
            )
        )
    ]

    key_moment_ids = [
        r.entry_id
        for r in db.execute(text("SELECT entry_id FROM eci_file_key_moment ORDER BY position"))
    ]
    key_moments = _load_entries(db, key_moment_ids)

    counts_row = db.execute(
        text(
            """
            SELECT
                (SELECT count(*) FROM eci_file_entry) AS entries,
                (SELECT count(*) FROM eci_file_entry WHERE check_status = 'checked') AS checked,
                (SELECT count(*) FROM eci_file_person) AS people,
                (SELECT count(*) FROM eci_file_citation) AS citations
            """
        )
    ).one()
    last_loaded = db.execute(text("SELECT max(loaded_at) FROM eci_file_entry")).scalar_one()

    return {
        "headline": headline,
        "key_moments": key_moments,
        "counts": {
            "entries": counts_row.entries,
            "checked": counts_row.checked,
            "people": counts_row.people,
            "citations": counts_row.citations,
        },
        "last_loaded": last_loaded,
    }


def derive_metrics(stages: dict[str, dict], exercise: str | None) -> dict:
    """Pure function, no DB access: the three derived state metrics from a region's stage rows.

    `stages` maps stage name -> {"electors": int, "computed": bool, "approx": bool, "note": str | None}.
    Assam's Special Revision (and any region not run as an SIR at all) is kept out of the SIR
    comparison entirely: every metric is null when `exercise != "sir"`.
    """
    if exercise != "sir":
        return {"draft_left_off": None, "net_change": None, "appeals_filed": None}

    def build(needed: tuple[str, ...], count: int, base_stage: str) -> dict | None:
        if any(n not in stages for n in needed) or base_stage not in stages:
            return None
        base = stages[base_stage]["electors"]
        if base == 0:
            return None
        return {
            "value": round(count / base * 100, 2),
            "count": count,
            "base": base,
            "computed": any(stages[n]["computed"] for n in needed),
            "approx": any(stages[n]["approx"] for n in needed),
            "noted": any(stages[n].get("note") is not None for n in needed),
        }

    draft_left_off = None
    if "before" in stages and "draft" in stages:
        count = stages["before"]["electors"] - stages["draft"]["electors"]
        draft_left_off = build(("before", "draft"), count, "before")

    net_change = None
    if "before" in stages and "final" in stages:
        count = stages["final"]["electors"] - stages["before"]["electors"]
        net_change = build(("before", "final"), count, "before")

    appeals_filed = None
    if "appeals_filed" in stages and "final" in stages:
        count = stages["appeals_filed"]["electors"]
        appeals_filed = build(("appeals_filed", "final"), count, "final")

    return {"draft_left_off": draft_left_off, "net_change": net_change, "appeals_filed": appeals_filed}


def _region_rows(db: Session) -> list[dict]:
    """Every region, with its state row (phase/exercise/notes), stage figures (joined to their
    source entry's title/status), and the count of entries naming it (kind <> 'person')."""
    regions = db.execute(
        text("SELECT slug, name, code, kind FROM eci_file_region ORDER BY name")
    ).all()

    state_by_slug = {
        r.region_slug: r
        for r in db.execute(text("SELECT region_slug, phase, exercise, notes FROM eci_file_state"))
    }

    stages_by_slug: dict[str, list[dict]] = defaultdict(list)
    for r in db.execute(
        text(
            """
            SELECT ss.region_slug, ss.stage, ss.electors, ss.as_of, ss.computed, ss.approx, ss.note,
                   ss.source_entry_id, e.title AS source_entry_title, e.status AS source_status,
                   ss.url, ss.tier
            FROM eci_file_state_stage ss
            JOIN eci_file_entry e ON e.id = ss.source_entry_id
            """
        )
    ):
        stages_by_slug[r.region_slug].append(
            {
                "stage": r.stage,
                "electors": r.electors,
                "as_of": r.as_of,
                "computed": r.computed,
                "approx": r.approx,
                "note": r.note,
                "source_entry_id": r.source_entry_id,
                "source_entry_title": r.source_entry_title,
                "source_status": r.source_status,
                "url": r.url,
                "tier": r.tier,
            }
        )

    entry_counts = {
        r.slug: r.n
        for r in db.execute(
            text(
                """
                SELECT r.slug, count(e.id) AS n
                FROM eci_file_region r
                LEFT JOIN eci_file_entry e ON r.name = ANY(e.states) AND e.kind <> 'person'
                GROUP BY r.slug
                """
            )
        )
    }

    out = []
    for region in regions:
        state = state_by_slug.get(region.slug)
        raw_stages = sorted(
            stages_by_slug.get(region.slug, []),
            key=lambda s: _STAGE_ORDER.index(s["stage"]),
        )
        stages_by_name = {s["stage"]: s for s in raw_stages}
        exercise = state.exercise if state else None
        out.append(
            {
                "slug": region.slug,
                "name": region.name,
                "code": region.code,
                "kind": region.kind,
                "phase": state.phase if state else None,
                "exercise": exercise,
                "has_figures": bool(raw_stages),
                "entry_count": entry_counts.get(region.slug, 0),
                "stages": raw_stages,
                "notes": state.notes if state else None,
                "metrics": derive_metrics(stages_by_name, exercise),
            }
        )
    return out


def states_overview(db: Session) -> dict:
    """`/eci-files/states` — all 36 regions, sorted by name, with the national figures."""
    regions = _region_rows(db)
    national = [
        {
            "group": r.grp,
            "measure": r.measure,
            "label": r.label,
            "scope": r.scope,
            "electors": r.electors,
            "as_of": r.as_of,
            "computed": r.computed,
            "approx": r.approx,
            "note": r.note,
            "source_entry_id": r.source_entry_id,
            "source_entry_title": r.source_entry_title,
            "source_status": r.source_status,
        }
        for r in db.execute(
            text(
                """
                SELECT f.grp, f.measure, f.label, f.scope, f.electors, f.as_of, f.computed, f.approx,
                       f.note, f.source_entry_id, e.title AS source_entry_title, e.status AS source_status
                FROM eci_file_national_figure f
                JOIN eci_file_entry e ON e.id = f.source_entry_id
                ORDER BY f.position
                """
            )
        )
    ]
    last_as_of = db.execute(text("SELECT max(as_of) FROM eci_file_state_stage")).scalar_one()
    return {"regions": regions, "national": national, "last_as_of": last_as_of}


def state_page(db: Session, slug: str) -> dict | None:
    """`/eci-files/states/{slug}` — one region with its notes, or None (-> 404) if unknown."""
    region = next((r for r in _region_rows(db) if r["slug"] == slug), None)
    if region is None:
        return None
    return {"region": region, "notes": region["notes"]}


def density(db: Session) -> dict:
    """Month x lane counts across the whole record, for the timeline's overview strip. Person-kind
    entries are excluded, same as the timeline — they're profiles, not dated events."""
    months = [
        {"month": r.month, "lane": r.lane, "count": r.n}
        for r in db.execute(
            text(
                """
                SELECT to_char(date, 'YYYY-MM') AS month, lane, count(*) AS n
                FROM eci_file_entry
                WHERE kind <> 'person' AND date IS NOT NULL
                GROUP BY month, lane
                ORDER BY month, lane
                """
            )
        )
    ]
    return {"months": months}
