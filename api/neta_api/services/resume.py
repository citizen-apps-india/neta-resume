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


def build_resume(db: Session, person_id: int) -> PersonResume | None:
    person = db.execute(
        text("SELECT id, display_name FROM person WHERE id = :pid"), {"pid": person_id}
    ).first()
    if person is None:
        return None

    office_terms = [
        OfficeTerm(
            house=r.house,
            cycle_number=r.cycle_number,
            constituency=r.constituency,
            party=r.party,
            membership_type=r.membership_type,
            start_date=r.start_date,
            end_date=r.end_date,
            status=r.status,
            source=_source(r),
        )
        for r in db.execute(
            text(
                """
                SELECT h.name AS house, tc.number AS cycle_number, ot.constituency,
                       pt.canonical_name AS party, ot.membership_type, ot.start_date, ot.end_date,
                       ot.status, s.code AS source_code, s.name AS source_name, s.trust_tier,
                       sr.native_url
                FROM office_term ot
                JOIN house h ON h.id = ot.house_id
                JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                LEFT JOIN party pt ON pt.id = ot.party_id
                JOIN source_ref sr ON sr.id = ot.source_ref_id
                JOIN source s ON s.id = sr.source_id
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

    wealth = [
        AffidavitWealth(
            election_cycle=r.election_cycle,
            filed_year=r.filed_year,
            total_assets=r.total_assets,
            total_liabilities=r.total_liabilities,
            self_income=r.self_income,
            source=_source(r),
        )
        for r in db.execute(
            text(
                """
                SELECT a.election_cycle, a.filed_year, a.total_assets, a.total_liabilities,
                       a.self_income, s.code AS source_code, s.name AS source_name, s.trust_tier,
                       sr.native_url
                FROM affidavit a
                JOIN source_ref sr ON sr.id = a.source_ref_id
                JOIN source s ON s.id = sr.source_id
                WHERE a.person_id = :pid
                ORDER BY a.filed_year
                """
            ),
            {"pid": person_id},
        )
    ]

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
        office_terms=office_terms,
        party_history=party_history,
        wealth=wealth,
        criminal_cases=criminal_cases,
    )


def search_persons(db: Session, q: str) -> list[PersonSummary]:
    rows = db.execute(
        text(
            """
            SELECT p.id, p.display_name,
                   pt.canonical_name AS current_party,
                   h.name AS current_house,
                   ot.constituency
            FROM person p
            LEFT JOIN LATERAL (
                SELECT party_id, source_ref_id FROM party_affiliation
                WHERE person_id = p.id AND is_current LIMIT 1
            ) cur ON true
            LEFT JOIN party pt ON pt.id = cur.party_id
            LEFT JOIN LATERAL (
                SELECT house_id, constituency FROM office_term
                WHERE person_id = p.id ORDER BY term_cycle_id DESC LIMIT 1
            ) ot ON true
            LEFT JOIN house h ON h.id = ot.house_id
            WHERE p.normalized_name % :q OR p.display_name ILIKE '%' || :q || '%'
            ORDER BY similarity(p.normalized_name, :q) DESC
            LIMIT 25
            """
        ),
        {"q": q},
    )
    return [
        PersonSummary(
            id=r.id,
            display_name=r.display_name,
            current_party=r.current_party,
            current_house=r.current_house,
            constituency=r.constituency,
        )
        for r in rows
    ]
