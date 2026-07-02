"""Tier-2: backfill a CURRENT MP's PAST-cycle records, even if they lost or changed seats.

Tier-1 (winners list + merge_cycles) only links a current MP's past record when they *won* that past
Lok Sabha election. This pipeline closes the rest: for each sitting LS18 MP without an affidavit for a
given past cycle, it searches that cycle's full MyNeta candidate set by name — first in the MP's current
constituency, then globally — and attaches a confident match's affidavit + criminal data to the existing
person (no new person). These are criminal records, so the bar is precision: same-seat strong matches and
unique global name matches with age corroboration are auto-written; anything ambiguous goes to a review
queue (data/hist_index/review_<cycle>.json) for human/agent adjudication instead of being guessed.

The per-cycle candidate index (every constituency's candidate list) is crawled once and cached to disk,
so re-runs and the matching pass cost no network. All fetches go through the throttled http client.
"""

from __future__ import annotations

import json
import os

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_ingest.pipelines.identity import affidavit_attach as aa
from neta_sources.myneta import client as myneta

_INDEX_DIR = "data/hist_index"

# Thresholds: looser inside the MP's own constituency (strong prior), strict for a blind global match.
SAME_CONST_THRESHOLD = 0.80
GLOBAL_THRESHOLD = 0.90
AGE_TOLERANCE_YEARS = 3


def _index_path(cycle: str) -> str:
    return os.path.join(_INDEX_DIR, f"candidates_{cycle}.json")


def build_index(cycle: str, refresh: bool = False) -> dict[str, list[list[str]]]:
    """{constituency_norm: [[candidate_id, name], ...]} for an entire cycle. Cached to disk.

    One fetch per constituency (~540), so it is crawled once and reused by every matching run.
    """
    path = _index_path(cycle)
    if not refresh and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    os.makedirs(_INDEX_DIR, exist_ok=True)
    const_map = myneta.fetch_constituency_map(cycle)
    print(f"[hist:{cycle}] building candidate index over {len(const_map)} constituencies (one-time crawl)…")
    index: dict[str, list[list[str]]] = {}
    for i, (const_norm, cons_id) in enumerate(sorted(const_map.items()), 1):
        try:
            cands = myneta.fetch_constituency_candidates(cons_id, cycle)
            index[const_norm] = [[cid, name] for cid, name in cands]
        except Exception as e:  # noqa: BLE001 - skip a bad constituency page, keep crawling
            print(f"  [{i}/{len(const_map)}] {const_norm}: FAILED {type(e).__name__}: {e}")
            continue
        if i % 50 == 0:
            print(f"  [{i}/{len(const_map)}] indexed … ({sum(len(v) for v in index.values())} candidates)")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f)
    print(f"[hist:{cycle}] index cached: {len(index)} constituencies, "
          f"{sum(len(v) for v in index.values())} candidates -> {path}")
    return index


def _build_token_index(index: dict[str, list[list[str]]]) -> dict[str, list[tuple[str, str, str]]]:
    """Inverted index {name_token: [(candidate_id, name, constituency), ...]} built once per cycle.

    Lets each MP's global search touch only candidates that share a token, instead of rescanning and
    re-tokenizing the whole cycle (~8k candidates) for every one of ~540 MPs.
    """
    inv: dict[str, list[tuple[str, str, str]]] = {}
    for const_norm, cands in index.items():
        for cid, name in cands:
            for tok in aa.name_tokens(name):
                inv.setdefault(tok, []).append((cid, name, const_norm))
    return inv


def _token_shortlist(token_index: dict[str, list[tuple[str, str, str]]],
                     display_name: str) -> list[tuple[str, str, str]]:
    """Global candidates (cand_id, name, constituency) sharing >=2 meaningful name tokens with the MP."""
    want = aa.name_tokens(display_name)
    if len(want) < 2:
        return []
    counts: dict[str, int] = {}
    rec: dict[str, tuple[str, str, str]] = {}
    for tok in want:
        for cid, name, const in token_index.get(tok, ()):
            counts[cid] = counts.get(cid, 0) + 1
            rec[cid] = (cid, name, const)
    return [rec[cid] for cid, n in counts.items() if n >= 2]


