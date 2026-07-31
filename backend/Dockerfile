FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY packages/neta-core packages/neta-core
COPY packages/neta-sources packages/neta-sources
COPY ingestion ingestion
COPY backend backend
COPY orchestration orchestration

RUN uv sync --frozen --no-dev --package neta-backend

WORKDIR /app/backend
EXPOSE 8001
CMD ["sh", "docker/start-api.sh"]
