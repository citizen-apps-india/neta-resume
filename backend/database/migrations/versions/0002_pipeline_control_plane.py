"""Add ingestion control-plane tables.

Revision ID: pipeline_control_0001
Revises: legacy_0030
Create Date: 2026-07-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "pipeline_control_0001"
down_revision: Union[str, Sequence[str], None] = "legacy_0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

config_revision_operation = postgresql.ENUM(
    "patch",
    "reset",
    name="pipeline_config_revision_operation",
    create_type=False,
)
run_request_type = postgresql.ENUM(
    "run_now",
    "retry",
    "replay",
    "backfill",
    name="pipeline_run_request_type",
    create_type=False,
)
run_request_status = postgresql.ENUM(
    "pending",
    "accepted",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    name="pipeline_run_request_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    config_revision_operation.create(bind, checkfirst=True)
    run_request_type.create(bind, checkfirst=True)
    run_request_status.create(bind, checkfirst=True)

    op.create_table(
        "pipeline_source_state",
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.SmallInteger(), nullable=True),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("git_commit_sha", sa.String(length=255), nullable=False),
        sa.Column(
            "admin_overrides",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("effective_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("paused", sa.Boolean(), nullable=False),
        sa.Column("frequency_seconds", sa.Integer(), nullable=True),
        sa.Column("concurrency_limit", sa.Integer(), nullable=False),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False),
        sa.Column("retry_limit", sa.Integer(), nullable=False),
        sa.Column("active_revision", sa.BigInteger(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quarantined_by", sa.Text(), nullable=True),
        sa.Column("quarantined_reason", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "source_key LIKE '%.%'", name="ck_pipeline_source_state_key"
        ),
        sa.CheckConstraint(
            "length(manifest_hash) = 64",
            name="ck_pipeline_source_state_manifest_hash",
        ),
        sa.CheckConstraint(
            "length(trim(git_commit_sha)) > 0",
            name="ck_pipeline_source_state_git_commit",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(admin_overrides) = 'object'",
            name="ck_pipeline_source_state_admin_overrides",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(effective_config) = 'object'",
            name="ck_pipeline_source_state_effective_config",
        ),
        sa.CheckConstraint(
            "frequency_seconds IS NULL OR frequency_seconds >= 30",
            name="ck_pipeline_source_state_frequency",
        ),
        sa.CheckConstraint(
            "concurrency_limit >= 1", name="ck_pipeline_source_state_concurrency"
        ),
        sa.CheckConstraint(
            "rate_limit_per_minute >= 1", name="ck_pipeline_source_state_rate_limit"
        ),
        sa.CheckConstraint(
            "retry_limit >= 0", name="ck_pipeline_source_state_retry_limit"
        ),
        sa.CheckConstraint(
            "active_revision >= 0", name="ck_pipeline_source_state_active_revision"
        ),
        sa.CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_pipeline_source_state_consecutive_failures",
        ),
        sa.CheckConstraint(
            "(quarantined_at IS NULL AND quarantined_by IS NULL "
            "AND quarantined_reason IS NULL) OR "
            "(quarantined_at IS NOT NULL AND quarantined_by IS NOT NULL "
            "AND quarantined_reason IS NOT NULL)",
            name="ck_pipeline_source_state_quarantine",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["source.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pipeline_source_state_source_key",
        "pipeline_source_state",
        ["source_key"],
        unique=True,
    )
    op.create_index(
        "ix_pipeline_source_state_source_id",
        "pipeline_source_state",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_source_state_schedulable",
        "pipeline_source_state",
        ["next_run_at"],
        unique=False,
        postgresql_where=sa.text(
            "enabled AND NOT paused AND quarantined_at IS NULL AND next_run_at IS NOT NULL"
        ),
    )

    op.create_table(
        "pipeline_source_config_revision",
        sa.Column("source_state_id", sa.Integer(), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("operation", config_revision_operation, nullable=False),
        sa.Column("patch", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("effective_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("git_commit_sha", sa.String(length=255), nullable=False),
        sa.Column("changed_by", sa.Text(), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_pipeline_config_revision_number"
        ),
        sa.CheckConstraint(
            "(operation = 'patch' AND patch <> '{}'::jsonb) OR "
            "(operation = 'reset' AND patch = '{}'::jsonb)",
            name="ck_pipeline_config_revision_payload",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(patch) = 'object'",
            name="ck_pipeline_config_revision_patch_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(effective_config) = 'object'",
            name="ck_pipeline_config_revision_effective_config",
        ),
        sa.CheckConstraint(
            "length(trim(changed_by)) > 0",
            name="ck_pipeline_config_revision_changed_by",
        ),
        sa.CheckConstraint(
            "length(trim(change_reason)) >= 3",
            name="ck_pipeline_config_revision_reason",
        ),
        sa.ForeignKeyConstraint(["source_state_id"], ["pipeline_source_state.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_state_id", "revision", name="uq_pipeline_config_revision"
        ),
    )
    op.create_index(
        "ix_pipeline_source_config_revision_source_state_id",
        "pipeline_source_config_revision",
        ["source_state_id"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_config_revision_history",
        "pipeline_source_config_revision",
        ["source_state_id", sa.literal_column("revision DESC")],
        unique=False,
    )

    op.create_table(
        "pipeline_run_request",
        sa.Column("source_state_id", sa.Integer(), nullable=False),
        sa.Column("request_type", run_request_type, nullable=False),
        sa.Column("status", run_request_status, nullable=False),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("requested_by", sa.Text(), nullable=False),
        sa.Column("request_reason", sa.Text(), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(parameters) = 'object'",
            name="ck_pipeline_run_request_parameters",
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="ck_pipeline_run_request_idempotency_key",
        ),
        sa.CheckConstraint(
            "length(trim(requested_by)) > 0",
            name="ck_pipeline_run_request_requested_by",
        ),
        sa.CheckConstraint(
            "length(trim(request_reason)) >= 3",
            name="ck_pipeline_run_request_reason",
        ),
        sa.ForeignKeyConstraint(["source_state_id"], ["pipeline_source_state.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_state_id",
            "idempotency_key",
            name="uq_pipeline_run_request_idempotency",
        ),
    )
    op.create_index(
        "ix_pipeline_run_request_source_state_id",
        "pipeline_run_request",
        ["source_state_id"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_run_request_pending",
        "pipeline_run_request",
        ["requested_at", "id"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_pipeline_run_request_source_history",
        "pipeline_run_request",
        ["source_state_id", sa.literal_column("requested_at DESC")],
        unique=False,
    )

    op.create_table(
        "pipeline_audit_event",
        sa.Column("source_state_id", sa.Integer(), nullable=True),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.CheckConstraint(
            "length(trim(actor)) > 0", name="ck_pipeline_audit_event_actor"
        ),
        sa.CheckConstraint(
            "length(trim(action)) > 0", name="ck_pipeline_audit_event_action"
        ),
        sa.CheckConstraint(
            "length(trim(entity_type)) > 0",
            name="ck_pipeline_audit_event_entity_type",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_pipeline_audit_event_payload",
        ),
        sa.ForeignKeyConstraint(
            ["source_state_id"], ["pipeline_source_state.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pipeline_audit_event_source_state_id",
        "pipeline_audit_event",
        ["source_state_id"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_audit_event_source_history",
        "pipeline_audit_event",
        [
            "source_state_id",
            sa.literal_column("occurred_at DESC"),
            sa.literal_column("id DESC"),
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pipeline_audit_event_source_history", table_name="pipeline_audit_event"
    )
    op.drop_index(
        "ix_pipeline_audit_event_source_state_id", table_name="pipeline_audit_event"
    )
    op.drop_table("pipeline_audit_event")
    op.drop_index(
        "ix_pipeline_run_request_source_history", table_name="pipeline_run_request"
    )
    op.drop_index("ix_pipeline_run_request_pending", table_name="pipeline_run_request")
    op.drop_index(
        "ix_pipeline_run_request_source_state_id", table_name="pipeline_run_request"
    )
    op.drop_table("pipeline_run_request")
    op.drop_index(
        "ix_pipeline_config_revision_history",
        table_name="pipeline_source_config_revision",
    )
    op.drop_index(
        "ix_pipeline_source_config_revision_source_state_id",
        table_name="pipeline_source_config_revision",
    )
    op.drop_table("pipeline_source_config_revision")
    op.drop_index(
        "ix_pipeline_source_state_schedulable", table_name="pipeline_source_state"
    )
    op.drop_index(
        "ix_pipeline_source_state_source_id", table_name="pipeline_source_state"
    )
    op.drop_index(
        "ix_pipeline_source_state_source_key", table_name="pipeline_source_state"
    )
    op.drop_table("pipeline_source_state")

    bind = op.get_bind()
    run_request_status.drop(bind, checkfirst=True)
    run_request_type.drop(bind, checkfirst=True)
    config_revision_operation.drop(bind, checkfirst=True)
