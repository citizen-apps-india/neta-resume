"""Cloud-neutral ingestion and control-plane contracts."""

from neta_core.pipeline.contracts import (
    AdminRuntimePatch,
    CanonicalChange,
    ConfigRevisionOperation,
    OrchestrationSpec,
    RawHistoryMode,
    RawEnvelope,
    SourceConfigRevision,
    SourceManifest,
    apply_runtime_patch,
    effective_runtime_config,
    source_manifest_hash,
)
from neta_core.pipeline.loader import load_source_manifest, load_source_manifests
from neta_core.pipeline.extraction import (
    ExtractionContext,
    FileRawObjectStore,
    HttpExtractionRequest,
    HttpSourceAdapter,
    RawArtifact,
    RawObjectStore,
    SourceAdapter,
    StoredRawObject,
    capture_raw,
)

__all__ = [
    "AdminRuntimePatch",
    "CanonicalChange",
    "ConfigRevisionOperation",
    "ExtractionContext",
    "FileRawObjectStore",
    "HttpExtractionRequest",
    "HttpSourceAdapter",
    "RawEnvelope",
    "RawHistoryMode",
    "RawArtifact",
    "RawObjectStore",
    "SourceConfigRevision",
    "SourceAdapter",
    "SourceManifest",
    "OrchestrationSpec",
    "StoredRawObject",
    "apply_runtime_patch",
    "capture_raw",
    "effective_runtime_config",
    "load_source_manifest",
    "load_source_manifests",
    "source_manifest_hash",
]
