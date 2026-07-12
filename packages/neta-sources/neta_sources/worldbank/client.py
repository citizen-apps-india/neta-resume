"""World Bank Open Data API (api.worldbank.org/v2) — country-level macro indicator time series.

One GET per indicator returns the FULL yearly history for a country (India: ~65 points), so a whole
dashboard refresh is ~25 polite requests. The API is keyless; the data is CC-BY 4.0 (the most permissive
license we ingest). Trust tier 1 (official international agency).

Gotchas learned from the live API:
- Some series (the EN.GHG.* emissions family) arrive with a UTF-8 BOM — decode with utf-8-sig.
- An unknown/retired code returns HTTP 200 with a one-element [{"message": ...}] body, not an error.
- Years the source has no value for come back as value=null — we DROP them (missing ≠ zero).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from neta_core.http import client as http
from neta_core.provenance import cache_raw

API = "https://api.worldbank.org/v2"

_ISO2 = {"IND": "IN"}  # data.worldbank.org human pages use ISO-2 in ?locations=


@dataclass(slots=True)
class IndicatorSeries:
    code: str
    name: str                        # the source's official series name
    points: list[tuple[int, float]]  # (year, value) — non-null only, ascending by year
    native_url: str                  # human-readable chart page (provenance link)
    raw_ref: str                     # cache_raw snapshot of the API response


def fetch_indicator(code: str, country: str = "IND") -> IndicatorSeries:
    """Fetch one indicator's full yearly history for a country. Raises if the code returns no data."""
    url = f"{API}/country/{country}/indicator/{code}?format=json&per_page=500"
    resp = http.get(url)
    resp.raise_for_status()
    raw_ref = cache_raw(resp.content, suffix=".json")
    payload = json.loads(resp.content.decode("utf-8-sig"))
    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        raise ValueError(f"World Bank returned no data for {code}: {str(payload)[:200]}")
    rows = payload[1]
    points = sorted((int(r["date"]), float(r["value"])) for r in rows if r.get("value") is not None)
    loc = _ISO2.get(country, country)
    return IndicatorSeries(
        code=code,
        name=rows[0]["indicator"]["value"],
        points=points,
        native_url=f"https://data.worldbank.org/indicator/{code}?locations={loc}",
        raw_ref=raw_ref,
    )
