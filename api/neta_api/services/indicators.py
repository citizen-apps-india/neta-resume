"""India Dashboard read service — country-level macro indicators grouped by curated category.

One query joins the fetched values (macro_indicator_value) to the curated catalog (macro_indicator_def,
which fixes grouping + ordering) and each series' provenance (source_ref -> source). The whole dashboard
is a single payload: ~24 series × their yearly points, small enough to ship at once and cached by the
web's 1-hour ISR. Sparse series stay sparse — missing years are absent, never zero.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

_DASHBOARD_SQL = text("""
    SELECT d.code, d.name, d.unit, d.format, d.category,
           v.year, v.value,
           s.code AS src_code, s.name AS src_name, s.trust_tier, sr.native_url
    FROM macro_indicator_value v
    JOIN macro_indicator_def d ON d.code = v.indicator_code
    LEFT JOIN source_ref sr ON sr.id = v.source_ref_id
    LEFT JOIN source s ON s.id = sr.source_id
    WHERE v.country_code = 'IND'
    ORDER BY d.category_order, d.ind_order, v.year
""")


def india_dashboard(db: Session) -> dict:
    rows = db.execute(_DASHBOARD_SQL).all()

    categories: list[dict] = []
    series: dict | None = None
    for r in rows:
        if series is None or series["code"] != r.code:
            source = {
                "code": r.src_code or "worldbank",
                "name": r.src_name or "World Bank Open Data",
                "url": r.native_url,
                "trust_tier": r.trust_tier or 1,
            }
            series = {"code": r.code, "name": r.name, "unit": r.unit, "format": r.format,
                      "latest_value": 0.0, "latest_year": 0, "points": [], "source": source}
            if not categories or categories[-1]["name"] != r.category:
                categories.append({"name": r.category, "indicators": []})
            categories[-1]["indicators"].append(series)
        series["points"].append({"year": r.year, "value": float(r.value)})
        series["latest_year"] = r.year          # rows arrive year-ascending per series
        series["latest_value"] = float(r.value)

    return {
        "country": "India",
        "categories": categories,
        "total_indicators": sum(len(c["indicators"]) for c in categories),
    }
