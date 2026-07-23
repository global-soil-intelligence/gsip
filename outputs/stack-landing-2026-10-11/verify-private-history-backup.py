"""Restore a private ledger dump locally; emit metadata/digests only."""
from __future__ import annotations

import hashlib
import json
import re
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
PRIVATE = Path('/Users/justinhart/.supabase/gsip-recovery/2026-10-11')
IMAGE = 'sha256:521e67f2812db505fe6d462b1820136394824d7f5c6016a19234b07ac93d6760'
EXPECTED = {
    'original-history-schema.sql': 'ae56295c7e66a8b46ab50df6f00cf57f7866f2478a17fbe3910d9def39e836ab',
    'original-history.sql': '612b05231c79eac1e52cc4bf5da49ec2e9d4755358b461c902af69f6f089c857',
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lex(sql: str) -> list[list[tuple[str, str]]]:
    """Keep strings opaque; reject all non-dump metacommands/expressions."""
    statements: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    i = 0
    while i < len(sql):
        c = sql[i]
        if c.isspace():
            i += 1
            continue
        if sql.startswith('--', i):
            j = sql.find('\n', i)
            i = len(sql) if j == -1 else j + 1
            continue
        if c in "'\"":
            quote = c
            i += 1
            value: list[str] = []
            while i < len(sql):
                if sql[i] == quote:
                    if i + 1 < len(sql) and sql[i + 1] == quote:
                        value.append(quote)
                        i += 2
                        continue
                    i += 1
                    break
                value.append(sql[i])
                i += 1
            else:
                raise ValueError('unterminated dump literal')
            current.append(('S' if quote == "'" else 'I', ''.join(value)))
            continue
        match = re.match(r'[A-Za-z_][A-Za-z_0-9]*|[0-9]+', sql[i:])
        if match:
            value = match.group(0)
            current.append(('N' if value.isdigit() else 'W', value.upper()))
            i += len(value)
            continue
        if c == ';':
            if current:
                statements.append(current)
                current = []
            i += 1
            continue
        if c in '.,()[]=':
            current.append(('P', c))
            i += 1
            continue
        raise ValueError('unsupported dump token')
    if current:
        raise ValueError('unterminated outer dump command')
    return statements


def syntax(sql: str) -> list[tuple[str, str]]:
    parsed = lex(sql + ';')
    assert len(parsed) == 1
    return parsed[0]


def envelope(tokens: list[tuple[str, str]]) -> bool:
    allowed = [
        'SET statement_timeout = 0', 'SET lock_timeout = 0',
        'SET idle_in_transaction_session_timeout = 0', 'SET transaction_timeout = 0',
        "SET client_encoding = 'UTF8'", 'SET standard_conforming_strings = on',
        "SELECT pg_catalog.set_config('search_path', '', false)",
        'SET check_function_bodies = false', 'SET xmloption = content',
        'SET client_min_messages = warning', 'SET row_security = off',
        "SET default_tablespace = ''", 'SET default_table_access_method = "heap"',
        'SET session_replication_role = replica', "SET session_replication_role = 'replica'",
        'RESET ALL',
    ]
    return tokens in [syntax(item) for item in allowed]


def validate_schema(sql: str) -> dict[str, int]:
    expected_ddl = [
        'CREATE SCHEMA IF NOT EXISTS "supabase_migrations"',
        'ALTER SCHEMA "supabase_migrations" OWNER TO "postgres"',
        'CREATE TABLE IF NOT EXISTS "supabase_migrations"."schema_migrations" '
        '("version" "text" NOT NULL, "statements" "text"[], "name" "text", '
        '"created_by" "text", "idempotency_key" "text", "rollback" "text"[])',
        'ALTER TABLE "supabase_migrations"."schema_migrations" OWNER TO "postgres"',
        'ALTER TABLE ONLY "supabase_migrations"."schema_migrations" ADD CONSTRAINT '
        '"schema_migrations_idempotency_key_key" UNIQUE ("idempotency_key")',
        'ALTER TABLE ONLY "supabase_migrations"."schema_migrations" ADD CONSTRAINT '
        '"schema_migrations_pkey" PRIMARY KEY ("version")',
    ]
    parsed = lex(sql)
    ddl = [item for item in parsed if not envelope(item)]
    if ddl != [syntax(item) for item in expected_ddl]:
        raise ValueError('schema dump differs from trusted ledger-only shape')
    return {'outer_commands': len(parsed), 'ledger_ddl_commands': len(ddl)}


def validate_data(sql: str) -> dict[str, int]:
    parsed = lex(sql)
    insertions = [item for item in parsed if not envelope(item)]
    if len(insertions) != 1:
        raise ValueError('data dump must have one ledger insert only')
    tokens = insertions[0]
    prefix = syntax('INSERT INTO "supabase_migrations"."schema_migrations"')
    if tokens[:len(prefix)] != prefix:
        raise ValueError('unexpected data target')
    i = len(prefix)
    if tokens[i] != ('P', '('):
        raise ValueError('missing ledger column list')
    i += 1
    columns: list[str] = []
    while True:
        if tokens[i][0] != 'I':
            raise ValueError('invalid ledger column')
        columns.append(tokens[i][1])
        i += 1
        if tokens[i] == ('P', ')'):
            i += 1
            break
        if tokens[i] != ('P', ','):
            raise ValueError('invalid ledger column delimiter')
        i += 1
    allowed = {'version', 'statements', 'name', 'created_by', 'idempotency_key', 'rollback'}
    if len(set(columns)) != len(columns) or not set(columns) <= allowed:
        raise ValueError('unexpected ledger columns')
    if not {'version', 'statements', 'name'} <= set(columns):
        raise ValueError('missing ledger identity or statement columns')
    if tokens[i] != ('W', 'VALUES'):
        raise ValueError('data must be literal VALUES, without executable expressions')
    i += 1
    rows = 0
    while i < len(tokens):
        if tokens[i] != ('P', '('):
            raise ValueError('invalid literal row')
        i += 1
        for j in range(len(columns)):
            if tokens[i][0] != 'S' and tokens[i] != ('W', 'NULL'):
                raise ValueError('ledger value must be opaque text or NULL')
            i += 1
            expected_delimiter = ')' if j == len(columns) - 1 else ','
            if tokens[i] != ('P', expected_delimiter):
                raise ValueError('invalid literal value delimiter')
            i += 1
        rows += 1
        if i < len(tokens):
            if tokens[i] != ('P', ','):
                raise ValueError('unexpected command after literal row')
            i += 1
    if rows != 18:
        raise ValueError('unexpected ledger row count')
    return {'outer_commands': len(parsed), 'ledger_insert_commands': 1,
            'literal_rows': rows, 'inserted_column_count': len(columns),
            'executable_ledger_statement_values': 0}


QUERY = r"""
SELECT jsonb_build_object(
  'postgres_version', current_setting('server_version'),
  'ledger_count', (SELECT count(*) FROM supabase_migrations.schema_migrations),
  'ledger_columns', (SELECT jsonb_agg(jsonb_build_object('name',attname,'type',format_type(atttypid,atttypmod),'not_null',attnotnull) ORDER BY attnum)
    FROM pg_attribute WHERE attrelid='supabase_migrations.schema_migrations'::regclass AND attnum>0 AND NOT attisdropped),
  'user_table_count', (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind IN ('r','p') AND n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
  'user_function_count', (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
  'ledger_owner', (SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid='supabase_migrations.schema_migrations'::regclass),
  'constraints', (SELECT jsonb_agg(jsonb_build_object('name',conname,'type',contype,'definition',pg_get_constraintdef(oid)) ORDER BY conname) FROM pg_constraint WHERE conrelid='supabase_migrations.schema_migrations'::regclass),
  'migrations', (SELECT jsonb_agg(jsonb_build_object(
    'version',version,'name',name,'statement_count',cardinality(statements),'statements_null',statements IS NULL,
    'statement_sha256',encode(sha256(convert_to(array_to_string(statements,E'\n'),'UTF8')),'hex'),
    'statement_array_sha256',encode(sha256(convert_to(to_jsonb(statements)::text,'UTF8')),'hex'),
    'full_metadata_sha256',encode(sha256(convert_to(to_jsonb(m)::text,'UTF8')),'hex')
    ) ORDER BY version) FROM supabase_migrations.schema_migrations m)
)::text;
"""

CONTAINER = r"""
set -eu
export PGDATA=/tmp/gsip-ledger-pg
mkdir -p "$PGDATA" /tmp/gsip-ledger-socket
initdb -D "$PGDATA" --auth=trust --encoding=UTF8 --no-locale >/tmp/initdb.log 2>&1
pg_ctl -D "$PGDATA" -l /tmp/pg.log -o "-k /tmp/gsip-ledger-socket -p 55499 -c listen_addresses=''" -w start >/tmp/start.log 2>&1
trap 'pg_ctl -D "$PGDATA" -m immediate stop >/dev/null 2>&1 || true' EXIT
export PGHOST=/tmp/gsip-ledger-socket PGPORT=55499 PGUSER=postgres PGDATABASE=postgres
if ! psql -X -q -v ON_ERROR_STOP=1 --single-transaction -f - >/tmp/restore.log 2>/tmp/restore-error.log; then
  echo '{"error":"private ledger restore failed; contents suppressed"}'
  exit 3
fi
if ! psql -X -q -A -t -v ON_ERROR_STOP=1 -f /metadata/query.sql 2>/tmp/query-error.log; then
  echo '{"error":"metadata query failed; contents suppressed"}'
  exit 4
fi
"""


def main() -> None:
    original: dict[str, bytes] = {}
    files: list[dict[str, object]] = []
    for name, expected in EXPECTED.items():
        path = PRIVATE / name
        data = path.read_bytes()
        if digest(data) != expected or stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise ValueError('private backup hash/mode mismatch')
        original[name] = data
        files.append({'name': name, 'bytes': len(data), 'sha256': expected, 'mode': '0600'})
    if stat.S_IMODE(PRIVATE.stat().st_mode) != 0o700:
        raise ValueError('private recovery directory mode mismatch')
    structure = {
        'schema': validate_schema(original['original-history-schema.sql'].decode()),
        'data': validate_data(original['original-history.sql'].decode()),
    }
    prod_path = BASE / 'production-history-full-array-digests.json'
    observed_bytes = prod_path.read_bytes()
    observed = json.loads(observed_bytes)
    whole_path = BASE / 'production-history-whole-row-digests.json'
    whole_bytes = whole_path.read_bytes()
    whole_observed = json.loads(whole_bytes)
    # Only metadata enters the container's output. The original dump travels on
    # stdin; it is never copied to host output folders or mounted writable.
    with tempfile.TemporaryDirectory(prefix='gsip-history-restore-', dir='/private/tmp') as temp:
        work = Path(temp)
        work.chmod(0o755)
        (work/'query.sql').write_text(QUERY)
        result = subprocess.run([
            '/usr/local/bin/docker', 'run', '--rm', '--network', 'none', '--user', 'postgres',
            '--entrypoint', '/bin/bash', '--cidfile', str(work/'container-id'),
            '-v', str(work)+':/metadata:ro', '-i', IMAGE, '-c', CONTAINER,
        ], input=original['original-history-schema.sql']+b'\n'+original['original-history.sql'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode:
            raise RuntimeError('isolated restore failed; private diagnostic contents suppressed')
        restored = json.loads(result.stdout)
        container_id = (work/'container-id').read_text().strip()
        inventory = subprocess.run(['/usr/local/bin/docker','container','ls','-a','--no-trunc','--format','{{.ID}}'],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        removed = inventory.returncode == 0 and container_id not in inventory.stdout.decode().splitlines()
    if not removed:
        raise RuntimeError('ephemeral restore container still present')
    if restored['ledger_count'] != 18 or restored['user_table_count'] != 1 or restored['user_function_count'] != 0:
        raise ValueError('restore created unexpected database objects')
    records = observed.get('records', observed.get('migrations', observed.get('result'))) if isinstance(observed,dict) else observed
    if isinstance(records,dict):
        records = records.get('migrations')
    if not isinstance(records,list) or len(records) != 18:
        raise ValueError('unexpected production metadata receipt shape')
    comparison_keys = ('version','name','statement_count','statements_null','statement_sha256','statement_array_sha256')
    expected_records = sorted([{k:r[k] for k in comparison_keys} for r in records],key=lambda r:r['version'])
    actual_records = sorted([{k:r[k] for k in comparison_keys} for r in restored['migrations']],key=lambda r:r['version'])
    if expected_records != actual_records:
        raise ValueError('restored identities/names/complete statement arrays differ from production receipt')
    whole_records = whole_observed.get('records', whole_observed.get('migrations', whole_observed.get('result'))) if isinstance(whole_observed,dict) else whole_observed
    if isinstance(whole_records,dict):
        whole_records = whole_records.get('migrations')
    if not isinstance(whole_records,list) or len(whole_records) != 18:
        raise ValueError('unexpected production whole-row receipt shape')
    expected_whole = sorted([{'version':r['version'],'name':r['name'],'history_row_sha256':r['history_row_sha256']} for r in whole_records],key=lambda r:r['version'])
    actual_whole = sorted([{'version':r['version'],'name':r['name'],'history_row_sha256':r['full_metadata_sha256']} for r in restored['migrations']],key=lambda r:r['version'])
    if expected_whole != actual_whole:
        raise ValueError('restored full six-field metadata differs from production receipt')
    for name, data in original.items():
        if (PRIVATE/name).read_bytes() != data:
            raise ValueError('private input changed during verification')
    receipt = {
        'status':'PASS', 'observed_at_utc':datetime.now(timezone.utc).isoformat(),
        'target':'toxldjgwkxtneoqsazym',
        'scope':'Local private-ledger recovery verification only; no production connection or mutation',
        'private_directory':str(PRIVATE), 'directory_mode':'0700', 'files':files,
        'image_id':IMAGE, 'image_digest':'public.ecr.aws/supabase/postgres@sha256:ca7871b587ca2c401ac0f325df6249c9aa0d25647ded34631158efc51176767f',
        'postgres_version':restored['postgres_version'], 'network':'none', 'user':'postgres', 'host_ports':[],
        'private_sql_transport':'stdin to psql inside disposable container; no host output copy',
        'dump_structure_validation':structure, 'ledger_count':18,
        'complete_statement_arrays_equal':True, 'exact_names_and_versions_equal':True,
        'complete_six_field_metadata_equal':True,
        'comparison_record_count':18, 'production_metadata_receipt_sha256':digest(observed_bytes),
        'production_whole_row_metadata_receipt_sha256':digest(whole_bytes),
        'query_sha256':digest(QUERY.encode()), 'driver_sha256':digest(Path(__file__).read_bytes()),
        'restored_ledger_columns':restored['ledger_columns'], 'restored_ledger_owner':restored['ledger_owner'],
        'restored_ledger_constraints':restored['constraints'], 'migrations':restored['migrations'],
        'user_table_count':1, 'user_function_count':0, 'container_removed':removed,
        'ledger_statement_values_executed':False, 'restore_driver_private_sql_contents_printed_or_copied_to_outputs':False,
        'production_mutations_performed':False,
        'scope_limits':['All six stored ledger fields are independently compared through whole-row JSON hashes; names, versions and complete statement arrays also have individual comparisons.','This verifies local recoverability, not owner-controlled durable backup retention.'],
    }
    path=BASE/'production-history-backup-restoration-receipt.json'
    path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS','matched_full_statement_arrays':18,'ledger_count':18,'container_removed':removed,'receipt':str(path),'receipt_sha256':digest(path.read_bytes())}))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status':'FAIL','error_class':type(exc).__name__,'reason':str(exc) if str(exc) in {
            'private backup hash/mode mismatch','private recovery directory mode mismatch','unexpected production metadata receipt shape',
            'restored identities/names/complete statement arrays differ from production receipt','private input changed during verification',
            'restored full six-field metadata differs from production receipt','unexpected production whole-row receipt shape',
            'restore created unexpected database objects','ephemeral restore container still present',
            'isolated restore failed; private diagnostic contents suppressed',
        } else 'validation failed; source contents suppressed'}))
        raise SystemExit(1) from None
