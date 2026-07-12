"""Resume assembly + search queries (read-only).

build_resume does the aggregate join and maps rows -> schemas, attaching a Source to every fact so the
frontend can render provenance on each datapoint.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from neta_api.schemas import (
    ActivityMetric,
    AffidavitWealth,
    ChargeSection,
    Contact,
    CriminalCase,
    Facets,
    FacetCount,
    NewsItem,
    OfficeTerm,
    ParliamentaryActivity,
    ParliamentaryDebate,
    ParliamentaryQuestion,
    ParliamentaryRecord,
    PartyStint,
    PartySwitch,
    PersonResume,
    PersonSummary,
    RoleEntry,
    Source,
    ThemeFocus,
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


def _build_activity(db: Session, person_id: int) -> ParliamentaryActivity | None:
    """The PRS activity scorecard + peer context, computed at read time from all same-term rows.

    Percentile = share of house peers whose count this MP strictly exceeds (top MP = 100). NULL counts
    (metric not reported) yield a null value + null percentile, never a misleading 0.
    """
    row = db.execute(
        text(
            """
            WITH me AS (
                SELECT pa.house_id, pa.term_cycle_id, pa.questions_asked, pa.debates_participated,
                       pa.private_member_bills, pa.period_start, pa.period_end,
                       h.name AS house_name,
                       s.code AS source_code, s.name AS source_name, s.trust_tier, sr.native_url
                FROM parliamentary_activity pa
                JOIN house h ON h.id = pa.house_id
                LEFT JOIN source_ref sr ON sr.id = pa.source_ref_id
                LEFT JOIN source s ON s.id = sr.source_id
                WHERE pa.person_id = :pid
                ORDER BY pa.period_end DESC NULLS LAST
                LIMIT 1
            ),
            peers AS (
                SELECT questions_asked AS q, debates_participated AS d, private_member_bills AS pmb
                FROM parliamentary_activity WHERE term_cycle_id = (SELECT term_cycle_id FROM me)
            )
            SELECT me.house_name, me.questions_asked, me.debates_participated, me.private_member_bills,
                   me.period_start, me.period_end,
                   me.source_code, me.source_name, me.trust_tier, me.native_url,
                   (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY q)   FROM peers) AS q_med,
                   (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY d)   FROM peers) AS d_med,
                   (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY pmb) FROM peers) AS pmb_med,
                   (SELECT count(*) FROM peers WHERE q   < me.questions_asked)      AS q_below,
                   (SELECT count(*) FROM peers WHERE d   < me.debates_participated) AS d_below,
                   (SELECT count(*) FROM peers WHERE pmb < me.private_member_bills) AS pmb_below,
                   (SELECT count(*) FROM peers) AS peer_n
            FROM me
            """
        ),
        {"pid": person_id},
    ).first()
    if row is None or not row.source_code:
        return None

    def metric(value, median, below) -> ActivityMetric:
        pct = None
        if value is not None and row.peer_n and row.peer_n > 1:
            pct = round(100.0 * below / (row.peer_n - 1))
        return ActivityMetric(value=value, house_median=median, percentile=pct)

    return ParliamentaryActivity(
        house=row.house_name,
        questions=metric(row.questions_asked, row.q_med, row.q_below),
        debates=metric(row.debates_participated, row.d_med, row.d_below),
        private_member_bills=metric(row.private_member_bills, row.pmb_med, row.pmb_below),
        period_start=row.period_start,
        period_end=row.period_end,
        source=Source(code=row.source_code, name=row.source_name, url=row.native_url,
                      trust_tier=row.trust_tier),
    )


# Cap the returned lists so a prolific MP doesn't bloat the payload — but high enough that the questions
# list is effectively complete for any LS MP (max ~a few hundred), so the theme filter chips match what the
# list shows. The full tallies still come from a cheap count(*) for the "showing N of total" note.
_RECORD_LIST_CAP = 300

# Below this many distinct MPs in the term's question corpus, a "House average" is not yet meaningful
# (e.g. before the full-house ingest) — we return house_share = None so the UI shows the MP's own mix only.
_HOUSE_AVG_MIN_MEMBERS = 25


def _build_thematic_focus(db: Session, person_id: int) -> list[ThemeFocus]:
    """Policy-theme emphasis of an MP's questions vs the House, from the ministry->theme map (read time).

    Descriptive only (topical mix from official ministry tags). `share` = this MP's fraction per theme;
    `house_share` = the pooled same-term fraction, or None until the house corpus has enough members.
    """
    rows = db.execute(
        text(
            """
            WITH me_terms AS (
                SELECT DISTINCT term_cycle_id FROM parliamentary_question WHERE person_id = :pid
            ),
            me AS (
                SELECT COALESCE(mt.theme, 'Other') AS theme, count(*) AS cnt
                FROM parliamentary_question pq
                LEFT JOIN ministry_theme mt ON mt.ministry_key = lower(btrim(pq.ministry))
                WHERE pq.person_id = :pid
                GROUP BY 1
            ),
            house AS (
                SELECT COALESCE(mt.theme, 'Other') AS theme, count(*) AS cnt
                FROM parliamentary_question pq
                LEFT JOIN ministry_theme mt ON mt.ministry_key = lower(btrim(pq.ministry))
                WHERE pq.term_cycle_id IN (SELECT term_cycle_id FROM me_terms)
                GROUP BY 1
            )
            SELECT me.theme, me.cnt AS me_cnt,
                   (SELECT sum(cnt) FROM me) AS me_total,
                   h.cnt AS house_cnt,
                   (SELECT sum(cnt) FROM house) AS house_total,
                   (SELECT count(DISTINCT person_id) FROM parliamentary_question
                    WHERE term_cycle_id IN (SELECT term_cycle_id FROM me_terms)) AS house_members
            FROM me LEFT JOIN house h ON h.theme = me.theme
            ORDER BY me.cnt DESC, me.theme
            """
        ),
        {"pid": person_id},
    ).all()
    if not rows:
        return []

    me_total = rows[0].me_total or 0
    house_total = rows[0].house_total or 0
    house_ok = (rows[0].house_members or 0) >= _HOUSE_AVG_MIN_MEMBERS and house_total > 0
    out: list[ThemeFocus] = []
    for r in rows:
        out.append(ThemeFocus(
            theme=r.theme,
            count=r.me_cnt,
            share=(r.me_cnt / me_total) if me_total else 0.0,
            house_share=(r.house_cnt / house_total) if (house_ok and r.house_cnt is not None) else None,
        ))
    return out


def _build_parliamentary_record(db: Session, person_id: int) -> ParliamentaryRecord | None:
    """Individual questions + debates from PRS profiles, newest first, capped; None if the MP has none."""
    counts = db.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM parliamentary_question WHERE person_id = :pid) AS q_count,
              (SELECT count(*) FROM parliamentary_debate   WHERE person_id = :pid) AS d_count,
              (SELECT h.name FROM office_term ot JOIN house h ON h.id = ot.house_id
                 WHERE ot.person_id = :pid ORDER BY ot.start_date DESC NULLS LAST LIMIT 1) AS house_name
            """
        ),
        {"pid": person_id},
    ).first()
    if not counts or (counts.q_count == 0 and counts.d_count == 0):
        return None

    questions = [
        ParliamentaryQuestion(
            id=r.id, subject=r.subject, ministry=r.ministry, theme=r.theme, question_type=r.question_type,
            asked_date=r.asked_date, document_url=r.document_url,
        )
        for r in db.execute(
            text(
                """
                SELECT pq.id, pq.subject, pq.ministry, pq.question_type, pq.asked_date, pq.document_url,
                       COALESCE(mt.theme, 'Other') AS theme
                FROM parliamentary_question pq
                LEFT JOIN ministry_theme mt ON mt.ministry_key = lower(btrim(pq.ministry))
                WHERE pq.person_id = :pid
                ORDER BY pq.asked_date DESC NULLS LAST, pq.id DESC
                LIMIT :cap
                """
            ),
            {"pid": person_id, "cap": _RECORD_LIST_CAP},
        )
    ]
    debates = [
        ParliamentaryDebate(
            id=r.id, title=r.title, debate_type=r.debate_type, debate_date=r.debate_date,
            document_url=r.document_url,
        )
        for r in db.execute(
            text(
                """
                SELECT id, title, debate_type, debate_date, document_url
                FROM parliamentary_debate WHERE person_id = :pid
                ORDER BY debate_date DESC NULLS LAST, id DESC
                LIMIT :cap
                """
            ),
            {"pid": person_id, "cap": _RECORD_LIST_CAP},
        )
    ]
    # One PRS source_ref backs all of a member's rows — read it once for the container-level provenance.
    src = db.execute(
        text(
            """
            SELECT s.code AS source_code, s.name AS source_name, s.trust_tier, sr.native_url
            FROM parliamentary_question pq
            JOIN source_ref sr ON sr.id = pq.source_ref_id
            JOIN source s ON s.id = sr.source_id
            WHERE pq.person_id = :pid
            UNION ALL
            SELECT s.code, s.name, s.trust_tier, sr.native_url
            FROM parliamentary_debate pd
            JOIN source_ref sr ON sr.id = pd.source_ref_id
            JOIN source s ON s.id = sr.source_id
            WHERE pd.person_id = :pid
            LIMIT 1
            """
        ),
        {"pid": person_id},
    ).first()

    return ParliamentaryRecord(
        house=counts.house_name or "",
        questions_count=counts.q_count,
        debates_count=counts.d_count,
        questions=questions,
        debates=debates,
        thematic_focus=_build_thematic_focus(db, person_id),
        source=_source(src) if src else Source(code="prs", name="PRS Legislative Research",
                                               url=None, trust_tier=2),
    )


