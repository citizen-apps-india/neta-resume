-- 0024: per-legislator parliamentary ACTIVITY scorecard (what an MP did, not just who they are).
-- One row per person per term, sourced from PRS Legislative Research's MP Track (CC-BY 4.0): the
-- cumulative counts of questions asked, debates participated in, and private-member bills introduced
-- over the term, with the PRS reporting window. Attendance-% is NOT duplicated here — it stays on
-- office_term (attendance_pct). Peer context (house median/percentile) is computed at read time from
-- these rows, so only the raw counts are stored.
--
-- Individual question TEXT (the parliamentary_question table) lands in a later migration once the
-- sansad questions endpoint is confirmed — this migration is the scorecard only.

CREATE TABLE parliamentary_activity (
    id                   bigserial PRIMARY KEY,
    person_id            bigint NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    house_id             smallint NOT NULL REFERENCES house(id),
    term_cycle_id        bigint NOT NULL REFERENCES term_cycle(id),
    questions_asked      int,                 -- NULL = not reported (distinct from 0 = reported none)
    debates_participated int,
    private_member_bills int,
    period_start         date,                -- PRS "data corresponds to the period from …"
    period_end           date,                -- … to <as-of date> (data currency)
    source_ref_id        bigint REFERENCES source_ref(id) ON DELETE SET NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (person_id, term_cycle_id)         -- one scorecard per MP per term (idempotent upsert key)
);

CREATE INDEX parliamentary_activity_person_idx ON parliamentary_activity (person_id);
