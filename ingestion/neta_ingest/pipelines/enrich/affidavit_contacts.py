"""Enrich the Contact tab with each legislator's DECLARED HOME STATE from the ECI affidavit.

The affidavit (transcribed by MyNeta from the candidate's ECI filing) is the source; a person's
home_state is already derived on the person row, so this pipeline surfaces it as a sourced contact fact,
attributed to that person's latest affidavit's source_ref (the MyNeta candidate page = the ECI affidavit).
Only the coarse state is surfaced — residential addresses and personal mobile numbers stay deliberately
excluded. Idempotent: a person's home_state contact is replaced each run.
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope


def _title(state: str) -> str:
    """home_state is stored with mixed casing ('MAHARASHTRA' / 'Maharashtra'); render Title Case."""
    return " ".join(w.capitalize() for w in state.split())


def run() -> None:
    attached = skipped = 0
    with session_scope() as s:
        # Only persons who have BOTH a home_state and an affidavit — the affidavit's source_ref is the
        # honest provenance (link to the ECI/MyNeta filing). No affidavit -> no sourced contact (missing != zero).
        rows = s.execute(
            text(
                """
                SELECT p.id, p.home_state, a.source_ref_id
                FROM person p
                JOIN LATERAL (
                    SELECT source_ref_id FROM affidavit
                    WHERE person_id = p.id ORDER BY filed_year DESC LIMIT 1
                ) a ON true
                WHERE p.home_state IS NOT NULL AND btrim(p.home_state) <> ''
                """
            )
        ).all()
        for pid, home_state, sref in rows:
            value = _title(home_state)
            # Idempotent: replace this person's home_state contact (value/casing may change between runs).
            s.execute(
                text("DELETE FROM contact WHERE person_id = :pid AND channel_type = 'home_state'"),
                {"pid": pid},
            )
            s.execute(
                text(
                    """
                    INSERT INTO contact (person_id, channel_type, value, label, source_ref_id)
                    VALUES (:pid, 'home_state', :val, 'Declared home state (ECI affidavit)', :sr)
                    ON CONFLICT (person_id, channel_type, value) DO UPDATE
                      SET label = EXCLUDED.label, source_ref_id = EXCLUDED.source_ref_id
                    """
                ),
                {"pid": pid, "val": value, "sr": sref},
            )
            attached += 1
    print(f"[affidavit-contacts] home-state contact attached to {attached} person(s); {skipped} skipped.")
