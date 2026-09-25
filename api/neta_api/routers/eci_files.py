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
    EciDensity,
    EciEntry,
    EciPersonPage,
    EciPersonSummary,
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
    fields: str | None = None,
    db: Session = Depends(get_db),
) -> EciTimeline | EciTimelineCompact:
    """Entries matching the filter (date ascending, then id), plus topic/people/lane facets and
    checked/unchecked counts scoped to that same filtered set. `fields=compact` returns just enough
    per entry to draw the lane timeline's dots (no citations)."""
    result = eci_files_service.timeline(
        db, topic=topic, person=person, status=status, lane=lane, date_from=from_, date_to=to, fields=fields
    )
    if fields == "compact":
        return EciTimelineCompact(**result)
    return EciTimeline(**result)


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


@router.get("/entries/{entry_id}", response_model=EciEntry)
def get_entry(entry_id: str, db: Session = Depends(get_db)) -> EciEntry:
    result = eci_files_service.entry(db, entry_id)
    if result is None:
        raise HTTPException(status_code=404, detail="entry not found")
    return EciEntry(**result)
