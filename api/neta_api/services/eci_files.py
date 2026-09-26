"""ECI Files read service — a sourced, dated record of the Election Commission of India (2019-today).

The curated tables (`eci_file_entry`, `eci_file_person`, `eci_file_entry_person`, `eci_file_citation`) are a
small, editorially-loaded set (see `ingestion/neta_ingest/pipelines/curated/eci_files.py`), so every route
here loads its full filtered entry set in a handful of queries and assembles it in Python, the same shape as
`services/indicators.py`. `figures`/`details` are jsonb and come back from psycopg already as Python
list/dict; `topics`/`states` are native Postgres arrays and come back as Python lists.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

_ENTRY_COLUMNS = """
    id, area, kind, date, date_precision, title, summary, status, lane, attributed_to,
    topics, states, figures, details, response_to, notes, check_status
"""

_COMPACT_COLUMNS = "id, date, date_precision, title, status, lane, check_status"

_STAGE_ORDER = (
    "before", "draft", "left_off", "final", "under_adjudication", "form7_deletions",
    "appeals_filed", "appeals_pending", "restored",
)


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
                "JOIN eci_file_entry e ON e.id = ep.entry_id AND e.kind <> 'person' "
                "GROUP BY p.slug, p.name ORDER BY n DESC, p.name"
            )
        )
    ]
    lanes = [
        {"lane": r.lane, "count": r.n}
        for r in db.execute(
            text(
                "SELECT lane, count(*) AS n FROM eci_file_entry WHERE kind <> 'person' "
                "GROUP BY lane ORDER BY n DESC, lane"
            )
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


_PHOTO_COLUMNS = """
    m.url AS photo_url, m.source_page, m.original_publisher, m.caption, m.photo_date,
    m.licence, m.licence_url, m.licence_review, m.attribution
"""


def _photo_payload(row) -> dict | None:
    if row.photo_url is None:
        return None
    return {
        "url": row.photo_url,
        "source_page": row.source_page,
        "attribution": row.attribution,
        "licence": row.licence,
        "licence_url": row.licence_url,
        "licence_review": row.licence_review,
        "original_publisher": row.original_publisher,
        "caption": row.caption,
        "photo_date": row.photo_date,
    }


def _photo_map(db: Session, slugs: set[str]) -> dict[str, dict]:
    if not slugs:
        return {}
    rows = db.execute(
        text(
            f"""
            SELECT person_slug, {_PHOTO_COLUMNS.replace("m.", "")}
            FROM eci_file_person_media WHERE person_slug = ANY(:slugs)
            """  # noqa: S608
        ),
        {"slugs": list(slugs)},
    ).all()
    return {r.person_slug: _photo_payload(r) for r in rows}


def _entry_refs(db: Session, ids: list[str]) -> list[dict]:
    """Compact `id, title, date, date_precision, status` refs for exactly these ids (dedup, drops
    unknown ids) — used to label every entry a selection/regime/departure cites."""
    ordered = list(dict.fromkeys(ids))
    if not ordered:
        return []
    rows = db.execute(
        text(
            "SELECT id, title, date, date_precision, status FROM eci_file_entry WHERE id = ANY(:ids)"
        ),
        {"ids": ordered},
    ).all()
    by_id = {r.id: r for r in rows}
    out = []
    for eid in ordered:
        r = by_id.get(eid)
        if r is None:
            continue
        out.append(
            {
                "id": r.id,
                "title": r.title,
                "date": r.date,
                "date_precision": r.date_precision,
                "status": r.status,
            }
        )
    return out


def _selection_rows(db: Session, ids: list[str] | None = None) -> list[dict]:
    """Every `eci_file_selection` row (or just `ids`), newest first, with `has_profile` added to
    each member and `photo` added to each appointee."""
    where = "WHERE id = ANY(:ids)" if ids is not None else ""
    rows = db.execute(
        text(
            f"""
            SELECT id, date, date_precision, date_meaning, regime, method,
                   appointed, members, search, dissent, entry_ids, notes
            FROM eci_file_selection
            {where}
            ORDER BY date DESC, id DESC
            """  # noqa: S608
        ),
        {"ids": ids} if ids is not None else {},
    ).all()
    if not rows:
        return []

    slugs: set[str] = set()
    for r in rows:
        for a in r.appointed:
            slugs.add(a["person_slug"])
        for m in r.members:
            if m.get("person_slug"):
                slugs.add(m["person_slug"])

    profile_flags = (
        {
            r.slug: r.has_profile
            for r in db.execute(
                text(
                    "SELECT slug, (profile_entry_id IS NOT NULL) AS has_profile "
                    "FROM eci_file_person WHERE slug = ANY(:slugs)"
                ),
                {"slugs": list(slugs)},
            )
        }
        if slugs
        else {}
    )
    photos = _photo_map(db, slugs)

    out = []
    for r in rows:
        appointed = [{**a, "photo": photos.get(a["person_slug"])} for a in r.appointed]
        members = [
            {**m, "has_profile": profile_flags.get(m.get("person_slug"), False)} for m in r.members
        ]
        out.append(
            {
                "id": r.id,
                "date": r.date,
                "date_precision": r.date_precision,
                "date_meaning": r.date_meaning,
                "regime": r.regime,
                "method": r.method,
                "appointed": appointed,
                "members": members,
                "search": r.search,
                "dissent": r.dissent,
                "entry_ids": list(r.entry_ids or []),
                "notes": r.notes,
            }
        )
    return out


def people(db: Session) -> list[dict]:
    """Every person, grouped and ordered per docs/eci-files/PHASE4-SPEC.md section 1.4: the
    Commission, then senior officials, then state Chief Electoral Officers, then everyone else named
    only in passing. Status counts and the entry count both exclude the person's own profile entry."""
    rows = db.execute(
        text(
            f"""
            SELECT p.slug, p.name, p.role_group, p.group_rank, p.is_current AS is_current,
                   p.first_from, p.last_to, prof.details,
                   {_PHOTO_COLUMNS},
                   (SELECT count(*) FROM eci_file_entry_person ep
                    JOIN eci_file_entry e ON e.id = ep.entry_id
                    WHERE ep.person_slug = p.slug AND e.kind <> 'person') AS entry_count
            FROM eci_file_person p
            LEFT JOIN eci_file_entry prof ON prof.id = p.profile_entry_id
            LEFT JOIN eci_file_person_media m ON m.person_slug = p.slug
            ORDER BY
                CASE p.role_group
                    WHEN 'commission' THEN 0 WHEN 'secretariat' THEN 1 WHEN 'state' THEN 2 ELSE 3
                END,
                p.group_rank, p.name
            """
        )
    ).all()

    status_counts: dict[str, dict[str, int]] = defaultdict(dict)
    for r in db.execute(
        text(
            """
            SELECT ep.person_slug, e.status, count(*) AS n
            FROM eci_file_entry_person ep JOIN eci_file_entry e ON e.id = ep.entry_id
            WHERE e.kind <> 'person'
            GROUP BY 1, 2
            """
        )
    ):
        status_counts[r.person_slug][r.status] = r.n

    out = []
    for r in rows:
        details = r.details or {}
        out.append(
            {
                "slug": r.slug,
                "name": r.name,
                "group": r.role_group,
                "group_rank": r.group_rank,
                "current": r.is_current,
                "role": details.get("role"),
                "service": details.get("service"),
                "tenure": details.get("tenure") or [],
                "first_from": r.first_from,
                "last_to": r.last_to,
                "entry_count": r.entry_count,
                "status_counts": status_counts.get(r.slug, {}),
                "photo": _photo_payload(r),
            }
        )
    return out


