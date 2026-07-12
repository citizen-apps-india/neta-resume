-- 0028: country-level macro indicators for the India Dashboard (GDP, prices, health, education, …).
-- Two tables: a curated indicator CATALOG (seeded from db/seeds/macro_indicators.sql — which indicators we
-- show, grouped and ordered) and the fetched VALUES (one row per indicator × country × year, upserted by
-- `neta macro-indicators`). Country-level facts — no person FK; the provenance source_ref rows keep
-- person_id NULL. v1 source is the World Bank Open Data API (keyless, CC-BY 4.0, trust tier 1); the
-- code column holds the source's native indicator code (e.g. 'NY.GDP.MKTP.CD').
-- Missing ≠ zero: years the source reports as null are simply absent here — never stored as 0.

CREATE TABLE macro_indicator_def (
    code           text PRIMARY KEY,   -- source-native series code, e.g. 'NY.GDP.MKTP.CD'
    name           text NOT NULL,      -- citizen-readable name (source's official series name)
    unit           text NOT NULL,      -- display unit label ('US$', '%', 'years', 'per 1,000 live births', …)
    format         text NOT NULL,      -- render hint: 'usd_compact' | 'pct' | 'number' | 'count_compact'
    category       text NOT NULL,      -- dashboard section, e.g. 'Economy & Growth'
    category_order smallint NOT NULL,  -- section order on the page
    ind_order      smallint NOT NULL   -- order within the section
);

CREATE TABLE macro_indicator_value (
    indicator_code text NOT NULL REFERENCES macro_indicator_def(code),
    country_code   text NOT NULL DEFAULT 'IND',  -- ISO alpha-3; 'IND' today, extensible later
    year           int NOT NULL,
    value          numeric NOT NULL,             -- never null: absent years are absent rows
    source_ref_id  bigint REFERENCES source_ref(id),
    fetched_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (indicator_code, country_code, year)
);
