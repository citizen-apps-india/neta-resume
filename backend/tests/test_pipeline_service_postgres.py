from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from neta_core.pipeline.contracts import AdminRuntimePatch, SourceManifest
from neta_core.pipeline.loader import load_source_manifest

from neta_backend.database.models.pipeline import (
    PipelineAuditEvent,
    PipelineRun,
    PipelineRunRequest,
    PipelineRunStatus,
    PipelineRunRequestType,
    PipelineSourceConfigRevision,
    PipelineSourceState,
)
from neta_backend.pipeline.service import (
    IdempotencyConflict,
    PipelineControlService,
    SourceQuarantined,
)

DATABASE_URL = os.getenv("NETA_TEST_DATABASE_URL")
ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / "ingestion" / "source_registry" / "digital_sansad_members.yaml"

pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="NETA_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


async def _clear_control_tables(session_factory: async_sessionmaker) -> None:
    async with session_factory() as session:
        await session.execute(delete(PipelineAuditEvent))
        await session.execute(delete(PipelineRun))
        await session.execute(delete(PipelineRunRequest))
        await session.execute(delete(PipelineSourceConfigRevision))
        await session.execute(delete(PipelineSourceState))
        await session.commit()


async def test_async_service_revisions_rebase_commands_and_quarantine() -> None:
    assert DATABASE_URL is not None
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    await _clear_control_tables(session_factory)

    try:
        async with session_factory() as session:
            manifest = load_source_manifest(MANIFEST)
            service = PipelineControlService(session)
            started_at = datetime(2026, 7, 31, 9, 0, tzinfo=UTC)

            state = await service.register_manifest(
                manifest,
                git_commit_sha="a" * 40,
                occurred_at=started_at,
            )
            assert state.active_revision == 0
            assert state.next_run_at == started_at

            frequency_revision = await service.change_runtime(
                manifest,
                AdminRuntimePatch(frequency_seconds=3600),
                changed_by="operator@example.org",
                change_reason="Pin an approved hourly operator cadence",
                occurred_at=started_at + timedelta(minutes=1),
            )
            pause_revision = await service.change_runtime(
                manifest,
                AdminRuntimePatch(paused=True),
                changed_by="operator@example.org",
                change_reason="Pause while the upstream endpoint is unstable",
                occurred_at=started_at + timedelta(minutes=2),
            )
            assert frequency_revision.revision == 1
            assert pause_revision.revision == 2
            assert pause_revision.effective_config["frequency_seconds"] == 3600
            assert pause_revision.effective_config["paused"] is True

            changed_data = manifest.model_dump(mode="json")
            changed_data["ingestion"]["defaults"]["frequency_seconds"] = 7200
            changed_data["ingestion"]["defaults"]["retry_limit"] = 4
            changed_manifest = SourceManifest.model_validate(changed_data)
            rebased = await service.register_manifest(
                changed_manifest,
                git_commit_sha="b" * 40,
                occurred_at=started_at + timedelta(minutes=3),
            )
            assert rebased.effective_config["frequency_seconds"] == 3600
            assert rebased.effective_config["retry_limit"] == 4
            assert rebased.effective_config["paused"] is True
            assert rebased.admin_overrides == {
                "frequency_seconds": 3600,
                "paused": True,
            }

            reset_revision = await service.reset_runtime_to_defaults(
                changed_manifest,
                changed_by="operator@example.org",
                change_reason="Return scheduling to repository-owned defaults",
                occurred_at=started_at + timedelta(minutes=4),
            )
            assert reset_revision.operation.value == "reset"
            assert reset_revision.patch == {}
            assert reset_revision.effective_config["frequency_seconds"] == 7200

            request, created = await service.request_run(
                changed_manifest.id,
                PipelineRunRequestType.BACKFILL,
                parameters={"partition": "2026-07-30"},
                idempotency_key="admin-backfill-20260730",
                requested_by="operator@example.org",
                request_reason="Replay the missing daily partition",
                requested_at=started_at + timedelta(minutes=5),
            )
            repeated, repeated_created = await service.request_run(
                changed_manifest.id,
                PipelineRunRequestType.BACKFILL,
                parameters={"partition": "2026-07-30"},
                idempotency_key="admin-backfill-20260730",
                requested_by="operator@example.org",
                request_reason="Replay the missing daily partition",
                requested_at=started_at + timedelta(minutes=6),
            )
            assert created is True
            assert repeated_created is False
            assert repeated.id == request.id

            with pytest.raises(IdempotencyConflict):
                await service.request_run(
                    changed_manifest.id,
                    PipelineRunRequestType.BACKFILL,
                    parameters={"partition": "2026-07-29"},
                    idempotency_key="admin-backfill-20260730",
                    requested_by="operator@example.org",
                    request_reason="Try to reuse a command key",
                )

            quarantined = await service.set_quarantine(
                changed_manifest,
                quarantined=True,
                changed_by="operator@example.org",
                change_reason="Stop execution until source output is reviewed",
                occurred_at=started_at + timedelta(minutes=7),
            )
            assert quarantined.quarantined_at is not None
            with pytest.raises(SourceQuarantined):
                await service.request_run(
                    changed_manifest.id,
                    PipelineRunRequestType.RUN_NOW,
                    parameters={},
                    idempotency_key="blocked-by-quarantine",
                    requested_by="operator@example.org",
                    request_reason="Validate quarantine enforcement",
                )

            assert await session.scalar(select(func.count(PipelineSourceConfigRevision.id))) == 3
            assert await session.scalar(select(func.count(PipelineRunRequest.id))) == 1
            assert await session.scalar(select(func.count(PipelineAuditEvent.id))) == 7
    finally:
        await _clear_control_tables(session_factory)
        await engine.dispose()


