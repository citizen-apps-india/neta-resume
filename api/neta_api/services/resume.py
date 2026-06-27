"""Resume assembly + search queries (read-only).

build_resume does the aggregate join and maps rows -> schemas, attaching a Source to every fact so the
frontend can render provenance on each datapoint.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from neta_api.schemas import (
    AffidavitWealth,
    CriminalCase,
    OfficeTerm,
    PartyStint,
    PartySwitch,
    PersonResume,
    PersonSummary,
    Source,
)


def _source(row) -> Source:
    return Source(
        code=row.source_code,
        name=row.source_name,
        url=row.native_url,
        trust_tier=row.trust_tier,
    )


def _attendance_source(row) -> Source | None:
    """Provenance for the attendance figure (PRS), from att_*-prefixed columns; None if no record."""
    if not row.att_code:
        return None
    return Source(code=row.att_code, name=row.att_name, url=row.att_url, trust_tier=row.att_trust)


def build_resume(db: Session, person_id: int) -> PersonResume | None:
    person = db.execute(
        text(
            """
            SELECT p.id, p.display_name, p.photo_url,
                   (SELECT variant FROM person_name_variant
                    WHERE person_id = p.id AND script = 'devanagari' LIMIT 1) AS native_name
            FROM person p WHERE p.id = :pid
            """
        ),
        {"pid": person_id},
    ).first()
    if person is None:
        return None

    office_terms = [
        OfficeTerm(
            house=r.house,
            cycle_number=r.cycle_number,
            constituency=r.constituency,
            state=r.state,
            party=r.party,
            membership_type=r.membership_type,
            start_date=r.start_date,
            end_date=r.end_date,
            status=r.status,
            source=_source(r),
            attendance_pct=float(r.attendance_pct) if r.attendance_pct is not None else None,
            attendance_source=_attendance_source(r),
        )
        for r in db.execute(
            text(
                """
                SELECT h.name AS house, tc.number AS cycle_number, ot.constituency,
                       ot.rs_state_code AS state,
                       pt.canonical_name AS party, ot.membership_type, ot.start_date, ot.end_date,
                       ot.status, s.code AS source_code, s.name AS source_name, s.trust_tier,
                       sr.native_url, ot.attendance_pct,
                       att_s.code AS att_code, att_s.name AS att_name, att_s.trust_tier AS att_trust,
                       att_sr.native_url AS att_url
                FROM office_term ot
                JOIN house h ON h.id = ot.house_id
                JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                LEFT JOIN party pt ON pt.id = ot.party_id
                JOIN source_ref sr ON sr.id = ot.source_ref_id
                JOIN source s ON s.id = sr.source_id
                LEFT JOIN source_ref att_sr ON att_sr.id = ot.attendance_source_ref_id
                LEFT JOIN source att_s ON att_s.id = att_sr.source_id
                WHERE ot.person_id = :pid
                ORDER BY tc.number DESC
                """
            ),
            {"pid": person_id},
        )
    ]

    party_history = [
        PartyStint(
            party=r.party,
            joined_date=r.joined_date,
            left_date=r.left_date,
            is_current=r.is_current,
            join_reason=r.join_reason,
            leave_reason=r.leave_reason,
            reason_source=None,
            source=_source(r),
        )
        for r in db.execute(
            text(
                """
                SELECT pt.canonical_name AS party, pa.joined_date, pa.left_date, pa.is_current,
                       pa.join_reason, pa.leave_reason,
                       s.code AS source_code, s.name AS source_name, s.trust_tier, sr.native_url
                FROM party_affiliation pa
                JOIN party pt ON pt.id = pa.party_id
                JOIN source_ref sr ON sr.id = pa.source_ref_id
                JOIN source s ON s.id = sr.source_id
                WHERE pa.person_id = :pid
                ORDER BY pa.is_current DESC, pa.joined_date NULLS LAST
                """
            ),
            {"pid": person_id},
        )
    ]

    party_switches = [
        PartySwitch(
            from_party=r.from_party,
            to_party=r.to_party,
            event_date=r.event_date,
            narrative=r.narrative,
            source=_source(r) if r.source_code else None,
        )
        for r in db.execute(
            text(
                """
                SELECT fp.canonical_name AS from_party, tp.canonical_name AS to_party,
                       e.event_date, e.narrative,
                       s.code AS source_code, COALESCE(sr.raw_name, s.name) AS source_name,
                       s.trust_tier, sr.native_url
                FROM party_switch_event e
                JOIN party tp ON tp.id = e.to_party_id
                LEFT JOIN party fp ON fp.id = e.from_party_id
                LEFT JOIN source_ref sr ON sr.id = e.narrative_source_ref_id
                LEFT JOIN source s ON s.id = sr.source_id
                WHERE e.person_id = :pid
                ORDER BY e.event_date NULLS LAST
                """
            ),
            {"pid": person_id},
        )
    ]

    wealth_rows = list(
        db.execute(
            text(
                """
                SELECT a.election_cycle, a.filed_year, a.total_assets, a.total_liabilities,
                       a.movable_assets, a.immovable_assets, a.self_income, a.age, a.education,
                       s.code AS source_code, s.name AS source_name, s.trust_tier, sr.native_url
                FROM affidavit a
                JOIN source_ref sr ON sr.id = a.source_ref_id
                JOIN source s ON s.id = sr.source_id
                WHERE a.person_id = :pid
                ORDER BY a.filed_year
                """
            ),
            {"pid": person_id},
        )
    )
    wealth = [
        AffidavitWealth(
            election_cycle=r.election_cycle,
            filed_year=r.filed_year,
            total_assets=r.total_assets,
            total_liabilities=r.total_liabilities,
            movable_assets=r.movable_assets,
            immovable_assets=r.immovable_assets,
            self_income=r.self_income,
            source=_source(r),
        )
        for r in wealth_rows
    ]
    # Person-level age/education come from the most recent affidavit.
    latest = wealth_rows[-1] if wealth_rows else None

    criminal_cases = [
        CriminalCase(
            case_number=r.case_number,
            court=r.court,
            filed_year=r.filed_year,
            status=r.status,
            is_convicted=r.is_convicted,
            severity=r.severity,
            sections=list(r.sections) if r.sections else [],
            description=r.description,
            source=_source(r),
        )
        for r in db.execute(
            text(
                """
                SELECT c.case_number, c.court, c.filed_year, c.status, c.is_convicted, c.severity,
                       c.description, s.code AS source_code, s.name AS source_name, s.trust_tier,
                       sr.native_url,
                       ARRAY_REMOVE(ARRAY_AGG(cc.raw_section_text ORDER BY cc.id), NULL) AS sections
                FROM criminal_case c
                JOIN source_ref sr ON sr.id = c.source_ref_id
                JOIN source s ON s.id = sr.source_id
                LEFT JOIN case_charge cc ON cc.criminal_case_id = c.id
                WHERE c.person_id = :pid
                GROUP BY c.id, s.code, s.name, s.trust_tier, sr.native_url
                ORDER BY c.filed_year DESC NULLS LAST
                """
            ),
            {"pid": person_id},
        )
    ]

    return PersonResume(
        id=person.id,
        display_name=person.display_name,
        native_name=person.native_name,
        photo_url=person.photo_url,
        age=latest.age if latest else None,
        education=latest.education if latest else None,
        office_terms=office_terms,
        party_history=party_history,
        party_switches=party_switches,
        wealth=wealth,
        criminal_cases=criminal_cases,
    )


# Shared summary projection: per person, current party + house/constituency, latest assets,
# case counts, and worst severity. `{where}` and `{order}` are filled by list/search.
_SUMMARY_SQL = """
    SELECT p.id, p.display_name, p.photo_url,
           (SELECT variant FROM person_name_variant
            WHERE person_id = p.id AND script = 'devanagari' LIMIT 1) AS native_name,
           cur.party       AS current_party,
           oh.house        AS current_house,
           oh.constituency AS constituency,
           w.total_assets  AS net_assets,
           COALESCE(cc.total, 0)   AS total_cases,
           COALESCE(cc.pending, 0) AS pending_cases,
           sev.severity    AS top_severity,
           oh.attendance_pct AS current_attendance_pct
    FROM person p
    LEFT JOIN LATERAL (
        SELECT pt.canonical_name AS party
        FROM party_affiliation pa JOIN party pt ON pt.id = pa.party_id
        WHERE pa.person_id = p.id AND pa.is_current LIMIT 1
    ) cur ON true
    LEFT JOIN LATERAL (
        SELECT h.name AS house, COALESCE(ot.constituency, ot.rs_state_code) AS constituency,
               ot.attendance_pct
        FROM office_term ot JOIN house h ON h.id = ot.house_id
        WHERE ot.person_id = p.id ORDER BY ot.term_cycle_id DESC LIMIT 1
    ) oh ON true
    LEFT JOIN LATERAL (
        SELECT total_assets FROM affidavit
        WHERE person_id = p.id ORDER BY filed_year DESC LIMIT 1
    ) w ON true
    LEFT JOIN LATERAL (
        SELECT count(*) AS total, count(*) FILTER (WHERE NOT is_convicted) AS pending
        FROM criminal_case WHERE person_id = p.id
    ) cc ON true
    LEFT JOIN LATERAL (
        SELECT severity FROM criminal_case
        WHERE person_id = p.id AND severity IS NOT NULL
        ORDER BY CASE severity WHEN 'heinous' THEN 1 WHEN 'serious' THEN 2 WHEN 'minor' THEN 3 ELSE 4 END
        LIMIT 1
    ) sev ON true
    {where}
    {order}
    LIMIT :limit OFFSET :offset
