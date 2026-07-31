"""sansad.in committee composition — Lok Sabha standing / other committees + their memberships.

Discovered Digital Sansad endpoints (reachable without an India IP, unlike the question backend):

    /api_ls/committee/allCommittee?loksabha=18&locale=en
        -> [{committeeCode, committeeName, committeeNameH}, ...]                    (the committee list)
    /api_ls/committee/committeeMembers?loksabha=18&committeeCode=N&locale=en
        -> [{committeeName, committeeType, committeeFormationDate,
             memberOrChairperson, memberName, memberHouse}, ...]                    (one committee's roster)

`committeeMembers` carries NO mpsno, so the pipeline matches members to persons by name. Joint
Parliamentary Committees list Rajya Sabha members too (memberHouse distinguishes them).

Official source (trust_tier 1). Every fetch is throttled and captured by the raw-envelope adapter.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from neta_core.pipeline import (
    ExtractionContext,
    HttpExtractionRequest,
    HttpSourceAdapter,
    RawArtifact,
    SourceAdapter,
)

from .client import _clean_name

COMMITTEE_API = "https://sansad.in/api_ls/committee"
SOURCE_ID = "digital_sansad.committees"


@dataclass(slots=True)
class Committee:
    code: int
    name: str
    raw_ref: str | None = None


@dataclass(slots=True)
class CommitteeMembership:
    committee_code: int
    committee_name: str
    committee_type: str | None
    formation_date: str | None    # ISO 'YYYY-MM-DD' (committeeFormationDate), or None
    member_name: str              # cleaned "Given Surname"
    is_chairperson: bool          # memberOrChairperson == 'Chairperson'
    member_house: str | None      # 'Lok sabha' / 'Rajya sabha' (JPCs include RS members)
    raw_ref: str | None = None


def _artifact_json_list(artifact: RawArtifact) -> list:
    if artifact.envelope.http_metadata.get("status_code") != "200":
        return []
    try:
        data = json.loads(artifact.text())
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def extract_committees(
    loksabha: int = 18,
    *,
    context: ExtractionContext,
    adapter: SourceAdapter[HttpExtractionRequest] | None = None,
) -> RawArtifact:
    extractor = adapter if adapter is not None else HttpSourceAdapter()
    return extractor.extract(
        HttpExtractionRequest(
            source_id=SOURCE_ID,
            native_id=f"ls:{loksabha}:committees",
            url=f"{COMMITTEE_API}/allCommittee",
            default_content_type="application/json",
            headers={"Accept": "application/json"},
            params={"loksabha": loksabha, "locale": "en"},
        ),
        context=context,
    )


def parse_committees_artifact(artifact: RawArtifact) -> list[Committee]:
    return [
        Committee(
            code=int(row["committeeCode"]),
            name=(row.get("committeeName") or "").strip(),
            raw_ref=artifact.provenance_ref,
        )
        for row in _artifact_json_list(artifact)
        if row.get("committeeCode") is not None and (row.get("committeeName") or "").strip()
    ]


def fetch_committees(
    loksabha: int = 18,
    *,
    context: ExtractionContext,
) -> list[Committee]:
    """The full list of Lok Sabha committees for a given Lok Sabha (18th by default)."""
    return parse_committees_artifact(extract_committees(loksabha, context=context))


def extract_committee_members(
    committee_code: int,
    loksabha: int = 18,
    *,
    context: ExtractionContext,
    adapter: SourceAdapter[HttpExtractionRequest] | None = None,
) -> RawArtifact:
    extractor = adapter if adapter is not None else HttpSourceAdapter()
    return extractor.extract(
        HttpExtractionRequest(
            source_id=SOURCE_ID,
            native_id=f"ls:{loksabha}:committee:{committee_code}:members",
            url=f"{COMMITTEE_API}/committeeMembers",
            default_content_type="application/json",
            headers={"Accept": "application/json"},
            params={
                "loksabha": loksabha,
                "committeeCode": committee_code,
                "locale": "en",
            },
            accepted_status_codes=frozenset({200, 400}),
        ),
        context=context,
    )


def parse_committee_members_artifact(
    artifact: RawArtifact,
    committee_code: int,
) -> list[CommitteeMembership]:
    rows = _artifact_json_list(artifact)
    out: list[CommitteeMembership] = []
    for r in rows:
        role = (r.get("memberOrChairperson") or "").strip().lower()
        name = _clean_name(r.get("memberName") or "")
        if not name:
            continue
        out.append(
            CommitteeMembership(
                committee_code=committee_code,
                committee_name=(r.get("committeeName") or "").strip(),
                committee_type=(r.get("committeeType") or "").strip() or None,
                formation_date=(r.get("committeeFormationDate") or "").strip() or None,
                member_name=name,
                is_chairperson=role.startswith("chair"),
                member_house=(r.get("memberHouse") or "").strip() or None,
                raw_ref=artifact.provenance_ref,
            )
        )
    return out


def fetch_committee_members(
    committee_code: int,
    loksabha: int = 18,
    *,
    context: ExtractionContext,
) -> list[CommitteeMembership]:
    """One committee's members + chairperson. Names are cleaned to 'Given Surname' for matching."""
    artifact = extract_committee_members(
        committee_code,
        loksabha,
        context=context,
    )
    return parse_committee_members_artifact(artifact, committee_code)
