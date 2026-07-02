"""Cross-cycle entity resolution: merge the same person across election cycles.

After ingesting more than one cycle (e.g. LS2024 + LS2019), the same incumbent exists as two separate
persons. This pass merges them so a person accrues multiple affidavits (a wealth trend) and multiple
office terms — and detects party switches between cycles.

Match rule (deliberately conservative — entity resolution is the highest-risk step):
    same normalized_name AND a shared constituency across two different cycles.
Same name + same seat in both elections is an extremely high-confidence match; people who changed
seats simply won't merge (acceptable — we favour precision over recall here). See docs/entity-resolution.md.
"""

from __future__ import annotations

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
        print(f"[merge] {len(pairs)} cross-cycle match(es) to merge")
        merged = 0
        for old_id, new_id in pairs:
            # old/new may already have been merged in a chain; skip if either is gone.
            if not _exists(s, old_id) or not _exists(s, new_id) or old_id == new_id:
                continue
            _merge(s, old_id, new_id)
            merged += 1
        switches = 0
        for pid in _multi_cycle_persons(s):
            switches += _detect_switches(s, pid)
        _set_cycle_status(s)
        pruned = _prune_non_current(s) if prune else 0
        print(f"[merge] merged {merged} person(s); {switches} switch event(s); "
              f"pruned {pruned} non-current (prior-cycle-only) person(s)")


def _exists(s, pid: int) -> bool:
    return s.execute(text("SELECT 1 FROM person WHERE id = :id"), {"id": pid}).first() is not None


def _merge_pairs(s) -> list[tuple[int, int]]:
    """Return (old_person_id, new_person_id) pairs: same name+constituency, older cycle -> newer."""
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


def _merge(s, old_id: int, new_id: int) -> None:
    # The older person's affiliations become historical (avoids two "current" parties).
    s.execute(text("UPDATE party_affiliation SET is_current = false WHERE person_id = :old"), {"old": old_id})
    # Drop name variants that would collide with the survivor's (UNIQUE person_id,variant,source_id).
    s.execute(
        text(
            """
            DELETE FROM person_name_variant o
            WHERE o.person_id = :old
              AND EXISTS (
                SELECT 1 FROM person_name_variant n
                WHERE n.person_id = :new AND n.variant = o.variant
                  AND n.source_id IS NOT DISTINCT FROM o.source_id)
            """
        ),
        {"old": old_id, "new": new_id},
    )
    # Drop old-side rows that would collide with the survivor's UNIQUE keys before repointing:
    #   contact   UNIQUE(person_id, channel_type, value)   ·   news_item UNIQUE(person_id, url)
    s.execute(
        text("DELETE FROM contact o WHERE o.person_id = :old AND EXISTS (SELECT 1 FROM contact n "
             "WHERE n.person_id = :new AND n.channel_type = o.channel_type AND n.value = o.value)"),
        {"old": old_id, "new": new_id},
    )
    s.execute(
        text("DELETE FROM news_item o WHERE o.person_id = :old AND EXISTS (SELECT 1 FROM news_item n "
             "WHERE n.person_id = :new AND n.url = o.url)"),
        {"old": old_id, "new": new_id},
    )
    for tbl in _PERSON_TABLES:
        s.execute(text(f"UPDATE {tbl} SET person_id = :new WHERE person_id = :old"), {"new": new_id, "old": old_id})
    s.execute(text("DELETE FROM person WHERE id = :old"), {"old": old_id})


def _multi_cycle_persons(s) -> list[int]:
    rows = s.execute(
        text(
            """
            SELECT person_id FROM office_term
            GROUP BY person_id HAVING count(DISTINCT term_cycle_id) > 1
            """
        )
    ).all()
    return [r.person_id for r in rows]


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
    """Delete persons who are not currently sitting in ANY house — prior-cycle-only winners ingested
    solely to backfill current members' history.

    A person is KEPT if they hold an office term in a currently-sitting cycle: the LATEST cycle of that
    term's OWN house (per-house max number), OR any Rajya Sabha cycle (RS is a continuous house whose
    sitting cohort is modelled as one cycle). Per-house max is essential: cycle numbers are independent
    across houses (RS-CURRENT is number 1; Maharashtra VS is 15), so a cross-house `max(number)` compare
    would wrongly delete every RS member and every state/municipal member. Persons with no office term at
    all are left untouched.
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
    for pid in ids:
        # criminal_case -> case_charge and affidavit -> line_item cascade on delete.
        for tbl in ("criminal_case", "affidavit", "office_term", "cabinet_post", "role",
                    "party_affiliation", "party_switch_event", "news_item", "contact",
                    "person_name_variant", "source_ref"):
            s.execute(text(f"DELETE FROM {tbl} WHERE person_id = :p"), {"p": pid})
        s.execute(text("DELETE FROM person WHERE id = :p"), {"p": pid})
    return len(ids)


def _detect_switches(s, person_id: int) -> int:
    """Compare party across this person's office terms (oldest->newest); record switch events."""
    terms = s.execute(
        text(
            """
            SELECT tc.number AS cyc, ot.party_id, ot.source_ref_id
            FROM office_term ot JOIN term_cycle tc ON tc.id = ot.term_cycle_id
            WHERE ot.person_id = :pid AND ot.party_id IS NOT NULL
            ORDER BY COALESCE(tc.start_date, DATE '2099-12-31')  -- chronological across houses, not by number
            """
        ),
        {"pid": person_id},
    ).all()
    count = 0
    for prev, curr in zip(terms, terms[1:]):
        if prev.party_id != curr.party_id:
            # idempotent: don't duplicate an already-recorded switch
            exists = s.execute(
                text(
                    "SELECT 1 FROM party_switch_event WHERE person_id=:p AND from_party_id=:f AND to_party_id=:t"
                ),
                {"p": person_id, "f": prev.party_id, "t": curr.party_id},
            ).first()
            if not exists:
                s.execute(
                    text(
                        """
                        INSERT INTO party_switch_event
                          (person_id, from_party_id, to_party_id, detected_from, narrative_source_ref_id)
                        VALUES (:p, :f, :t, 'term_diff', :sr)
                        """
                    ),
                    {"p": person_id, "f": prev.party_id, "t": curr.party_id, "sr": curr.source_ref_id},
                )
                count += 1
    return count