def person_page(db: Session, slug: str) -> dict | None:
    """One person's profile entry (if any), every non-profile entry that names them (timeline-
    ordered), every selection they took part in (newest first), and a compact index of every entry
    those selections cite."""
    row = db.execute(
        text(
            f"""
            SELECT p.slug, p.name, p.profile_entry_id, p.role_group, p.is_current AS is_current,
                   {_PHOTO_COLUMNS}
            FROM eci_file_person p
            LEFT JOIN eci_file_person_media m ON m.person_slug = p.slug
            WHERE p.slug = :slug
            """
        ),
        {"slug": slug},
    ).first()
    if row is None:
        return None

    profile = None
    details: dict = {}
    if row.profile_entry_id:
        loaded = _load_entries(db, [row.profile_entry_id])
        profile = loaded[0] if loaded else None
        details = (profile or {}).get("details") or {}

    entry_ids = [
        r.entry_id
        for r in db.execute(
            text(
                """
                SELECT ep.entry_id
                FROM eci_file_entry_person ep JOIN eci_file_entry e ON e.id = ep.entry_id
                WHERE ep.person_slug = :slug AND e.kind <> 'person'
                ORDER BY e.date ASC NULLS LAST, e.id ASC
                """
            ),
            {"slug": slug},
        )
    ]
    entries = _load_entries(db, entry_ids)

    status_counts: dict[str, int] = defaultdict(int)
    for r in db.execute(
        text(
            """
            SELECT e.status, count(*) AS n
            FROM eci_file_entry_person ep JOIN eci_file_entry e ON e.id = ep.entry_id
            WHERE ep.person_slug = :slug AND e.kind <> 'person'
            GROUP BY e.status
            """
        ),
        {"slug": slug},
    ):
        status_counts[r.status] = r.n

    selection_ids = [
        r.selection_id
        for r in db.execute(
            text(
                "SELECT DISTINCT selection_id FROM eci_file_selection_person WHERE person_slug = :slug"
            ),
            {"slug": slug},
        )
    ]
    person_selections = _selection_rows(db, selection_ids) if selection_ids else []
    entries_index = _entry_refs(db, [eid for s in person_selections for eid in s["entry_ids"]])

    return {
        "person": {
            "slug": row.slug,
            "name": row.name,
            "profile": profile,
            "group": row.role_group,
            "current": row.is_current,
            "role": details.get("role"),
            "service": details.get("service"),
            "tenure": details.get("tenure") or [],
            "status_counts": dict(status_counts),
            "photo": _photo_payload(row),
        },
        "entries": entries,
        "selections": person_selections,
        "entries_index": entries_index,
    }


