"""Dagster resource that accesses the audited async control-plane service."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TypeVar

import dagster as dg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from neta_backend.database.models.pipeline import PipelineRunStatus
from neta_backend.pipeline.service import (
    PipelineControlService,
    PipelineDispatch,
    PipelineExecutionSnapshot,
)
from neta_core.pipeline import SourceManifest

ResultT = TypeVar("ResultT")


class PipelineControlResource(dg.ConfigurableResource):
    """Short-lived async sessions around the single control-plane transaction boundary."""

    database_url: str
    dispatch_limit: int = 100

    def register_manifests(
        self,
        manifests: Sequence[SourceManifest],
        *,
        git_commit_sha: str,
        actor: str,
    ) -> None:
        async def register(service: PipelineControlService) -> None:
            for manifest in manifests:
                await service.register_manifest(
                    manifest,
                    git_commit_sha=git_commit_sha,
                    actor=actor,
                )

        self._call(register)

    def claim_dispatches(
        self,
        manifests: Mapping[str, SourceManifest],
    ) -> list[PipelineDispatch]:
        return self._call(
            lambda service: service.claim_dispatches(
                manifests,
                limit=self.dispatch_limit,
            )
        )

    def start_pipeline_run(
        self,
        pipeline_run_id: int,
        *,
        orchestrator_run_id: str,
        attempt_number: int,
    ) -> PipelineExecutionSnapshot:
        return self._call(
            lambda service: service.start_pipeline_run(
                pipeline_run_id,
                orchestrator_run_id=orchestrator_run_id,
                attempt_number=attempt_number,
            )
        )

    def record_pipeline_retry(
        self,
        pipeline_run_id: int,
        *,
        attempt_number: int,
        error_message: str,
    ) -> None:
        self._call(
            lambda service: service.record_pipeline_retry(
                pipeline_run_id,
                attempt_number=attempt_number,
                error_message=_bounded_error(error_message),
            )
        )

    def complete_pipeline_run(
        self,
        pipeline_run_id: int,
        *,
        status: PipelineRunStatus,
        error_message: str | None = None,
    ) -> None:
        self._call(
            lambda service: service.complete_pipeline_run(
                pipeline_run_id,
                status=status,
                error_message=_bounded_error(error_message) if error_message else None,
            )
        )

    def _call(
        self,
        operation: Callable[[PipelineControlService], Awaitable[ResultT]],
    ) -> ResultT:
        async def execute() -> ResultT:
            engine = create_async_engine(
                _async_database_url(self.database_url),
                pool_pre_ping=True,
            )
            factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            try:
                async with factory() as session:
                    return await operation(PipelineControlService(session))
            finally:
                await engine.dispose()

        return asyncio.run(execute())


def _async_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url.replace("+psycopg2", "+asyncpg").replace("+psycopg", "+asyncpg")


def _bounded_error(message: str, limit: int = 8000) -> str:
    return message if len(message) <= limit else f"{message[: limit - 1]}…"
