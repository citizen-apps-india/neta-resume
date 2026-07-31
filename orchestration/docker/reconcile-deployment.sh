#!/usr/bin/env sh
set -eu

: "${NETA_GIT_COMMIT_SHA:?NETA_GIT_COMMIT_SHA must identify the deployed revision}"

neta migrate
alembic -c backend/database/alembic.ini upgrade head
neta seed
neta-orchestrator register-manifests \
  --git-commit "${NETA_GIT_COMMIT_SHA}" \
  --actor "argo-cd"
