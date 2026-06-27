"""Public API contract (Pydantic). The frontend codegens TypeScript from the OpenAPI this produces.

Every fact-bearing model carries a `source` (provenance) so the UI can render a link on each datapoint.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Source(BaseModel):
    code: str               # 'myneta','sansad',...
    name: str
    url: str | None = None  # native_url for this specific fact
    trust_tier: int         # 1 official, 2 ADR/TCPD, 3 reported/news


class OfficeTerm(BaseModel):
    house: str              # 'Lok Sabha'
    cycle_number: int       # 18
    constituency: str | None
    party: str | None
    membership_type: str
    start_date: date | None
    end_date: date | None
    status: str
    source: Source


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
    self_income: int | None
    source: Source


class CriminalCase(BaseModel):
    case_number: str | None
    court: str | None
    filed_year: int | None
    status: str                  # pending | convicted | acquitted | framed_charges
    is_convicted: bool
    severity: str | None         # heinous | serious | minor (derived)
    sections: list[str]          # ['IPC 302', 'BNS 103']
    description: str | None
    source: Source


class PersonResume(BaseModel):
    id: int
    display_name: str
    office_terms: list[OfficeTerm]
    party_history: list[PartyStint]
    wealth: list[AffidavitWealth]      # ordered by filed_year for YoY
    criminal_cases: list[CriminalCase]


class PersonSummary(BaseModel):
    id: int
    display_name: str
    current_party: str | None
    current_house: str | None
    constituency: str | None