def selections(db: Session) -> dict:
    """`/eci-files/selections` — every regime, every selection (newest first), every departure, and
    a compact index of every entry any of them cites."""
    regime_rows = db.execute(
        text(
            """
            SELECT r.key, r.label, r.from_date, r.to_date, r.rule, r.panel, r.entry_ids, r.notes,
                   (SELECT count(*) FROM eci_file_selection s WHERE s.regime = r.key) AS selection_count
            FROM eci_file_selection_regime r
            ORDER BY r.position
            """
        )
    ).all()

    selections_out = _selection_rows(db)

    departure_rows = db.execute(
        text(
            """
            SELECT d.date, d.person_slug, p.name, d.office, d.how, d.notes, d.entry_ids
            FROM eci_file_departure d JOIN eci_file_person p ON p.slug = d.person_slug
            ORDER BY d.date ASC, d.id ASC
            """
        )
    ).all()

    cited_ids = (
        [eid for s in selections_out for eid in s["entry_ids"]]
        + [eid for r in regime_rows for eid in (r.entry_ids or [])]
        + [eid for d in departure_rows for eid in (d.entry_ids or [])]
    )

    return {
        "regimes": [
            {
                "key": r.key,
                "label": r.label,
                "from_date": r.from_date,
                "to_date": r.to_date,
                "rule": r.rule,
                "panel": list(r.panel or []),
                "entry_ids": list(r.entry_ids or []),
                "notes": r.notes,
                "selection_count": r.selection_count,
            }
            for r in regime_rows
        ],
        "selections": selections_out,
        "departures": [
            {
                "date": d.date,
                "person_slug": d.person_slug,
                "name": d.name,
                "office": d.office,
                "how": d.how,
                "notes": d.notes,
                "entry_ids": list(d.entry_ids or []),
            }
            for d in departure_rows
        ],
        "entries_index": _entry_refs(db, cited_ids),
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
                (SELECT count(*) FROM eci_file_entry WHERE kind <> 'person') AS dated_entries,
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
            # launch fixdata S9: the timeline lists dated entries only (kind <> 'person'); `entries`
            # above also counts the 30 `kind='person'` profiles, which is why the front page and the
            # timeline must read `dated_entries` for "N sourced entries", not `entries`.
            "dated_entries": counts_row.dated_entries,
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
    if "before" in stages and "left_off" in stages:
        # launch fixdata B2: a draft entry can report the left-off count directly (e.g. Bihar's "65
        # lakh"), which need not be the same as `before` minus the (often separately rounded) `draft`
        # figure. Prefer it over the subtraction whenever the record carries one.
        count = stages["left_off"]["electors"]
        draft_left_off = build(("before", "left_off"), count, "before")
    elif "before" in stages and "draft" in stages:
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


def _date_key_asc(d: date | None) -> tuple:
    return (1, 0) if d is None else (0, d.toordinal())


def _date_key_desc(d: date | None) -> tuple:
    return (1, 0) if d is None else (0, -d.toordinal())


def _load_cards(db: Session, ids: list[str]) -> list[dict]:
    """EciEntryCard payloads for exactly these ids, in the given order (dedup, drops unknown ids).
    Three queries: base columns, people, and a citation count with a lateral lead citation."""
    ordered = list(dict.fromkeys(ids))
    if not ordered:
        return []

    base_rows = db.execute(
        text(
            """
            SELECT id, kind, date, date_precision, title, summary, status, lane, attributed_to,
                   check_status
            FROM eci_file_entry WHERE id = ANY(:ids)
            """
        ),
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

    counts_by_entry: dict[str, int] = {}
    lead_by_entry: dict[str, dict | None] = {}
    for r in db.execute(
        text(
            """
            SELECT e.id AS entry_id, c.n AS citation_count, lead.url, lead.publisher, lead.title,
                   lead.published, lead.tier, lead.archive_url, lead.quote
            FROM eci_file_entry e
            JOIN LATERAL (SELECT count(*) AS n FROM eci_file_citation WHERE entry_id = e.id) c ON true
            LEFT JOIN LATERAL (
                SELECT sr.native_url AS url, cit.publisher, cit.title, cit.published, cit.tier,
                       cit.archive_url, cit.quote
                FROM eci_file_citation cit JOIN source_ref sr ON sr.id = cit.source_ref_id
                WHERE cit.entry_id = e.id ORDER BY cit.position LIMIT 1
            ) lead ON true
            WHERE e.id = ANY(:ids)
            """
        ),
        {"ids": ordered},
    ):
        counts_by_entry[r.entry_id] = r.citation_count
        lead_by_entry[r.entry_id] = (
            {
                "position": 1,
                "url": r.url,
                "publisher": r.publisher,
                "title": r.title,
                "published": r.published,
                "tier": r.tier,
                "archive_url": r.archive_url,
                "quote": r.quote,
            }
            if r.url is not None
            else None
        )

    out = []
    for eid in ordered:
        r = by_id.get(eid)
        if r is None:
            continue
        out.append(
            {
                "id": r.id,
                "kind": r.kind,
                "date": r.date,
                "date_precision": r.date_precision,
                "title": r.title,
                "summary": r.summary,
                "status": r.status,
                "lane": r.lane,
                "attributed_to": r.attributed_to,
                "check_status": r.check_status,
                "people": people_by_entry.get(eid, []),
                "citation_count": counts_by_entry.get(eid, 0),
                "lead_citation": lead_by_entry.get(eid),
            }
        )
    return out


def _load_entry_refs(db: Session, ids: list[str]) -> dict[str, dict]:
    """EciEntryRef payloads (with `check_status`), keyed by id. A phase 5 sibling of `_entry_refs`
    (phase 3/4), which keeps its own shape so existing callers are unaffected."""
    ordered = list(dict.fromkeys(ids))
    if not ordered:
        return {}
    rows = db.execute(
        text(
            "SELECT id, title, date, date_precision, status, check_status "
            "FROM eci_file_entry WHERE id = ANY(:ids)"
        ),
        {"ids": ordered},
    ).all()
    return {
        r.id: {
            "id": r.id,
            "title": r.title,
            "date": r.date,
            "date_precision": r.date_precision,
            "status": r.status,
            "check_status": r.check_status,
        }
        for r in rows
    }


def objections(db: Session) -> dict:
    """`/eci-files/objections` — the fourteen: 11 identified objections plus the report/response."""
    meta_row = db.execute(
        text(
            "SELECT missing, notes, report_entry_id, response_entry_id "
            "FROM eci_file_objection_meta WHERE id = 1"
        )
    ).first()

    obj_rows = db.execute(
        text(
            "SELECT n, date, date_precision, concerns, followed_by, public "
            "FROM eci_file_objection ORDER BY n"
        )
    ).all()

    by_objection: dict[int, list[dict]] = defaultdict(list)
    for r in db.execute(
        text(
            """
            SELECT op.n, p.slug, p.name
            FROM eci_file_objection_person op JOIN eci_file_person p ON p.slug = op.person_slug
            ORDER BY op.n, op.position
            """
        )
    ):
        by_objection[r.n].append({"slug": r.slug, "name": r.name})

    entries_by_objection: dict[int, list[str]] = defaultdict(list)
    for r in db.execute(
        text("SELECT n, entry_id FROM eci_file_objection_entry ORDER BY n, position")
    ):
        entries_by_objection[r.n].append(r.entry_id)

    followed_by_ids: dict[int, list[str]] = {}
    ref_ids: list[str] = [eid for ids in entries_by_objection.values() for eid in ids]
    for row in obj_rows:
        if row.followed_by:
            ids = [
                tok
                for tok in re.findall(r"\(([^)]+)\)", row.followed_by)
                if not re.fullmatch(r"objection \d+", tok)
            ]
            followed_by_ids[row.n] = ids
            ref_ids.extend(ids)
    if meta_row is not None and meta_row.report_entry_id:
        ref_ids.append(meta_row.report_entry_id)

    refs = _load_entry_refs(db, ref_ids)
    all_person_slugs = {p["slug"] for rows in by_objection.values() for p in rows}
    photos = _photo_map(db, all_person_slugs)

    response_card = None
    if meta_row is not None and meta_row.response_entry_id:
        cards = _load_cards(db, [meta_row.response_entry_id])
        response_card = cards[0] if cards else None

    objections_out = [
        {
            "n": row.n,
            "date": row.date,
            "date_precision": row.date_precision,
            "by": [
                {"slug": p["slug"], "name": p["name"], "photo": photos.get(p["slug"])}
                for p in by_objection.get(row.n, [])
            ],
            "concerns": row.concerns,
            "followed_by": row.followed_by,
            "followed_by_refs": [
                refs[eid] for eid in followed_by_ids.get(row.n, []) if eid in refs
            ],
            "public": row.public,
            "entries": [refs[eid] for eid in entries_by_objection.get(row.n, []) if eid in refs],
        }
        for row in obj_rows
    ]

    person_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "joint": 0})
    names_by_slug: dict[str, str] = {}
    for row in obj_rows:
        people = by_objection.get(row.n, [])
        joint = len(people) > 1
        for p in people:
            names_by_slug[p["slug"]] = p["name"]
            person_counts[p["slug"]]["count"] += 1
            if joint:
                person_counts[p["slug"]]["joint"] += 1

    by_person = sorted(
        (
            {
                "slug": slug,
                "name": names_by_slug[slug],
                "photo": photos.get(slug),
                "count": c["count"],
                "joint": c["joint"],
            }
            for slug, c in person_counts.items()
        ),
        key=lambda p: (-p["count"], p["name"]),
    )

    identified = len(obj_rows)
    missing = meta_row.missing if meta_row is not None else 0
    return {
        "identified": identified,
        "missing": missing,
        "reported_total": identified + missing,
        "notes": meta_row.notes if meta_row is not None else None,
        "report": (
            refs.get(meta_row.report_entry_id)
            if meta_row is not None and meta_row.report_entry_id
            else None
        ),
        "response": response_card,
        "objections": objections_out,
        "by_person": by_person,
    }


