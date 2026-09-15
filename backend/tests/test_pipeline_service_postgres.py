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


async def test_claimed_runs_carry_the_operator_effective_runtime_configuration() -> None:
    """The executor must read its rate limit from the run, not from repository defaults."""
    assert DATABASE_URL is not None
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    await _clear_control_tables(session_factory)

    try:
        async with session_factory() as session:
            manifest = load_source_manifest(MANIFEST)
            service = PipelineControlService(session)
            at = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
            await service.register_manifest(manifest, git_commit_sha="d" * 40, occurred_at=at)
            await service.change_runtime(
                manifest,
                AdminRuntimePatch(rate_limit_per_minute=3, concurrency_limit=1),
                changed_by="operator@example.org",
                change_reason="Slow this source down while upstream is fragile",
                occurred_at=at + timedelta(minutes=1),
            )

            dispatches = await service.claim_dispatches(
                {manifest.id: manifest}, occurred_at=at + timedelta(minutes=2)
            )
            assert len(dispatches) == 1
            assert manifest.ingestion.defaults.rate_limit_per_minute == 30  # the Git default
            assert dispatches[0].runtime_config.rate_limit_per_minute == 3  # the operator's

            snapshot = await service.start_pipeline_run(
                dispatches[0].pipeline_run_id,
                orchestrator_run_id="cli-tick:1",
                attempt_number=1,
                occurred_at=at + timedelta(minutes=3),
            )
            assert snapshot.runtime_config.rate_limit_per_minute == 3
            assert snapshot.runtime_config.concurrency_limit == 1
            assert snapshot.retry_limit == snapshot.runtime_config.retry_limit
    finally:
        await _clear_control_tables(session_factory)
        await engine.dispose()


async def test_stale_runs_are_cancelled_and_release_their_source() -> None:
    """A killed job leaves a RUNNING row that blocks its source until a later tick cancels it."""
    assert DATABASE_URL is not None
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    await _clear_control_tables(session_factory)

    try:
        async with session_factory() as session:
            manifest = load_source_manifest(MANIFEST)
            service = PipelineControlService(session)
            at = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)
            await service.register_manifest(manifest, git_commit_sha="e" * 40, occurred_at=at)
            # Single-slot sources (myneta.candidates is one) are the ones an abandoned run kills
            # outright, so pin the concurrency limit to 1 for this scenario.
            await service.change_runtime(
                manifest,
                AdminRuntimePatch(concurrency_limit=1),
                changed_by="operator@example.org",
                change_reason="Run this source one execution at a time",
                occurred_at=at,
            )

            claimed = await service.claim_dispatches({manifest.id: manifest}, occurred_at=at)
            assert len(claimed) == 1
            await service.start_pipeline_run(
                claimed[0].pipeline_run_id,
                orchestrator_run_id="gha-999.1:1",
                attempt_number=1,
                occurred_at=at,
            )

            # The job is killed here: nothing ever reports a terminal status. The source is now
            # blocked, because a RUNNING run counts against concurrency_limit.
            blocked = await service.claim_dispatches(
                {manifest.id: manifest}, occurred_at=at + timedelta(hours=7)
            )
            assert blocked == []

            # A run younger than the cutoff is left strictly alone.
            untouched = await service.reconcile_stale_runs(
                stale_after=timedelta(hours=6),
                occurred_at=at + timedelta(hours=5, minutes=59),
            )
            assert untouched == []
            still_running = await session.get(PipelineRun, claimed[0].pipeline_run_id)
            assert still_running is not None
            assert still_running.status is PipelineRunStatus.RUNNING

            reconciled = await service.reconcile_stale_runs(
                stale_after=timedelta(hours=6),
                occurred_at=at + timedelta(hours=7),
            )
            assert [entry.pipeline_run_id for entry in reconciled] == [
                claimed[0].pipeline_run_id
            ]
            assert reconciled[0].source_key == manifest.id
            assert reconciled[0].orchestrator_run_id == "gha-999.1:1"

            cancelled = await session.get(PipelineRun, claimed[0].pipeline_run_id)
            assert cancelled is not None
            assert cancelled.status is PipelineRunStatus.CANCELLED
            assert cancelled.completed_at == at + timedelta(hours=7)
            assert "stopped reporting" in (cancelled.error_message or "")

            # The cancellation is its own audit event, not a failure.
            events = list(
                await session.scalars(
                    select(PipelineAuditEvent).where(
                        PipelineAuditEvent.entity_id == str(claimed[0].pipeline_run_id)
                    )
                )
            )
            actions = {event.action for event in events}
            assert "run.cancelled" in actions
            assert "run.failed" not in actions
            cancellation = next(event for event in events if event.action == "run.cancelled")
            assert cancellation.actor == "dispatch-reconciler"
            assert cancellation.payload["reason"] == "stale_orchestrator_run"
            assert cancellation.payload["stale_after_seconds"] == 21600

            # …and the source is claimable again, with no human involved.
            released = await service.claim_dispatches(
                {manifest.id: manifest}, occurred_at=at + timedelta(hours=7, seconds=1)
            )
            assert len(released) == 1
            assert released[0].pipeline_run_id != claimed[0].pipeline_run_id

            # Reconciliation is idempotent: the cancelled run is no longer a candidate.
            assert (
                await service.reconcile_stale_runs(
                    stale_after=timedelta(hours=6),
                    occurred_at=at + timedelta(hours=8),
                )
                == []
            )
    finally:
        await _clear_control_tables(session_factory)
        await engine.dispose()


async def test_reconcile_stale_runs_rejects_an_unsafe_cutoff() -> None:
    assert DATABASE_URL is not None
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            service = PipelineControlService(session)
            with pytest.raises(ValueError, match="positive interval"):
                await service.reconcile_stale_runs(stale_after=timedelta(0))
            with pytest.raises(ValueError, match="between 1 and 500"):
                await service.reconcile_stale_runs(stale_after=timedelta(hours=6), limit=0)
    finally:
        await engine.dispose()
