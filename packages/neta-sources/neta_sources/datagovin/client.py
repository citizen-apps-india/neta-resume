"""data.gov.in (OGD) resource client — official Government-of-India open datasets (GODL, trust tier 1).

Each dataset on data.gov.in is a "resource" with a UUID; the resource API returns its rows as JSON:
    https://api.data.gov.in/resource/{resource_id}?api-key={key}&format=json&limit=…&offset=…
The key is free (register at api.data.gov.in) and read from NETA_DATAGOVIN_API_KEY. We use this to
auto-refresh the subset of India-Dashboard institutional counts that data.gov.in exposes as clean
resources (e.g. district-wise scheduled-commercial-bank offices); the rest come from curated report
figures. Every response is snapshotted via cache_raw for provenance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from neta_core.config import settings
from neta_core.http import client as http
from neta_core.provenance import cache_raw

API = "https://api.data.gov.in/resource"


class MissingApiKey(RuntimeError):
    """Raised when NETA_DATAGOVIN_API_KEY is unset — callers fall back to curated figures."""


@dataclass(slots=True)
class ResourcePage:
    resource_id: str
    records: list[dict]      # the dataset rows for this page
    total: int               # total rows the resource reports (for paging)
    native_url: str          # human-readable catalog page (provenance link)
    raw_ref: str             # cache_raw snapshot of the API response


def have_api_key() -> bool:
    return bool(settings.datagovin_api_key)


def fetch_resource(resource_id: str, *, limit: int = 1000, offset: int = 0) -> ResourcePage:
    """Fetch one page of an OGD resource's rows. Raises MissingApiKey when no key is configured."""
    if not settings.datagovin_api_key:
        raise MissingApiKey("NETA_DATAGOVIN_API_KEY is not set")
    url = (f"{API}/{resource_id}?api-key={settings.datagovin_api_key}"
           f"&format=json&limit={limit}&offset={offset}")
    resp = http.get(url)
    resp.raise_for_status()
    raw_ref = cache_raw(resp.content, suffix=".json")
    payload = json.loads(resp.content.decode("utf-8-sig"))
    records = payload.get("records") or []
    total = int(payload.get("total") or len(records))
    return ResourcePage(
        resource_id=resource_id,
        records=records,
        total=total,
        native_url=f"https://www.data.gov.in/resource/{resource_id}",
        raw_ref=raw_ref,
    )
