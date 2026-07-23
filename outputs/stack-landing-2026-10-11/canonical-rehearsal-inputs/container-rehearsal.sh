set -euo pipefail
PG_BIN="$(pg_config --bindir)";work=/tmp/gsip-ledger-reference;mkdir -p "$work"
trap '"$PG_BIN/pg_ctl" -D "$work/data" -m immediate stop >/dev/null 2>&1 || true' EXIT
"$PG_BIN/initdb" -D "$work/data" -A trust -U postgres >/dev/null
"$PG_BIN/pg_ctl" -D "$work/data" -l "$work/server.log" -w -o "-k $work -p 55498 -c listen_addresses=" start >/dev/null
PSQL=("$PG_BIN/psql" -X -q -t -A -v ON_ERROR_STOP=1 -h "$work" -p 55498 -U postgres -d postgres)
"${PSQL[@]}" -f /source/supabase/migration-tests/stand_in.sql >/dev/null
for migration in /source/supabase/migrations/202607*.sql; do "${PSQL[@]}" -f "$migration" >/dev/null 2>"$work/step.err"; done
"${PSQL[@]}" -f /source/seed.sql >/dev/null
"${PSQL[@]}" -f /source/rls-canonical.sql >/dev/null
"${PSQL[@]}" -f /source/alias.sql >/dev/null
"${PSQL[@]}" -f /source/rls-alias.sql >/dev/null
"${PSQL[@]}" -c 'drop policy photos_select_own on public.photos; create policy photos_select_own on public.photos for select to authenticated using(true);' >/dev/null
if "${PSQL[@]}" -f /source/rls-alias.sql >/dev/null 2>"$work/negative.err"; then echo 'unsafe RLS negative control passed' >&2;exit 1;fi
case "$(cat "$work/negative.err")" in *'synthetic own-row visibility failed for photos'*) ;; *) echo 'unexpected negative-control failure' >&2;exit 1;;esac
printf 'NEGATIVE_RLS_REJECTED\n'
"${PSQL[@]}" -f /source/alias.sql >/dev/null
for item in CATALOG_BEFORE:catalog-snapshot.sql SUPPLEMENT_BEFORE:catalog-snapshot-supplement.sql DATA_BEFORE:fingerprint.sql; do printf '%s\n' "${item%%:*}";"${PSQL[@]}" -f "/source/${item#*:}";done
"${PSQL[@]}" -f /source/ledger-seed.sql >/dev/null
printf 'LEDGER18\n';"${PSQL[@]}" -f /source/ledger-read.sql
"${PSQL[@]}" -f /source/ledger-add.sql >/dev/null
printf 'LEDGER31\n';"${PSQL[@]}" -f /source/ledger-read.sql
"${PSQL[@]}" -f /source/ledger-retire.sql >/dev/null
printf 'LEDGER18_AFTER_RETIRE\n';"${PSQL[@]}" -f /source/ledger-read.sql
"${PSQL[@]}" -f /source/ledger-stray.sql >/dev/null
printf 'LEDGER17\n';"${PSQL[@]}" -f /source/ledger-read.sql
for item in CATALOG_AFTER:catalog-snapshot.sql SUPPLEMENT_AFTER:catalog-snapshot-supplement.sql DATA_AFTER:fingerprint.sql; do printf '%s\n' "${item%%:*}";"${PSQL[@]}" -f "/source/${item#*:}";done
count=0
for migration in /source/supabase/migrations/202610*.sql;do
 "${PSQL[@]}" -f "$migration" >/dev/null 2>"$work/step.err"
 stem="$(basename "$migration" .sql)";version="${stem%%_*}";name="${stem#*_}"
 "${PSQL[@]}" -c "insert into supabase_migrations.schema_migrations(version,name) values('$version','$name')" >/dev/null
 count=$((count+1))
done
printf 'PENDING_COUNT\n%s\n' "$count"
"${PSQL[@]}" -f /source/post-upgrade.sql >/dev/null
for item in TARGET:catalog-snapshot.sql TARGET_SUPPLEMENT:catalog-snapshot-supplement.sql LEDGER26:ledger-read.sql DATA_TARGET:fingerprint.sql;do printf '%s\n' "${item%%:*}";"${PSQL[@]}" -f "/source/${item#*:}";done
