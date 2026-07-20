"""sansad.in committee composition — Lok Sabha standing / other committees + their memberships.

Discovered Digital Sansad endpoints (reachable without an India IP, unlike the question backend):

    /api_ls/committee/allCommittee?loksabha=18&locale=en
        -> [{committeeCode, committeeName, committeeNameH}, ...]                    (the committee list)
    /api_ls/committee/committeeMembers?loksabha=18&committeeCode=N&locale=en
        -> [{committeeName, committeeType, committeeFormationDate,
             memberOrChairperson, memberName, memberHouse}, ...]                    (one committee's roster)

`committeeMembers` carries NO mpsno, so the pipeline matches members to persons by name. Joint
Parliamentary Committees list Rajya Sabha members too (memberHouse distinguishes them).

Official source (trust_tier 1). Every fetch is throttled by neta_core.http and cached by the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

from neta_core.http import client as http

from .client import _clean_name

COMMITTEE_API = "https://sansad.in/api_ls/committee"


@dataclass(slots=True)
class Committee:
    code: int
    name: str


@dataclass(slots=True)
class CommitteeMembership:
    committee_code: int
    committee_name: str
    committee_type: str | None
    formation_date: str | None    # ISO 'YYYY-MM-DD' (committeeFormationDate), or None
    member_name: str              # cleaned "Given Surname"
    is_chairperson: bool          # memberOrChairperson == 'Chairperson'
    member_house: str | None      # 'Lok sabha' / 'Rajya sabha' (JPCs include RS members)


def _json_list(url: str, params: dict) -> list:
    """GET a sansad committee endpoint and return its JSON array. Some committee codes have no roster and
    the gateway answers with a plain-text '404 page not found' (HTTP 400) instead of JSON — treat any
    non-200 / non-JSON / non-list response as empty rather than raising."""
    resp = http.get(url, params=params, headers={"Accept": "application/json"})
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def fetch_committees(loksabha: int = 18) -> list[Committee]:
    """The full list of Lok Sabha committees for a given Lok Sabha (18th by default)."""
    return [
        Committee(code=int(c["committeeCode"]), name=(c.get("committeeName") or "").strip())
        for c in _json_list(f"{COMMITTEE_API}/allCommittee", {"loksabha": loksabha, "locale": "en"})
        if c.get("committeeCode") is not None and (c.get("committeeName") or "").strip()
    ]


def fetch_committee_members(committee_code: int, loksabha: int = 18) -> list[CommitteeMembership]:
    """One committee's members + chairperson. Names are cleaned to 'Given Surname' for person matching."""
    rows = _json_list(
        f"{COMMITTEE_API}/committeeMembers",
        {"loksabha": loksabha, "committeeCode": committee_code, "locale": "en"},
    )
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
            )
        )
    return out
