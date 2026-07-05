"""Normalize Indian politician names for entity-resolution blocking + search.

Goal: collapse spelling/transliteration/honorific noise into a stable key while keeping the raw
variant for audit (stored in person_name_variant). This is the FIRST line of the ER pipeline; the
heavy similarity scoring (SURF) lives in resolve/surf.py.

Examples:
    "Dr. Shashi Tharoor"          -> "shashi tharoor"
    "Smt. Sonia Gandhi"           -> "sonia gandhi"
    "Adv. P. Chidambaram"         -> "chidambaram p"   (token-sorted, initials kept)
    "Narendra  Damodardas Modi"   -> "damodardas modi narendra"
"""

from __future__ import annotations

import re
import unicodedata

import jellyfish

# Honorifics / titles to strip (leading or anywhere as a standalone token).
_HONORIFICS = {
    "dr", "shri", "sri", "smt", "kumari", "km", "adv", "advocate", "prof",
    "mr", "mrs", "ms", "thiru", "selvi", "ch", "md", "mohd", "capt", "col",
    "justice", "hon", "honble",
}
_PUNCT = re.compile(r"[.\-_/\\,]")
_WS = re.compile(r"\s+")


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_name(raw: str) -> str:
    """Produce a transliteration-normalized, honorific-stripped, token-sorted key."""
    if not raw:
        return ""
    s = _strip_accents(raw).lower()
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    tokens = [t for t in s.split(" ") if t and t not in _HONORIFICS]
    # Token-sort so "Narendra Modi" and "Modi Narendra" collide (common in roster vs affidavit order).
    tokens.sort()
    return " ".join(tokens)


def name_tokens(raw: str) -> set[str]:
    """Normalized token set — useful for Jaccard blocking before SURF scoring."""
    return set(normalize_name(raw).split())


def phonetic_key(raw: str) -> str:
    """A metaphone-over-sorted-tokens key for blocking same-SOUND / different-SPELLING names.

    Collapses transliteration variants trigram misses:
        phonetic_key("Muhammad Ali") == phonetic_key("Mohammed Ali")   # both "AL MHMT"
    Order-stable (tokens are normalized+sorted first, codes sorted again); "" for empty input.
    """
    codes = [c for t in normalize_name(raw).split() if (c := jellyfish.metaphone(t))]
    codes.sort()
    return " ".join(codes)
