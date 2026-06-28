"""Attach OFFICIAL contact channels to sitting MPs from the sansad.in member API.

Official channels only — the @*.sansad.in email, the Parliament/Delhi office phone, and the official
sansad profile. Personal mobile and residence address are deliberately NOT stored. Members are matched to
the EXISTING person via the sansad source_ref (native_id 'ls-{mpsno}' / 'rs-{mpsno}') — no name matching.
Idempotent: a person's sansad-sourced contacts are replaced each run.
"""

from __future__ import annotations

from sqlalchemy import text

from neta_ingest.db.engine import session_scope
from neta_ingest.provenance import record_source_ref
from neta_ingest.sources.sansad import client as sansad


def run(house: str | None = None) -> None:
    members: list[tuple[str, str, str, str, str | None, str | None, str]] = []
    # (house_prefix, mpsno, name, profile_url, official_email, office_phone, phone_label)
    if house in (None, "ls"):
        for m in sansad.fetch_ls_sitting_members():
            members.append(("ls", m.member_id, m.name, m.profile_url, m.official_email, m.office_phone,
                            "Parliament office (Delhi)"))
    if house in (None, "rs"):
        for m in sansad.fetch_rs_sitting_members():
            members.append(("rs", m.member_id, m.name, m.profile_url, m.official_email, m.office_phone,
                            "Office"))
    print(f"[contacts] {len(members)} sitting members fetched from sansad …")

    attached = channels = missing = 0
    with session_scope() as s:
        for prefix, mpsno, name, profile_url, email, phone, phone_label in members:
            pid = s.execute(
                text(
                    "SELECT sr.person_id FROM source_ref sr JOIN source so ON so.id = sr.source_id "
                    "WHERE so.code = 'sansad' AND sr.native_id = :nid"
                ),
                {"nid": f"{prefix}-{mpsno}"},
            ).scalar()
            if pid is None:
                missing += 1
                continue
            sref = record_source_ref(
                s, source_code="sansad", native_id=f"{prefix}-{mpsno}-contact",
                native_url=profile_url, raw_name=name,
            )
            s.execute(text("DELETE FROM contact WHERE source_ref_id = :sr"), {"sr": sref})
            rows = [("website", profile_url, "Official profile")]
            if email:
                rows.append(("email", email, "Official (sansad.in)"))
            if phone:
                rows.append(("phone", phone, phone_label))
            for ch, val, label in rows:
                s.execute(
                    text(
                        """
                        INSERT INTO contact (person_id, channel_type, value, label, source_ref_id)
                        VALUES (:pid, :ch, :val, :label, :sr)
                        ON CONFLICT (person_id, channel_type, value) DO UPDATE
                          SET label = EXCLUDED.label, source_ref_id = EXCLUDED.source_ref_id
                        """
                    ),
                    {"pid": pid, "ch": ch, "val": val, "label": label, "sr": sref},
                )
                channels += 1
            attached += 1
    print(f"[contacts] attached contacts to {attached} member(s), {channels} channels, {missing} unmatched.")
