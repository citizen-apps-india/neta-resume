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

_SECTION = re.compile(r"\b([0-9]{1,4}[A-Za-z]?)\b")
_CODE = re.compile(r"\b(ipc|bns|pca|rpa)\b", re.IGNORECASE)
# Statute phrases MyNeta writes in the "Other Acts" column, mapped to our code_system.
_STATUTE_PHRASES = [
    (re.compile(r"R\.?\s*P\.?\s*Act|representation of the people", re.I), "RPA"),
    (re.compile(r"P\.?\s*C\.?\s*Act|prevention of corruption", re.I), "PCA"),
]
_CODE_WORDS = {"ipc": "IPC", "bns": "BNS", "pca": "PCA", "rpa": "RPA"}


def _detect_code(raw: str, default_code: str) -> str:
    code_match = _CODE.search(raw)
    if code_match:
        return _CODE_WORDS[code_match.group(1).lower()]
    for pat, code in _STATUTE_PHRASES:
        if pat.search(raw):
            return code
    return default_code


def has_statute_marker(raw: str) -> bool:
    """True if the text explicitly names a statute (IPC/BNS/PCA/RPA or a phrase like "R.P. Act").

    Used to decide whether bare numbers in a free-text column are safe to read as section numbers.
    Older MyNeta layouts (LS2014/LS2009) bundle case metadata ("Case No-294/10, FIR No-191/2009,
    Thana ..., Court ...") into the same "Other Acts" column that newer pages use for real statute
    refs — so without a marker those numbers are case/FIR numbers and years, not charges.
    """
    if not raw:
        return False
    if _CODE.search(raw):
        return True
    return any(pat.search(raw) for pat, _ in _STATUTE_PHRASES)


def parse_sections(raw: str, default_code: str = "IPC") -> list[tuple[str, str]]:
    """Return [(code_system, section_number), ...] parsed from a raw charge string.

    Recognizes inline code words (IPC/BNS/PCA/RPA) and statute phrases ("R.P. Act",
    "Prevention of Corruption Act"). Numbers in parentheses like "126(2)" yield "126".
    """
    if not raw:
        return []
    code = _detect_code(raw, default_code)
    # Strip the code word so it isn't mistaken for a section number, and drop parenthetical sub-section
    # refs ("351(1)", "196(1)(A)" -> "351", "196") so they aren't read as separate sections (1, A).
    cleaned = _CODE.sub(" ", raw)
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
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
