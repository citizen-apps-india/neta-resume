-- 0023: a phonetic (metaphone-over-sorted-tokens) blocking key on person, refreshed by
-- `neta derive-signals`. Lets the cross-house stitcher block same-SOUND / different-SPELLING names
-- (e.g. Muhammad/Mohammed) that the trigram key misses. Derived purely from normalized_name.

ALTER TABLE person ADD COLUMN phonetic_key text;

-- Partial b-tree on equality (empty keys never participate in the blocking join).
CREATE INDEX IF NOT EXISTS person_phonetic_key_idx
    ON person (phonetic_key) WHERE phonetic_key <> '';
