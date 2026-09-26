"""Public API contract (Pydantic). The frontend codegens TypeScript from the OpenAPI this produces.

Every fact-bearing model carries a `source` (provenance) so the UI can render a link on each datapoint.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["heinous", "serious", "minor"]

# Alias so a model can expose a field literally named `date` without the field default shadowing the
# `date` type in its own annotation (see RecordHit).
_Date = date


class Source(BaseModel):
    code: str               # 'myneta','sansad',...
    name: str
    url: str | None = None  # native_url for this specific fact
    trust_tier: int         # 1 official, 2 ADR/TCPD, 3 reported/news


class OfficeTerm(BaseModel):
    house: str              # 'Lok Sabha'
    cycle_number: int       # 18
    constituency: str | None
    state: str | None       # Rajya Sabha members represent a state
    party: str | None
    membership_type: str
    start_date: date | None
    end_date: date | None
    status: str
    source: Source
    attendance_pct: float | None = None         # cumulative parliamentary attendance %, PRS
    attendance_source: Source | None = None     # provenance for the attendance figure


class PartyStint(BaseModel):
    party: str
    joined_date: date | None
    left_date: date | None
    is_current: bool
    join_reason: str | None      # REPORTED narrative
    leave_reason: str | None     # REPORTED narrative
    reason_source: Source | None
    source: Source


class AffidavitWealth(BaseModel):
    election_cycle: str
    filed_year: int
    total_assets: int            # rupees
    total_liabilities: int
    movable_assets: int | None = None
    immovable_assets: int | None = None
    self_income: int | None = None
    source: Source


class ChargeSection(BaseModel):
    raw: str                     # the section as filed, e.g. 'IPC 302' or 'BNS 103'
    title: str | None = None     # offence name from the catalog, when the section is known
    equivalent: str | None = None  # the counterpart code+number, e.g. 'IPC 302' for BNS 103 (IPC↔BNS)


class CriminalCase(BaseModel):
    case_number: str | None
    court: str | None
    filed_year: int | None
    status: str                  # pending | convicted | acquitted | framed_charges
    is_convicted: bool
    severity: Severity | None    # heinous | serious | minor (derived)
    sections: list[ChargeSection]
    description: str | None
    source: Source


class Election(BaseModel):
    eci_election_id: str | None       # ties a past election to its term_cycle; None for upcoming
    name: str
    level: str                        # national | state | municipal
    status: str                       # past | upcoming
    election_date: date | None
    seats: int | None
    house: str | None                 # house whose winners are this election's results
    winner_count: int                 # winners we hold (0 for upcoming)
    note: str | None = None           # e.g. "Expected — not yet notified by ECI"


class Contact(BaseModel):
    channel_type: str            # email | phone | office_address | website | social | party_office
    value: str
    label: str | None
    source: Source


class RoleEntry(BaseModel):
    role_type: str               # prime_minister | minister | speaker | lop | committee_chair | ...
    title: str | None            # 'Minister of Finance', 'Speaker, Lok Sabha'
    body: str | None             # 'Union Council of Ministers', 'Lok Sabha'
    house: str | None            # house name, when the role is tied to one
    portfolio: str | None        # ministry/portfolio, when applicable
    start_date: date | None
    end_date: date | None
    status: str                  # current | former
    source: Source


class FirstOffice(BaseModel):
    """The earliest public office on record — a person's 'entered public life' anchor.

    Derived (not stored): the earliest-dated of the person's office_terms and leadership roles. It's only
    as deep as the sourced record reaches, so it's a floor ('at least since'), never a claim of the very
    first office ever held. Carries the provenance of whichever fact it was derived from."""

    year: int
    label: str                   # 'Member of Lok Sabha, Aligarh' / 'Chief Minister, Madhya Pradesh'
    kind: str                    # 'term' | 'role'
    source: Source


class PartySwitch(BaseModel):
    from_party: str | None
    to_party: str
    event_date: date | None
    narrative: str | None              # REPORTED reason, quoted from the public record
    source: Source | None


class ActivityMetric(BaseModel):
    value: int | None                  # this MP's cumulative count (None = not reported by PRS)
    house_median: float | None = None  # median across sitting members of the same house/term
    percentile: int | None = None      # 0..100: share of house peers this MP's count exceeds


class ParliamentaryActivity(BaseModel):
    """What an MP did in the House — counts with peer context, from PRS MP Track (CC-BY 4.0)."""

    house: str                         # 'Lok Sabha' | 'Rajya Sabha'
    questions: ActivityMetric
    debates: ActivityMetric
    private_member_bills: ActivityMetric
    period_start: date | None = None
    period_end: date | None = None     # data currency ("as of")
    source: Source


class ParliamentaryQuestion(BaseModel):
    id: int                            # row id — the web links the reply via /questions/{id}/document (proxy)
    subject: str | None = None
    ministry: str | None = None
    theme: str | None = None           # policy theme (from ministry_theme map); for grouping/filtering
    question_type: str | None = None   # 'Starred' | 'Unstarred'
    asked_date: date | None = None
    document_url: str | None = None    # official sansad.in question PDF (= the ministry's reply)


class ParliamentaryDebate(BaseModel):
    id: int                            # row id — the web links the doc via /debates/{id}/document (proxy)
    title: str | None = None
    debate_type: str | None = None
    debate_date: date | None = None
    document_url: str | None = None    # official sansad.in debate PDF (per sitting-day)


class ThemeFocus(BaseModel):
    """One policy theme's weight in an MP's questions, vs the House — the 'Policy focus' breakdown.

    Descriptive topical emphasis derived from the official ministry each question addressed (never a value
    judgment). `share` = this MP's fraction of questions in the theme; `house_share` = the same fraction
    pooled across all sitting members of the house (None until the house corpus is large enough to average).
    """

    theme: str
    count: int                         # this MP's questions in the theme
    share: float                       # count / this MP's total mapped questions (0..1)
    house_share: float | None = None   # pooled house fraction for the theme (0..1); None if house data thin


class ParliamentaryRecord(BaseModel):
    """Individual questions asked + debates joined — the content behind the activity counts.

    Enumerated from PRS MP Track profiles (CC-BY 4.0). `*_count` is the full total; the lists are capped
    (most-recent first) to bound payload — the UI shows "showing N of total".
    """

    house: str                         # 'Lok Sabha' | 'Rajya Sabha'
    questions_count: int
    debates_count: int
    questions: list[ParliamentaryQuestion]
    debates: list[ParliamentaryDebate]
    thematic_focus: list[ThemeFocus] = []   # 'Policy focus' — theme emphasis vs House, sorted by count desc
    source: Source                     # PRS provenance (per-item official doc links live on each row)


class PersonResume(BaseModel):
    id: int
    display_name: str
    native_name: str | None = None     # Devanagari (Hindi) name, where available
    photo_url: str | None = None
    age: int | None = None
    education: str | None = None
    relative_name: str | None = None   # S/o · D/o · W/o name from the ECI affidavit (identity signal)
    home_state: str | None = None      # modal state across the person's terms (context, esp. between terms)
    first_office: FirstOffice | None = None   # earliest sourced office (derived) — 'entered public life'
    office_terms: list[OfficeTerm]
    roles: list[RoleEntry] = []
    contacts: list[Contact] = []
    party_history: list[PartyStint]
    party_switches: list[PartySwitch] = []
    wealth: list[AffidavitWealth]      # ordered by filed_year for YoY
    criminal_cases: list[CriminalCase]
    activity: ParliamentaryActivity | None = None   # PRS scorecard: questions/debates/bills + peer context
    parliamentary_record: ParliamentaryRecord | None = None  # individual questions + debates (PRS profiles)


class VisitCount(BaseModel):
    count: int                         # lifetime unique-visitor tally


class Stats(BaseModel):
    total_legislators: int
    lok_sabha: int
    rajya_sabha: int
    with_cases: int                    # legislators with >= 1 declared criminal case
    crorepatis: int                    # legislators whose latest affidavit declares assets >= ₹1 crore


class PersonSummary(BaseModel):
    id: int
    display_name: str
    native_name: str | None = None
    photo_url: str | None = None
    current_party: str | None
    current_house: str | None
    constituency: str | None           # for RS this carries the represented state
    state: str | None = None           # the member's state (LS: constituency's state; RS: represented state)
    net_assets: int | None = None          # latest declared total assets (rupees)
    age: int | None = None                  # from the latest affidavit
    education: str | None = None            # highest qualification declared (latest affidavit)
    gender: str | None = None               # 'male' | 'female' | 'other' where declared
    pending_cases: int = 0                  # count of non-convicted cases
    total_cases: int = 0
    top_severity: Severity | None = None    # worst severity across cases (heinous>serious>minor)
    current_attendance_pct: float | None = None  # current-term parliamentary attendance %, PRS
    questions_count: int | None = None      # parliamentary questions asked (None = none on record)
    top_theme: str | None = None            # the policy area this MP raises most (from ministry_theme)


class FacetCount(BaseModel):
    value: str
    count: int


class Facets(BaseModel):
    """Dropdown option lists for a browse scope (party / state / house / theme), each with its row count."""

    parties: list[FacetCount] = []
    states: list[FacetCount] = []
    houses: list[FacetCount] = []
    themes: list[FacetCount] = []
    cycles: list[FacetCount] = []   # Lok Sabha sessions (cycle number + member count) — session selector


# --- "Parliament functioning" section — national/ministry aggregates over parliamentary_question --------
class ThemeCount(BaseModel):
    theme: str
    count: int


class MinistryCount(BaseModel):
    ministry: str
    theme: str
    count: int


class MpCount(BaseModel):
    id: int
    display_name: str
    photo_url: str | None = None
    count: int
    top_theme: str | None = None


class ParliamentStats(BaseModel):
    """Institutional-lens dashboard: what the House is asking (currently the 18th Lok Sabha)."""

    house: str
    total_questions: int
    total_debates: int
    active_mps: int                          # distinct members who asked >= 1 question
    themes: list[ThemeCount]                 # question distribution across policy themes
    top_ministries: list[MinistryCount]      # most-questioned ministries
    most_active: list[MpCount]               # top questioners


class RecordHit(BaseModel):
    """One topic-search hit — a question or debate matching the query (18th Lok Sabha)."""

    kind: Literal["question", "debate"]
    id: int                                  # row id — the doc link is built via /{kind}s/{id}/document
    title: str | None = None                 # question subject / debate title
    mp_id: int
    mp_name: str
    ministry: str | None = None              # questions only
    theme: str | None = None                 # policy theme (questions only)
    date: _Date | None = None                # asked_date / debate_date


class ThemeSeries(BaseModel):
    theme: str
    points: list[int]                        # one count per month, aligned to Trends.months


class Trends(BaseModel):
    """Monthly question volume split by policy theme (stacked-area trends over the term)."""

    house: str
    months: list[str]                        # dense 'YYYY-MM', oldest first
    totals: list[int]                        # total questions per month (sum across themes)
    series: list[ThemeSeries]                # per-theme monthly counts, ordered by total volume


class ThemeShare(BaseModel):
    theme: str
    count: int
    share: float                             # count / this group's total questions (0..1)


class AggregateGroup(BaseModel):
    """One party or state's collective question profile (18th Lok Sabha)."""

    key: str                                 # party canonical name / state
    total: int                               # total questions by this group's members
    mps: int                                 # members of this group who asked >= 1 question
    themes: list[ThemeShare]                 # theme emphasis (shares), ordered by count desc


