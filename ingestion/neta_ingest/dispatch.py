"""Dagster-free ingestion dispatcher: claim due control-plane work and run it in-process.

This is the plain-CLI port of the Dagster dispatch sensor plus the per-source asset body in
``neta_orchestration.component``.  One ``neta dispatch`` tick:

1. loads the Git-owned manifests from ``ingestion/source_registry/``;
2. asks :class:`~neta_backend.pipeline.service.PipelineControlService` to ``claim_dispatches``
   (that call is the durable, advisory-locked transaction that turns due schedules and audited
   admin run requests into ``pipeline_run`` rows);
3. executes each claimed dispatch's manifest-declared runner in this process, inside
   ``pipeline_execution_scope(snapshot.run_key)`` so every fact keeps the durable run key; and
4. writes the outcome back through ``record_pipeline_retry`` / ``complete_pipeline_run``.

Semantics carried over from the Dagster asset verbatim:

* a ``pydantic.ValidationError`` is a deterministic contract failure and is **never** retried —
  everything else is operational and retries up to ``snapshot.retry_limit``;
* the retry backoff is ``min(60, 2 ** retry_number)`` seconds, where ``retry_number`` is the
  zero-based count of attempts already made (Dagster's ``context.retry_number``);
* every retried attempt records ``record_pipeline_retry`` so the audit trail stays complete, and
  the terminal attempt records the error through ``complete_pipeline_run(status=FAILED, ...)``.

Deliberately *not* ported: raw-envelope history loading into dlt.  Nothing in production emits a
``RawEnvelope`` today, so there is nothing to load; the dlt ledger stays with the Dagster fallback.

Politeness is load-bearing, not cosmetic: MyNeta/ADR, PRS and the court portals are non-commercial
public resources.  Each manifest's ``rate_limit_per_minute`` is applied to the shared throttled HTTP
client for the duration of that source's execution, and its ``concurrency_limit`` caps how many
executions of one source may be in flight at once.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import time
from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, TypeVar, cast
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from neta_backend.database.models.pipeline import (
    PipelineRunRequestStatus,
    PipelineRunStatus,
)
from neta_backend.pipeline.service import (
    PipelineControlService,
    PipelineDispatch,
    PipelineExecutionSnapshot,
)
from neta_core.config import settings as core_settings
from neta_core.pipeline import (
    SourceManifest,
    effective_runtime_config,
    load_source_manifests,
    source_manifest_hash,
)
from neta_core.pipeline.contracts import RuntimeConfig
from neta_ingest.extraction import SOURCE_REGISTRY, pipeline_execution_scope

SourceRunner = Callable[[Mapping[str, Any]], None]
ResultT = TypeVar("ResultT")

MAX_BACKOFF_SECONDS = 60
DEFAULT_DISPATCH_LIMIT = 100
ERROR_MESSAGE_LIMIT = 8000


class DispatchError(RuntimeError):
    """A dispatch could not be executed for a reason outside the runner itself."""


# --------------------------------------------------------------------------------------------
# manifests + runners
# --------------------------------------------------------------------------------------------


def executable_manifests(directory: str | Path = SOURCE_REGISTRY) -> dict[str, SourceManifest]:
    """Index the manifests that declare an executable runner, keyed by source id."""
    return {
        manifest.id: manifest
        for manifest in load_source_manifests(directory)
        if manifest.orchestration is not None
    }


def load_runner(reference: str) -> SourceRunner:
    """Resolve a ``module:function`` runner reference, refusing imports outside ``neta_ingest``."""
    module_name, separator, attribute = reference.partition(":")
    if not separator:
        raise ValueError(f"runner reference must use module:function syntax: {reference!r}")
    if not module_name.startswith("neta_ingest."):
        raise ValueError(f"runner must live under neta_ingest: {reference!r}")
    value = getattr(importlib.import_module(module_name), attribute)
    if not callable(value):
        raise TypeError(f"source runner is not callable: {reference!r}")
    return cast(SourceRunner, value)


def manifest_runner(manifest: SourceManifest) -> SourceRunner:
    if manifest.orchestration is None:
        raise DispatchError(f"{manifest.id} declares no orchestration runner")
    return load_runner(manifest.orchestration.runner)


# --------------------------------------------------------------------------------------------
# politeness: rate limit + concurrency
# --------------------------------------------------------------------------------------------


@contextmanager
def source_rate_limit(rate_limit_per_minute: int) -> Iterator[float]:
    """Hold the shared HTTP client to at most ``rate_limit_per_minute`` requests per host.

    ``neta_core.http.client`` reads ``settings.http_min_delay_seconds`` on every request, so
    raising it here throttles every fetch the runner makes.  The floor is never lowered below the
    globally configured delay: a manifest may ask us to be *more* polite than the default, never
    less.
    """
    if rate_limit_per_minute < 1:
        raise ValueError("rate_limit_per_minute must be at least 1")
    minimum_delay = 60.0 / rate_limit_per_minute
    previous = core_settings.http_min_delay_seconds
    core_settings.http_min_delay_seconds = max(previous, minimum_delay)
    try:
        yield core_settings.http_min_delay_seconds
    finally:
        core_settings.http_min_delay_seconds = previous


class ConcurrencyLedger:
    """Cap in-flight executions per source at the manifest's ``concurrency_limit``.

    A tick executes dispatches serially, so in practice at most one execution is ever in flight;
    the ledger is the explicit guard that keeps that invariant true (and the single chokepoint any
    future parallel executor has to pass through).  A dispatch that cannot be admitted is simply
    left ``PENDING`` in the control plane and picked up by the next tick.
    """

    def __init__(self) -> None:
        self._in_flight: dict[str, int] = {}

    def in_flight(self, source_key: str) -> int:
        return self._in_flight.get(source_key, 0)

    def admit(self, source_key: str, limit: int) -> bool:
        if limit < 1:
            raise ValueError("concurrency_limit must be at least 1")
        if self._in_flight.get(source_key, 0) >= limit:
            return False
        self._in_flight[source_key] = self._in_flight.get(source_key, 0) + 1
        return True

    def release(self, source_key: str) -> None:
        remaining = self._in_flight.get(source_key, 0) - 1
        if remaining > 0:
            self._in_flight[source_key] = remaining
        else:
            self._in_flight.pop(source_key, None)

    @contextmanager
    def slot(self, source_key: str, limit: int) -> Iterator[bool]:
        admitted = self.admit(source_key, limit)
        try:
            yield admitted
        finally:
            if admitted:
                self.release(source_key)


def retry_backoff_seconds(retry_number: int) -> int:
    """``min(60, 2 ** retry_number)`` — Dagster's ``seconds_to_wait``, retry_number is 0-based."""
    if retry_number < 0:
        raise ValueError("retry_number cannot be negative")
    return min(MAX_BACKOFF_SECONDS, 2**retry_number)


