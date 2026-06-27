"""TCPD (Ashoka) client — seeds canonical persons + the unique-ID backbone.

TCPD-IPD / LokDhaba / Political Career Tracker already assign stable IDs across elections and track
party switching. Seed person.tcpd_surf_id from here BEFORE fuzzy matching so high-quality anchors
exist. Academic data — cite TCPD-IPD. See docs/entity-resolution.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TcpdPerson:
    surf_id: str
    name: str
    normalized_name: str
    birth_year: int | None
    known_parties: list[str]


def seed_persons() -> list[TcpdPerson]:
    raise NotImplementedError("tcpd.seed_persons — load LokDhaba/Incumbents export; populate person + tcpd_surf_id.")
