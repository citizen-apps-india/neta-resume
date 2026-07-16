"""Stale-while-revalidate cache headers for the public read API.

Every JSON endpoint is read-only and changes only when a batch ingest lands, so a `Cache-Control` with a
shared-cache `s-maxage` plus a long `stale-while-revalidate` lets any CDN (and Vercel's Data Cache) serve a
response instantly and refresh it in the background — the whole point of a mostly-static public record.

We use `s-maxage` (shared/CDN caches) rather than `max-age` so a *browser* doesn't pin a stale copy: the
edge caches, individual users don't. TTLs are keyed by path prefix (longest match wins) and are kept >= the
web layer's `next: { revalidate }` values so the API header never forces the web cache to look stale sooner
than intended. `stale-while-revalidate` is the grace window during which a stale hit is served while a fresh
one is fetched — so even a Render cold-start after idle is hidden behind the last good response.

Set only on cacheable GET 200s. Exempt: `/health` (keep-warm ping), the photo/document proxies (which set
their own 7-day header — don't clobber), and `/visits` (a near-live counter). The `POST /visits/hit` write is
never cached because only GET responses are touched.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# (s-maxage, stale-while-revalidate) in seconds, keyed by path prefix. Longest matching prefix wins; anything
# unmatched falls back to the short list tier. Kept >= the web `revalidate` values (see web/src/lib/api.ts).
_RULES: tuple[tuple[str, tuple[int, int]], ...] = (
    ("/persons/facets", (300, 3600)),      # dropdown filter options — list-tier
    ("/persons", (3600, 86400)),           # /persons/{id} detail (also covers /persons list; see below)
    ("/parliament/search", (300, 3600)),   # full-text search — short, results shift with new ingests
    ("/parliament", (3600, 86400)),        # parliament aggregates (stats/trends/ministries/…)
    ("/aggregate", (3600, 86400)),         # theme-focus aggregates
    ("/indicators", (3600, 86400)),        # India Dashboard macro series
    ("/search", (300, 3600)),              # person typeahead
    ("/stats", (600, 3600)),               # homepage headline counts
    ("/elections", (600, 3600)),           # election results
)
_LIST_TIER = (300, 3600)  # /persons list + default for anything unmatched
_DEFAULT = _LIST_TIER


def _is_exempt(path: str) -> bool:
    return (
        path == "/health"
        or path.endswith("/photo")
        or path.endswith("/document")
        or path.startswith("/visits")
    )


def _ttl_for(path: str) -> tuple[int, int]:
    # The bare `/persons` list wants the short list tier, but `/persons/{id}` wants the long detail tier.
    # Both share the `/persons` prefix, so special-case the collection root before the prefix scan.
    # (path never carries the query string, so an exact match cleanly separates the list from a detail id.)
    if path == "/persons":
        return _LIST_TIER
    for prefix, ttl in _RULES:
        if path == prefix or path.startswith(prefix + "/"):
            return ttl
    return _DEFAULT


class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        if (
            request.method == "GET"
            and response.status_code == 200
            and not _is_exempt(request.url.path)
            and "cache-control" not in response.headers
        ):
            s_maxage, swr = _ttl_for(request.url.path)
            response.headers["Cache-Control"] = (
                f"public, s-maxage={s_maxage}, stale-while-revalidate={swr}"
            )
        return response
