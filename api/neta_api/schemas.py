"""Public API contract (Pydantic). The frontend codegens TypeScript from the OpenAPI this produces.

Every fact-bearing model carries a `source` (provenance) so the UI can render a link on each datapoint.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

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


class NewsItem(BaseModel):
    title: str
    snippet: str | None = None
    url: str
    publisher: str | None = None
    published_at: date | None = None
    source: Source                     # trust_tier 3 (reported); links to the publisher


class PersonResume(BaseModel):
    id: int
    display_name: str
    native_name: str | None = None     # Devanagari (Hindi) name, where available
    photo_url: str | None = None
    age: int | None = None
    education: str | None = None
    relative_name: str | None = None   # S/o · D/o · W/o name from the ECI affidavit (identity signal)
    home_state: str | None = None      # modal state across the person's terms (context, esp. between terms)
    office_terms: list[OfficeTerm]
    roles: list[RoleEntry] = []
    contacts: list[Contact] = []
    party_history: list[PartyStint]
    party_switches: list[PartySwitch] = []
    wealth: list[AffidavitWealth]      # ordered by filed_year for YoY
    criminal_cases: list[CriminalCase]
    activity: ParliamentaryActivity | None = None   # PRS scorecard: questions/debates/bills + peer context
    parliamentary_record: ParliamentaryRecord | None = None  # individual questions + debates (PRS profiles)
    news: list[NewsItem] = []          # recent press coverage (Google News), newest first


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
    format: str                              # render hint: usd_compact | pct | number | count_compact
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
