"""Backfill native-script (Devanagari) names from Wikidata for the Mukta-typeface display.

Wikidata tags members of the 18th Lok Sabha (position Q125498038) and carries Hindi (hi) labels for
many of them. We match those to our persons by normalized name and store the Hindi label as a
person_name_variant with script='devanagari', source=wikidata. Coverage is partial (Wikidata hasn't
tagged every MP yet); names degrade gracefully to English where absent.
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_core.http import client as http
from neta_core.transform.names import normalize_name

SPARQL = """
SELECT ?p ?enLabel ?hiLabel WHERE {
  ?p wdt:P39 wd:Q125498038 .
  ?p rdfs:label ?enLabel . FILTER(LANG(?enLabel)="en")
  OPTIONAL { ?p rdfs:label ?hiLabel . FILTER(LANG(?hiLabel)="hi") }
}
"""


def run() -> None:
    resp = http.get(
        "https://query.wikidata.org/sparql",
        params={"query": SPARQL, "format": "json"},
        headers={"Accept": "application/sparql-results+json"},
    )
    rows = resp.json()["results"]["bindings"]
    pairs = [
        (r["enLabel"]["value"], r["hiLabel"]["value"])
        for r in rows
        if "hiLabel" in r and r["hiLabel"]["value"].strip()
    ]
    print(f"[native] Wikidata returned {len(rows)} members, {len(pairs)} with Hindi labels")

    with session_scope() as s:
        wikidata_source_id = s.execute(text("SELECT id FROM source WHERE code = 'wikidata'")).scalar()
        # index our persons by normalized name
        people = s.execute(text("SELECT id, normalized_name FROM person")).all()
        by_norm: dict[str, int] = {p.normalized_name: p.id for p in people}

        matched = 0
        for en, hi in pairs:
            pid = by_norm.get(normalize_name(en))
            if pid is None:
                continue
            s.execute(
                text(
                    """
                    INSERT INTO person_name_variant (person_id, variant, source_id, script)
                    VALUES (:pid, :v, :sid, 'devanagari')
                    ON CONFLICT (person_id, variant, source_id) DO NOTHING
                    """
                ),
                {"pid": pid, "v": hi, "sid": wikidata_source_id},
            )
            matched += 1
        print(f"[native] matched + stored Devanagari names for {matched} person(s)")
