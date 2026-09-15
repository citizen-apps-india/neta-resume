"""Scrape recent news for every sitting legislator from the free Google News RSS feed.

For each current LS/RS member we search their name (+ office/party/seat context), keep the most recent
articles whose headline actually mentions them, and refresh their news_item rows. Runs weekly on CI.
Idempotent: a person's news is replaced each run. Provenance via source_ref ('news', trust_tier 3).

Bounding + resumability: Google News RSS is fetched serially (one host, throttled to 1 req/sec — see
neta_core.http.client), and CI runner IPs are the kind of shared/datacenter traffic Google's anti-bot
layer is most likely to rate-limit, which drives every request into its full retry/backoff ceiling
(neta_core.http.client.get: 4 attempts, 30s timeout each). Against ~800 sitting legislators that can
add up past any fixed job ceiling. So a run stops itself once it has spent its wall-clock budget
(_time_budget_exceeded), rather than relying on GitHub to hard-cancel it — and the roster query orders
by each person's last successful fetch (never-covered first), so whoever a run didn't get to is exactly
who the next run picks up first. No tail is ever permanently dropped by cutting a run short.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_core.provenance import record_source_ref
from neta_ingest.extraction import source_extraction_context
from neta_ingest.pipelines.identity.affidavit_attach import name_tokens
from neta_sources.google_news import client as gn

KEEP = 15  # most-recent articles to store per legislator

# Stop cleanly with time to spare inside the news workflow's `timeout-minutes: 240` — comfortably
# before GitHub's own 360-minute hard ceiling would cancel the job mid-run.
TIME_BUDGET_SECONDS = 210 * 60  # 3h30m

# Indirection so tests can substitute a fake clock without patching the stdlib `time` module.
_clock: Callable[[], float] = time.monotonic


def _time_budget_exceeded(started: float, *, now: float | None = None) -> bool:
    """True once a run has spent its wall-clock budget and should stop before its next legislator."""
    current = _clock() if now is None else now
    return (current - started) >= TIME_BUDGET_SECONDS


def _relevant(title: str, toks: set[str]) -> bool:
    """Keep an article only if its headline mentions part of the member's name (trims Google's tangents)."""
    title_toks = name_tokens(title)
    return any(t in title_toks for t in toks if len(t) >= 3)


def run(house: str | None = None, limit: int | None = None) -> None:
    started = _clock()
    with session_scope() as s:
        rows = s.execute(
            text(
                """
                SELECT p.id, p.display_name, p.normalized_name,
                       (SELECT pt.canonical_name FROM party_affiliation pa JOIN party pt ON pt.id = pa.party_id
                        WHERE pa.person_id = p.id AND pa.is_current LIMIT 1) AS party,
                       (SELECT COALESCE(ot.constituency, ot.rs_state_code)
                        FROM office_term ot JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                        WHERE ot.person_id = p.id ORDER BY (ot.status = 'sitting') DESC, tc.number DESC LIMIT 1) AS constituency,
                       (SELECT h.code FROM office_term ot JOIN house h ON h.id = ot.house_id
                        WHERE ot.person_id = p.id ORDER BY (ot.status = 'sitting') DESC LIMIT 1) AS house_code,
                       (SELECT MAX(ni.fetched_at) FROM news_item ni WHERE ni.person_id = p.id) AS last_fetched_at
                FROM person p
                WHERE EXISTS (SELECT 1 FROM office_term o WHERE o.person_id = p.id AND o.status = 'sitting')
                ORDER BY last_fetched_at ASC NULLS FIRST, p.display_name
                """
            )
        ).all()

    if house:
        rows = [r for r in rows if (r.house_code or "").lower() == house.lower().replace("ls", "ls").replace("rs", "rs")]
    if limit:
        rows = rows[:limit]
    print(f"[news] fetching news for {len(rows)} legislators (never-covered / stalest-covered first) …")

    extraction_context = source_extraction_context(gn.SOURCE_ID)
    ok = stored = failed = 0
    stopped_early = False
    for i, r in enumerate(rows):
        if _time_budget_exceeded(started):
            remaining = len(rows) - i
            stopped_early = True
            print(
                f"[news] time budget ({TIME_BUDGET_SECONDS // 60}m) reached after {ok} legislators "
                f"({failed} failed) — stopping cleanly with {remaining} legislators left; they are the "
                f"stalest-covered and will lead the next run."
            )
            break
        try:
            artifact = gn.extract_news(
                r.display_name,
                r.party,
                r.constituency,
                slug=str(r.id),
                context=extraction_context,
            )
            arts = gn.parse_news_artifact(artifact)
            raw_rel = artifact.provenance_ref
        except Exception as e:  # noqa: BLE001 — log + skip a bad feed, keep the batch going
            failed += 1
            print(f"  [{r.id}] {r.display_name}: FAILED {type(e).__name__}: {e}")
            continue

        toks = name_tokens(r.display_name)
        keep = [a for a in arts if _relevant(a.title, toks)][:KEEP]
        with session_scope() as s:
            s.execute(text("DELETE FROM news_item WHERE person_id = :p"), {"p": r.id})
            for a in keep:
                sref = record_source_ref(
                    s, source_code="news", native_id=f"google-news:{a.url}",
                    native_url=a.url, raw_name=r.display_name, raw_payload_ref=raw_rel,
                )
                s.execute(
                    text(
                        """
                        INSERT INTO news_item (person_id, source_ref_id, title, snippet, url, publisher, published_at)
                        VALUES (:pid, :sr, :title, :snip, :url, :pub, :pdate)
                        ON CONFLICT (person_id, url) DO UPDATE SET
                          title = EXCLUDED.title, snippet = EXCLUDED.snippet, publisher = EXCLUDED.publisher,
                          published_at = EXCLUDED.published_at, source_ref_id = EXCLUDED.source_ref_id, fetched_at = now()
                        """
                    ),
                    {"pid": r.id, "sr": sref, "title": a.title, "snip": a.snippet, "url": a.url,
                     "pub": a.publisher, "pdate": a.published_at},
                )
        ok += 1
        stored += len(keep)
        if ok % 50 == 0:
            print(f"  [{ok}/{len(rows)}] … {stored} articles stored")
    if not stopped_early:
        print(f"[news] done: {ok} legislators, {stored} articles, {failed} failed. Nothing left in this run's batch.")
