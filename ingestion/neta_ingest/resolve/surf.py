"""SURF name-similarity integration (TCPD, Ashoka).

SURF's similarity metric is purpose-built for Indian-name transliteration/spelling variants. Adopt it
(or port its metric) as the primary string scorer rather than hand-rolling fuzzy matching.
Ref: https://tcpd.ashoka.edu.in/surf-an-entity-mapping-and-resolution-system-for-indian/
"""

from __future__ import annotations


def similarity(name_a: str, name_b: str) -> float:
    """Return 0..1 name similarity using the SURF metric. TODO: integrate/port SURF."""
    raise NotImplementedError("surf.similarity — integrate SURF or port its Indian-name similarity metric.")
