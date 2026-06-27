"""Candidate-pair blocking — cheaply narrow comparisons before expensive SURF scoring.

Block on: (state/constituency), (party), (birth_year +/- 1), and pg_trgm similarity on
person.normalized_name. Avoids O(n^2) over all persons. See docs/entity-resolution.md.
"""

from __future__ import annotations


def candidate_person_ids(source_ref: dict) -> list[int]:
    """Return a small candidate set of person.id to score against. TODO(Phase 2)."""
    raise NotImplementedError("blocking.candidate_person_ids — use pg_trgm + structured blocking keys.")
