-- 0002: canonical person + observed name variants

CREATE TABLE person (
    id               bigserial PRIMARY KEY,        -- canonical person_id, stable across houses/elections
    display_name     text NOT NULL,
    normalized_name  text NOT NULL,                -- transliteration-normalized key (blocking/search)
    gender           text,
    birth_year       int,
    tcpd_surf_id     text UNIQUE,                  -- seeded from TCPD where available
    wikidata_qid     text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX person_normalized_name_idx      ON person (normalized_name);
CREATE INDEX person_normalized_name_trgm_idx ON person USING gin (normalized_name gin_trgm_ops);

-- Every observed spelling of a person's name (search + entity-resolution audit).
CREATE TABLE person_name_variant (
    id         bigserial PRIMARY KEY,
    person_id  bigint NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    variant    text NOT NULL,
    source_id  smallint REFERENCES source(id),
    script     text,                               -- 'latin','devanagari'
    UNIQUE (person_id, variant, source_id)
);

CREATE INDEX person_name_variant_trgm_idx ON person_name_variant USING gin (variant gin_trgm_ops);
