"""SQLAlchemy models for the ingestion control plane."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from neta_core.pipeline.contracts import ConfigRevisionOperation

from neta_backend.database.base import Base, IntegerPrimaryKeyMixin, TimestampMixin

JsonObject = JSON().with_variant(JSONB(), "postgresql")


class PipelineRunRequestType(StrEnum):
    RUN_NOW = "run_now"
    RETRY = "retry"
    REPLAY = "replay"
    BACKFILL = "backfill"


class PipelineRunRequestStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineRunTrigger(StrEnum):
    SCHEDULED = "scheduled"
    RUN_NOW = "run_now"
    RETRY = "retry"
    REPLAY = "replay"
    BACKFILL = "backfill"


class PipelineRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_class]


class SourceRegistry(Base):
    """Minimal mapping of the legacy publisher-level source registry."""

    __tablename__ = "source"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(Text)
    trust_tier: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)


class PipelineSourceState(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pipeline_source_state"
    __table_args__ = (
        CheckConstraint("source_key LIKE '%.%'", name="ck_pipeline_source_state_key"),
        CheckConstraint(
            "length(manifest_hash) = 64", name="ck_pipeline_source_state_manifest_hash"
        ),
        CheckConstraint(
            "length(trim(git_commit_sha)) > 0", name="ck_pipeline_source_state_git_commit"
        ),
        CheckConstraint(
            "jsonb_typeof(admin_overrides) = 'object'",
            name="ck_pipeline_source_state_admin_overrides",
        ),
        CheckConstraint(
            "jsonb_typeof(effective_config) = 'object'",
            name="ck_pipeline_source_state_effective_config",
        ),
        CheckConstraint(
            "frequency_seconds IS NULL OR frequency_seconds >= 30",
            name="ck_pipeline_source_state_frequency",
        ),
        CheckConstraint(
            "concurrency_limit >= 1", name="ck_pipeline_source_state_concurrency"
        ),
        CheckConstraint(
            "rate_limit_per_minute >= 1", name="ck_pipeline_source_state_rate_limit"
        ),
        CheckConstraint("retry_limit >= 0", name="ck_pipeline_source_state_retry_limit"),
        CheckConstraint(
            "active_revision >= 0", name="ck_pipeline_source_state_active_revision"
        ),
        CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_pipeline_source_state_consecutive_failures",
        ),
        CheckConstraint(
            "(quarantined_at IS NULL AND quarantined_by IS NULL "
            "AND quarantined_reason IS NULL) OR "
            "(quarantined_at IS NOT NULL AND quarantined_by IS NOT NULL "
            "AND quarantined_reason IS NOT NULL)",
            name="ck_pipeline_source_state_quarantine",
        ),
        Index(
            "ix_pipeline_source_state_schedulable",
            "next_run_at",
            postgresql_where=text(
                "enabled AND NOT paused AND quarantined_at IS NULL AND next_run_at IS NOT NULL"
            ),
        ),
    )

    source_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    source_id: Mapped[int | None] = mapped_column(
        SmallInteger,
        ForeignKey("source.id", ondelete="SET NULL"),
        index=True,
    )
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    git_commit_sha: Mapped[str] = mapped_column(String(255), nullable=False)
    admin_overrides: Mapped[dict[str, Any]] = mapped_column(
        JsonObject,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    effective_config: Mapped[dict[str, Any]] = mapped_column(JsonObject, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    frequency_seconds: Mapped[int | None] = mapped_column(Integer)
    concurrency_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    retry_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    active_revision: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quarantined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quarantined_by: Mapped[str | None] = mapped_column(Text)
    quarantined_reason: Mapped[str | None] = mapped_column(Text)

    source: Mapped[SourceRegistry | None] = relationship()
    revisions: Mapped[list[PipelineSourceConfigRevision]] = relationship(
        back_populates="source_state",
        cascade="all, delete-orphan",
    )
    run_requests: Mapped[list[PipelineRunRequest]] = relationship(
        back_populates="source_state",
        cascade="all, delete-orphan",
    )
    runs: Mapped[list[PipelineRun]] = relationship(
        back_populates="source_state",
        cascade="all, delete-orphan",
    )
    audit_events: Mapped[list[PipelineAuditEvent]] = relationship(
        back_populates="source_state",
    )


class PipelineSourceConfigRevision(IntegerPrimaryKeyMixin, Base):
    __tablename__ = "pipeline_source_config_revision"
    __table_args__ = (
        UniqueConstraint("source_state_id", "revision", name="uq_pipeline_config_revision"),
        CheckConstraint("revision >= 1", name="ck_pipeline_config_revision_number"),
        CheckConstraint(
            "(operation = 'patch' AND patch <> '{}'::jsonb) OR "
            "(operation = 'reset' AND patch = '{}'::jsonb)",
            name="ck_pipeline_config_revision_payload",
        ),
        CheckConstraint(
            "jsonb_typeof(patch) = 'object'",
            name="ck_pipeline_config_revision_patch_object",
        ),
        CheckConstraint(
            "jsonb_typeof(effective_config) = 'object'",
            name="ck_pipeline_config_revision_effective_config",
        ),
        CheckConstraint(
            "length(trim(changed_by)) > 0",
            name="ck_pipeline_config_revision_changed_by",
        ),
        CheckConstraint(
            "length(trim(change_reason)) >= 3",
            name="ck_pipeline_config_revision_reason",
        ),
        Index(
            "ix_pipeline_config_revision_history",
            "source_state_id",
            text("revision DESC"),
        ),
    )

    source_state_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_source_state.id"), nullable=False, index=True
    )
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    operation: Mapped[ConfigRevisionOperation] = mapped_column(
        Enum(
            ConfigRevisionOperation,
            name="pipeline_config_revision_operation",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=ConfigRevisionOperation.PATCH,
    )
    patch: Mapped[dict[str, Any]] = mapped_column(JsonObject, nullable=False, default=dict)
    effective_config: Mapped[dict[str, Any]] = mapped_column(JsonObject, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    git_commit_sha: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_by: Mapped[str] = mapped_column(Text, nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    source_state: Mapped[PipelineSourceState] = relationship(back_populates="revisions")


class PipelineRunRequest(IntegerPrimaryKeyMixin, Base):
    __tablename__ = "pipeline_run_request"
    __table_args__ = (
        UniqueConstraint(
            "source_state_id",
            "idempotency_key",
            name="uq_pipeline_run_request_idempotency",
        ),
        CheckConstraint(
            "jsonb_typeof(parameters) = 'object'",
            name="ck_pipeline_run_request_parameters",
        ),
        CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="ck_pipeline_run_request_idempotency_key",
        ),
        CheckConstraint(
            "length(trim(requested_by)) > 0",
            name="ck_pipeline_run_request_requested_by",
        ),
        CheckConstraint(
            "length(trim(request_reason)) >= 3",
            name="ck_pipeline_run_request_reason",
        ),
        Index(
            "ix_pipeline_run_request_pending",
            "requested_at",
            "id",
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "ix_pipeline_run_request_source_history",
            "source_state_id",
            text("requested_at DESC"),
        ),
    )

    source_state_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_source_state.id"), nullable=False, index=True
    )
    request_type: Mapped[PipelineRunRequestType] = mapped_column(
        Enum(
            PipelineRunRequestType,
            name="pipeline_run_request_type",
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    status: Mapped[PipelineRunRequestStatus] = mapped_column(
        Enum(
            PipelineRunRequestStatus,
            name="pipeline_run_request_status",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=PipelineRunRequestStatus.PENDING,
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JsonObject,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_by: Mapped[str] = mapped_column(Text, nullable=False)
    request_reason: Mapped[str] = mapped_column(Text, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    source_state: Mapped[PipelineSourceState] = relationship(back_populates="run_requests")
    run: Mapped[PipelineRun | None] = relationship(back_populates="run_request")


class PipelineRun(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    """One durable scheduled or operator-requested orchestration execution."""

    __tablename__ = "pipeline_run"
    __table_args__ = (
        CheckConstraint("length(trim(run_key)) > 0", name="ck_pipeline_run_key"),
        CheckConstraint(
            "length(manifest_hash) = 64", name="ck_pipeline_run_manifest_hash"
        ),
        CheckConstraint(
            "length(trim(git_commit_sha)) > 0", name="ck_pipeline_run_git_commit"
        ),
        CheckConstraint(
            "length(trim(converter)) > 0", name="ck_pipeline_run_converter"
        ),
        CheckConstraint(
            "length(trim(contract_version)) > 0",
            name="ck_pipeline_run_contract_version",
        ),
        CheckConstraint(
            "config_revision >= 0", name="ck_pipeline_run_config_revision"
        ),
        CheckConstraint("retry_limit >= 0", name="ck_pipeline_run_retry_limit"),
        CheckConstraint("attempt_count >= 0", name="ck_pipeline_run_attempt_count"),
        CheckConstraint(
            "jsonb_typeof(runtime_config) = 'object'",
            name="ck_pipeline_run_runtime_config",
        ),
        CheckConstraint(
            "jsonb_typeof(parameters) = 'object'",
            name="ck_pipeline_run_parameters",
        ),
        Index(
            "ix_pipeline_run_dispatchable",
            "created_at",
            "id",
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "ix_pipeline_run_source_history",
            "source_state_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
    )

    source_state_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_source_state.id"), nullable=False, index=True
    )
    run_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_run_request.id", ondelete="SET NULL"),
        unique=True,
        index=True,
    )
    run_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    orchestrator_run_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True
    )
    trigger: Mapped[PipelineRunTrigger] = mapped_column(
        Enum(
            PipelineRunTrigger,
            name="pipeline_run_trigger",
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    status: Mapped[PipelineRunStatus] = mapped_column(
        Enum(
            PipelineRunStatus,
            name="pipeline_run_status",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=PipelineRunStatus.PENDING,
    )
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    git_commit_sha: Mapped[str] = mapped_column(String(255), nullable=False)
    config_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    converter: Mapped[str] = mapped_column(Text, nullable=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False)
    runtime_config: Mapped[dict[str, Any]] = mapped_column(JsonObject, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JsonObject,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    retry_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    source_state: Mapped[PipelineSourceState] = relationship(back_populates="runs")
    run_request: Mapped[PipelineRunRequest | None] = relationship(back_populates="run")


class PipelineAuditEvent(IntegerPrimaryKeyMixin, Base):
    __tablename__ = "pipeline_audit_event"
    __table_args__ = (
        CheckConstraint(
            "length(trim(actor)) > 0", name="ck_pipeline_audit_event_actor"
        ),
        CheckConstraint(
            "length(trim(action)) > 0", name="ck_pipeline_audit_event_action"
        ),
        CheckConstraint(
            "length(trim(entity_type)) > 0",
            name="ck_pipeline_audit_event_entity_type",
        ),
        CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_pipeline_audit_event_payload",
        ),
        Index(
            "ix_pipeline_audit_event_source_history",
            "source_state_id",
            text("occurred_at DESC"),
            text("id DESC"),
        ),
    )

    source_state_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_source_state.id", ondelete="SET NULL"),
        index=True,
    )
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(255))
    payload: Mapped[dict[str, Any]] = mapped_column(
        JsonObject,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    source_state: Mapped[PipelineSourceState | None] = relationship(
        back_populates="audit_events"
    )
