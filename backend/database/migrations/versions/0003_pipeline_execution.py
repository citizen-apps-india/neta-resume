"""Add durable orchestration executions.

Revision ID: pipeline_execution_0002
Revises: pipeline_control_0001
Create Date: 2026-07-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "pipeline_execution_0002"
down_revision: Union[str, Sequence[str], None] = "pipeline_control_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

run_trigger = postgresql.ENUM(
    "scheduled",
    "run_now",
    "retry",
    "replay",
    "backfill",
    name="pipeline_run_trigger",
    create_type=False,
)
run_status = postgresql.ENUM(
    "pending",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    name="pipeline_run_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    run_trigger.create(bind, checkfirst=True)
    run_status.create(bind, checkfirst=True)

    op.create_table(
        "pipeline_run",
        sa.Column("source_state_id", sa.Integer(), nullable=False),
        sa.Column("run_request_id", sa.Integer(), nullable=True),
        sa.Column("run_key", sa.String(length=255), nullable=False),
        sa.Column("orchestrator_run_id", sa.String(length=255), nullable=True),
        sa.Column("trigger", run_trigger, nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("git_commit_sha", sa.String(length=255), nullable=False),
        sa.Column("config_revision", sa.BigInteger(), nullable=False),
        sa.Column("converter", sa.Text(), nullable=False),
        sa.Column("contract_version", sa.Text(), nullable=False),
        sa.Column("runtime_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("retry_limit", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(run_key)) > 0", name="ck_pipeline_run_key"),
        sa.CheckConstraint(
            "length(manifest_hash) = 64",
            name="ck_pipeline_run_manifest_hash",
        ),
        sa.CheckConstraint(
            "length(trim(git_commit_sha)) > 0",
            name="ck_pipeline_run_git_commit",
        ),
        sa.CheckConstraint(
            "length(trim(converter)) > 0",
            name="ck_pipeline_run_converter",
        ),
        sa.CheckConstraint(
            "length(trim(contract_version)) > 0",
            name="ck_pipeline_run_contract_version",
        ),
        sa.CheckConstraint(
            "config_revision >= 0",
            name="ck_pipeline_run_config_revision",
        ),
        sa.CheckConstraint("retry_limit >= 0", name="ck_pipeline_run_retry_limit"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_pipeline_run_attempt_count"),
        sa.CheckConstraint(
            "jsonb_typeof(runtime_config) = 'object'",
            name="ck_pipeline_run_runtime_config",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(parameters) = 'object'",
            name="ck_pipeline_run_parameters",
        ),
        sa.ForeignKeyConstraint(
            ["source_state_id"],
            ["pipeline_source_state.id"],
        ),
        sa.ForeignKeyConstraint(
            ["run_request_id"],
            ["pipeline_run_request.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_key"),
    )
    op.create_index(
        "ix_pipeline_run_source_state_id",
        "pipeline_run",
        ["source_state_id"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_run_run_request_id",
        "pipeline_run",
        ["run_request_id"],
        unique=True,
    )
    op.create_index(
        "ix_pipeline_run_orchestrator_run_id",
        "pipeline_run",
        ["orchestrator_run_id"],
        unique=True,
    )
    op.create_index(
        "ix_pipeline_run_dispatchable",
        "pipeline_run",
        ["created_at", "id"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_pipeline_run_source_history",
        "pipeline_run",
        [
            "source_state_id",
            sa.literal_column("created_at DESC"),
            sa.literal_column("id DESC"),
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_run_source_history", table_name="pipeline_run")
    op.drop_index("ix_pipeline_run_dispatchable", table_name="pipeline_run")
    op.drop_index("ix_pipeline_run_orchestrator_run_id", table_name="pipeline_run")
    op.drop_index("ix_pipeline_run_run_request_id", table_name="pipeline_run")
    op.drop_index("ix_pipeline_run_source_state_id", table_name="pipeline_run")
    op.drop_table("pipeline_run")

    bind = op.get_bind()
    run_status.drop(bind, checkfirst=True)
    run_trigger.drop(bind, checkfirst=True)
