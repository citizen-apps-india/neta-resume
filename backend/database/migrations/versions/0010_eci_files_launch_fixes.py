"""ECI Files pre-launch fixes: a directly-reported left-off stage, West Bengal's adjudication/Form 7
split, and a pair classification (defence/analysis) excluded from the charge/no-response counts.

Revision ID: eci_files_launch_0009
Revises: eci_files_views_0008
Create Date: 2026-09-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "eci_files_launch_0009"
down_revision: Union[str, Sequence[str], None] = "eci_files_views_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_STAGES = ("before", "draft", "final", "appeals_filed", "appeals_pending", "restored")
_NEW_STAGES = _OLD_STAGES + ("left_off", "under_adjudication", "form7_deletions")
_OLD_PAIR_KINDS: tuple[str, ...] = ()
_NEW_PAIR_KINDS = ("charge", "defence", "analysis")


def _in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.drop_constraint(
        "ck_eci_file_state_stage_stage", "eci_file_state_stage", type_="check"
    )
    op.create_check_constraint(
        "ck_eci_file_state_stage_stage",
        "eci_file_state_stage",
        f"stage IN ({_in_list(_NEW_STAGES)})",
    )

    op.add_column(
        "eci_file_pair",
        sa.Column("kind", sa.Text(), server_default="charge", nullable=False),
    )
    op.create_check_constraint(
        "ck_eci_file_pair_kind",
        "eci_file_pair",
        f"kind IN ({_in_list(_NEW_PAIR_KINDS)})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_eci_file_pair_kind", "eci_file_pair", type_="check")
    op.drop_column("eci_file_pair", "kind")

    op.drop_constraint(
        "ck_eci_file_state_stage_stage", "eci_file_state_stage", type_="check"
    )
    op.create_check_constraint(
        "ck_eci_file_state_stage_stage",
        "eci_file_state_stage",
        f"stage IN ({_in_list(_OLD_STAGES)})",
    )
