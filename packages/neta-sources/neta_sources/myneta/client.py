"""MyNeta (ADR) client — wealth + criminal affidavit data.

LICENSE: non-commercial only; no bulk CSV. Scrape politely (neta_core.http.client throttles).
URL scheme is election-partitioned, e.g. base = https://www.myneta.info/LokSabha2024
  winners list : {base}/index.php?action=show_winners&sort=default
  candidate    : {base}/candidate.php?candidate_id={id}

Every discovery and candidate response is captured through the manifest-backed raw-envelope adapter
before parsing, so every fact retains the exact snapshot it was derived from.
"""

from __future__ import annotations

import re

from neta_core.pipeline import (
    ExtractionContext,
    HttpExtractionRequest,
    HttpSourceAdapter,
    RawArtifact,
    SourceAdapter,
)
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
    "DL_MCD2017": "https://www.myneta.info/Delhi2017",   # trifurcated N/S/E MCD, merged on one MyNeta site
    "DL_MCD2012": "https://www.myneta.info/MCD2012",
    # DL_MCD2007 deferred: not on MyNeta (no per-election site).
}

# State/UT assemblies live in a data-driven registry (elections.py) so onboarding a state is one entry,
# not scattered edits here. Merge their cycle->URL map in.
from neta_sources.myneta import elections as _elections  # noqa: E402  (no import cycle: elections has no client dep)

ELECTION_BASE.update(_elections.election_base())

SOURCE_ID = "myneta.candidates"


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


def extract_winners(
    cycle: str = "LS2024",
    *,
    context: ExtractionContext,
    adapter: SourceAdapter[HttpExtractionRequest] | None = None,
) -> RawArtifact:
    """Fetch the election winners index as one raw artifact."""
    base = base_url(cycle)
    extractor = adapter if adapter is not None else HttpSourceAdapter()
    return extractor.extract(
        HttpExtractionRequest(
            source_id=SOURCE_ID,
            native_id=f"{cycle}:winners",
            url=f"{base}/index.php",
            default_content_type="text/html",
            params={"action": "show_winners", "sort": "default"},
        ),
        context=context,
    )


def parse_winners_artifact(artifact: RawArtifact, cycle: str = "LS2024") -> list[WinnerRow]:
    return parse_winners(artifact.text(), base_url=base_url(cycle))


def fetch_winners(
    cycle: str = "LS2024",
    *,
    context: ExtractionContext,
) -> list[WinnerRow]:
    return parse_winners_artifact(extract_winners(cycle, context=context), cycle)


def extract_candidate(
    candidate_id: str,
    cycle: str = "LS2024",
    *,
    context: ExtractionContext,
    adapter: SourceAdapter[HttpExtractionRequest] | None = None,
) -> RawArtifact:
    """Fetch one candidate page as a raw envelope, without parsing or canonical writes."""
    base = base_url(cycle)
    url = f"{base}/candidate.php?candidate_id={candidate_id}"
    extractor = adapter if adapter is not None else HttpSourceAdapter()
    return extractor.extract(
        HttpExtractionRequest(
            source_id=SOURCE_ID,
            native_id=native_id(cycle, candidate_id),
            url=url,
            default_content_type="text/html",
        ),
        context=context,
    )


def parse_candidate_artifact(artifact: RawArtifact, candidate_id: str) -> ParsedCandidate:
    """Convert a stored candidate response with the existing affidavit parser."""
    html = artifact.text()
    return parse_candidate(html, candidate_id=candidate_id)


def fetch_candidate(
    candidate_id: str,
    cycle: str = "LS2024",
    *,
    context: ExtractionContext,
) -> tuple[ParsedCandidate, str | None]:
    """Fetch + parse one candidate page. Returns the parsed record and raw provenance pointer."""
    artifact = extract_candidate(candidate_id, cycle, context=context)
    return parse_candidate_artifact(artifact, candidate_id), artifact.provenance_ref


def candidate_url(candidate_id: str, cycle: str = "LS2024") -> str:
    return f"{base_url(cycle)}/candidate.php?candidate_id={candidate_id}"


def _norm_const(name: str) -> str:
    """Normalize a constituency name for matching: strip (SC)/(ST) etc., uppercase, collapse spaces."""
    name = re.sub(r"\([^)]*\)", " ", name)
    return re.sub(r"\s+", " ", name).strip().upper()


