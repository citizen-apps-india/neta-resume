"""Canonicalize party records: merge abbreviation/full-name duplicates into one canonical party.

MyNeta gives party names inconsistently across cycles — 2019 affidavits use ECI abbreviations
("SHS", "AIMIM", "IUML", "LJP") while 2024 uses full names ("Shiv Sena", ...). Ingested verbatim,
these become separate party rows, which (a) splits a party's MP count and (b) fabricates party-switch
events (e.g. "SHS -> Shiv Sena"). This pass folds variants into a canonical party and deletes any
switch event that collapses to from == to.

The map is curated (not inferred) — party identity is too consequential to fuzzy-match.
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope

# variant (lower-cased name OR abbr) -> canonical display name
CANON: dict[str, str] = {
    "bjp": "Bharatiya Janata Party",
    "inc": "Indian National Congress",
    "shs": "Shiv Sena",
    "ss": "Shiv Sena",
    "aimim": "All India Majlis-E-Ittehadul Muslimeen",
    "iuml": "Indian Union Muslim League",
    "ljp": "Lok Janshakti Party(Ram Vilas)",
    "ysrcp": "Yuvajana Sramika Rythu Congress Party",
    "bjd": "Biju Janata Dal",
    "rjd": "Rashtriya Janata Dal",
    "jmm": "Jharkhand Mukti Morcha",
    "sad": "Shiromani Akali Dal",
    "aap": "Aam Aadmi Party",
    "tmc": "All India Trinamool Congress",
    "aitc": "All India Trinamool Congress",
    "dmk": "Dravida Munnetra Kazhagam",
    "tdp": "Telugu Desam Party",
    "sp": "Samajwadi Party",
    "ncp": "Nationalist Congress Party",
    "jdu": "Janata Dal (United)",
    "jd(u)": "Janata Dal (United)",
    "jds": "Janata Dal (Secular)",
    "jd(s)": "Janata Dal (Secular)",
    "rld": "Rashtriya Lok Dal",
    "vck": "Viduthalai Chiruthaigal Katchi",
    "cpi(m)": "Communist Party of India (Marxist)",
    "cpi": "Communist Party of India",
    "ajsu party": "AJSU Party",
}


def _canon_name(name: str, abbr: str | None) -> str:
    for key in (name.strip().lower(), (abbr or "").strip().lower()):
        if key in CANON:
            return CANON[key]
    return name.strip()


def run() -> None:
    with session_scope() as s:
        parties = s.execute(text("SELECT id, canonical_name, abbr FROM party")).all()
        groups: dict[str, list] = {}
        for p in parties:
            groups.setdefault(_canon_name(p.canonical_name, p.abbr), []).append(p)

        merged = 0
        for cn, members in groups.items():
            target = next((m for m in members if m.canonical_name.strip() == cn), members[0])
            if target.canonical_name.strip() != cn:
                s.execute(text("UPDATE party SET canonical_name = :cn WHERE id = :id"), {"cn": cn, "id": target.id})
            _add_alias(s, target.id, target.canonical_name)
            for m in members:
                if m.id == target.id:
                    continue
                _add_alias(s, target.id, m.canonical_name)
                for tbl, col in (
                    ("office_term", "party_id"), ("party_affiliation", "party_id"),
                    ("party_switch_event", "from_party_id"), ("party_switch_event", "to_party_id"),
                ):
                    s.execute(text(f"UPDATE {tbl} SET {col} = :t WHERE {col} = :m"), {"t": target.id, "m": m.id})
                s.execute(text("DELETE FROM party_alias WHERE party_id = :m"), {"m": m.id})
                s.execute(text("DELETE FROM party WHERE id = :m"), {"m": m.id})
                merged += 1

        # false switches that collapsed to the same party
        false_sw = s.execute(text("DELETE FROM party_switch_event WHERE from_party_id = to_party_id")).rowcount
        # collapse duplicate affiliations to the same party for a person (keep the current one)
        s.execute(
            text(
                """
                DELETE FROM party_affiliation a USING party_affiliation b
                WHERE a.person_id = b.person_id AND a.party_id = b.party_id
                  AND a.is_current = false AND b.is_current = true AND a.id <> b.id
                """
            )
        )
        print(f"[canon] merged {merged} duplicate party record(s); removed {false_sw} false switch event(s)")


def _add_alias(s, party_id: int, alias: str) -> None:
    s.execute(
        text(
            "INSERT INTO party_alias (party_id, alias, source) VALUES (:p, :a, 'canon') "
            "ON CONFLICT (party_id, alias) DO NOTHING"
        ),
        {"p": party_id, "a": alias.strip()},
    )
