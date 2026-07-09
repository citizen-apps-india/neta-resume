-- 0027: indexes for the "Parliament functioning" search + trends views (Phase 3). Index-only — no schema
-- or data change. Two jobs:
--   1. Full-text search over question subjects / debate titles, so the topic search (/parliament/search)
--      stays fast even uncached on the free-tier API. GIN over to_tsvector('english', …) matches the
--      websearch_to_tsquery the read layer uses; coalesce() keeps NULL subjects/titles out of the index.
--   2. Date-bucketing for the trends view (/parliament/trends), which GROUP BYs date_trunc('month', …).
-- All read-time compute is absorbed by the web's 1-hour ISR cache; these just keep the queries cheap.

-- 1. Free-text search
CREATE INDEX IF NOT EXISTS parliamentary_question_subject_fts_idx
  ON parliamentary_question USING gin (to_tsvector('english', coalesce(subject, '')));
CREATE INDEX IF NOT EXISTS parliamentary_debate_title_fts_idx
  ON parliamentary_debate  USING gin (to_tsvector('english', coalesce(title, '')));

-- 2. Trends date-bucketing
CREATE INDEX IF NOT EXISTS parliamentary_question_asked_date_idx ON parliamentary_question (asked_date);
CREATE INDEX IF NOT EXISTS parliamentary_debate_debate_date_idx  ON parliamentary_debate (debate_date);
