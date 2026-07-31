"""Authenticated admin pages and JSON control API."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from neta_core.pipeline.contracts import SourceManifest

from neta_backend.admin.auth import (
    AdminPrincipal,
    clear_session_cookies,
    require_admin,
    set_session_cookies,
    verify_login_token,
)
from neta_backend.admin.schemas import (
    CreateRunRequest,
    QuarantineRequest,
    RuntimeChangeRequest,
    RuntimeResetRequest,
)
from neta_backend.database.models.pipeline import (
    PipelineRun,
    PipelineRunRequest,
    PipelineSourceConfigRevision,
    PipelineSourceState,
)
from neta_backend.database.session import get_db_session
from neta_backend.pipeline.registry import source_manifest, source_manifest_index
from neta_backend.pipeline.service import (
    ControlPlaneError,
    IdempotencyConflict,
    ManifestOutOfSync,
    NoRuntimeChange,
    PipelineControlService,
    SourceNotRegistered,
    SourceQuarantined,
)

TEMPLATE_DIRECTORY = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=TEMPLATE_DIRECTORY)

admin_page_router = APIRouter(include_in_schema=False)
admin_api_router = APIRouter(
    prefix="/admin/api",
    tags=["ingestion administration"],
    dependencies=[Depends(require_admin)],
)

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
Principal = Annotated[AdminPrincipal, Depends(require_admin)]


@admin_page_router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    if request.app.state.settings.admin_auth_mode == "disabled":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return templates.TemplateResponse(request=request, name="login.html", context={})


@admin_page_router.post("/admin/login", response_class=HTMLResponse)
async def login(request: Request, token: Annotated[str, Form()]) -> HTMLResponse:
    try:
        verify_login_token(request, token)
    except HTTPException as error:
        if error.status_code == status.HTTP_404_NOT_FOUND:
            raise
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "That access token was not accepted."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    response = RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)
    set_session_cookies(response, request.app.state.settings)
    return response


@admin_page_router.get("/admin", response_class=HTMLResponse)
async def admin_console(request: Request) -> HTMLResponse:
    try:
        principal = require_admin(request)
    except HTTPException as error:
        if error.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        raise
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"actor": principal.actor},
    )


@admin_page_router.post("/admin/logout")
async def logout(request: Request, principal: Principal) -> RedirectResponse:
    del request, principal
    response = RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_session_cookies(response)
    return response


@admin_api_router.get("/sources")
async def list_sources(db_session: DatabaseSession) -> dict[str, Any]:
    service = PipelineControlService(db_session)
    states = {state.source_key: state for state in await service.list_source_states()}
    recent_runs = await service.list_pipeline_runs(limit=500)
    latest_runs: dict[str, PipelineRun] = {}
    for run, source_key in recent_runs:
        latest_runs.setdefault(source_key, run)
    manifests = source_manifest_index()
    return {
        "sources": [
            _source_payload(manifest, states.get(source_key), latest_runs.get(source_key))
            for source_key, manifest in sorted(manifests.items())
        ]
    }


@admin_api_router.get("/sources/{source_key}")
async def get_source(source_key: str, db_session: DatabaseSession) -> dict[str, Any]:
    manifest = _manifest_or_404(source_key)
    service = PipelineControlService(db_session)
    try:
        state = await service.source_state(source_key)
        revisions = await service.list_config_revisions(source_key, limit=50)
    except SourceNotRegistered:
        state = None
        revisions = []
    runs = await service.list_pipeline_runs(source_key=source_key, limit=50)
    return {
        "source": _source_payload(manifest, state, runs[0][0] if runs else None),
        "manifest": manifest.model_dump(mode="json"),
        "revisions": [_revision_payload(revision) for revision in revisions],
        "runs": [_run_payload(run, key) for run, key in runs],
    }


@admin_api_router.patch("/sources/{source_key}/runtime")
async def change_runtime(
    source_key: str,
    body: RuntimeChangeRequest,
    db_session: DatabaseSession,
    principal: Principal,
) -> dict[str, Any]:
    manifest = _manifest_or_404(source_key)
    try:
        revision = await PipelineControlService(db_session).change_runtime(
            manifest,
            body.patch,
            changed_by=principal.actor,
            change_reason=body.reason,
        )
    except (ControlPlaneError, ValueError) as error:
        raise _control_error(error) from error
    return {"revision": _revision_payload(revision)}


@admin_api_router.post("/sources/{source_key}/runtime/reset")
async def reset_runtime(
    source_key: str,
    body: RuntimeResetRequest,
    db_session: DatabaseSession,
    principal: Principal,
) -> dict[str, Any]:
    manifest = _manifest_or_404(source_key)
    try:
        revision = await PipelineControlService(db_session).reset_runtime_to_defaults(
            manifest,
            changed_by=principal.actor,
            change_reason=body.reason,
        )
    except (ControlPlaneError, ValueError) as error:
        raise _control_error(error) from error
    return {"revision": _revision_payload(revision)}


@admin_api_router.post("/sources/{source_key}/quarantine")
async def set_quarantine(
    source_key: str,
    body: QuarantineRequest,
    db_session: DatabaseSession,
    principal: Principal,
) -> dict[str, Any]:
    manifest = _manifest_or_404(source_key)
    try:
        state = await PipelineControlService(db_session).set_quarantine(
            manifest,
            quarantined=body.quarantined,
            changed_by=principal.actor,
            change_reason=body.reason,
        )
    except (ControlPlaneError, ValueError) as error:
        raise _control_error(error) from error
    return {"source": _source_payload(manifest, state, None)}


@admin_api_router.post("/sources/{source_key}/runs")
async def request_run(
    source_key: str,
    body: CreateRunRequest,
    db_session: DatabaseSession,
    principal: Principal,
) -> dict[str, Any]:
    _manifest_or_404(source_key)
    try:
        request, created = await PipelineControlService(db_session).request_run(
            source_key,
            body.request_type,
            parameters=body.parameters,
            idempotency_key=body.idempotency_key,
            requested_by=principal.actor,
            request_reason=body.reason,
        )
    except (ControlPlaneError, ValueError) as error:
        raise _control_error(error) from error
    return {
        "request": _run_request_payload(request, source_key),
        "created": created,
    }


@admin_api_router.get("/runs")
async def list_runs(
    db_session: DatabaseSession,
    source_key: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    if source_key is not None:
        _manifest_or_404(source_key)
    runs = await PipelineControlService(db_session).list_pipeline_runs(
        source_key=source_key,
        limit=limit,
    )
    return {"runs": [_run_payload(run, key) for run, key in runs]}


@admin_api_router.get("/activity")
async def list_execution_activity(
    db_session: DatabaseSession,
    source_key: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    if source_key is not None:
        _manifest_or_404(source_key)
    service = PipelineControlService(db_session)
    runs = await service.list_pipeline_runs(source_key=source_key, limit=limit)
    requests = await service.list_run_requests(source_key=source_key, limit=limit)
    return {
        "runs": [_run_payload(run, key) for run, key in runs],
        "requests": [
            _run_request_payload(request, key) for request, key in requests
        ],
    }


def _manifest_or_404(source_key: str) -> SourceManifest:
    try:
        return source_manifest(source_key)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


def _control_error(error: Exception) -> HTTPException:
    if isinstance(error, SourceNotRegistered):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(
        error,
        (ManifestOutOfSync, NoRuntimeChange, SourceQuarantined, IdempotencyConflict),
    ):
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(status_code=code, detail=str(error))


def _source_payload(
    manifest: SourceManifest,
    state: PipelineSourceState | None,
    latest_run: PipelineRun | None,
) -> dict[str, Any]:
    defaults = manifest.ingestion.defaults.model_dump(mode="json")
    return {
        "source_key": manifest.id,
        "display_name": manifest.display_name,
        "publisher": manifest.publisher,
        "lifecycle": manifest.lifecycle.value,
        "adapter": manifest.ingestion.adapter.value,
        "trigger_mode": manifest.ingestion.trigger.mode.value,
        "trigger_profile": manifest.ingestion.trigger.profile,
        "authority_role": manifest.authority.role.value,
        "trust_tier": manifest.authority.trust_tier,
        "license": manifest.rights.license,
        "registered": state is not None,
        "enabled": state.enabled if state else defaults["enabled"],
        "paused": state.paused if state else defaults["paused"],
        "effective_config": state.effective_config if state else defaults,
        "admin_overrides": state.admin_overrides if state else {},
        "guardrails": manifest.ingestion.guardrails.model_dump(mode="json"),
        "active_revision": state.active_revision if state else 0,
        "next_run_at": state.next_run_at if state else None,
        "last_run_at": state.last_run_at if state else None,
        "last_success_at": state.last_success_at if state else None,
        "last_failure_at": state.last_failure_at if state else None,
        "consecutive_failures": state.consecutive_failures if state else 0,
        "quarantined_at": state.quarantined_at if state else None,
        "quarantined_by": state.quarantined_by if state else None,
        "quarantined_reason": state.quarantined_reason if state else None,
        "manifest_hash": state.manifest_hash if state else None,
        "git_commit_sha": state.git_commit_sha if state else None,
        "latest_run": _run_payload(latest_run, manifest.id) if latest_run else None,
    }


def _revision_payload(revision: PipelineSourceConfigRevision) -> dict[str, Any]:
    return {
        "id": revision.id,
        "revision": revision.revision,
        "operation": revision.operation.value,
        "patch": revision.patch,
        "effective_config": revision.effective_config,
        "manifest_hash": revision.manifest_hash,
        "git_commit_sha": revision.git_commit_sha,
        "changed_by": revision.changed_by,
        "change_reason": revision.change_reason,
        "created_at": revision.created_at,
    }


def _run_payload(run: PipelineRun, source_key: str) -> dict[str, Any]:
    return {
        "id": run.id,
        "source_key": source_key,
        "run_request_id": run.run_request_id,
        "run_key": run.run_key,
        "orchestrator_run_id": run.orchestrator_run_id,
        "trigger": run.trigger.value,
        "status": run.status.value,
        "config_revision": run.config_revision,
        "parameters": run.parameters,
        "attempt_count": run.attempt_count,
        "retry_limit": run.retry_limit,
        "scheduled_for": run.scheduled_for,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "error_message": run.error_message,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }


def _run_request_payload(
    request: PipelineRunRequest,
    source_key: str | None = None,
) -> dict[str, Any]:
    return {
        "id": request.id,
        "source_key": source_key,
        "request_type": request.request_type.value,
        "status": request.status.value,
        "parameters": request.parameters,
        "idempotency_key": request.idempotency_key,
        "requested_by": request.requested_by,
        "request_reason": request.request_reason,
        "requested_at": request.requested_at,
        "accepted_at": request.accepted_at,
        "started_at": request.started_at,
        "completed_at": request.completed_at,
        "error_message": request.error_message,
    }
