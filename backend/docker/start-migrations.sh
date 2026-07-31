#!/usr/bin/env sh
set -eu

exec uv run alembic -c database/alembic.ini upgrade head
