"""/eci-files routes — a sourced, dated record of the Election Commission of India (2019-today).

Launch is gated: the pages are unlinked/noindex on the website until the owner approves, but the API itself
has no gate — it's read-only and inert until the web layer links to it. See docs/eci-files/SPEC.md section 6.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import (
    EciAnswersPage,
    EciCasePage,
    EciCourtsPage,
    EciDensity,
    EciEntryDetail,
    EciObjectionsPage,
    EciPersonPage,
    EciPersonSummary,
    EciRuleDiff,
    EciRulesPage,
    EciSelections,
    EciStatePage,
    EciStatesOverview,
    EciSummary,
    EciTimeline,
    EciTimelineCompact,
)
from neta_api.services import eci_files as eci_files_service

router = APIRouter(prefix="/eci-files", tags=["eci-files"])


@router.get("/summary", response_model=EciSummary)
def summary(db: Session = Depends(get_db)) -> EciSummary:
    """The front page: the four headline stats, ~8 key moments, and record-wide counts."""
    return EciSummary(**eci_files_service.summary(db))


@router.get("/timeline", response_model=EciTimeline | EciTimelineCompact)
def timeline(
    topic: str | None = None,
    person: str | None = None,
    status: str | None = None,
    lane: str | None = None,
    from_: date | None = Query(None, alias="from"),
    to: date | None = None,
    state: str | None = None,
    fields: str | None = None,
    db: Session = Depends(get_db),
) -> EciTimeline | EciTimelineCompact:
    """Entries matching the filter (date ascending, then id), plus topic/people/lane/state facets and
    checked/unchecked counts scoped to that same filtered set. `fields=compact` returns just enough
    per entry to draw the lane timeline's dots (no citations). An unknown `state` slug returns an empty
    `entries` list, the same as an unknown `person`."""
    result = eci_files_service.timeline(
        db,
        topic=topic,
        person=person,
        status=status,
        lane=lane,
        date_from=from_,
        date_to=to,
        state=state,
        fields=fields,
    )
    if fields == "compact":
        return EciTimelineCompact(**result)
    return EciTimeline(**result)


@router.get("/states", response_model=EciStatesOverview)
def states_overview(db: Session = Depends(get_db)) -> EciStatesOverview:
    """All 36 States/UTs, sorted by name, with the national SIR figures."""
    return EciStatesOverview(**eci_files_service.states_overview(db))


@router.get("/states/{slug}", response_model=EciStatePage)
def state_page(slug: str, db: Session = Depends(get_db)) -> EciStatePage:
    """One State/UT's summary and notes. The web fetches its entries separately, through the
    timeline's `state=` filter."""
    result = eci_files_service.state_page(db, slug)
    if result is None:
        raise HTTPException(status_code=404, detail="state not found")
    return EciStatePage(**result)


@router.get("/density", response_model=EciDensity)
def density(db: Session = Depends(get_db)) -> EciDensity:
    """Month x lane counts across the whole record, for the timeline overview strip."""
    return EciDensity(**eci_files_service.density(db))


@router.get("/people", response_model=list[EciPersonSummary])
def people(db: Session = Depends(get_db)) -> list[EciPersonSummary]:
    """Every person on record, with role/tenure from their profile entry and a linked-entry count."""
    return [EciPersonSummary(**p) for p in eci_files_service.people(db)]


@router.get("/people/{slug}", response_model=EciPersonPage)
def person_page(slug: str, db: Session = Depends(get_db)) -> EciPersonPage:
    """One person's profile (if linked) plus their full timeline."""
    result = eci_files_service.person_page(db, slug)
    if result is None:
        raise HTTPException(status_code=404, detail="person not found")
    return EciPersonPage(**result)


@router.get("/selections", response_model=EciSelections)
def selections(db: Session = Depends(get_db)) -> EciSelections:
    """Every selection regime, every selection (newest first), every departure, and a compact index
    of every entry any of them cites."""
    return EciSelections(**eci_files_service.selections(db))


@router.get("/objections", response_model=EciObjectionsPage)
def objections(db: Session = Depends(get_db)) -> EciObjectionsPage:
    """The fourteen: the 11 identified objections, the Indian Express report and the Commission's
    response, and a per-person count."""
    return EciObjectionsPage(**eci_files_service.objections(db))


@router.get("/answers", response_model=EciAnswersPage)
def answers(
    view: str = Query("all", pattern="^(all|no-response|with-record)$"),
    db: Session = Depends(get_db),
) -> EciAnswersPage:
    """Every charge or Commission action beside its response (charge date descending, then id).
    `counts` is always computed on the full set, whatever `view` filters the rows to."""
    return EciAnswersPage(**eci_files_service.answers(db, view=view))


@router.get("/rules", response_model=EciRulesPage)
def rules(db: Session = Depends(get_db)) -> EciRulesPage:
    """Every `kind='rule'` entry (date descending, then id) plus the before-and-after diffs."""
    return EciRulesPage(**eci_files_service.rules(db))


@router.get("/rules/diffs/{diff_id}", response_model=EciRuleDiff)
def rule_diff(diff_id: str, db: Session = Depends(get_db)) -> EciRuleDiff:
    result = eci_files_service.rule_diff(db, diff_id)
    if result is None:
        raise HTTPException(status_code=404, detail="rule diff not found")
    return EciRuleDiff(**result)


@router.get("/courts", response_model=EciCourtsPage)
def courts(db: Session = Depends(get_db)) -> EciCourtsPage:
    """The five court cases, file order, with their step counts and latest recorded step."""
    return EciCourtsPage(**eci_files_service.courts(db))


@router.get("/courts/{slug}", response_model=EciCasePage)
def case_page(slug: str, db: Session = Depends(get_db)) -> EciCasePage:
    """One case, order by order (entry date ascending, then id)."""
    result = eci_files_service.case_page(db, slug)
    if result is None:
        raise HTTPException(status_code=404, detail="case not found")
    return EciCasePage(**result)


@router.get("/entries/{entry_id}", response_model=EciEntryDetail)
def get_entry(entry_id: str, db: Session = Depends(get_db)) -> EciEntryDetail:
    result = eci_files_service.entry_detail(db, entry_id)
    if result is None:
        raise HTTPException(status_code=404, detail="entry not found")
    return EciEntryDetail(**result)
