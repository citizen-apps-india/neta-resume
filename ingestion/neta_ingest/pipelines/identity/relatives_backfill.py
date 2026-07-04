"""Re-crawl MyNeta candidate pages to backfill affidavit.relative_name / relation_type — the S/o|D/o
father (or W/o spouse) printed on each affidavit. This is the strongest identity-disambiguation signal
for cross-house stitching, and the earlier rollout's raw HTML caches are gone, so we re-fetch politely.

Idempotent + resumable: only affidavits with relative_name IS NULL are re-fetched (self-limiting — the
set shrinks each run), one MyNeta request/second (inherited from the throttled client), and a --minutes
budget so it fits under the cron cap like the historical backfill. A page with no discernible relative
is stamped '' (empty) so it isn't re-fetched forever.
"""

from __future__ import annotations

import time

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_sources.myneta import client as myneta


def _pending(s, cycle: str | None) -> list[tuple[int, str]]:
    src = s.execute(text("SELECT id FROM source WHERE code = 'myneta'")).scalar()
    if src is None:
        return []
    sql = (
        "SELECT DISTINCT a.source_ref_id, sr.native_id "
        "FROM affidavit a JOIN source_ref sr ON sr.id = a.source_ref_id "
        "WHERE a.relative_name IS NULL AND sr.source_id = :src"
    )
    params: dict = {"src": src}
    if cycle:
        sql += " AND sr.native_id LIKE :prefix"
        params["prefix"] = f"{cycle}:%"
    sql += " ORDER BY sr.native_id"
    rows = s.execute(text(sql), params).fetchall()
    return [(r[0], r[1]) for r in rows]


def run(cycle: str | None = None, minutes: float | None = None, limit: int = 0) -> None:
    deadline = time.monotonic() + minutes * 60 if minutes else None
    with session_scope() as s:
        pending = _pending(s, cycle)
    total = len(pending)
    if limit and limit > 0:
        pending = pending[:limit]
    print(f"[relatives] {total} affidavit pages missing a relative; processing {len(pending)} ...")

    fetched = with_rel = failed = 0
    for i, (source_ref_id, native_id) in enumerate(pending, 1):
        if deadline and time.monotonic() > deadline:
            print(f"[relatives] time budget reached at {i - 1}/{len(pending)} — resumable, exiting.")
            break
        cyc, _, cid = native_id.partition(":")  # MyNeta native_id = "{cycle}:{candidate_id}"
        if not cid:
            continue
        try:
            parsed, _raw = myneta.fetch_candidate(cid, cyc)
            with session_scope() as s:
                s.execute(
                    text(
                        "UPDATE affidavit SET relative_name = :rn, relation_type = :rt "
                        "WHERE source_ref_id = :sr AND relative_name IS NULL"
                    ),
                    # '' (not NULL) marks "fetched, none found" so it isn't re-crawled next run.
                    {"rn": parsed.relative_name or "", "rt": parsed.relation_type, "sr": source_ref_id},
                )
            fetched += 1
            if parsed.relative_name:
                with_rel += 1
            if i % 25 == 0 or i == len(pending):
                print(f"  [{i}/{len(pending)}] {cyc}:{cid} -> {parsed.relation_type}: {parsed.relative_name}")
        except Exception as e:  # noqa: BLE001 - log, keep going; NULL predicate retries it next run
            failed += 1
            print(f"  [{i}/{len(pending)}] {native_id}: FAILED {type(e).__name__}: {e}")
    print(f"[relatives] done: {fetched} fetched, {with_rel} with a relative, {failed} failed.")
