"""Resume assembly + search queries (read-only).

build_resume does the aggregate join and maps rows -> schemas, attaching a Source to every fact.
Implementation lands in Phase 1 alongside the first ingested MP; signatures are fixed here so the
router + frontend contract are stable.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from neta_api.schemas import PersonResume, PersonSummary


def build_resume(db: Session, person_id: int) -> PersonResume | None:
    """Assemble the full resume for a person, or None if not found. TODO(Phase 1)."""
    raise NotImplementedError(
        "resume.build_resume — join person + office_term + party_affiliation/switch + affidavit + "
        "criminal_case (+ case_charge sections) and map to schemas, attaching Source to each fact."
    )


def search_persons(db: Session, q: str) -> list[PersonSummary]:
    """Trigram search over person.normalized_name + name variants. TODO(Phase 2)."""
    raise NotImplementedError("resume.search_persons — pg_trgm similarity over person.normalized_name.")
