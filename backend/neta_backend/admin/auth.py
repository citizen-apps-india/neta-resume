"""Local-preview and GitHub-OIDC authentication with signed sessions and CSRF protection.

Two admin auth modes share one signed-session and CSRF mechanism, so every route keeps depending on
the same ``AdminPrincipal``:

- ``local_token``: a single shared bearer/form token for local development. Rejected in production.
- ``github_oidc``: GitHub OAuth (authorization code flow), gated by an allowlist of GitHub logins
  and/or org (optionally team) membership. This is the mode the Kubernetes deployment uses; it is
  permitted in production.

Both modes end the same way: ``set_session_cookies`` mints a signed session + CSRF cookie pair, and
``require_admin`` verifies that pair on every subsequent request.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from neta_backend.config import BackendSettings

SESSION_COOKIE = "neta_admin_session"
CSRF_COOKIE = "neta_admin_csrf"
CSRF_HEADER = "x-csrf-token"
OAUTH_STATE_COOKIE = "neta_admin_oauth_state"
OAUTH_STATE_TTL_SECONDS = 600
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


@dataclass(frozen=True, slots=True)
class AdminPrincipal:
    actor: str
    authentication: str


def require_admin(request: Request) -> AdminPrincipal:
    settings = _settings(request)
    _require_enabled(settings)

    authorization = request.headers.get("authorization", "")
    scheme, separator, credentials = authorization.partition(" ")
    if separator and scheme.lower() == "bearer" and _token_matches(settings, credentials):
        return AdminPrincipal(actor=settings.admin_actor.strip(), authentication="bearer")

    session_token = request.cookies.get(SESSION_COOKIE)
    verified = _verify_session(settings, session_token) if session_token else None
    if verified is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    actor, session_mode = verified
    if request.method in _UNSAFE_METHODS:
        csrf_cookie = request.cookies.get(CSRF_COOKIE, "")
        csrf_header = request.headers.get(CSRF_HEADER, "")
        if not csrf_cookie or not hmac.compare_digest(csrf_cookie, csrf_header):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The CSRF token is missing or invalid",
            )
    # Preserve the historical "session" label for the local-token cookie flow; only the newer
    # GitHub OIDC flow gets its own, more specific label so audit trails show what authenticated it.
    authentication = "session" if session_mode == "local_token" else "github_oidc"
    return AdminPrincipal(actor=actor, authentication=authentication)


def verify_login_token(request: Request, token: str) -> AdminPrincipal:
    settings = _settings(request)
    _require_enabled(settings)
    if not _token_matches(settings, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The local admin token is invalid",
        )
    return AdminPrincipal(actor=settings.admin_actor.strip(), authentication="local_token")


def build_github_login_redirect(request: Request) -> Response:
    """Start the GitHub OAuth authorization-code flow and hand back the redirect + state cookie."""
    settings = _settings(request)
    _require_enabled(settings)
    if settings.admin_auth_mode != "github_oidc":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    state = _sign_oauth_state(settings)
    scope = "read:org" if settings.admin_github_allowed_org else "read:user"
    params = {
        "client_id": settings.admin_github_client_id or "",
        "redirect_uri": settings.admin_github_redirect_uri or "",
        "scope": scope,
        "state": state,
        "allow_signup": "false",
    }
    response = RedirectResponse(
        f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}",
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite="lax",
        max_age=OAUTH_STATE_TTL_SECONDS,
        path="/admin",
    )
    return response


async def complete_github_login(request: Request, *, code: str, state: str) -> AdminPrincipal:
    """Finish the GitHub OAuth callback: validate state, resolve + authorize the GitHub login."""
    settings = _settings(request)
    _require_enabled(settings)
    if settings.admin_auth_mode != "github_oidc":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE, "")
    if (
        not cookie_state
        or not hmac.compare_digest(cookie_state, state)
        or not _oauth_state_is_valid(settings, state)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The GitHub sign-in attempt expired or was tampered with. Please try again.",
        )

    login = await _verify_github_identity(settings, code)
    return AdminPrincipal(actor=login, authentication="github_oidc")


def set_session_cookies(
    response: Response,
    settings: BackendSettings,
    *,
    actor: str | None = None,
    authentication: str = "local_token",
) -> None:
    expires_at = int(time.time()) + settings.admin_session_ttl_seconds
    resolved_actor = (actor if actor is not None else settings.admin_actor).strip()
    session_token = _sign_session(settings, resolved_actor, expires_at, authentication)
    csrf_token = secrets.token_urlsafe(32)
    cookie_options = {
        "secure": settings.admin_cookie_secure,
        "samesite": "strict",
        "max_age": settings.admin_session_ttl_seconds,
        "path": "/admin",
    }
    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        httponly=True,
        **cookie_options,
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        **cookie_options,
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/admin")
    response.delete_cookie(CSRF_COOKIE, path="/admin")
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/admin")


def admin_is_enabled(request: Request) -> bool:
    return _settings(request).admin_auth_mode != "disabled"


def _require_enabled(settings: BackendSettings) -> None:
    if settings.admin_auth_mode == "disabled":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _settings(request: Request) -> BackendSettings:
    return request.app.state.settings


def _token_matches(settings: BackendSettings, candidate: str) -> bool:
    if settings.admin_auth_mode != "local_token" or settings.admin_token is None:
        return False
    expected = settings.admin_token.get_secret_value()
    return bool(candidate) and hmac.compare_digest(expected, candidate)


def _is_github_login_allowed(settings: BackendSettings, login: str) -> bool:
    """Static allowlist check: does not require a network call, safe to run on every request."""
    allowed_logins = settings.github_allowed_logins
    if not allowed_logins:
        return False
    return login.strip().lower() in allowed_logins


async def _is_github_org_member(
    client: httpx.AsyncClient,
    access_token: str,
    org: str,
    login: str,
    team: str | None,
) -> bool:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }
    if team:
        response = await client.get(
            f"https://api.github.com/orgs/{org}/teams/{team}/memberships/{login}",
            headers=headers,
        )
    else:
        response = await client.get(
            f"https://api.github.com/user/memberships/orgs/{org}",
            headers=headers,
        )
    if response.status_code != 200:
        return False
    body = response.json()
    return isinstance(body, dict) and body.get("state") == "active"


async def _verify_github_identity(settings: BackendSettings, code: str) -> str:
    """Exchange the OAuth code for a token, resolve the GitHub login, and enforce the allowlist.

    Returns the GitHub login on success. Raises ``HTTPException`` (401/403) otherwise. This is the
    seam tests replace to avoid making real network calls to GitHub.
    """
    client_secret = (
        settings.admin_github_client_secret.get_secret_value()
        if settings.admin_github_client_secret
        else None
    )
    if not settings.admin_github_client_id or not client_secret:
        raise RuntimeError("github_oidc admin authentication is not fully configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.admin_github_client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": settings.admin_github_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        token_payload = token_response.json() if token_response.status_code == 200 else {}
        access_token = (
            token_payload.get("access_token") if isinstance(token_payload, dict) else None
        )
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub did not issue an access token for that sign-in attempt.",
            )

        user_response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not read the GitHub profile for that sign-in attempt.",
            )
        login = user_response.json().get("login")
        if not isinstance(login, str) or not login.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub did not return a username for that sign-in attempt.",
            )
        login = login.strip()

        allowed = _is_github_login_allowed(settings, login)
        if not allowed and settings.admin_github_allowed_org:
            allowed = await _is_github_org_member(
                client,
                access_token,
                settings.admin_github_allowed_org,
                login,
                settings.admin_github_allowed_team,
            )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This GitHub account is not permitted to access the admin console.",
        )
    return login


def _sign_session(
    settings: BackendSettings,
    actor: str,
    expires_at: int,
    authentication: str,
) -> str:
    payload = json.dumps(
        {
            "actor": actor,
            "expires_at": expires_at,
            "nonce": secrets.token_urlsafe(12),
            "authentication": authentication,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    encoded = _urlsafe_encode(payload)
    signature = hmac.new(_session_secret(settings), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{_urlsafe_encode(signature)}"


def _verify_session(settings: BackendSettings, token: str) -> tuple[str, str] | None:
    encoded, separator, supplied_signature = token.partition(".")
    if not separator:
        return None
    expected_signature = hmac.new(
        _session_secret(settings),
        encoded.encode(),
        hashlib.sha256,
    ).digest()
    try:
        signature = _urlsafe_decode(supplied_signature)
        payload = json.loads(_urlsafe_decode(encoded))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if not hmac.compare_digest(expected_signature, signature):
        return None
    if not isinstance(payload, dict) or payload.get("expires_at", 0) < int(time.time()):
        return None
    actor = payload.get("actor")
    authentication = payload.get("authentication")
    if not isinstance(actor, str) or not actor:
        return None

    if authentication == "local_token":
        if settings.admin_auth_mode != "local_token" or actor != settings.admin_actor.strip():
            return None
        return actor, "local_token"

    if authentication == "github_oidc":
        if settings.admin_auth_mode != "github_oidc":
            return None
        # Re-check the static roster on every request so a revoked login stops working immediately.
        # An org/team-only allowlist (no explicit logins) can't be re-checked without a network call
        # per request, so such sessions are trusted for their bounded TTL, same as local_token.
        if settings.github_allowed_logins and not _is_github_login_allowed(settings, actor):
            return None
        return actor, "github_oidc"

    return None


def _sign_oauth_state(settings: BackendSettings) -> str:
    payload = json.dumps(
        {
            "purpose": "github_oauth_state",
            "expires_at": int(time.time()) + OAUTH_STATE_TTL_SECONDS,
            "nonce": secrets.token_urlsafe(18),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    encoded = _urlsafe_encode(payload)
    signature = hmac.new(_session_secret(settings), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{_urlsafe_encode(signature)}"


def _oauth_state_is_valid(settings: BackendSettings, token: str) -> bool:
    encoded, separator, supplied_signature = token.partition(".")
    if not separator:
        return False
    expected_signature = hmac.new(
        _session_secret(settings),
        encoded.encode(),
        hashlib.sha256,
    ).digest()
    try:
        signature = _urlsafe_decode(supplied_signature)
        payload = json.loads(_urlsafe_decode(encoded))
    except (ValueError, TypeError, json.JSONDecodeError):
        return False
    if not hmac.compare_digest(expected_signature, signature):
        return False
    if not isinstance(payload, dict) or payload.get("purpose") != "github_oauth_state":
        return False
    return payload.get("expires_at", 0) >= int(time.time())


def _session_secret(settings: BackendSettings) -> bytes:
    if settings.admin_session_secret is None:
        raise RuntimeError("admin session secret is not configured")
    return settings.admin_session_secret.get_secret_value().encode()


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _urlsafe_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")
