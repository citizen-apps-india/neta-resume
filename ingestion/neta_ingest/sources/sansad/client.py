"""sansad.in (Digital Sansad) roster client — the canonical LS/RS member spine.

Reuse note: sansad exposes structured member listings with stable member IDs. Prefer any JSON
endpoint behind the member directory over HTML scraping where one exists.

URLs:
    LS members: https://sansad.in/ls/members
    RS members: https://sansad.in/rs/members
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SansadMember:
    member_id: str          # native sansad id -> source_ref.native_id
    name: str
    house: str              # 'ls' | 'rs'
    constituency: str | None
    state: str | None
    party: str | None
    profile_url: str


def fetch_members(house: str = "ls", cycle: str = "18") -> list[SansadMember]:
    """Return the member roster for a house/cycle. TODO(Phase 1): implement fetch+parse."""
    raise NotImplementedError(
        "sansad.fetch_members not yet implemented — inspect https://sansad.in/{house}/members for a "
        "JSON endpoint first; fall back to selectolax HTML parsing. Cache raw via provenance.cache_raw."
    )
