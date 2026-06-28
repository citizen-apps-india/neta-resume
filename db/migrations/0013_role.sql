-- 0013: generic role/position model — the "Directory of Indian Politicians" maps one person across
-- houses AND roles over time (PM, minister, Speaker, LoP, committee chair, mayor, corporator, ...).
-- Supersedes the minimal cabinet_post (kept for a deprecation window; backfilled below).

CREATE TABLE IF NOT EXISTS role (
    id            bigserial PRIMARY KEY,
    person_id     bigint NOT NULL REFERENCES person(id),
    role_type     text NOT NULL CHECK (role_type IN (
                    'prime_minister','minister','minister_state','deputy_minister',
                    'chief_minister','deputy_cm',
                    'committee_member','committee_chair',
                    'speaker','deputy_speaker','lop','leader_of_house','whip','chief_whip',
                    'mayor','deputy_mayor','corporator')),
    title         text,                       -- 'Minister of Finance', 'Chairperson, PAC'
    body          text,                       -- 'Union Cabinet', 'Lok Sabha', 'BMC'
    house_id      smallint REFERENCES house(id),   -- nullable; ties the role to a house/jurisdiction
    portfolio     text,                       -- ministry/portfolio, when applicable
    start_date    date,
    end_date      date,                       -- NULL = current
    status        text NOT NULL DEFAULT 'current' CHECK (status IN ('current','former')),
    source_ref_id bigint NOT NULL REFERENCES source_ref(id),
    UNIQUE (person_id, role_type, body, start_date)   -- idempotency natural key
);

CREATE INDEX IF NOT EXISTS role_person_idx ON role (person_id);
CREATE INDEX IF NOT EXISTS role_type_idx   ON role (role_type);

-- Backfill from the minimal cabinet_post (heuristic role_type from title). Idempotent.
INSERT INTO role (person_id, role_type, title, body, start_date, end_date, status, source_ref_id)
SELECT person_id,
       CASE WHEN title ILIKE '%speaker%' AND title ILIKE '%deput%' THEN 'deputy_speaker'
            WHEN title ILIKE '%speaker%'                            THEN 'speaker'
            WHEN title ILIKE 'lop%' OR title ILIKE '%leader of opp%' THEN 'lop'
            WHEN title ILIKE '%whip%'                               THEN 'whip'
            ELSE 'minister' END,
       title, body, start_date, end_date,
       CASE WHEN end_date IS NULL THEN 'current' ELSE 'former' END, source_ref_id
FROM cabinet_post
ON CONFLICT (person_id, role_type, body, start_date) DO NOTHING;
