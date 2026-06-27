"""Parse MyNeta (ADR) HTML into structured records.

MyNeta is server-rendered HTML (no JS needed). Two page types:
  - winners/candidates LIST: index.php?action=show_winners -> rows of candidate_id + summary
  - candidate DETAIL: candidate.php?candidate_id=N -> full affidavit (assets, criminal cases)

The detail page is laid out with <h3> section anchors:
  "Assets & Liabilities", "Details of Criminal Cases", "Cases where Pending",
  "Cases where Convicted", "Educational Details", ...

These parsers are intentionally regex/text based: MyNeta's markup is old, deeply nested tables with
inconsistent attributes, so anchoring on stable visible labels is more robust than CSS paths.
Validated against tests/fixtures/myneta_candidate_5395.html.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from selectolax.parser import HTMLParser

from neta_ingest.transform.money import parse_rupees
from neta_ingest.transform.sections import parse_sections


def _strip_tags(s: str) -> str:
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass(slots=True)
class WinnerRow:
    candidate_id: str
    name: str
    detail_url: str


@dataclass(slots=True)
class ParsedCase:
    serial: str | None
    fir_number: str | None
    case_number: str | None
    court: str | None
    raw_sections: str                          # display string, e.g. "188 | Section-126(2) R.P. Act"
    sections: list[tuple[str, str]]            # structured: [("IPC","188"), ("RPA","126")]
    charges_framed: bool
    is_convicted: bool


@dataclass(slots=True)
class ParsedCandidate:
    candidate_id: str | None
    name: str
    party: str | None
    constituency: str | None
    state: str | None
    age: int | None
    education: str | None
    total_assets: int            # integer rupees
    total_liabilities: int
    criminal_cases: list[ParsedCase] = field(default_factory=list)


_CAND_LINK = re.compile(r'candidate\.php\?candidate_id=(\d+)')


def parse_winners(html: str, base_url: str) -> list[WinnerRow]:
    """Extract (candidate_id, name, url) rows from a winners/candidates list page."""
    seen: dict[str, WinnerRow] = {}
    # MyNeta anchors are UNQUOTED and may include a leading path, e.g.
    #   <a href=/candidate.php?candidate_id=5395>
    #   <a href=/LokSabha2024/candidate.php?candidate_id=5395>Godam Nagesh
    # Keep the row that carries the candidate's name; fall back to id-only rows.
    for m in re.finditer(
        r'<a\s+href=["\']?/?(?:[A-Za-z0-9_]+/)?candidate\.php\?candidate_id=(\d+)["\']?[^>]*>(.*?)</a>',
        html, re.S,
    ):
        cid = m.group(1)
        name = _strip_tags(m.group(2))
        url = f"{base_url}/candidate.php?candidate_id={cid}"
        if name and not name.isdigit():
            seen[cid] = WinnerRow(candidate_id=cid, name=name, detail_url=url)
        elif cid not in seen:
            seen[cid] = WinnerRow(candidate_id=cid, name="", detail_url=url)
    return list(seen.values())


def parse_candidate(html: str, candidate_id: str | None = None) -> ParsedCandidate:
    """Parse a MyNeta candidate detail page into a ParsedCandidate."""
    text = _strip_tags(html)

    # Name: <h2>NAME (Winner)</h2>  (fall back to title)
    name = None
    h2 = re.search(r"<h2[^>]*>(.*?)</h2>", html, re.S)
    if h2:
        name = re.sub(r"\s*\((?:Winner|Candidate)\).*$", "", _strip_tags(h2.group(1))).strip()
    if not name:
        t = re.search(r"<title>(.*?)</title>", html, re.S)
        name = _strip_tags(t.group(1)) if t else "UNKNOWN"
    # Strip a leading election prefix ("Lok Sabha 2024", "Rajya Sabha", "<State> 2023") + trailing tag.
    name = re.sub(r"^(?:Lok Sabha|Rajya Sabha|[A-Za-z ]+?)\s*\d{4}\s*", "", name).strip()
    name = re.sub(r"\s*\((?:Winner|Candidate)\).*$", "", name).strip()

    party = None
    # Party names can be long and contain dashes/en-dashes ("NCP – Sharadchandra Pawar"),
    # so match permissively up to the next header delimiter.
    mp = re.search(r"Party:\s*(.+?)\s+(?:S/o|D/o|W/o|Age|Name Enrolled)", text)
    if mp:
        party = mp.group(1).strip() or None

    # Constituency + state from header: "NAME (Winner) ADILABAD (ST) (TELANGANA) Party:"
    constituency = state = None
    mc = re.search(r"\(Winner\)\s*(.*?)\s*Party:", text) or re.search(r"\(Candidate\)\s*(.*?)\s*Party:", text)
    if mc:
        seat = mc.group(1).strip()
        ms = re.search(r"^(.*?)\(([^()]+)\)\s*$", seat)
        if ms:
            constituency = re.sub(r"\([^)]*\)", "", ms.group(1)).strip() or ms.group(1).strip()
            state = ms.group(2).strip()
        else:
            constituency = seat

    age = None
    ma = re.search(r"Age:\s*(\d+)", text)
    if ma:
        age = int(ma.group(1))

    education = None
    me = re.search(r"Educational Details\s*Category:\s*(.*?)\s*(?:Details of PAN|Details of Criminal|$)", text)
    if me:
        education = me.group(1).strip()[:200]

    # Assets & Liabilities: "Assets: Rs 3,09,16,833 ~3 Crore+ Liabilities: Rs 29,01,575 ~29 Lacs+"
    total_assets = total_liabilities = 0
    ma2 = re.search(r"Assets:\s*Rs\s*([0-9,]+)", text)
    if ma2:
        total_assets = parse_rupees(ma2.group(1))
    ml = re.search(r"Liabilities:\s*Rs\s*([0-9,]+)", text)
    if ml:
        total_liabilities = parse_rupees(ml.group(1))

    cases = _parse_cases(html)

    return ParsedCandidate(
        candidate_id=candidate_id,
        name=name,
        party=party,
        constituency=constituency,
        state=state,
        age=age,
        education=education,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        criminal_cases=cases,
    )


def _cell_text(node) -> str:
    return re.sub(r"\s+", " ", node.text(strip=True)).strip()


def _col_index(headers: list[str], *needles: str) -> int | None:
    for i, h in enumerate(headers):
        if any(n.lower() in h.lower() for n in needles):
            return i
    return None


def _parse_cases(html: str) -> list[ParsedCase]:
    """Parse the criminal-case tables (Pending + Convicted) by HTML table structure.

    A case table is identified by an 'IPC Sections Applicable' header cell. Convicted tables carry a
    'Punishment Imposed' column instead of 'Charges Framed'. Columns are mapped by header name, so the
    parser is resilient to MyNeta's wildly varying FIR/case-number formats.
    """
    cases: list[ParsedCase] = []
    tree = HTMLParser(html)
    for table in tree.css("table"):
        rows = table.css("tr")
        if not rows:
            continue
        headers = [_cell_text(c) for c in rows[0].css("td, th")]
        if _col_index(headers, "IPC Sections") is None:
            continue
        convicted = _col_index(headers, "Punishment Imposed") is not None
        i_serial = _col_index(headers, "Serial")
        i_fir = _col_index(headers, "FIR")
        i_case = _col_index(headers, "Case No")
        i_court = _col_index(headers, "Court")
        i_ipc = _col_index(headers, "IPC Sections")
        i_other = _col_index(headers, "Other Details", "Other Acts")
        i_framed = _col_index(headers, "Charges Framed")

        def cell(cells: list[str], i: int | None) -> str:
            return cells[i] if i is not None and i < len(cells) else ""

        for r in rows[1:]:
            cells = [_cell_text(c) for c in r.css("td")]
            serial = cell(cells, i_serial).strip()
            if not serial.isdigit():
                continue  # skip non-data rows (sub-headers, "No Cases", etc.)
            ipc_raw = cell(cells, i_ipc)
            other_raw = cell(cells, i_other)
            sections = parse_sections(ipc_raw, default_code="IPC")
            if other_raw:
                sections += parse_sections(other_raw, default_code="IPC")
            raw_display = " | ".join(x for x in (ipc_raw, other_raw) if x)
            cases.append(
                ParsedCase(
                    serial=serial,
                    fir_number=cell(cells, i_fir) or None,
                    case_number=cell(cells, i_case) or None,
                    court=cell(cells, i_court)[:120] or None,
                    raw_sections=raw_display,
                    sections=sections,
                    charges_framed=cell(cells, i_framed).strip().lower() == "yes",
                    is_convicted=convicted,
                )
            )
    return cases
