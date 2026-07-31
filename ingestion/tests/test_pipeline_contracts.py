from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from neta_core.pipeline.contracts import (
    AdminRuntimePatch,
    AuthorityRole,
    CanonicalChange,
    ChangeOperation,
    EvidenceRef,
    RawEnvelope,
    SourceConfigRevision,
    SourceManifest,
    apply_runtime_patch,
    effective_runtime_config,
    source_manifest_hash,
)
from neta_core.pipeline.loader import load_source_manifests

ROOT = Path(__file__).parents[2]
REGISTRY = ROOT / "ingestion" / "source_registry"


@pytest.fixture(scope="module")
def manifests() -> dict[str, SourceManifest]:
    loaded = load_source_manifests(REGISTRY)
    return {manifest.id: manifest for manifest in loaded}


def test_representative_source_families_are_validated(
    manifests: dict[str, SourceManifest],
) -> None:
    assert set(manifests) == {
        "digital_sansad.committees",
        "digital_sansad.members",
        "ecourts.case_status",
        "eci.affidavit_pdfs",
        "myneta.candidates",
        "news.google_feed",
        "prs.parliamentary_record",
        "tcpd.surf_bulk",
        "worldbank.india_indicators",
    }
    assert {manifest.ingestion.adapter.value for manifest in manifests.values()} == {
        "api",
        "bulk",
        "crawl",
        "document",
        "feed",
        "gated",
    }
    scheduled_active = {
        manifest.id
        for manifest in manifests.values()
        if manifest.lifecycle.value == "active" and manifest.ingestion.defaults.enabled
    }
    assert scheduled_active == {
        manifest.id
        for manifest in manifests.values()
        if manifest.orchestration is not None
    }


def test_admin_can_pause_resume_and_change_frequency(
    manifests: dict[str, SourceManifest],
) -> None:
    manifest = manifests["digital_sansad.members"]

    paused = effective_runtime_config(manifest, AdminRuntimePatch(paused=True))
    assert paused.paused is True
    assert paused.frequency_seconds == 1800

    resumed_at_new_frequency = effective_runtime_config(
        manifest,
        AdminRuntimePatch(paused=False, frequency_seconds=3600),
    )
    assert resumed_at_new_frequency.paused is False
    assert resumed_at_new_frequency.frequency_seconds == 3600


def test_admin_revisions_accumulate_without_losing_previous_changes(
    manifests: dict[str, SourceManifest],
) -> None:
    manifest = manifests["digital_sansad.members"]

    changed_frequency = apply_runtime_patch(
        manifest,
        manifest.ingestion.defaults,
        AdminRuntimePatch(frequency_seconds=3600),
    )
    paused = apply_runtime_patch(manifest, changed_frequency, AdminRuntimePatch(paused=True))

    assert paused.paused is True
    assert paused.frequency_seconds == 3600


def test_manifest_hash_is_stable_and_content_addressed(
    manifests: dict[str, SourceManifest],
) -> None:
    manifest = manifests["worldbank.india_indicators"]
    same_manifest = SourceManifest.model_validate(manifest.model_dump(mode="json"))
    changed_manifest = same_manifest.model_copy(update={"display_name": "World Bank India series"})

    assert source_manifest_hash(manifest) == source_manifest_hash(same_manifest)
    assert source_manifest_hash(manifest) != source_manifest_hash(changed_manifest)


def test_admin_frequency_change_must_respect_git_guardrails(
    manifests: dict[str, SourceManifest],
) -> None:
    manifest = manifests["digital_sansad.members"]

    with pytest.raises(ValueError, match="more aggressive"):
        effective_runtime_config(manifest, AdminRuntimePatch(frequency_seconds=120))

    with pytest.raises(ValueError, match="allowed maximum"):
        effective_runtime_config(manifest, AdminRuntimePatch(frequency_seconds=172800))


def test_manual_sources_cannot_be_scheduled_by_normal_operator_patch(
    manifests: dict[str, SourceManifest],
) -> None:
    manifest = manifests["ecourts.case_status"]

    with pytest.raises(ValueError, match="manual sources"):
        effective_runtime_config(manifest, AdminRuntimePatch(frequency_seconds=3600))


def test_admin_revisions_are_attributable_and_non_empty() -> None:
    revision = SourceConfigRevision(
        source_id="digital_sansad.members",
        revision=2,
        changed_by="operator@example.org",
        change_reason="Increase refresh frequency while Parliament is in session",
        created_at=datetime(2026, 7, 31, tzinfo=UTC),
        patch=AdminRuntimePatch(frequency_seconds=900),
    )
    assert revision.patch is not None
    assert revision.patch.frequency_seconds == 900

    with pytest.raises(ValidationError, match="must change at least one"):
        AdminRuntimePatch()


def test_unknown_manifest_fields_are_rejected(manifests: dict[str, SourceManifest]) -> None:
    raw = manifests["worldbank.india_indicators"].model_dump(mode="json")
    raw["ingestion"]["frequncy_seconds"] = 60

    with pytest.raises(ValidationError, match="frequncy_seconds"):
        SourceManifest.model_validate(raw)


def test_raw_and_canonical_contracts_require_provenance() -> None:
    fetched_at = datetime(2026, 7, 31, tzinfo=UTC)
    envelope = RawEnvelope(
        envelope_id="digital_sansad.members:ls-123:abc",
        source_id="digital_sansad.members",
        native_id="ls-123",
        source_uri="https://sansad.in/ls/members/biography/123",
        fetched_at=fetched_at,
        content_type="application/json",
        content_hash="a" * 64,
        object_uri="s3://raw/digital_sansad/members/aa/payload.json",
        license_snapshot="public-official",
        pipeline_run_id="run-123",
    )
    change = CanonicalChange(
        entity_type="person",
        natural_key="sansad:ls-123",
        operation=ChangeOperation.UPSERT,
        schema_version=1,
        observed_at=fetched_at,
        attributes={"name": "Example Member"},
        evidence=[
            EvidenceRef(
                envelope_id=envelope.envelope_id,
                source_id=envelope.source_id,
                role=AuthorityRole.PRIMARY,
            )
        ],
        confidence=1,
    )
    assert change.evidence[0].envelope_id == envelope.envelope_id

    with pytest.raises(ValidationError, match="evidence"):
        CanonicalChange(
            entity_type="person",
            natural_key="sansad:ls-123",
            schema_version=1,
            observed_at=fetched_at,
            attributes={"name": "Unproven Member"},
            evidence=[],
            confidence=1,
        )
