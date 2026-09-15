"""The plain-CLI dispatcher: retry classification, politeness, and the dry-run due set.

These are the semantics the Dagster asset owned before the cutover.  A bug here corrupts the audit
trail rather than crashing, so every branch is pinned: a contract failure must never be retried, an
operational failure must retry exactly ``retry_limit`` times with ``min(60, 2 ** retry)`` backoff,
and every retried attempt must be recorded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from neta_backend.database.models.pipeline import PipelineRunStatus
from neta_backend.pipeline.service import (
    PipelineDispatch,
    PipelineExecutionSnapshot,
    StaleRunReconciliation,
)
from neta_core.config import settings as core_settings
from neta_core.pipeline import effective_runtime_config, source_manifest_hash
from neta_core.pipeline.contracts import RuntimeConfig
from neta_ingest import dispatch as d

SOURCE_KEY = "myneta.candidates"
RUN_KEY = f"schedule:{SOURCE_KEY}:2026-09-15T00:00:00+00:00"
NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def manifests() -> dict[str, Any]:
    return d.executable_manifests()


@pytest.fixture
def manifest(manifests):
    return manifests[SOURCE_KEY]


class FakeControl:
    """Records every control-plane call so a test can assert the exact audit trail."""

    def __init__(
        self,
        *,
        snapshot: PipelineExecutionSnapshot,
        claims: list[PipelineDispatch] | None = None,
        stale: list[StaleRunReconciliation] | None = None,
    ) -> None:
        self.snapshot = snapshot
        self.claims = claims or []
        self.stale = stale or []
        self.claim_calls = 0
        self.calls: list[str] = []
        self.stale_after: list[Any] = []
        self.started: list[dict[str, Any]] = []
        self.retries: list[dict[str, Any]] = []
        self.completions: list[dict[str, Any]] = []

    def reconcile_stale_runs(self, *, stale_after):
        self.calls.append("reconcile_stale_runs")
        self.stale_after.append(stale_after)
        return list(self.stale)

    def claim_dispatches(self, manifests):
        self.calls.append("claim_dispatches")
        self.claim_calls += 1
        return list(self.claims)

    def start_pipeline_run(self, pipeline_run_id, *, orchestrator_run_id, attempt_number):
        self.calls.append("start_pipeline_run")
        self.started.append(
            {
                "pipeline_run_id": pipeline_run_id,
                "orchestrator_run_id": orchestrator_run_id,
                "attempt_number": attempt_number,
            }
        )
        return self.snapshot

    def record_pipeline_retry(self, pipeline_run_id, *, attempt_number, error_message):
        self.retries.append(
            {
                "pipeline_run_id": pipeline_run_id,
                "attempt_number": attempt_number,
                "error_message": error_message,
            }
        )

    def complete_pipeline_run(self, pipeline_run_id, *, status, error_message=None):
        self.completions.append(
            {
                "pipeline_run_id": pipeline_run_id,
                "status": status,
                "error_message": error_message,
            }
        )


# The control plane hands the executor the effective config the run was claimed under: repository
# defaults with the operator's admin overlay already applied.
MYNETA_EFFECTIVE = RuntimeConfig(
    frequency_seconds=21600,
    concurrency_limit=1,
    rate_limit_per_minute=20,
    retry_limit=4,
)


def snapshot(
    *,
    retry_limit: int = 3,
    source_key: str = SOURCE_KEY,
    runtime_config: RuntimeConfig | None = None,
) -> PipelineExecutionSnapshot:
    return PipelineExecutionSnapshot(
        pipeline_run_id=41,
        source_key=source_key,
        run_key=RUN_KEY,
        parameters={"cycle": "LS2024", "limit": 5},
        retry_limit=retry_limit,
        runtime_config=runtime_config or MYNETA_EFFECTIVE,
    )


def dispatch_row(runtime_config: RuntimeConfig | None = None) -> PipelineDispatch:
    return PipelineDispatch(
        pipeline_run_id=41,
        source_key=SOURCE_KEY,
        run_key=RUN_KEY,
        runtime_config=runtime_config or MYNETA_EFFECTIVE,
    )


def a_validation_error() -> ValidationError:
    class Parameters(BaseModel):
        model_config = ConfigDict(extra="forbid")

    with pytest.raises(ValidationError) as captured:
        Parameters.model_validate({"unexpected": True})
    return captured.value


def run_execution(control: FakeControl, manifest, runner, sleeps: list[float]):
    return d.execute_dispatch(
        control,
        dispatch_row(),
        manifest,
        runner,
        orchestrator_run_id="cli-test:41",
        sleep=sleeps.append,
        emit=lambda message: None,
    )


# --- retry branch 1: deterministic contract failures are terminal -----------------------------


def test_contract_validation_failure_is_never_retried(manifest) -> None:
    error = a_validation_error()
    control = FakeControl(snapshot=snapshot(retry_limit=3))
    sleeps: list[float] = []

    def runner(parameters):
        raise error

    outcome = run_execution(control, manifest, runner, sleeps)

    assert outcome.status is PipelineRunStatus.FAILED
    assert outcome.attempts == 1
    assert control.retries == []  # a contract failure is never a retry
    assert sleeps == []
    assert len(control.started) == 1
    assert control.completions == [
        {
            "pipeline_run_id": 41,
            "status": PipelineRunStatus.FAILED,
            "error_message": outcome.error_message,
        }
    ]
    assert "ValidationError" in (outcome.error_message or "")


def test_validation_error_is_terminal_even_with_retries_available(manifest) -> None:
    control = FakeControl(snapshot=snapshot(retry_limit=6))
    error = a_validation_error()
    sleeps: list[float] = []
    outcome = run_execution(control, manifest, lambda _: (_ for _ in ()).throw(error), sleeps)

    assert outcome.attempts == 1
    assert control.retries == []


def test_error_classification_matches_the_dagster_predicate() -> None:
    assert d.is_retryable_error(a_validation_error()) is False
    assert d.is_retryable_error(ConnectionError("temporary upstream failure")) is True
    assert d.is_retryable_error(TimeoutError("read timeout")) is True


# --- retry branch 2: operational failures retry to the limit ----------------------------------


def test_operational_failure_retries_to_the_limit_then_fails(manifest) -> None:
    control = FakeControl(snapshot=snapshot(retry_limit=3))
    sleeps: list[float] = []
    attempts: list[Any] = []

    def runner(parameters):
        attempts.append(parameters)
        raise ConnectionError("myneta timed out")

    outcome = run_execution(control, manifest, runner, sleeps)

    # retry_limit=3 means three retries after the first attempt: four attempts in total.
    assert len(attempts) == 4
    assert outcome.attempts == 4
    assert outcome.status is PipelineRunStatus.FAILED
    # Every attempt that was retried is in the audit trail, numbered 1-based.
    assert [retry["attempt_number"] for retry in control.retries] == [1, 2, 3]
    assert all("ConnectionError" in retry["error_message"] for retry in control.retries)
    # min(60, 2 ** retry_number) with retry_number 0-based.
    assert sleeps == [1, 2, 4]
    # The control plane is re-entered per attempt, exactly as Dagster re-ran the asset.
    assert [start["attempt_number"] for start in control.started] == [1, 2, 3, 4]
    assert len(control.completions) == 1
    assert control.completions[0]["status"] is PipelineRunStatus.FAILED


def test_retry_backoff_is_capped_at_sixty_seconds(manifest) -> None:
    control = FakeControl(snapshot=snapshot(retry_limit=8))
    sleeps: list[float] = []

    def runner(parameters):
        raise OSError("connection reset by peer")

    outcome = run_execution(control, manifest, runner, sleeps)

    assert sleeps == [1, 2, 4, 8, 16, 32, 60, 60]
    assert outcome.attempts == 9
    assert [retry["attempt_number"] for retry in control.retries] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_backoff_formula() -> None:
    assert [d.retry_backoff_seconds(n) for n in range(8)] == [1, 2, 4, 8, 16, 32, 60, 60]
    assert d.retry_backoff_seconds(1000) == 60
    with pytest.raises(ValueError, match="cannot be negative"):
        d.retry_backoff_seconds(-1)


def test_zero_retry_limit_fails_on_the_first_operational_error(manifest) -> None:
    control = FakeControl(snapshot=snapshot(retry_limit=0))
    sleeps: list[float] = []

    def runner(parameters):
        raise ConnectionError("upstream down")

    outcome = run_execution(control, manifest, runner, sleeps)

    assert outcome.attempts == 1
    assert control.retries == []
    assert sleeps == []
    assert control.completions[0]["status"] is PipelineRunStatus.FAILED


def test_transient_failure_then_success_records_one_retry(manifest) -> None:
    control = FakeControl(snapshot=snapshot(retry_limit=3))
    sleeps: list[float] = []
    calls = {"count": 0}

    def runner(parameters):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ConnectionError("flaky")

    outcome = run_execution(control, manifest, runner, sleeps)

    assert outcome.status is PipelineRunStatus.SUCCEEDED
    assert outcome.attempts == 2
    assert [retry["attempt_number"] for retry in control.retries] == [1]
    assert sleeps == [1]
    assert control.completions == [
        {"pipeline_run_id": 41, "status": PipelineRunStatus.SUCCEEDED, "error_message": None}
    ]


def test_success_records_no_retry_and_passes_the_claimed_parameters(manifest) -> None:
    control = FakeControl(snapshot=snapshot())
    seen: list[Any] = []
    outcome = run_execution(control, manifest, seen.append, [])

    assert seen == [{"cycle": "LS2024", "limit": 5}]
    assert control.retries == []
    assert outcome.status is PipelineRunStatus.SUCCEEDED
    assert outcome.run_key == RUN_KEY


def test_runner_executes_inside_the_durable_run_scope(manifest) -> None:
    from neta_ingest import extraction

    control = FakeControl(snapshot=snapshot())
    seen: list[str | None] = []

    def runner(parameters):
        seen.append(extraction._orchestrated_run_id.get())

    run_execution(control, manifest, runner, [])

    assert seen == [RUN_KEY]
    assert extraction._orchestrated_run_id.get() is None  # the scope is popped again


def test_source_key_mismatch_never_runs_the_runner(manifest) -> None:
    control = FakeControl(snapshot=snapshot(source_key="worldbank.india_indicators"))
    ran: list[Any] = []

    with pytest.raises(d.DispatchError, match="is for worldbank.india_indicators"):
        run_execution(control, manifest, ran.append, [])

    assert ran == []


# --- politeness: rate limit + concurrency -----------------------------------------------------


def test_manifest_rate_limit_is_applied_while_the_runner_runs(manifest) -> None:
    # myneta.candidates declares 20 requests/minute => at least 3s between requests to that host.
    assert effective_runtime_config(manifest).rate_limit_per_minute == 20
    before = core_settings.http_min_delay_seconds
    control = FakeControl(snapshot=snapshot())
    observed: list[float] = []

    def runner(parameters):
        observed.append(core_settings.http_min_delay_seconds)

    run_execution(control, manifest, runner, [])

    assert observed == [3.0]
    assert core_settings.http_min_delay_seconds == before


def test_rate_limit_is_restored_even_when_the_runner_explodes(manifest) -> None:
    before = core_settings.http_min_delay_seconds
    control = FakeControl(snapshot=snapshot(retry_limit=0))

    def runner(parameters):
        raise ConnectionError("boom")

    run_execution(control, manifest, runner, [])

    assert core_settings.http_min_delay_seconds == before


def test_rate_limit_never_becomes_less_polite_than_the_global_default() -> None:
    # 120/min would be a 0.5s gap; the globally configured 1s floor wins.
    with d.source_rate_limit(120) as delay:
        assert delay == core_settings.http_min_delay_seconds
        assert delay == max(1.0, core_settings.http_min_delay_seconds)
    with d.source_rate_limit(5) as delay:
        assert delay == 12.0
    with pytest.raises(ValueError, match="at least 1"):
        with d.source_rate_limit(0):
            pass


def test_the_executor_obeys_an_operator_override_not_the_manifest_default(manifest) -> None:
    # An operator slowed MyNeta from 20/min to 4/min through the admin console. The claimed run
    # carries that; the manifest still says 20. The executor must use the operator's number.
    slowed = MYNETA_EFFECTIVE.model_copy(update={"rate_limit_per_minute": 4})
    assert effective_runtime_config(manifest).rate_limit_per_minute == 20
    control = FakeControl(snapshot=snapshot(runtime_config=slowed))
    observed: list[float] = []

    run_execution(
        control, manifest, lambda _: observed.append(core_settings.http_min_delay_seconds), []
    )

    assert observed == [15.0]  # 60 / 4, not 60 / 20


def test_the_concurrency_gate_obeys_an_operator_override(manifest) -> None:
    # The operator raised concurrency to 2, so a second claim for the same source still runs.
    widened = MYNETA_EFFECTIVE.model_copy(update={"concurrency_limit": 2})
    control = FakeControl(
        snapshot=snapshot(runtime_config=widened),
        claims=[dispatch_row(widened), dispatch_row(widened)],
    )
    ledger = d.ConcurrencyLedger()
    ledger.admit(SOURCE_KEY, 2)  # one slot of two already taken

    outcomes = d.run_dispatch_cycle(
        control,
        {SOURCE_KEY: manifest},
        runner_factory=lambda _: (lambda parameters: None),
        emit=lambda message: None,
    )

    assert len(outcomes) == 2


def test_every_registry_rate_limit_stays_within_its_manifest_guardrail(manifests) -> None:
    for manifest in manifests.values():
        runtime = effective_runtime_config(manifest)
        guardrails = manifest.ingestion.guardrails
        assert runtime.rate_limit_per_minute <= guardrails.max_rate_limit_per_minute
        assert runtime.concurrency_limit <= guardrails.max_concurrency


def test_concurrency_ledger_caps_in_flight_executions_per_source() -> None:
    ledger = d.ConcurrencyLedger()
    assert ledger.admit("a", 2) is True
    assert ledger.admit("a", 2) is True
    assert ledger.admit("a", 2) is False  # saturated
    assert ledger.admit("b", 1) is True  # a different source is unaffected
    ledger.release("a")
    assert ledger.admit("a", 2) is True
    assert ledger.in_flight("a") == 2
    with pytest.raises(ValueError, match="at least 1"):
        ledger.admit("a", 0)


def test_concurrency_ledger_slot_releases_on_failure() -> None:
    ledger = d.ConcurrencyLedger()
    with pytest.raises(RuntimeError), ledger.slot("a", 1) as admitted:
        assert admitted is True
        raise RuntimeError("runner exploded")
    assert ledger.in_flight("a") == 0


def test_dispatch_cycle_defers_work_beyond_the_concurrency_limit(manifest, monkeypatch) -> None:
    # The claimed run allows one execution at a time; simulate a slot already taken.
    control = FakeControl(snapshot=snapshot(), claims=[dispatch_row()])
    ledger = d.ConcurrencyLedger()
    ledger.admit(SOURCE_KEY, 1)
    monkeypatch.setattr(d, "ConcurrencyLedger", lambda: ledger)
    messages: list[str] = []

    outcomes = d.run_dispatch_cycle(
        control,
        {SOURCE_KEY: manifest},
        runner_factory=lambda _: (lambda parameters: None),
        emit=messages.append,
    )

    assert outcomes == []
    assert control.started == []  # nothing was executed
    assert any("deferring" in message for message in messages)


# --- cycle-level behaviour --------------------------------------------------------------------


def test_dispatch_cycle_runs_each_claim_and_reports_outcomes(manifest) -> None:
    control = FakeControl(snapshot=snapshot(), claims=[dispatch_row()])
    outcomes = d.run_dispatch_cycle(
        control,
        {SOURCE_KEY: manifest},
        runner_factory=lambda _: (lambda parameters: None),
        emit=lambda message: None,
    )

    assert [outcome.succeeded for outcome in outcomes] == [True]
    assert control.claim_calls == 1
    assert control.started[0]["orchestrator_run_id"].endswith(":41")


def test_dispatch_cycle_reconciles_a_failure_outside_the_runner(manifest) -> None:
    # The Dagster run-status sensor used to close these out; the CLI does it in line so no
    # pipeline_run is left dangling in RUNNING.
    control = FakeControl(
        snapshot=snapshot(source_key="worldbank.india_indicators"),
        claims=[dispatch_row()],
    )
    outcomes = d.run_dispatch_cycle(
        control,
        {SOURCE_KEY: manifest},
        runner_factory=lambda _: (lambda parameters: None),
        emit=lambda message: None,
    )

    assert [outcome.status for outcome in outcomes] == [PipelineRunStatus.FAILED]
    assert control.completions[0]["status"] is PipelineRunStatus.FAILED


def test_dispatch_cycle_leaves_unknown_sources_pending(manifest) -> None:
    control = FakeControl(
        snapshot=snapshot(),
        claims=[
            PipelineDispatch(
                pipeline_run_id=7,
                source_key="ghost.source",
                run_key="k",
                runtime_config=MYNETA_EFFECTIVE,
            )
        ],
    )
    messages: list[str] = []
    outcomes = d.run_dispatch_cycle(
        control, {SOURCE_KEY: manifest}, emit=messages.append
    )

    assert outcomes == []
    assert control.completions == []  # somebody else's source is never marked failed
    assert any("no runner is registered" in message for message in messages)


# --- stale-run reconciliation -----------------------------------------------------------------


def stale_run(source_key: str = SOURCE_KEY) -> StaleRunReconciliation:
    return StaleRunReconciliation(
        pipeline_run_id=8,
        source_key=source_key,
        run_key=f"schedule:{source_key}:2026-09-14T00:00:00+00:00",
        started_at=NOW - timedelta(hours=9),
        orchestrator_run_id="gha-123.1:8",
    )


def test_a_tick_reconciles_abandoned_runs_before_it_claims(manifest) -> None:
    # Ordering is the whole point: an abandoned RUNNING row counts against concurrency_limit, so
    # reconciling after the claim would leave the source blocked for another tick.
    control = FakeControl(
        snapshot=snapshot(), claims=[dispatch_row()], stale=[stale_run()]
    )
    messages: list[str] = []

    d.run_dispatch_cycle(
        control,
        {SOURCE_KEY: manifest},
        runner_factory=lambda _: (lambda parameters: None),
        emit=messages.append,
    )

    assert control.calls[:2] == ["reconcile_stale_runs", "claim_dispatches"]
    assert any("reconciled stale run" in message for message in messages)


def test_the_tick_uses_the_conservative_cutoff_by_default(manifest) -> None:
    control = FakeControl(snapshot=snapshot())
    d.run_dispatch_cycle(control, {SOURCE_KEY: manifest}, emit=lambda message: None)

    assert control.stale_after == [timedelta(minutes=d.DEFAULT_STALE_AFTER_MINUTES)]
    # Comfortably above the workflow's timeout-minutes: 120, and equal to the hard ceiling
    # GitHub itself enforces, so it can never cancel a run that is still executing.
    assert d.DEFAULT_STALE_AFTER_MINUTES == 360
    assert timedelta(minutes=d.DEFAULT_STALE_AFTER_MINUTES) >= 3 * timedelta(minutes=120)


def test_the_cutoff_is_configurable(manifest) -> None:
    control = FakeControl(snapshot=snapshot())
    d.run_dispatch_cycle(
        control,
        {SOURCE_KEY: manifest},
        stale_after=timedelta(minutes=720),
        emit=lambda message: None,
    )
    assert control.stale_after == [timedelta(minutes=720)]


def test_reconciliation_still_runs_when_nothing_is_due(manifest) -> None:
    control = FakeControl(snapshot=snapshot(), claims=[], stale=[stale_run()])
    messages: list[str] = []

    outcomes = d.run_dispatch_cycle(control, {SOURCE_KEY: manifest}, emit=messages.append)

    assert outcomes == []
    assert control.calls == ["reconcile_stale_runs", "claim_dispatches"]
    assert any("reconciled stale run" in message for message in messages)


def test_dry_run_reports_stale_runs_without_cancelling_them(manifest, manifests) -> None:
    running = StubRun(
        run_key=RUN_KEY,
        manifest_hash=source_manifest_hash(manifest),
        status=PipelineRunStatus.RUNNING,
        started_at=NOW - timedelta(hours=9),
    )
    fresh = StubRun(
        run_key="schedule:news.google_feed:2026-09-15T11:00:00+00:00",
        manifest_hash="irrelevant",
        status=PipelineRunStatus.RUNNING,
        started_at=NOW - timedelta(minutes=30),
    )
    plan = d.plan_stale_runs(
        survey(running_runs=[(running, SOURCE_KEY), (fresh, "news.google_feed")]),
        stale_after=timedelta(minutes=d.DEFAULT_STALE_AFTER_MINUTES),
        now=NOW,
    )

    assert plan == [(SOURCE_KEY, RUN_KEY)]


def test_a_run_just_under_the_cutoff_is_not_reported_stale(manifest) -> None:
    cutoff = timedelta(minutes=d.DEFAULT_STALE_AFTER_MINUTES)
    just_inside = StubRun(
        run_key=RUN_KEY,
        manifest_hash="x",
        status=PipelineRunStatus.RUNNING,
        started_at=NOW - cutoff + timedelta(minutes=1),
    )
    assert (
        d.plan_stale_runs(
            survey(running_runs=[(just_inside, SOURCE_KEY)]), stale_after=cutoff, now=NOW
        )
        == []
    )


def test_orchestrator_run_ids_are_unique_per_pipeline_run() -> None:
    tick = d.current_tick_id()
    assert d.new_orchestrator_run_id(1, tick_id=tick) != d.new_orchestrator_run_id(2, tick_id=tick)
    assert len(d.new_orchestrator_run_id(1, tick_id=tick)) <= 255


def test_runner_loader_rejects_out_of_boundary_imports() -> None:
    assert callable(d.load_runner("neta_ingest.runners:run_worldbank_indicators"))
    with pytest.raises(ValueError, match="must live under neta_ingest"):
        d.load_runner("os:getcwd")
    with pytest.raises(ValueError, match="module:function"):
        d.load_runner("neta_ingest.runners")


def test_every_registry_manifest_has_a_loadable_runner(manifests) -> None:
    for manifest in manifests.values():
        assert callable(d.manifest_runner(manifest))


# --- dry run: the due set ---------------------------------------------------------------------


@dataclass
class StubState:
    source_key: str
    manifest_hash: str
    enabled: bool = True
    paused: bool = False
    quarantined_at: datetime | None = None
    next_run_at: datetime | None = None
    frequency_seconds: int | None = 21600
    concurrency_limit: int = 1
    rate_limit_per_minute: int = 20
    retry_limit: int = 4


@dataclass
class StubRequest:
    id: int = 9
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class StubRun:
    run_key: str
    manifest_hash: str
    status: PipelineRunStatus = PipelineRunStatus.PENDING
    started_at: datetime | None = None


def survey(
    states=(), pending_requests=(), pending_runs=(), active_runs=None, running_runs=()
) -> d.ControlPlaneSurvey:
    return d.ControlPlaneSurvey(
        states=list(states),
        pending_requests=list(pending_requests),
        pending_runs=list(pending_runs),
        active_runs=dict(active_runs or {}),
        running_runs=list(running_runs),
    )


def due_state(manifest, **overrides) -> StubState:
    values: dict[str, Any] = {
        "source_key": manifest.id,
        "manifest_hash": source_manifest_hash(manifest),
        "next_run_at": NOW - timedelta(minutes=5),
    }
    values.update(overrides)
    return StubState(**values)


def test_dry_run_plans_a_due_schedule(manifest, manifests) -> None:
    state = due_state(manifest)
    plans = d.plan_due_set(manifests, survey(states=[state]), now=NOW)

    assert [plan.source_key for plan in plans] == [SOURCE_KEY]
    plan = plans[0]
    assert plan.trigger == "scheduled"
    assert plan.run_key == f"schedule:{SOURCE_KEY}:{state.next_run_at.isoformat()}"
    assert plan.rate_limit_per_minute == 20
    assert plan.concurrency_limit == 1
    assert plan.retry_limit == 4
    assert SOURCE_KEY in plan.render()


@pytest.mark.parametrize(
    "overrides",
    [
        {"enabled": False},
        {"paused": True},
        {"quarantined_at": NOW},
        {"next_run_at": None},
        {"next_run_at": NOW + timedelta(hours=1)},
        {"frequency_seconds": None},
        {"manifest_hash": "drifted-from-git"},
    ],
    ids=[
        "disabled",
        "paused",
        "quarantined",
        "never-scheduled",
        "not-yet-due",
        "no-frequency",
        "manifest-drift",
    ],
)
def test_dry_run_excludes_sources_a_real_tick_would_skip(manifest, manifests, overrides) -> None:
    plans = d.plan_due_set(manifests, survey(states=[due_state(manifest, **overrides)]), now=NOW)
    assert plans == []


def test_dry_run_excludes_a_source_already_at_its_concurrency_limit(manifest, manifests) -> None:
    state = due_state(manifest, concurrency_limit=1)
    plans = d.plan_due_set(
        manifests, survey(states=[state], active_runs={SOURCE_KEY: 1}), now=NOW
    )
    assert plans == []


def test_dry_run_includes_pending_runs_claimed_by_an_earlier_tick(manifest, manifests) -> None:
    state = due_state(manifest, next_run_at=None)
    run = StubRun(run_key=RUN_KEY, manifest_hash=source_manifest_hash(manifest))
    plans = d.plan_due_set(
        manifests, survey(states=[state], pending_runs=[(run, SOURCE_KEY)]), now=NOW
    )

    assert [(plan.trigger, plan.run_key) for plan in plans] == [("pending", RUN_KEY)]


def test_dry_run_drops_a_pending_run_whose_manifest_drifted(manifest, manifests) -> None:
    state = due_state(manifest, next_run_at=None)
    run = StubRun(run_key=RUN_KEY, manifest_hash="a-previous-commit")
    plans = d.plan_due_set(
        manifests, survey(states=[state], pending_runs=[(run, SOURCE_KEY)]), now=NOW
    )
    assert plans == []


def test_dry_run_includes_an_admin_request_even_when_the_source_is_paused(
    manifest, manifests
) -> None:
    # claim_dispatches deliberately ignores `paused` for hand-made run requests.
    state = due_state(manifest, paused=True, next_run_at=None)
    request = StubRequest(id=12, parameters={"limit": 3})
    plans = d.plan_due_set(
        manifests, survey(states=[state], pending_requests=[(request, SOURCE_KEY)]), now=NOW
    )

    assert [(plan.trigger, plan.run_key) for plan in plans] == [
        ("run_request", f"request:{SOURCE_KEY}:12")
    ]


def test_dry_run_drops_an_admin_request_for_a_quarantined_source(manifest, manifests) -> None:
    state = due_state(manifest, quarantined_at=NOW, next_run_at=None)
    plans = d.plan_due_set(
        manifests,
        survey(states=[state], pending_requests=[(StubRequest(), SOURCE_KEY)]),
        now=NOW,
    )
    assert plans == []


def test_dry_run_counts_a_planned_request_against_the_concurrency_limit(
    manifest, manifests
) -> None:
    # One request plus a due schedule, but concurrency_limit=1: only the request is planned.
    state = due_state(manifest, concurrency_limit=1)
    plans = d.plan_due_set(
        manifests,
        survey(states=[state], pending_requests=[(StubRequest(id=3), SOURCE_KEY)]),
        now=NOW,
    )

    assert [plan.trigger for plan in plans] == ["run_request"]


def test_dry_run_respects_the_limit(manifest, manifests) -> None:
    states = [
        due_state(other, concurrency_limit=4) for other in manifests.values()
    ]
    plans = d.plan_due_set(manifests, survey(states=states), now=NOW, limit=2)
    assert len(plans) == 2


def test_dry_run_claims_nothing_and_writes_nothing(manifest, monkeypatch) -> None:
    calls: list[str] = []

    class RecordingControlPlane:
        def __init__(self, database_url, *, dispatch_limit=100):
            calls.append(f"init:{dispatch_limit}")

        def survey(self, *, limit=100):
            calls.append("survey")
            # d.run() plans against the real wall clock, so make the state unambiguously due.
            return survey(
                states=[due_state(manifest, next_run_at=datetime.now(UTC) - timedelta(days=1))]
            )

        def claim_dispatches(self, manifests):  # pragma: no cover - must never be reached
            raise AssertionError("a dry run must not claim dispatches")

        def start_pipeline_run(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("a dry run must not start pipeline runs")

        def complete_pipeline_run(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("a dry run must not complete pipeline runs")

    monkeypatch.setattr(d, "ControlPlane", RecordingControlPlane)
    messages: list[str] = []

    outcomes = d.run(
        dry_run=True,
        database_url="postgresql+asyncpg://unused/unused",
        emit=messages.append,
    )

    assert outcomes == []
    assert calls == ["init:100", "survey"]
    assert any("dry run" in message for message in messages)
    assert any(SOURCE_KEY in message for message in messages)


def _exploding_runner_factory(manifest):
    def runner(parameters):
        raise ConnectionError("upstream refused the connection")

    return runner


def test_a_failed_dispatch_makes_the_tick_exit_non_zero(manifest, monkeypatch) -> None:
    control = FakeControl(snapshot=snapshot(retry_limit=0), claims=[dispatch_row()])

    class FixedControlPlane:
        def __init__(self, database_url, *, dispatch_limit=100):
            pass

        def __getattr__(self, name):
            return getattr(control, name)

    monkeypatch.setattr(d, "ControlPlane", FixedControlPlane)
    # Patch the factory the cycle actually resolves; never let a test reach a real scraper.
    monkeypatch.setattr(d, "manifest_runner", _exploding_runner_factory)

    with pytest.raises(d.DispatchError, match=SOURCE_KEY):
        d.run(database_url="postgresql+asyncpg://unused/unused", emit=lambda message: None)

    assert control.completions[0]["status"] is PipelineRunStatus.FAILED


def test_async_database_url_normalises_sync_drivers() -> None:
    assert (
        d.async_database_url("postgresql://neta:neta@localhost/neta")
        == "postgresql+asyncpg://neta:neta@localhost/neta"
    )
    assert (
        d.async_database_url("postgresql+psycopg://neta@localhost/neta")
        == "postgresql+asyncpg://neta@localhost/neta"
    )
    assert (
        d.async_database_url("postgresql+asyncpg://neta@localhost/neta")
        == "postgresql+asyncpg://neta@localhost/neta"
    )


def test_error_messages_are_bounded() -> None:
    assert d.bounded_error("short") == "short"
    bounded = d.bounded_error("x" * 9000)
    assert len(bounded) == d.ERROR_MESSAGE_LIMIT
    assert bounded.endswith("…")
