from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr, ValidationError

from neta_core.pipeline.contracts import ConfigRevisionOperation

from neta_backend.admin import auth as admin_auth
from neta_backend.admin.auth import CSRF_COOKIE, CSRF_HEADER, OAUTH_STATE_COOKIE
from neta_backend.config import BackendSettings
from neta_backend.database.session import get_db_session
from neta_backend.main import create_app
from neta_backend.pipeline.service import PipelineControlService

ADMIN_TOKEN = "local-preview-token-with-24-chars"
SESSION_SECRET = "local-preview-session-secret-with-more-than-32-chars"
GITHUB_CLIENT_ID = "test-github-client-id"
GITHUB_CLIENT_SECRET = "test-github-client-secret-value"
GITHUB_REDIRECT_URI = "http://test/admin/login/github/callback"


def admin_settings() -> BackendSettings:
    return BackendSettings(
        database_url="sqlite+aiosqlite:///:memory:",
        environment="test",
        admin_auth_mode="local_token",
        admin_token=SecretStr(ADMIN_TOKEN),
        admin_session_secret=SecretStr(SESSION_SECRET),
        admin_actor="test-operator",
        admin_cookie_secure=False,
    )


def admin_settings_github(**overrides: object) -> BackendSettings:
    fields: dict[str, object] = dict(
        database_url="sqlite+aiosqlite:///:memory:",
        environment="test",
        admin_auth_mode="github_oidc",
        admin_session_secret=SecretStr(SESSION_SECRET),
        admin_actor="test-operator",
        admin_cookie_secure=False,
        admin_github_client_id=GITHUB_CLIENT_ID,
        admin_github_client_secret=SecretStr(GITHUB_CLIENT_SECRET),
        admin_github_redirect_uri=GITHUB_REDIRECT_URI,
        admin_github_allowed_logins="octocat,ana-dev",
    )
    fields.update(overrides)
    return BackendSettings(**fields)


def admin_app(settings: BackendSettings | None = None):
    application = create_app(settings or admin_settings())

    async def fake_session() -> AsyncIterator[object]:
        yield object()

    application.dependency_overrides[get_db_session] = fake_session
    return application


