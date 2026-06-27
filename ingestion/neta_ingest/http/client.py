"""Polite HTTP client: per-host rate limiting + retry/backoff + raw-snapshot caching.

Be a good citizen — MyNeta/ADR is a non-commercial public resource. Default 1 req/host/sec,
identifying User-Agent, exponential backoff on 429/5xx.
"""

from __future__ import annotations

import time
from urllib.parse import urlparse

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from neta_ingest.config import settings

_last_hit: dict[str, float] = {}


def _throttle(url: str) -> None:
    host = urlparse(url).netloc
    now = time.monotonic()
    wait = settings.http_min_delay_seconds - (now - _last_hit.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.monotonic()


@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(settings.http_max_retries),
    reraise=True,
)
def get(url: str, **kwargs) -> httpx.Response:
    """GET with throttling + retry. Raises on 4xx/5xx (after retries on retryable codes)."""
    _throttle(url)
    headers = {"User-Agent": settings.http_user_agent, **kwargs.pop("headers", {})}
    resp = httpx.get(url, headers=headers, timeout=settings.http_timeout_seconds, **kwargs)
    if resp.status_code in (429, 500, 502, 503, 504):
        resp.raise_for_status()
    return resp
