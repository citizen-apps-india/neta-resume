"""Entity-resolution decision layer.

Three bands (thresholds in config): auto-merge >= er_auto_merge_score, auto-reject < er_auto_reject_score,
else -> review queue (er_candidate). Combines SURF name similarity (resolve.surf) with structured signals
(same constituency+cycle, overlapping party history, age). Writes are reversible (FK only) and audited.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MatchDecision:
    source_ref_id: int
    person_id: int | None
    score: float
    band: str               # 'auto_merge' | 'review' | 'reject'


def score_pair(left: dict, right: dict) -> float:
    """Weighted blend of SURF name similarity + structured signals. Returns 0..1."""
    raise NotImplementedError("match.score_pair — combine resolve.surf.similarity with structured signals.")


def resolve_unlinked() -> int:
    """Resolve all source_refs with person_id IS NULL. Returns count decided. TODO(Phase 2)."""
    raise NotImplementedError("match.resolve_unlinked — block (resolve.blocking) -> score -> decide -> link.")