def is_retryable_error(error: BaseException) -> bool:
    """Reject deterministic contract failures; retain retries for operational failures."""
    return not isinstance(error, ValidationError)


# --------------------------------------------------------------------------------------------
# control plane access (async service, synchronous callers)
# --------------------------------------------------------------------------------------------


class ControlPlaneProtocol(Protocol):
    """The four control-plane calls one execution makes (a test may substitute a fake)."""

    def claim_dispatches(
        self, manifests: Mapping[str, SourceManifest]
    ) -> list[PipelineDispatch]: ...

    def start_pipeline_run(
        self,
        pipeline_run_id: int,
        *,
        orchestrator_run_id: str,
        attempt_number: int,
    ) -> PipelineExecutionSnapshot: ...

    def record_pipeline_retry(
        self, pipeline_run_id: int, *, attempt_number: int, error_message: str
    ) -> None: ...

    def complete_pipeline_run(
        self,
        pipeline_run_id: int,
        *,
        status: PipelineRunStatus,
        error_message: str | None = None,
    ) -> None: ...


class ControlPlane:
    """Short-lived async sessions around the single control-plane transaction boundary.

    One engine per call, exactly like the Dagster resource it replaces: a tick may spend hours
    inside a runner and must not hold a pooled Postgres connection open across it.
    """

    def __init__(self, database_url: str, *, dispatch_limit: int = DEFAULT_DISPATCH_LIMIT) -> None:
        self._database_url = database_url
        self._dispatch_limit = dispatch_limit

    def register_manifests(
        self,
        manifests: Sequence[SourceManifest],
        *,
        git_commit_sha: str,
        actor: str,
    ) -> int:
        async def register(service: PipelineControlService) -> int:
            for manifest in manifests:
                await service.register_manifest(
                    manifest,
                    git_commit_sha=git_commit_sha,
                    actor=actor,
                )
            return len(manifests)

        return self._call(register)

    def claim_dispatches(
        self, manifests: Mapping[str, SourceManifest]
    ) -> list[PipelineDispatch]:
        return self._call(
            lambda service: service.claim_dispatches(manifests, limit=self._dispatch_limit)
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
        self, pipeline_run_id: int, *, attempt_number: int, error_message: str
    ) -> None:
        self._call(
            lambda service: service.record_pipeline_retry(
                pipeline_run_id,
                attempt_number=attempt_number,
                error_message=bounded_error(error_message),
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
                error_message=bounded_error(error_message) if error_message else None,
            )
        )

    def survey(self, *, limit: int = DEFAULT_DISPATCH_LIMIT) -> ControlPlaneSurvey:
        """Read-only snapshot of scheduler state for ``--dry-run``.  Claims nothing, writes nothing."""

        async def read(service: PipelineControlService) -> ControlPlaneSurvey:
            states = await service.list_source_states()
            requests = await service.list_run_requests(limit=min(500, max(limit, 1)))
            runs = await service.list_pipeline_runs(limit=min(500, max(limit, 1)))
            return ControlPlaneSurvey(
                states=list(states),
                pending_requests=[
                    (request, source_key)
                    for request, source_key in requests
                    if request.status is PipelineRunRequestStatus.PENDING
                ],
                pending_runs=[
                    (run, source_key)
                    for run, source_key in runs
                    if run.status is PipelineRunStatus.PENDING
                ],
                active_runs=_count_active(runs),
            )

        return self._call(read)

    def _call(
        self, operation: Callable[[PipelineControlService], Awaitable[ResultT]]
    ) -> ResultT:
        async def execute() -> ResultT:
            engine = create_async_engine(async_database_url(self._database_url), pool_pre_ping=True)
            factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            try:
                async with factory() as session:
                    return await operation(PipelineControlService(session))
            finally:
                await engine.dispose()

        return asyncio.run(execute())


