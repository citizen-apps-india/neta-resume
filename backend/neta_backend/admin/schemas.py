"""Validated request bodies for private ingestion administration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from neta_core.pipeline.contracts import AdminRuntimePatch

from neta_backend.database.models.pipeline import PipelineRunRequestType


class AdminRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuntimeChangeRequest(AdminRequest):
    patch: AdminRuntimePatch
    reason: str = Field(min_length=3, max_length=500)


class RuntimeResetRequest(AdminRequest):
    reason: str = Field(min_length=3, max_length=500)


class QuarantineRequest(AdminRequest):
    quarantined: bool
    reason: str = Field(min_length=3, max_length=500)


class CreateRunRequest(AdminRequest):
    request_type: PipelineRunRequestType = PipelineRunRequestType.RUN_NOW
    parameters: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=3, max_length=500)
