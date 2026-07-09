-- 0025: individual parliamentary QUESTIONS and DEBATES per legislator (the content behind the 0024
-- scorecard counts). One row per (member, item). Sourced from PRS Legislative Research's MP Track
-- per-member profile (CC-BY 4.0): the sansad.in question/debate backend (eParlib) is not reachable
-- from outside-India IPs, but PRS enumerates the same items on its reachable, server-rendered profile
-- pages — subject/title, ministry, date, type — each linking the official sansad.in document PDF.
--
-- Missing != zero: an MP with no rows simply has none listed (ministers/rule-exempt/RS may legitimately
-- have none). Idempotent upsert on the natural key. Peer context (counts) already lives in
-- parliamentary_activity (0024) and is computed at read time — not duplicated here.

CREATE TABLE parliamentary_question (
    id              bigserial PRIMARY KEY,
    person_id       bigint NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    house_id        smallint NOT NULL REFERENCES house(id),
    term_cycle_id   bigint NOT NULL REFERENCES term_cycle(id),
    question_ref    text NOT NULL,          -- PRS annex id, e.g. "AS150" (starred) / "AU1111" (unstarred)
    subject         text,                   -- the question's subject line (short title)
    ministry        text,                   -- ministry addressed
    question_type   text,                   -- 'Starred' | 'Unstarred'
    asked_date      date,
    document_url    text,                   -- official sansad.in/getFile/loksabhaquestions/... PDF
    source_ref_id   bigint REFERENCES source_ref(id) ON DELETE SET NULL,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (person_id, term_cycle_id, question_ref)   -- one row per (member, question); idempotent
);

CREATE INDEX parliamentary_question_person_idx ON parliamentary_question (person_id);

CREATE TABLE parliamentary_debate (
    id              bigserial PRIMARY KEY,
    person_id       bigint NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    house_id        smallint NOT NULL REFERENCES house(id),
    term_cycle_id   bigint NOT NULL REFERENCES term_cycle(id),
    debate_ref      text NOT NULL,          -- stable key: normalized(title|date), debates lack a public id
    title           text,                   -- debate title / bill name
    debate_type     text,                   -- e.g. 'Discussion', 'Zero Hour', 'Special Mention'
    debate_date     date,
    document_url    text,                   -- official sansad.in/getFile/debatestextmk/... PDF (per sitting-day)
    source_ref_id   bigint REFERENCES source_ref(id) ON DELETE SET NULL,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (person_id, term_cycle_id, debate_ref)     -- one row per (member, debate); idempotent
);

CREATE INDEX parliamentary_debate_person_idx ON parliamentary_debate (person_id);
