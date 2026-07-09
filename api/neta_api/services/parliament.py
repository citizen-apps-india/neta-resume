"""Aggregates for the "Parliament functioning" section — the institutional lens over the questions data.

Read-time GROUP BYs over parliamentary_question (+ the ministry_theme map). All current rows are the 18th
Lok Sabha; queries are scoped by the LS house_id so Rajya Sabha extends cleanly once its questions land.
Everything is cached by the web's 1-hour ISR, so per-request compute is near-zero.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.orm import Session

# One ministry->theme join, reused everywhere. ministry casing/spacing is normalized to match the map key.
_JOIN_THEME = "LEFT JOIN ministry_theme mt ON mt.ministry_key = lower(btrim(pq.ministry))"

# Freeform user text → tsquery. websearch_to_tsquery never raises on odd input (unbalanced quotes, bare
# operators), so it's safe to feed a raw search box; it supports quoted phrases and `-exclude` too.
_TSQ = "websearch_to_tsquery('english', :q)"


def _ls_house(db: Session) -> tuple[int, str]:
    row = db.execute(text("SELECT id, name FROM house WHERE code = 'LS'")).one()
    return row.id, row.name


def parliament_stats(db: Session) -> dict:
    hid, house_name = _ls_house(db)
    p = {"hid": hid}

    totals = db.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM parliamentary_question WHERE house_id = :hid) AS total_questions,
              (SELECT count(*) FROM parliamentary_debate   WHERE house_id = :hid) AS total_debates,
              (SELECT count(DISTINCT person_id) FROM parliamentary_question WHERE house_id = :hid) AS active_mps
            """
        ),
        p,
    ).one()

    themes = db.execute(
        text(
            f"""
            SELECT COALESCE(mt.theme, 'Other') AS theme, count(*) AS n
            FROM parliamentary_question pq {_JOIN_THEME}
            WHERE pq.house_id = :hid
            GROUP BY 1 ORDER BY n DESC
            """
        ),
        p,
    ).all()

    top_ministries = db.execute(
        text(
            f"""
            SELECT pq.ministry AS ministry, COALESCE(mt.theme, 'Other') AS theme, count(*) AS n
            FROM parliamentary_question pq {_JOIN_THEME}
            WHERE pq.house_id = :hid AND pq.ministry IS NOT NULL
            GROUP BY 1, 2 ORDER BY n DESC LIMIT 12
            """
        ),
        p,
    ).all()

    most_active = db.execute(
        text(
            f"""
            WITH q AS (
                SELECT person_id, count(*) AS n
                FROM parliamentary_question WHERE house_id = :hid
                GROUP BY 1 ORDER BY n DESC LIMIT 10
            )
            SELECT q.person_id AS id, p.display_name, p.photo_url, q.n AS n,
                   (SELECT COALESCE(mt.theme, 'Other')
                      FROM parliamentary_question pq {_JOIN_THEME}
                      WHERE pq.person_id = q.person_id
                      GROUP BY 1 ORDER BY count(*) DESC LIMIT 1) AS top_theme
            FROM q JOIN person p ON p.id = q.person_id
            ORDER BY q.n DESC
            """
        ),
        p,
    ).all()

    return {
        "house": house_name,
        "total_questions": totals.total_questions,
        "total_debates": totals.total_debates,
        "active_mps": totals.active_mps,
        "themes": [{"theme": r.theme, "count": r.n} for r in themes],
        "top_ministries": [{"ministry": r.ministry, "theme": r.theme, "count": r.n} for r in top_ministries],
        "most_active": [
            {"id": r.id, "display_name": r.display_name, "photo_url": r.photo_url,
             "count": r.n, "top_theme": r.top_theme}
            for r in most_active
        ],
    }


def ministries(db: Session) -> list[dict]:
    """The full ranked ministry list (name, theme, question count) for the /parliament/ministries page."""
    hid, _ = _ls_house(db)
    rows = db.execute(
        text(
            f"""
            SELECT pq.ministry AS ministry, COALESCE(mt.theme, 'Other') AS theme, count(*) AS n
            FROM parliamentary_question pq {_JOIN_THEME}
            WHERE pq.house_id = :hid AND pq.ministry IS NOT NULL
            GROUP BY 1, 2 ORDER BY n DESC
            """
        ),
        {"hid": hid},
    ).all()
    return [{"ministry": r.ministry, "theme": r.theme, "count": r.n} for r in rows]


