"""sansad.in (Digital Sansad) — official roster client.

The Lok Sabha member directory is a JS SPA, but the Rajya Sabha sitting-members API is a clean,
paginated JSON endpoint (discovered via the page's network calls):

    https://sansad.in/api_rs/member/sitting-members?page=N&size=100&mpFlag=1&locale=en

It returns name, party (+ code), state ("Nominated" for nominated members), term, status, and an
official photo URL — but NOT affidavit wealth/criminal data (RS members are indirectly elected, so
ADR/MyNeta does not aggregate their affidavits). This is therefore a roster source, not an affidavit one.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from neta_core.pipeline import (
    ExtractionContext,
    HttpExtractionRequest,
    HttpSourceAdapter,
    RawArtifact,
    SourceAdapter,
)

RS_API = "https://sansad.in/api_rs/member/sitting-members"
LS_API = "https://sansad.in/api_ls/member"
SOURCE_ID = "digital_sansad.members"
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
    raw_ref: str | None = None


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
    raw_ref: str | None = None


def _ls_params(page: int, page_size: int) -> dict[str, object]:
    return {
        "loksabha": 18,
        "sitting": 1,
        "page": page,
        "size": page_size,
        "locale": "en",
        "state": "",
        "party": "",
        "gender": "",
        "ageFrom": "",
        "ageTo": "",
        "noOfTerms": "",
        "searchText": "",
        "constituency": "",
        "month": "",
    }


def extract_ls_members_page(
    page: int,
    page_size: int,
    *,
    context: ExtractionContext,
    adapter: SourceAdapter[HttpExtractionRequest] | None = None,
) -> RawArtifact:
    extractor = adapter if adapter is not None else HttpSourceAdapter()
    return extractor.extract(
        HttpExtractionRequest(
            source_id=SOURCE_ID,
            native_id=f"ls:18:page:{page}:size:{page_size}",
            url=LS_API,
            default_content_type="application/json",
            headers={"Accept": "application/json"},
            params=_ls_params(page, page_size),
        ),
        context=context,
    )


def parse_ls_members_page(artifact: RawArtifact) -> tuple[list[LsMember], int]:
    return _parse_ls_members_data(json.loads(artifact.text()), artifact.provenance_ref)


def _parse_ls_members_data(
    data: dict,
    raw_ref: str | None,
) -> tuple[list[LsMember], int]:
    records = data.get("membersDtoList", [])
    members: list[LsMember] = []
    for record in records:
        name = _HONORIFICS.sub("", record.get("mpFirstLastName") or "").strip()
        name = re.sub(r"\s+", " ", name).strip(" .")
        members.append(
            LsMember(
                member_id=str(record["mpsno"]),
                name=name,
                party=(record.get("partySname") or record.get("partyFname") or "").strip()
                or None,
                state=(record.get("stateName") or "").strip() or None,
                constituency=(record.get("constName") or "").strip() or None,
                photo_url=(record.get("imageUrl") or "").strip() or None,
                age=record.get("age"),
                gender=(record.get("gender") or "").strip().title() or None,
                terms=record.get("noOfTerms"),
                profile_url=f"https://sansad.in/ls/members?mpsno={record['mpsno']}",
                official_email=_official_email(record.get("email")),
                office_phone=(record.get("delhiPhone") or "").strip() or None,
                raw_ref=raw_ref,
            )
        )
    return members, int(data.get("metaDatasDto", {}).get("totalPages", 1))


def fetch_ls_sitting_members(
    page_size: int = 100,
    *,
    context: ExtractionContext,
    adapter: SourceAdapter[HttpExtractionRequest] | None = None,
) -> list[LsMember]:
    """Fetch all sitting (18th) Lok Sabha members from the official sansad.in API."""
    out: list[LsMember] = []
    page = 1
    while True:
        artifact = extract_ls_members_page(page, page_size, context=context, adapter=adapter)
        members, total_pages = parse_ls_members_page(artifact)
        out.extend(members)
        if page >= total_pages or not members:
            return out
        page += 1


def _rs_params(page: int, page_size: int) -> dict[str, object]:
    return {
        "page": page,
        "size": page_size,
        "mpFlag": 1,
        "locale": "en",
        "state": "",
        "party": "",
        "gender": "",
        "ageFrom": "",
        "ageTo": "",
        "terms": "",
        "search": "",
        "month": "",
        "minister": "",
    }


def extract_rs_members_page(
    page: int,
    page_size: int,
    *,
    context: ExtractionContext,
    adapter: SourceAdapter[HttpExtractionRequest] | None = None,
) -> RawArtifact:
    extractor = adapter if adapter is not None else HttpSourceAdapter()
    return extractor.extract(
        HttpExtractionRequest(
            source_id=SOURCE_ID,
            native_id=f"rs:sitting:page:{page}:size:{page_size}",
            url=RS_API,
            default_content_type="application/json",
            headers={"Accept": "application/json"},
            params=_rs_params(page, page_size),
        ),
        context=context,
    )


def parse_rs_members_page(artifact: RawArtifact) -> tuple[list[RsMember], int]:
    return _parse_rs_members_data(json.loads(artifact.text()), artifact.provenance_ref)


def _parse_rs_members_data(
    data: dict,
    raw_ref: str | None,
) -> tuple[list[RsMember], int]:
    records = data.get("records", [])
    members: list[RsMember] = []
    for record in records:
        state_raw = (record.get("state") or "").strip()
        nominated = state_raw.lower() == "nominated"
        start_year, end_year = _years(record.get("term"))
        members.append(
            RsMember(
                member_id=str(record["mpsno"]),
                name=_clean_name(record.get("name", "")),
                party=(record.get("partyCode") or record.get("party") or "").strip() or None,
                state=None if nominated else (state_raw or None),
                nominated=nominated,
                photo_url=(record.get("imageUrl") or "").strip() or None,
                term=record.get("term"),
                start_year=start_year,
                end_year=end_year,
                gender=(record.get("gender") or "").strip() or None,
                age=record.get("age"),
                profile_url=f"https://sansad.in/rs/members?mpsno={record['mpsno']}",
                official_email=_official_email(record.get("emailID")),
                office_phone=(record.get("localTele") or "").strip() or None,
                raw_ref=raw_ref,
            )
        )
    return members, int(data.get("_metadata", {}).get("totalPages", 1))


def fetch_rs_sitting_members(
    page_size: int = 100,
    *,
    context: ExtractionContext,
    adapter: SourceAdapter[HttpExtractionRequest] | None = None,
) -> list[RsMember]:
    """Fetch all sitting Rajya Sabha members across pages."""
    out: list[RsMember] = []
    page = 1
    while True:
        artifact = extract_rs_members_page(page, page_size, context=context, adapter=adapter)
        members, total_pages = parse_rs_members_page(artifact)
        out.extend(members)
        if page >= total_pages or not members:
            return out
        page += 1
