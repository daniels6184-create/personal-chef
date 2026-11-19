#!/usr/bin/env bash
# Decrypt a backup and restore it into an EMPTY database (it never overwrites existing data).
#   TARGET_DATABASE_URL=...  scripts/restore.sh  backup.dump.age  my-age-key.txt
set -euo pipefail
: "${TARGET_DATABASE_URL:?set TARGET_DATABASE_URL}"
in="${1:?encrypted backup}"; key="${2:?age identity (private key) file}"
tables=$(psql "$TARGET_DATABASE_URL" -tAc "select count(*) from information_schema.tables where table_schema='public'")
if [ "$tables" != "0" ]; then echo "Refusing: the target database is not empty ($tables tables)." >&2; exit 1; fi
age --decrypt -i "$key" "$in" | pg_restore --no-owner --no-privileges --exit-on-error -d "$TARGET_DATABASE_URL"
echo "Restored into the target database."
