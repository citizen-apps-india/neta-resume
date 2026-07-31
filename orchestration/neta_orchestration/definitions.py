"""Dagster code-location entrypoint (``dagster dev -m neta_orchestration.definitions``)."""

from pathlib import Path

from neta_orchestration.component import SourceComponent

SOURCE_REGISTRY = Path(__file__).parents[2] / "ingestion" / "source_registry"

# The component context is used only by Dagster's YAML/component loader.  This module is the direct
# Python code-location entrypoint, so construction needs only the version-controlled registry path.
defs = SourceComponent(SOURCE_REGISTRY).build_defs(None)  # type: ignore[arg-type]
