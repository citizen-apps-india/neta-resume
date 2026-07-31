"""Typed contracts shared by source manifests, workers, and the admin control plane.

Git owns :class:`SourceManifest`: source identity, code, contracts, defaults, and guardrails.
The admin layer owns versioned :class:`AdminRuntimePatch` values. The effective configuration is
resolved at run time so operators can pause, resume, or change frequency without a deployment.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictModel(BaseModel):
    """Reject misspelled or undeclared configuration keys."""

    model_config = ConfigDict(extra="forbid")


class AdapterKind(StrEnum):
    API = "api"
    CRAWL = "crawl"
    DOCUMENT = "document"
    FEED = "feed"
    BULK = "bulk"
    GATED = "gated"


class AuthorityRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    VERIFICATION = "verification"
    REPORTED = "reported"
    REFERENCE = "reference"


class LifecycleStatus(StrEnum):
    ACTIVE = "active"
    PLANNED = "planned"
    VERIFICATION_ONLY = "verification_only"
    REFERENCE_ONLY = "reference_only"
    BLOCKED = "blocked"


class UsageDecision(StrEnum):
    ALLOWED = "allowed"
    PROHIBITED = "prohibited"
    REVIEW = "review"


class TriggerMode(StrEnum):
    SCHEDULED = "scheduled"
    EVENT = "event"
    MANUAL = "manual"


class ChangeDetection(StrEnum):
    CURSOR = "cursor"
    ETAG = "etag"
    LAST_MODIFIED = "last_modified"
    CONTENT_HASH = "content_hash"
    RELEASE = "release"
    EVENT_ID = "event_id"
    MANUAL = "manual"


class ChangeOperation(StrEnum):
    UPSERT = "upsert"
    DELETE = "delete"


class RawHistoryMode(StrEnum):
    """How an orchestrated source catalogs immutable raw-envelope metadata."""

    DLT = "dlt"
    DISABLED = "disabled"


class ConfigRevisionOperation(StrEnum):
    PATCH = "patch"
    RESET = "reset"


class AuthorityPolicy(StrictModel):
    role: AuthorityRole
    trust_tier: int = Field(ge=1, le=3)
    jurisdiction: str | None = None


class RightsPolicy(StrictModel):
    license: str = Field(min_length=1)
    commercial_use: UsageDecision
    redistribution: UsageDecision
    store_raw: bool = True
    notes: str | None = None


class TriggerSpec(StrictModel):
    mode: TriggerMode
    profile: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9-]*$")


class RuntimeConfig(StrictModel):
    enabled: bool = True
    paused: bool = False
    frequency_seconds: int | None = Field(default=None, ge=30)
    concurrency_limit: int = Field(default=1, ge=1)
    rate_limit_per_minute: int = Field(default=30, ge=1)
    retry_limit: int = Field(default=3, ge=0)


class RuntimeGuardrails(StrictModel):
    min_frequency_seconds: int | None = Field(default=None, ge=30)
    max_frequency_seconds: int | None = Field(default=None, ge=30)
    max_concurrency: int = Field(default=1, ge=1)
    max_rate_limit_per_minute: int = Field(default=60, ge=1)
    max_retry_limit: int = Field(default=6, ge=0)

    @model_validator(mode="after")
    def validate_frequency_range(self) -> RuntimeGuardrails:
        if (
            self.min_frequency_seconds is not None
            and self.max_frequency_seconds is not None
            and self.min_frequency_seconds > self.max_frequency_seconds
        ):
            raise ValueError("min_frequency_seconds cannot exceed max_frequency_seconds")
        return self


class IngestionSpec(StrictModel):
    adapter: AdapterKind
    base_url: HttpUrl
    trigger: TriggerSpec
    change_detection: list[ChangeDetection] = Field(min_length=1)
    defaults: RuntimeConfig
    guardrails: RuntimeGuardrails
    secret_refs: list[str] = Field(default_factory=list)


class ConversionSpec(StrictModel):
    converter: str = Field(pattern=r"^[a-zA-Z_][\w.]*:[a-zA-Z_]\w*$")
    contract: str = Field(pattern=r"^[a-z][a-z0-9_.-]*\.v[1-9]\d*$")
    produces: list[str] = Field(min_length=1)


class QualitySpec(StrictModel):
    freshness_slo_seconds: int | None = Field(default=None, ge=30)
    minimum_records: int | None = Field(default=None, ge=0)
    required_fields: list[str] = Field(default_factory=list)


class OrchestrationSpec(StrictModel):
    """Executable entrypoint and history policy used by the orchestration plane."""

    runner: str = Field(pattern=r"^[a-zA-Z_][\w.]*:[a-zA-Z_]\w*$")
    raw_history: RawHistoryMode = RawHistoryMode.DLT


class VerificationSpec(StrictModel):
    corroborate_with: list[str] = Field(default_factory=list)
    human_review_required: bool = False


class SourceManifest(StrictModel):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$")
    source_code: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    lifecycle: LifecycleStatus
    authority: AuthorityPolicy
    rights: RightsPolicy
    ingestion: IngestionSpec
    conversion: ConversionSpec
    quality: QualitySpec
    orchestration: OrchestrationSpec | None = None
    verification: VerificationSpec = Field(default_factory=VerificationSpec)

    @model_validator(mode="after")
    def validate_runtime_defaults(self) -> SourceManifest:
        _validate_runtime(self.ingestion.trigger, self.ingestion.defaults, self.ingestion.guardrails)
        return self


class AdminRuntimePatch(StrictModel):
    """Admin-owned operational settings; omitted fields retain their current/default value."""

    enabled: bool | None = None
    paused: bool | None = None
    frequency_seconds: int | None = Field(default=None, ge=30)
    concurrency_limit: int | None = Field(default=None, ge=1)
    rate_limit_per_minute: int | None = Field(default=None, ge=1)
    retry_limit: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_change(self) -> AdminRuntimePatch:
        if not self.model_fields_set:
            raise ValueError("an admin runtime patch must change at least one setting")
        return self


class SourceConfigRevision(StrictModel):
    source_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$")
    revision: int = Field(ge=1)
    operation: ConfigRevisionOperation = ConfigRevisionOperation.PATCH
    changed_by: str = Field(min_length=1)
    change_reason: str = Field(min_length=3)
    created_at: datetime
    patch: AdminRuntimePatch | None = None

    @model_validator(mode="after")
    def validate_operation(self) -> SourceConfigRevision:
        if self.operation is ConfigRevisionOperation.PATCH and self.patch is None:
            raise ValueError("patch revisions require an admin runtime patch")
        if self.operation is ConfigRevisionOperation.RESET and self.patch is not None:
            raise ValueError("reset revisions cannot include an admin runtime patch")
        return self


class RawEnvelope(StrictModel):
    envelope_id: str = Field(min_length=1)
    source_id: str
    native_id: str
    source_uri: HttpUrl
    fetched_at: datetime
    effective_at: datetime | None = None
    content_type: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    object_uri: str = Field(min_length=1)
    license_snapshot: str = Field(min_length=1)
    pipeline_run_id: str = Field(min_length=1)
    http_metadata: dict[str, str] = Field(default_factory=dict)


class EvidenceRef(StrictModel):
    envelope_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    role: AuthorityRole


class CanonicalChange(StrictModel):
    entity_type: str = Field(min_length=1)
    natural_key: str = Field(min_length=1)
    operation: ChangeOperation = ChangeOperation.UPSERT
    schema_version: int = Field(ge=1)
    observed_at: datetime
    effective_at: datetime | None = None
    attributes: dict[str, Any]
    evidence: list[EvidenceRef] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


def effective_runtime_config(
    manifest: SourceManifest, patch: AdminRuntimePatch | None = None
) -> RuntimeConfig:
    """Overlay an admin revision on Git defaults and enforce Git-owned safety guardrails."""
    return apply_runtime_patch(manifest, manifest.ingestion.defaults, patch)


def apply_runtime_patch(
    manifest: SourceManifest,
    current: RuntimeConfig,
    patch: AdminRuntimePatch | None = None,
) -> RuntimeConfig:
    """Apply one admin patch without losing values accepted by earlier revisions."""
    values = current.model_dump()
    if patch is not None:
        values.update(patch.model_dump(exclude_unset=True))
    effective = RuntimeConfig.model_validate(values)
    _validate_runtime(manifest.ingestion.trigger, effective, manifest.ingestion.guardrails)
    return effective


def source_manifest_hash(manifest: SourceManifest) -> str:
    """Return a stable content hash for recording the exact Git-owned configuration used."""
    canonical = json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _validate_runtime(
    trigger: TriggerSpec, runtime: RuntimeConfig, guardrails: RuntimeGuardrails
) -> None:
    frequency = runtime.frequency_seconds
    if trigger.mode is TriggerMode.SCHEDULED and frequency is None:
        raise ValueError("scheduled sources require frequency_seconds")
    if trigger.mode is TriggerMode.MANUAL and frequency is not None:
        raise ValueError("manual sources cannot define frequency_seconds")
    if guardrails.min_frequency_seconds is not None and (
        frequency is not None and frequency < guardrails.min_frequency_seconds
    ):
        raise ValueError("frequency_seconds is more aggressive than the allowed minimum")
    if guardrails.max_frequency_seconds is not None and (
        frequency is not None and frequency > guardrails.max_frequency_seconds
    ):
        raise ValueError("frequency_seconds exceeds the allowed maximum")
    if runtime.concurrency_limit > guardrails.max_concurrency:
        raise ValueError("concurrency_limit exceeds the source guardrail")
    if runtime.rate_limit_per_minute > guardrails.max_rate_limit_per_minute:
        raise ValueError("rate_limit_per_minute exceeds the source guardrail")
    if runtime.retry_limit > guardrails.max_retry_limit:
        raise ValueError("retry_limit exceeds the source guardrail")
