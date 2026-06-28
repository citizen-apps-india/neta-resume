"""Adjudicate the Tier-2 review queues to recover true matches held back as ambiguous.

For each queued MP with candidate evidence, fetch the top tied candidates and disambiguate by AGE
corroboration against the MP's known birth_year (e.g. two "Dimple Yadav" candidates — pick the one
whose declared age implies the MP's birth year). Attach only when exactly one candidate corroborates
within tolerance; otherwise leave it in the queue. Idempotent (write_affidavit upserts).

Run after the crawl/indexes are in place:  uv run python scripts_adjudicate.py
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text

from neta_ingest.db.engine import session_scope
from neta_ingest.pipelines import affidavit_attach as aa
from neta_ingest.sources.myneta import client as myneta

CYCLES = ("LS2019", "LS2014", "LS2009")
AGE_TOLERANCE = 3
NAME_FLOOR = 0.88  # only consider candidate evidence at/above this name score
QDIR = Path("data/hist_index")


def main():
    with session_scope() as s:
        house_id = s.execute(text("SELECT id FROM house WHERE code='LS'")).scalar()

    for cycle in CYCLES:
        rp = QDIR / f"review_{cycle}.json"
        if not rp.exists():
            print(f"[adj:{cycle}] no review file")
            continue
        queue = json.loads(rp.read_text())
        with session_scope() as s:
            term_cycle_id = s.execute(
                text("SELECT id FROM term_cycle WHERE eci_election_id=:c"), {"c": cycle}).scalar()

        attached, still = 0, []
        for entry in queue:
            cands = [c for c in (entry.get("candidates") or []) if c.get("score", 0) >= NAME_FLOOR]
            pid = entry["person_id"]
            with session_scope() as s:
                birth_year, has_aff = s.execute(text(
                    "SELECT p.birth_year, EXISTS(SELECT 1 FROM affidavit a "
                    "WHERE a.person_id=p.id AND a.election_cycle=:c) FROM person p WHERE p.id=:p"),
                    {"c": cycle, "p": pid}).one()
            if has_aff:
                continue  # already resolved by a refresh re-run
            if not cands or not birth_year:
                still.append(entry)
                continue

            # Fetch tied candidates, keep those whose declared age corroborates the MP's birth year.
            corroborating = []
            for c in cands[:5]:
                try:
                    parsed, raw_rel = myneta.fetch_candidate(c["candidate_id"], cycle)
                except Exception:  # noqa: BLE001
                    continue
                if parsed.age and abs((aa.cycle_year(cycle) - parsed.age) - birth_year) <= AGE_TOLERANCE:
                    corroborating.append((c["candidate_id"], parsed, raw_rel))

            if len(corroborating) == 1:
                cand_id, parsed, raw_rel = corroborating[0]
                with session_scope() as s:
                    aa.write_affidavit(s, parsed, pid, cand_id, raw_rel,
                                       house_id=house_id, term_cycle_id=term_cycle_id, cycle=cycle)
                attached += 1
                print(f"[adj:{cycle}] {entry['name']} -> {cand_id} (age-corroborated) "
                      f"assets={parsed.total_assets:,} cases={len(parsed.criminal_cases)}")
            else:
                entry["adjudication"] = f"{len(corroborating)} age-corroborating candidate(s)"
                still.append(entry)

        (QDIR / f"review_{cycle}_unresolved.json").write_text(json.dumps(still, indent=2))
        print(f"[adj:{cycle}] attached {attached}; {len(still)} still unresolved")


if __name__ == "__main__":
    main()
