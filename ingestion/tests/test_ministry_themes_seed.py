"""Integrity guard for the ministry -> theme seed (db/seeds/ministry_themes.sql).

The mapping itself is applied in SQL (a JOIN at read time), but this DB-free test catches seed typos:
every theme must be one of the agreed set, and every ministry_key must be unique + lowercased (the read
path joins on lower(trim(ministry)), so an upper-case key would silently never match).
"""

import re
from pathlib import Path

SEED = Path(__file__).parents[2] / "db" / "seeds" / "ministry_themes.sql"

ALLOWED_THEMES = {
    "Economy & Industry",
    "Health",
    "Education & Skills",
    "Social Welfare & Justice",
    "Agriculture & Environment",
    "Infrastructure & Connectivity",
    "Governance & External",
}

_ROW = re.compile(r"\('([^']+)',\s*'([^']+)'\)")


def _rows() -> list[tuple[str, str]]:
    return _ROW.findall(SEED.read_text(encoding="utf-8"))


def test_seed_has_rows():
    assert len(_rows()) >= 50               # ~52 live ministries + common extras


def test_all_themes_are_allowed():
    bad = {theme for _, theme in _rows() if theme not in ALLOWED_THEMES}
    assert not bad, f"unexpected theme(s): {bad}"


def test_keys_unique_and_lowercased():
    keys = [k for k, _ in _rows()]
    assert len(keys) == len(set(keys)), "duplicate ministry_key in seed"
    assert all(k == k.lower() for k in keys), "ministry_key must be lowercased to match the read-time join"