class ThemeFocusBreakdown(BaseModel):
    """Descriptive theme-emphasis breakdown by party or state — what a group's members collectively raise.

    Topical emphasis derived from the official ministry each question addressed; a comparison of focus, never
    a value judgment or productivity ranking (same ethic as the per-MP 'Policy focus'). Missing ≠ zero.
    """

    by: Literal["party", "state"]
    house: str
    groups: list[AggregateGroup]             # ordered by total volume desc


class IndicatorPoint(BaseModel):
    year: int
    value: float


class IndicatorSeries(BaseModel):
    """One macro series (e.g. GDP) — full yearly history + the latest value, with provenance."""

    code: str                                # source-native series code, e.g. 'NY.GDP.MKTP.CD'
    name: str                                # the source's official series name
    unit: str                                # display unit label ('US$', '%', 'years', …)
    format: str                              # render hint: usd_compact | pct | number | count_compact | count_in
    polarity: int = 0                        # +1 higher-is-better, -1 lower-is-better, 0 neutral (change chip)
    note: str | None = None                  # optional caveat (e.g. the report + vintage a count came from)
    latest_value: float
    latest_year: int                         # ALWAYS show this next to the value — series lag differs
    points: list[IndicatorPoint]             # ascending by year; sparse series stay sparse (missing ≠ zero)
    source: Source


