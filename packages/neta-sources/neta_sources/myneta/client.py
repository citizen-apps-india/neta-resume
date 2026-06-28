"""MyNeta (ADR) client — wealth + criminal affidavit data.

LICENSE: non-commercial only; no bulk CSV. Scrape politely (neta_core.http.client throttles).
URL scheme is election-partitioned, e.g. base = https://www.myneta.info/LokSabha2024
  winners list : {base}/index.php?action=show_winners&sort=default
  candidate    : {base}/candidate.php?candidate_id={id}

Raw HTML is cached via provenance.cache_raw so every fact has a snapshot it was derived from.
"""

from __future__ import annotations

import re

from neta_core.http import client as http
from neta_core.provenance import cache_raw
from neta_sources.myneta.parser import (
    ParsedCandidate,
    WinnerRow,
    parse_candidate,
    parse_winners,
)

# Election-cycle code -> MyNeta site path. Path casing/scheme varies per cycle (verified live):
# 2024 uses "LokSabha2024"; older cycles use the short "ls{year}" form ("loksabha{year}" is a dead path
# for 2009/2014 — its show_winners action returns an empty list). State assemblies use their own paths,
# e.g. Maharashtra 2024 = "Maharashtra2024" (same show_winners / candidate.php structure as LS).
ELECTION_BASE = {
    "LS2024": "https://www.myneta.info/LokSabha2024",
    "LS2019": "https://www.myneta.info/loksabha2019",
    "LS2014": "https://www.myneta.info/ls2014",
    "LS2009": "https://www.myneta.info/ls2009",
    "MH_VS2024": "https://www.myneta.info/Maharashtra2024",
    "MH_VS2019": "https://www.myneta.info/Maharashtra2019",
    "MH_VS2014": "https://www.myneta.info/Maharashtra2014",
    # MH_VS2009 deferred: MyNeta's 2009 MH assembly isn't at the per-election path scheme (legacy URL).
    "DL_MCD2022": "https://www.myneta.info/Delhi2022",
}


def base_url(cycle: str) -> str:
    try:
        return ELECTION_BASE[cycle]
    except KeyError as e:
        raise ValueError(f"unknown MyNeta election cycle {cycle!r}; add it to ELECTION_BASE") from e


def native_id(cycle: str, candidate_id: str) -> str:
    """The source_ref native_id for a MyNeta candidate, namespaced by cycle.

    MyNeta candidate_ids are NOT globally unique — the same integer is reused across elections
    (e.g. id 5069 is a different person in LS2024 vs LS2019). Namespacing by cycle keeps each cycle's
    candidate a distinct source_ref so a historical ingest can never overwrite another cycle's person.
    """
    return f"{cycle}:{candidate_id}"


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


def _norm_const(name: str) -> str:
    """Normalize a constituency name for matching: strip (SC)/(ST) etc., uppercase, collapse spaces."""
    name = re.sub(r"\([^)]*\)", " ", name)
    return re.sub(r"\s+", " ", name).strip().upper()


def fetch_constituency_map(cycle: str = "LS2024") -> dict[str, str]:
    """Map normalized constituency name -> MyNeta constituency_id (from the election index page)."""
    resp = http.get(f"{base_url(cycle)}/")
    out: dict[str, str] = {}
    for m in re.finditer(
        r'href=["\']?[^"\'>]*action=show_candidates&constituency_id=(\d+)[^"\'>]*["\']?[^>]*>(.*?)</a>',
        resp.text, re.S,
    ):
        cid = m.group(1)
        name = _norm_const(re.sub(r"<[^>]+>", " ", m.group(2)))
        if name and name not in out:
            out[name] = cid
    return out


def fetch_constituency_candidates(constituency_id: str, cycle: str = "LS2024") -> list[tuple[str, str]]:
    """Return [(candidate_id, name), ...] for every candidate in a constituency."""
    resp = http.get(f"{base_url(cycle)}/index.php?action=show_candidates&constituency_id={constituency_id}")
    seen: dict[str, str] = {}
    for m in re.finditer(r'candidate\.php\?candidate_id=(\d+)[^>]*>([^<]+)', resp.text):
        cid, name = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
        if name and not name.isdigit():
            seen[cid] = name
    return list(seen.items())


def fetch_constituency_winner(constituency_id: str, cycle: str = "LS2024") -> str | None:
    """Return the winning candidate_id for a constituency, read from its show_candidates page.

    The winner's row carries a "Winner" marker right after the candidate link, e.g.
    `candidate.php?candidate_id=931>Gaikwad Sanjay Rambhau &nbsp&nbsp Winner`. Used to recover winners
    MyNeta omits from its aggregate show_winners list (esp. state-assembly elections).
    """
    resp = http.get(f"{base_url(cycle)}/index.php?action=show_candidates&constituency_id={constituency_id}")
    cache_raw(resp.content, suffix=f"_{cycle}_const_{constituency_id}.html")
    # The candidate link nearest before the "Winner" marker (allow markup/whitespace between them).
    m = re.search(r'candidate\.php\?candidate_id=(\d+)[^>]*>(?:(?!candidate\.php).){0,200}?Winner',
                  resp.text, re.S | re.I)
    return m.group(1) if m else None
