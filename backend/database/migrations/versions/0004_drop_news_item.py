"""Drop the retired In The News headlines and their provenance rows.

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
    op.execute("DROP TABLE IF EXISTS news_item")
    # Only the Google News collector minted 'google-news:' refs. The source row itself stays: the
    # curated party-switch narratives still cite 'news' (trust tier 3) with 'switch-' refs.
    op.execute(
        """
        DELETE FROM source_ref sr
        USING source s
        WHERE sr.source_id = s.id
          AND s.code = 'news'
          AND sr.native_id LIKE 'google-news:%'
          AND NOT EXISTS (SELECT 1 FROM fact_source fs WHERE fs.source_ref_id = sr.id)
        """
    )


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
