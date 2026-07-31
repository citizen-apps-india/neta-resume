"""Async SQLAlchemy service boundary for ingestion runtime controls."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from neta_core.pipeline.contracts import (
    AdminRuntimePatch,
    ConfigRevisionOperation,
    RuntimeConfig,
    SourceManifest,
    TriggerMode,
    effective_runtime_config,
    source_manifest_hash,
)

from neta_backend.database.models.pipeline import (
    PipelineAuditEvent,
    PipelineRun,
    PipelineRunRequest,
    PipelineRunRequestStatus,
    PipelineRunRequestType,
    PipelineRunStatus,
    PipelineRunTrigger,
    PipelineSourceConfigRevision,
    PipelineSourceState,
    SourceRegistry,
)


class ControlPlaneError(RuntimeError):
    pass


class SourceNotRegistered(ControlPlaneError):
    pass


class ManifestOutOfSync(ControlPlaneError):
    pass


class NoRuntimeChange(ControlPlaneError):
    pass


class SourceQuarantined(ControlPlaneError):
    pass


class IdempotencyConflict(ControlPlaneError):
    pass


class PipelineRunNotFound(ControlPlaneError):
    pass


@dataclass(frozen=True, slots=True)
class PipelineDispatch:
    """A durable pending execution that a Dagster sensor may safely emit repeatedly."""

    pipeline_run_id: int
    source_key: str
    run_key: str


@dataclass(frozen=True, slots=True)
class PipelineExecutionSnapshot:
    pipeline_run_id: int
    source_key: str
    run_key: str
    parameters: dict[str, Any]
    retry_limit: int


class PipelineControlService:
    """Own control-plane transactions, validation, revisions, and audit events."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def register_manifest(
        self,
        manifest: SourceManifest,
        *,
        git_commit_sha: str,
        actor: str = "deployment-controller",
        occurred_at: datetime | None = None,
    ) -> PipelineSourceState:
        at = _aware_timestamp(occurred_at)
        actor = _required_text(actor, "actor")
        git_commit_sha = _required_text(git_commit_sha, "git_commit_sha")
        manifest_hash = source_manifest_hash(manifest)
        # A row lock cannot protect the first insert. The transaction-scoped advisory lock makes
        # concurrent deployment replicas serialize registration for this manifest key.
        await self._db_session.execute(
            select(func.pg_advisory_xact_lock(func.hashtextextended(manifest.id, 0)))
        )
        state = await self._get_source_state(manifest.id, for_update=True, required=False)
        source_id = await self._source_registry_id(manifest.source_code)
        created = state is None

        if state is None:
            effective = effective_runtime_config(manifest)
            state = PipelineSourceState(
                source_key=manifest.id,
                source_id=source_id,
                manifest_hash=manifest_hash,
                git_commit_sha=git_commit_sha,
                admin_overrides={},
                effective_config=effective.model_dump(mode="json"),
                **_runtime_columns(effective),
                next_run_at=_initial_next_run(manifest, effective, at),
                active_revision=0,
                consecutive_failures=0,
            )
            self._db_session.add(state)
            await self._db_session.flush()
            previous_manifest_hash = None
            previous_git_commit = None
        else:
            previous_manifest_hash = state.manifest_hash
            previous_git_commit = state.git_commit_sha
            override_patch = (
                AdminRuntimePatch.model_validate(state.admin_overrides)
                if state.admin_overrides
                else None
            )
            effective = effective_runtime_config(manifest, override_patch)
            if manifest_hash != state.manifest_hash:
                state.next_run_at = (
                    None
                    if state.quarantined_at is not None
                    else _initial_next_run(manifest, effective, at)
                )
            state.source_id = source_id
            state.manifest_hash = manifest_hash
            state.git_commit_sha = git_commit_sha
            _set_runtime(state, effective)

        if created or manifest_hash != previous_manifest_hash or git_commit_sha != previous_git_commit:
            self._db_session.add(
                PipelineAuditEvent(
                    source_state_id=state.id,
                    actor=actor,
                    action="manifest.registered" if created else "manifest.reconciled",
                    entity_type="source_manifest",
                    entity_id=manifest.id,
                    payload={
                        "manifest_hash": manifest_hash,
                        "git_commit_sha": git_commit_sha,
                        "previous_manifest_hash": previous_manifest_hash,
                        "previous_git_commit_sha": previous_git_commit,
                        "admin_overrides": state.admin_overrides,
                        "effective_config": effective.model_dump(mode="json"),
                    },
                    occurred_at=at,
                )
            )
        await self._db_session.commit()
        await self._db_session.refresh(state)
        return state

    async def change_runtime(
        self,
        manifest: SourceManifest,
        patch: AdminRuntimePatch,
        *,
        changed_by: str,
        change_reason: str,
        occurred_at: datetime | None = None,
    ) -> PipelineSourceConfigRevision:
        at = _aware_timestamp(occurred_at)
        changed_by = _required_text(changed_by, "changed_by")
        change_reason = _required_text(change_reason, "change_reason", minimum=3)
        state = await self._locked_current_state(manifest)
        updated_overrides = {
            **state.admin_overrides,
            **patch.model_dump(mode="json", exclude_unset=True),
        }
        if updated_overrides == state.admin_overrides:
            raise NoRuntimeChange(f"admin overrides for {manifest.id} would not change")

        current = RuntimeConfig.model_validate(state.effective_config)
        effective = effective_runtime_config(
            manifest, AdminRuntimePatch.model_validate(updated_overrides)
        )
        revision = await self._append_config_revision(
            state,
            operation=ConfigRevisionOperation.PATCH,
            patch=patch.model_dump(mode="json", exclude_unset=True),
            admin_overrides=updated_overrides,
            current=current,
            effective=effective,
            trigger_mode=manifest.ingestion.trigger.mode,
            changed_fields=patch.model_fields_set,
            changed_by=changed_by,
            change_reason=change_reason,
            occurred_at=at,
        )
        await self._db_session.commit()
        await self._db_session.refresh(revision)
        return revision

    async def reset_runtime_to_defaults(
        self,
        manifest: SourceManifest,
        *,
        changed_by: str,
        change_reason: str,
        occurred_at: datetime | None = None,
    ) -> PipelineSourceConfigRevision:
        at = _aware_timestamp(occurred_at)
        changed_by = _required_text(changed_by, "changed_by")
        change_reason = _required_text(change_reason, "change_reason", minimum=3)
        state = await self._locked_current_state(manifest)
        if not state.admin_overrides:
            raise NoRuntimeChange(f"source {manifest.id} already uses Git defaults")

        revision = await self._append_config_revision(
            state,
            operation=ConfigRevisionOperation.RESET,
            patch={},
            admin_overrides={},
            current=RuntimeConfig.model_validate(state.effective_config),
            effective=effective_runtime_config(manifest),
            trigger_mode=manifest.ingestion.trigger.mode,
            changed_fields=set(state.admin_overrides),
            changed_by=changed_by,
            change_reason=change_reason,
            occurred_at=at,
        )
        await self._db_session.commit()
        await self._db_session.refresh(revision)
        return revision

    async def set_quarantine(
        self,
        manifest: SourceManifest,
        *,
        quarantined: bool,
        changed_by: str,
        change_reason: str,
        occurred_at: datetime | None = None,
    ) -> PipelineSourceState:
        at = _aware_timestamp(occurred_at)
        changed_by = _required_text(changed_by, "changed_by")
        change_reason = _required_text(change_reason, "change_reason", minimum=3)
        state = await self._locked_current_state(manifest)
        currently_quarantined = state.quarantined_at is not None
        if quarantined == currently_quarantined:
            label = "quarantined" if quarantined else "not quarantined"
            raise NoRuntimeChange(f"source {manifest.id} is already {label}")

        state.quarantined_at = at if quarantined else None
        state.quarantined_by = changed_by if quarantined else None
        state.quarantined_reason = change_reason if quarantined else None
        runtime = RuntimeConfig.model_validate(state.effective_config)
        state.next_run_at = None if quarantined else _initial_next_run(manifest, runtime, at)
        self._db_session.add(
            PipelineAuditEvent(
                source_state_id=state.id,
                actor=changed_by,
                action="source.quarantined" if quarantined else "source.quarantine_released",
                entity_type="pipeline_source_state",
                entity_id=manifest.id,
                payload={"reason": change_reason},
                occurred_at=at,
            )
        )
        await self._db_session.commit()
        await self._db_session.refresh(state)
        return state

    async def request_run(
        self,
        source_key: str,
        request_type: PipelineRunRequestType,
        *,
        parameters: dict[str, Any] | None,
        idempotency_key: str,
        requested_by: str,
        request_reason: str,
        requested_at: datetime | None = None,
    ) -> tuple[PipelineRunRequest, bool]:
        at = _aware_timestamp(requested_at)
        idempotency_key = _required_text(idempotency_key, "idempotency_key")
        requested_by = _required_text(requested_by, "requested_by")
        request_reason = _required_text(request_reason, "request_reason", minimum=3)
        parameters = parameters or {}
        state = await self._get_source_state(source_key, for_update=True)
        if state.quarantined_at is not None:
            raise SourceQuarantined(f"source {source_key} is quarantined")

        existing = await self._db_session.scalar(
            select(PipelineRunRequest).where(
                PipelineRunRequest.source_state_id == state.id,
                PipelineRunRequest.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            expected = (request_type, parameters, requested_by, request_reason)
            actual = (
                existing.request_type,
                existing.parameters,
                existing.requested_by,
                existing.request_reason,
            )
            if actual != expected:
                raise IdempotencyConflict(
                    f"idempotency key {idempotency_key!r} already identifies another request"
                )
            await self._db_session.commit()
            return existing, False

        request = PipelineRunRequest(
            source_state_id=state.id,
            request_type=request_type,
            status=PipelineRunRequestStatus.PENDING,
            parameters=parameters,
            idempotency_key=idempotency_key,
            requested_by=requested_by,
            request_reason=request_reason,
            requested_at=at,
        )
        self._db_session.add(request)
        await self._db_session.flush()
        self._db_session.add(
            PipelineAuditEvent(
                source_state_id=state.id,
                actor=requested_by,
                action="run.requested",
                entity_type="pipeline_run_request",
                entity_id=str(request.id),
                payload={
                    "request_type": request_type.value,
                    "parameters": parameters,
                    "reason": request_reason,
                },
                occurred_at=at,
            )
        )
        await self._db_session.commit()
        await self._db_session.refresh(request)
        return request, True

    async def list_source_states(self) -> list[PipelineSourceState]:
        return list(
            await self._db_session.scalars(
                select(PipelineSourceState).order_by(PipelineSourceState.source_key)
            )
        )

    async def source_state(self, source_key: str) -> PipelineSourceState:
        state = await self._get_source_state(source_key)
        assert state is not None
        return state

    async def list_config_revisions(
        self,
        source_key: str,
        *,
        limit: int = 50,
    ) -> list[PipelineSourceConfigRevision]:
        if limit < 1 or limit > 500:
            raise ValueError("revision limit must be between 1 and 500")
        state = await self._get_source_state(source_key)
        assert state is not None
        return list(
            await self._db_session.scalars(
                select(PipelineSourceConfigRevision)
                .where(PipelineSourceConfigRevision.source_state_id == state.id)
                .order_by(PipelineSourceConfigRevision.revision.desc())
                .limit(limit)
            )
        )

    async def list_pipeline_runs(
        self,
        *,
        source_key: str | None = None,
        limit: int = 100,
    ) -> list[tuple[PipelineRun, str]]:
        if limit < 1 or limit > 500:
            raise ValueError("run limit must be between 1 and 500")
        statement = (
            select(PipelineRun, PipelineSourceState.source_key)
            .join(PipelineSourceState)
            .order_by(PipelineRun.created_at.desc(), PipelineRun.id.desc())
            .limit(limit)
        )
        if source_key is not None:
            statement = statement.where(PipelineSourceState.source_key == source_key)
        return [(run, key) for run, key in (await self._db_session.execute(statement)).all()]

    async def list_run_requests(
        self,
        *,
        source_key: str | None = None,
        limit: int = 100,
    ) -> list[tuple[PipelineRunRequest, str]]:
        if limit < 1 or limit > 500:
            raise ValueError("run-request limit must be between 1 and 500")
        statement = (
            select(PipelineRunRequest, PipelineSourceState.source_key)
            .join(PipelineSourceState)
            .order_by(
                PipelineRunRequest.requested_at.desc(),
                PipelineRunRequest.id.desc(),
            )
            .limit(limit)
        )
        if source_key is not None:
            statement = statement.where(PipelineSourceState.source_key == source_key)
        return [
            (request, key)
            for request, key in (await self._db_session.execute(statement)).all()
        ]

    async def claim_dispatches(
        self,
        manifests: Mapping[str, SourceManifest],
        *,
        occurred_at: datetime | None = None,
        limit: int = 100,
    ) -> list[PipelineDispatch]:
        """Create due execution records and return all pending records safe to dispatch.

        A transaction advisory lock serialises multiple Dagster sensor replicas.  Each execution has
        a stable run key, so an unacknowledged sensor tick can emit it again without creating a second
        Dagster run.
        """
        at = _aware_timestamp(occurred_at)
        if limit < 1:
            raise ValueError("dispatch limit must be at least 1")
        await self._db_session.execute(
            select(func.pg_advisory_xact_lock(func.hashtextextended("pipeline-dispatch", 0)))
        )

        active_rows = (
            await self._db_session.execute(
                select(PipelineRun.source_state_id, func.count(PipelineRun.id))
                .where(
                    PipelineRun.status.in_(
                        [PipelineRunStatus.PENDING, PipelineRunStatus.RUNNING]
                    )
                )
                .group_by(PipelineRun.source_state_id)
            )
        ).all()
        active_by_state = {state_id: count for state_id, count in active_rows}

        pending_requests = (
            await self._db_session.execute(
                select(PipelineRunRequest, PipelineSourceState)
                .join(
                    PipelineSourceState,
                    PipelineSourceState.id == PipelineRunRequest.source_state_id,
                )
                .where(
                    PipelineRunRequest.status == PipelineRunRequestStatus.PENDING,
                    PipelineSourceState.enabled.is_(True),
                    PipelineSourceState.quarantined_at.is_(None),
                )
                .order_by(PipelineRunRequest.requested_at, PipelineRunRequest.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for request, state in pending_requests:
            manifest = manifests.get(state.source_key)
            if not _manifest_is_executable(state, manifest):
                continue
            active = active_by_state.get(state.id, 0)
            if active >= state.concurrency_limit:
                continue
            pipeline_run = _new_pipeline_run(
                state,
                manifest,
                trigger=PipelineRunTrigger(request.request_type.value),
                run_key=f"request:{state.source_key}:{request.id}",
                parameters=request.parameters,
                run_request_id=request.id,
                scheduled_for=None,
            )
            self._db_session.add(pipeline_run)
            request.status = PipelineRunRequestStatus.ACCEPTED
            request.accepted_at = at
            active_by_state[state.id] = active + 1
            await self._db_session.flush()
            _audit_run_claimed(self._db_session, state, pipeline_run, at)

        due_states = (
            await self._db_session.scalars(
                select(PipelineSourceState)
                .where(
                    PipelineSourceState.enabled.is_(True),
                    PipelineSourceState.paused.is_(False),
                    PipelineSourceState.quarantined_at.is_(None),
                    PipelineSourceState.next_run_at.is_not(None),
                    PipelineSourceState.next_run_at <= at,
                )
                .order_by(PipelineSourceState.next_run_at, PipelineSourceState.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for state in due_states:
            manifest = manifests.get(state.source_key)
            if not _manifest_is_executable(state, manifest):
                continue
            active = active_by_state.get(state.id, 0)
            if active >= state.concurrency_limit:
                continue
            scheduled_for = state.next_run_at
            if scheduled_for is None or state.frequency_seconds is None:
                continue
            pipeline_run = _new_pipeline_run(
                state,
                manifest,
                trigger=PipelineRunTrigger.SCHEDULED,
                run_key=f"schedule:{state.source_key}:{scheduled_for.isoformat()}",
                parameters={},
                run_request_id=None,
                scheduled_for=scheduled_for,
            )
            self._db_session.add(pipeline_run)
            state.next_run_at = _next_future_interval(
                scheduled_for,
                state.frequency_seconds,
                at,
            )
            active_by_state[state.id] = active + 1
            await self._db_session.flush()
            _audit_run_claimed(self._db_session, state, pipeline_run, at)

        await self._db_session.commit()
        pending = (
            await self._db_session.execute(
                select(PipelineRun, PipelineSourceState)
                .join(PipelineSourceState)
                .where(PipelineRun.status == PipelineRunStatus.PENDING)
                .order_by(PipelineRun.created_at, PipelineRun.id)
                .limit(limit)
            )
        ).all()
        return [
            PipelineDispatch(
                pipeline_run_id=run.id,
                source_key=state.source_key,
                run_key=run.run_key,
            )
            for run, state in pending
            if (
                (manifest := manifests.get(state.source_key)) is not None
                and _manifest_is_executable(state, manifest)
                and run.manifest_hash == source_manifest_hash(manifest)
            )
        ]

    async def start_pipeline_run(
        self,
        pipeline_run_id: int,
        *,
        orchestrator_run_id: str,
        attempt_number: int,
        occurred_at: datetime | None = None,
    ) -> PipelineExecutionSnapshot:
        at = _aware_timestamp(occurred_at)
        orchestrator_run_id = _required_text(orchestrator_run_id, "orchestrator_run_id")
        if attempt_number < 1:
            raise ValueError("attempt_number must be at least 1")
        run = await self._locked_pipeline_run(pipeline_run_id)
        state = await self._get_source_state_by_id(run.source_state_id, for_update=True)
        if run.status in {
            PipelineRunStatus.SUCCEEDED,
            PipelineRunStatus.FAILED,
            PipelineRunStatus.CANCELLED,
        }:
            raise ControlPlaneError(f"pipeline run {pipeline_run_id} is already {run.status.value}")
        if run.orchestrator_run_id not in {None, orchestrator_run_id}:
            raise IdempotencyConflict(
                f"pipeline run {pipeline_run_id} belongs to orchestrator run "
                f"{run.orchestrator_run_id!r}"
            )

        first_start = run.status is PipelineRunStatus.PENDING
        run.status = PipelineRunStatus.RUNNING
        run.orchestrator_run_id = orchestrator_run_id
        run.started_at = run.started_at or at
        run.attempt_count = max(run.attempt_count, attempt_number)
        state.last_run_at = at
        if run.run_request_id is not None:
            request = await self._db_session.get(PipelineRunRequest, run.run_request_id)
            if request is not None:
                request.status = PipelineRunRequestStatus.RUNNING
                request.started_at = request.started_at or at
        if first_start:
            self._db_session.add(
                PipelineAuditEvent(
                    source_state_id=state.id,
                    actor="dagster",
                    action="run.started",
                    entity_type="pipeline_run",
                    entity_id=str(run.id),
                    payload={
                        "run_key": run.run_key,
                        "orchestrator_run_id": orchestrator_run_id,
                    },
                    occurred_at=at,
                )
            )
        await self._db_session.commit()
        return _execution_snapshot(run, state.source_key)

    async def record_pipeline_retry(
        self,
        pipeline_run_id: int,
        *,
        attempt_number: int,
        error_message: str,
        occurred_at: datetime | None = None,
    ) -> None:
        at = _aware_timestamp(occurred_at)
        run = await self._locked_pipeline_run(pipeline_run_id)
        state = await self._get_source_state_by_id(run.source_state_id)
        run.attempt_count = max(run.attempt_count, attempt_number)
        run.error_message = error_message
        self._db_session.add(
            PipelineAuditEvent(
                source_state_id=state.id,
                actor="dagster",
                action="run.retrying",
                entity_type="pipeline_run",
                entity_id=str(run.id),
                payload={"attempt_number": attempt_number, "error": error_message},
                occurred_at=at,
            )
        )
        await self._db_session.commit()

    async def complete_pipeline_run(
        self,
        pipeline_run_id: int,
        *,
        status: PipelineRunStatus,
        error_message: str | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        if status not in {
            PipelineRunStatus.SUCCEEDED,
            PipelineRunStatus.FAILED,
            PipelineRunStatus.CANCELLED,
        }:
            raise ValueError("pipeline run completion requires a terminal status")
        at = _aware_timestamp(occurred_at)
        run = await self._locked_pipeline_run(pipeline_run_id)
        state = await self._get_source_state_by_id(run.source_state_id, for_update=True)
        if run.status in {
            PipelineRunStatus.SUCCEEDED,
            PipelineRunStatus.FAILED,
            PipelineRunStatus.CANCELLED,
        }:
            await self._db_session.commit()
            return

        run.status = status
        run.completed_at = at
        run.error_message = error_message
        if status is PipelineRunStatus.SUCCEEDED:
            state.last_success_at = at
            state.consecutive_failures = 0
        else:
            state.last_failure_at = at
            state.consecutive_failures += 1
        if run.run_request_id is not None:
            request = await self._db_session.get(PipelineRunRequest, run.run_request_id)
            if request is not None:
                request.status = PipelineRunRequestStatus(status.value)
                request.completed_at = at
                request.error_message = error_message
        self._db_session.add(
            PipelineAuditEvent(
                source_state_id=state.id,
                actor="dagster",
                action=f"run.{status.value}",
                entity_type="pipeline_run",
                entity_id=str(run.id),
                payload={
                    "run_key": run.run_key,
                    "orchestrator_run_id": run.orchestrator_run_id,
                    "attempt_count": run.attempt_count,
                    "error": error_message,
                },
                occurred_at=at,
            )
        )
        await self._db_session.commit()

    async def _append_config_revision(
        self,
        state: PipelineSourceState,
        *,
        operation: ConfigRevisionOperation,
        patch: dict[str, Any],
        admin_overrides: dict[str, Any],
        current: RuntimeConfig,
        effective: RuntimeConfig,
        trigger_mode: TriggerMode,
        changed_fields: set[str],
        changed_by: str,
        change_reason: str,
        occurred_at: datetime,
    ) -> PipelineSourceConfigRevision:
        revision_number = state.active_revision + 1
        revision = PipelineSourceConfigRevision(
            source_state_id=state.id,
            revision=revision_number,
            operation=operation,
            patch=patch,
            effective_config=effective.model_dump(mode="json"),
            manifest_hash=state.manifest_hash,
            git_commit_sha=state.git_commit_sha,
            changed_by=changed_by,
            change_reason=change_reason,
            created_at=occurred_at,
        )
        self._db_session.add(revision)
        state.admin_overrides = admin_overrides
        state.active_revision = revision_number
        state.next_run_at = _next_run_after_change(
            current=current,
            effective=effective,
            current_next_run_at=state.next_run_at,
            trigger_mode=trigger_mode,
            changed_fields=changed_fields,
            occurred_at=occurred_at,
        )
        _set_runtime(state, effective)
        await self._db_session.flush()
        self._db_session.add(
            PipelineAuditEvent(
                source_state_id=state.id,
                actor=changed_by,
                action=(
                    "runtime.reset"
                    if operation is ConfigRevisionOperation.RESET
                    else "runtime.changed"
                ),
                entity_type="pipeline_source_config_revision",
                entity_id=str(revision_number),
                payload={
                    "operation": operation.value,
                    "patch": patch,
                    "admin_overrides": admin_overrides,
                    "effective_config": effective.model_dump(mode="json"),
                    "reason": change_reason,
                },
                occurred_at=occurred_at,
            )
        )
        return revision

    async def _locked_current_state(self, manifest: SourceManifest) -> PipelineSourceState:
        state = await self._get_source_state(manifest.id, for_update=True)
        if state.manifest_hash != source_manifest_hash(manifest):
            raise ManifestOutOfSync(
                f"manifest {manifest.id!r} must be registered before changing runtime state"
            )
        return state

    async def _get_source_state(
        self,
        source_key: str,
        *,
        for_update: bool = False,
        required: bool = True,
    ) -> PipelineSourceState | None:
        statement = select(PipelineSourceState).where(
            PipelineSourceState.source_key == source_key
        )
        if for_update:
            statement = statement.with_for_update()
        state = await self._db_session.scalar(statement)
        if state is None and required:
            raise SourceNotRegistered(f"source manifest {source_key!r} is not registered")
        return state

    async def _get_source_state_by_id(
        self,
        source_state_id: int,
        *,
        for_update: bool = False,
    ) -> PipelineSourceState:
        statement = select(PipelineSourceState).where(
            PipelineSourceState.id == source_state_id
        )
        if for_update:
            statement = statement.with_for_update()
        state = await self._db_session.scalar(statement)
        if state is None:
            raise SourceNotRegistered(f"source state {source_state_id} is not registered")
        return state

    async def _locked_pipeline_run(self, pipeline_run_id: int) -> PipelineRun:
        run = await self._db_session.scalar(
            select(PipelineRun)
            .where(PipelineRun.id == pipeline_run_id)
            .with_for_update()
        )
        if run is None:
            raise PipelineRunNotFound(f"pipeline run {pipeline_run_id} does not exist")
        return run

    async def _source_registry_id(self, source_code: str) -> int | None:
        return await self._db_session.scalar(
            select(SourceRegistry.id).where(SourceRegistry.code == source_code)
        )


def _manifest_is_executable(
    state: PipelineSourceState,
    manifest: SourceManifest | None,
) -> bool:
    return bool(
        manifest is not None
        and manifest.orchestration is not None
        and state.manifest_hash == source_manifest_hash(manifest)
    )


def _new_pipeline_run(
    state: PipelineSourceState,
    manifest: SourceManifest,
    *,
    trigger: PipelineRunTrigger,
    run_key: str,
    parameters: dict[str, Any],
    run_request_id: int | None,
    scheduled_for: datetime | None,
) -> PipelineRun:
    return PipelineRun(
        source_state_id=state.id,
        run_request_id=run_request_id,
        run_key=run_key,
        trigger=trigger,
        status=PipelineRunStatus.PENDING,
        manifest_hash=state.manifest_hash,
        git_commit_sha=state.git_commit_sha,
        config_revision=state.active_revision,
        converter=manifest.conversion.converter,
        contract_version=manifest.conversion.contract,
        runtime_config=state.effective_config,
        parameters=parameters,
        retry_limit=state.retry_limit,
        attempt_count=0,
        scheduled_for=scheduled_for,
    )


def _audit_run_claimed(
    session: AsyncSession,
    state: PipelineSourceState,
    pipeline_run: PipelineRun,
    occurred_at: datetime,
) -> None:
    session.add(
        PipelineAuditEvent(
            source_state_id=state.id,
            actor="dagster-controller",
            action="run.claimed",
            entity_type="pipeline_run",
            entity_id=str(pipeline_run.id),
            payload={
                "run_key": pipeline_run.run_key,
                "trigger": pipeline_run.trigger.value,
                "run_request_id": pipeline_run.run_request_id,
                "manifest_hash": pipeline_run.manifest_hash,
                "config_revision": pipeline_run.config_revision,
            },
            occurred_at=occurred_at,
        )
    )


def _next_future_interval(
    scheduled_for: datetime,
    frequency_seconds: int,
    occurred_at: datetime,
) -> datetime:
    elapsed = max(0.0, (occurred_at - scheduled_for).total_seconds())
    periods = int(elapsed // frequency_seconds) + 1
    return scheduled_for + timedelta(seconds=periods * frequency_seconds)


def _execution_snapshot(
    pipeline_run: PipelineRun,
    source_key: str,
) -> PipelineExecutionSnapshot:
    return PipelineExecutionSnapshot(
        pipeline_run_id=pipeline_run.id,
        source_key=source_key,
        run_key=pipeline_run.run_key,
        parameters=dict(pipeline_run.parameters),
        retry_limit=pipeline_run.retry_limit,
    )


def _runtime_columns(runtime: RuntimeConfig) -> dict[str, Any]:
    return {
        "enabled": runtime.enabled,
        "paused": runtime.paused,
        "frequency_seconds": runtime.frequency_seconds,
        "concurrency_limit": runtime.concurrency_limit,
        "rate_limit_per_minute": runtime.rate_limit_per_minute,
        "retry_limit": runtime.retry_limit,
    }


def _set_runtime(state: PipelineSourceState, runtime: RuntimeConfig) -> None:
    state.effective_config = runtime.model_dump(mode="json")
    for field, value in _runtime_columns(runtime).items():
        setattr(state, field, value)


def _initial_next_run(
    manifest: SourceManifest, runtime: RuntimeConfig, occurred_at: datetime
) -> datetime | None:
    if (
        manifest.ingestion.trigger.mode is TriggerMode.SCHEDULED
        and runtime.enabled
        and not runtime.paused
    ):
        return occurred_at
    return None


def _next_run_after_change(
    *,
    current: RuntimeConfig,
    effective: RuntimeConfig,
    current_next_run_at: datetime | None,
    trigger_mode: TriggerMode,
    changed_fields: set[str],
    occurred_at: datetime,
) -> datetime | None:
    if trigger_mode is not TriggerMode.SCHEDULED or not effective.enabled or effective.paused:
        return None
    if current.paused or not current.enabled or changed_fields & {
        "enabled",
        "paused",
        "frequency_seconds",
    }:
        return occurred_at
    return current_next_run_at


def _aware_timestamp(value: datetime | None) -> datetime:
    value = value or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("control-plane timestamps must be timezone-aware")
    return value


def _required_text(value: str, field: str, *, minimum: int = 1) -> str:
    value = value.strip()
    if len(value) < minimum:
        raise ValueError(f"{field} must contain at least {minimum} non-whitespace characters")
    return value
