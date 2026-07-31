# syntax=docker/dockerfile:1

FROM python:3.14.6-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.0 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/neta-core packages/neta-core
COPY packages/neta-sources packages/neta-sources
COPY ingestion ingestion
COPY backend backend
COPY orchestration orchestration

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package neta-backend

FROM python:3.14.6-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 neta \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin neta

WORKDIR /app/backend
COPY --from=builder --chown=10001:10001 /app /app

USER 10001:10001
EXPOSE 8001

CMD ["sh", "docker/start-api.sh"]