class IndicatorCategory(BaseModel):
    name: str                                # dashboard section ('Economy & Growth', …)
    indicators: list[IndicatorSeries]


class IndiaDashboard(BaseModel):
    """The India Dashboard aggregate — country-level macro indicators, grouped by category.

    Descriptive official statistics (World Bank Open Data, CC-BY 4.0, trust tier 1) — what the record
    says, never a judgment. Every series carries its own source link and its latest year (series lag
    differs: GDP is near-current, survey series like the Gini update only in survey years).
    """

    country: str                             # 'India'
    categories: list[IndicatorCategory]      # in curated display order
    total_indicators: int


# --- ECI Files: a sourced, dated record of the Election Commission of India (2019-today) -----------------
class EciPersonRef(BaseModel):
    slug: str
    name: str


class EciResponseRef(BaseModel):
    """One entry that answers another (`response_to` points back at the charge it responds to)."""

    id: str
    title: str
    date: _Date | None = None


class EciCitation(BaseModel):
    position: int
    url: str | None = None          # source_ref.native_url for this citation
    publisher: str | None = None
    title: str | None = None
    published: date | None = None
    tier: int                       # 1 official, 2 research/filing, 3 reported
    archive_url: str | None = None
    quote: str | None = None        # <= 200 chars, optional exact wording


