#!/usr/bin/env bash
# Migration tests on existing data.
#
# Builds a throwaway PostgreSQL cluster with PostGIS and pgTAP and applies every migration in
# supabase/migrations in order, loading supabase/migration-tests/before_<migration file> just
# before the migration it names, so each fixture is data as an earlier schema held it. It then runs
# every supabase/migration-tests/*.test.sql and fails on any failed or missing assertion.
# supabase/migration-tests/stand_in.sql replaces the parts of Supabase the migrations touch; the
# full pgTAP suite still runs on the real local stack (pnpm db:test).
#
# Needs PostgreSQL server binaries (PG_BIN, default `pg_config --bindir`) with the postgis and pgtap
# extensions installed. Usage: scripts/db-migration-test.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TESTS="$REPO/supabase/migration-tests"
PG_BIN="${PG_BIN:-$(pg_config --bindir)}"
PORT="${PG_TEST_PORT:-55491}"
DB=gsip_migration_test
WORK="$(mktemp -d)"

# PostgreSQL refuses to run its server as root; a root shell (a container) runs it as postgres.
as_server() {
  if [ "$(id -u)" = 0 ]; then runuser -u postgres -- "$@"; else "$@"; fi
}

cleanup() {
  as_server "$PG_BIN/pg_ctl" -D "$WORK/data" -m immediate stop >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

for fixture in "$TESTS"/before_*.sql; do
  [ -e "$fixture" ] || continue
  migration="$REPO/supabase/migrations/$(basename "$fixture" | sed 's/^before_//')"
  if [ ! -f "$migration" ]; then
    echo "FIXTURE NAMES NO MIGRATION: $fixture"
    exit 1
  fi
done

if [ "$(id -u)" = 0 ]; then chown postgres "$WORK"; fi
as_server "$PG_BIN/initdb" -D "$WORK/data" -A trust -U postgres >/dev/null
as_server "$PG_BIN/pg_ctl" -D "$WORK/data" -l "$WORK/server.log" -w \
  -o "-k $WORK -p $PORT -c listen_addresses=" start >/dev/null

PSQL=(psql -X -q -v ON_ERROR_STOP=1 -h "$WORK" -p "$PORT" -U postgres)
"${PSQL[@]}" -d postgres -c "create database $DB" >/dev/null
"${PSQL[@]}" -d "$DB" -f "$TESTS/stand_in.sql" >/dev/null

for migration in "$REPO"/supabase/migrations/*.sql; do
  fixture="$TESTS/before_$(basename "$migration")"
  if [ -f "$fixture" ]; then
    "${PSQL[@]}" -d "$DB" -f "$fixture" >/dev/null 2>"$WORK/step.err" ||
      { cat "$WORK/step.err"; echo "FIXTURE FAILED: $fixture"; exit 1; }
  fi
  "${PSQL[@]}" -d "$DB" -f "$migration" >/dev/null 2>"$WORK/step.err" ||
    { cat "$WORK/step.err"; echo "MIGRATION FAILED: $migration"; exit 1; }
done

status=0
for test in "$TESTS"/*.test.sql; do
  [ -e "$test" ] || continue
  if ! out="$("${PSQL[@]}" -d "$DB" -t -A -f "$test" 2>&1)"; then
    echo "$out" | tail -20
    echo "ERROR in $(basename "$test")"
    status=1
    continue
  fi
  failed="$(grep -c '^not ok' <<<"$out" || true)"
  total="$(grep -cE '^(ok|not ok)' <<<"$out" || true)"
  echo "$(basename "$test"): $((total - failed))/$total ok"
  if [ "$failed" != 0 ] || grep -q '^# Looks like' <<<"$out"; then
    grep -A3 -E '^not ok|^# Looks like' <<<"$out"
    status=1
  fi
done
exit "$status"
