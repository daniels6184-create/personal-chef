#!/usr/bin/env bash
# Dump the database and encrypt it to an age public key. Nothing unencrypted touches disk.
#   DATABASE_URL=...  AGE_RECIPIENT=age1...  scripts/backup.sh  out.dump.age
set -euo pipefail
: "${DATABASE_URL:?set DATABASE_URL}"
: "${AGE_RECIPIENT:?set AGE_RECIPIENT (an age public key, age1...)}"
out="${1:?output file}"
pg_dump --format=custom --no-owner --no-privileges "$DATABASE_URL" | age --encrypt -r "$AGE_RECIPIENT" -o "$out"
echo "Encrypted backup written: $out ($(wc -c < "$out") bytes)"
