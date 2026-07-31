#!/usr/bin/env sh
set -eu

exec uv run fastapi run neta_backend/main.py --host 0.0.0.0 --port 8001
