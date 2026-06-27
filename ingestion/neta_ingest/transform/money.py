"""Parse Indian rupee amounts from affidavit text into INTEGER RUPEES.

Affidavit/MyNeta amounts come in many shapes:
    "Rs 1,23,45,678"          -> 12345678
    "Rs 5 Crore+"             -> 50000000
    "Rs 2,50,000 ~ 2.5 Lakh"  -> 250000   (take the numeric, ignore the ~human gloss)
    "1.5 crore"               -> 15000000
    "Nil" / "" / "-"          -> 0

Store integer rupees only. Never store a float (precision) or the raw string as a value.
See docs/schema.md (Money).
"""

from __future__ import annotations

import re

LAKH = 100_000
CRORE = 10_000_000

_NIL = {"", "nil", "none", "-", "na", "n/a", "not given", "0"}
# A trailing "~ 2.5 Lakh"/"Thousand+" human gloss MyNeta appends after the exact figure.
_GLOSS = re.compile(r"~.*$")
_UNIT = re.compile(r"\b(crore|cr|lakh|lac|thousand)\b", re.IGNORECASE)


def parse_rupees(text: str | None) -> int:
    """Best-effort parse of an affidavit amount string to integer rupees."""
    if text is None:
        return 0
    s = text.strip().lower()
    if s in _NIL:
        return 0

    # Drop currency markers and the trailing "~ x Lakh" gloss; keep the precise figure if present.
    s = s.replace("rs.", " ").replace("rs", " ").replace("₹", " ").replace("inr", " ")
    s = _GLOSS.sub("", s).strip()

    unit_match = _UNIT.search(s)
    # Pull the first numeric token (handles Indian grouping "1,23,45,678" and decimals "1.5").
    num_match = re.search(r"[0-9][0-9,]*(?:\.[0-9]+)?", s)
    if not num_match:
        return 0
    raw_num = num_match.group(0).replace(",", "")
    try:
        value = float(raw_num)
    except ValueError:
        return 0

    if unit_match:
        unit = unit_match.group(1).lower()
        if unit in ("crore", "cr"):
            value *= CRORE
        elif unit in ("lakh", "lac"):
            value *= LAKH
        elif unit == "thousand":
            value *= 1_000

    return int(round(value))
