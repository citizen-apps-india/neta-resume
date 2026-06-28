"""Complete the Lok Sabha roster + official photos from the sansad.in API.

MyNeta's winners list only covers ~485 of the 543 seats, and carries no photos. The official sansad.in
LS members API has the full sitting roster (~540; the remainder are current vacancies) with photos. This
pass:
  1. matches each sansad member to our existing (MyNeta-sourced) LS person by constituency, else by name,
     and fills the official photo (keeping the richer MyNeta affidavit data intact);
  2. creates the members MyNeta is missing as roster-only LS persons (no affidavit available).

Matching on constituency is safe — one winner per seat. Idempotent on the sansad source_ref (mpsno).
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_sources.sansad import client as sansad
from neta_core.transform.names import normalize_name
from neta_core.transform.parties import resolve_or_create_party_id


def run() -> None:
    members = sansad.fetch_ls_sitting_members()
    print(f"[ls-roster] fetched {len(members)} sitting Lok Sabha members from sansad.in")
    with session_scope() as s:
        source_id = s.execute(text("SELECT id FROM source WHERE code = 'sansad'")).scalar()
        house_id = s.execute(text("SELECT id FROM house WHERE code = 'LS'")).scalar()
        term_cycle_id = s.execute(
            text("SELECT id FROM term_cycle WHERE house_id = :h AND number = 18"), {"h": house_id}
        ).scalar()

        existing = s.execute(
            text(
                """
                SELECT ot.person_id, upper(trim(ot.constituency)) AS con, p.normalized_name AS norm
                FROM office_term ot
                JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                JOIN house h ON h.id = tc.house_id
                JOIN person p ON p.id = ot.person_id
                WHERE h.code = 'LS' AND tc.number = 18
                """
            )
        ).all()
        by_const = {r.con: r.person_id for r in existing if r.con}
        by_name = {r.norm: r.person_id for r in existing}

        matched = created = photos = 0
        for m in members:
            pid = by_const.get((m.constituency or "").upper().strip()) or by_name.get(normalize_name(m.name))
            if pid is not None:
                if m.photo_url:
                    s.execute(text("UPDATE person SET photo_url = COALESCE(photo_url, :p) WHERE id = :id"),
                              {"p": m.photo_url, "id": pid})
                    photos += 1
                _record_sansad_ref(s, source_id, m, pid)
                matched += 1
            else:
                created += _create_member(s, m, source_id=source_id, house_id=house_id, term_cycle_id=term_cycle_id)
        print(f"[ls-roster] matched {matched} (added {photos} photos); created {created} previously-missing member(s)")


def _record_sansad_ref(s, source_id: int, m: sansad.LsMember, person_id: int) -> None:
    s.execute(
        text(
            """
            INSERT INTO source_ref (source_id, native_id, native_url, raw_name, person_id)
            VALUES (:sid, :nid, :url, :name, :pid)
            ON CONFLICT (source_id, native_id) DO UPDATE
              SET native_url = EXCLUDED.native_url, person_id = EXCLUDED.person_id
            """
        ),
        {"sid": source_id, "nid": f"ls-{m.member_id}", "url": m.profile_url, "name": m.name, "pid": person_id},
    )


def _create_member(s, m: sansad.LsMember, *, source_id: int, house_id: int, term_cycle_id: int) -> int:
    source_ref_id = s.execute(
        text(
            """
            INSERT INTO source_ref (source_id, native_id, native_url, raw_name)
            VALUES (:sid, :nid, :url, :name)
            ON CONFLICT (source_id, native_id) DO UPDATE SET native_url = EXCLUDED.native_url
            RETURNING id
            """
        ),
        {"sid": source_id, "nid": f"ls-{m.member_id}", "url": m.profile_url, "name": m.name},
    ).scalar()
    birth_year = (2024 - m.age) if m.age else None
    person_id = s.execute(
        text(
            """
            INSERT INTO person (display_name, normalized_name, gender, birth_year, photo_url)
            VALUES (:dn, :nn, :g, :by, :photo) RETURNING id
            """
        ),
        {"dn": m.name, "nn": normalize_name(m.name), "g": m.gender, "by": birth_year, "photo": m.photo_url},
    ).scalar()
    s.execute(text("UPDATE source_ref SET person_id = :pid WHERE id = :sr"),
              {"pid": person_id, "sr": source_ref_id})
    party_id = resolve_or_create_party_id(s, m.party) if m.party else None
    s.execute(
        text(
            """
            INSERT INTO office_term
              (person_id, house_id, term_cycle_id, constituency, membership_type, start_date,
               party_id, status, source_ref_id)
            VALUES (:pid, :hid, :tcid, :con, 'elected', DATE '2024-06-24', :party, 'sitting', :sr)
            """
        ),
        {"pid": person_id, "hid": house_id, "tcid": term_cycle_id, "con": m.constituency,
         "party": party_id, "sr": source_ref_id},
    )
    if party_id is not None:
        s.execute(
            text(
                "INSERT INTO party_affiliation (person_id, party_id, is_current, detection, confidence, source_ref_id) "
                "VALUES (:pid, :party, true, 'structured_term_diff', 80, :sr) "
                "ON CONFLICT (person_id) WHERE is_current DO NOTHING"
            ),
            {"pid": person_id, "party": party_id, "sr": source_ref_id},
        )
    return 1
