"""Read the version-controlled source registry from the repository image."""

from functools import lru_cache
from pathlib import Path

from neta_core.pipeline import SourceManifest, load_source_manifests

SOURCE_REGISTRY = Path(__file__).parents[3] / "ingestion" / "source_registry"


@lru_cache(maxsize=1)
def source_manifest_index() -> dict[str, SourceManifest]:
    return {
        manifest.id: manifest
        for manifest in load_source_manifests(SOURCE_REGISTRY)
    }


def source_manifest(source_key: str) -> SourceManifest:
    try:
        return source_manifest_index()[source_key]
    except KeyError as error:
        raise KeyError(f"source manifest {source_key!r} does not exist") from error
