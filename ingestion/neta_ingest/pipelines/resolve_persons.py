"""Entity-resolution pipeline: link unresolved source_refs to canonical persons.

Steps (see docs/entity-resolution.md):
  1. Seed persons from TCPD/SURF where available (tcpd_surf_id anchors person).
  2. For each source_ref with person_id IS NULL: normalize name (transform.names),
     block candidates (resolve.blocking), score (resolve.surf + structured signals),
     decide (resolve.match: auto-merge / review-queue / reject), link (resolve.link).
"""

from __future__ import annotations

from neta_ingest.resolve import match


def run() -> None:
    decided = match.resolve_unlinked()
    raise NotImplementedError(
        f"resolve pipeline scaffolded; resolve.match returned {decided}. "
        "Wire blocking + SURF scoring + link writes next (Phase 2)."
    )