class EciEntry(BaseModel):
    id: str
    area: str
    kind: str                       # event | person | rule | figure | case | statement
    date: _Date | None = None
    date_precision: str             # day | month | year
    title: str
    summary: str
    status: str                     # documented | reported | claim | response
    lane: str                       # responses | claims | courts | inside | commission
    attributed_to: str | None = None
    topics: list[str] = []
    states: list[str] = []
    figures: list[Any] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    check_status: str               # checked | unchecked
    people: list[EciPersonRef] = []
    response_to: str | None = None
    responses: list[EciResponseRef] = []   # entries whose response_to == this entry's id
    citations: list[EciCitation] = []


class EciEntryCompact(BaseModel):
    """`fields=compact` on `/eci-files/timeline` — just enough to draw a dot, no citations."""

    id: str
    date: _Date | None = None
    date_precision: str
    title: str
    status: str
    lane: str
    check_status: str
    people: list[EciPersonRef] = []


class EciTopicCount(BaseModel):
    topic: str
    count: int


class EciPersonCount(BaseModel):
    slug: str
    name: str
    count: int


class EciLaneCount(BaseModel):
    lane: str
    count: int


class EciStateCount(BaseModel):
    slug: str
    name: str
    count: int


class EciCheckCounts(BaseModel):
    checked: int
    unchecked: int


