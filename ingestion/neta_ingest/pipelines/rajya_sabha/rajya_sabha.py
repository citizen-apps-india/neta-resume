"""Rajya Sabha roster ingest from the official sansad.in sitting-members API.

Populates the upper house: person (+ official photo), office_term (house=RS, state, term dates,
nominated vs elected), and current party affiliation. There is NO affidavit wealth/criminal data for
sitting RS members (indirectly elected -> not aggregated by ADR/MyNeta), so those remain empty and the
UI shows "no affidavit on record." Idempotent on the sansad source_ref (mpsno).
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_sources.sansad import client as sansad
from neta_core.transform.names import normalize_name
from neta_core.transform.parties import resolve_or_create_party_id


def run() -> None:
    members = sansad.fetch_rs_sitting_members()
    print(f"[rs] fetched {len(members)} sitting Rajya Sabha members from sansad.in")
    ok = 0
    with session_scope() as s:
        source_id = s.execute(text("SELECT id FROM source WHERE code = 'sansad'")).scalar()
        house_id = s.execute(text("SELECT id FROM house WHERE code = 'RS'")).scalar()
        term_cycle_id = s.execute(
            text("SELECT id FROM term_cycle WHERE house_id = :h AND eci_election_id = 'RS-CURRENT'"),
            {"h": house_id},
        ).scalar()
        for m in members:
            _persist(s, m, source_id=source_id, house_id=house_id, term_cycle_id=term_cycle_id)
            ok += 1
    print(f"[rs] done: {ok} Rajya Sabha members ingested (roster only — no affidavit data available)")


def _persist(s, m: sansad.RsMember, *, source_id: int, house_id: int, term_cycle_id: int) -> None:
    row = s.execute(
        text(
            """
            INSERT INTO source_ref (source_id, native_id, native_url, raw_name)
            VALUES (:sid, :nid, :url, :name)
            ON CONFLICT (source_id, native_id) DO UPDATE
              SET native_url = EXCLUDED.native_url, raw_name = EXCLUDED.raw_name, fetched_at = now()
            RETURNING id, person_id
            """
        ),
        {"sid": source_id, "nid": f"rs-{m.member_id}", "url": m.profile_url, "name": m.name},
    ).one()
    source_ref_id, person_id = row.id, row.person_id

    birth_year = (2026 - m.age) if m.age else None
    if person_id is None:
        # repair: relink to an existing orphaned RS roster person of the same name (no source_ref)
        person_id = s.execute(
            text(
                """
                SELECT p.id FROM person p
                JOIN office_term ot ON ot.person_id = p.id
                JOIN term_cycle tc ON tc.id = ot.term_cycle_id JOIN house h ON h.id = tc.house_id
                WHERE h.code='RS' AND p.normalized_name = :nn
                  AND NOT EXISTS (SELECT 1 FROM source_ref sr WHERE sr.person_id = p.id)
                LIMIT 1
                """
            ),
            {"nn": normalize_name(m.name)},
        ).scalar()
        if person_id is not None:
            s.execute(text("UPDATE source_ref SET person_id = :pid WHERE id = :sid"),
                      {"pid": person_id, "sid": source_ref_id})
    if person_id is None:
        person_id = s.execute(
            text(
                """
                INSERT INTO person (display_name, normalized_name, gender, birth_year, photo_url)
                VALUES (:dn, :nn, :g, :by, :photo) RETURNING id
                """
            ),
            {"dn": m.name, "nn": normalize_name(m.name), "g": m.gender, "by": birth_year, "photo": m.photo_url},
        ).scalar()
        s.execute(text("UPDATE source_ref SET person_id = :pid WHERE id = :sid"),
                  {"pid": person_id, "sid": source_ref_id})
    else:
        s.execute(text("UPDATE person SET photo_url = COALESCE(:photo, photo_url) WHERE id = :pid"),
                  {"photo": m.photo_url, "pid": person_id})
    s.execute(
        text(
            "INSERT INTO person_name_variant (person_id, variant, source_id, script) "
            "VALUES (:pid, :v, :sid, 'latin') ON CONFLICT DO NOTHING"
        ),
        {"pid": person_id, "v": m.name, "sid": source_id},
    )

    party_id = resolve_or_create_party_id(s, m.party) if m.party else None

    # idempotent: wipe this source_ref's derived facts, then reinsert
    for tbl in ("office_term", "party_affiliation"):
        s.execute(text(f"DELETE FROM {tbl} WHERE source_ref_id = :sr"), {"sr": source_ref_id})

    start_date = f"{m.start_year}-01-01" if m.start_year else None
    end_date = f"{m.end_year}-01-01" if m.end_year else None
    s.execute(
        text(
            """
            INSERT INTO office_term
              (person_id, house_id, term_cycle_id, constituency, rs_state_code, membership_type,
               start_date, end_date, party_id, status, source_ref_id)
            VALUES (:pid, :hid, :tcid, NULL, :state, :mtype, :sd, :ed, :party, 'sitting', :sr)
            """
        ),
        {"pid": person_id, "hid": house_id, "tcid": term_cycle_id, "state": m.state,
         "mtype": "nominated" if m.nominated else "elected", "sd": start_date, "ed": end_date,
         "party": party_id, "sr": source_ref_id},
    )
    if party_id is not None:
        s.execute(
            text(
                """
                INSERT INTO party_affiliation
                  (person_id, party_id, is_current, detection, confidence, source_ref_id)
                VALUES (:pid, :party, true, 'structured_term_diff', 80, :sr)
                ON CONFLICT (person_id) WHERE is_current DO NOTHING
                """
            ),
            {"pid": person_id, "party": party_id, "sr": source_ref_id},
        )
