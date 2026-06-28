"""/elections route — the election registry (past with results + upcoming), for the Elections module."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import Election

router = APIRouter(prefix="/elections", tags=["elections"])


@router.get("", response_model=list[Election])
def list_elections(db: Session = Depends(get_db)) -> list[Election]:
    """All registered elections. Past entries carry a winner_count + house (results reuse /persons?house=…)."""
    rows = db.execute(
        text(
            """
            SELECT e.eci_election_id, e.name, e.level, e.status, e.election_date, e.seats, e.note,
                   h.name AS house,
                   COALESCE((
                       SELECT count(*) FROM office_term ot
                       JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                       WHERE tc.eci_election_id = e.eci_election_id
                   ), 0) AS winner_count
            FROM election e
            LEFT JOIN house h ON h.code = e.house_code
            ORDER BY (e.status = 'upcoming') DESC,
                     CASE WHEN e.status = 'upcoming' THEN e.election_date END ASC,
                     CASE WHEN e.status = 'past' THEN e.election_date END DESC
            """
        )
    )
    return [
        Election(
            eci_election_id=r.eci_election_id,
            name=r.name,
            level=r.level,
            status=r.status,
            election_date=r.election_date,
            seats=r.seats,
            house=r.house,
            winner_count=r.winner_count,
            note=r.note,
        )
        for r in rows
    ]