def async_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url.replace("+psycopg2", "+asyncpg").replace("+psycopg", "+asyncpg")


def bounded_error(message: str, limit: int = ERROR_MESSAGE_LIMIT) -> str:
    return message if len(message) <= limit else f"{message[: limit - 1]}…"


# --------------------------------------------------------------------------------------------
# execution
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DispatchOutcome:
    source_key: str
    pipeline_run_id: int
    run_key: str
    status: PipelineRunStatus | None
    attempts: int
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status is PipelineRunStatus.SUCCEEDED


def execute_dispatch(
    control: ControlPlaneProtocol,
    dispatch: PipelineDispatch,
    manifest: SourceManifest,
    runner: SourceRunner,
    *,
    orchestrator_run_id: str,
    runtime: RuntimeConfig | None = None,
    sleep: Callable[[float], None] = time.sleep,
    emit: Callable[[str], None] = print,
) -> DispatchOutcome:
    """Run one claimed dispatch to a terminal control-plane status.

    This is the port of the Dagster asset body.  ``attempt_number`` is 1-based (what the control
    plane records); ``retry_number = attempt_number - 1`` is Dagster's 0-based retry counter, which
    drives both the retry-limit comparison and the backoff.
    """
    runtime = runtime or effective_runtime_config(manifest)
    attempt_number = 1
    while True:
        snapshot = control.start_pipeline_run(
            dispatch.pipeline_run_id,
            orchestrator_run_id=orchestrator_run_id,
            attempt_number=attempt_number,
        )
        if snapshot.source_key != manifest.id:
            raise DispatchError(
                f"pipeline run {dispatch.pipeline_run_id} is for {snapshot.source_key}, "
                f"not {manifest.id}"
            )

        try:
            with source_rate_limit(runtime.rate_limit_per_minute) as min_delay:
                emit(
                    f"{manifest.id} run_key={snapshot.run_key} attempt={attempt_number} "
                    f"rate_limit={runtime.rate_limit_per_minute}/min "
                    f"(>= {min_delay:.2f}s between requests)"
                )
                with pipeline_execution_scope(snapshot.run_key):
                    runner(snapshot.parameters)
        except Exception as error:  # noqa: BLE001 - classified below, then re-recorded
            error_message = bounded_error(f"{type(error).__name__}: {error}")
            retry_number = attempt_number - 1
            if is_retryable_error(error) and retry_number < snapshot.retry_limit:
                control.record_pipeline_retry(
                    dispatch.pipeline_run_id,
                    attempt_number=attempt_number,
                    error_message=error_message,
                )
                wait = retry_backoff_seconds(retry_number)
                emit(
                    f"{manifest.id} attempt {attempt_number} failed ({error_message}); "
                    f"retrying in {wait}s "
                    f"({attempt_number}/{snapshot.retry_limit + 1} attempts used)"
                )
                sleep(wait)
                attempt_number += 1
                continue
            control.complete_pipeline_run(
                dispatch.pipeline_run_id,
                status=PipelineRunStatus.FAILED,
                error_message=error_message,
            )
            emit(f"{manifest.id} FAILED after {attempt_number} attempt(s): {error_message}")
            return DispatchOutcome(
                source_key=manifest.id,
                pipeline_run_id=dispatch.pipeline_run_id,
                run_key=snapshot.run_key,
                status=PipelineRunStatus.FAILED,
                attempts=attempt_number,
                error_message=error_message,
            )

        control.complete_pipeline_run(
            dispatch.pipeline_run_id, status=PipelineRunStatus.SUCCEEDED
        )
        emit(f"{manifest.id} SUCCEEDED after {attempt_number} attempt(s)")
        return DispatchOutcome(
            source_key=manifest.id,
            pipeline_run_id=dispatch.pipeline_run_id,
            run_key=snapshot.run_key,
            status=PipelineRunStatus.SUCCEEDED,
            attempts=attempt_number,
        )