def search_records(
    db: Session,
    q: str,
    kind: str | None = None,
    theme: str | None = None,
    limit: int = 30,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Full-text topic search over question subjects + debate titles (18th Lok Sabha).

    Returns (page, total). `kind` filters to 'question'/'debate' (default both). `theme` (a policy theme)
    filters via the ministry_theme map — debates carry no ministry, so a theme filter narrows to questions.
    Ranked by ts_rank, then most-recent first.
    """
    hid, _ = _ls_house(db)
    params: dict = {"hid": hid, "q": q, "limit": limit, "offset": offset}

    want_q = kind in (None, "question")
    want_d = kind in (None, "debate") and not theme  # a theme filter excludes ministry-less debates
    parts: list[str] = []

    if want_q:
        theme_pred = ""
        if theme:
            theme_pred = "AND COALESCE(mt.theme, 'Other') = :theme"
            params["theme"] = theme
        parts.append(
            f"""
            SELECT 'question' AS kind, pq.id AS id, pq.subject AS title, pq.person_id AS mp_id,
                   pq.ministry AS ministry, COALESCE(mt.theme, 'Other') AS theme, pq.asked_date AS dt,
                   ts_rank(to_tsvector('english', coalesce(pq.subject, '')), {_TSQ}) AS rank
            FROM parliamentary_question pq {_JOIN_THEME}
            WHERE pq.house_id = :hid
              AND to_tsvector('english', coalesce(pq.subject, '')) @@ {_TSQ}
              {theme_pred}
            """
        )
    if want_d:
        parts.append(
            f"""
            SELECT 'debate' AS kind, pd.id AS id, pd.title AS title, pd.person_id AS mp_id,
                   NULL AS ministry, NULL AS theme, pd.debate_date AS dt,
                   ts_rank(to_tsvector('english', coalesce(pd.title, '')), {_TSQ}) AS rank
            FROM parliamentary_debate pd
            WHERE pd.house_id = :hid
              AND to_tsvector('english', coalesce(pd.title, '')) @@ {_TSQ}
            """
        )
    if not parts:
        return [], 0

    inner = " UNION ALL ".join(f"({p})" for p in parts)
    rows = db.execute(
        text(
            f"""
            SELECT h.kind, h.id, h.title, h.mp_id, per.display_name AS mp_name,
                   h.ministry, h.theme, h.dt
            FROM ({inner}) h JOIN person per ON per.id = h.mp_id
            ORDER BY h.rank DESC, h.dt DESC NULLS LAST, h.id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).all()
    total = db.execute(text(f"SELECT count(*) FROM ({inner}) h"), params).scalar() or 0

    items = [
        {"kind": r.kind, "id": r.id, "title": r.title, "mp_id": r.mp_id, "mp_name": r.mp_name,
         "ministry": r.ministry, "theme": r.theme, "date": r.dt}
        for r in rows
    ]
    return items, int(total)


def _dense_months(start: str, end: str) -> list[str]:
    """Inclusive list of 'YYYY-MM' from start to end, so the trends stack has no gaps between sittings."""
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    out: list[str] = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def trends(db: Session) -> dict:
    """Monthly question volume split by policy theme (18th Lok Sabha) — how the House's attention shifted.

    Months are dense (zero-filled between sittings) so the stacked area stays continuous; themes are ordered
    by total volume to match the dashboard donut.
    """
    hid, house_name = _ls_house(db)
    rows = db.execute(
        text(
            f"""
            SELECT to_char(date_trunc('month', pq.asked_date), 'YYYY-MM') AS ym,
                   COALESCE(mt.theme, 'Other') AS theme, count(*) AS n
            FROM parliamentary_question pq {_JOIN_THEME}
            WHERE pq.house_id = :hid AND pq.asked_date IS NOT NULL
            GROUP BY 1, 2
            """
        ),
        {"hid": hid},
    ).all()

    if not rows:
        return {"house": house_name, "months": [], "totals": [], "series": []}

    by_theme: dict[str, dict[str, int]] = defaultdict(dict)
    theme_totals: dict[str, int] = defaultdict(int)
    yms: set[str] = set()
    for r in rows:
        by_theme[r.theme][r.ym] = r.n
        theme_totals[r.theme] += r.n
        yms.add(r.ym)

    months = _dense_months(min(yms), max(yms))
    ordered = sorted(theme_totals, key=lambda t: theme_totals[t], reverse=True)
    series = [{"theme": t, "points": [by_theme[t].get(m, 0) for m in months]} for t in ordered]
    totals = [sum(by_theme[t].get(m, 0) for t in ordered) for m in months]
    return {"house": house_name, "months": months, "totals": totals, "series": series}
