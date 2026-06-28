"""Unified MyNeta candidate ingest (the Phase-1 vertical slice).

A MyNeta candidate page carries BOTH wealth and criminal data, so we fetch once and write everything
for that candidate in one transaction. Idempotency is keyed on the candidate's source_ref: we delete
this source_ref's derived facts and re-insert, so re-running never duplicates.

Entity resolution is intentionally bypassed here (1 MyNeta candidate == 1 person). The real ER pipeline
(resolve_persons) will later merge a person across sources/elections; for the slice, the source_ref
links straight to a freshly created person. See docs/entity-resolution.md.
"""

from __future__ import annotations

import re

from sqlalchemy import text

from neta_ingest.config import settings
from neta_ingest.db.engine import session_scope
from neta_ingest.sources.myneta import client as myneta
from neta_ingest.sources.myneta.parser import ParsedCandidate
from neta_ingest.transform.names import normalize_name
from neta_ingest.transform.parties import resolve_or_create_party_id
from neta_ingest.transform.sections import rollup_severity

# State-assembly candidate pages don't repeat the state (the whole election is one state), so we stamp it
# from the house's state_code. ISO 3166-2:IN codes -> canonical state name (extend as states are added).
_STATE_CODE_TO_NAME = {
    "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam", "BR": "Bihar",
    "CT": "Chhattisgarh", "GA": "Goa", "GJ": "Gujarat", "HR": "Haryana", "HP": "Himachal Pradesh",
    "JH": "Jharkhand", "KA": "Karnataka", "KL": "Kerala", "MP": "Madhya Pradesh", "MH": "Maharashtra",
    "MN": "Manipur", "ML": "Meghalaya", "MZ": "Mizoram", "NL": "Nagaland", "OR": "Odisha",
    "PB": "Punjab", "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu", "TG": "Telangana",
    "TR": "Tripura", "UP": "Uttar Pradesh", "UT": "Uttarakhand", "WB": "West Bengal",
    "DL": "Delhi", "JK": "Jammu and Kashmir", "PY": "Puducherry",
}


def run(cycle: str = "LS2024", house: str = "ls", limit: int = 10,
        candidate_ids: list[str] | None = None) -> None:
    ids = candidate_ids
    if ids is None:
        winners = myneta.fetch_winners(cycle)
        ids = [w.candidate_id for w in winners][:limit]
    print(f"[myneta] ingesting {len(ids)} candidates for {cycle} ...")

    ok = 0
    failed: list[str] = []
    for i, cid in enumerate(ids, 1):
        # Resilient per-candidate: at backfill scale (~500 pages/cycle) the odd malformed page
        # must not abort the whole run. Each candidate is its own transaction (idempotent on
        # source_ref), so skipping a bad one and re-running later is safe.
        try:
            parsed, raw_rel = myneta.fetch_candidate(cid, cycle)
            with session_scope() as s:
                _persist_candidate(s, parsed, cycle=cycle, house=house, raw_rel=raw_rel)
            ok += 1
            print(f"  [{i}/{len(ids)}] {parsed.name} ({parsed.party}) "
                  f"assets={parsed.total_assets:,} cases={len(parsed.criminal_cases)}")
        except Exception as e:  # noqa: BLE001 - log, keep going, report at the end
            failed.append(cid)
            print(f"  [{i}/{len(ids)}] candidate {cid}: FAILED {type(e).__name__}: {e}")
    print(f"[myneta] done: {ok} ingested, {len(failed)} failed for {cycle}.")
    if failed:
        print(f"[myneta] failed candidate_ids ({cycle}): {','.join(failed)}")


def _scalar(s, sql: str, **params):
    return s.execute(text(sql), params).scalar()


