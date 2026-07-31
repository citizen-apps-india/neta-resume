"""Manifest-driven Dagster component for source assets, jobs, and control-plane sensors."""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import dagster as dg
from pydantic import ValidationError

from neta_backend.database.models.pipeline import PipelineRunStatus
from neta_core.pipeline import RawEnvelope, RawHistoryMode, SourceManifest, load_source_manifests
from neta_core.pipeline.contracts import source_manifest_hash
from neta_ingest.extraction import pipeline_execution_scope
from neta_orchestration.control import PipelineControlResource
from neta_orchestration.history import DltHistoryResource, HistoryLoadResult

PIPELINE_RUN_ID_TAG = "neta/pipeline_run_id"
SOURCE_ID_TAG = "neta/source_id"
RUN_KEY_TAG = "neta/run_key"

SourceRunner = Callable[[Mapping[str, Any]], None]


@dataclass(frozen=True, slots=True)
class SourceComponent(dg.Component):
    """Load source manifests and build one observable, controllable asset job per source."""

    manifest_directory: Path

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        del context
        return build_source_definitions(load_source_manifests(self.manifest_directory))


def build_source_definitions(manifests: Sequence[SourceManifest]) -> dg.Definitions:
    executable = tuple(manifest for manifest in manifests if manifest.orchestration is not None)
    manifest_index = {manifest.id: manifest for manifest in executable}
    assets_by_source = {
        manifest.id: _source_asset(manifest, _load_runner(manifest.orchestration.runner))
        for manifest in executable
        if manifest.orchestration is not None
    }
    jobs_by_source = {
        source_id: dg.define_asset_job(
            name=f"ingest__{_slug(source_id)}",
            selection=dg.AssetSelection.assets(asset),
            description=f"Manifest-backed ingestion for {source_id}.",
        )
        for source_id, asset in assets_by_source.items()
    }

    @dg.sensor(
        name="pipeline_control_dispatch",
        jobs=list(jobs_by_source.values()),
        minimum_interval_seconds=30,
        default_status=dg.DefaultSensorStatus.RUNNING,
        description="Dispatch due schedules and audited admin run requests from PostgreSQL.",
    )
    def dispatch_sensor(
        context,
        control: PipelineControlResource,
    ):
        dispatches = control.claim_dispatches(manifest_index)
        if not dispatches:
            yield dg.SkipReason("No due sources or pending run requests")
            return
        for dispatch in dispatches:
            job = jobs_by_source.get(dispatch.source_key)
            if job is None:
                context.log.error("No Dagster job is registered for %s", dispatch.source_key)
                continue
            yield dg.RunRequest(
                run_key=dispatch.run_key,
                job_name=job.name,
                tags={
                    PIPELINE_RUN_ID_TAG: str(dispatch.pipeline_run_id),
                    SOURCE_ID_TAG: dispatch.source_key,
                    RUN_KEY_TAG: dispatch.run_key,
                },
            )

    failure_sensor = _run_reconciliation_sensor(
        jobs=list(jobs_by_source.values()),
        dagster_status=dg.DagsterRunStatus.FAILURE,
        pipeline_status=PipelineRunStatus.FAILED,
    )
    cancellation_sensor = _run_reconciliation_sensor(
        jobs=list(jobs_by_source.values()),
        dagster_status=dg.DagsterRunStatus.CANCELED,
        pipeline_status=PipelineRunStatus.CANCELLED,
    )

    return dg.Definitions(
        assets=list(assets_by_source.values()),
        jobs=list(jobs_by_source.values()),
        sensors=[dispatch_sensor, failure_sensor, cancellation_sensor],
        resources={
            "control": PipelineControlResource(
                database_url=dg.EnvVar("NETA_BACKEND_DATABASE_URL")
            ),
            "history": DltHistoryResource(database_url=dg.EnvVar("NETA_DATABASE_URL")),
        },
    )


