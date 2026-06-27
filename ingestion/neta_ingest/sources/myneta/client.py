"""MyNeta (ADR) client — wealth + criminal affidavit data.

LICENSE: non-commercial only; no bulk CSV. Scrape politely (neta_ingest.http.client throttles).
Reuse: study nini1294/myneta_api + datameet/india-election-data (affidavits/myneta.ipynb) for the
URL structure (election-partitioned) and parsing recipe before re-implementing.

Backfill historical cycles from datameet/Vonter corpora instead of live-scraping.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MynetaAffidavit:
    candidate_id: str       # native myneta id -> source_ref.native_id
    page_url: str
    name: str
    election_cycle: str     # e.g. 'LS2024'
    constituency: str | None
    party: str | None
    total_assets_raw: str | None       # pass through transform.money.parse_rupees
    total_liabilities_raw: str | None
    self_income_raw: str | None
    age: int | None = None
    education: str | None = None


@dataclass(slots=True)
class MynetaCase:
    candidate_id: str
    page_url: str
    raw_section_text: str   # pass through transform.sections.parse_sections
    status_raw: str | None
    description: str | None = None


def fetch_affidavits(house: str = "ls", cycle: str = "LS2024") -> list[MynetaAffidavit]:
    raise NotImplementedError("myneta.fetch_affidavits — implement using the election-partitioned URL scheme.")


def fetch_criminal_cases(house: str = "ls", cycle: str = "LS2024") -> list[MynetaCase]:
    raise NotImplementedError("myneta.fetch_criminal_cases — parse the candidate 'criminal cases' table.")
