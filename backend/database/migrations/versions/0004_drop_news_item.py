"""Drop the retired In The News headlines table.

Revision ID: drop_news_item_0003
Revises: pipeline_execution_0002
Create Date: 2026-09-24
"""

from typing import Sequence, Union

from alembic import op

revision: str = "drop_news_item_0003"
down_revision: Union[str, Sequence[str], None] = "pipeline_execution_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dropping news_item takes ACCESS EXCLUSIVE on person and source_ref (its FK targets), which
    # queues every public profile read behind it. Fail fast rather than wait on a lock holder.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("DROP TABLE IF EXISTS news_item")
    # The 'google-news:' source_ref rows are left in place, unreferenced. Deleting them runs an FK
    # check against ~16 unindexed referencing columns per row while the lock above is held: on
    # 2026-09-24 that stalled profile reads for 12 minutes before the run was cancelled.


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS news_item (
            id            bigserial PRIMARY KEY,
            person_id     bigint NOT NULL REFERENCES person(id),
            source_ref_id bigint NOT NULL REFERENCES source_ref(id),
            title         text NOT NULL,
            snippet       text,
            url           text NOT NULL,
            publisher     text,
            published_at  date,
            fetched_at    timestamptz NOT NULL DEFAULT now(),
            UNIQUE (person_id, url)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS news_item_person_idx ON news_item (person_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS news_item_published_idx ON news_item (published_at DESC)"
    )
