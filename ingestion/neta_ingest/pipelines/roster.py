"""Roster pipeline: sansad.in members -> office_term + source_ref.

Steps (idempotent):
  1. Fetch member list for (house, cycle) from neta_ingest.sources.sansad.
  2. For each member: cache_raw + record_source_ref(source='sansad', native_id=member_id).
  3. Upsert office_term (person_id resolved later by the `resolve` pipeline).

Run order: this comes BEFORE resolve_persons; office_term.source_ref.person_id stays NULL until then.
"""

from __future__ import annotations

from neta_ingest.sources.sansad import client as sansad


def run(house: str = "ls", cycle: str = "18") -> None:
    members = sansad.fetch_members(house=house, cycle=cycle)
    raise NotImplementedError(
        f"roster pipeline scaffolded for house={house} cycle={cycle}; "
        f"got {len(members)} members from sansad. Wire upsert into office_term next (Phase 1)."
    )