"""


def _to_summary(r) -> PersonSummary:
    return PersonSummary(
        id=r.id,
        display_name=r.display_name,
        native_name=r.native_name,
        photo_url=r.photo_url,
        current_party=r.current_party,
        current_house=r.current_house,
        constituency=r.constituency,
        net_assets=r.net_assets,
        pending_cases=r.pending_cases,
        total_cases=r.total_cases,
        top_severity=r.top_severity,
        current_attendance_pct=float(r.current_attendance_pct) if r.current_attendance_pct is not None else None,
    )


def list_persons(db: Session, limit: int = 60, offset: int = 0, house: str | None = None) -> list[PersonSummary]:
    where = "WHERE oh.house = :house" if house else ""
    sql = _SUMMARY_SQL.format(where=where, order="ORDER BY w.total_assets DESC NULLS LAST, p.display_name")
    params: dict = {"limit": limit, "offset": offset}
    if house:
        params["house"] = house
    rows = db.execute(text(sql), params)
    return [_to_summary(r) for r in rows]


def search_persons(db: Session, q: str, limit: int = 25) -> list[PersonSummary]:
    sql = _SUMMARY_SQL.format(
        where="WHERE p.normalized_name % :q OR p.display_name ILIKE '%' || :q || '%'",
        order="ORDER BY similarity(p.normalized_name, :q) DESC",
    )
    rows = db.execute(text(sql), {"q": q, "limit": limit, "offset": 0})
    return [_to_summary(r) for r in rows]
