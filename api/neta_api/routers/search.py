"""/search routes — name / constituency / party lookup (pg_trgm-backed)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import PersonSummary
from neta_api.services import resume as resume_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[PersonSummary])
def search(q: str = Query(min_length=2), db: Session = Depends(get_db)) -> list[PersonSummary]:
    """Fuzzy search legislators by name (uses person.normalized_name trigram index)."""
    return resume_service.search_persons(db, q)
