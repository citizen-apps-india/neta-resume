"""Local-preview authentication with signed sessions and CSRF protection.

The local-token mode is deliberately rejected in production. The Kubernetes deployment step will
replace it with OIDC while preserving the ``AdminPrincipal`` dependency used by the API routes.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, Response, status

from neta_backend.config import BackendSettings

SESSION_COOKIE = "neta_admin_session"
CSRF_COOKIE = "neta_admin_csrf"
CSRF_HEADER = "x-csrf-token"
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


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
    actor = _verify_session(settings, session_token) if session_token else None
    if actor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if request.method in _UNSAFE_METHODS:
        csrf_cookie = request.cookies.get(CSRF_COOKIE, "")
        csrf_header = request.headers.get(CSRF_HEADER, "")
        if not csrf_cookie or not hmac.compare_digest(csrf_cookie, csrf_header):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The CSRF token is missing or invalid",
            )
    return AdminPrincipal(actor=actor, authentication="session")


def verify_login_token(request: Request, token: str) -> AdminPrincipal:
    settings = _settings(request)
    _require_enabled(settings)
    if not _token_matches(settings, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The local admin token is invalid",
        )
    return AdminPrincipal(actor=settings.admin_actor.strip(), authentication="local_token")


def set_session_cookies(response: Response, settings: BackendSettings) -> None:
    expires_at = int(time.time()) + settings.admin_session_ttl_seconds
    session_token = _sign_session(settings, settings.admin_actor.strip(), expires_at)
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


def _sign_session(settings: BackendSettings, actor: str, expires_at: int) -> str:
    payload = json.dumps(
        {"actor": actor, "expires_at": expires_at, "nonce": secrets.token_urlsafe(12)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    encoded = _urlsafe_encode(payload)
    signature = hmac.new(_session_secret(settings), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{_urlsafe_encode(signature)}"


def _verify_session(settings: BackendSettings, token: str) -> str | None:
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
    if actor != settings.admin_actor.strip():
        return None
    return actor


def _session_secret(settings: BackendSettings) -> bytes:
    if settings.admin_session_secret is None:
        raise RuntimeError("admin session secret is not configured")
    return settings.admin_session_secret.get_secret_value().encode()


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _urlsafe_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")
