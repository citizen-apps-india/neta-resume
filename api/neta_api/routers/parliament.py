"""/parliament routes — the "Parliament functioning" section: national + ministry aggregates."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import MinistryCount, ParliamentStats
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