class EciTimeline(BaseModel):
    """The filtered ECI Files timeline — entries plus facets scoped to the same filter."""

    entries: list[EciEntry]
    topics: list[EciTopicCount]
    people: list[EciPersonCount]
    lanes: list[EciLaneCount]
    states: list[EciStateCount] = []
    counts: EciCheckCounts


class EciTimelineCompact(BaseModel):
    """The `fields=compact` shape of `/eci-files/timeline`: same facets, slimmer entries."""

    entries: list[EciEntryCompact]
    topics: list[EciTopicCount]
    people: list[EciPersonCount]
    lanes: list[EciLaneCount]
    states: list[EciStateCount] = []
    counts: EciCheckCounts


class EciHeadlineStat(BaseModel):
    value: str
    label: str
    source_label: str
    source_url: str
    entry_id: str


class EciSummaryCounts(BaseModel):
    entries: int
    checked: int
    people: int
    citations: int


class EciSummary(BaseModel):
    """`/eci-files/summary` — the front page's headline stats, key moments and record-wide counts."""

    headline: list[EciHeadlineStat]
    key_moments: list[EciEntry]
    counts: EciSummaryCounts
    last_loaded: datetime | None = None


class EciDensityMonth(BaseModel):
    month: str          # "2025-08"
    lane: str
    count: int


class EciDensity(BaseModel):
    """`/eci-files/density` — the overview strip's month x lane counts."""

    months: list[EciDensityMonth]


class EciPhoto(BaseModel):
    url: str
    source_page: str
    attribution: str
    licence: str
    licence_url: str
    licence_review: str             # reviewed | uploader_asserted
    original_publisher: str | None = None
    caption: str | None = None
    photo_date: date | None = None


class EciStatusCounts(BaseModel):
    documented: int = 0
    reported: int = 0
    claim: int = 0
    response: int = 0


class EciEntryRef(BaseModel):
    """A compact, labelled reference to an entry cited by a selection, regime or departure."""

    id: str
    title: str
    date: _Date | None = None
    date_precision: str
    status: str
    check_status: str | None = None   # NEW (phase 5), optional so phase 3/4 callers are unaffected


class EciPersonSummary(BaseModel):
    slug: str
    name: str
    group: str                      # commission | secretariat | state | named
    group_rank: int
    current: bool
    role: str | None = None         # profile entry's details.role
    service: str | None = None      # profile entry's details.service
    tenure: list[Any] = Field(default_factory=list)  # profile entry's details.tenure (office/from/to spans)
    first_from: date | None = None
    last_to: date | None = None
    entry_count: int
    status_counts: EciStatusCounts = Field(default_factory=EciStatusCounts)
    photo: EciPhoto | None = None


class EciSelectionAppointee(BaseModel):
    person_slug: str
    name: str
    office: str
    took_charge: date | None = None
    replaced: str | None = None
    photo: EciPhoto | None = None


class EciSelectionMember(BaseModel):
    person_slug: str | None = None
    name: str | None = None
    role: str
    part: str                       # recommended | proposed | voted_with_majority | dissented | search_chair
    has_profile: bool = False
    entry_ids: list[str]


class EciSelectionSearch(BaseModel):
    by: str
    chair_slug: str | None = None
    shortlist_size: int | None = None
    shortlist: list[str] | None = None
    shortlist_source: str | None = None
    entry_ids: list[str]


class EciSelectionDissent(BaseModel):
    person_slug: str
    name: str
    summary: str
    note_public: bool
    status: str
    entry_ids: list[str]
    response_entry_ids: list[str] = []


class EciSelection(BaseModel):
    id: str
    date: _Date
    date_precision: str
    date_meaning: str | None = None
    regime: str
    method: str                     # executive_appointment | elevation_of_senior_ec | selection_committee
    appointed: list[EciSelectionAppointee]
    members: list[EciSelectionMember]
    search: EciSelectionSearch | None = None
    dissent: list[EciSelectionDissent]
    entry_ids: list[str]
    notes: str | None = None


