"""Orchestrate onboarding a state assembly — run the proven house-generic sequence over its registry cycles.

`neta onboard-state --house up_vs` does, for the state's cleanly-available cycles (from elections.py):
  per cycle:  myneta (all winners -> person + affidavit + criminal_case) + fill-assembly (per-constituency
              winners MyNeta omits from show_winners)
  then:       merge-cycles (links the same person across cycles -> multi-cycle wealth/career + detects
              party switches) + canon-parties (dedupe party records)
  optional:   --backfill runs historical-lookup for each older cycle (extra recall — current members who
              ran-but-lost in a past cycle, so their wealth trend includes that year). This is the
              expensive extra crawl; off by default.

Idempotent throughout (upsert on natural keys). `--cycle X` ingests only that one cycle (to chunk a large
state across separate ingest jobs). No `resolve` step: `myneta` persists persons directly. State MLAs have
no attendance/contact source, so those render "—".
"""

from __future__ import annotations

from neta_sources.myneta import elections

from neta_ingest.pipelines.identity import canon_parties, merge_cycles, myneta
from neta_ingest.pipelines.lok_sabha import historical_lookup
from neta_ingest.pipelines.state import assembly_backfill


def _ingest_cycle(house: str, eci_id: str) -> None:
    print(f"[onboard:{house}] ingesting {eci_id} …")
    myneta.run(cycle=eci_id, house=house, limit=0)       # limit<=0 => all winners
    assembly_backfill.run(house=house, cycle=eci_id)      # fill winners MyNeta omitted


def run(house: str, cycle: str | None = None, backfill: bool = False) -> None:
    from neta_ingest import admin

    a = elections.assembly(house)                         # validates the house is registered
    admin.run_seed_states()                               # ensure house + term_cycle rows exist (idempotent)
    cycles = sorted(a.cycles, key=lambda c: c.number)     # oldest -> newest
    latest = cycles[-1].eci_id

    if cycle:
        _ingest_cycle(house, cycle)
        print(f"[onboard:{house}] ingested {cycle} only (chunk); re-run without --cycle to link + dedupe.")
        return

    for c in cycles:
        _ingest_cycle(house, c.eci_id)
    print(f"[onboard:{house}] linking across cycles + detecting switches …")
    merge_cycles.run()
    canon_parties.run()
    if backfill:
        for c in cycles[:-1]:
            historical_lookup.run(cycle=c.eci_id, current_cycle=latest, house=house)
    print(f"[onboard:{house}] done — {a.name}: {len(cycles)} cycle(s)"
          f"{' + historical backfill' if backfill else ''}.")


def _house_has_terms(house: str) -> bool:
    from sqlalchemy import text

    from neta_core.db.engine import session_scope
    with session_scope() as s:
        return s.execute(
            text("SELECT 1 FROM office_term ot JOIN term_cycle tc ON tc.id = ot.term_cycle_id "
                 "JOIN house h ON h.id = tc.house_id WHERE h.code = :c LIMIT 1"),
            {"c": house},
        ).first() is not None


def run_pending(minutes: int = 300, backfill: bool = False) -> None:
    """Onboard every registered state house that has no office_term yet, one at a time, until `minutes`
    elapses or none remain. Idempotent + resumable: the scheduled `onboard-driver` workflow re-invokes this
    to continue after each time-boxed run, so the whole rollout finishes with NO laptop in the loop. One
    failing state is logged and skipped, never stalling the queue."""
    import time

    deadline = time.monotonic() + minutes * 60
    done = 0
    for a in elections.ASSEMBLIES:
        if time.monotonic() >= deadline:
            print(f"[onboard-pending] time budget hit after {done} state(s); the driver will continue.")
            return
        if _house_has_terms(a.house_code):
            continue
        print(f"[onboard-pending] {a.house_code} has no data yet — onboarding (base)…")
        try:
            run(house=a.house_code, backfill=backfill)
            done += 1
        except Exception as e:  # noqa: BLE001 — never let one bad state stall the rollout
            print(f"[onboard-pending] WARN {a.house_code} failed: {e!r} — continuing.")
    print(f"[onboard-pending] no pending state houses left ({done} onboarded this run).")


def _pp_done(task: str) -> bool:
    from sqlalchemy import text

    from neta_core.db.engine import session_scope
    with session_scope() as s:
        return s.execute(text("SELECT 1 FROM pipeline_progress WHERE task = :t"), {"t": task}).first() is not None


def _pp_mark(task: str) -> None:
    from sqlalchemy import text

    from neta_core.db.engine import session_scope
    with session_scope() as s:
        s.execute(text("INSERT INTO pipeline_progress (task) VALUES (:t) ON CONFLICT DO NOTHING"), {"t": task})


def run_rollout(minutes: int = 270) -> None:
    """Self-driving, two-phase rollout for the `onboard-driver` cron — no laptop in the loop.

    Phase 1 (breadth): base-onboard every registered state house that has no data yet — fast current
    rosters + multi-cycle wealth trends for all states first. Phase 2 (depth), reached only once every
    house has base data: run historical-lookup for each older cycle, recording a 'backfill:<cycle>' marker
    in pipeline_progress so it's skipped on re-run. Deadline-guarded before every unit and resumable across
    the cron's time-boxed jobs; a failing unit is logged and skipped, never stalling the rollout."""
    import time

    deadline = time.monotonic() + minutes * 60

    # Phase 1 — breadth (base onboard).
    for a in elections.ASSEMBLIES:
        if time.monotonic() >= deadline:
            print("[rollout] budget hit during breadth phase; the driver will continue.")
            return
        if _house_has_terms(a.house_code):
            continue
        print(f"[rollout] breadth: base-onboard {a.house_code}…")
        try:
            run(house=a.house_code, backfill=False)
        except Exception as e:  # noqa: BLE001
            print(f"[rollout] WARN base {a.house_code} failed: {e!r} — continuing.")

    # Phase 2 — depth (historical backfill per older cycle). Only meaningful once every house has base data.
    for a in elections.ASSEMBLIES:
        cycles = sorted(a.cycles, key=lambda c: c.number)   # oldest -> newest
        latest = cycles[-1].eci_id
        for older in cycles[:-1]:
            if time.monotonic() >= deadline:
                print("[rollout] budget hit during backfill phase; the driver will continue.")
                return
            task = f"backfill:{older.eci_id}"
            if _pp_done(task):
                continue
            print(f"[rollout] depth: historical-lookup {older.eci_id} (house {a.house_code})…")
            try:
                historical_lookup.run(cycle=older.eci_id, current_cycle=latest, house=a.house_code)
                _pp_mark(task)
            except Exception as e:  # noqa: BLE001
                print(f"[rollout] WARN backfill {older.eci_id} failed: {e!r} — continuing.")
    print("[rollout] nothing pending — breadth + backfill complete.")
