"""QA for the historical backfill (read-only, no network).

Run after Tier-1 + Tier-2:  uv run python scripts_qa_backfill.py
Checks coverage, provenance integrity, and re-parses cached raw HTML to confirm stored values match
their source snapshot.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from sqlalchemy import text

from neta_ingest.config import settings
from neta_ingest.db.engine import session_scope
from neta_ingest.sources.myneta.parser import parse_candidate

CACHE = Path(settings.raw_cache_dir)


def section(t):
    print(f"\n{'='*70}\n{t}\n{'='*70}")


def main():
    with session_scope() as s:
        section("1. Affidavit coverage by cycle")
        for cyc, n in s.execute(text(
                "SELECT election_cycle, count(*) FROM affidavit GROUP BY 1 ORDER BY 1")):
            print(f"  {cyc}: {n}")

        section("2. Historical depth per current MP (distinct affidavit cycles)")
        dist = s.execute(text(
            """
            SELECT ncyc, count(*) FROM (
              SELECT person_id, count(DISTINCT election_cycle) AS ncyc
              FROM affidavit GROUP BY person_id
            ) t GROUP BY ncyc ORDER BY ncyc
            """)).all()
        for ncyc, n in dist:
            print(f"  {ncyc} cycle(s): {n} MP(s)")
        total_mp = s.execute(text("SELECT count(*) FROM person")).scalar()
        with_hist = s.execute(text(
            "SELECT count(DISTINCT person_id) FROM affidavit WHERE election_cycle <> 'LS2024'")).scalar()
        print(f"  -> {with_hist}/{total_mp} MPs have at least one PRE-2024 affidavit")

        section("3. Provenance integrity")
        for tbl in ("affidavit", "criminal_case"):
            miss = s.execute(text(f"SELECT count(*) FROM {tbl} WHERE source_ref_id IS NULL")).scalar()
            print(f"  {tbl} rows with NULL source_ref_id: {miss}")
        # raw snapshot file existence for a sample of source_refs
        refs = s.execute(text(
            "SELECT id, raw_payload_ref FROM source_ref "
            "WHERE source_id=(SELECT id FROM source WHERE code='myneta') AND raw_payload_ref IS NOT NULL")).all()
        missing_files = [r.id for r in refs if not (CACHE / r.raw_payload_ref).exists()]
        print(f"  myneta source_refs: {len(refs)}, missing raw snapshot on disk: {len(missing_files)}")

        section("4. Cross-check stored values vs cached raw HTML (sample 40)")
        rows = s.execute(text(
            """
            SELECT a.id, a.election_cycle, a.total_assets, sr.raw_payload_ref, sr.native_id
            FROM affidavit a JOIN source_ref sr ON sr.id = a.source_ref_id
            WHERE sr.raw_payload_ref IS NOT NULL
            """)).all()
        sample = random.sample(rows, min(40, len(rows)))
        mism = 0
        for r in sample:
            p = CACHE / r.raw_payload_ref
            if not p.exists():
                print(f"  [missing file] aff#{r.id} {r.native_id}")
                mism += 1
                continue
            parsed = parse_candidate(p.read_text(encoding="utf-8", errors="ignore"))
            if parsed.total_assets != r.total_assets:
                print(f"  [MISMATCH] aff#{r.id} {r.native_id}: db={r.total_assets} reparsed={parsed.total_assets}")
                mism += 1
        print(f"  checked {len(sample)} affidavits; {mism} mismatch(es)")

        section("5. Review queues (Tier-2 ambiguous/unmatched)")
        for cyc in ("LS2019", "LS2014", "LS2009"):
            rp = Path("data/hist_index") / f"review_{cyc}.json"
            if rp.exists():
                data = json.loads(rp.read_text())
                print(f"  {cyc}: {len(data)} queued for review")
            else:
                print(f"  {cyc}: (no review file yet)")

        section("6. Sample multi-cycle MP timeline")
        pid = s.execute(text(
            """
            SELECT person_id FROM affidavit GROUP BY person_id
            HAVING count(DISTINCT election_cycle) = (SELECT max(c) FROM
              (SELECT count(DISTINCT election_cycle) c FROM affidavit GROUP BY person_id) z)
            LIMIT 1
            """)).scalar()
        if pid:
            name = s.execute(text("SELECT display_name FROM person WHERE id=:p"), {"p": pid}).scalar()
            print(f"  {name} (person {pid}):")
            for row in s.execute(text(
                    "SELECT election_cycle, filed_year, total_assets, total_liabilities "
                    "FROM affidavit WHERE person_id=:p ORDER BY filed_year"), {"p": pid}):
                print(f"    {row.election_cycle} ({row.filed_year}): assets={row.total_assets:,} liab={row.total_liabilities:,}")
            ncases = s.execute(text("SELECT count(*) FROM criminal_case WHERE person_id=:p"), {"p": pid}).scalar()
            print(f"    criminal cases across cycles: {ncases}")


if __name__ == "__main__":
    main()