def assemble_answer_rows(
    pair_charge_ids: set[str],
    also_recorded_ids: set[str],
    claim_ids: list[str],
    response_links: dict[str, str],
    unpaired_ids: set[str],
) -> list[dict]:
    """Pure (no DB): a synthesised, `curated=False` answer row for every claim or response target
    the curated `pairs.json` rows don't already cover — PHASE5-SPEC.md section 4.3's completeness
    rule. A new claim, or a response nobody paired yet, can never go missing from `/eci-files/answers`
    just because a curated file wasn't updated.

    `pair_charge_ids` / `also_recorded_ids` are every curated pair's `charge_id`s and
    `also_recorded_as` ids. `claim_ids` is every `status='claim'` entry id. `response_links` maps a
    `status='response'` entry id to the entry id its `response_to` names. `unpaired_ids` is every id
    already recorded in `eci_file_unpaired_response`. A row's `responses` come from `response_links`;
    `record`, `related` and `note` are always empty.
    """
    covered = pair_charge_ids | also_recorded_ids | unpaired_ids
    response_targets = list(dict.fromkeys(response_links.values()))

    seen: set[str] = set()
    rows: list[dict] = []
    for charge_id in [*claim_ids, *response_targets]:
        if charge_id in covered or charge_id in seen:
            continue
        seen.add(charge_id)
        responses = [rid for rid, target in response_links.items() if target == charge_id]
        rows.append(
            {
                "charge_id": charge_id,
                # A synthesised row always covers a claim or an answered response target -- never a
                # curated defence/analysis pair, which only pairs.json can classify (S11 below).
                "kind": "charge",
                "also_recorded_as": [],
                "response_ids": responses,
                "record_ids": [],
                "related": [],
                "note": None,
                "curated": False,
            }
        )
    return rows


