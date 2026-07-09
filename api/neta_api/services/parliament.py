"""Aggregates for the "Parliament functioning" section — the institutional lens over the questions data.

Read-time GROUP BYs over parliamentary_question (+ the ministry_theme map). All current rows are the 18th
Lok Sabha; queries are scoped by the LS house_id so Rajya Sabha extends cleanly once its questions land.
Everything is cached by the web's 1-hour ISR, so per-request compute is near-zero.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# One ministry->theme join, reused everywhere. ministry casing/spacing is normalized to match the map key.
_JOIN_THEME = "LEFT JOIN ministry_theme mt ON mt.ministry_key = lower(btrim(pq.ministry))"


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
