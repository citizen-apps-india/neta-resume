"""ECI Files redesign phase 1: lanes, state figures and the curated headline.

Revision ID: eci_files_lane_0005
Revises: eci_files_0004
Create Date: 2026-09-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "eci_files_lane_0005"
down_revision: Union[str, Sequence[str], None] = "eci_files_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LANES = ("responses", "claims", "courts", "inside", "commission")
_STAGES = ("before", "draft", "final", "appeals_filed", "appeals_pending", "restored")


def upgrade() -> None:
    op.add_column(
        "eci_file_entry",
        sa.Column("lane", sa.Text(), nullable=False, server_default="commission"),
    )
    op.create_check_constraint(
        "ck_eci_file_entry_lane", "eci_file_entry", "lane IN ({})".format(", ".join(f"'{v}'" for v in _LANES))
    )
    op.create_index("ix_eci_file_entry_lane_date", "eci_file_entry", ["lane", "date"])

    op.create_table(
        "eci_file_state_stage",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("electors", sa.BigInteger(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=True),
        sa.Column("computed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source_entry_id", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("tier", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "stage IN ({})".format(", ".join(f"'{v}'" for v in _STAGES)),
            name="ck_eci_file_state_stage_stage",
        ),
        sa.CheckConstraint("tier IN (1,2,3)", name="ck_eci_file_state_stage_tier"),
        sa.ForeignKeyConstraint(["source_entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eci_file_state_stage_state", "eci_file_state_stage", ["state"])

    op.create_table(
        "eci_file_headline",
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("source_label", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("entry_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("position"),
    )

    op.create_table(
        "eci_file_key_moment",
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("entry_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("position"),
    )


def downgrade() -> None:
    op.drop_table("eci_file_key_moment")
    op.drop_table("eci_file_headline")
    op.drop_table("eci_file_state_stage")
    op.drop_index("ix_eci_file_entry_lane_date", table_name="eci_file_entry")
    op.drop_constraint("ck_eci_file_entry_lane", "eci_file_entry", type_="check")
    op.drop_column("eci_file_entry", "lane")