async def test_scheduler_claims_idempotent_runs_and_records_execution_lifecycle() -> None:
    assert DATABASE_URL is not None
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    await _clear_control_tables(session_factory)

    try:
        async with session_factory() as session:
            manifest = load_source_manifest(MANIFEST)
            service = PipelineControlService(session)
            started_at = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
            await service.register_manifest(
                manifest,
                git_commit_sha="c" * 40,
                occurred_at=started_at,
            )

            first = await service.claim_dispatches(
                {manifest.id: manifest},
                occurred_at=started_at,
            )
            repeated = await service.claim_dispatches(
                {manifest.id: manifest},
                occurred_at=started_at + timedelta(seconds=10),
            )
            assert len(first) == 1
            assert repeated == first
            assert first[0].run_key.startswith("schedule:digital_sansad.members:")
            assert await session.scalar(select(func.count(PipelineRun.id))) == 1

            snapshot = await service.start_pipeline_run(
                first[0].pipeline_run_id,
                orchestrator_run_id="dagster-run-1",
                attempt_number=1,
                occurred_at=started_at + timedelta(seconds=20),
            )
            assert snapshot.source_key == manifest.id
            assert snapshot.parameters == {}
            assert snapshot.retry_limit == manifest.ingestion.defaults.retry_limit

            await service.record_pipeline_retry(
                first[0].pipeline_run_id,
                attempt_number=1,
                error_message="temporary upstream failure",
                occurred_at=started_at + timedelta(seconds=30),
            )
            await service.start_pipeline_run(
                first[0].pipeline_run_id,
                orchestrator_run_id="dagster-run-1",
                attempt_number=2,
                occurred_at=started_at + timedelta(seconds=40),
            )
            await service.complete_pipeline_run(
                first[0].pipeline_run_id,
                status=PipelineRunStatus.SUCCEEDED,
                occurred_at=started_at + timedelta(seconds=50),
            )

            persisted_run = await session.get(PipelineRun, first[0].pipeline_run_id)
            assert persisted_run is not None
            assert persisted_run.status is PipelineRunStatus.SUCCEEDED
            assert persisted_run.attempt_count == 2
            state = await session.scalar(
                select(PipelineSourceState).where(
                    PipelineSourceState.source_key == manifest.id
                )
            )
            assert state is not None
            assert state.last_success_at == started_at + timedelta(seconds=50)
            assert state.next_run_at == started_at + timedelta(minutes=30)
    finally:
        await _clear_control_tables(session_factory)
        await engine.dispose()