def new_orchestrator_run_id(pipeline_run_id: int, *, tick_id: str | None = None) -> str:
    """A globally unique orchestrator id per pipeline run (the column is UNIQUE).

    Inside GitHub Actions the id names the workflow run + attempt so the audit trail points back at
    the job that produced it; elsewhere it is a random CLI id.
    """
    if tick_id is None:
        tick_id = current_tick_id()
    return f"{tick_id}:{pipeline_run_id}"


def current_tick_id() -> str:
    github_run_id = os.getenv("GITHUB_RUN_ID")
    if github_run_id:
        return f"gha-{github_run_id}.{os.getenv('GITHUB_RUN_ATTEMPT', '1')}"
    return f"cli-{uuid4().hex[:16]}"


def run_dispatch_cycle(
    control: ControlPlaneProtocol,
    manifests: Mapping[str, SourceManifest],
    *,
    tick_id: str | None = None,
    runner_factory: Callable[[SourceManifest], SourceRunner] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    emit: Callable[[str], None] = print,
) -> list[DispatchOutcome]:
    """Claim everything due and execute it serially.  Returns one outcome per executed dispatch."""
    tick_id = tick_id or current_tick_id()
    # Resolved here, not as a default argument, so the runner factory stays substitutable.
    runner_factory = runner_factory or manifest_runner
    dispatches = control.claim_dispatches(manifests)
    if not dispatches:
        emit("no due sources or pending run requests")
        return []

    ledger = ConcurrencyLedger()
    outcomes: list[DispatchOutcome] = []
    for dispatch in dispatches:
        manifest = manifests.get(dispatch.source_key)
        if manifest is None:
            # The sensor's "no job registered" branch: the control plane knows a source this
            # deployment does not. Leave the run PENDING rather than failing someone else's work.
            emit(f"ERROR no runner is registered for {dispatch.source_key}; leaving it pending")
            continue
        runtime = effective_runtime_config(manifest)
        with ledger.slot(dispatch.source_key, runtime.concurrency_limit) as admitted:
            if not admitted:
                emit(
                    f"deferring {dispatch.run_key}: {dispatch.source_key} already has "
                    f"{runtime.concurrency_limit} execution(s) in flight"
                )
                continue
            outcomes.append(
                _execute_guarded(
                    control,
                    dispatch,
                    manifest,
                    runtime=runtime,
                    tick_id=tick_id,
                    runner_factory=runner_factory,
                    sleep=sleep,
                    emit=emit,
                )
            )
    return outcomes


