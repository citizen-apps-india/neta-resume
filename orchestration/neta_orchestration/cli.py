"""Deployment and inspection commands for the orchestration code location."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from neta_backend.config import settings as backend_settings
from neta_core.pipeline import load_source_manifests
from neta_orchestration.control import PipelineControlResource

app = typer.Typer(no_args_is_help=True)
REPOSITORY_ROOT = Path(__file__).parents[2]
SOURCE_REGISTRY = REPOSITORY_ROOT / "ingestion" / "source_registry"


@app.command("register-manifests")
def register_manifests(
    git_commit: Annotated[
        str | None,
        typer.Option(help="Exact deployed Git commit; defaults to NETA_GIT_COMMIT_SHA or HEAD."),
    ] = None,
    actor: Annotated[str, typer.Option(help="Deployment actor recorded in the audit log.")] = (
        "deployment-controller"
    ),
) -> None:
    """Validate and atomically reconcile Git manifests into scheduler state."""
    manifests = load_source_manifests(SOURCE_REGISTRY)
    commit = git_commit or os.getenv("NETA_GIT_COMMIT_SHA") or _head_commit()
    PipelineControlResource(database_url=backend_settings.database_url).register_manifests(
        manifests,
        git_commit_sha=commit,
        actor=actor,
    )
    typer.echo(f"Registered {len(manifests)} source manifests at {commit}")


@app.command("list-sources")
def list_sources() -> None:
    """List validated manifests that currently have executable Dagster jobs."""
    for manifest in load_source_manifests(SOURCE_REGISTRY):
        if manifest.orchestration is not None:
            typer.echo(f"{manifest.id}\t{manifest.orchestration.runner}")


def _head_commit() -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
