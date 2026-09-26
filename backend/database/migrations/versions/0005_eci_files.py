"""Add ECI Files: a sourced, dated record of the Election Commission of India.

Revision ID: eci_files_0004
Revises: drop_news_item_0003
Create Date: 2026-09-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "eci_files_0004"
down_revision: Union[str, Sequence[str], None] = "drop_news_item_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eci_file_entry",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("area", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("date_precision", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attributed_to", sa.Text(), nullable=True),
        sa.Column("topics", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("states", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column(
            "figures", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column(
            "details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("response_to", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("check_status", sa.Text(), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "kind IN ('event','person','rule','figure','case','statement')",
            name="ck_eci_file_entry_kind",
        ),
        sa.CheckConstraint(
            "date_precision IN ('day','month','year')", name="ck_eci_file_entry_date_precision"
        ),
        sa.CheckConstraint(
            "status IN ('documented','reported','claim','response')", name="ck_eci_file_entry_status"
        ),
        sa.CheckConstraint(
            "check_status IN ('checked','unchecked')", name="ck_eci_file_entry_check_status"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eci_file_entry_date", "eci_file_entry", ["date"])
    op.create_index(
        "ix_eci_file_entry_topics", "eci_file_entry", ["topics"], postgresql_using="gin"
    )

    op.create_table(
        "eci_file_person",
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("profile_entry_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["profile_entry_id"], ["eci_file_entry.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("slug"),
    )

    op.create_table(
        "eci_file_entry_person",
        sa.Column("entry_id", sa.Text(), nullable=False),
        sa.Column("person_slug", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_slug"], ["eci_file_person.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entry_id", "person_slug"),
    )
    op.create_index(
        "ix_eci_file_entry_person_person_slug", "eci_file_entry_person", ["person_slug"]
    )

    op.create_table(
        "eci_file_citation",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entry_id", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("source_ref_id", sa.BigInteger(), nullable=False),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("published", sa.Date(), nullable=True),
        sa.Column("tier", sa.SmallInteger(), nullable=False),
        sa.Column("archive_url", sa.Text(), nullable=True),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.CheckConstraint("tier IN (1,2,3)", name="ck_eci_file_citation_tier"),
        sa.CheckConstraint(
            "quote IS NULL OR length(quote) <= 200", name="ck_eci_file_citation_quote_length"
        ),
        sa.ForeignKeyConstraint(["entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_ref_id"], ["source_ref.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entry_id", "position"),
    )
    op.create_index("ix_eci_file_citation_entry_id", "eci_file_citation", ["entry_id"])
    op.create_index("ix_eci_file_citation_source_ref_id", "eci_file_citation", ["source_ref_id"])


def downgrade() -> None:
    op.drop_table("eci_file_citation")
    op.drop_table("eci_file_entry_person")
    op.drop_table("eci_file_person")
    op.drop_table("eci_file_entry")
