"""Seed 18th-Lok-Sabha leadership roles — PM, Speaker, LoP, and the full Cabinet-rank Union Council of
Ministers (Modi 3.0, sworn in 2024-06-09) with portfolios.

Each role is a public-record fact attributed to the relevant official government portal (source 'govt',
trust_tier 1) and attached to the EXISTING person (matched by name tokens, then exact normalized name — no
new persons created). Idempotent: the role upserts on (person_id, role_type, body, start_date) and the
source_ref on (source, native_id). Sansad/PMO don't expose this as a clean API (SPA/WAF), so it is curated;
Ministers of State and committee memberships can follow as sources allow.
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
    # Remaining Cabinet-rank ministers (Union Council of Ministers, sworn in 2024-06-09).
    ("Nadda", "minister", "Minister of Health and Family Welfare", "Union Council of Ministers", "RS",
     "Health and Family Welfare", "https://mohfw.gov.in/"),
    ("Shivraj Singh Chouhan", "minister", "Minister of Agriculture and Farmers' Welfare", "Union Council of Ministers", "LS",
     "Agriculture and Farmers' Welfare", "https://agriwelfare.gov.in/"),
    ("Manohar Lal", "minister", "Minister of Housing and Urban Affairs", "Union Council of Ministers", "LS",
     "Housing and Urban Affairs; Power", "https://mohua.gov.in/"),
    ("Kumaraswamy", "minister", "Minister of Heavy Industries and Steel", "Union Council of Ministers", "LS",
     "Heavy Industries; Steel", "https://heavyindustries.gov.in/"),
    ("Piyush Goyal", "minister", "Minister of Commerce and Industry", "Union Council of Ministers", "RS",
     "Commerce and Industry", "https://commerce.gov.in/"),
    ("Dharmendra Pradhan", "minister", "Minister of Education", "Union Council of Ministers", "LS",
     "Education", "https://www.education.gov.in/"),
    ("Jitan Ram Manjhi", "minister", "Minister of Micro, Small and Medium Enterprises", "Union Council of Ministers", "LS",
     "Micro, Small and Medium Enterprises", "https://msme.gov.in/"),
    ("Rajiv Ranjan Singh", "minister", "Minister of Panchayati Raj; Fisheries, Animal Husbandry and Dairying", "Union Council of Ministers", "LS",
     "Panchayati Raj; Fisheries, Animal Husbandry and Dairying", "https://panchayat.gov.in/"),
    ("Sarbananda Sonowal", "minister", "Minister of Ports, Shipping and Waterways", "Union Council of Ministers", "RS",
     "Ports, Shipping and Waterways", "https://shipmin.gov.in/"),
    ("Virendra Kumar", "minister", "Minister of Social Justice and Empowerment", "Union Council of Ministers", "LS",
     "Social Justice and Empowerment", "https://socialjustice.gov.in/"),
    ("Rammohan Naidu", "minister", "Minister of Civil Aviation", "Union Council of Ministers", "LS",
     "Civil Aviation", "https://www.civilaviation.gov.in/"),
    ("Pralhad Joshi", "minister", "Minister of Consumer Affairs, Food and Public Distribution", "Union Council of Ministers", "LS",
     "Consumer Affairs, Food and Public Distribution; New and Renewable Energy", "https://consumeraffairs.nic.in/"),
    ("Jual Oram", "minister", "Minister of Tribal Affairs", "Union Council of Ministers", "LS",
     "Tribal Affairs", "https://tribal.nic.in/"),
    ("Giriraj Singh", "minister", "Minister of Textiles", "Union Council of Ministers", "LS",
     "Textiles", "https://texmin.gov.in/"),
    ("Ashwini Vaishnaw", "minister", "Minister of Railways; Information and Broadcasting; Electronics and IT", "Union Council of Ministers", "RS",
     "Railways; Information and Broadcasting; Electronics and Information Technology", "https://www.indianrailways.gov.in/"),
    ("Jyotiraditya Scindia", "minister", "Minister of Communications; DoNER", "Union Council of Ministers", "RS",
     "Communications; Development of North Eastern Region", "https://dot.gov.in/"),
    ("Bhupender Yadav", "minister", "Minister of Environment, Forest and Climate Change", "Union Council of Ministers", "RS",
     "Environment, Forest and Climate Change", "https://moef.gov.in/"),
    ("Gajendra Singh Shekhawat", "minister", "Minister of Culture and Tourism", "Union Council of Ministers", "LS",
     "Culture; Tourism", "https://www.indiaculture.gov.in/"),
    ("Annpurna Devi", "minister", "Minister of Women and Child Development", "Union Council of Ministers", "LS",
     "Women and Child Development", "https://wcd.gov.in/"),
    ("Kiren Rijiju", "minister", "Minister of Parliamentary Affairs and Minority Affairs", "Union Council of Ministers", "LS",
     "Parliamentary Affairs; Minority Affairs", "https://mpa.gov.in/"),
    ("Hardeep Singh Puri", "minister", "Minister of Petroleum and Natural Gas", "Union Council of Ministers", "RS",
     "Petroleum and Natural Gas", "https://mopng.gov.in/"),
    ("Mansukh Mandaviya", "minister", "Minister of Labour and Employment; Youth Affairs and Sports", "Union Council of Ministers", "RS",
     "Labour and Employment; Youth Affairs and Sports", "https://labour.gov.in/"),
    ("Kishan Reddy", "minister", "Minister of Coal and Mines", "Union Council of Ministers", "LS",
     "Coal; Mines", "https://coal.nic.in/"),
    ("Chirag Paswan", "minister", "Minister of Food Processing Industries", "Union Council of Ministers", "LS",
     "Food Processing Industries", "https://mofpi.gov.in/"),
    ("C R Patil", "minister", "Minister of Jal Shakti", "Union Council of Ministers", "LS",
     "Jal Shakti", "https://jalshakti-dowr.gov.in/"),
]

# Past Cabinet tenures of CURRENTLY-SITTING MPs — seeded as status='former'. High-confidence, term-level
# dates only (full-term portfolios). (match_name, role_type, title, body, house_code, portfolio, start, end, url)
_PAST_ROLES: list[tuple[str, str, str, str, str, str | None, str, str, str]] = [
    # Modi 2.0 (2019-05-31 to 2024-06-09)
    ("Raj Nath Singh", "minister", "Minister of Defence", "Union Council of Ministers", "LS",
     "Defence", "2019-05-31", "2024-06-09", "https://www.mod.gov.in/"),
    ("Amit Shah", "minister", "Minister of Home Affairs", "Union Council of Ministers", "LS",
     "Home Affairs", "2019-05-31", "2024-06-09", "https://www.mha.gov.in/"),
    ("Nirmala Sitharaman", "minister", "Minister of Finance", "Union Council of Ministers", "RS",
     "Finance", "2019-05-31", "2024-06-09", "https://finmin.nic.in/"),
    ("Jaishankar", "minister", "Minister of External Affairs", "Union Council of Ministers", "RS",
     "External Affairs", "2019-05-31", "2024-06-09", "https://www.mea.gov.in/"),
    ("Nitin Gadkari", "minister", "Minister of Road Transport and Highways", "Union Council of Ministers", "LS",
     "Road Transport and Highways", "2019-05-31", "2024-06-09", "https://morth.nic.in/"),
    ("Piyush Goyal", "minister", "Minister of Commerce and Industry", "Union Council of Ministers", "RS",
     "Commerce and Industry", "2019-05-31", "2024-06-09", "https://commerce.gov.in/"),
    ("Pralhad Joshi", "minister", "Minister of Parliamentary Affairs", "Union Council of Ministers", "LS",
     "Parliamentary Affairs", "2019-05-31", "2024-06-09", "https://mpa.gov.in/"),
    # Modi 1.0 (2014-05-26 to 2019-05-30)
    ("Raj Nath Singh", "minister", "Minister of Home Affairs", "Union Council of Ministers", "LS",
     "Home Affairs", "2014-05-26", "2019-05-30", "https://www.mha.gov.in/"),
    ("Nitin Gadkari", "minister", "Minister of Road Transport and Highways", "Union Council of Ministers", "LS",
     "Road Transport and Highways", "2014-05-26", "2019-05-30", "https://morth.nic.in/"),
    ("Dharmendra Pradhan", "minister", "Minister of Petroleum and Natural Gas", "Union Council of Ministers", "RS",
     "Petroleum and Natural Gas", "2014-05-26", "2019-05-30", "https://mopng.gov.in/"),
    ("Jual Oram", "minister", "Minister of Tribal Affairs", "Union Council of Ministers", "LS",
     "Tribal Affairs", "2014-05-26", "2019-05-30", "https://tribal.nic.in/"),
    ("Nirmala Sitharaman", "minister", "Minister of Defence", "Union Council of Ministers", "RS",
     "Defence", "2017-09-03", "2019-05-30", "https://www.mod.gov.in/"),
    # UPA 2.0 (2009-2014)
    ("Shashi Tharoor", "minister_state", "Minister of State, Human Resource Development",
     "Union Council of Ministers", "LS", "Human Resource Development", "2012-10-28", "2014-05-26",
     "https://www.education.gov.in/"),
]


def _match_person(persons: list, name: str) -> int | None:
    """Unique person for a name: token-superset (handles middle names), then exact normalized-name
    equality as a fallback (handles initials like 'C R Patil' whose single-char tokens are dropped)."""
    want = name_tokens(name)
    hits = [p.id for p in persons if want and want <= name_tokens(p.display_name)]
    if len(hits) == 1:
        return hits[0]
    key = normalize_name(name)
    exact = [p.id for p in persons if normalize_name(p.display_name) == key]
    return exact[0] if len(exact) == 1 else None


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

        # Past ministerial tenures (status='former'), for sitting MPs who held office in earlier terms.
        for name, role_type, title, body, house_code, portfolio, start, end, url in _PAST_ROLES:
            pid = _match_person(persons, name)
            if pid is None:
                skipped.append(f"{name} ({title} {start[:4]}) — no unique person match")
                continue
            house_id = s.execute(text("SELECT id FROM house WHERE code = :c"), {"c": house_code}).scalar()
            sref = record_source_ref(
                s, source_code="govt",
                native_id=f"past:{role_type}:{normalize_name(name).replace(' ', '-')}:{start}",
                native_url=url, raw_name=name,
            )
            s.execute(
                text(
                    """
                    INSERT INTO role
                      (person_id, role_type, title, body, house_id, portfolio, start_date, end_date,
                       status, source_ref_id)
                    VALUES (:pid, :rt, :title, :body, :hid, :port, :start, :end, 'former', :sr)
                    ON CONFLICT (person_id, role_type, body, start_date) DO UPDATE
                      SET title = EXCLUDED.title, portfolio = EXCLUDED.portfolio, end_date = EXCLUDED.end_date,
                          house_id = EXCLUDED.house_id, source_ref_id = EXCLUDED.source_ref_id
                    """
                ),
                {"pid": pid, "rt": role_type, "title": title, "body": body, "hid": house_id,
                 "port": portfolio, "start": start, "end": end, "sr": sref},
            )
            seeded += 1
            print(f"  [former {role_type}] {name} -> person {pid}: {title} ({start[:4]}–{end[:4]})")

    print(f"[leadership] seeded {seeded} role(s); {len(skipped)} skipped.")
    for sk in skipped:
        print("   · " + sk)
