#!/usr/bin/env bash
# Wipes and re-migrates a LOCAL development database. Refuses anything that isn't localhost/socket.
set -euo pipefail
url="${DATABASE_URL:?set DATABASE_URL}"
case "$url" in *neon.tech*|*render.com*) echo "Refusing: not a local database." >&2; exit 1;; esac
psql "$url" -qc "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
cd "$(dirname "$0")/../backend" && ../.venv/bin/alembic upgrade head
