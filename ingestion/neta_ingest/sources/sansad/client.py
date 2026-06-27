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
    m = re.findall(r"(19|20)\d{2}", term)
    yrs = re.findall(r"((?:19|20)\d{2})", term)
    return (int(yrs[0]) if yrs else None, int(yrs[1]) if len(yrs) > 1 else None)


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
                )
            )
        meta = data.get("_metadata", {})
        if page >= meta.get("totalPages", 1) or not records:
            break
        page += 1
    return out
