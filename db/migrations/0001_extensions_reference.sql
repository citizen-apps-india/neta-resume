-- 0001: extensions + reference/spine tables (no person dependency)
-- Apply order: 0001 → 0007, then db/seeds/*.sql

CREATE EXTENSION IF NOT EXISTS pg_trgm;        -- fuzzy name search + ER blocking

-- A legislative house: LS, RS, or a state assembly/council (states added later, no schema change).
CREATE TABLE house (
    id            smallserial PRIMARY KEY,
    code          text NOT NULL UNIQUE,          -- 'LS','RS','MH_VS', ...
    name          text NOT NULL,
    jurisdiction  text NOT NULL CHECK (jurisdiction IN ('union','state')),
    state_code    text                            -- NULL for LS/RS; ISO-ish for states
);

-- A numbered house instance / election cycle (17th LS, 18th LS; RS biennial cohort).
CREATE TABLE term_cycle (
    id               bigserial PRIMARY KEY,
    house_id         smallint NOT NULL REFERENCES house(id),
    number           int NOT NULL,
    start_date       date,
    end_date         date,
    eci_election_id  text,                         -- ties to ECI/MyNeta election partition
    UNIQUE (house_id, number)
);

-- Canonical party registry + spelling aliases (BJP / Bharatiya Janata Party / regional spellings).
CREATE TABLE party (
    id              bigserial PRIMARY KEY,
    canonical_name  text NOT NULL,
    abbr            text,
    eci_party_id    text,
    is_active       boolean NOT NULL DEFAULT true
);

CREATE TABLE party_alias (
    id        bigserial PRIMARY KEY,
    party_id  bigint NOT NULL REFERENCES party(id),
    alias     text NOT NULL,
    source    text,
    UNIQUE (party_id, alias)
);

-- A data SOURCE (system), not a single row.
CREATE TABLE source (
    id          smallserial PRIMARY KEY,
    code        text NOT NULL UNIQUE,             -- 'sansad','myneta','tcpd_surf','bharat_courts','datagovin','wikidata','news'
    name        text NOT NULL,
    base_url    text,
    license     text,                             -- 'non-commercial' for MyNeta/ADR
    trust_tier  smallint NOT NULL DEFAULT 2       -- 1 official, 2 ADR/TCPD, 3 reported/news
);