def _execute_guarded(
    control: ControlPlaneProtocol,
    dispatch: PipelineDispatch,
    manifest: SourceManifest,
    *,
    runtime: RuntimeConfig,
    tick_id: str,
    runner_factory: Callable[[SourceManifest], SourceRunner],
    sleep: Callable[[float], None],
    emit: Callable[[str], None],
) -> DispatchOutcome:
    """Keep one source's failure from killing the tick, the way separate Dagster runs did.

    A failure *outside* the runner (an unloadable runner, a source-key mismatch) used to be
    reconciled by the run-status sensor; here we close the run out in line so no ``pipeline_run``
    is left dangling in RUNNING.
    """
    try:
        runner = runner_factory(manifest)
        return execute_dispatch(
            control,
            dispatch,
            manifest,
            runner,
            orchestrator_run_id=new_orchestrator_run_id(
                dispatch.pipeline_run_id, tick_id=tick_id
            ),
            runtime=runtime,
            sleep=sleep,
            emit=emit,
        )
    except Exception as error:  # noqa: BLE001 - reconciled below, never swallowed silently
        error_message = bounded_error(f"{type(error).__name__}: {error}")
        emit(f"ERROR {dispatch.source_key} could not be executed: {error_message}")
        try:
            control.complete_pipeline_run(
                dispatch.pipeline_run_id,
                status=PipelineRunStatus.FAILED,
                error_message=error_message,
            )
        except Exception as reconcile_error:  # noqa: BLE001 - best effort, reported
            emit(
                f"ERROR pipeline run {dispatch.pipeline_run_id} could not be reconciled: "
                f"{type(reconcile_error).__name__}: {reconcile_error}"
            )
            return DispatchOutcome(
                source_key=dispatch.source_key,
                pipeline_run_id=dispatch.pipeline_run_id,
                run_key=dispatch.run_key,
                status=None,
                attempts=0,
                error_message=error_message,
            )
        return DispatchOutcome(
            source_key=dispatch.source_key,
            pipeline_run_id=dispatch.pipeline_run_id,
            run_key=dispatch.run_key,
            status=PipelineRunStatus.FAILED,
            attempts=0,
            error_message=error_message,
        )


# --------------------------------------------------------------------------------------------
# dry run: what would this tick claim?
# --------------------------------------------------------------------------------------------


class SourceStateLike(Protocol):
    source_key: str
    enabled: bool
    paused: bool
    quarantined_at: datetime | None
    next_run_at: datetime | None
    frequency_seconds: int | None
    concurrency_limit: int
    rate_limit_per_minute: int
    retry_limit: int
    manifest_hash: str


class RunRequestLike(Protocol):
    id: int
    parameters: dict[str, Any]


class PipelineRunLike(Protocol):
    run_key: str
    manifest_hash: str
    status: PipelineRunStatus


@dataclass(frozen=True, slots=True)
class ControlPlaneSurvey:
    """Everything ``--dry-run`` needs, read through existing read-only service methods."""

    states: list[SourceStateLike]
    pending_requests: list[tuple[RunRequestLike, str]]
    pending_runs: list[tuple[PipelineRunLike, str]]
    active_runs: dict[str, int]


@dataclass(frozen=True, slots=True)
class DuePlan:
    """One execution a real tick would perform, with the politeness knobs it would apply."""

    source_key: str
    trigger: str
    run_key: str
    detail: str
    rate_limit_per_minute: int
    concurrency_limit: int
    retry_limit: int

    def render(self) -> str:
        return (
            f"{self.source_key}\t{self.trigger}\t{self.run_key}\t"
            f"rate={self.rate_limit_per_minute}/min concurrency={self.concurrency_limit} "
            f"retries={self.retry_limit}\t{self.detail}"
        )


def plan_due_set(
    manifests: Mapping[str, SourceManifest],
    survey: ControlPlaneSurvey,
    *,
    now: datetime | None = None,
    limit: int = DEFAULT_DISPATCH_LIMIT,
) -> list[DuePlan]:
    """Mirror ``claim_dispatches``' predicates without claiming or writing anything.

    Order matches a real tick: runs already pending first (they were created by an earlier tick),
    then admin run requests, then due schedules.
    """
    at = now or datetime.now(UTC)
    states = {state.source_key: state for state in survey.states}
    active = dict(survey.active_runs)
    plans: list[DuePlan] = []

    for run, source_key in survey.pending_runs:
        state = states.get(source_key)
        manifest = manifests.get(source_key)
        if state is None or not _executable(state, manifest):
            continue
        assert manifest is not None
        if run.manifest_hash != source_manifest_hash(manifest):
            continue
        plans.append(_plan(state, "pending", run.run_key, "claimed by an earlier tick"))

    for request, source_key in survey.pending_requests:
        state = states.get(source_key)
        manifest = manifests.get(source_key)
        # Admin run requests deliberately ignore `paused` (an operator asked for this run by hand);
        # they still respect enabled, quarantine, manifest drift, and the concurrency limit.
        if state is None or not state.enabled or state.quarantined_at is not None:
            continue
        if not _executable(state, manifest):
            continue
        assert manifest is not None
        if not _reserve(active, source_key, state.concurrency_limit):
            continue
        plans.append(
            _plan(
                state,
                "run_request",
                f"request:{source_key}:{request.id}",
                f"admin request #{request.id} parameters={request.parameters}",
            )
        )

    for state in survey.states:
        manifest = manifests.get(state.source_key)
        if not state.enabled or state.paused or state.quarantined_at is not None:
            continue
        if state.next_run_at is None or state.next_run_at > at or state.frequency_seconds is None:
            continue
        if not _executable(state, manifest):
            continue
        assert manifest is not None
        if not _reserve(active, state.source_key, state.concurrency_limit):
            continue
        plans.append(
            _plan(
                state,
                "scheduled",
                f"schedule:{state.source_key}:{state.next_run_at.isoformat()}",
                f"due since {state.next_run_at.isoformat()} "
                f"(every {state.frequency_seconds}s)",
            )
        )

    return plans[:limit]


