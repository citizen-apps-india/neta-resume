"""Human review of the cross-house merge queue (person_merge_candidate).
`accept` merges the pair (via merge_cycles._merge); `reject` suppresses it. Backing `neta review …`.
"""

from __future__ import annotations

import json

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_ingest.pipelines.identity import derive_identity_signals, merge_cycles


def list_pending(limit: int = 30) -> None:
    with session_scope() as s:
        rows = s.execute(
            text(
                """
                SELECT c.id, c.person_lo, c.person_hi, c.score,
                       pl.display_name AS lo_name, ph.display_name AS hi_name
                FROM person_merge_candidate c
                JOIN person pl ON pl.id = c.person_lo
                JOIN person ph ON ph.id = c.person_hi
                WHERE c.status = 'pending'
                ORDER BY c.score DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        ).all()
    if not rows:
        print("[review] no pending merge candidates.")
        return
    print(f"[review] {len(rows)} pending (highest score first):")
    for r in rows:
        print(f"  #{r.id}  {r.score}  {r.lo_name} (#{r.person_lo})  <->  {r.hi_name} (#{r.person_hi})")
    print("  inspect: neta review show <id>  ·  accept: neta review accept <id>  ·  reject: neta review reject <id>")


def _print_person(s, pid: int) -> None:
    p = s.execute(
        text("SELECT display_name, birth_year, home_state, relative_name, gender FROM person WHERE id = :i"),
        {"i": pid},
    ).mappings().first()
    if not p:
        print(f"  #{pid}: (merged away)")
        return
    print(f"  #{pid} {p['display_name']}  b.{p['birth_year']}  {p['home_state']}  "
          f"rel={p['relative_name']!r}  {p['gender']}")
    terms = s.execute(
        text(
            """
            SELECT h.name AS house, ot.constituency, tc.eci_election_id AS cycle
            FROM office_term ot JOIN house h ON h.id = ot.house_id
            JOIN term_cycle tc ON tc.id = ot.term_cycle_id
            WHERE ot.person_id = :i ORDER BY tc.start_date
            """
        ),
        {"i": pid},
    ).all()
    for t in terms:
        print(f"       {t.house} · {t.constituency} · {t.cycle}")


def show(cid: int) -> None:
    with session_scope() as s:
        r = s.execute(
            text("SELECT * FROM person_merge_candidate WHERE id = :i"), {"i": cid}
        ).mappings().first()
        if not r:
            print(f"[review] no candidate #{cid}.")
            return
        print(f"Candidate #{cid}  score={r['score']}  band={r['band']}  status={r['status']}")
        for side in ("person_lo", "person_hi"):
            _print_person(s, r[side]) if r[side] else print(f"  {side}: (merged away)")
        print("Evidence:", json.dumps(r["evidence"], indent=2, ensure_ascii=False))


def _survivor(s, lo: int, hi: int) -> tuple[int, int]:
    """(survivor, loser): the person with the more-recent latest office term survives."""
    lt = dict(
        s.execute(
            text(
                """
                SELECT ot.person_id AS pid, max(COALESCE(tc.start_date, DATE '2099-12-31')) AS lt
                FROM office_term ot JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                WHERE ot.person_id = ANY(:ids) GROUP BY ot.person_id
                """
            ),
            {"ids": [lo, hi]},
        ).all()
    )
    return (lo, hi) if (lt.get(lo) or "") >= (lt.get(hi) or "") else (hi, lo)


def accept(cid: int, by: str = "cli") -> None:
    with session_scope() as s:
        r = s.execute(
            text("SELECT person_lo, person_hi, status FROM person_merge_candidate WHERE id = :i"),
            {"i": cid},
        ).mappings().first()
        if not r:
            print(f"[review] no candidate #{cid}.")
            return
        if r["status"] != "pending":
            print(f"[review] #{cid} already {r['status']}.")
            return
        if r["person_lo"] is None or r["person_hi"] is None:
            print(f"[review] #{cid} is stale (a side was merged away).")
            return
        surv, loser = _survivor(s, r["person_lo"], r["person_hi"])
        merge_cycles._merge(s, {loser: surv})
        merge_cycles._set_cycle_status(s)
        merge_cycles._detect_switches(s)
        s.execute(
            text("UPDATE person_merge_candidate SET status='accepted', decided_by=:by, decided_at=now() "
                 "WHERE id=:i"),
            {"by": by, "i": cid},
        )
        print(f"[review] #{cid} accepted — merged #{loser} into #{surv}.")
    derive_identity_signals.run()


def reject(cid: int, by: str = "cli", reason: str | None = None) -> None:
    with session_scope() as s:
        decided_by = f"{by}: {reason}" if reason else by  # keep the reason with the decider (no extra column)
        n = s.execute(
            text("UPDATE person_merge_candidate SET status='rejected', decided_by=:by, decided_at=now() "
                 "WHERE id=:i AND status='pending'"),
            {"by": decided_by, "i": cid},
        ).rowcount
    print(f"[review] #{cid} rejected." if n else f"[review] #{cid} not pending / not found.")