class EciSelectionRegime(BaseModel):
    key: str                        # convention | baranwal | act_2023
    label: str
    from_date: date | None = None
    to_date: date | None = None
    rule: str
    panel: list[str]
    entry_ids: list[str]
    notes: str | None = None
    selection_count: int


class EciDeparture(BaseModel):
    date: _Date
    person_slug: str
    name: str
    office: str
    how: str                        # resigned | tenure_ended
    notes: str | None = None
    entry_ids: list[str]


class EciSelections(BaseModel):
    """`/eci-files/selections` — every regime, every selection, every departure and a compact index
    of every entry any of them cites."""

    regimes: list[EciSelectionRegime]
    selections: list[EciSelection]
    departures: list[EciDeparture]
    entries_index: list[EciEntryRef]


class EciPersonDetail(BaseModel):
    slug: str
    name: str
    profile: EciEntry | None = None  # the kind='person' entry, if one was linked
    group: str
    current: bool
    role: str | None = None
    service: str | None = None
    tenure: list[Any] = Field(default_factory=list)
    status_counts: EciStatusCounts = Field(default_factory=EciStatusCounts)
    photo: EciPhoto | None = None


class EciPersonPage(BaseModel):
    person: EciPersonDetail
    entries: list[EciEntry]          # kind='person' excluded
    selections: list[EciSelection]   # as appointee, member or search chair
    entries_index: list[EciEntryRef]


class EciStageValue(BaseModel):
    stage: str                  # before | draft | final | appeals_filed | appeals_pending | restored
    electors: int
    as_of: date | None = None
    computed: bool
    approx: bool
    note: str | None = None
    source_entry_id: str
    source_entry_title: str     # eci_file_entry.title, joined
    source_status: str          # the source entry's status: documented | reported | claim | response
    url: str
    tier: int


class EciStateMetric(BaseModel):
    value: float                # percent, rounded to 2 dp; signed for net_change
    count: int                  # electors; signed for net_change
    base: int                   # the denominator, in electors
    computed: bool               # any contributing stage is computed
    approx: bool                 # any contributing stage is approx
    noted: bool                  # any contributing stage carries a note


class EciStateMetrics(BaseModel):
    draft_left_off: EciStateMetric | None = None
    net_change: EciStateMetric | None = None
    appeals_filed: EciStateMetric | None = None


class EciRegionSummary(BaseModel):
    slug: str
    name: str
    code: str
    kind: str                   # state | ut
    phase: int | None = None
    exercise: str | None = None  # sir | special_revision | None (not in any exercise on record)
    has_figures: bool           # at least one stage
    entry_count: int            # entries whose states include this region (kind <> 'person')
    stages: list[EciStageValue] = []   # canonical order: before, draft, final, appeals_filed, appeals_pending, restored
    metrics: EciStateMetrics


class EciNationalFigure(BaseModel):
    group: str                  # all | phase_1 | phase_2 | phase_3
    measure: str                # before | draft | final | left_off | net_fall
    label: str
    scope: str
    electors: int
    as_of: date | None = None
    computed: bool
    approx: bool
    note: str | None = None
    source_entry_id: str
    source_entry_title: str
    source_status: str


class EciStatesOverview(BaseModel):
    regions: list[EciRegionSummary]
    national: list[EciNationalFigure]
    last_as_of: date | None = None   # max(as_of) over every stage


class EciStatePage(BaseModel):
    region: EciRegionSummary
    notes: str | None = None


# --- ECI Files phase 5 ------------------------------------------------------------------------------


class EciEntryCard(BaseModel):
    """Enough for a row or cell on the phase 5 pages; the drawer fetches the full entry."""

    id: str
    kind: str
    date: _Date | None = None
    date_precision: str
    title: str
    summary: str
    status: str
    lane: str
    attributed_to: str | None = None
    check_status: str
    people: list[EciPersonRef] = []
    citation_count: int
    lead_citation: EciCitation | None = None   # position 1


