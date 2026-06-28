"""Backfill historical office_terms for current MPs' PAST WINS + recover multi-seat candidacies.

Why: Tier-2 attached past-cycle affidavits but not office terms, and merge_cycles only links a past win
at the SAME constituency. So a seat-changing MP (e.g. Rahul Gandhi: Amethi -> Wayanad -> Rae Bareli)
showed only their current term and no party-switch history, even though their past wealth was attached.

What this does:
  Part A — multi-seat recovery: for a current MP still missing a cycle's affidavit who was flagged
    ambiguous because they contested >1 seat, attach the WINNING seat's affidavit (age-corroborated).
  Part B — office terms: for every past-cycle affidavit whose candidate WON that election (MyNeta
    winners list), create the historical office_term (status 'former') + non-current party affiliation,
    re-parsing the already-cached candidate HTML (no re-crawl).

After this, re-run `neta merge-cycles` to (re)detect party switches from the new multi-cycle terms.
Run from ingestion/:  uv run python scripts/backfill_historical_terms.py
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text

from neta_core.config import settings
from neta_core.db.engine import session_scope
from neta_ingest.pipelines.identity import affidavit_attach as aa
from neta_sources.myneta import client as myneta
from neta_sources.myneta.parser import parse_candidate
from neta_core.transform.parties import resolve_or_create_party_id

CACHE = Path(settings.raw_cache_dir)
QDIR = Path("data/hist_index")
PAST = ("LS2019", "LS2014", "LS2009")
AGE_TOL = 3


def main():
    winners = {c: {w.candidate_id for w in myneta.fetch_winners(c)} for c in PAST}
    print({c: len(v) for c, v in winners.items()})

    with session_scope() as s:
        house_id = s.execute(text("SELECT id FROM house WHERE code='LS'")).scalar()

    # Part A — recover a current MP's missing affidavit when they won one of several seats they contested.
    recovered = 0
    for cycle in PAST:
        rf = QDIR / f"review_{cycle}.json"
        if not rf.exists():
            continue
        for e in json.loads(rf.read_text()):
            pid = e["person_id"]
            with session_scope() as s:
                birth_year, has_aff = s.execute(text(
                    "SELECT p.birth_year, EXISTS(SELECT 1 FROM affidavit a WHERE a.person_id=p.id "
                    "AND a.election_cycle=:c) FROM person p WHERE p.id=:p"), {"c": cycle, "p": pid}).one()
            if has_aff:
                continue
            strong = [c for c in (e.get("candidates") or []) if c.get("score", 0) >= 0.95]
            winner_cands = [c for c in strong if c["candidate_id"] in winners[cycle]]
            if not winner_cands:
                continue  # no winning seat among strong matches -> true namesake / lost both -> leave queued
            # A high-profile candidate often contests two seats and, if they win both, resigns one. Those
            # winning candidacies are the SAME person, so attach the first that age-corroborates — either
            # seat's affidavit gives the same wealth, and Part B records one term for the cycle.
            chosen = None
            for c in winner_cands:
                parsed, raw_rel = myneta.fetch_candidate(c["candidate_id"], cycle)
                if birth_year and parsed.age and abs((aa.cycle_year(cycle) - parsed.age) - birth_year) > AGE_TOL:
                    continue  # namesake winner
                chosen = (c, parsed, raw_rel)
                break
            if not chosen:
                continue
            c, parsed, raw_rel = chosen
            with session_scope() as s:
                tcid = s.execute(text("SELECT id FROM term_cycle WHERE eci_election_id=:c"), {"c": cycle}).scalar()
                aa.write_affidavit(s, parsed, pid, c["candidate_id"], raw_rel,
                                   house_id=house_id, term_cycle_id=tcid, cycle=cycle)
            recovered += 1
            print(f"[multiseat:{cycle}] {e['name']} -> {c['candidate_id']} ({c['constituency']}) won")
    print(f"Part A: recovered {recovered} multi-seat affidavit(s)")

    # Part B — create historical office_terms for every attached past-cycle affidavit that was a WIN.
    with session_scope() as s:
        rows = s.execute(text(
            """
            SELECT a.person_id, a.election_cycle, sr.id AS sref, sr.native_id, sr.raw_payload_ref,
                   tc.id AS tcid
            FROM affidavit a
            JOIN source_ref sr ON sr.id = a.source_ref_id
            JOIN term_cycle tc ON tc.eci_election_id = a.election_cycle
            WHERE a.election_cycle <> 'LS2024' AND sr.raw_payload_ref IS NOT NULL
            """)).all()

    created = 0
    for r in rows:
        cand_id = r.native_id.split(":", 1)[1]
        if cand_id not in winners.get(r.election_cycle, ()):
            continue  # contested but did not win -> affidavit only, no office term
        snap = CACHE / r.raw_payload_ref
        if not snap.exists():
            continue
        parsed = parse_candidate(snap.read_text(encoding="utf-8", errors="ignore"))
        with session_scope() as s:
            if s.execute(text("SELECT 1 FROM office_term WHERE person_id=:p AND term_cycle_id=:t LIMIT 1"),
                         {"p": r.person_id, "t": r.tcid}).first():
                continue
            party_id = resolve_or_create_party_id(s, parsed.party) if parsed.party else None
            s.execute(text(
                """
                INSERT INTO office_term
                  (person_id, house_id, term_cycle_id, constituency, ls_state_code, membership_type, party_id, status, source_ref_id)
                VALUES (:p, :h, :t, :con, :state, 'elected', :party, 'former', :sr)
                ON CONFLICT DO NOTHING
                """),
                {"p": r.person_id, "h": house_id, "t": r.tcid, "con": parsed.constituency,
                 "state": parsed.state, "party": party_id, "sr": r.sref})
            # historical (non-current) party affiliation for this term
            if party_id is not None:
                s.execute(text(
                    "INSERT INTO party_affiliation (person_id, party_id, is_current, detection, confidence, source_ref_id) "
                    "VALUES (:p,:party,false,'structured_term_diff',70,:sr) ON CONFLICT DO NOTHING"),
                    {"p": r.person_id, "party": party_id, "sr": r.sref})
            created += 1
    print(f"Part B: created {created} historical office_term(s)")


if __name__ == "__main__":
    main()
