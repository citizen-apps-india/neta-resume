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
