#!/usr/bin/env bash
# Nightly logical backup of the Supabase database via pg_dump.
# Keeps 14 days locally. A backup on the same VM does not survive losing the
# VM - copy ./backups off-box (see docs/DEPLOY.md, "Backups").
set -euo pipefail

cd "$(dirname "$0")/.."

# Read DATABASE_URL without `source`-ing .env (the URL contains ? and &).
DATABASE_URL="$(grep -E '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)"
[ -n "$DATABASE_URL" ] || { echo "DATABASE_URL missing from .env" >&2; exit 1; }
export DATABASE_URL

mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
tmp="backups/.budget-${stamp}.sql.gz.part"
out="backups/budget-${stamp}.sql.gz"

# Use a pg_dump of the SAME major version as the server: a newer client emits
# settings (e.g. transaction_timeout, PG17) that older servers reject on
# restore. Only the public schema: Supabase's own schemas are managed by
# Supabase and not ours to restore.
version_num="$(docker run --rm -e DATABASE_URL postgres:17-alpine \
    sh -c 'psql "$DATABASE_URL" -tAc "show server_version_num"')"
major="$(( version_num / 10000 ))"

docker run --rm -e DATABASE_URL "postgres:${major}-alpine" \
    sh -c 'pg_dump --no-owner --no-privileges --schema=public "$DATABASE_URL"' \
    | sed '/^CREATE SCHEMA public;$/d' \
    | gzip > "$tmp"

[ -s "$tmp" ] || { rm -f "$tmp"; echo "empty backup" >&2; exit 1; }
mv "$tmp" "$out"
find backups -name 'budget-*.sql.gz' -mtime +14 -delete
echo "backup ok: $out ($(du -h "$out" | cut -f1))"
