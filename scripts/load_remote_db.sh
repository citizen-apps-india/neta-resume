#!/usr/bin/env bash
# Copy the local Neta-Resume database (schema + all data) into a hosted Postgres (Neon, RDS, …).
# FULL REPLACE: resets the target's public schema and reloads it. The lifetime visitor counter
# (site_counter) is captured first and restored afterwards so a rebuild never zeroes it.
#
# Usage:
#   TARGET_DSN="postgresql://USER:PASS@HOST/neta?sslmode=require" ./scripts/load_remote_db.sh
#
# LOCAL_DSN defaults to the dev database; override if yours differs.
set -euo pipefail

: "${TARGET_DSN:?Set TARGET_DSN to the destination Postgres URL (e.g. your Neon/RDS connection string)}"
LOCAL_DSN="${LOCAL_DSN:-postgresql://neta:neta@localhost:5432/neta}"

command -v pg_dump >/dev/null || { echo "pg_dump not found — install postgresql client tools first."; exit 1; }
command -v psql    >/dev/null || { echo "psql not found — install postgresql client tools first."; exit 1; }

# Hide the password when echoing a DSN (so terminal output is safe to share).
_mask() { printf '%s' "$1" | sed -E 's#(://[^:/@]+:)[^@]*@#\1****@#'; }

echo "Source : $(_mask "$LOCAL_DSN")"
echo "Target : $(_mask "${TARGET_DSN%%\?*}")  (full replace — resets the target's public schema)"
echo

# Preserve the lifetime visitor counter across the rebuild: the dump carries the LOCAL count (usually 0),
# so capture the target's current tally first and restore the larger value afterwards.
SAVED_VISITS="$(psql "$TARGET_DSN" -tAc "SELECT count FROM site_counter WHERE key='unique_visitors'" 2>/dev/null || true)"
SAVED_VISITS="${SAVED_VISITS:-0}"

# Full replace: reset the target's public schema, then load. --no-owner/--no-privileges strip local
# roles so it restores cleanly under the hosted DB's own user.
psql "$TARGET_DSN" -v ON_ERROR_STOP=1 -q -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
pg_dump "$LOCAL_DSN" --no-owner --no-privileges --no-comments \
  | psql "$TARGET_DSN" -v ON_ERROR_STOP=1 -q

# Never let the lifetime visitor count go backwards.
psql "$TARGET_DSN" -v ON_ERROR_STOP=1 -q \
  -c "UPDATE site_counter SET count = GREATEST(count, ${SAVED_VISITS}) WHERE key = 'unique_visitors';"

echo
echo "Done. Sanity check:"
psql "$TARGET_DSN" -c "SELECT count(*) AS people FROM person;" \
                   -c "SELECT count(*) AS with_attendance FROM office_term WHERE attendance_pct IS NOT NULL;" \
                   -c "SELECT count AS visitors FROM site_counter WHERE key='unique_visitors';"
