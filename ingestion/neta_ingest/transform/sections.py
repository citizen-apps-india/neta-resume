"""Parse raw charge text into (code_system, section_number) and derive case severity.

Raw text from MyNeta / affidavits looks like:
    "IPC 302"        -> [("IPC", "302")]
    "u/s 302/34 IPC" -> [("IPC", "302"), ("IPC", "34")]
    "BNS 103"        -> [("BNS", "103")]
    "Sec 13 PCA"     -> [("PCA", "13")]

Case-level severity = the MAX severity across the case's charges (one heinous charge => heinous case).
Severity per section comes from the legal_section catalog (db/seeds/ipc_bns_sections.sql); this module
only parses + rolls up. See docs/severity-rubric.md.
"""

from __future__ import annotations

import re

# Order matters: heinous > serious > minor.
SEVERITY_ORDER = {"minor": 0, "serious": 1, "heinous": 2}
_RANK_TO_SEVERITY = {v: k for k, v in SEVERITY_ORDER.items()}

_CODE_WORDS = {
    "ipc": "IPC",
    "bns": "BNS",
    "pca": "PCA",            # Prevention of Corruption Act
    "rpa": "RPA",            # Representation of the People Act (electoral offences)
}
_SECTION = re.compile(r"\b([0-9]{1,4}[A-Za-z]?)\b")
_CODE = re.compile(r"\b(ipc|bns|pca|rpa)\b", re.IGNORECASE)


def parse_sections(raw: str, default_code: str = "IPC") -> list[tuple[str, str]]:
    """Return [(code_system, section_number), ...] parsed from a raw charge string."""
    if not raw:
        return []
    code_match = _CODE.search(raw)
    code = _CODE_WORDS[code_match.group(1).lower()] if code_match else default_code
    # Strip the code word so it isn't mistaken for a section number.
    cleaned = _CODE.sub(" ", raw)
    sections = [m.group(1).upper() for m in _SECTION.finditer(cleaned)]
    # Dedup, preserve order.
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for sec in sections:
        if sec not in seen:
            seen.add(sec)
            out.append((code, sec))
    return out


def rollup_severity(charge_severities: list[str | None]) -> str | None:
    """Case severity = max over its charges. None if nothing is classified yet."""
    ranks = [SEVERITY_ORDER[s] for s in charge_severities if s in SEVERITY_ORDER]
    if not ranks:
        return None
    return _RANK_TO_SEVERITY[max(ranks)]
