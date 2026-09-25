"""/eci-files routes — a sourced, dated record of the Election Commission of India (2019-today).

Launch is gated: the pages are unlinked/noindex on the website until the owner approves, but the API itself
has no gate — it's read-only and inert until the web layer links to it. See docs/eci-files/SPEC.md section 6.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import EciEntry, EciPersonPage, EciPersonSummary, EciTimeline
from neta_api.services import eci_files as eci_files_service

router = APIRouter(prefix="/eci-files", tags=["eci-files"])


@router.get("/timeline", response_model=EciTimeline)
def timeline(
    topic: str | None = None,
    person: str | None = None,
    status: str | None = None,
    from_: date | None = Query(None, alias="from"),
    to: date | None = None,
    db: Session = Depends(get_db),
) -> EciTimeline:
    """Entries matching the filter (date ascending, then id), plus topic/people facets and checked/unchecked
    counts scoped to that same filtered set."""
    return EciTimeline(
        **eci_files_service.timeline(
            db, topic=topic, person=person, status=status, date_from=from_, date_to=to
        )
    )


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