class EciPersonWithPhoto(BaseModel):
    slug: str
    name: str
    photo: EciPhoto | None = None


class EciObjection(BaseModel):
    n: int
    date: _Date | None = None
    date_precision: str
    by: list[EciPersonWithPhoto]
    concerns: str
    followed_by: str | None = None
    followed_by_refs: list[EciEntryRef] = []
    public: bool
    entries: list[EciEntryRef]


class EciObjectionPersonCount(BaseModel):
    slug: str
    name: str
    photo: EciPhoto | None = None
    count: int
    joint: int


class EciObjectionsPage(BaseModel):
    identified: int
    missing: int
    reported_total: int
    notes: str | None = None
    report: EciEntryRef | None = None
    response: EciEntryCard | None = None
    objections: list[EciObjection]
    by_person: list[EciObjectionPersonCount]


class EciRelatedRef(BaseModel):
    entry: EciEntryRef
    why: str


class EciAnswerRow(BaseModel):
    charge: EciEntryCard
    also_recorded_as: list[EciEntryRef] = []
    responses: list[EciEntryCard] = []
    record: list[EciEntryCard] = []
    related: list[EciRelatedRef] = []
    note: str | None = None
    curated: bool


class EciAnswersCounts(BaseModel):
    rows: int
    with_response: int
    without_response: int
    with_record: int


class EciUnpairedResponse(BaseModel):
    response: EciEntryCard
    note: str | None = None


class EciAnswersPage(BaseModel):
    counts: EciAnswersCounts
    rows: list[EciAnswerRow]
    unpaired_responses: list[EciUnpairedResponse]


class EciRuleDiffRef(BaseModel):
    id: str
    title: str
    text_status: str


class EciRuleRow(BaseModel):
    entry: EciEntryCard
    diffs: list[EciRuleDiffRef] = []


class EciRulesPage(BaseModel):
    rules: list[EciRuleRow]
    diffs: list[EciRuleDiffRef]
    counts: dict[str, int]


class EciRuleDiff(BaseModel):
    id: str
    title: str
    document: str
    rule_entry: EciEntryCard
    before_label: str
    after_label: str
    before: list[str]
    after: list[str]
    before_status: str
    after_status: str
    text_status: str
    excerpt: bool
    quoted_lines_before: list[int] = []
    quoted_lines_after: list[int] = []
    source_urls: list[str]
    note: str | None = None
    related: list[EciEntryRef] = []


class EciCaseSummary(BaseModel):
    slug: str
    short_name: str
    title: str
    case_number: str | None = None
    court: str
    short_status: str
    status_note: str | None = None
    item_count: int
    order_count: int
    first_date: _Date | None = None
    last_date: _Date | None = None
    latest: EciEntryRef | None = None


class EciCourtsPage(BaseModel):
    cases: list[EciCaseSummary]
    other_court_entries: int


class EciCaseItem(BaseModel):
    role: str
    note: str | None = None
    entry: EciEntryCard


class EciCasePage(BaseModel):
    slug: str
    short_name: str
    court: str
    short_status: str
    status_note: str | None = None
    case: EciEntry
    case_name: str
    case_number: str | None = None
    bench: str | None = None
    citation: str | None = None
    parties: dict[str, list[str]]
    items: list[EciCaseItem]


class EciPairContext(BaseModel):
    charge: EciEntryRef
    role: str
    responses: list[EciEntryRef] = []
    record: list[EciEntryRef] = []
    note: str | None = None


class EciEntryContext(BaseModel):
    pairs: list[EciPairContext] = []
    case: dict[str, Any] | None = None
    objections: list[dict[str, Any]] = []
    rule_diffs: list[EciRuleDiffRef] = []


class EciEntryDetail(EciEntry):
    context: EciEntryContext = EciEntryContext()
