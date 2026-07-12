"""/indicators routes — the India Dashboard (country-level macro indicators).

Official statistics about the country itself (GDP, prices, health, education, …), not about any
legislator — the "understand the data your government puts out" counterpart to the per-MP record.
v1 source: World Bank Open Data (keyless API, CC-BY 4.0, trust tier 1), refreshed monthly by
`neta macro-indicators`. Descriptive, sourced, missing ≠ zero — same ethic as everything else.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import IndiaDashboard
from neta_api.services import indicators as indicators_service

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/india", response_model=IndiaDashboard)
def india(db: Session = Depends(get_db)) -> IndiaDashboard:
    """The full India Dashboard: every catalogued macro series (history + latest), grouped by category."""
    return IndiaDashboard(**indicators_service.india_dashboard(db))
