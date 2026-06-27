"""Court enrichment client — live case status via bharat-courts / openjustice-in/ecourts.

eCourts is CAPTCHA-gated for direct portal use; prefer:
  - iamshouvikmitra/bharat-courts (MIT, async) + its public AWS S3 judgment archive for backfill.
  - openjustice-in/ecourts (CLI) for targeted pulls (High Courts + benches strongest).

This runs AFTER cases exist (declared via MyNeta); it updates criminal_case.status / is_convicted /
court_source_ref_id, keyed on cnr_number where available. Best-effort enrichment, not the baseline.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CourtStatus:
    cnr_number: str
    status: str             # map to criminal_case.status enum
    is_convicted: bool
    source_url: str


def fetch_status(cnr_number: str) -> CourtStatus | None:
    raise NotImplementedError("courts.fetch_status — wrap bharat-courts; treat as best-effort enrichment.")
