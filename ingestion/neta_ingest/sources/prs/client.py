"""PRS Legislative Research (prsindia.org/mptrack) — per-MP cumulative attendance %.

PRS publishes the attendance % that journalists cite — sittings attended / sittings held over the
whole term. The mptrack LISTING (paginated, 9 MPs/page) gives each member's name, state and a profile
slug, but NOT attendance; attendance lives on each member's PROFILE page, server-rendered in a
`field-name-field-attendance field-type-text` block (e.g. "27 %"). So we paginate the listing to
enumerate members, then fetch a member's profile for the %.

Houses: LS = /mptrack/18th-lok-sabha, RS = /mptrack/rajya-sabha.

LICENSE: non-commercial public resource. Scrape politely (neta_ingest.http.client throttles); every
profile's raw HTML is cached so each attendance value keeps a snapshot it was derived from.

Caveat (not a bug): ministers, the PM, the Speaker/Deputy Speaker and the Leader of Opposition don't
sign the attendance register, so their profile carries no %, and fetch_attendance returns None.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from neta_ingest.http import client as http
from neta_ingest.provenance import cache_raw

BASE = "https://prsindia.org"

# house code -> (listing path, profile path segment)
_HOUSE = {
    "ls": ("/mptrack/18th-lok-sabha", "18th-lok-sabha"),
    "rs": ("/mptrack/rajya-sabha", "rajya-sabha"),
}


@dataclass(slots=True)
class PrsMember:
    slug: str
    name: str
    state: str | None
    profile_url: str


def _row_parser(segment: str):
    anchor = re.compile(
        rf'<a href="/mptrack/{segment}/([a-z0-9-]+)"[^>]*>\s*([^<]+?)\s*</a>'
    )
    state = re.compile(r'views-field-field-net-revenue-railway[^>]*>(.*?)</div>', re.S)

    def parse(row: str) -> PrsMember | None:
        a = anchor.search(row)
        if not a:
            return None
        name = a.group(2).strip()
        if not name or name.isdigit():
            return None
        st = state.search(row)
        state_txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", st.group(1))).strip() if st else None
        slug = a.group(1)
        return PrsMember(slug=slug, name=name, state=state_txt or None,
                         profile_url=f"{BASE}/mptrack/{segment}/{slug}")

    return parse


def fetch_roster(house: str) -> list[PrsMember]:
    """Paginate the mptrack listing -> every sitting member (slug, name, state, profile_url)."""
    listing_path, segment = _HOUSE[house]
    parse = _row_parser(segment)
    members: dict[str, PrsMember] = {}
    # PRS's pager is 1-indexed: page=0 clamps to page 1 (so 0 and 1 are identical), and paging past
    # the last page repeats it. Start at 1 and stop once a page adds no new members (the end clamp).
    page = 1
    while page < 200:  # safety bound (LS ~61 pages, RS ~28)
        resp = http.get(f"{BASE}{listing_path}?page={page}")
        rows = re.split(r'<div[^>]*class="[^"]*views-row', resp.text)[1:]
        before = len(members)
        for row in rows:
            m = parse(row)
            if m and m.slug not in members:
                members[m.slug] = m
        if len(members) == before:  # page produced no new members -> past the last page
            break
        page += 1
    return list(members.values())


# The selected MP's own % — distinct from the national/state averages, whose fields are
# `field-name-field-national-attendance` / `...-state-attendance`. Anchoring on the exact class prefix
# `field-name-field-attendance field-type-text` matches only the member's own block.
_ATTENDANCE_ANCHOR = "field-name-field-attendance field-type-text"
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def parse_attendance(html: str) -> float | None:
    i = html.find(_ATTENDANCE_ANCHOR)
    if i < 0:
        return None
    seg = re.sub(r"<[^>]+>", " ", html[i : i + 200])
    m = _PCT.search(seg)
    return float(m.group(1)) if m else None


def fetch_attendance(member: PrsMember) -> tuple[float | None, str]:
    """Fetch + parse one member's profile. Returns (attendance_pct_or_None, raw_cache_relpath)."""
    resp = http.get(member.profile_url)
    rel = cache_raw(resp.content, suffix=f"_prs_{member.slug}.html")
    return parse_attendance(resp.text), rel