def build_resume(db: Session, person_id: int) -> PersonResume | None:
    person = db.execute(
        text(
            """
            SELECT p.id, p.display_name, p.photo_url, p.relative_name, p.home_state,
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
                       COALESCE(ot.ls_state_code, ot.rs_state_code) AS state,
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
                ORDER BY COALESCE(tc.start_date, DATE '2099-12-31') DESC
                """
            ),
            {"pid": person_id},
        )
    ]

    roles = [
        RoleEntry(
            role_type=r.role_type,
            title=r.title,
            body=r.body,
            house=r.house,
            portfolio=r.portfolio,
            start_date=r.start_date,
            end_date=r.end_date,
            status=r.status,
            source=_source(r),
        )
        for r in db.execute(
            text(
                """
                SELECT rl.role_type, rl.title, rl.body, h.name AS house, rl.portfolio,
                       rl.start_date, rl.end_date, rl.status,
                       s.code AS source_code, s.name AS source_name, s.trust_tier, sr.native_url
                FROM role rl
                LEFT JOIN house h ON h.id = rl.house_id
                JOIN source_ref sr ON sr.id = rl.source_ref_id
                JOIN source s ON s.id = sr.source_id
                WHERE rl.person_id = :pid
                ORDER BY (rl.status = 'current') DESC, rl.start_date DESC NULLS LAST
                """
            ),
            {"pid": person_id},
        )
    ]

    contacts = [
        Contact(
            channel_type=r.channel_type,
            value=r.value,
            label=r.label,
            source=_source(r),
        )
        for r in db.execute(
            text(
                """
                SELECT c.channel_type, c.value, c.label,
                       s.code AS source_code, s.name AS source_name, s.trust_tier, sr.native_url
                FROM contact c
                JOIN source_ref sr ON sr.id = c.source_ref_id
                JOIN source s ON s.id = sr.source_id
                WHERE c.person_id = :pid
                ORDER BY CASE c.channel_type WHEN 'email' THEN 1 WHEN 'phone' THEN 2
                         WHEN 'office_address' THEN 3 WHEN 'website' THEN 4 ELSE 5 END
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
            sections=[ChargeSection(**sec) for sec in (r.sections or [])],
            description=r.description,
            source=_source(r),
        )
        for r in db.execute(
            text(
                """
                SELECT c.case_number, c.court, c.filed_year, c.status, c.is_convicted, c.severity,
                       c.description, s.code AS source_code, s.name AS source_name, s.trust_tier,
                       sr.native_url,
                       COALESCE(
                         json_agg(
                           json_build_object(
                             'raw', cc.raw_section_text,
                             'title', ls.title,
                             'equivalent', CASE
                               WHEN ls.code_system = 'BNS' AND ls.ipc_equivalent IS NOT NULL
                                 THEN 'IPC ' || ls.ipc_equivalent
                               WHEN ls.code_system = 'IPC' AND ls.bns_equivalent IS NOT NULL
                                 THEN 'BNS ' || ls.bns_equivalent
                               ELSE NULL END
                           ) ORDER BY cc.id
                         ) FILTER (WHERE cc.id IS NOT NULL),
                         '[]'
                       ) AS sections
                FROM criminal_case c
                JOIN source_ref sr ON sr.id = c.source_ref_id
                JOIN source s ON s.id = sr.source_id
                LEFT JOIN case_charge cc ON cc.criminal_case_id = c.id
                LEFT JOIN legal_section ls ON ls.id = cc.section_id
                WHERE c.person_id = :pid
                GROUP BY c.id, s.code, s.name, s.trust_tier, sr.native_url
                ORDER BY c.filed_year DESC NULLS LAST
                """
            ),
            {"pid": person_id},
        )
    ]

    news = [
        NewsItem(
            title=r.title,
            snippet=r.snippet,
            url=r.url,
            publisher=r.publisher,
            published_at=r.published_at,
            source=_source(r),
        )
        for r in db.execute(
            text(
                """
                SELECT n.title, n.snippet, n.url, n.publisher, n.published_at,
                       s.code AS source_code, s.name AS source_name, s.trust_tier, sr.native_url
                FROM news_item n
                JOIN source_ref sr ON sr.id = n.source_ref_id
                JOIN source s ON s.id = sr.source_id
                WHERE n.person_id = :pid
                ORDER BY n.published_at DESC NULLS LAST, n.fetched_at DESC
                LIMIT 15
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
        relative_name=person.relative_name,
        home_state=person.home_state,
        office_terms=office_terms,
        roles=roles,
        contacts=contacts,
        party_history=party_history,
        party_switches=party_switches,
        wealth=wealth,
        criminal_cases=criminal_cases,
        activity=_build_activity(db, person_id),
        parliamentary_record=_build_parliamentary_record(db, person_id),
        news=news,
    )


# Shared summary projection: per person, current party + house/constituency, latest assets,
# case counts, and worst severity. Used raw by search (filters on base columns) and wrapped as a
# subquery `s` by list/facets (so the computed columns below are filterable/sortable by name).
_SUMMARY_BASE = """
    SELECT p.id, p.display_name, p.photo_url,
           (SELECT variant FROM person_name_variant
            WHERE person_id = p.id AND script = 'devanagari' LIMIT 1) AS native_name,
           cur.party       AS current_party,
           oh.house        AS current_house,
           oh.jurisdiction AS jurisdiction,
           oh.constituency AS constituency,
           oh.state        AS state,
           w.total_assets  AS net_assets,
           w.age           AS age,
           w.education     AS education,
           p.gender        AS gender,
           COALESCE(cc.total, 0)   AS total_cases,
           COALESCE(cc.pending, 0) AS pending_cases,
           sev.severity    AS top_severity,
           oh.attendance_pct AS current_attendance_pct,
           qc.cnt          AS questions_count,
           tt.theme        AS top_theme
    FROM person p
    LEFT JOIN LATERAL (
        SELECT pt.canonical_name AS party
        FROM party_affiliation pa JOIN party pt ON pt.id = pa.party_id
        WHERE pa.person_id = p.id AND pa.is_current LIMIT 1
    ) cur ON true
    LEFT JOIN LATERAL (
        SELECT h.name AS house, h.jurisdiction AS jurisdiction,
               COALESCE(ot.constituency, ot.rs_state_code) AS constituency,
               COALESCE(ot.ls_state_code, ot.rs_state_code) AS state,
               ot.attendance_pct
        FROM office_term ot
        JOIN house h ON h.id = ot.house_id
        JOIN term_cycle tc ON tc.id = ot.term_cycle_id
        -- current term = the sitting one; tie-break by most-recent DATE (cycle number isn't comparable
        -- across houses — LS is 15–18, state assemblies use year-numbers; RS-CURRENT has no date).
        WHERE ot.person_id = p.id
        ORDER BY (ot.status = 'sitting') DESC, COALESCE(tc.start_date, DATE '2099-12-31') DESC LIMIT 1
    ) oh ON true
    LEFT JOIN LATERAL (
        SELECT total_assets, age, education FROM affidavit
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
    -- Parliamentary-questions discovery signals. Both are LIMIT-1 / single-row LATERALs, so the planner
    -- removes them from the count/facets queries that don't reference them (left-join removal).
    LEFT JOIN LATERAL (
        SELECT count(*) AS cnt FROM parliamentary_question WHERE person_id = p.id
    ) qc ON true
    LEFT JOIN LATERAL (
        SELECT COALESCE(mt.theme, 'Other') AS theme
        FROM parliamentary_question pq
        LEFT JOIN ministry_theme mt ON mt.ministry_key = lower(btrim(pq.ministry))
        WHERE pq.person_id = p.id
        GROUP BY 1 ORDER BY count(*) DESC LIMIT 1
    ) tt ON true
"""

# Search filters/orders on base columns (p.normalized_name, p.display_name), so it appends its own tail.
_SUMMARY_SQL = _SUMMARY_BASE + """
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
        state=r.state,
        net_assets=r.net_assets,
        age=r.age,
        education=r.education,
        gender=r.gender,
        pending_cases=r.pending_cases,
        total_cases=r.total_cases,
        top_severity=r.top_severity,
        current_attendance_pct=float(r.current_attendance_pct) if r.current_attendance_pct is not None else None,
        questions_count=r.questions_count or None,   # 0 questions -> None (missing != zero; hides the card row)
        top_theme=r.top_theme,
    )


# Normalize a name for filtering: uppercase, drop everything but letters/digits (so "Tamil Nadu",
# "TAMIL-NADU" and "tamilnadu" all match). Used for state/constituency filters.
_NORM = "upper(regexp_replace({col}, '[^a-zA-Z0-9]', '', 'g')) = upper(regexp_replace(:{p}, '[^a-zA-Z0-9]', '', 'g'))"


# sort key -> ORDER BY fragment (whitelist: the raw ?sort= value is never interpolated into SQL).
_SORTS = {
    "assets": "net_assets DESC NULLS LAST, display_name",
    "cases": "total_cases DESC, display_name",
    "attendance": "current_attendance_pct DESC NULLS LAST, display_name",
    "theme_questions": "questions_count DESC NULLS LAST, display_name",
    "name": "display_name ASC",
}

# ?cases= value -> predicate over the wrapped subquery (fixed SQL, no user text interpolated).
_CASE_FILTERS = {
    "with": "s.total_cases > 0",
    "clean": "s.total_cases = 0",
    "heinous": "s.top_severity = 'heinous'",
    "serious": "s.top_severity = 'serious'",
    "minor": "s.top_severity = 'minor'",
}


def _list_conditions(params: dict, *, house=None, state=None, constituency=None, jurisdiction=None,
                     party=None, cases=None, q=None, theme=None) -> list[str]:
    """WHERE conditions over the wrapped summary subquery `s`; mutates `params` with bound values."""
    conds: list[str] = []
    if theme:
        # MPs with >= 1 question in this policy area (theme via the ministry_theme map; read-time).
        conds.append(
            "EXISTS (SELECT 1 FROM parliamentary_question pq "
            "LEFT JOIN ministry_theme mt ON mt.ministry_key = lower(btrim(pq.ministry)) "
            "WHERE pq.person_id = s.id AND COALESCE(mt.theme, 'Other') = :theme)"
        )
        params["theme"] = theme
    if house:
        conds.append("s.current_house = :house")
        params["house"] = house
    if jurisdiction:
        conds.append("s.jurisdiction = :jurisdiction")
        params["jurisdiction"] = jurisdiction
    if state:
        conds.append(_NORM.format(col="s.state", p="state"))
        params["state"] = state
    if constituency:
        conds.append(_NORM.format(col="s.constituency", p="constituency"))
        params["constituency"] = constituency
    if party:
        conds.append("s.current_party = :party")
        params["party"] = party
    if cases in _CASE_FILTERS:
        conds.append(_CASE_FILTERS[cases])
    if q and q.strip():
        conds.append("(s.display_name ILIKE :q OR s.current_party ILIKE :q "
                     "OR s.constituency ILIKE :q OR s.native_name ILIKE :q)")
        params["q"] = f"%{q.strip()}%"
    return conds


def list_persons(db: Session, *, limit: int = 60, offset: int = 0, house: str | None = None,
                 state: str | None = None, constituency: str | None = None, jurisdiction: str | None = None,
                 party: str | None = None, cases: str | None = None, q: str | None = None,
                 theme: str | None = None, sort: str = "assets") -> tuple[list[PersonSummary], int]:
    """Browse legislators: filter (house/jurisdiction/state/constituency/party/cases/theme/search) + sort +
    page. Returns (page rows, total matching count) so the caller can emit an X-Total-Count header."""
    params: dict = {"limit": limit, "offset": offset}
    conds = _list_conditions(params, house=house, state=state, constituency=constituency,
                             jurisdiction=jurisdiction, party=party, cases=cases, q=q, theme=theme)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    # When a theme is selected, "sort by questions" means questions IN THAT theme (a true theme leaderboard),
    # not overall volume. Compute a theme-scoped count and sort on it; otherwise sort by total questions.
    sorts, extra = _SORTS, ""
    if theme:
        theme_count = ("(SELECT count(*) FROM parliamentary_question pq "
                       "LEFT JOIN ministry_theme mt ON mt.ministry_key = lower(btrim(pq.ministry)) "
                       "WHERE pq.person_id = s.id AND COALESCE(mt.theme,'Other') = :theme)")
        extra = f", {theme_count} AS theme_q_count"
        sorts = {**_SORTS, "theme_questions": "theme_q_count DESC NULLS LAST, display_name"}
    order = "ORDER BY " + sorts.get(sort, sorts["assets"])
    total = db.execute(text(f"SELECT count(*) FROM ({_SUMMARY_BASE}) s {where}"), params).scalar_one()
    rows = db.execute(
        text(f"SELECT s.*{extra} FROM ({_SUMMARY_BASE}) s {where} {order} LIMIT :limit OFFSET :offset"),
        params,
    )
    return [_to_summary(r) for r in rows], total


def facets(db: Session, *, house: str | None = None, state: str | None = None,
           jurisdiction: str | None = None) -> Facets:
    """Distinct party / state / house option lists (+counts) for a browse scope, to populate dropdowns."""
    params: dict = {}
    conds = _list_conditions(params, house=house, state=state, jurisdiction=jurisdiction)

    def group(col: str) -> list[FacetCount]:
        where = "WHERE " + " AND ".join([*conds, f"{col} IS NOT NULL"])
        sql = f"SELECT {col} AS value, count(*) AS n FROM ({_SUMMARY_BASE}) s {where} GROUP BY {col} ORDER BY n DESC, value"
        return [FacetCount(value=r.value, count=r.n) for r in db.execute(text(sql), params)]

    def themes_group() -> list[FacetCount]:
        # Policy themes (via ministry_theme) with the count of distinct MPs who asked in each. Only restrict
        # to a person-id subquery when a scope filter is active — unscoped, group the questions directly
        # (every question already belongs to a real person), avoiding a needless _SUMMARY_BASE re-run.
        scope = (f"WHERE pq.person_id IN (SELECT s.id FROM ({_SUMMARY_BASE}) s "
                 f"WHERE {' AND '.join(conds)})") if conds else ""
        sql = (
            "SELECT COALESCE(mt.theme, 'Other') AS value, count(DISTINCT pq.person_id) AS n "
            "FROM parliamentary_question pq "
            "LEFT JOIN ministry_theme mt ON mt.ministry_key = lower(btrim(pq.ministry)) "
            f"{scope} GROUP BY 1 ORDER BY n DESC, value"
        )
        return [FacetCount(value=r.value, count=r.n) for r in db.execute(text(sql), params)]

    return Facets(parties=group("s.current_party"), states=group("s.state"),
                  houses=group("s.current_house"), themes=themes_group())


def search_persons(db: Session, q: str, limit: int = 25) -> list[PersonSummary]:
    sql = _SUMMARY_SQL.format(
        where="WHERE p.normalized_name % :q OR p.display_name ILIKE '%' || :q || '%'",
        order="ORDER BY similarity(p.normalized_name, :q) DESC",
    )
    rows = db.execute(text(sql), {"q": q, "limit": limit, "offset": 0})
    return [_to_summary(r) for r in rows]


_STATS_SQL = """
SELECT
  (SELECT count(*) FROM person) AS total_legislators,
  (SELECT count(DISTINCT ot.person_id) FROM office_term ot
     JOIN term_cycle tc ON tc.id = ot.term_cycle_id JOIN house h ON h.id = tc.house_id
     WHERE h.code = 'LS') AS lok_sabha,
  (SELECT count(DISTINCT ot.person_id) FROM office_term ot
     JOIN term_cycle tc ON tc.id = ot.term_cycle_id JOIN house h ON h.id = tc.house_id
     WHERE h.code = 'RS') AS rajya_sabha,
  (SELECT count(DISTINCT person_id) FROM criminal_case) AS with_cases,
  (SELECT count(*) FROM (
     SELECT DISTINCT ON (person_id) person_id, total_assets
     FROM affidavit ORDER BY person_id, filed_year DESC NULLS LAST
   ) latest WHERE total_assets >= 10000000) AS crorepatis
"""


def stats(db: Session) -> dict:
    """Headline counts for the homepage: total legislators, per house, with cases, crorepatis (>= ₹1cr)."""
    r = db.execute(text(_STATS_SQL)).one()
    return {
        "total_legislators": r.total_legislators,
        "lok_sabha": r.lok_sabha,
        "rajya_sabha": r.rajya_sabha,
        "with_cases": r.with_cases,
        "crorepatis": r.crorepatis,
    }