def _source_asset(manifest: SourceManifest, runner: SourceRunner) -> dg.AssetsDefinition:
    @dg.asset(
        name=f"canonical__{_slug(manifest.id)}",
        key_prefix=["ingestion"],
        group_name=_slug(manifest.source_code),
        description=(
            f"{manifest.display_name}: raw extraction, deterministic conversion, canonical write, "
            "and raw-envelope history registration."
        ),
        code_version=source_manifest_hash(manifest),
        kinds={"python", manifest.ingestion.adapter.value},
    )
    def source_asset(
        context,
        control: PipelineControlResource,
        history: DltHistoryResource,
    ) -> dg.MaterializeResult:
        pipeline_run_id = _required_pipeline_run_id(context.run_tags)
        attempt_number = context.retry_number + 1
        snapshot = control.start_pipeline_run(
            pipeline_run_id,
            orchestrator_run_id=context.run_id,
            attempt_number=attempt_number,
        )
        if snapshot.source_key != manifest.id:
            raise RuntimeError(
                f"pipeline run {pipeline_run_id} is for {snapshot.source_key}, not {manifest.id}"
            )

        envelopes: list[RawEnvelope] = []
        history_result = HistoryLoadResult(envelope_count=0)
        try:
            with pipeline_execution_scope(
                snapshot.run_key,
                artifact_observer=lambda artifact: envelopes.append(artifact.envelope),
            ):
                runner(snapshot.parameters)
            if manifest.orchestration is not None and (
                manifest.orchestration.raw_history is RawHistoryMode.DLT
            ):
                history_result = history.load(manifest.id, envelopes)
        except Exception as error:
            error_message = f"{type(error).__name__}: {error}"
            if _is_retryable_error(error) and context.retry_number < snapshot.retry_limit:
                control.record_pipeline_retry(
                    pipeline_run_id,
                    attempt_number=attempt_number,
                    error_message=error_message,
                )
                raise dg.RetryRequested(
                    max_retries=snapshot.retry_limit,
                    seconds_to_wait=min(60, 2**context.retry_number),
                ) from error
            control.complete_pipeline_run(
                pipeline_run_id,
                status=PipelineRunStatus.FAILED,
                error_message=error_message,
            )
            raise

        control.complete_pipeline_run(
            pipeline_run_id,
            status=PipelineRunStatus.SUCCEEDED,
        )
        return dg.MaterializeResult(
            metadata={
                "source_id": manifest.id,
                "pipeline_run_id": pipeline_run_id,
                "raw_envelopes": history_result.envelope_count,
                "dlt_load_ids": list(history_result.load_ids),
                "contract": manifest.conversion.contract,
                "manifest_hash": source_manifest_hash(manifest),
            }
        )

    return source_asset


def _is_retryable_error(error: Exception) -> bool:
    """Reject deterministic contract failures; retain retries for operational failures."""
    return not isinstance(error, ValidationError)


def _run_reconciliation_sensor(
    *,
    jobs: list[dg.UnresolvedAssetJobDefinition],
    dagster_status: dg.DagsterRunStatus,
    pipeline_status: PipelineRunStatus,
) -> dg.RunStatusSensorDefinition:
    @dg.run_status_sensor(
        name=f"pipeline_run_{pipeline_status.value}_reconciliation",
        run_status=dagster_status,
        monitored_jobs=jobs,
        default_status=dg.DefaultSensorStatus.RUNNING,
    )
    def reconcile(
        context,
        control: PipelineControlResource,
    ) -> None:
        raw_id = context.dagster_run.tags.get(PIPELINE_RUN_ID_TAG)
        if raw_id is None:
            return
        control.complete_pipeline_run(
            int(raw_id),
            status=pipeline_status,
            error_message=(
                f"Dagster run {context.dagster_run.run_id} ended with "
                f"{dagster_status.value.lower()}"
            ),
        )

    return reconcile


def _load_runner(reference: str) -> SourceRunner:
    module_name, separator, attribute = reference.partition(":")
    if not separator:
        raise ValueError(f"runner reference must use module:function syntax: {reference!r}")
    if not module_name.startswith("neta_ingest."):
        raise ValueError(f"runner must live under neta_ingest: {reference!r}")
    value = getattr(importlib.import_module(module_name), attribute)
    if not callable(value):
        raise TypeError(f"source runner is not callable: {reference!r}")
    return cast(SourceRunner, value)


def _required_pipeline_run_id(tags: Mapping[str, str]) -> int:
    value = tags.get(PIPELINE_RUN_ID_TAG)
    if value is None:
        raise RuntimeError(
            "source jobs must be launched through pipeline_control_dispatch; "
            f"missing {PIPELINE_RUN_ID_TAG!r}"
        )
    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(f"invalid {PIPELINE_RUN_ID_TAG}: {value!r}") from error


def _slug(value: str) -> str:
    return value.replace(".", "__").replace("-", "_")
