"""ECI Files phase 5: objections, charge-and-answer pairs, rule diffs and court cases.

Revision ID: eci_files_views_0008
Revises: eci_files_people_0007
Create Date: 2026-09-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "eci_files_views_0008"
down_revision: Union[str, Sequence[str], None] = "eci_files_people_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PAIR_ITEM_ROLES = ("response", "record", "related", "same")
_TEXT_STATUSES = ("verbatim", "quoted in reporting", "paraphrased from reporting")
_CASE_SHORT_STATUSES = ("pending", "disposed", "referred")
_CASE_ITEM_ROLES = (
    "order",
    "judgment",
    "hearing",
    "filing",
    "listing",
    "recusal",
    "compliance",
    "related",
)


def _in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "eci_file_objection",
        sa.Column("n", sa.SmallInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("date_precision", sa.Text(), nullable=False),
        sa.Column("concerns", sa.Text(), nullable=False),
        sa.Column("followed_by", sa.Text(), nullable=True),
        sa.Column("public", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint("n > 0", name="ck_eci_file_objection_n"),
        sa.CheckConstraint(
            "date_precision IN ('day','month','year')",
            name="ck_eci_file_objection_date_precision",
        ),
        sa.PrimaryKeyConstraint("n"),
    )

    op.create_table(
        "eci_file_objection_person",
        sa.Column("n", sa.SmallInteger(), nullable=False),
        sa.Column("person_slug", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(["n"], ["eci_file_objection.n"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_slug"], ["eci_file_person.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("n", "person_slug"),
    )

    op.create_table(
        "eci_file_objection_entry",
        sa.Column("n", sa.SmallInteger(), nullable=False),
        sa.Column("entry_id", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(["n"], ["eci_file_objection.n"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("n", "entry_id"),
    )
    op.create_index(
        "ix_eci_file_objection_entry_entry_id", "eci_file_objection_entry", ["entry_id"]
    )

    op.create_table(
        "eci_file_objection_meta",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("missing", sa.SmallInteger(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("report_entry_id", sa.Text(), nullable=True),
        sa.Column("response_entry_id", sa.Text(), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_eci_file_objection_meta_id"),
        sa.CheckConstraint("missing >= 0", name="ck_eci_file_objection_meta_missing"),
        sa.ForeignKeyConstraint(
            ["report_entry_id"], ["eci_file_entry.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["response_entry_id"], ["eci_file_entry.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "eci_file_pair",
        sa.Column("charge_id", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["charge_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("charge_id"),
        sa.UniqueConstraint("position", name="uq_eci_file_pair_position"),
    )

    op.create_table(
        "eci_file_pair_item",
        sa.Column("charge_id", sa.Text(), nullable=False),
        sa.Column("entry_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("why", sa.Text(), nullable=True),
        sa.CheckConstraint(
            f"role IN ({_in_list(_PAIR_ITEM_ROLES)})", name="ck_eci_file_pair_item_role"
        ),
        sa.ForeignKeyConstraint(["charge_id"], ["eci_file_pair.charge_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("charge_id", "entry_id", "role"),
    )
    op.create_index("ix_eci_file_pair_item_entry_id", "eci_file_pair_item", ["entry_id"])

    op.create_table(
        "eci_file_unpaired_response",
        sa.Column("response_entry_id", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["response_entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("response_entry_id"),
    )

    op.create_table(
        "eci_file_rule_diff",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("rule_entry_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("document", sa.Text(), nullable=False),
        sa.Column("before_label", sa.Text(), nullable=False),
        sa.Column("after_label", sa.Text(), nullable=False),
        sa.Column("before_lines", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("after_lines", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("before_status", sa.Text(), nullable=False),
        sa.Column("after_status", sa.Text(), nullable=False),
        sa.Column("text_status", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "quoted_lines_before",
            postgresql.ARRAY(sa.SmallInteger()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "quoted_lines_after",
            postgresql.ARRAY(sa.SmallInteger()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("source_urls", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint("id ~ '^[a-z0-9-]+$'", name="ck_eci_file_rule_diff_id"),
        sa.CheckConstraint(
            f"before_status IN ({_in_list(_TEXT_STATUSES)})",
            name="ck_eci_file_rule_diff_before_status",
        ),
        sa.CheckConstraint(
            f"after_status IN ({_in_list(_TEXT_STATUSES)})",
            name="ck_eci_file_rule_diff_after_status",
        ),
        sa.CheckConstraint(
            f"text_status IN ({_in_list(_TEXT_STATUSES)})",
            name="ck_eci_file_rule_diff_text_status",
        ),
        sa.CheckConstraint(
            "cardinality(source_urls) >= 1", name="ck_eci_file_rule_diff_source_urls"
        ),
        sa.ForeignKeyConstraint(["rule_entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("position", name="uq_eci_file_rule_diff_position"),
    )
    op.create_index("ix_eci_file_rule_diff_rule_entry_id", "eci_file_rule_diff", ["rule_entry_id"])

    op.create_table(
        "eci_file_rule_diff_entry",
        sa.Column("diff_id", sa.Text(), nullable=False),
        sa.Column("entry_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["diff_id"], ["eci_file_rule_diff.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("diff_id", "entry_id"),
    )
    op.create_index(
        "ix_eci_file_rule_diff_entry_entry_id", "eci_file_rule_diff_entry", ["entry_id"]
    )

    op.create_table(
        "eci_file_case",
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("short_name", sa.Text(), nullable=False),
        sa.Column("case_entry_id", sa.Text(), nullable=False),
        sa.Column("court", sa.Text(), nullable=False),
        sa.Column("short_status", sa.Text(), nullable=False),
        sa.Column("status_note", sa.Text(), nullable=True),
        sa.Column(
            "parties",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.CheckConstraint("slug ~ '^[a-z0-9-]+$'", name="ck_eci_file_case_slug"),
        sa.CheckConstraint(
            f"short_status IN ({_in_list(_CASE_SHORT_STATUSES)})",
            name="ck_eci_file_case_short_status",
        ),
        sa.ForeignKeyConstraint(["case_entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("slug"),
        sa.UniqueConstraint("position", name="uq_eci_file_case_position"),
        sa.UniqueConstraint("case_entry_id", name="uq_eci_file_case_case_entry_id"),
    )

    op.create_table(
        "eci_file_case_item",
        sa.Column("case_slug", sa.Text(), nullable=False),
        sa.Column("entry_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            f"role IN ({_in_list(_CASE_ITEM_ROLES)})", name="ck_eci_file_case_item_role"
        ),
        sa.ForeignKeyConstraint(["case_slug"], ["eci_file_case.slug"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entry_id"], ["eci_file_entry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("case_slug", "entry_id"),
        sa.UniqueConstraint("entry_id", name="uq_eci_file_case_item_entry_id"),
    )


def downgrade() -> None:
    op.drop_table("eci_file_case_item")
    op.drop_table("eci_file_case")
    op.drop_index("ix_eci_file_rule_diff_entry_entry_id", table_name="eci_file_rule_diff_entry")
    op.drop_table("eci_file_rule_diff_entry")
    op.drop_index("ix_eci_file_rule_diff_rule_entry_id", table_name="eci_file_rule_diff")
    op.drop_table("eci_file_rule_diff")
    op.drop_table("eci_file_unpaired_response")
    op.drop_index("ix_eci_file_pair_item_entry_id", table_name="eci_file_pair_item")
    op.drop_table("eci_file_pair_item")
    op.drop_table("eci_file_pair")
    op.drop_table("eci_file_objection_meta")
    op.drop_index(
        "ix_eci_file_objection_entry_entry_id", table_name="eci_file_objection_entry"
    )
    op.drop_table("eci_file_objection_entry")
    op.drop_table("eci_file_objection_person")
    op.drop_table("eci_file_objection")
