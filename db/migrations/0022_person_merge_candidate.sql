-- 0022: the cross-house identity-stitcher's review queue + audit. Each row is a proposed merge of two
-- person records (ordered lo<hi so the pair is stable regardless of scan direction). The stitcher
-- auto-merges only the near-certain band; everything else is 'pending' for a human to accept/reject.
-- 'rejected' rows are the SUPPRESSION list — a pair is never re-proposed at the same rule_version.
--
-- FKs are ON DELETE SET NULL (not CASCADE) so an accepted/auto-merged audit row SURVIVES the loser's
-- deletion (the merged-away side nulls out; evidence.pair retains both original ids). Rows with a null
-- side are stale and ignored by the stitcher/review.

CREATE TABLE person_merge_candidate (
    id           bigserial PRIMARY KEY,
    person_lo    bigint REFERENCES person(id) ON DELETE SET NULL,   -- min(id) of the pair
    person_hi    bigint REFERENCES person(id) ON DELETE SET NULL,   -- max(id) of the pair
    score        numeric(5, 4) NOT NULL,
    band         text NOT NULL CHECK (band IN ('auto_merge', 'review', 'reject')),
    evidence     jsonb NOT NULL,                    -- per-signal breakdown + {"pair":[lo,hi]}
    rule_version text NOT NULL,                     -- scorer version, e.g. 'stitch-v1'
    status       text NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'accepted', 'rejected', 'auto_merged')),
    decided_by   text,                              -- email / 'auto'
    decided_at   timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (person_lo, person_hi)                   -- one live proposal per unordered pair
);

CREATE INDEX person_merge_candidate_status_idx ON person_merge_candidate (status);
