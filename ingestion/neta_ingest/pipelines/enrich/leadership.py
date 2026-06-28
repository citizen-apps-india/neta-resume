"""Seed marquee 18th-Lok-Sabha leadership roles (PM, Speaker, LoP, senior Union ministers).

Each role is a public-record fact attributed to an official government portal (source 'govt', trust_tier 1)
and attached to the EXISTING person (matched by name tokens — no new persons created). Idempotent: the role
row upserts on (person_id, role_type, body, start_date) and the source_ref on (source, native_id).

This is a curated starter set; a scalable scraper of sansad.in committee/ministry pages comes later.
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_ingest.pipelines.identity.affidavit_attach import name_tokens
from neta_core.provenance import record_source_ref
from neta_core.transform.names import normalize_name

# 18th Lok Sabha term anchor (first sitting 2024-06-24; the Modi-3.0 cabinet was sworn in 2024-06-09 —
# we anchor all to the term start for a stable idempotency key).
_TERM_START = "2024-06-24"

# (match_name, role_type, title, body, house_code, portfolio, source_url)
_ROLES: list[tuple[str, str, str, str, str, str | None, str]] = [
    ("Narendra Modi", "prime_minister", "Prime Minister of India", "Union Council of Ministers", "LS",
     None, "https://www.pmindia.gov.in/en/pms-profile/"),
    ("Om Birla", "speaker", "Speaker, Lok Sabha", "Lok Sabha", "LS",
     None, "https://sansad.in/ls"),
    ("Rahul Gandhi", "lop", "Leader of the Opposition, Lok Sabha", "Lok Sabha", "LS",
     None, "https://sansad.in/ls"),
    ("Amit Shah", "minister", "Minister of Home Affairs", "Union Council of Ministers", "LS",
     "Home Affairs", "https://www.mha.gov.in/"),
    ("Raj Nath Singh", "minister", "Minister of Defence", "Union Council of Ministers", "LS",
     "Defence", "https://www.mod.gov.in/"),
    ("Nitin Gadkari", "minister", "Minister of Road Transport and Highways", "Union Council of Ministers",
     "LS", "Road Transport and Highways", "https://morth.nic.in/"),
    ("Nirmala Sitharaman", "minister", "Minister of Finance", "Union Council of Ministers", "RS",
     "Finance", "https://finmin.nic.in/"),
    ("Jaishankar", "minister", "Minister of External Affairs", "Union Council of Ministers",
     "RS", "External Affairs", "https://www.mea.gov.in/"),
]


def _match_person(persons: list, name: str) -> int | None:
    """Unique person whose name tokens are a superset of the query tokens (handles middle names)."""
    want = name_tokens(name)
    hits = [p.id for p in persons if want and want <= name_tokens(p.display_name)]
    return hits[0] if len(hits) == 1 else None


def run() -> None:
    seeded = 0
    skipped: list[str] = []
    with session_scope() as s:
        persons = s.execute(text("SELECT id, display_name FROM person")).all()
        for name, role_type, title, body, house_code, portfolio, url in _ROLES:
            pid = _match_person(persons, name)
            if pid is None:
                skipped.append(f"{name} ({title}) — no unique person match")
                continue
            house_id = s.execute(
                text("SELECT id FROM house WHERE code = :c"), {"c": house_code}
            ).scalar()
            sref = record_source_ref(
                s, source_code="govt",
                native_id=f"18ls:{role_type}:{normalize_name(name).replace(' ', '-')}",
                native_url=url, raw_name=name,
            )
            s.execute(
                text(
                    """
                    INSERT INTO role
                      (person_id, role_type, title, body, house_id, portfolio, start_date, status, source_ref_id)
                    VALUES (:pid, :rt, :title, :body, :hid, :port, :start, 'current', :sr)
                    ON CONFLICT (person_id, role_type, body, start_date) DO UPDATE
                      SET title = EXCLUDED.title, portfolio = EXCLUDED.portfolio,
                          house_id = EXCLUDED.house_id, source_ref_id = EXCLUDED.source_ref_id
                    """
                ),
                {"pid": pid, "rt": role_type, "title": title, "body": body, "hid": house_id,
                 "port": portfolio, "start": _TERM_START, "sr": sref},
            )
            seeded += 1
            print(f"  [{role_type}] {name} -> person {pid}: {title}")
    print(f"[leadership] seeded {seeded} role(s); {len(skipped)} skipped.")
    for sk in skipped:
        print("   · " + sk)
