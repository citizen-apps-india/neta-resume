# syntax=docker/dockerfile:1

###############################################################################
# Builder: resolve and install dependencies into a self-contained .venv
###############################################################################
FROM python:3.12-slim AS builder

# Install uv (static binary) from the official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies first (cached layer) using only the lockfile + manifest.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy the application source and install the project itself.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

###############################################################################
# Runtime: slim image carrying just the venv + app
###############################################################################
FROM python:3.12-slim AS runtime

WORKDIR /app

# Bring in the built virtualenv and the application code.
COPY --from=builder /app /app

# Put the venv on PATH so `uvicorn` resolves to the installed one.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "neta_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
