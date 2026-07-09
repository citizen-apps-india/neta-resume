"""PRS Legislative Research (prsindia.org/mptrack) — per-MP cumulative attendance %.

PRS publishes the attendance % that journalists cite — sittings attended / sittings held over the
whole term. The mptrack LISTING (paginated, 9 MPs/page) gives each member's name, state and a profile
slug, but NOT attendance; attendance lives on each member's PROFILE page, server-rendered in a
`field-name-field-attendance field-type-text` block (e.g. "27 %"). So we paginate the listing to
enumerate members, then fetch a member's profile for the %.

Houses: LS = /mptrack/18th-lok-sabha, RS = /mptrack/rajya-sabha.

LICENSE: non-commercial public resource. Scrape politely (neta_core.http.client throttles); every
profile's raw HTML is cached so each attendance value keeps a snapshot it was derived from.

Caveat (not a bug): ministers, the PM, the Speaker/Deputy Speaker and the Leader of Opposition don't
sign the attendance register, so their profile carries no %, and fetch_attendance returns None.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime

from neta_core.http import client as http
from neta_core.provenance import cache_raw

BASE = "https://prsindia.org"

# house code -> (listing path, profile path segment)
_HOUSE = {
    "ls": ("/mptrack/18th-lok-sabha", "18th-lok-sabha"),
    "rs": ("/mptrack/rajya-sabha", "rajya-sabha"),
}

# Each listing card carries the member's own cumulative counts (server-rendered, no profile fetch):
#   "… Debates Total 0 Questions 80 Pvt Member Bills 0"
_COUNTS = re.compile(r"Debates Total\s*(\d+)\s*Questions\s*(\d+)\s*Pvt Member Bills\s*(\d+)")


def _clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


@dataclass(slots=True)
class PrsMember:
    slug: str
    name: str
    state: str | None
    profile_url: str
    questions: int | None = None       # cumulative activity counts from the listing card
    debates: int | None = None
    private_member_bills: int | None = None
    raw_ref: str | None = None         # cache_raw snapshot of the listing page these counts came from


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
        c = _COUNTS.search(_clean(row))
        return PrsMember(
            slug=slug, name=name, state=state_txt or None,
            profile_url=f"{BASE}/mptrack/{segment}/{slug}",
            debates=int(c.group(1)) if c else None,
            questions=int(c.group(2)) if c else None,
            private_member_bills=int(c.group(3)) if c else None,
        )

    return parse


def parse_listing(html: str, house: str) -> list[PrsMember]:
    """Parse one mptrack listing page's cards into PrsMembers (pure; shared by fetch_roster + tests)."""
    _, segment = _HOUSE[house]
    parse = _row_parser(segment)
    rows = re.split(r'<div[^>]*class="[^"]*views-row', html)[1:]
    return [m for row in rows if (m := parse(row))]


def fetch_roster(house: str) -> list[PrsMember]:
    """Paginate the mptrack listing -> every sitting member (slug, name, state, counts, profile_url)."""
    listing_path, _ = _HOUSE[house]
    members: dict[str, PrsMember] = {}
    # PRS's pager is 1-indexed: page=0 clamps to page 1 (so 0 and 1 are identical), and paging past
    # the last page repeats it. Start at 1 and stop once a page adds no new members (the end clamp).
    page = 1
    while page < 200:  # safety bound (LS ~61 pages, RS ~28)
        resp = http.get(f"{BASE}{listing_path}?page={page}")
        raw_ref = cache_raw(resp.content, suffix=f"_prs_p{page}.html")
        before = len(members)
        for m in parse_listing(resp.text, house):
            if m.slug not in members:
                m.raw_ref = raw_ref     # snapshot of the listing page these counts were read from
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


# The term-wide reporting window PRS stamps on every profile:
#   "Data corresponds to the period from 24-06-2024 to 18-04-2026"
_PERIOD = re.compile(r"period from\s*(\d{2}-\d{2}-\d{4})\s*to\s*(\d{2}-\d{2}-\d{4})")


def parse_report_period(html: str) -> tuple[date, date] | None:
    m = _PERIOD.search(_clean(html))
    if not m:
        return None
    d = [datetime.strptime(g, "%d-%m-%Y").date() for g in m.groups()]
    return d[0], d[1]


def fetch_report_period(house: str) -> tuple[date, date] | None:
    """One profile fetch to read the house's term-wide PRS reporting window (same for all members)."""
    roster = fetch_roster(house)
    if not roster:
        return None
    resp = http.get(roster[0].profile_url)
    return parse_report_period(resp.text)


