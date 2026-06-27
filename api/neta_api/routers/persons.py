"""/persons routes — the resume aggregate that drives the frontend person page.

The heavy join (person + terms + party history + N affidavit cycles + cases + sources) lives in
neta_api.services.resume so the route stays thin and every emitted fact carries its source.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import PersonResume
from neta_api.services import resume as resume_service

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("/{person_id}", response_model=PersonResume)
def get_person(person_id: int, db: Session = Depends(get_db)) -> PersonResume:
    """Full resume for one legislator."""
    result = resume_service.build_resume(db, person_id)
    if result is None:
        raise HTTPException(status_code=404, detail="person not found")
    return result
