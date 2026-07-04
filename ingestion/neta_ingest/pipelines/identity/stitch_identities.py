"""Cross-house identity stitcher — a sibling pass to merge-cycles that catches the SAME human stored as
separate person records across DIFFERENT houses (an MLA who became an MP, a state minister now in RS, …).

Blocks candidate pairs across houses by trigram-similar name, scores each with stitch_score (name +
relative + birth-year + home-state + party + gender + native), then:
  * auto_merge (near-certain, ≥2 corroborating signals, no veto) -> merge NOW via merge_cycles._merge,
  * review -> a 'pending' row in person_merge_candidate for a human (neta review),
  * reject -> dropped (never stored).
A person appearing in >1 auto_merge pair with different partners is ambiguous -> all its pairs go to review.
Idempotent + safe to re-run: decided pairs (rejected/accepted/auto_merged) are skipped.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_ingest.pipelines.identity import merge_cycles
from neta_ingest.pipelines.identity import derive_identity_signals
from neta_ingest.pipelines.identity.stitch_score import RULE_VERSION, score_person_pair

# Trigram floor for BLOCKING only (cheap superset); stitch_score's NAME_FLOOR (0.85) does the real gate.
_BLOCK_SIMILARITY = 0.5


def _candidate_pairs(s, limit: int) -> list[tuple[int, int]]:
    s.execute(text(f"SET LOCAL pg_trgm.similarity_threshold = {_BLOCK_SIMILARITY}"))
    sql = """
        SELECT DISTINCT p1.id AS id1, p2.id AS id2
        FROM person p1
        JOIN person p2
          ON p2.id > p1.id
         AND p1.normalized_name <> '' AND p2.normalized_name <> ''
         AND p1.normalized_name % p2.normalized_name           -- pg_trgm, uses the GIN index
        WHERE EXISTS (
            SELECT 1 FROM office_term o1
            JOIN office_term o2 ON o2.person_id = p2.id AND o2.house_id <> o1.house_id
            WHERE o1.person_id = p1.id
        )
        ORDER BY p1.id, p2.id
    """
    if limit and limit > 0:
        sql += f"\n        LIMIT {int(limit)}"
    return [(r.id1, r.id2) for r in s.execute(text(sql)).all()]


def _load_signals(s, ids: list[int]) -> dict[int, dict]:
    rows = s.execute(
        text(
            """
            SELECT p.id, p.display_name, p.normalized_name, p.birth_year, p.home_state,
                   p.relative_name, p.gender,
                   (SELECT variant FROM person_name_variant
                      WHERE person_id = p.id AND script = 'devanagari' LIMIT 1) AS native_name,
                   (SELECT max(COALESCE(tc.start_date, DATE '2099-12-31'))
                      FROM office_term ot JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                      WHERE ot.person_id = p.id) AS latest_term,
                   ARRAY(SELECT DISTINCT party_id FROM party_affiliation
                          WHERE person_id = p.id AND party_id IS NOT NULL) AS party_ids
            FROM person p WHERE p.id = ANY(:ids)
            """
        ),
        {"ids": ids},
    )
    return {r.id: dict(r._mapping) for r in rows}


def _decided_pairs(s) -> set[tuple[int, int]]:
    """Pairs already handled: human rejects (suppressed at this rule_version) + completed merges."""
    rows = s.execute(
        text(
            """
            SELECT person_lo, person_hi FROM person_merge_candidate
            WHERE person_lo IS NOT NULL AND person_hi IS NOT NULL
              AND (status IN ('accepted', 'auto_merged')
                   OR (status = 'rejected' AND rule_version = :rv))
            """
        ),
        {"rv": RULE_VERSION},
    )
    return {(r.person_lo, r.person_hi) for r in rows}


def _upsert_candidate(s, lo: int, hi: int, score: float, band: str, evidence: dict, status: str,
                      decided_by: str | None) -> None:
    s.execute(
        text(
            """
            INSERT INTO person_merge_candidate
              (person_lo, person_hi, score, band, evidence, rule_version, status, decided_by, decided_at)
            VALUES (:lo,:hi,:sc,:band, CAST(:ev AS jsonb), :rv, :status, :by,
                    CASE WHEN CAST(:by AS text) IS NULL THEN NULL ELSE now() END)
            ON CONFLICT (person_lo, person_hi) DO UPDATE
              SET score = EXCLUDED.score, band = EXCLUDED.band, evidence = EXCLUDED.evidence,
                  rule_version = EXCLUDED.rule_version
              WHERE person_merge_candidate.status = 'pending'
            """
        ),
        {"lo": lo, "hi": hi, "sc": score, "band": band, "ev": _json(evidence), "rv": RULE_VERSION,
         "status": status, "by": decided_by},
    )


def _json(d: dict) -> str:
    import json
    return json.dumps(d)


def run(dry_run: bool = False, limit: int = 0) -> None:
    with session_scope() as s:
        pairs = _candidate_pairs(s, limit)
        ids = sorted({i for pair in pairs for i in pair})
        sig = _load_signals(s, ids)
        decided = _decided_pairs(s)

        bands: dict[str, int] = defaultdict(int)
        scored: list[tuple[int, int, float, dict]] = []   # auto_merge candidates
        for id1, id2 in pairs:
            lo, hi = (id1, id2) if id1 < id2 else (id2, id1)
            if (lo, hi) in decided:
                bands["skipped"] += 1
                continue
            a, b = sig.get(id1), sig.get(id2)
            if not a or not b:
                continue
            score, band, ev = score_person_pair(a, b)
            ev["pair"] = [lo, hi]
            bands[band] += 1
            if band == "reject":
                continue
            if band == "review":
                _upsert_candidate(s, lo, hi, score, band, ev, status="pending", decided_by=None)
            else:  # auto_merge
                scored.append((lo, hi, score, ev))

        # Ambiguity guard: a person in >1 auto_merge pair with different partners -> demote all to review.
        seen: dict[int, int] = defaultdict(int)
        for lo, hi, _sc, _ev in scored:
            seen[lo] += 1
            seen[hi] += 1
        remap: dict[int, int] = {}
        auto_done = ambiguous = 0
        for lo, hi, score, ev in scored:
            if seen[lo] > 1 or seen[hi] > 1:
                ambiguous += 1
                ev["note"] = "ambiguous: person in multiple auto-merge pairs -> review"
                _upsert_candidate(s, lo, hi, score, ev.get("_band", "review"), ev,
                                  status="pending", decided_by=None)
                continue
            # survivor = the person with the more-recent latest term (keeps the current identity).
            a, b = sig[lo], sig[hi]
            survivor, loser = (lo, hi) if (a["latest_term"] or "") >= (b["latest_term"] or "") else (hi, lo)
            remap[loser] = survivor
            _upsert_candidate(s, lo, hi, score, "auto_merge", ev, status="auto_merged", decided_by="auto")
            auto_done += 1

        if dry_run:
            s.rollback()
            print(f"[stitch] DRY RUN — bands: {dict(bands)}; would auto-merge {auto_done} "
                  f"({ambiguous} demoted to review).")
            return

        merged = merge_cycles._merge(s, remap) if remap else 0
        if merged:
            merge_cycles._set_cycle_status(s)
            merge_cycles._detect_switches(s)
        print(f"[stitch] bands: {dict(bands)}; auto-merged {merged} person(s), {ambiguous} demoted, "
              f"{bands['review']} queued for review.")

    if not dry_run and remap:
        derive_identity_signals.run()
