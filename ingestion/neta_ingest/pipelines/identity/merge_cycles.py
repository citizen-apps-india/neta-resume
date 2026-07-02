"""Cross-cycle entity resolution: merge the same person across election cycles.

After ingesting more than one cycle (e.g. LS2024 + LS2019), the same incumbent exists as two separate
persons. This pass merges them so a person accrues multiple affidavits (a wealth trend) and multiple
office terms — and detects party switches between cycles.

Match rule (deliberately conservative — entity resolution is the highest-risk step):
    same normalized_name AND a shared constituency across two different cycles.
Same name + same seat in both elections is an extremely high-confidence match; people who changed
seats simply won't merge (acceptable — we favour precision over recall here). See docs/entity-resolution.md.

Implemented SET-BASED: instead of thousands of per-row round-trips (slow over a hosted DB), each step is a
handful of bulk statements over a temp remap table — ~constant statement count regardless of row volume.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import text

from neta_core.db.engine import session_scope

# Person-scoped tables whose rows must move from the merged-away person to the survivor.
# (Keep in sync with _prune_non_current's delete list + every table carrying a person_id FK.)
_PERSON_TABLES = (
    "person_name_variant", "source_ref", "office_term", "cabinet_post", "role",
    "party_affiliation", "party_switch_event", "affidavit", "criminal_case",
    "news_item", "contact",
)


def run(prune: bool = True) -> None:
    with session_scope() as s:
        pairs = _merge_pairs(s)
        remap = _resolve_survivors(pairs)
        merged = _merge(s, remap)
        switches = _detect_switches(s)
        _set_cycle_status(s)
        pruned = _prune_non_current(s) if prune else 0
        print(f"[merge] {len(pairs)} pair(s); merged {merged} person(s); {switches} switch event(s); "
              f"pruned {pruned} non-current (prior-cycle-only) person(s)")


def _merge_pairs(s) -> list[tuple[int, int]]:
    """(old_person_id, new_person_id): same name+constituency, older cycle -> newer (by DATE)."""
    rows = s.execute(
        text(
            """
            SELECT DISTINCT o.person_id AS old_id, n.person_id AS new_id
            FROM office_term o
            JOIN office_term n
              ON n.constituency = o.constituency AND n.person_id <> o.person_id
            JOIN person po ON po.id = o.person_id
            JOIN person pn ON pn.id = n.person_id
            JOIN term_cycle tco ON tco.id = o.term_cycle_id
            JOIN term_cycle tcn ON tcn.id = n.term_cycle_id
            WHERE po.normalized_name = pn.normalized_name
              AND po.normalized_name <> ''
              AND o.constituency IS NOT NULL
              -- chronological by DATE, not cycle number (number isn't comparable across houses:
              -- LS is 15–18, state assemblies use year-numbers). RS-CURRENT has no date -> treat as latest.
              AND COALESCE(tco.start_date, DATE '2099-12-31') < COALESCE(tcn.start_date, DATE '2099-12-31')
            """
        )
    ).all()
    return [(r.old_id, r.new_id) for r in rows]


def _resolve_survivors(pairs: list[tuple[int, int]]) -> dict[int, int]:
    """Map each merged-away person -> its FINAL survivor.

    Pairs are old->new with strictly-increasing dates, so the graph is a DAG. The survivor of a component
    is a terminal node (one that is never on an "old" side). Walking forward from each loser to the reachable
    terminal(s) deterministically collapses chains — including name-bridged ones the old sequential loop
    could skip. A rare multi-terminal branch (one person continuing into two later persons) picks max() —
    deterministic and precision-preserving (survivors are never remapped, so two survivors never fuse).
    """
    adj: dict[int, set[int]] = defaultdict(set)
    olds: set[int] = set()
    news: set[int] = set()
    for old, new in pairs:
        adj[old].add(new)
        olds.add(old)
        news.add(new)
    terminals = news - olds  # survivors: appear as "new" but never as "old"

    remap: dict[int, int] = {}
    for loser in olds:
        seen: set[int] = set()
        stack = [loser]
        reached: list[int] = []
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            if node in terminals:
                reached.append(node)
            else:
                stack.extend(adj[node])
        remap[loser] = max(reached)
    return remap


def _dedup(s, tbl: str, match: str) -> None:
    """Delete loser-side rows that would violate {tbl}'s UNIQUE key once repointed onto the survivor.

    Resolves each candidate row through the remap so it covers BOTH loser-vs-survivor and loser-vs-loser
    collisions: keep the survivor's own row if any, else the lowest-id loser row.
    """
    s.execute(
        text(
            f"""
            DELETE FROM {tbl} o
            USING _merge_remap rm
            WHERE o.person_id = rm.loser_id            -- only ever delete loser rows
              AND EXISTS (
                SELECT 1 FROM {tbl} k
                LEFT JOIN _merge_remap rk ON rk.loser_id = k.person_id
                WHERE COALESCE(rk.survivor_id, k.person_id) = rm.survivor_id  -- k resolves to same survivor
                  AND {match}
                  AND k.id <> o.id
                  AND (rk.loser_id IS NULL   -- k is survivor-owned -> it always wins (loser-vs-survivor)
                       OR k.id < o.id)        -- else the lowest-id loser wins (loser-vs-loser)
              )
            """
        )
    )


def _merge(s, remap: dict[int, int]) -> int:
    if not remap:
        return 0
    s.execute(text("CREATE TEMP TABLE _merge_remap (loser_id bigint PRIMARY KEY, survivor_id bigint NOT NULL) "
                   "ON COMMIT DROP"))
    s.execute(text("INSERT INTO _merge_remap (loser_id, survivor_id) VALUES (:l, :s)"),
              [{"l": loser, "s": surv} for loser, surv in remap.items()])
    s.execute(text("CREATE INDEX ON _merge_remap (survivor_id)"))

    # Losers' affiliations become historical BEFORE repoint (party_affiliation has a partial-unique
    # index on person_id WHERE is_current — two 'current' rows on the survivor would collide).
    s.execute(text("UPDATE party_affiliation pa SET is_current = false "
                   "FROM _merge_remap rm WHERE pa.person_id = rm.loser_id AND pa.is_current"))

    # Drop rows that would collide on a UNIQUE key after repoint.
    _dedup(s, "person_name_variant", "k.variant = o.variant AND k.source_id IS NOT DISTINCT FROM o.source_id")
    _dedup(s, "contact", "k.channel_type = o.channel_type AND k.value = o.value")
    _dedup(s, "news_item", "k.url = o.url")

    for tbl in _PERSON_TABLES:
        s.execute(text(f"UPDATE {tbl} t SET person_id = rm.survivor_id "
                       f"FROM _merge_remap rm WHERE t.person_id = rm.loser_id"))
    s.execute(text("DELETE FROM person p USING _merge_remap rm WHERE p.id = rm.loser_id"))
    return len(remap)


def _detect_switches(s) -> int:
    """Record a party_switch_event for each change of party across a person's terms (oldest->newest by DATE).

    Single windowed INSERT (LAG over each person's date-ordered terms). Skips party-NULL terms; keeps the
    first occurrence of an A->B transition; idempotent (NOT EXISTS the existing event). The 'to' term's
    source_ref is the narrative source; detected_from='term_diff'.
    """
    res = s.execute(
        text(
            """
            INSERT INTO party_switch_event
                (person_id, from_party_id, to_party_id, detected_from, narrative_source_ref_id)
            SELECT DISTINCT ON (person_id, from_party_id, to_party_id)
                   person_id, from_party_id, to_party_id, 'term_diff', to_source_ref_id
            FROM (
                SELECT ot.person_id,
                       lag(ot.party_id) OVER w AS from_party_id,
                       ot.party_id             AS to_party_id,
                       ot.source_ref_id        AS to_source_ref_id,
                       ot.id                   AS ot_id
                FROM office_term ot
                JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                WHERE ot.party_id IS NOT NULL
                WINDOW w AS (PARTITION BY ot.person_id
                             ORDER BY COALESCE(tc.start_date, DATE '2099-12-31'), tc.id, ot.id)
            ) seq
            WHERE from_party_id IS NOT NULL
              AND from_party_id <> to_party_id
              AND NOT EXISTS (
                    SELECT 1 FROM party_switch_event e
                    WHERE e.person_id = seq.person_id
                      AND e.from_party_id = seq.from_party_id
                      AND e.to_party_id = seq.to_party_id)
            ORDER BY person_id, from_party_id, to_party_id, ot_id
            """
        )
    )
    return res.rowcount or 0


def _set_cycle_status(s) -> None:
    """Each person's most recent term (by DATE) is 'sitting'; earlier terms become 'former'.

    Ranks by start_date, NOT cycle number — number isn't comparable across houses (LS is 15–18, state
    assemblies use year-numbers), so a person spanning houses (e.g. an MLA who became an MP) would otherwise
    get the wrong term marked sitting. RS-CURRENT has no date -> COALESCE to a far-future sentinel so the
    continuous current RS cohort ranks as latest.
    """
    s.execute(
        text(
            """
            UPDATE office_term ot
            SET status = CASE WHEN COALESCE(tc.start_date, DATE '2099-12-31') = mx.maxd
                              THEN 'sitting' ELSE 'former' END
            FROM term_cycle tc,
                 (SELECT ot2.person_id, max(COALESCE(tc2.start_date, DATE '2099-12-31')) AS maxd
                  FROM office_term ot2 JOIN term_cycle tc2 ON tc2.id = ot2.term_cycle_id
                  GROUP BY ot2.person_id) mx
            WHERE ot.term_cycle_id = tc.id AND mx.person_id = ot.person_id
            """
        )
    )


def _prune_non_current(s) -> int:
    """Delete persons not currently sitting in ANY house — prior-cycle-only winners ingested solely to
    backfill current members' history. KEPT if they hold a term in the LATEST cycle of that term's OWN house
    (per-house max number — monotonic within a house) OR any Rajya Sabha cycle. Persons with no office term
    at all are left untouched.
    """
    ids = [
        r.id
        for r in s.execute(
            text(
                """
                SELECT p.id
                FROM person p
                WHERE EXISTS (SELECT 1 FROM office_term o WHERE o.person_id = p.id)
                  AND NOT EXISTS (
                    SELECT 1 FROM office_term ot
                    JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                    JOIN house h ON h.id = tc.house_id
                    WHERE ot.person_id = p.id
                      AND (h.code = 'RS'
                           OR tc.number = (SELECT max(tc2.number) FROM term_cycle tc2
                                           WHERE tc2.house_id = h.id))
                  )
                """
            ),
        ).all()
    ]
    if not ids:
        return 0
    # criminal_case -> case_charge and affidavit -> line_item cascade on delete.
    for tbl in ("criminal_case", "affidavit", "office_term", "cabinet_post", "role",
                "party_affiliation", "party_switch_event", "news_item", "contact",
                "person_name_variant", "source_ref"):
        s.execute(text(f"DELETE FROM {tbl} WHERE person_id = ANY(:ids)"), {"ids": ids})
    s.execute(text("DELETE FROM person WHERE id = ANY(:ids)"), {"ids": ids})
    return len(ids)
