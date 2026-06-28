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


class CriminalCase(BaseModel):
    case_number: str | None
    court: str | None
    filed_year: int | None
    status: str                  # pending | convicted | acquitted | framed_charges
    is_convicted: bool
    severity: Severity | None    # heinous | serious | minor (derived)
    sections: list[str]          # ['IPC 302', 'BNS 103']
    description: str | None
    source: Source


class PartySwitch(BaseModel):
    from_party: str | None
    to_party: str
    event_date: date | None
    narrative: str | None              # REPORTED reason, quoted from the public record
    source: Source | None


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
    party_history: list[PartyStint]
    party_switches: list[PartySwitch] = []
    wealth: list[AffidavitWealth]      # ordered by filed_year for YoY
    criminal_cases: list[CriminalCase]
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
