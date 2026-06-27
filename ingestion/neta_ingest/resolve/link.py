"""Apply ER decisions: set source_ref.person_id and record an audit row.

Linking is just an FK write -> reversible and idempotent. Keep an er_decision audit (signals, score,
rule version) so any merge is explainable and unmergeable.
"""

from __future__ import annotations


def link(source_ref_id: int, person_id: int, *, score: float, signals: dict) -> None:
    raise NotImplementedError("link.link — UPDATE source_ref SET person_id; INSERT er_decision audit.")
