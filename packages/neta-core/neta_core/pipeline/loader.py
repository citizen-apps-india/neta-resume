"""Load and validate version-controlled source manifests."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml

from neta_core.pipeline.contracts import SourceManifest


def load_source_manifest(path: str | Path) -> SourceManifest:
    manifest_path = Path(path)
    with manifest_path.open(encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    if not isinstance(raw, dict):
        raise ValueError(f"source manifest must contain a mapping: {manifest_path}")
    return SourceManifest.model_validate(raw)


def load_source_manifests(directory: str | Path) -> list[SourceManifest]:
    manifest_dir = Path(directory)
    manifests = [load_source_manifest(path) for path in sorted(manifest_dir.glob("*.yaml"))]
    _require_unique_ids(manifests)
    return manifests


def _require_unique_ids(manifests: Iterable[SourceManifest]) -> None:
    seen: set[str] = set()
    for manifest in manifests:
        if manifest.id in seen:
            raise ValueError(f"duplicate source manifest id: {manifest.id}")
        seen.add(manifest.id)