async def test_admin_surface_is_not_exposed_when_disabled() -> None:
    application = create_app(
        BackendSettings(database_url="sqlite+aiosqlite:///:memory:", environment="test")
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        response = await client.get("/admin")

    assert response.status_code == 404


async def test_admin_api_accepts_bearer_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_states(self: PipelineControlService) -> list[object]:
        return []

    async def no_runs(self: PipelineControlService, **kwargs: object) -> list[object]:
        return []

    async def no_requests(self: PipelineControlService, **kwargs: object) -> list[object]:
        return []

    monkeypatch.setattr(PipelineControlService, "list_source_states", no_states)
    monkeypatch.setattr(PipelineControlService, "list_pipeline_runs", no_runs)
    monkeypatch.setattr(PipelineControlService, "list_run_requests", no_requests)
    application = admin_app()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        unauthenticated = await client.get("/admin/api/sources")
        authenticated = await client.get(
            "/admin/api/sources",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
        activity = await client.get(
            "/admin/api/activity",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 200
    sources = authenticated.json()["sources"]
    assert {source["source_key"] for source in sources} >= {
        "myneta.candidates",
        "digital_sansad.members",
        "prs.parliamentary_record",
    }
    assert all(source["registered"] is False for source in sources)
    assert activity.status_code == 200
    assert activity.json() == {"runs": [], "requests": []}


async def test_login_session_and_csrf_protect_runtime_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    async def change_runtime(
        self: PipelineControlService,
        manifest: object,
        patch: object,
        *,
        changed_by: str,
        change_reason: str,
        **kwargs: object,
    ) -> object:
        observed.update(
            source_key=manifest.id,
            patch=patch.model_dump(exclude_unset=True),
            changed_by=changed_by,
            reason=change_reason,
        )
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=1,
            revision=1,
            operation=ConfigRevisionOperation.PATCH,
            patch=patch.model_dump(exclude_unset=True),
            effective_config={"paused": True},
            manifest_hash="a" * 64,
            git_commit_sha="test-sha",
            changed_by=changed_by,
            change_reason=change_reason,
            created_at=now,
        )

    monkeypatch.setattr(PipelineControlService, "change_runtime", change_runtime)
    application = admin_app()
    body = {"patch": {"paused": True}, "reason": "maintenance window"}

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        bad_login = await client.post("/admin/login", data={"token": "wrong"})
        login = await client.post("/admin/login", data={"token": ADMIN_TOKEN})
        admin_page = await client.get("/admin")
        without_csrf = await client.patch(
            "/admin/api/sources/myneta.candidates/runtime",
            json=body,
        )
        csrf = client.cookies.get(CSRF_COOKIE)
        with_csrf = await client.patch(
            "/admin/api/sources/myneta.candidates/runtime",
            json=body,
            headers={CSRF_HEADER: csrf},
        )

    assert bad_login.status_code == 401
    assert login.status_code == 303
    assert login.headers["location"] == "/admin"
    assert admin_page.status_code == 200
    assert "Ingestion desk" in admin_page.text
    assert without_csrf.status_code == 403
    assert with_csrf.status_code == 200
    assert observed == {
        "source_key": "myneta.candidates",
        "patch": {"paused": True},
        "changed_by": "test-operator",
        "reason": "maintenance window",
    }


def test_local_token_authentication_is_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="prohibited in production"):
        BackendSettings(
            environment="production",
            admin_auth_mode="local_token",
            admin_token=SecretStr(ADMIN_TOKEN),
            admin_session_secret=SecretStr(SESSION_SECRET),
        )


def test_github_oidc_authentication_is_permitted_in_production() -> None:
    settings = BackendSettings(
        environment="production",
        admin_auth_mode="github_oidc",
        admin_session_secret=SecretStr(SESSION_SECRET),
        admin_github_client_id=GITHUB_CLIENT_ID,
        admin_github_client_secret=SecretStr(GITHUB_CLIENT_SECRET),
        admin_github_redirect_uri="https://admin.example.com/admin/login/github/callback",
        admin_github_allowed_logins="octocat",
    )
    assert settings.admin_auth_mode == "github_oidc"


def test_github_oidc_requires_an_allowlist() -> None:
    with pytest.raises(ValidationError, match="ALLOWED_LOGINS"):
        BackendSettings(
            environment="test",
            admin_auth_mode="github_oidc",
            admin_session_secret=SecretStr(SESSION_SECRET),
            admin_github_client_id=GITHUB_CLIENT_ID,
            admin_github_client_secret=SecretStr(GITHUB_CLIENT_SECRET),
            admin_github_redirect_uri=GITHUB_REDIRECT_URI,
        )


async def test_github_oidc_happy_path_allows_allowlisted_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_identity(settings: BackendSettings, code: str) -> str:
        assert settings.admin_auth_mode == "github_oidc"
        assert code == "good-code"
        return "octocat"

    monkeypatch.setattr(admin_auth, "_verify_github_identity", fake_identity)

    observed: dict[str, object] = {}

    async def change_runtime(
        self: PipelineControlService,
        manifest: object,
        patch: object,
        *,
        changed_by: str,
        change_reason: str,
        **kwargs: object,
    ) -> object:
        observed.update(changed_by=changed_by)
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=1,
            revision=1,
            operation=ConfigRevisionOperation.PATCH,
            patch=patch.model_dump(exclude_unset=True),
            effective_config={"paused": True},
            manifest_hash="a" * 64,
            git_commit_sha="test-sha",
            changed_by=changed_by,
            change_reason=change_reason,
            created_at=now,
        )

    monkeypatch.setattr(PipelineControlService, "change_runtime", change_runtime)
    application = admin_app(admin_settings_github())

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        start = await client.get("/admin/login/github")
        assert start.status_code == status.HTTP_302_FOUND
        oauth_state = client.cookies.get(OAUTH_STATE_COOKIE)
        assert oauth_state

        callback = await client.get(
            "/admin/login/github/callback",
            params={"code": "good-code", "state": oauth_state},
        )
        assert callback.status_code == status.HTTP_303_SEE_OTHER
        assert callback.headers["location"] == "/admin"

        admin_page = await client.get("/admin")
        assert admin_page.status_code == 200

        csrf = client.cookies.get(CSRF_COOKIE)
        runtime_change = await client.patch(
            "/admin/api/sources/myneta.candidates/runtime",
            json={"patch": {"paused": True}, "reason": "rotate"},
            headers={CSRF_HEADER: csrf},
        )

    assert runtime_change.status_code == 200
    assert observed["changed_by"] == "octocat"


async def test_github_oidc_rejects_non_allowlisted_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_identity(settings: BackendSettings, code: str) -> str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This GitHub account is not permitted to access the admin console.",
        )

    monkeypatch.setattr(admin_auth, "_verify_github_identity", fake_identity)
    application = admin_app(admin_settings_github())

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/login/github")
        oauth_state = client.cookies.get(OAUTH_STATE_COOKIE)
        assert oauth_state

        callback = await client.get(
            "/admin/login/github/callback",
            params={"code": "someone-elses-code", "state": oauth_state},
        )
        assert callback.status_code == status.HTTP_403_FORBIDDEN
        assert "not permitted" in callback.text

        after = await client.get("/admin")

    assert after.status_code == status.HTTP_303_SEE_OTHER
    assert after.headers["location"] == "/admin/login"