def run(cycle: str, current_cycle: str = "LS2024", house: str = "ls",
        limit: int | None = None, refresh_index: bool = False) -> None:
    if cycle == current_cycle:
        raise ValueError(f"historical-lookup is for PAST cycles; {current_cycle} is the current roster")
    index = build_index(cycle, refresh=refresh_index)

    with session_scope() as s:
        house_id = s.execute(text("SELECT id FROM house WHERE code=:c"), {"c": house.upper()}).scalar()
        term_cycle_id = s.execute(
            text("SELECT id FROM term_cycle WHERE eci_election_id=:c"), {"c": cycle}
        ).scalar()
        if term_cycle_id is None:
            raise RuntimeError(f"term_cycle {cycle!r} not seeded")
        # Current (LS18) MPs who do NOT yet have an affidavit for this past cycle.
        rows = s.execute(
            text(
                """
                SELECT p.id, p.display_name, p.normalized_name, p.birth_year, ot.constituency
                FROM office_term ot
                JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                JOIN person p ON p.id = ot.person_id
                WHERE tc.eci_election_id = :cur
                  AND NOT EXISTS (
                    SELECT 1 FROM affidavit a WHERE a.person_id = p.id AND a.election_cycle = :c
                  )
                ORDER BY p.display_name
                """
            ),
            {"c": cycle, "cur": current_cycle},
        ).all()

    const_map = myneta.fetch_constituency_map(cycle)
    stripped = {aa.strip_const(k): v for k, v in const_map.items()}
    token_index = _build_token_index(index)
    winners = {w.candidate_id for w in myneta.fetch_winners(cycle)}
    if limit:
        rows = rows[:limit]
    print(f"[hist:{cycle}] {len(rows)} sitting MPs missing a {cycle} affidavit to search for")

    written = 0
    terms = 0
    review: list[dict] = []
    for person in rows:
        cand_id, score, source, evidence = _resolve_person(
            person, cycle, index, token_index, const_map, stripped, winners
        )
        if cand_id is None:
            if evidence:  # ambiguous / near-miss worth a human look
                review.append({"person_id": person.id, "name": person.display_name,
                               "constituency": person.constituency, "reason": source,
                               "candidates": evidence})
            continue

        parsed, raw_rel = myneta.fetch_candidate(cand_id, cycle)
        # Age corroboration for every sourced match (when both ages are known). Guards same-name-
        # different-person attaches — including dynastic relatives who share a surname AND a seat, which
        # Jaro-Winkler's prefix weighting can now lift over the same-const gate. A genuine age mismatch
        # routes to review rather than a false attach.
        if source in ("same-const", "global", "multiseat-win") and person.birth_year and parsed.age:
            implied = aa.cycle_year(cycle) - parsed.age
            if abs(implied - person.birth_year) > AGE_TOLERANCE_YEARS:
                review.append({"person_id": person.id, "name": person.display_name,
                               "constituency": person.constituency,
                               "reason": f"{source} match {cand_id} age mismatch "
                                         f"(implied {implied} vs birth_year {person.birth_year})",
                               "candidates": evidence})
                continue
        won = cand_id in winners
        with session_scope() as s:
            aa.write_affidavit(s, parsed, person.id, cand_id, raw_rel,
                               house_id=house_id, term_cycle_id=term_cycle_id, cycle=cycle)
            # If this candidacy was a WIN, also record the historical office term (status 'former'),
            # so a seat-changing MP shows the full career, not just their current seat.
            if won:
                aa.write_office_term(s, parsed, person.id, cand_id,
                                     house_id=house_id, term_cycle_id=term_cycle_id, cycle=cycle)
                terms += 1
        written += 1
        print(f"  [{written}] {person.display_name} -> {cand_id} ({source} {score:.2f}{' WON' if won else ''}) "
              f"assets={parsed.total_assets:,} cases={len(parsed.criminal_cases)}")

    os.makedirs(_INDEX_DIR, exist_ok=True)
    review_path = os.path.join(_INDEX_DIR, f"review_{cycle}.json")
    with open(review_path, "w", encoding="utf-8") as f:
        json.dump(review, f, indent=2)
    print(f"[hist:{cycle}] done: {written} affidavits attached ({terms} as won terms); "
          f"{len(review)} queued for review -> {review_path}")


def _resolve_person(person, cycle, index, token_index, const_map, stripped, winners):
    """Return (candidate_id|None, score, source, evidence).

    source ∈ {'same-const','global','multiseat-win'} when matched; otherwise a reason string and
    `evidence` holds the top near-miss candidates (so an unmatched-but-plausible MP can be reviewed).
    """
    # 1) Same constituency as the MP's current seat — strongest prior.
    cons_id = aa.resolve_constituency(const_map, stripped, person.constituency or "")
    if cons_id:
        const_norm = next((k for k, v in const_map.items() if v == cons_id), None)
        cands = [(cid, name) for cid, name in index.get(const_norm, [])] if const_norm else []
        cid, score, ambiguous = aa.best_match(
            cands, person.display_name, person.normalized_name, threshold=SAME_CONST_THRESHOLD
        )
        if cid and not ambiguous:
            return cid, score, "same-const", None

    # 2) Global name search across the whole cycle (token-shortlisted, strict threshold).
    shortlist = _token_shortlist(token_index, person.display_name)
    cands = [(cid, name) for cid, name, _const in shortlist]
    cid, score, ambiguous = aa.best_match(
        cands, person.display_name, person.normalized_name, threshold=GLOBAL_THRESHOLD
    )
    if cid and not ambiguous:
        return cid, score, "global", None

    # Multi-seat: a high-profile candidate often contests >1 seat, so several candidacies tie on name
    # (-> ambiguous). Those are the same person; if the WINNING seat is among them, resolve to it
    # (win-both -> take the first winner). Age corroboration in run() guards against a same-name winner.
    if cid and ambiguous:
        winner_hits = [
            c for c, name, _const in shortlist
            if c in winners
            and aa.name_score(person.display_name, name, person.normalized_name) >= GLOBAL_THRESHOLD
        ]
        if winner_hits:
            return winner_hits[0], 1.0, "multiseat-win", None

    # No confident pick. Surface the strongest near-misses for review if any are interesting.
    evidence = sorted(
        ({"candidate_id": cid, "name": name, "constituency": const,
          "score": round(aa.name_score(person.display_name, name, person.normalized_name), 3)}
         for cid, name, const in shortlist),
        key=lambda d: d["score"], reverse=True,
    )[:5]
    evidence = [e for e in evidence if e["score"] >= 0.70]
    reason = "ambiguous" if (cid and ambiguous) else "no confident match"
    return None, 0.0, reason, evidence
