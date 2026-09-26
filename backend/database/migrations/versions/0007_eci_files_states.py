"""ECI Files phase 3: regions, per-state phase/exercise/notes, and national figures.

Revision ID: eci_files_states_0006
Revises: eci_files_lane_0005
Create Date: 2026-09-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "eci_files_states_0006"
down_revision: Union[str, Sequence[str], None] = "eci_files_lane_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NATIONAL_GROUPS = ("all", "phase_1", "phase_2", "phase_3")
_NATIONAL_MEASURES = ("before", "draft", "final", "left_off", "net_fall")


def upgrade() -> None:
    op.create_table(
        "eci_file_region",
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column(
            "aliases",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.CheckConstraint("code ~ '^[A-Z]{2}$'", name="ck_eci_file_region_code"),
        sa.CheckConstraint("kind IN ('state','ut')", name="ck_eci_file_region_kind"),
        sa.PrimaryKeyConstraint("slug"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "eci_file_state",
        sa.Column("region_slug", sa.Text(), nullable=False),
        sa.Column("phase", sa.SmallInteger(), nullable=True),
        sa.Column("exercise", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("phase IS NULL OR phase IN (1,2,3)", name="ck_eci_file_state_phase"),
        sa.CheckConstraint(
            "exercise IS NULL OR exercise IN ('sir','special_revision')",
            name="ck_eci_file_state_exercise",
        ),
        sa.ForeignKeyConstraint(["region_slug"], ["eci_file_region.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_slug"),
    )

    # Full-replace derived data: clear before altering, so a stale `state` text column can't
    # collide with the new NOT NULL `region_slug`. Re-run `neta eci-files` after upgrading.
    op.execute("DELETE FROM eci_file_state_stage")

    op.drop_index("ix_eci_file_state_stage_state", table_name="eci_file_state_stage")
    op.drop_column("eci_file_state_stage", "state")
    op.add_column(
        "eci_file_state_stage",
        sa.Column("region_slug", sa.Text(), nullable=False),
    )
    op.add_column("eci_file_state_stage", sa.Column("note", sa.Text(), nullable=True))
    op.add_column(
        "eci_file_state_stage",
        sa.Column("approx", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_foreign_key(
        "fk_eci_file_state_stage_region_slug",
        "eci_file_state_stage",
        "eci_file_state",
        ["region_slug"],
        ["region_slug"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_eci_file_state_stage_region_stage",
        "eci_file_state_stage",
        ["region_slug", "stage"],
    )
    op.create_index(
        "ix_eci_file_state_stage_region", "eci_file_state_stage", ["region_slug"]
    )

    op.create_table(
        "eci_file_national_figure",
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("grp", sa.Text(), nullable=False),
        sa.Column("measure", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("electors", sa.BigInteger(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=True),
        sa.Column("computed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("approx", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source_entry_id", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "grp IN ({})".format(", ".join(f"'{v}'" for v in _NATIONAL_GROUPS)),
            name="ck_eci_file_national_figure_grp",
        ),
        sa.CheckConstraint(
            "measure IN ({})".format(", ".join(f"'{v}'" for v in _NATIONAL_MEASURES)),
            name="ck_eci_file_national_figure_measure",
        ),
        sa.ForeignKeyConstraint(["source_entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("position"),
    )
    op.create_index(
        "ix_eci_file_national_figure_source_entry_id",
        "eci_file_national_figure",
        ["source_entry_id"],
    )

    op.create_index(
        "ix_eci_file_entry_states",
        "eci_file_entry",
        ["states"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_eci_file_entry_states", table_name="eci_file_entry")

    op.drop_index(
        "ix_eci_file_national_figure_source_entry_id", table_name="eci_file_national_figure"
    )
    op.drop_table("eci_file_national_figure")

    op.execute("DELETE FROM eci_file_state_stage")

    op.drop_index("ix_eci_file_state_stage_region", table_name="eci_file_state_stage")
    op.drop_constraint(
        "uq_eci_file_state_stage_region_stage", "eci_file_state_stage", type_="unique"
    )
    op.drop_constraint(
        "fk_eci_file_state_stage_region_slug", "eci_file_state_stage", type_="foreignkey"
    )
    op.drop_column("eci_file_state_stage", "approx")
    op.drop_column("eci_file_state_stage", "note")
    op.drop_column("eci_file_state_stage", "region_slug")
    # The table is empty at this point (rows deleted above), so a NOT NULL column with no
    # default can be added directly.
    op.add_column(
        "eci_file_state_stage",
        sa.Column("state", sa.Text(), nullable=False),
    )
    op.create_index("ix_eci_file_state_stage_state", "eci_file_state_stage", ["state"])

    op.drop_table("eci_file_state")
    op.drop_table("eci_file_region")
