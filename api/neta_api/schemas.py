"""Public API contract (Pydantic). The frontend codegens TypeScript from the OpenAPI this produces.

Every fact-bearing model carries a `source` (provenance) so the UI can render a link on each datapoint.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

Severity = Literal["heinous", "serious", "minor"]


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
    office_terms: list[OfficeTerm]
    roles: list[RoleEntry] = []
    contacts: list[Contact] = []
    party_history: list[PartyStint]
    party_switches: list[PartySwitch] = []
    wealth: list[AffidavitWealth]      # ordered by filed_year for YoY
    criminal_cases: list[CriminalCase]
    activity: ParliamentaryActivity | None = None   # PRS scorecard: questions/debates/bills + peer context
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
    pending_cases: int = 0                  # count of non-convicted cases
    total_cases: int = 0
    top_severity: Severity | None = None    # worst severity across cases (heinous>serious>minor)
    current_attendance_pct: float | None = None  # current-term parliamentary attendance %, PRS


class FacetCount(BaseModel):
    value: str
    count: int


class Facets(BaseModel):
    """Dropdown option lists for a browse scope (party / state / house), each with its row count."""

    parties: list[FacetCount] = []
    states: list[FacetCount] = []
    houses: list[FacetCount] = []
