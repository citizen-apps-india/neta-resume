"""Attach a per-MP parliamentary RECORD — individual questions asked + debates participated in.

This is the content behind the 0024 activity *counts*. The sansad.in question/debate backend (eParlib)
is unreachable from outside-India IPs, but PRS Legislative Research's MP Track profile page enumerates the
same items on a reachable, server-rendered page: per question a subject, ministry, date, type and a link
to the official sansad.in document PDF; per debate a title, type, date and PDF. This pass enumerates the
PRS roster for a house, matches each member to our current-term person by name (same matcher as
`activity.py`), fetches each matched member's profile ONCE, and upserts their `parliamentary_question` and
`parliamentary_debate` rows in a single pass (both tables come from the one page — fetching them under two
separate commands would re-download every profile for nothing).

Provenance: each member's rows share one PRS `source_ref` (raw snapshot = the profile they were read
from); the official sansad.in PDF is kept per row as `document_url`. PRS MP Track is CC-BY 4.0 — attribute
in the UI. Idempotent: upserts on the natural keys; per-member commits so a long run keeps partial
progress. Missing != zero: a member with no listed items simply gets no rows.
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_core.provenance import record_source_ref
from neta_core.transform.names import normalize_name
from neta_ingest.pipelines.identity.affidavit_attach import best_match
from neta_sources.prs import client as prs

# house code -> (DB house code, current term_cycle WHERE clause) — same selectors as activity.py
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
    """Match a PRS member name to a single (person_id, house_id, term_cycle_id), ambiguity-gated."""
    cands = [(f"{pid}:{hid}:{tcid}", dn) for pid, dn, hid, tcid in persons]
    cid, _score, ambiguous = best_match(cands, name, normalize_name(name), threshold=0.88)
    if not cid or ambiguous:
        return None
    pid, hid, tcid = cid.split(":")
    return int(pid), int(hid), int(tcid)


_Q_UPSERT = text(
    """
    INSERT INTO parliamentary_question
      (person_id, house_id, term_cycle_id, question_ref, subject, ministry, question_type,
       asked_date, document_url, source_ref_id, updated_at)
    VALUES (:pid, :hid, :tcid, :ref, :subject, :ministry, :qtype, :adate, :url, :sr, now())
    ON CONFLICT (person_id, term_cycle_id, question_ref) DO UPDATE SET
      subject = EXCLUDED.subject, ministry = EXCLUDED.ministry, question_type = EXCLUDED.question_type,
      asked_date = EXCLUDED.asked_date, document_url = EXCLUDED.document_url,
      source_ref_id = EXCLUDED.source_ref_id, updated_at = now()
    """
)

_D_UPSERT = text(
    """
    INSERT INTO parliamentary_debate
      (person_id, house_id, term_cycle_id, debate_ref, title, debate_type, debate_date,
       document_url, source_ref_id, updated_at)
    VALUES (:pid, :hid, :tcid, :ref, :title, :dtype, :ddate, :url, :sr, now())
    ON CONFLICT (person_id, term_cycle_id, debate_ref) DO UPDATE SET
      title = EXCLUDED.title, debate_type = EXCLUDED.debate_type, debate_date = EXCLUDED.debate_date,
      document_url = EXCLUDED.document_url, source_ref_id = EXCLUDED.source_ref_id, updated_at = now()
    """
)


def run(house: str = "ls") -> None:
    house = house.lower()
    if house not in _CYCLE:
        raise ValueError(f"house must be 'ls' or 'rs', got {house!r}")
    house_code, cycle_where = _CYCLE[house]

    roster = prs.fetch_roster(house)
    with session_scope() as s:
        persons = _load_current_terms(s, house_code, cycle_where)

    matched: list[tuple[prs.PrsMember, int, int, int]] = []
    unmatched = 0
    for m in roster:
        hit = _resolve(m.name, persons)
        if hit:
            matched.append((m, *hit))
        else:
            unmatched += 1
    print(f"[record] PRS {house_code} roster: {len(roster)} members; "
          f"{len(matched)} matched, {unmatched} unmatched to our roster")

    q_written = d_written = failed = no_items = 0
    for m, person_id, house_id, term_cycle_id in matched:
        try:
            questions, debates, raw_ref = prs.fetch_record(m)
        except Exception as e:  # one bad profile must not abort the whole run
            failed += 1
            print(f"[record] fetch failed for {m.name} ({m.slug}): {e}")
            continue
        if not questions and not debates:
            no_items += 1  # legitimately none listed (missing != zero) — nothing to write
            continue
        with session_scope() as s:
            source_ref_id = record_source_ref(
                s, source_code="prs", native_id=f"prs-record-{house}-{m.slug}",
                native_url=m.profile_url, raw_name=m.name, raw_payload_ref=raw_ref,
            )
            s.execute(text("UPDATE source_ref SET person_id = :pid WHERE id = :sr"),
                      {"pid": person_id, "sr": source_ref_id})
            for q in questions:
                s.execute(_Q_UPSERT, {
                    "pid": person_id, "hid": house_id, "tcid": term_cycle_id, "ref": q.question_ref,
                    "subject": q.subject, "ministry": q.ministry, "qtype": q.question_type,
                    "adate": q.asked_date, "url": q.document_url, "sr": source_ref_id,
                })
                q_written += 1
            for d in debates:
                s.execute(_D_UPSERT, {
                    "pid": person_id, "hid": house_id, "tcid": term_cycle_id, "ref": d.debate_ref,
                    "title": d.title, "dtype": d.debate_type, "ddate": d.debate_date,
                    "url": d.document_url, "sr": source_ref_id,
                })
                d_written += 1

    print(f"[record] done: {q_written} questions + {d_written} debates upserted across "
          f"{len(matched) - failed - no_items} members; {no_items} with none listed, {failed} fetch-failed")
