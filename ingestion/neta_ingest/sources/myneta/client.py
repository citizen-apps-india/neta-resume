"""MyNeta (ADR) client — wealth + criminal affidavit data.

LICENSE: non-commercial only; no bulk CSV. Scrape politely (neta_ingest.http.client throttles).
URL scheme is election-partitioned, e.g. base = https://www.myneta.info/LokSabha2024
  winners list : {base}/index.php?action=show_winners&sort=default
  candidate    : {base}/candidate.php?candidate_id={id}

Raw HTML is cached via provenance.cache_raw so every fact has a snapshot it was derived from.
"""

from __future__ import annotations

from neta_ingest.http import client as http
from neta_ingest.provenance import cache_raw
from neta_ingest.sources.myneta.parser import (
    ParsedCandidate,
    WinnerRow,
    parse_candidate,
    parse_winners,
)

# Election-cycle code -> MyNeta site path.
ELECTION_BASE = {
    "LS2024": "https://www.myneta.info/LokSabha2024",
    "LS2019": "https://www.myneta.info/loksabha2019",
}


def base_url(cycle: str) -> str:
    try:
        return ELECTION_BASE[cycle]
    except KeyError as e:
        raise ValueError(f"unknown MyNeta election cycle {cycle!r}; add it to ELECTION_BASE") from e


def fetch_winners(cycle: str = "LS2024") -> list[WinnerRow]:
    base = base_url(cycle)
    resp = http.get(f"{base}/index.php?action=show_winners&sort=default")
    cache_raw(resp.content, suffix=f"_{cycle}_winners.html")
    return parse_winners(resp.text, base_url=base)


def fetch_candidate(candidate_id: str, cycle: str = "LS2024") -> tuple[ParsedCandidate, str]:
    """Fetch + parse one candidate page. Returns (parsed, raw_cache_relpath)."""
    base = base_url(cycle)
    url = f"{base}/candidate.php?candidate_id={candidate_id}"
    resp = http.get(url)
    rel = cache_raw(resp.content, suffix=f"_{cycle}_cand_{candidate_id}.html")
    parsed = parse_candidate(resp.text, candidate_id=candidate_id)
    return parsed, rel


def candidate_url(candidate_id: str, cycle: str = "LS2024") -> str:
    return f"{base_url(cycle)}/candidate.php?candidate_id={candidate_id}"
