"""/visits routes — the homepage lifetime unique-visitor counter.

The web layer decides *when* a visitor is new (a first-visit cookie set in Next middleware) and calls
POST /visits/hit exactly once per new browser; GET /visits just reads the running total for display.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import VisitCount

router = APIRouter(prefix="/visits", tags=["visits"])

_KEY = "unique_visitors"


@router.get("", response_model=VisitCount)
def get_visits(db: Session = Depends(get_db)) -> VisitCount:
    """Current lifetime unique-visitor count (no increment)."""
    n = db.execute(text("SELECT count FROM site_counter WHERE key = :k"), {"k": _KEY}).scalar()
    return VisitCount(count=int(n or 0))


@router.post("/hit", response_model=VisitCount)
def hit(db: Session = Depends(get_db)) -> VisitCount:
    """Atomically increment the unique-visitor count and return the new total."""
    n = db.execute(
        text(
            """
            INSERT INTO site_counter (key, count) VALUES (:k, 1)
            ON CONFLICT (key) DO UPDATE SET count = site_counter.count + 1
            RETURNING count
            """
        ),
        {"k": _KEY},
    ).scalar()
    db.commit()
    return VisitCount(count=int(n or 0))