# --- Individual questions + debates (the content behind the 0024 scorecard counts) -----------------
# The profile page renders a member's questions and debates as two Drupal views tables. Each data row is
# a <tr> of responsive cells tagged with data-title="…". Both tables reuse generic field classes, so we
# key off the human-readable data-title labels, which ARE table-specific:
#   questions -> a "Ministry or Category" cell;   debates -> a "Debate Type" cell.
# Question rows link the official annex PDF on the reachable sansad.in/getFile host; the annex path
# encodes session + question id (e.g. .../annex/187/AU6358_….pdf -> ref "187-AU6358", stable per term).

_TR = re.compile(r"<tr\b.*?</tr>", re.S)
_QUESTION_REF = re.compile(r"/annex/(\d+)/([A-Za-z]+\d+)_")


def _digest(s: str) -> str:
    """Deterministic short hash (built-in hash() is per-process randomized -> breaks idempotency)."""
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()[:10]


@dataclass(slots=True)
class PrsQuestion:
    question_ref: str
    subject: str | None
    ministry: str | None
    question_type: str | None       # 'Starred' | 'Unstarred'
    asked_date: date | None
    document_url: str | None


@dataclass(slots=True)
class PrsDebate:
    debate_ref: str
    title: str | None
    debate_type: str | None
    debate_date: date | None
    document_url: str | None


def _cell(row: str, data_title: str) -> str | None:
    """Inner HTML of the <td data-title="…"> cell, or None if this row has no such cell."""
    m = re.search(rf'<td[^>]*data-title="{re.escape(data_title)}"[^>]*>(.*?)</td>', row, re.S)
    return m.group(1) if m else None


def _href(frag: str | None) -> str | None:
    if not frag:
        return None
    m = re.search(r'href="([^"]+)"', frag)
    return m.group(1).replace("&amp;", "&") if m else None


def _row_date(frag: str | None) -> date | None:
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", frag or "")
    return date(int(m[3]), int(m[2]), int(m[1])) if m else None


def parse_questions(html: str) -> list[PrsQuestion]:
    """Parse a member profile's questions table (pure; shared by fetch_record + tests)."""
    out: list[PrsQuestion] = []
    seen: set[str] = set()
    for row in _TR.findall(html):
        ministry_cell = _cell(row, "Ministry or Category")
        if ministry_cell is None:               # not a question row (header, or a different table)
            continue
        title_cell = _cell(row, "Title")
        url = _href(title_cell)
        subject = _clean(title_cell) if title_cell else None
        d = _row_date(_cell(row, "Date"))
        rm = _QUESTION_REF.search(url or "")
        if rm:
            ref = f"{rm[1]}-{rm[2]}"             # session-scoped annex id, e.g. "187-AU6358"
        else:                                    # ~2% of rows carry no annex PDF -> synthesize a stable ref
            ref = f"q-{d.isoformat() if d else 'na'}-{_digest(subject or '')}"
        if ref in seen:
            continue
        seen.add(ref)
        out.append(PrsQuestion(
            question_ref=ref, subject=subject or None, ministry=_clean(ministry_cell) or None,
            question_type=_clean(_cell(row, "Type")) or None, asked_date=d, document_url=url,
        ))
    return out


def parse_debates(html: str) -> list[PrsDebate]:
    """Parse a member profile's debates table (pure; shared by fetch_record + tests)."""
    out: list[PrsDebate] = []
    seen: set[str] = set()
    for row in _TR.findall(html):
        type_cell = _cell(row, "Debate Type")
        if type_cell is None:                    # not a debate row
            continue
        title_cell = _cell(row, "Debate title/Bill name")
        url = _href(title_cell)
        title = _clean(title_cell) if title_cell else None
        d = _row_date(_cell(row, "Date"))
        # Debates have no per-item public id (the PDF is per sitting-day, shared) -> key on date|title.
        ref = f"{d.isoformat() if d else 'na'}-{_digest(title or '')}"
        if ref in seen:
            continue
        seen.add(ref)
        out.append(PrsDebate(
            debate_ref=ref, title=title or None, debate_type=_clean(type_cell) or None,
            debate_date=d, document_url=url,
        ))
    return out


def fetch_record(member: PrsMember) -> tuple[list[PrsQuestion], list[PrsDebate], str]:
    """One profile fetch -> (questions, debates, raw_cache_relpath). Cheaper than fetching per-table."""
    resp = http.get(member.profile_url)
    rel = cache_raw(resp.content, suffix=f"_prs_{member.slug}.html")
    return parse_questions(resp.text), parse_debates(resp.text), rel
