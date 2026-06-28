"""Affidavit/wealth pipeline: MyNeta candidate pages -> affidavit + affidavit_line_item.

Steps (idempotent):
  1. Fetch candidate affidavit pages for (house, cycle) from neta_sources.myneta.
  2. transform.money.parse_rupees on assets/liabilities/income -> integer rupees.
  3. record_source_ref(source='myneta', native_id=candidate_id, native_url=page_url).
  4. Upsert affidavit (UNIQUE person_id, election_cycle, source_ref_id); upsert line items.

Backfill historical cycles from datameet/Vonter parsed corpora instead of live-scraping (see docs).
"""

from __future__ import annotations

from neta_sources.myneta import client as myneta


def run(house: str = "ls", cycle: str = "LS2024") -> None:
    candidates = myneta.fetch_affidavits(house=house, cycle=cycle)
    raise NotImplementedError(
        f"affidavits pipeline scaffolded for house={house} cycle={cycle}; "
        f"got {len(candidates)} candidates from MyNeta. Wire money parse + upsert next (Phase 1)."
    )