def finalize_answer_rows(rows: list[dict]) -> tuple[list[dict], dict]:
    """Pure (no DB): sorts assembled answer rows (charge date descending, then id) and computes the
    `view=all` counts, always on the full set regardless of what the caller later filters to. Each
    row is `{"charge": EciEntryCard-shaped dict, "responses": [...], "record": [...], "kind": ..., ...}`.

    launch fixdata S11: a pair's `kind` classifies it as a `charge` against the Commission or a named
    person (the default), a `defence` (e.g. a party spokesperson defending the Commission) or an
    `analysis` (e.g. PRS's bill analysis) -- neither of the latter two is a charge, so `counts` (and
    the `no-response` filter below) are computed over `kind == "charge"` rows only. Both still show up
    in `rows` for `view=all`, tagged with their `kind`, so the page can group them separately.
    """
    ordered = sorted(rows, key=lambda r: (_date_key_desc(r["charge"]["date"]), r["charge"]["id"]))
    charges = [r for r in ordered if r["kind"] == "charge"]
    with_response = sum(1 for r in charges if r["responses"])
    with_record = sum(1 for r in charges if r["record"])
    counts = {
        "rows": len(charges),
        "with_response": with_response,
        "without_response": len(charges) - with_response,
        "with_record": with_record,
    }
    return ordered, counts


def filter_answer_rows(rows: list[dict], view: str) -> list[dict]:
    """Pure (no DB): the `?view=` filter over already-sorted rows."""
    if view == "no-response":
        return [r for r in rows if r["kind"] == "charge" and not r["responses"]]
    if view == "with-record":
        return [r for r in rows if r["record"]]
    return rows


