"""FastAPI app entrypoint.

    uv run uvicorn neta_api.main:app --reload

OpenAPI at /docs. The frontend codegens its TS types from /openapi.json.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from neta_api.cachecontrol import CacheControlMiddleware
from neta_api.deps import settings
from neta_api.ratelimit import RateLimitMiddleware
from neta_api.routers import (
    aggregate,
    elections,
    indicators,
    parliament,
    persons,
    questions,
    search,
    stats,
    visits,
)

app = FastAPI(
    title="Neta-Resume API",
    version="0.1.0",
    description="Read-only resume aggregate for Indian legislators. Every fact carries provenance.",
)

# Per-IP rate limiting (see ratelimit.py). Added before CORS so CORS ends up the OUTER middleware and a 429
# still carries Access-Control-Allow-Origin for browser callers.
app.add_middleware(RateLimitMiddleware)

# Stale-while-revalidate cache headers on read GETs (see cachecontrol.py). Added before CORS for the same
# reason — CORS stays the outermost layer; this only annotates the response headers on the way out.
app.add_middleware(CacheControlMiddleware)

# Allowed origins are env-driven (NETA_ALLOWED_ORIGINS); the default is the local Next.js dev server.
# Read-only API plus the browser-side visitor counter (POST /visits/hit), so GET + POST, no credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(persons.router)
app.include_router(questions.router)
app.include_router(parliament.router)
app.include_router(aggregate.router)
app.include_router(search.router)
app.include_router(stats.router)
app.include_router(visits.router)
app.include_router(elections.router)
app.include_router(indicators.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
