-- Simple key→count store for site-wide tallies (the homepage lifetime unique-visitor counter).
-- Kept separate from the legislator data so it is just a durable counter the API increments.
CREATE TABLE IF NOT EXISTS site_counter (
    key   text PRIMARY KEY,
    count bigint NOT NULL DEFAULT 0
);

INSERT INTO site_counter (key, count) VALUES ('unique_visitors', 0)
ON CONFLICT (key) DO NOTHING;