def answers(db: Session, *, view: str = "all") -> dict:
    """`/eci-files/answers` — every charge or Commission action beside its response, plus the
    synthesised completeness rows (`assemble_answer_rows`). `counts` is always computed on the full
    (`view=all`) set, whatever `view` is requested."""
    pair_rows = db.execute(
        text("SELECT charge_id, note, kind FROM eci_file_pair ORDER BY position")
    ).all()

    items_by_charge: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in db.execute(
        text(
            "SELECT charge_id, entry_id, role, why FROM eci_file_pair_item "
            "ORDER BY charge_id, role, position"
        )
    ):
        items_by_charge[r.charge_id][r.role].append({"entry_id": r.entry_id, "why": r.why})

    unpaired_rows = db.execute(
        text("SELECT response_entry_id, note FROM eci_file_unpaired_response")
    ).all()
    unpaired_ids = {r.response_entry_id for r in unpaired_rows}

    claim_ids = [
        r.id for r in db.execute(text("SELECT id FROM eci_file_entry WHERE status = 'claim'"))
    ]
    response_links = {
        r.id: r.response_to
        for r in db.execute(
            text(
                "SELECT id, response_to FROM eci_file_entry "
                "WHERE status = 'response' AND response_to IS NOT NULL"
            )
        )
    }

    pair_charge_ids = {r.charge_id for r in pair_rows}
    also_recorded_ids = {
        item["entry_id"] for rows in items_by_charge.values() for item in rows.get("same", [])
    }

    curated_rows = [
        {
            "charge_id": r.charge_id,
            "also_recorded_as": [i["entry_id"] for i in items_by_charge[r.charge_id].get("same", [])],
            "response_ids": [
                i["entry_id"] for i in items_by_charge[r.charge_id].get("response", [])
            ],
            "record_ids": [i["entry_id"] for i in items_by_charge[r.charge_id].get("record", [])],
            "related": items_by_charge[r.charge_id].get("related", []),
            "note": r.note,
            "kind": r.kind,
            "curated": True,
        }
        for r in pair_rows
    ]

    synthesised_rows = assemble_answer_rows(
        pair_charge_ids, also_recorded_ids, claim_ids, response_links, unpaired_ids
    )
    all_rows = curated_rows + synthesised_rows

    entry_ids: list[str] = []
    for row in all_rows:
        entry_ids.append(row["charge_id"])
        entry_ids.extend(row["response_ids"])
        entry_ids.extend(row["record_ids"])
        entry_ids.extend(row["also_recorded_as"])
        entry_ids.extend(i["entry_id"] for i in row["related"])
    entry_ids.extend(unpaired_ids)

    cards = {c["id"]: c for c in _load_cards(db, entry_ids)}
    refs = _load_entry_refs(db, entry_ids)

    out_rows = []
    for row in all_rows:
        charge_card = cards.get(row["charge_id"])
        if charge_card is None:
            continue
        responses = sorted(
            (cards[r] for r in row["response_ids"] if r in cards),
            key=lambda c: _date_key_asc(c["date"]),
        )
        record = [cards[r] for r in row["record_ids"] if r in cards]
        related = [
            {"entry": refs[i["entry_id"]], "why": i["why"]}
            for i in row["related"]
            if i["entry_id"] in refs
        ]
        out_rows.append(
            {
                "charge": charge_card,
                "also_recorded_as": [refs[eid] for eid in row["also_recorded_as"] if eid in refs],
                "responses": responses,
                "record": record,
                "related": related,
                "note": row["note"],
                "curated": row["curated"],
                "kind": row["kind"],
            }
        )

    ordered_rows, counts = finalize_answer_rows(out_rows)
    filtered = filter_answer_rows(ordered_rows, view)

    return {
        "counts": counts,
        "rows": filtered,
        "unpaired_responses": [
            {"response": cards[r.response_entry_id], "note": r.note}
            for r in unpaired_rows
            if r.response_entry_id in cards
        ],
    }


def rules(db: Session) -> dict:
    """`/eci-files/rules` — every `kind='rule'` entry, date descending, with the before-and-after
    diffs available for each."""
    rule_entry_ids = [
        r.id
        for r in db.execute(
            text(
                "SELECT id FROM eci_file_entry WHERE kind = 'rule' ORDER BY date DESC NULLS LAST, id"
            )
        )
    ]
    cards = {c["id"]: c for c in _load_cards(db, rule_entry_ids)}

    diffs_by_rule: dict[str, list[dict]] = defaultdict(list)
    all_diffs: list[dict] = []
    for r in db.execute(
        text(
            "SELECT id, title, text_status, rule_entry_id FROM eci_file_rule_diff ORDER BY position"
        )
    ):
        ref = {"id": r.id, "title": r.title, "text_status": r.text_status}
        diffs_by_rule[r.rule_entry_id].append(ref)
        all_diffs.append(ref)

    rows = [
        {"entry": cards[eid], "diffs": diffs_by_rule.get(eid, [])}
        for eid in rule_entry_ids
        if eid in cards
    ]

    with_diff = db.execute(
        text("SELECT count(DISTINCT rule_entry_id) FROM eci_file_rule_diff")
    ).scalar_one()

    return {
        "rules": rows,
        "diffs": all_diffs,
        "counts": {"rules": len(rule_entry_ids), "with_diff": with_diff, "diffs": len(all_diffs)},
    }


