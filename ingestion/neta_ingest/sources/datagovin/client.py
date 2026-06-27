"""data.gov.in (OGD) client — bulk election/candidate datasets.

data.gov.in has no native search API, so use addypy/datagovindia to index the catalog locally, then
pull resources via the REST API (requires a free API key -> settings via NETA_ env). Used for
cross-validation / bulk backfill, not as the primary roster.
"""

from __future__ import annotations


def search_resources(query: str) -> list[dict]:
    raise NotImplementedError("datagovin.search_resources — use datagovindia catalog index; needs API key.")