def _persist_candidate(s, c: ParsedCandidate, *, cycle: str, house: str, raw_rel: str) -> None:
    house_id = _scalar(s, "SELECT id FROM house WHERE code = :code", code=house.upper())
    if house_id is None:
        raise RuntimeError(f"house {house!r} not seeded")
    term_cycle_id = _scalar(
        s, "SELECT id FROM term_cycle WHERE eci_election_id = :c ORDER BY number DESC LIMIT 1", c=cycle
    )
    filed_year = int(re.search(r"(\d{4})", cycle).group(1)) if re.search(r"\d{4}", cycle) else None
    source_url = myneta.candidate_url(c.candidate_id, cycle)

    # 1) source_ref (idempotent on source_id, native_id) -> id + existing person_id
    source_id = _scalar(s, "SELECT id FROM source WHERE code = 'myneta'")
    row = s.execute(
        text(
            """
            INSERT INTO source_ref (source_id, native_id, native_url, raw_name, raw_payload_ref)
            VALUES (:sid, :nid, :url, :name, :raw)
            ON CONFLICT (source_id, native_id) DO UPDATE
              SET native_url = EXCLUDED.native_url,
                  raw_name = EXCLUDED.raw_name,
                  raw_payload_ref = EXCLUDED.raw_payload_ref,
                  fetched_at = now()
            RETURNING id, person_id
            """
        ),
        {"sid": source_id, "nid": myneta.native_id(cycle, c.candidate_id), "url": source_url,
         "name": c.name, "raw": raw_rel},
    ).one()
    source_ref_id, person_id = row.id, row.person_id

    # 2) person (create if this source_ref isn't linked yet)
    birth_year = (filed_year - c.age) if (filed_year and c.age) else None
    if person_id is None:
        person_id = _scalar(
            s,
            """
            INSERT INTO person (display_name, normalized_name, birth_year)
            VALUES (:dn, :nn, :by) RETURNING id
            """,
            dn=c.name, nn=normalize_name(c.name), by=birth_year,
        )
        s.execute(
            text("UPDATE source_ref SET person_id = :pid WHERE id = :sid"),
            {"pid": person_id, "sid": source_ref_id},
        )
    s.execute(
        text(
            """
            INSERT INTO person_name_variant (person_id, variant, source_id, script)
            VALUES (:pid, :v, :sid, 'latin') ON CONFLICT DO NOTHING
            """
        ),
        {"pid": person_id, "v": c.name, "sid": source_id},
    )

    party_id = resolve_or_create_party_id(s, c.party) if c.party else None

    # Is this the latest cycle for the house? Past-cycle ingest must NOT claim the person's "current"
    # party (the partial unique party_affiliation_current_idx allows only one current row per person)
    # nor a "sitting" office term. This keeps re-runs idempotent even after merge_cycles has folded a
    # past-cycle candidate's source_ref onto the current (LS2024) person.
    is_latest_cycle = _scalar(
        s,
        """
        SELECT NOT EXISTS (
            SELECT 1 FROM term_cycle t2
            WHERE t2.house_id = :hid
              AND t2.number > (SELECT number FROM term_cycle WHERE id = :tcid)
        )
        """,
        hid=house_id, tcid=term_cycle_id,
    )
    term_status = "sitting" if is_latest_cycle else "former"

    # 3) wipe this source_ref's derived facts, then re-insert (idempotent re-run)
    for tbl in ("case_charge",):
        s.execute(text(
            "DELETE FROM case_charge WHERE criminal_case_id IN "
            "(SELECT id FROM criminal_case WHERE source_ref_id = :sr)"
        ), {"sr": source_ref_id})
    for tbl in ("criminal_case", "affidavit", "office_term", "party_affiliation"):
        s.execute(text(f"DELETE FROM {tbl} WHERE source_ref_id = :sr"), {"sr": source_ref_id})

    # 4) office_term (winner == sitting). ls_state_code = the seat's STATE. National (union) pages carry the
    # state inline; state-assembly pages put the DISTRICT in that slot instead (the election is one state),
    # so for a state house we stamp the house's own state rather than trust the parsed value.
    house_meta = s.execute(
        text("SELECT jurisdiction, state_code FROM house WHERE id = :hid"), {"hid": house_id}
    ).one()
    if house_meta.jurisdiction == "state":
        seat_state = _STATE_CODE_TO_NAME.get(house_meta.state_code) or c.state
    else:
        seat_state = c.state
    s.execute(
        text(
            """
            INSERT INTO office_term
              (person_id, house_id, term_cycle_id, constituency, ls_state_code, membership_type,
               party_id, status, source_ref_id)
            VALUES (:pid, :hid, :tcid, :con, :state, 'elected', :party, :status, :sr)
            """
        ),
        {"pid": person_id, "hid": house_id, "tcid": term_cycle_id, "con": c.constituency,
         "state": seat_state, "party": party_id, "status": term_status, "sr": source_ref_id},
    )

    # 5) party affiliation for this cycle (current only when this is the latest cycle)
    if party_id is not None:
        s.execute(
            text(
                """
                INSERT INTO party_affiliation
                  (person_id, party_id, is_current, detection, confidence, source_ref_id)
                VALUES (:pid, :party, :cur, 'structured_term_diff', 70, :sr)
                """
            ),
            {"pid": person_id, "party": party_id, "cur": is_latest_cycle, "sr": source_ref_id},
        )

    # 6) affidavit (assets/liabilities/income)
    affidavit_id = _scalar(
        s,
        """
        INSERT INTO affidavit
          (person_id, source_ref_id, election_cycle, house_id, filed_year, age, education,
           total_assets, total_liabilities, movable_assets, immovable_assets,
           self_income, income_year, raw_url)
        VALUES (:pid, :sr, :cycle, :hid, :fy, :age, :edu, :assets, :liab, :mov, :immov,
                :income, :iyear, :url)
        RETURNING id
        """,
        pid=person_id, sr=source_ref_id, cycle=cycle, hid=house_id, fy=filed_year,
        age=c.age, edu=c.education, assets=c.total_assets, liab=c.total_liabilities,
        mov=c.movable_assets, immov=c.immovable_assets,
        income=c.self_income, iyear=c.income_year, url=source_url,
    )

    # 7) criminal cases + charges (with derived severity)
    for case in c.criminal_cases:
        sections = case.sections
        severities = [
            _scalar(s, "SELECT base_severity FROM legal_section WHERE code_system=:cs AND section_number=:sn",
                    cs=code, sn=num)
            for code, num in sections
        ]
        severity = rollup_severity(severities)
        status = "convicted" if case.is_convicted else ("framed_charges" if case.charges_framed else "pending")
        case_id = _scalar(
            s,
            """
            INSERT INTO criminal_case
              (person_id, affidavit_id, source_ref_id, case_number, court, filed_year,
               status, is_convicted, severity, severity_rule_version, description)
            VALUES (:pid, :aid, :sr, :cn, :court, :fy, :st, :conv, :sev, :ver, :desc)
            RETURNING id
            """,
            pid=person_id, aid=affidavit_id, sr=source_ref_id,
            cn=case.fir_number, court=case.court, fy=filed_year, st=status,
            conv=case.is_convicted, sev=severity, ver=settings.severity_rule_version,
            desc=case.raw_sections,
        )
        for code, num in sections:
            section_id = _scalar(
                s, "SELECT id FROM legal_section WHERE code_system=:cs AND section_number=:sn",
                cs=code, sn=num,
            )
            s.execute(
                text(
                    """
                    INSERT INTO case_charge (criminal_case_id, section_id, raw_section_text)
                    VALUES (:cid, :sid, :raw)
                    """
                ),
                {"cid": case_id, "sid": section_id, "raw": f"{code} {num}"},
            )
