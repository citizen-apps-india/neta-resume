"""Attach a per-MP parliamentary ACTIVITY scorecard (PRS Legislative Research MP Track).

Each PRS mptrack listing card carries a sitting member's cumulative counts over the term — questions
asked, debates participated in, private-member bills introduced. This pass enumerates the PRS roster for
a house (listing scrape only — no per-member profile fetch), matches each member to our current-term
person by name, and upserts a `parliamentary_activity` row with a PRS source_ref (raw snapshot = the
listing page the counts came from).

Attendance-% is handled separately (see `attendance.py`) and stays on office_term; this pass stores only
the three activity counts + the PRS reporting window. Peer context (house median/percentile) is computed
at read time by the API, so nothing but raw counts is stored here.

Idempotent: upserts on (person_id, term_cycle_id). PRS MP Track is CC-BY 4.0 — attribute in the UI.
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_core.provenance import record_source_ref
from neta_core.transform.names import normalize_name
from neta_ingest.pipelines.identity.affidavit_attach import best_match
from neta_sources.prs import client as prs

# house code -> (DB house code, current term_cycle WHERE clause) — same selectors as attendance.py
_CYCLE = {
    "ls": ("LS", "tc.number = 18"),
    "rs": ("RS", "tc.eci_election_id = 'RS-CURRENT'"),
}


def _load_current_terms(s, house_code: str, cycle_where: str) -> list[tuple[int, str, int, int]]:
    """[(person_id, display_name, house_id, term_cycle_id)] for the house's current term."""
    rows = s.execute(
        text(
            f"""
            SELECT ot.person_id, p.display_name AS name, tc.house_id, tc.id AS term_cycle_id
            FROM office_term ot
            JOIN term_cycle tc ON tc.id = ot.term_cycle_id
            JOIN house h ON h.id = tc.house_id
            JOIN person p ON p.id = ot.person_id
            WHERE h.code = :hc AND {cycle_where}
            """
        ),
        {"hc": house_code},
    ).all()
    return [(r.person_id, r.name, r.house_id, r.term_cycle_id) for r in rows]


def _resolve(name: str, persons: list[tuple[int, str, int, int]]) -> tuple[int, int, int] | None:
    """Match a PRS member name to a single (person_id, house_id, term_cycle_id).

    Reuses the token-aware matcher (exact normalized name, else >=2-shared-token subset, else fuzzy) with
    its ambiguity gate, so a name that ties two people is skipped rather than mis-attached.
    """
    cands = [(f"{pid}:{hid}:{tcid}", dn) for pid, dn, hid, tcid in persons]
    cid, _score, ambiguous = best_match(cands, name, normalize_name(name), threshold=0.88)
    if not cid or ambiguous:
        return None
    pid, hid, tcid = cid.split(":")
    return int(pid), int(hid), int(tcid)


def run(house: str = "ls") -> None:
    house = house.lower()
    if house not in _CYCLE:
        raise ValueError(f"house must be 'ls' or 'rs', got {house!r}")
    house_code, cycle_where = _CYCLE[house]

    roster = prs.fetch_roster(house)
    period = prs.fetch_report_period(house)
    ps, pe = period if period else (None, None)
    print(f"[activity] PRS {house_code} roster: {len(roster)} members; period {ps}..{pe}")

    written = unmatched = no_counts = 0
    with session_scope() as s:
        persons = _load_current_terms(s, house_code, cycle_where)
        for m in roster:
            hit = _resolve(m.name, persons)
            if not hit:
                unmatched += 1
                continue
            if m.questions is None and m.debates is None and m.private_member_bills is None:
                no_counts += 1  # card without parseable counts (should not happen) — skip, don't blank
                continue
            person_id, house_id, term_cycle_id = hit
            source_ref_id = record_source_ref(
                s, source_code="prs", native_id=f"prs-activity-{house}-{m.slug}",
                native_url=m.profile_url, raw_name=m.name, raw_payload_ref=m.raw_ref,
            )
            s.execute(text("UPDATE source_ref SET person_id = :pid WHERE id = :sr"),
                      {"pid": person_id, "sr": source_ref_id})
            s.execute(
                text(
                    """
                    INSERT INTO parliamentary_activity
                      (person_id, house_id, term_cycle_id, questions_asked, debates_participated,
                       private_member_bills, period_start, period_end, source_ref_id, updated_at)
                    VALUES (:pid, :hid, :tcid, :q, :d, :pmb, :ps, :pe, :sr, now())
                    ON CONFLICT (person_id, term_cycle_id) DO UPDATE SET
                      questions_asked = EXCLUDED.questions_asked,
                      debates_participated = EXCLUDED.debates_participated,
                      private_member_bills = EXCLUDED.private_member_bills,
                      period_start = EXCLUDED.period_start, period_end = EXCLUDED.period_end,
                      source_ref_id = EXCLUDED.source_ref_id, updated_at = now()
                    """
                ),
                {"pid": person_id, "hid": house_id, "tcid": term_cycle_id, "q": m.questions,
                 "d": m.debates, "pmb": m.private_member_bills, "ps": ps, "pe": pe, "sr": source_ref_id},
            )
            written += 1

    print(f"[activity] done: {written} scorecards written, {no_counts} cards without counts, "
          f"{unmatched} PRS members unmatched to our {house_code} roster")
