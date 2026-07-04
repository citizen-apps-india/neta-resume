-- 0021: denormalized identity match-features on person, refreshed by `neta derive-signals`
-- (the sourced truth stays on affidavit / office_term). These power the cross-house identity
-- stitcher's scoring; keeping them on person avoids re-aggregating on every candidate pair.

ALTER TABLE person
    ADD COLUMN home_state    text,   -- modal state across office_terms / rs_state_code
    ADD COLUMN relative_name text;   -- the S/o|D/o|W/o relative from the person's latest affidavit
                                     -- (MyNeta's label is generic, so this is father-or-spouse; still a
                                     -- decisive disambiguator — two same-name politicians rarely share it)

-- Trigram index on normalized_name for the stitcher's candidate blocking (pg_trgm is created in 0001).
CREATE INDEX IF NOT EXISTS person_normalized_name_trgm_idx
    ON person USING gin (normalized_name gin_trgm_ops);
