"""/parliament routes — the "Parliament functioning" section: national + ministry aggregates."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import MinistryCount, ParliamentStats, RecordHit, Trends
from neta_api.services import parliament as parliament_service

router = APIRouter(prefix="/parliament", tags=["parliament"])


@router.get("/stats", response_model=ParliamentStats)
def parliament_stats(db: Session = Depends(get_db)) -> ParliamentStats:
    """National dashboard: totals + theme mix + top ministries + most-active MPs (18th Lok Sabha)."""
    return ParliamentStats(**parliament_service.parliament_stats(db))


@router.get("/ministries", response_model=list[MinistryCount])
def parliament_ministries(db: Session = Depends(get_db)) -> list[MinistryCount]:
    """The full ranked list of ministries by question count."""
    return [MinistryCount(**m) for m in parliament_service.ministries(db)]


@router.get("/search", response_model=list[RecordHit])
def parliament_search(
    response: Response,
    q: str = Query(min_length=2),
    kind: str | None = Query(default=None, pattern="^(question|debate)$"),
    theme: str | None = None,
    limit: int = 30,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[RecordHit]:
    """Topic search over question subjects + debate titles (18th Lok Sabha). Filter by kind/theme, page via
    limit/offset; the total match count is in the `X-Total-Count` header (body stays a plain list)."""
    items, total = parliament_service.search_records(
        db, q=q, kind=kind, theme=theme, limit=limit, offset=offset,
    )
    response.headers["X-Total-Count"] = str(total)
    return [RecordHit(**it) for it in items]


@router.get("/trends", response_model=Trends)
def parliament_trends(db: Session = Depends(get_db)) -> Trends:
    """Monthly question volume split by policy theme (18th Lok Sabha) — the stacked-area trends view."""
    return Trends(**parliament_service.trends(db))
