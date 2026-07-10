"""Per-IP rate limiting for the public read API.

A fixed-window per-IP cap (via the `limits` library) applied to every request by RateLimitMiddleware,
except cheap/hot paths: the keep-warm `/health` ping and the disk-cached photo proxy (`/persons/{id}/photo`),
which a directory page fires in bursts of dozens from one browser IP. Defence-in-depth — the per-statement DB
timeout (deps.py) already bounds any single query's cost; this caps request *floods*.

Behind Render's proxy, `request.client.host` is the proxy, so we key on the left-most `X-Forwarded-For`
entry. Server-rendered pages call this API from the web backend's single IP, but those calls are ISR-cached
(~1/hr per path), so their aggregate stays well under the limit; if the web backend is ever throttled, add a
trusted-origin bypass (shared-secret header) rather than raising this ceiling.

Storage is in-process memory — correct for the single-instance Render deployment; a multi-worker/multi-instance
setup would need shared storage (e.g. Redis) for a global count.
"""

from __future__ import annotations

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_LIMIT = parse("120/minute")
_limiter = FixedWindowRateLimiter(MemoryStorage())


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "anonymous"


def _is_exempt(path: str) -> bool:
    return path == "/health" or path.endswith("/photo")


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not _is_exempt(request.url.path) and not _limiter.hit(_LIMIT, _client_ip(request)):
            return JSONResponse(
                {"detail": "Rate limit exceeded. Try again shortly."},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        return await call_next(request)
