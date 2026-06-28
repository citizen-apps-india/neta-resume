"""Backfill affidavit data for LS members MyNeta omitted from its winners summary.

These members exist on MyNeta only on their per-constituency candidate page (not the winners list).
For each roster-only LS person we resolve their constituency -> MyNeta constituency_id -> candidate list,
match the winner by name, then write that candidate's affidavit + criminal data onto the EXISTING person
(creating a MyNeta source_ref for provenance). No new persons -> no duplicates.

Cycle-parametrized (default LS2024 = current roster) so the same gap-filling works on any cycle; the
shared attach/match logic lives in `affidavit_attach`.
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_ingest.pipelines.identity import affidavit_attach as aa
from neta_sources.myneta import client as myneta

# A few 2024 winners whose MyNeta name is formatted too differently to auto-match safely; verified by
# hand against the constituency candidate list. Keyed by normalized constituency -> MyNeta candidate_id.
OVERRIDES_LS2024 = {
    "SATARA": "4320",        # Shrimant Chh Udayanraje Pratapsinhamaharaj Bhonsle
    "NARASARAOPET": "5116",  # Lavu Srikrishna Devarayalu
    "ANANTAPUR": "5097",     # Ambica G Lakshminarayana Valmiki
}


def run(cycle: str = "LS2024") -> None:
    overrides = OVERRIDES_LS2024 if cycle == "LS2024" else {}
    const_map = myneta.fetch_constituency_map(cycle)
    stripped = {aa.strip_const(k): v for k, v in const_map.items()}
    print(f"[missing] {cycle} MyNeta constituency map: {len(const_map)} constituencies")

    with session_scope() as s:
        house_id = s.execute(text("SELECT id FROM house WHERE code='LS'")).scalar()
        term_cycle_id = s.execute(
            text("SELECT id FROM term_cycle WHERE eci_election_id=:c"), {"c": cycle}
        ).scalar()
        if term_cycle_id is None:
            raise RuntimeError(f"term_cycle {cycle!r} not seeded")
        missing = s.execute(
            text(
                """
                SELECT p.id, p.display_name, p.normalized_name, ot.constituency
                FROM office_term ot
                JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                JOIN person p ON p.id = ot.person_id
                WHERE tc.id = :tcid AND ot.constituency IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM affidavit a WHERE a.person_id = p.id AND a.election_cycle = :c
                  )
                """
            ),
            {"tcid": term_cycle_id, "c": cycle},
        ).all()
    print(f"[missing] {len(missing)} {cycle} members without affidavit data")

    enriched = 0
    unresolved: list[str] = []
    for person in missing:
        override = overrides.get(myneta._norm_const(person.constituency))
        if override:
            candidate_id = override
        else:
            cons_id = aa.resolve_constituency(const_map, stripped, person.constituency)
            if not cons_id:
                unresolved.append(f"{person.display_name} ({person.constituency}) — constituency not on MyNeta")
                continue
            cands = myneta.fetch_constituency_candidates(cons_id, cycle)
            candidate_id, _score, _amb = aa.best_match(
                cands, person.display_name, person.normalized_name, threshold=0.80
            )
        if not candidate_id:
            unresolved.append(f"{person.display_name} ({person.constituency}) — no name match among candidates")
            continue
        parsed, raw_rel = myneta.fetch_candidate(candidate_id, cycle)
        with session_scope() as s:
            aa.write_affidavit(s, parsed, person.id, candidate_id, raw_rel,
                               house_id=house_id, term_cycle_id=term_cycle_id, cycle=cycle)
        enriched += 1
        print(f"  [{enriched}] {person.display_name} ({person.constituency}) -> cand {candidate_id} "
              f"assets={parsed.total_assets:,} cases={len(parsed.criminal_cases)}")

    print(f"[missing] enriched {enriched} member(s) with affidavit data; {len(unresolved)} unresolved")
    for u in unresolved:
        print("   · " + u)