def rule_diff(db: Session, diff_id: str) -> dict | None:
    """`/eci-files/rules/diffs/{id}` — one before-and-after comparison. The API returns lines; the
    diff itself is computed on the web, next to its renderer."""
    row = db.execute(
        text(
            """
            SELECT id, title, document, rule_entry_id, before_label, after_label, before_lines,
                   after_lines, before_status, after_status, text_status, excerpt,
                   quoted_lines_before, quoted_lines_after, source_urls, note
            FROM eci_file_rule_diff WHERE id = :id
            """
        ),
        {"id": diff_id},
    ).first()
    if row is None:
        return None

    rule_cards = _load_cards(db, [row.rule_entry_id])
    related_ids = [
        r.entry_id
        for r in db.execute(
            text("SELECT entry_id FROM eci_file_rule_diff_entry WHERE diff_id = :id"),
            {"id": diff_id},
        )
    ]
    refs = _load_entry_refs(db, related_ids)

    return {
        "id": row.id,
        "title": row.title,
        "document": row.document,
        "rule_entry": rule_cards[0] if rule_cards else None,
        "before_label": row.before_label,
        "after_label": row.after_label,
        "before": list(row.before_lines or []),
        "after": list(row.after_lines or []),
        "before_status": row.before_status,
        "after_status": row.after_status,
        "text_status": row.text_status,
        "excerpt": row.excerpt,
        "quoted_lines_before": list(row.quoted_lines_before or []),
        "quoted_lines_after": list(row.quoted_lines_after or []),
        "source_urls": list(row.source_urls or []),
        "note": row.note,
        "related": [refs[eid] for eid in related_ids if eid in refs],
    }


def courts(db: Session) -> dict:
    """`/eci-files/courts` — the five cases, file order, with their step counts and latest item."""
    case_rows = db.execute(
        text(
            "SELECT slug, short_name, case_entry_id, court, short_status, status_note "
            "FROM eci_file_case ORDER BY position"
        )
    ).all()

    items_by_case: dict[str, list[dict]] = defaultdict(list)
    for r in db.execute(
        text(
            """
            SELECT ci.case_slug, ci.entry_id, ci.role, e.date
            FROM eci_file_case_item ci JOIN eci_file_entry e ON e.id = ci.entry_id
            """
        )
    ):
        items_by_case[r.case_slug].append({"entry_id": r.entry_id, "role": r.role, "date": r.date})

    case_entry_ids = [r.case_entry_id for r in case_rows]
    case_entry_rows = {
        r.id: r
        for r in db.execute(
            text("SELECT id, title, details FROM eci_file_entry WHERE id = ANY(:ids)"),
            {"ids": case_entry_ids},
        )
    }

    latest_ids: list[str] = []
    per_case: list[dict] = []
    for r in case_rows:
        items = sorted(
            items_by_case.get(r.slug, []),
            key=lambda i: (_date_key_asc(i["date"]), i["entry_id"]),
        )
        non_related = [i for i in items if i["role"] != "related"]
        latest_item = non_related[-1] if non_related else None
        if latest_item is not None:
            latest_ids.append(latest_item["entry_id"])
        entry_row = case_entry_rows.get(r.case_entry_id)
        details = (entry_row.details if entry_row is not None else None) or {}
        per_case.append(
            {
                "slug": r.slug,
                "short_name": r.short_name,
                "title": entry_row.title if entry_row is not None else "",
                "case_number": details.get("case_number"),
                "court": r.court,
                "short_status": r.short_status,
                "status_note": r.status_note,
                "item_count": len(items),
                "order_count": sum(1 for i in items if i["role"] in ("order", "judgment")),
                "first_date": items[0]["date"] if items else None,
                "last_date": items[-1]["date"] if items else None,
                "_latest_entry_id": latest_item["entry_id"] if latest_item is not None else None,
            }
        )

    refs = _load_entry_refs(db, latest_ids)
    for c in per_case:
        c["latest"] = refs.get(c.pop("_latest_entry_id"))

    other_court_entries = db.execute(
        text(
            """
            SELECT count(*) FROM eci_file_entry e
            WHERE e.lane = 'courts' AND e.kind <> 'case'
              AND e.id NOT IN (SELECT entry_id FROM eci_file_case_item)
            """
        )
    ).scalar_one()

    return {"cases": per_case, "other_court_entries": other_court_entries}


def case_page(db: Session, slug: str) -> dict | None:
    """`/eci-files/courts/{slug}` — one case, order by order (entry date ascending, then id)."""
    row = db.execute(
        text(
            "SELECT slug, short_name, case_entry_id, court, short_status, status_note, parties "
            "FROM eci_file_case WHERE slug = :slug"
        ),
        {"slug": slug},
    ).first()
    if row is None:
        return None

    case_entry = entry(db, row.case_entry_id)
    details = (case_entry or {}).get("details") or {}

    item_rows = db.execute(
        text("SELECT entry_id, role, note FROM eci_file_case_item WHERE case_slug = :slug"),
        {"slug": slug},
    ).all()
    cards = {c["id"]: c for c in _load_cards(db, [r.entry_id for r in item_rows])}
    items = [
        {"role": r.role, "note": r.note, "entry": cards[r.entry_id]}
        for r in item_rows
        if r.entry_id in cards
    ]
    items.sort(key=lambda i: (_date_key_asc(i["entry"]["date"]), i["entry"]["id"]))

    parties = row.parties or {}
    return {
        "slug": row.slug,
        "short_name": row.short_name,
        "court": row.court,
        "short_status": row.short_status,
        "status_note": row.status_note,
        "case": case_entry,
        "case_name": details.get("case_name") or (case_entry or {}).get("title"),
        "case_number": details.get("case_number"),
        "bench": details.get("bench"),
        "citation": details.get("citation"),
        "parties": {
            "petitioners": list(parties.get("petitioners", [])),
            "respondents": list(parties.get("respondents", [])),
        },
        "items": items,
    }