def _plan(
    state: SourceStateLike,
    trigger: str,
    run_key: str,
    detail: str,
) -> DuePlan:
    return DuePlan(
        source_key=state.source_key,
        trigger=trigger,
        run_key=run_key,
        detail=detail,
        rate_limit_per_minute=state.rate_limit_per_minute,
        concurrency_limit=state.concurrency_limit,
        retry_limit=state.retry_limit,
    )


def _executable(state: SourceStateLike, manifest: SourceManifest | None) -> bool:
    return bool(
        manifest is not None
        and manifest.orchestration is not None
        and state.manifest_hash == source_manifest_hash(manifest)
    )


def _reserve(active: dict[str, int], source_key: str, concurrency_limit: int) -> bool:
    if active.get(source_key, 0) >= concurrency_limit:
        return False
    active[source_key] = active.get(source_key, 0) + 1
    return True


def _count_active(runs: Sequence[tuple[PipelineRunLike, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run, source_key in runs:
        if run.status in {PipelineRunStatus.PENDING, PipelineRunStatus.RUNNING}:
            counts[source_key] = counts.get(source_key, 0) + 1
    return counts


# --------------------------------------------------------------------------------------------
# CLI entrypoints
# --------------------------------------------------------------------------------------------


def backend_database_url() -> str:
    from neta_backend.config import settings as backend_settings

    return backend_settings.database_url


def run(
    *,
    dry_run: bool = False,
    limit: int = DEFAULT_DISPATCH_LIMIT,
    registry: str | Path = SOURCE_REGISTRY,
    database_url: str | None = None,
    emit: Callable[[str], None] = print,
) -> list[DispatchOutcome]:
    """``neta dispatch`` — one tick of the scheduler.

    Raises :class:`DispatchError` if any executed dispatch ended in a non-success terminal state,
    so a scheduled job turns red instead of failing silently.
    """
    manifests = executable_manifests(registry)
    control = ControlPlane(database_url or backend_database_url(), dispatch_limit=limit)

    if dry_run:
        plans = plan_due_set(manifests, control.survey(limit=limit), limit=limit)
        emit(f"dry run: {len(plans)} execution(s) would start; nothing was claimed or written")
        for plan in plans:
            emit(plan.render())
        return []

    outcomes = run_dispatch_cycle(control, manifests, emit=emit)
    failures = [outcome for outcome in outcomes if not outcome.succeeded]
    emit(
        f"dispatch tick finished: {len(outcomes) - len(failures)} succeeded, "
        f"{len(failures)} failed"
    )
    if failures:
        raise DispatchError(
            "failed dispatches: "
            + ", ".join(f"{failure.source_key}({failure.run_key})" for failure in failures)
        )
    return outcomes


def register_manifests(
    *,
    registry: str | Path = SOURCE_REGISTRY,
    git_commit_sha: str | None = None,
    actor: str = "deployment-controller",
    database_url: str | None = None,
) -> tuple[int, str]:
    """``neta register-manifests`` — reconcile Git manifests into scheduler state.

    Every manifest is registered, not just the executable ones: the control plane tracks
    reference-only sources too.
    """
    manifests = load_source_manifests(registry)
    commit = git_commit_sha or resolve_git_commit()
    ControlPlane(database_url or backend_database_url()).register_manifests(
        manifests,
        git_commit_sha=commit,
        actor=actor,
    )
    return len(manifests), commit


def resolve_git_commit() -> str:
    """The exact deployed commit: explicit env, then the GitHub Actions SHA, then local HEAD."""
    for variable in ("NETA_GIT_COMMIT_SHA", "GITHUB_SHA"):
        value = os.getenv(variable)
        if value and value.strip():
            return value.strip()
    import subprocess

    result = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        cwd=Path(__file__).parents[2],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
