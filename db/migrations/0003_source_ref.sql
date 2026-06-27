-- 0003: source_ref (native identity in a source → person) + multi-source provenance edge

-- A native record identity in a source, linked to a person once entity-resolved.
-- This is the dedup/idempotency key for ingestion upserts: UNIQUE(source_id, native_id).
CREATE TABLE source_ref (
    id               bigserial PRIMARY KEY,
    source_id        smallint NOT NULL REFERENCES source(id),
    native_id        text NOT NULL,                -- sansad member_id / myneta candidate_id / tcpd surf_id
    native_url       text,                         -- canonical link to that page (provenance)
    person_id        bigint REFERENCES person(id), -- NULL until entity-resolved
    raw_name         text,
    raw_payload_ref  text,                         -- path/hash into ingestion/data/raw_cache snapshot
    fetched_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, native_id)
);

CREATE INDEX source_ref_person_idx ON source_ref (person_id);

-- Generic provenance edge: used when one fact is corroborated by multiple sources
-- (e.g. a party-switch event confirmed by news + Wikidata).
CREATE TABLE fact_source (
    id             bigserial PRIMARY KEY,
    source_ref_id  bigint NOT NULL REFERENCES source_ref(id),
    observed_at    date,
    retrieved_at   timestamptz NOT NULL DEFAULT now(),
    note           text
);
