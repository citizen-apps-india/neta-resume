"""Country-level macro indicators (India Dashboard) — World Bank Open Data -> macro_indicator_value.

The catalog of WHICH series we show lives in macro_indicator_def (seeded, curated); this pipeline fetches
each catalogued code's full India history and upserts the values. Country-level facts: the source_ref rows
carry no person_id. Idempotent — the source_ref upserts on (source, native_id) and values upsert on
(indicator_code, country_code, year), so a re-run refreshes in place.

Missing ≠ zero: the client already drops null years; a year the World Bank hasn't published is simply
absent (sparse series like the Gini stay sparse — the UI charts actual points).
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_core.provenance import record_source_ref
from neta_sources.worldbank import client as wb

_UPSERT = text("""
    INSERT INTO macro_indicator_value (indicator_code, country_code, year, value, source_ref_id, fetched_at)
    VALUES (:code, 'IND', :year, :value, :sr, now())
    ON CONFLICT (indicator_code, country_code, year)
    DO UPDATE SET value = EXCLUDED.value, source_ref_id = EXCLUDED.source_ref_id,
                  fetched_at = EXCLUDED.fetched_at
""")


def run(only: list[str] | None = None) -> None:
    with session_scope() as s:
        codes = [r.code for r in s.execute(
            text("SELECT code FROM macro_indicator_def ORDER BY category_order, ind_order")).all()]
    if only:
        wanted = set(only)
        codes = [c for c in codes if c in wanted]
    print(f"[macro-indicators] {len(codes)} catalogued indicator(s) to fetch from the World Bank")

    written = failed = 0
    for code in codes:
        try:
            series = wb.fetch_indicator(code)
        except Exception as e:  # one bad/retired code must not abort the whole refresh
            failed += 1
            print(f"  ! {code}: {e!r}")
            continue
        with session_scope() as s:
            source_ref_id = record_source_ref(
                s, source_code="worldbank", native_id=f"wb-{code}-IND",
                native_url=series.native_url, raw_name=series.name, raw_payload_ref=series.raw_ref,
            )
            s.execute(_UPSERT, [{"code": code, "year": y, "value": v, "sr": source_ref_id}
                                for y, v in series.points])
        written += len(series.points)
        print(f"  + {code}: {len(series.points)} year(s), latest {series.points[-1][0]}")

    print(f"[macro-indicators] done: {written} values across {len(codes) - failed} indicator(s), "
          f"{failed} failed")