def entry_context(db: Session, entry_id: str) -> dict:
    """Every curated pair, case membership, objection and rule diff this entry is part of. One query
    per context kind, each on an indexed `entry_id` column. Synthesised answer rows are not included —
    the drawer already shows `responses`/`response_to` for those."""
    charge_ids: list[str] = []
    role_by_charge: dict[str, str] = {}

    def _add_charge(charge_id: str, role: str) -> None:
        if charge_id not in role_by_charge:
            charge_ids.append(charge_id)
            role_by_charge[charge_id] = role

    if db.execute(
        text("SELECT 1 FROM eci_file_pair WHERE charge_id = :id"), {"id": entry_id}
    ).first():
        _add_charge(entry_id, "charge")

    for r in db.execute(
        text("SELECT charge_id, role FROM eci_file_pair_item WHERE entry_id = :id"),
        {"id": entry_id},
    ):
        _add_charge(r.charge_id, r.role)

    pairs: list[dict] = []
    if charge_ids:
        notes_by_charge = {
            r.charge_id: r.note
            for r in db.execute(
                text("SELECT charge_id, note FROM eci_file_pair WHERE charge_id = ANY(:ids)"),
                {"ids": charge_ids},
            )
        }
        item_rows = db.execute(
            text(
                "SELECT charge_id, entry_id, role FROM eci_file_pair_item "
                "WHERE charge_id = ANY(:ids)"
            ),
            {"ids": charge_ids},
        ).all()
        refs = _load_entry_refs(db, [r.entry_id for r in item_rows] + charge_ids)

        responses_by_charge: dict[str, list[dict]] = defaultdict(list)
        record_by_charge: dict[str, list[dict]] = defaultdict(list)
        for r in item_rows:
            if r.role == "response" and r.entry_id in refs:
                responses_by_charge[r.charge_id].append(refs[r.entry_id])
            elif r.role == "record" and r.entry_id in refs:
                record_by_charge[r.charge_id].append(refs[r.entry_id])

        pairs = [
            {
                "charge": refs[cid],
                "role": role_by_charge[cid],
                "responses": responses_by_charge.get(cid, []),
                "record": record_by_charge.get(cid, []),
                "note": notes_by_charge.get(cid),
            }
            for cid in charge_ids
            if cid in refs
        ]

    case_row = db.execute(
        text(
            """
            SELECT c.slug, c.short_name, ci.role
            FROM eci_file_case_item ci JOIN eci_file_case c ON c.slug = ci.case_slug
            WHERE ci.entry_id = :id
            """
        ),
        {"id": entry_id},
    ).first()
    if case_row is None:
        case_row = db.execute(
            text(
                "SELECT slug, short_name, 'case' AS role FROM eci_file_case "
                "WHERE case_entry_id = :id"
            ),
            {"id": entry_id},
        ).first()
    case_ctx = (
        {"slug": case_row.slug, "short_name": case_row.short_name, "role": case_row.role}
        if case_row is not None
        else None
    )

    objections_ctx = [
        {"n": r.n, "concerns": r.concerns}
        for r in db.execute(
            text(
                """
                SELECT o.n, o.concerns
                FROM eci_file_objection_entry oe JOIN eci_file_objection o ON o.n = oe.n
                WHERE oe.entry_id = :id ORDER BY o.n
                """
            ),
            {"id": entry_id},
        )
    ]

    # The entry's own diff (its `rule_entry_id`) comes first; a diff that merely names it in
    # `related_entry_ids` comes after, in position order.
    own_diffs = [
        {"id": r.id, "title": r.title, "text_status": r.text_status}
        for r in db.execute(
            text(
                "SELECT id, title, text_status FROM eci_file_rule_diff "
                "WHERE rule_entry_id = :id ORDER BY position"
            ),
            {"id": entry_id},
        )
    ]
    own_diff_ids = {d["id"] for d in own_diffs}
    related_diffs = [
        {"id": r.id, "title": r.title, "text_status": r.text_status}
        for r in db.execute(
            text(
                """
                SELECT rd.id, rd.title, rd.text_status
                FROM eci_file_rule_diff_entry rde JOIN eci_file_rule_diff rd ON rd.id = rde.diff_id
                WHERE rde.entry_id = :id ORDER BY rd.position
                """
            ),
            {"id": entry_id},
        )
        if r.id not in own_diff_ids
    ]
    rule_diffs_ctx = own_diffs + related_diffs

    return {"pairs": pairs, "case": case_ctx, "objections": objections_ctx, "rule_diffs": rule_diffs_ctx}


def entry_detail(db: Session, entry_id: str) -> dict | None:
    """`/eci-files/entries/{id}` — the full entry plus its phase 5 `context`."""
    base = entry(db, entry_id)
    if base is None:
        return None
    return {**base, "context": entry_context(db, entry_id)}


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
