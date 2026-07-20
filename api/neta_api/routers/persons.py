"""/persons routes — the resume aggregate that drives the frontend person page.

The heavy join (person + terms + party history + N affidavit cycles + cases + sources) lives in
neta_api.services.resume so the route stays thin and every emitted fact carries its source.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import Facets, PersonResume, PersonSummary
from neta_api.services import resume as resume_service

router = APIRouter(prefix="/persons", tags=["persons"])

# Photos are proxied (not hot-linked): the upstream (sansad.in) sets Cross-Origin-Resource-Policy:
# same-site, so a browser refuses to embed them from our origin. We fetch server-side (CORP is a
# browser policy, not enforced here) and disk-cache so each photo hits the source at most once.
_PHOTO_CACHE = Path(__file__).resolve().parents[2] / ".photo_cache"

# SSRF guard: the proxy fetches a URL read from the DB, so restrict it to https on the only host
# photos are ever sourced from (sansad.in). This blocks file://, internal hosts, and other schemes
# even if a bad URL ever reached the person table. Size is capped to avoid memory-exhaustion fetches.
_ALLOWED_PHOTO_HOSTS = ("sansad.in", "myneta.info")
_MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB


def _is_allowed_photo_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and any(
        host == h or host.endswith("." + h) for h in _ALLOWED_PHOTO_HOSTS
    )


@router.get("/{person_id}/photo")
def person_photo(person_id: int, db: Session = Depends(get_db)) -> Response:
    url = db.execute(text("SELECT photo_url FROM person WHERE id = :id"), {"id": person_id}).scalar()
    if not url:
        raise HTTPException(status_code=404, detail="no photo")
    if not _is_allowed_photo_url(url):
        raise HTTPException(status_code=400, detail="unsupported photo source")
    _PHOTO_CACHE.mkdir(exist_ok=True)
    cached = _PHOTO_CACHE / f"{person_id}.jpg"
    if not cached.exists():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "neta-resume/0.1"})
            with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310 (scheme validated above)
                if (clen := r.headers.get("Content-Length")) and int(clen) > _MAX_PHOTO_BYTES:
                    raise HTTPException(status_code=502, detail="photo too large")
                data = r.read(_MAX_PHOTO_BYTES + 1)
            if len(data) > _MAX_PHOTO_BYTES:
                raise HTTPException(status_code=502, detail="photo too large")
            cached.write_bytes(data)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail="photo fetch failed") from exc
    return Response(
        content=cached.read_bytes(),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=604800", "Cross-Origin-Resource-Policy": "cross-origin"},
    )


@router.get("", response_model=list[PersonSummary])
def list_persons(
    response: Response,
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
    house: str | None = None,
    state: str | None = None,
    constituency: str | None = None,
    jurisdiction: str | None = None,
    party: str | None = None,
    cases: str | None = None,
    q: str | None = None,
    theme: str | None = None,
    cycle: int | None = None,
    sort: str = "assets",
    db: Session = Depends(get_db),
) -> list[PersonSummary]:
    """Browse legislators (directory): filter by house/state/constituency/jurisdiction/party/cases/theme/
    search, sort by assets|cases|attendance|theme_questions|name, and page via limit/offset. `cycle` (a Lok
    Sabha cycle number) browses that session's roster as it stood at the time. Total match count is returned
    in the `X-Total-Count` response header (the body stays a plain list)."""
    items, total = resume_service.list_persons(
        db, limit=limit, offset=offset, house=house, state=state, constituency=constituency,
        jurisdiction=jurisdiction, party=party, cases=cases, q=q, theme=theme, cycle=cycle, sort=sort,
    )
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get("/facets", response_model=Facets)
def person_facets(
    house: str | None = None,
    state: str | None = None,
    jurisdiction: str | None = None,
    cycle: int | None = None,
    db: Session = Depends(get_db),
) -> Facets:
    """Dropdown option lists (party / state / house / LS session, each with a count) for a browse scope."""
    return resume_service.facets(db, house=house, state=state, jurisdiction=jurisdiction, cycle=cycle)


@router.get("/{person_id}", response_model=PersonResume)
def get_person(person_id: int, db: Session = Depends(get_db)) -> PersonResume:
    """Full resume for one legislator."""
    result = resume_service.build_resume(db, person_id)
    if result is None:
        raise HTTPException(status_code=404, detail="person not found")
    return result
