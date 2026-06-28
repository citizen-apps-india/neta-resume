-- Recent press coverage per legislator, scraped weekly from the free Google News RSS feed.
-- Headline + source + date + short snippet only; every row links out to the publisher (trust_tier 3,
-- 'reported'). Provenance via source_ref like every other fact.
CREATE TABLE IF NOT EXISTS news_item (
    id            bigserial PRIMARY KEY,
    person_id     bigint NOT NULL REFERENCES person(id),
    source_ref_id bigint NOT NULL REFERENCES source_ref(id),
    title         text NOT NULL,
    snippet       text,
    url           text NOT NULL,
    publisher     text,                                   -- the outlet name from the feed (e.g. "The Hindu")
    published_at  date,
    fetched_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (person_id, url)
);

CREATE INDEX IF NOT EXISTS news_item_person_idx ON news_item (person_id);
CREATE INDEX IF NOT EXISTS news_item_published_idx ON news_item (published_at DESC);
