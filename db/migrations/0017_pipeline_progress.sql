-- Progress ledger for the self-driving state rollout (onboard-driver -> `neta rollout`).
-- Lets the depth (backfill) phase be resumable across time-boxed cron jobs: each completed
-- historical-lookup records a 'backfill:<cycle>' task here, so re-runs skip finished work.
-- (Base-onboard "done" is inferred from office_term presence, so it needs no marker.)

CREATE TABLE IF NOT EXISTS pipeline_progress (
    task     text PRIMARY KEY,                       -- e.g. 'backfill:WB_VS2016'
    done_at  timestamptz NOT NULL DEFAULT now()
);
