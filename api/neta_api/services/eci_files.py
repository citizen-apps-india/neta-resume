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
