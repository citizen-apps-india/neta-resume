-- 0020: relative on the affidavit (S/o|D/o = father/guardian, W/o = spouse) as printed on the
-- MyNeta candidate page. This is the strongest identity DISAMBIGUATION signal for stitching one
-- human across houses/cycles (two politicians sharing a name rarely share a father's name).
-- Sourced + per-cycle on the affidavit; a person-level rollup lives on person (0021).

ALTER TABLE affidavit
    ADD COLUMN relative_name text,
    ADD COLUMN relation_type text CHECK (relation_type IN ('father', 'spouse', 'guardian'));
