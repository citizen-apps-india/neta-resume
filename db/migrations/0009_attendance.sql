-- 0009: per-term parliamentary attendance % (cumulative, from PRS Legislative Research).
-- Lives on office_term (one value per posting) and carries its own provenance pointer, like every fact.
-- NULL is meaningful: rule-exempt members (ministers, PM, Speaker/Dep. Speaker, LoP) don't sign the
-- attendance register, so they legitimately have no %. NULL renders as "—", never 0.
ALTER TABLE office_term ADD COLUMN IF NOT EXISTS attendance_pct numeric(5,2);
ALTER TABLE office_term ADD COLUMN IF NOT EXISTS attendance_source_ref_id bigint REFERENCES source_ref(id);
