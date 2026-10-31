# -- Builder stage
FROM python:3.14-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# -- Runtime stage
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

COPY . /app/

ENV PATH="/app/.venv/bin:$PATH"

# Code stays root-owned (read-only); only the seed's output folder is writable
RUN useradd --system --uid 10001 --create-home app \
  && mkdir -p /app/data \
  && chown app:app /app/data
USER app

ENTRYPOINT ["python", "main.py"]

CMD ["--help"]
