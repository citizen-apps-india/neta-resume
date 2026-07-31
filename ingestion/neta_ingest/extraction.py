"""Run-scoped construction of manifest-backed extraction contexts."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from neta_core.pipeline import (
    ExtractionContext,
    FileRawObjectStore,
    RawObjectStore,
    RawArtifact,
    SourceManifest,
    load_source_manifests,
)

SOURCE_REGISTRY = Path(__file__).parents[1] / "source_registry"

_orchestrated_run_id: ContextVar[str | None] = ContextVar(
    "neta_orchestrated_run_id",
    default=None,
)
_artifact_observer: ContextVar[Callable[[RawArtifact], None] | None] = ContextVar(
    "neta_artifact_observer",
    default=None,
)


@lru_cache(maxsize=1)
def _manifest_index() -> dict[str, SourceManifest]:
    return {manifest.id: manifest for manifest in load_source_manifests(SOURCE_REGISTRY)}


def new_pipeline_run_id(source_id: str) -> str:
    """Create a transitional run ID until the orchestrator supplies its durable run key."""
    return f"{source_id}:{uuid4().hex}"


def source_extraction_context(
    source_id: str,
    *,
    pipeline_run_id: str | None = None,
    object_store: RawObjectStore | None = None,
    artifact_observer: Callable[[RawArtifact], None] | None = None,
) -> ExtractionContext:
    """Bind a source execution to its validated manifest, run ID, and raw object store."""
    try:
        manifest = _manifest_index()[source_id]
    except KeyError as error:
        raise ValueError(f"source manifest {source_id!r} is not registered") from error
    return ExtractionContext(
        manifest=manifest,
        pipeline_run_id=(
            pipeline_run_id
            or _orchestrated_run_id.get()
            or new_pipeline_run_id(source_id)
        ),
        object_store=object_store if object_store is not None else FileRawObjectStore(),
        artifact_observer=artifact_observer or _artifact_observer.get(),
    )


@contextmanager
def pipeline_execution_scope(
    pipeline_run_id: str,
    *,
    artifact_observer: Callable[[RawArtifact], None] | None = None,
) -> Iterator[None]:
    """Propagate one durable orchestrator run ID through existing pipeline entrypoints."""
    if not pipeline_run_id.strip():
        raise ValueError("pipeline_run_id cannot be empty")
    run_token = _orchestrated_run_id.set(pipeline_run_id)
    observer_token = _artifact_observer.set(artifact_observer)
    try:
        yield
    finally:
        _artifact_observer.reset(observer_token)
        _orchestrated_run_id.reset(run_token)
