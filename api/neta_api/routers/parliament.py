"""/parliament routes — the "Parliament functioning" section: national + ministry aggregates."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import MinistryCount, ParliamentStats, RecordHit, Trends
from neta_api.services import parliament as parliament_service

router = APIRouter(prefix="/parliament", tags=["parliament"])

# Which house the section is scoped to. 'ls' (18th Lok Sabha) or 'rs' (current Rajya Sabha); default LS.
_HOUSE_Q = Query("ls", pattern="^(ls|rs)$")


@router.get("/stats", response_model=ParliamentStats)
def parliament_stats(house: str = _HOUSE_Q, db: Session = Depends(get_db)) -> ParliamentStats:
    """National dashboard: totals + theme mix + top ministries + most-active MPs, for the given house."""
    return ParliamentStats(**parliament_service.parliament_stats(db, house=house.upper()))


@router.get("/ministries", response_model=list[MinistryCount])
def parliament_ministries(house: str = _HOUSE_Q, db: Session = Depends(get_db)) -> list[MinistryCount]:
    """The full ranked list of ministries by question count, for the given house."""
    return [MinistryCount(**m) for m in parliament_service.ministries(db, house=house.upper())]


@router.get("/search", response_model=list[RecordHit])
def parliament_search(
    response: Response,
    q: str = Query(min_length=2),
    kind: str | None = Query(default=None, pattern="^(question|debate)$"),
    theme: str | None = None,
    limit: int = 30,
    offset: int = 0,
    house: str = _HOUSE_Q,
    db: Session = Depends(get_db),
) -> list[RecordHit]:
    """Topic search over question subjects + debate titles for the given house. Filter by kind/theme, page via
    limit/offset; the total match count is in the `X-Total-Count` header (body stays a plain list)."""
    items, total = parliament_service.search_records(
        db, q=q, kind=kind, theme=theme, limit=limit, offset=offset, house=house.upper(),
    )
    response.headers["X-Total-Count"] = str(total)
    return [RecordHit(**it) for it in items]


@router.get("/trends", response_model=Trends)
def parliament_trends(house: str = _HOUSE_Q, db: Session = Depends(get_db)) -> Trends:
    """Monthly question volume split by policy theme, for the given house — the stacked-area trends view."""
    return Trends(**parliament_service.trends(db, house=house.upper()))
