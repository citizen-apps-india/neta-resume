"""Scrape recent news for every sitting legislator from the free Google News RSS feed.

For each current LS/RS member we search their name (+ office/party/seat context), keep the most recent
articles whose headline actually mentions them, and refresh their news_item rows. Runs weekly on CI.
Idempotent: a person's news is replaced each run. Provenance via source_ref ('news', trust_tier 3).
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_ingest.pipelines.identity.affidavit_attach import name_tokens
from neta_core.provenance import record_source_ref
from neta_sources.google_news import client as gn

KEEP = 15  # most-recent articles to store per legislator


def _relevant(title: str, toks: set[str]) -> bool:
    """Keep an article only if its headline mentions part of the member's name (trims Google's tangents)."""
    title_toks = name_tokens(title)
    return any(t in title_toks for t in toks if len(t) >= 3)


def run(house: str | None = None, limit: int | None = None) -> None:
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
                        WHERE ot.person_id = p.id ORDER BY (ot.status = 'sitting') DESC LIMIT 1) AS house_code
                FROM person p
                WHERE EXISTS (SELECT 1 FROM office_term o WHERE o.person_id = p.id AND o.status = 'sitting')
                ORDER BY p.display_name
                """
            )
        ).all()

    if house:
        rows = [r for r in rows if (r.house_code or "").lower() == house.lower().replace("ls", "ls").replace("rs", "rs")]
    if limit:
        rows = rows[:limit]
    print(f"[news] fetching news for {len(rows)} legislators …")

    ok = stored = failed = 0
    for r in rows:
        try:
            arts, raw_rel = gn.fetch_news(r.display_name, r.party, r.constituency, slug=str(r.id))
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
    print(f"[news] done: {ok} legislators, {stored} articles, {failed} failed.")
