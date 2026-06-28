"""Backfill state-assembly winners MyNeta omits from its aggregate show_winners list.

MyNeta's `show_winners` page for a state election can be incomplete (e.g. Maharashtra 2024 lists 256 of
288 seats). The missing winners still exist on their per-constituency pages, which mark the winner. For
each constituency in MyNeta's index that we haven't ingested yet, we read its winning candidate_id and
persist it through the normal MyNeta ingest (`myneta.run` -> `_persist_candidate`), so the state-stamp and
affidavit/criminal parsing are identical to the main pass. Idempotent: dedupes by candidate_id.
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_ingest.pipelines.identity import myneta as myneta_pipeline
from neta_sources.myneta import client as myneta


def run(house: str = "mh_vs", cycle: str = "MH_VS2024") -> None:
    const_map = myneta.fetch_constituency_map(cycle)
    print(f"[fill-assembly] {cycle} MyNeta constituency index: {len(const_map)} entries")

    # Candidate_ids already ingested for this cycle (native_id is "{cycle}:{candidate_id}").
    with session_scope() as s:
        prefix = f"{cycle}:"
        have_ids = {
            r[0].split(":", 1)[1]
            for r in s.execute(
                text("SELECT native_id FROM source_ref sr JOIN source so ON so.id = sr.source_id "
                     "WHERE so.code = 'myneta' AND sr.native_id LIKE :p"),
                {"p": prefix + "%"},
            )
        }
        have_consts = {
            myneta._norm_const(r[0])
            for r in s.execute(
                text("SELECT ot.constituency FROM office_term ot JOIN house h ON h.id = ot.house_id "
                     "WHERE h.code = :code AND ot.constituency IS NOT NULL"),
                {"code": house.upper()},
            )
        }
    print(f"[fill-assembly] already ingested: {len(have_ids)} candidates / {len(have_consts)} constituencies")

    missing_ids: list[str] = []
    skipped = unresolved = 0
    for raw_name, cons_id in const_map.items():
        norm = myneta._norm_const(raw_name)
        if "BYE ELECTION" in norm or "BYE-ELECTION" in norm:
            continue  # future/standalone byelections aren't part of the sitting assembly
        if norm in have_consts:
            continue  # already have this seat
        winner = myneta.fetch_constituency_winner(cons_id, cycle)
        if not winner:
            unresolved += 1
            print(f"  [{raw_name}] no Winner marker found (constituency_id={cons_id})")
            continue
        if winner in have_ids:
            skipped += 1  # different constituency spelling, same already-ingested winner
            continue
        missing_ids.append(winner)
        have_ids.add(winner)
        print(f"  [{raw_name}] winner candidate_id={winner}")

    print(f"[fill-assembly] {len(missing_ids)} new winner(s) to ingest "
          f"({skipped} already-ingested, {unresolved} unresolved)")
    if missing_ids:
        myneta_pipeline.run(cycle=cycle, house=house, candidate_ids=missing_ids)
