"""Attach cumulative parliamentary attendance % (PRS Legislative Research) to current-term office_terms.

PRS lists every sitting member with a profile slug; the % lives on each member's profile page. This
pass enumerates the PRS roster for a house, matches each member to our existing current-term person by
normalized name (exact, else a conservative fuzzy fallback), then fetches that member's profile and
writes the % onto their office_term with a PRS source_ref for provenance.

Idempotent: the source_ref upserts on (source, native_id) and the office_term UPDATE overwrites.

Coverage is partial by design — rule-exempt members (ministers, PM, Speaker/Dep. Speaker, LoP) don't
sign the register, so PRS shows no % and we leave attendance NULL (renders as "—", never 0).
"""

from __future__ import annotations

import difflib

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_core.provenance import record_source_ref
from neta_sources.prs import client as prs
from neta_core.transform.names import normalize_name

# house code -> (DB house code, current term_cycle WHERE clause)
_CYCLE = {
    "ls": ("LS", "tc.number = 18"),
    "rs": ("RS", "tc.eci_election_id = 'RS-CURRENT'"),
}


def _load_current_terms(s, house_code: str, cycle_where: str) -> dict[str, list[tuple[int, int]]]:
    """normalized_name -> [(office_term_id, person_id)] for the house's current term."""
    rows = s.execute(
        text(
            f"""
            SELECT ot.id AS ot_id, ot.person_id, p.normalized_name AS norm
            FROM office_term ot
            JOIN term_cycle tc ON tc.id = ot.term_cycle_id
            JOIN house h ON h.id = tc.house_id
            JOIN person p ON p.id = ot.person_id
            WHERE h.code = :hc AND {cycle_where}
            """
        ),
        {"hc": house_code},
    ).all()
    by_norm: dict[str, list[tuple[int, int]]] = {}
    for r in rows:
        by_norm.setdefault(r.norm, []).append((r.ot_id, r.person_id))
    return by_norm


def _resolve(name: str, by_norm: dict[str, list[tuple[int, int]]], keys: list[str]) -> tuple[int, int] | None:
    """Match a PRS name to a single (office_term_id, person_id); None if absent or ambiguous."""
    key = normalize_name(name)
    hits = by_norm.get(key)
    if hits is None:
        close = difflib.get_close_matches(key, keys, n=1, cutoff=0.90)
        hits = by_norm.get(close[0]) if close else None
    return hits[0] if hits and len(hits) == 1 else None


def run(house: str = "ls") -> None:
    house = house.lower()
    if house not in _CYCLE:
        raise ValueError(f"house must be 'ls' or 'rs', got {house!r}")
    house_code, cycle_where = _CYCLE[house]

    roster = prs.fetch_roster(house)
    print(f"[attendance] PRS {house_code} roster: {len(roster)} members")

    with session_scope() as s:
        by_norm = _load_current_terms(s, house_code, cycle_where)
        keys = list(by_norm)
        matched = [(m, *hit) for m in roster if (hit := _resolve(m.name, by_norm, keys))]
        print(f"[attendance] matched {len(matched)}/{len(roster)} to current-term persons; "
              f"fetching profiles…")

    written = exempt = failed = 0
    unmatched = len(roster) - len(matched)
    for m, ot_id, person_id in matched:
        try:
            pct, raw_rel = prs.fetch_attendance(m)
        except Exception as e:  # one slow/blocked profile must not abort the whole run
            failed += 1
            print(f"  ! fetch failed for {m.name} ({m.slug}): {e!r}")
            continue
        if pct is None:
            exempt += 1
            continue
        with session_scope() as s:
            source_ref_id = record_source_ref(
                s, source_code="prs", native_id=f"prs-{house}-{m.slug}",
                native_url=m.profile_url, raw_name=m.name, raw_payload_ref=raw_rel,
            )
            s.execute(text("UPDATE source_ref SET person_id = :pid WHERE id = :sr"),
                      {"pid": person_id, "sr": source_ref_id})
            s.execute(
                text("UPDATE office_term SET attendance_pct = :p, attendance_source_ref_id = :sr "
                     "WHERE id = :ot"),
                {"p": pct, "sr": source_ref_id, "ot": ot_id},
            )
        written += 1
        if written % 50 == 0:
            print(f"  …{written} written")

    print(f"[attendance] done: {written} attendance %s written, {exempt} exempt/no-% (left NULL), "
          f"{failed} fetch-failed, {unmatched} PRS members unmatched to our roster")
