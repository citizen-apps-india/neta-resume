"""ECI Files phase 4: person grouping, photos, selections and departures.

Revision ID: eci_files_people_0007
Revises: eci_files_states_0006
Create Date: 2026-09-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "eci_files_people_0007"
down_revision: Union[str, Sequence[str], None] = "eci_files_states_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ROLE_GROUPS = ("commission", "secretariat", "state", "named")
_REGIME_KEYS = ("convention", "baranwal", "act_2023")
_SELECTION_METHODS = ("executive_appointment", "elevation_of_senior_ec", "selection_committee")
_SELECTION_PARTS = (
    "appointed",
    "recommended",
    "proposed",
    "voted_with_majority",
    "dissented",
    "search_chair",
)
_DEPARTURE_HOW = ("resigned", "tenure_ended")
_LICENCE_REVIEW = ("reviewed", "uploader_asserted")


def upgrade() -> None:
    op.add_column(
        "eci_file_person",
        sa.Column(
            "role_group",
            sa.Text(),
            nullable=False,
            server_default="named",
        ),
    )
    op.create_check_constraint(
        "ck_eci_file_person_role_group",
        "eci_file_person",
        "role_group IN ({})".format(", ".join(f"'{v}'" for v in _ROLE_GROUPS)),
    )
    op.add_column(
        "eci_file_person",
        sa.Column("group_rank", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "eci_file_person",
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("eci_file_person", sa.Column("first_from", sa.Date(), nullable=True))
    op.add_column("eci_file_person", sa.Column("last_to", sa.Date(), nullable=True))
    op.create_index(
        "ix_eci_file_person_role_group_rank",
        "eci_file_person",
        ["role_group", "group_rank"],
    )

    op.create_table(
        "eci_file_person_media",
        sa.Column("person_slug", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("source_page", sa.Text(), nullable=False),
        sa.Column("original_source", sa.Text(), nullable=True),
        sa.Column("original_publisher", sa.Text(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("photo_date", sa.Date(), nullable=True),
        sa.Column("licence", sa.Text(), nullable=False),
        sa.Column("licence_url", sa.Text(), nullable=False),
        sa.Column("licence_review", sa.Text(), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.Column("self_host", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "licence_review IN ({})".format(", ".join(f"'{v}'" for v in _LICENCE_REVIEW)),
            name="ck_eci_file_person_media_licence_review",
        ),
        sa.ForeignKeyConstraint(["person_slug"], ["eci_file_person.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("person_slug"),
    )

    op.create_table(
        "eci_file_selection_regime",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=True),
        sa.Column("to_date", sa.Date(), nullable=True),
        sa.Column("rule", sa.Text(), nullable=False),
        sa.Column(
            "panel", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "entry_ids", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "key IN ({})".format(", ".join(f"'{v}'" for v in _REGIME_KEYS)),
            name="ck_eci_file_selection_regime_key",
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "eci_file_selection",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("date_precision", sa.Text(), nullable=False),
        sa.Column("date_meaning", sa.Text(), nullable=True),
        sa.Column("regime", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column(
            "appointed",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "members",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("search", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "dissent",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "entry_ids", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "date_precision IN ('day','month','year')",
            name="ck_eci_file_selection_date_precision",
        ),
        sa.CheckConstraint(
            "method IN ({})".format(", ".join(f"'{v}'" for v in _SELECTION_METHODS)),
            name="ck_eci_file_selection_method",
        ),
        sa.ForeignKeyConstraint(["regime"], ["eci_file_selection_regime.key"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "eci_file_selection_person",
        sa.Column("selection_id", sa.Text(), nullable=False),
        sa.Column("person_slug", sa.Text(), nullable=False),
        sa.Column("part", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "part IN ({})".format(", ".join(f"'{v}'" for v in _SELECTION_PARTS)),
            name="ck_eci_file_selection_person_part",
        ),
        sa.ForeignKeyConstraint(
            ["selection_id"], ["eci_file_selection.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["person_slug"], ["eci_file_person.slug"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("selection_id", "person_slug", "part"),
    )
    op.create_index(
        "ix_eci_file_selection_person_person_slug",
        "eci_file_selection_person",
        ["person_slug"],
    )

    op.create_table(
        "eci_file_departure",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("person_slug", sa.Text(), nullable=False),
        sa.Column("office", sa.Text(), nullable=False),
        sa.Column("how", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "entry_ids", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False
        ),
        sa.CheckConstraint(
            "how IN ({})".format(", ".join(f"'{v}'" for v in _DEPARTURE_HOW)),
            name="ck_eci_file_departure_how",
        ),
        sa.ForeignKeyConstraint(["person_slug"], ["eci_file_person.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("eci_file_departure")
    op.drop_index(
        "ix_eci_file_selection_person_person_slug", table_name="eci_file_selection_person"
    )
    op.drop_table("eci_file_selection_person")
    op.drop_table("eci_file_selection")
    op.drop_table("eci_file_selection_regime")
    op.drop_table("eci_file_person_media")

    op.drop_index("ix_eci_file_person_role_group_rank", table_name="eci_file_person")
    op.drop_column("eci_file_person", "last_to")
    op.drop_column("eci_file_person", "first_from")
    op.drop_column("eci_file_person", "is_current")
    op.drop_column("eci_file_person", "group_rank")
    op.drop_constraint("ck_eci_file_person_role_group", "eci_file_person", type_="check")
    op.drop_column("eci_file_person", "role_group")
