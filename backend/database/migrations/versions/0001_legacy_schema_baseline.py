"""Record the legacy SQL schema through db/migrations/0030.

Revision ID: legacy_0030
Revises: None
Create Date: 2026-07-31
"""

from typing import Sequence, Union

revision: str = "legacy_0030"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """The existing SQL migration runner has already created this schema."""


def downgrade() -> None:
    """The frozen legacy schema is deliberately not dropped by Alembic."""
