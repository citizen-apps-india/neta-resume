"""/stats route — headline counts for the homepage."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import Stats
from neta_api.services import resume as resume_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=Stats)
def get_stats(db: Session = Depends(get_db)) -> Stats:
    """Real counts (total / per house / with cases / crorepatis) — not capped by any list limit."""
    return Stats(**resume_service.stats(db))
