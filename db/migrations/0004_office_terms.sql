-- 0004: office-posting / term history (the roster spine) + cabinet/leadership posts

-- One posting in a legislature. Extends to states purely by adding house/term_cycle rows.
CREATE TABLE office_term (
    id               bigserial PRIMARY KEY,
    person_id        bigint NOT NULL REFERENCES person(id),
    house_id         smallint NOT NULL REFERENCES house(id),
    term_cycle_id    bigint NOT NULL REFERENCES term_cycle(id),
    constituency     text,                          -- LS seat; NULL for RS nominated
    rs_state_code    text,                          -- RS members represent a state
    membership_type  text NOT NULL DEFAULT 'elected'  -- 'elected','nominated','byelection'
                       CHECK (membership_type IN ('elected','nominated','byelection')),
    start_date       date,
    end_date         date,
    party_id         bigint REFERENCES party(id),   -- party AT TIME OF this term (drives switch detection)
    status           text NOT NULL DEFAULT 'sitting'  -- 'sitting','former','disqualified','resigned'
                       CHECK (status IN ('sitting','former','disqualified','resigned')),
    source_ref_id    bigint NOT NULL REFERENCES source_ref(id),
    UNIQUE (person_id, term_cycle_id, constituency)
);

CREATE INDEX office_term_person_idx ON office_term (person_id);
CREATE INDEX office_term_cycle_idx  ON office_term (term_cycle_id);

-- Ministerial / leadership office postings over time.
CREATE TABLE cabinet_post (
    id             bigserial PRIMARY KEY,
    person_id      bigint NOT NULL REFERENCES person(id),
    title          text NOT NULL,                   -- 'Minister of Finance','LoP','Speaker'
    body           text,                            -- 'Union Cabinet','Lok Sabha'
    start_date     date,
    end_date       date,
    source_ref_id  bigint NOT NULL REFERENCES source_ref(id)
);

CREATE INDEX cabinet_post_person_idx ON cabinet_post (person_id);
