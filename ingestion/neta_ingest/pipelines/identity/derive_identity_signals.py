"""Refresh the denormalized identity match-features on `person` (home_state, relative_name) from the
sourced truth on affidavit / office_term. Run after the relatives backfill and after every merge — the
cross-house stitcher scores against these columns instead of re-aggregating per pair.

relative_name = the S/o|D/o|W/o relative from the person's most-recent affidavit that has one.
home_state    = the person's modal office_term state (ls_state_code / rs_state_code).
phonetic_key  = metaphone-over-sorted-tokens of the name, for same-sound stitcher blocking.
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_core.transform.names import phonetic_key


def run() -> None:
    with session_scope() as s:
        s.execute(
            text(
                """
                UPDATE person p SET relative_name = sub.rn
                FROM (
                    SELECT DISTINCT ON (a.person_id) a.person_id, a.relative_name AS rn
                    FROM affidavit a
                    WHERE a.relative_name IS NOT NULL AND a.relative_name <> ''
                    ORDER BY a.person_id, a.filed_year DESC
                ) sub
                WHERE p.id = sub.person_id
                """
            )
        )

        # home_state = modal office_term state (ties broken alphabetically for determinism).
        s.execute(
            text(
                """
                UPDATE person p SET home_state = sub.st
                FROM (
                    SELECT DISTINCT ON (person_id) person_id, st
                    FROM (
                        SELECT ot.person_id,
                               COALESCE(ot.ls_state_code, ot.rs_state_code) AS st,
                               count(*) AS n
                        FROM office_term ot
                        WHERE COALESCE(ot.ls_state_code, ot.rs_state_code) IS NOT NULL
                        GROUP BY ot.person_id, COALESCE(ot.ls_state_code, ot.rs_state_code)
                    ) g
                    ORDER BY person_id, n DESC, st
                ) sub
                WHERE p.id = sub.person_id
                """
            )
        )
        # phonetic_key: computed in Python (metaphone), bulk-written via a temp table (recompute each run).
        rows = s.execute(text("SELECT id, normalized_name FROM person WHERE normalized_name <> ''")).all()
        data = [{"id": r.id, "pk": phonetic_key(r.normalized_name)} for r in rows]
        if data:
            s.execute(text("CREATE TEMP TABLE _pk (id bigint PRIMARY KEY, pk text) ON COMMIT DROP"))
            s.execute(text("INSERT INTO _pk (id, pk) VALUES (:id, :pk)"), data)
            s.execute(text("UPDATE person p SET phonetic_key = _pk.pk FROM _pk WHERE p.id = _pk.id"))

        n = s.execute(
            text("SELECT count(*) FROM person WHERE relative_name IS NOT NULL OR home_state IS NOT NULL")
        ).scalar()
    print(f"[derive-signals] refreshed identity features; {n} persons now carry a relative_name/home_state; "
          f"phonetic_key set on {len(data)}.")
