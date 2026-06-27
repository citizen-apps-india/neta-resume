-- 0005: party-affiliation history (with reported narrative) + explicit switch events

-- A person's membership of a party over a date range. The "why" is REPORTED narrative.
CREATE TABLE party_affiliation (
    id             bigserial PRIMARY KEY,
    person_id      bigint NOT NULL REFERENCES person(id),
    party_id       bigint NOT NULL REFERENCES party(id),
    joined_date    date,
    left_date      date,
    is_current     boolean NOT NULL DEFAULT false,
    join_reason    text,                            -- narrative, REPORTED (UI labels it so)
    leave_reason   text,                            -- narrative, REPORTED
    detection      text NOT NULL DEFAULT 'structured_term_diff'
                     CHECK (detection IN ('structured_term_diff','manual','news_derived')),
    confidence     smallint NOT NULL DEFAULT 50,    -- 0..100
    source_ref_id  bigint NOT NULL REFERENCES source_ref(id)  -- source for the AFFILIATION FACT
);

CREATE INDEX party_affiliation_person_idx  ON party_affiliation (person_id);
CREATE UNIQUE INDEX party_affiliation_current_idx
    ON party_affiliation (person_id) WHERE is_current;

-- An explicit switch: left from_party → joined to_party. Auto-detected from office_term party diffs;
-- the narrative "why" carries its own (lower-trust) source ref.
CREATE TABLE party_switch_event (
    id                       bigserial PRIMARY KEY,
    person_id                bigint NOT NULL REFERENCES person(id),
    from_party_id            bigint REFERENCES party(id),
    to_party_id              bigint NOT NULL REFERENCES party(id),
    event_date               date,
    narrative                text,                  -- "reported reason", clearly labelled in UI
    narrative_source_ref_id  bigint REFERENCES source_ref(id),  -- news / wikidata link
    detected_from            text NOT NULL DEFAULT 'term_diff'
);

CREATE INDEX party_switch_event_person_idx ON party_switch_event (person_id);
