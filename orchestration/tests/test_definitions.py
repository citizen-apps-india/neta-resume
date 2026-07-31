from __future__ import annotations

from pathlib import Path

import dagster as dg
import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from neta_core.pipeline import RawEnvelope, load_source_manifests
from neta_orchestration.component import (
    _is_retryable_error,
    _load_runner,
    build_source_definitions,
)
from neta_orchestration.history import DltHistoryResource

ROOT = Path(__file__).parents[2]
REGISTRY = ROOT / "ingestion" / "source_registry"


def test_source_component_builds_loadable_assets_jobs_and_sensors(monkeypatch) -> None:
    monkeypatch.setenv(
        "NETA_BACKEND_DATABASE_URL",
        "postgresql+asyncpg://neta:neta@localhost:5432/neta",
    )
    monkeypatch.setenv(
        "NETA_DATABASE_URL",
        "postgresql+psycopg://neta:neta@localhost:5432/neta",
    )
    definitions = build_source_definitions(load_source_manifests(REGISTRY))
    dg.Definitions.validate_loadable(definitions)

    asset_keys = {
        key.to_user_string()
        for asset in definitions.assets or []
        for key in asset.keys
    }
    assert asset_keys == {
        "ingestion/canonical__digital_sansad__committees",
        "ingestion/canonical__digital_sansad__members",
        "ingestion/canonical__myneta__candidates",
        "ingestion/canonical__news__google_feed",
        "ingestion/canonical__prs__parliamentary_record",
        "ingestion/canonical__worldbank__india_indicators",
    }
    assert {sensor.name for sensor in definitions.sensors or []} == {
        "pipeline_control_dispatch",
        "pipeline_run_cancelled_reconciliation",
        "pipeline_run_failed_reconciliation",
    }


def test_manifest_runner_loader_rejects_out_of_boundary_imports() -> None:
    assert callable(_load_runner("neta_ingest.runners:run_worldbank_indicators"))
    with pytest.raises(ValueError, match="must live under neta_ingest"):
        _load_runner("os:getcwd")


def test_contract_validation_failures_are_not_retried() -> None:
    class Parameters(BaseModel):
        model_config = ConfigDict(extra="forbid")

    with pytest.raises(ValidationError) as captured:
        Parameters.model_validate({"unexpected": True})

    assert _is_retryable_error(captured.value) is False
    assert _is_retryable_error(ConnectionError("temporary upstream failure")) is True


def test_empty_dlt_history_load_does_not_open_a_database() -> None:
    resource = DltHistoryResource(database_url="postgresql://unused")
    assert resource.load("worldbank.india_indicators", []).envelope_count == 0


def test_dlt_history_deduplicates_envelopes(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakePipeline:
        def run(self, resource):
            captured["rows"] = list(resource)
            return type("LoadInfo", (), {"loads_ids": ["load-1"]})()

    monkeypatch.setattr("neta_orchestration.history.dlt.pipeline", lambda **kwargs: FakePipeline())
    envelope = RawEnvelope(
        envelope_id="worldbank.india_indicators:item:abc",
        source_id="worldbank.india_indicators",
        native_id="item",
        source_uri="https://example.test/item",
        fetched_at="2026-07-31T00:00:00Z",
        content_type="application/json",
        content_hash="a" * 64,
        object_uri="raw-cache://aa/item.json",
        license_snapshot="CC-BY-4.0",
        pipeline_run_id="run-1",
    )
    result = DltHistoryResource(database_url="postgresql://unused").load(
        envelope.source_id,
        [envelope, envelope],
    )

    assert result.envelope_count == 1
    assert result.load_ids == ("load-1",)
    assert len(captured["rows"]) == 1
