"""/persons routes — the resume aggregate that drives the frontend person page.

The heavy join (person + terms + party history + N affidavit cycles + cases + sources) lives in
neta_api.services.resume so the route stays thin and every emitted fact carries its source.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import PersonResume, PersonSummary
from neta_api.services import resume as resume_service

router = APIRouter(prefix="/persons", tags=["persons"])

# Photos are proxied (not hot-linked): the upstream (sansad.in) sets Cross-Origin-Resource-Policy:
# same-site, so a browser refuses to embed them from our origin. We fetch server-side (CORP is a
# browser policy, not enforced here) and disk-cache so each photo hits the source at most once.
_PHOTO_CACHE = Path(__file__).resolve().parents[2] / ".photo_cache"


@router.get("/{person_id}/photo")
def person_photo(person_id: int, db: Session = Depends(get_db)) -> Response:
    url = db.execute(text("SELECT photo_url FROM person WHERE id = :id"), {"id": person_id}).scalar()
    if not url:
        raise HTTPException(status_code=404, detail="no photo")
    _PHOTO_CACHE.mkdir(exist_ok=True)
    cached = _PHOTO_CACHE / f"{person_id}.jpg"
    if not cached.exists():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "neta-resume/0.1"})
            with urllib.request.urlopen(req, timeout=20) as r:
                cached.write_bytes(r.read())
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail="photo fetch failed") from exc
    return Response(
        content=cached.read_bytes(),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=604800", "Cross-Origin-Resource-Policy": "cross-origin"},
    )


@router.get("", response_model=list[PersonSummary])
def list_persons(
    limit: int = 60,
    offset: int = 0,
    house: str | None = None,
    db: Session = Depends(get_db),
) -> list[PersonSummary]:
    """Browse legislators (directory). Optionally filter by house. Ordered by declared assets desc."""
    return resume_service.list_persons(db, limit=limit, offset=offset, house=house)


@router.get("/{person_id}", response_model=PersonResume)
def get_person(person_id: int, db: Session = Depends(get_db)) -> PersonResume:
    """Full resume for one legislator."""
    result = resume_service.build_resume(db, person_id)
    if result is None:
        raise HTTPException(status_code=404, detail="person not found")
    return result
