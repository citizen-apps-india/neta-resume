"""sansad.in (Digital Sansad) — official roster client.

The Lok Sabha member directory is a JS SPA, but the Rajya Sabha sitting-members API is a clean,
paginated JSON endpoint (discovered via the page's network calls):

    https://sansad.in/api_rs/member/sitting-members?page=N&size=100&mpFlag=1&locale=en

It returns name, party (+ code), state ("Nominated" for nominated members), term, status, and an
official photo URL — but NOT affidavit wealth/criminal data (RS members are indirectly elected, so
ADR/MyNeta does not aggregate their affidavits). This is therefore a roster source, not an affidavit one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from neta_ingest.http import client as http

RS_API = "https://sansad.in/api_rs/member/sitting-members"
LS_API = "https://sansad.in/api_ls/member"
_HONORIFICS = re.compile(
    r"\b(dr|shri|smt|kumari|km|adv|advocate|prof|mr|mrs|ms|thiru|selvi|justice|hon|md|mohd|capt|col)\.?\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class RsMember:
    member_id: str          # mpsno -> source_ref.native_id
    name: str               # cleaned "Given Surname"
    party: str | None       # party code (resolved via canon map)
    state: str | None       # None for nominated members
    nominated: bool
    photo_url: str | None
    term: str | None        # e.g. "2022-2028"
    start_year: int | None
    end_year: int | None
    gender: str | None
    age: int | None
    profile_url: str
    official_email: str | None = None   # @*.sansad.in
    office_phone: str | None = None      # local office line


def _clean_name(raw: str) -> str:
    """sansad gives 'Surname, Initial GivenName' (sometimes '@'-prefixed). Render 'Given Surname'."""
    raw = raw.replace("@", " ").strip()
    if "," in raw:
        surname, given = raw.split(",", 1)
    else:
        surname, given = raw, ""
    given = _HONORIFICS.sub("", given)
    surname = _HONORIFICS.sub("", surname)
    given, surname = re.sub(r"\s+", " ", given).strip(), re.sub(r"\s+", " ", surname).strip()
    return " ".join(p for p in (given, surname) if p).strip(" .")


def _years(term: str | None) -> tuple[int | None, int | None]:
    if not term:
        return None, None
    yrs = re.findall(r"((?:19|20)\d{2})", term)
    return (int(yrs[0]) if yrs else None, int(yrs[1]) if len(yrs) > 1 else None)


def _official_email(raw) -> str | None:
    """Return the OFFICIAL (@*.sansad.in) email from sansad's obfuscated value(s), de-obfuscated.

    sansad writes 'name[at]mpls[dot]sansad[dot]in' and may list a personal address too; we keep only the
    official sansad.in channel (Decision: official channels only — no personal contacts)."""
    vals = raw if isinstance(raw, list) else [raw]
    for v in vals:
        if not v:
            continue
        e = str(v).replace("[at]", "@").replace("[dot]", ".").replace(" ", "").strip().lower()
        if e.endswith("sansad.in") and "@" in e:
            return e
    return None


@dataclass(slots=True)
class LsMember:
    member_id: str          # mpsno -> source_ref.native_id
    name: str               # cleaned "Given Surname"
    party: str | None       # party short name (resolved via canon map)
    state: str | None
    constituency: str | None
    photo_url: str | None
    age: int | None
    gender: str | None
    terms: int | None
    profile_url: str
    official_email: str | None = None   # @*.sansad.in
    office_phone: str | None = None      # Delhi/Parliament office line


def fetch_ls_sitting_members(page_size: int = 100) -> list[LsMember]:
    """Fetch all sitting (18th) Lok Sabha members from the official sansad.in API."""
    out: list[LsMember] = []
    page = 1
    while True:
        resp = http.get(
            LS_API,
            params={"loksabha": 18, "sitting": 1, "page": page, "size": page_size, "locale": "en",
                    "state": "", "party": "", "gender": "", "ageFrom": "", "ageTo": "",
                    "noOfTerms": "", "searchText": "", "constituency": "", "month": ""},
            headers={"Accept": "application/json"},
        )
        data = resp.json()
        records = data.get("membersDtoList", [])
        for r in records:
            name = _HONORIFICS.sub("", r.get("mpFirstLastName") or "").strip()
            name = re.sub(r"\s+", " ", name).strip(" .")
            out.append(
                LsMember(
                    member_id=str(r["mpsno"]),
                    name=name,
                    party=(r.get("partySname") or r.get("partyFname") or "").strip() or None,
                    state=(r.get("stateName") or "").strip() or None,
                    constituency=(r.get("constName") or "").strip() or None,
                    photo_url=(r.get("imageUrl") or "").strip() or None,
                    age=r.get("age"),
                    gender=(r.get("gender") or "").strip().title() or None,
                    terms=r.get("noOfTerms"),
                    profile_url=f"https://sansad.in/ls/members?mpsno={r['mpsno']}",
                    official_email=_official_email(r.get("email")),
                    office_phone=(r.get("delhiPhone") or "").strip() or None,
                )
            )
        meta = data.get("metaDatasDto", {})
        if page >= meta.get("totalPages", 1) or not records:
            break
        page += 1
    return out


def fetch_rs_sitting_members(page_size: int = 100) -> list[RsMember]:
    """Fetch all sitting Rajya Sabha members across pages."""
    out: list[RsMember] = []
    page = 1
    while True:
        resp = http.get(
            RS_API,
            params={"page": page, "size": page_size, "mpFlag": 1, "locale": "en",
                    "state": "", "party": "", "gender": "", "ageFrom": "", "ageTo": "",
                    "terms": "", "search": "", "month": "", "minister": ""},
            headers={"Accept": "application/json"},
        )
        data = resp.json()
        records = data.get("records", [])
        for r in records:
            state_raw = (r.get("state") or "").strip()
            nominated = state_raw.lower() == "nominated"
            sy, ey = _years(r.get("term"))
            out.append(
                RsMember(
                    member_id=str(r["mpsno"]),
                    name=_clean_name(r.get("name", "")),
                    party=(r.get("partyCode") or r.get("party") or "").strip() or None,
                    state=None if nominated else (state_raw or None),
                    nominated=nominated,
                    photo_url=(r.get("imageUrl") or "").strip() or None,
                    term=r.get("term"),
                    start_year=sy,
                    end_year=ey,
                    gender=(r.get("gender") or "").strip() or None,
                    age=r.get("age"),
                    profile_url=f"https://sansad.in/rs/members?mpsno={r['mpsno']}",
                    official_email=_official_email(r.get("emailID")),
                    office_phone=(r.get("localTele") or "").strip() or None,
                )
            )
        meta = data.get("_metadata", {})
        if page >= meta.get("totalPages", 1) or not records:
            break
        page += 1
    return out
