"""/aggregate routes — collective lenses over the parliamentary record (party / state).

Descriptive theme-emphasis breakdowns, sourced from the official ministry each question addressed; a
comparison of focus, never a value judgment. Read-time aggregate; cached by the web's 1-hour ISR. The
namespace is built to grow (wealth/cases by group later).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import ThemeFocusBreakdown
from neta_api.services import parliament as parliament_service

router = APIRouter(prefix="/aggregate", tags=["aggregate"])


@router.get("/theme-focus", response_model=ThemeFocusBreakdown)
def theme_focus(
    by: str = Query(pattern="^(party|state)$"),
    house: str | None = None,
    db: Session = Depends(get_db),
) -> ThemeFocusBreakdown:
    """Theme-emphasis mix per party or state (18th Lok Sabha): each group's policy-theme shares + volume."""
    return ThemeFocusBreakdown(**parliament_service.theme_focus_by(db, by=by, house=house))
