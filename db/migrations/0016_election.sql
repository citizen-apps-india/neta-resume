-- 0016: election registry — the Elections module's index of past (with results) + upcoming elections.
-- Reference data (seeded, like house/party); the winners it links to already carry their own provenance.

CREATE TABLE IF NOT EXISTS election (
    id              bigserial PRIMARY KEY,
    eci_election_id text UNIQUE,                 -- ties a PAST election to its term_cycle; NULL for upcoming
    name            text NOT NULL,
    level           text NOT NULL CHECK (level IN ('national', 'state', 'municipal')),
    house_code      text,                        -- house whose winners are this election's results; NULL upcoming
    election_date   date,
    status          text NOT NULL CHECK (status IN ('past', 'upcoming')),
    seats           int,
    note            text
);
