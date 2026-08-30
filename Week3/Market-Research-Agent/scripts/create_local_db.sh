#!/usr/bin/env bash
# Idempotent local Postgres setup for native (non-Docker) development.
# Requires a running local Postgres (e.g. `brew install postgresql@16 && brew services start postgresql@16`).
set -euo pipefail

DB_NAME="${1:-competitor_research}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-$(whoami)}"

if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -lqt | cut -d '|' -f 1 | grep -qw "$DB_NAME"; then
  echo "Database '$DB_NAME' already exists — skipping create."
else
  createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$DB_NAME"
  echo "Created database '$DB_NAME'."
fi

psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
echo "pgcrypto ensured on '$DB_NAME'."