def extract_constituency_index(
    cycle: str = "LS2024",
    *,
    context: ExtractionContext,
    adapter: SourceAdapter[HttpExtractionRequest] | None = None,
) -> RawArtifact:
    """Fetch the election landing page containing constituency identifiers."""
    extractor = adapter if adapter is not None else HttpSourceAdapter()
    return extractor.extract(
        HttpExtractionRequest(
            source_id=SOURCE_ID,
            native_id=f"{cycle}:constituency-index",
            url=f"{base_url(cycle)}/",
            default_content_type="text/html",
        ),
        context=context,
    )


def parse_constituency_map_artifact(artifact: RawArtifact) -> dict[str, str]:
    return _parse_constituency_map(artifact.text())


def _parse_constituency_map(html: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(
        r'href=["\']?[^"\'>]*action=show_candidates&constituency_id=(\d+)[^"\'>]*["\']?[^>]*>(.*?)</a>',
        html, re.S,
    ):
        cid = m.group(1)
        name = _norm_const(re.sub(r"<[^>]+>", " ", m.group(2)))
        if name and name not in out:
            out[name] = cid
    return out


def fetch_constituency_map(
    cycle: str = "LS2024",
    *,
    context: ExtractionContext,
) -> dict[str, str]:
    """Map normalized constituency name -> MyNeta constituency_id (from the election index page)."""
    return parse_constituency_map_artifact(extract_constituency_index(cycle, context=context))


def extract_constituency_candidates(
    constituency_id: str,
    cycle: str = "LS2024",
    *,
    context: ExtractionContext,
    adapter: SourceAdapter[HttpExtractionRequest] | None = None,
) -> RawArtifact:
    """Fetch one constituency's complete candidate listing as a raw artifact."""
    extractor = adapter if adapter is not None else HttpSourceAdapter()
    return extractor.extract(
        HttpExtractionRequest(
            source_id=SOURCE_ID,
            native_id=f"{cycle}:constituency:{constituency_id}",
            url=f"{base_url(cycle)}/index.php",
            default_content_type="text/html",
            params={"action": "show_candidates", "constituency_id": constituency_id},
        ),
        context=context,
    )


def parse_constituency_candidates_artifact(artifact: RawArtifact) -> list[tuple[str, str]]:
    return _parse_constituency_candidates(artifact.text())


def _parse_constituency_candidates(html: str) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for m in re.finditer(r'candidate\.php\?candidate_id=(\d+)[^>]*>([^<]+)', html):
        cid, name = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
        if name and not name.isdigit():
            seen[cid] = name
    return list(seen.items())


def fetch_constituency_candidates(
    constituency_id: str,
    cycle: str = "LS2024",
    *,
    context: ExtractionContext,
) -> list[tuple[str, str]]:
    """Return [(candidate_id, name), ...] for every candidate in a constituency."""
    artifact = extract_constituency_candidates(
        constituency_id,
        cycle,
        context=context,
    )
    return parse_constituency_candidates_artifact(artifact)


def parse_constituency_winner_artifact(artifact: RawArtifact) -> str | None:
    return _parse_constituency_winner(artifact.text())


def _parse_constituency_winner(html: str) -> str | None:
    m = re.search(
        r"candidate\.php\?candidate_id=(\d+)[^>]*>(?:(?!candidate\.php).){0,200}?Winner",
        html,
        re.S | re.I,
    )
    return m.group(1) if m else None


def fetch_constituency_winner(
    constituency_id: str,
    cycle: str = "LS2024",
    *,
    context: ExtractionContext,
) -> str | None:
    """Return the winning candidate_id for a constituency, read from its show_candidates page.

    The winner's row carries a "Winner" marker right after the candidate link, e.g.
    `candidate.php?candidate_id=931>Gaikwad Sanjay Rambhau &nbsp&nbsp Winner`. Used to recover winners
    MyNeta omits from its aggregate show_winners list (esp. state-assembly elections).
    """
    artifact = extract_constituency_candidates(
        constituency_id,
        cycle,
        context=context,
    )
    return parse_constituency_winner_artifact(artifact)
