#!/usr/bin/env sh
set -eu

exec alembic -c database/alembic.ini upgrade head
