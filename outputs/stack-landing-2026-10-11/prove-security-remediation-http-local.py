"""Synthetic loopback-only HTTP proof; never uses production or real credentials."""
from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import json
import secrets
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE / 'repo'
HEAD = 'f9e1ac2f8a88671f99b959e476499392297bd30f'
PG_IMAGE = 'sha256:521e67f2812db505fe6d462b1820136394824d7f5c6016a19234b07ac93d6760'
REST_IMAGE = 'sha256:fcb9fa67dd53b3b978b52ef07fb195d4bb26434c2e8cba8c96ef257abf2ee753'
PORT = 55498
USER_A = '31000000-0000-4000-8000-000000000001'
USER_B = '31000000-0000-4000-8000-000000000002'
DELETED_USER = '31000000-0000-4000-8000-000000000003'
SUBMISSION_A = '51000000-0000-4000-8000-000000000001'
MISSING_PHOTOS = '51000000-0000-4000-8000-000000000002'
WITHDRAWN_SUBMISSION = '51000000-0000-4000-8000-000000000003'


class ProofFailure(Exception):
    """Contains only a stage name/status, never a SQL/HTTP response body."""


def call(args: list[str], data: str | None = None, stage: str = 'command') -> str:
    result = subprocess.run(args, input=data, capture_output=True, text=True)
    if result.returncode:
        # SQLSTATE only; psql is configured never to emit row/statement detail.
        states = [line.split('ERROR:', 1)[1].strip()[:5]
                  for line in result.stderr.splitlines() if 'ERROR:' in line]
        raise ProofFailure(f'{stage}: exit={result.returncode}, sqlstates={states}')
    return result.stdout


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


suffix = secrets.token_hex(5)
pg_name = 'gsip-http-pg-' + suffix
rest_name = 'gsip-http-rest-' + suffix
source = Path(tempfile.mkdtemp(prefix='gsip-http-proof-', dir='/private/tmp'))
source.chmod(0o755)
jwt_material = secrets.token_urlsafe(48)
tests: list[dict[str, object]] = []
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
cleaned = False


def sql(text: str, stage: str = 'sql') -> str:
    return call(['docker', 'exec', '-i', pg_name, 'psql',
                 '-X', '-q', '-t', '-A', '-v', 'ON_ERROR_STOP=1',
                 '-v', 'VERBOSITY=sqlstate', '-h', '127.0.0.1', '-p', str(PORT),
                 '-U', 'postgres', '-d', 'postgres'], text, stage)


def token(role: str, uid: str | None = None) -> str:
    payload: dict[str, object] = {'role': role, 'exp': int(time.time()) + 600}
    if uid:
        payload['sub'] = uid
    def encoded(obj: object) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj, separators=(',', ':')).encode()).decode().rstrip('=')
    message = encoded({'alg': 'HS256', 'typ': 'JWT'}) + '.' + encoded(payload)
    signature = base64.urlsafe_b64encode(hmac.new(jwt_material.encode(), message.encode(), hashlib.sha256).digest()).decode().rstrip('=')
    return message + '.' + signature


def request(path: str, role: str | None = None, uid: str | None = None,
            body: dict[str, object] | None = None, profile: str | None = None,
            method: str | None = None) -> tuple[int, object]:
    verb = method or ('POST' if body is not None else 'GET')
    lines = ['silent', 'show-error', 'max-time = 10',
             'url = ' + json.dumps('http://127.0.0.1:3000' + path),
             'request = ' + json.dumps(verb), 'write-out = "\\n%{http_code}"']
    if role:
        lines.append('header = ' + json.dumps('Authorization: Bearer ' + token(role, uid)))
    if body is not None:
        lines.append('header = "Content-Type: application/json"')
        lines.append('data = ' + json.dumps(json.dumps(body)))
    if profile:
        header = 'Accept-Profile' if verb in ('GET', 'HEAD') else 'Content-Profile'
        lines.append('header = ' + json.dumps(header + ': ' + profile))
    output = call(['docker', 'exec', '-i', pg_name, 'curl', '--config', '-'],
                  '\n'.join(lines) + '\n', 'loopback-http')
    text, status = output.rsplit('\n', 1)
    return int(status), json.loads(text)


def check(name: str, condition: bool, status: int | None = None) -> None:
    if not condition:
        raise ProofFailure(name + (f': HTTP={status}' if status else ''))
    tests.append({'name': name, 'status': 'PASS', **({'http_status': status} if status else {})})


def success(name: str, path: str, expected: object, role: str | None = None,
            uid: str | None = None, body: dict[str, object] | None = None) -> object:
    status, value = request(path, role, uid, body)
    check(name, status == 200 and value == expected, status)
    return value


def refused(name: str, path: str, code: str, role: str | None = None,
            uid: str | None = None, body: dict[str, object] | None = None,
            profile: str | None = None) -> None:
    status, value = request(path, role, uid, body, profile)
    check(name, status >= 400 and isinstance(value, dict) and value.get('code') == code, status)


try:
    paths = call(['git', '-C', str(REPO), 'ls-tree', '-r', '--name-only', HEAD, 'supabase/migrations'],
                 stage='source-inventory').splitlines()
    paths += ['supabase/migration-tests/stand_in.sql']
    for name in paths:
        if not name.endswith('.sql'):
            continue
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(subprocess.check_output(['git', 'show', HEAD + ':' + name], cwd=REPO))
    boot = '''set -euo pipefail
PG_BIN="$(pg_config --bindir)"
mkdir -p /tmp/proof
"$PG_BIN/initdb" -D /tmp/proof/data -A trust -U postgres >/dev/null
"$PG_BIN/pg_ctl" -D /tmp/proof/data -l /tmp/proof/server.log -w -o '-p 55498 -k /tmp/proof -c listen_addresses=127.0.0.1' start >/dev/null
exec sleep infinity
'''
    call(['docker', 'run', '--pull=never', '-d', '--name', pg_name,
          '--network', 'none', '--user', 'postgres', '--entrypoint', '/bin/bash',
          '-v', str(source) + ':/source:ro', PG_IMAGE, '-c', boot], stage='start-isolated-pg')
    for _ in range(60):
        probe = subprocess.run(['docker', 'exec', pg_name, 'pg_isready',
                                '-h', '127.0.0.1', '-p', str(PORT)], capture_output=True)
        if probe.returncode == 0:
            break
        time.sleep(0.1)
    else:
        raise ProofFailure('isolated-pg-not-ready')
    call(['docker', 'exec', pg_name, 'curl', '--version'], stage='cached-container-curl')
    sql((source / 'supabase/migration-tests/stand_in.sql').read_text(), 'stand-in')
    for path in sorted((source / 'supabase/migrations').glob('*.sql')):
        sql(path.read_text(), 'migration-' + path.name)
    # Empty points satisfy the required geometry type without coordinate values.
    sql("""
create role gsip_http_authenticator login noinherit;
grant anon, authenticated, service_role to gsip_http_authenticator;
insert into auth.users(id) values
('31000000-0000-4000-8000-000000000001'),('31000000-0000-4000-8000-000000000002');
insert into public.terms_versions(version,published_at) values('http-local-v1',now());
insert into public.contributors(id,auth_uid,handle) values
('21000000-0000-4000-8000-000000000001','31000000-0000-4000-8000-000000000001','http-proof-a'),
('21000000-0000-4000-8000-000000000002','31000000-0000-4000-8000-000000000002','http-proof-b');
insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,attribution_name) values
('41000000-0000-4000-8000-000000000001','21000000-0000-4000-8000-000000000001','http-local-v1',now(),'Anonymous soil contributor'),
('41000000-0000-4000-8000-000000000002','21000000-0000-4000-8000-000000000002','http-local-v1',now(),'Anonymous soil contributor'),
('41000000-0000-4000-8000-000000000003','21000000-0000-4000-8000-000000000001','http-local-v1',now(),'Anonymous soil contributor');
insert into public.submissions(id,contributor_id,grant_id,geom_precise,captured_at,status,is_synthetic) values
('51000000-0000-4000-8000-000000000001','21000000-0000-4000-8000-000000000001','41000000-0000-4000-8000-000000000001',extensions.st_geomfromtext('POINT EMPTY',4326),now(),'pending',true),
('51000000-0000-4000-8000-000000000002','21000000-0000-4000-8000-000000000001','41000000-0000-4000-8000-000000000001',extensions.st_geomfromtext('POINT EMPTY',4326),now(),'pending',true),
('51000000-0000-4000-8000-000000000003','21000000-0000-4000-8000-000000000001','41000000-0000-4000-8000-000000000003',extensions.st_geomfromtext('POINT EMPTY',4326),now(),'pending',true);
insert into public.photos(submission_id,shot_type,storage_path) values
('51000000-0000-4000-8000-000000000001','A','31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000001/A/61000000-0000-4000-8000-000000000001.jpg'),
('51000000-0000-4000-8000-000000000001','B','31000000-0000-4000-8000-000000000001/51000000-0000-4000-8000-000000000001/B/61000000-0000-4000-8000-000000000002.jpg');
create function public.http_proof_context() returns jsonb language sql stable security invoker
return jsonb_build_object('pid',pg_backend_pid(),'uid',auth.uid(),'role',current_user);
revoke all on function public.http_proof_context() from public;
grant execute on function public.http_proof_context() to anon, authenticated, service_role;
""", 'synthetic-fixtures')
    env = {'PGRST_DB_URI': f'postgresql://gsip_http_authenticator@127.0.0.1:{PORT}/postgres',
           'PGRST_DB_SCHEMAS': 'public', 'PGRST_DB_ANON_ROLE': 'anon',
           'PGRST_JWT_SECRET': jwt_material, 'PGRST_DB_POOL': '1',
           'PGRST_DB_PREPARED_STATEMENTS': 'true', 'PGRST_LOG_LEVEL': 'error',
           'PGRST_SERVER_HOST': '127.0.0.1', 'PGRST_SERVER_PORT': '3000'}
    args = ['docker', 'run', '--pull=never', '-d', '--name', rest_name,
            '--network', 'container:' + pg_name]
    for name, value in env.items():
        args += ['-e', name + '=' + value]
    call(args + [REST_IMAGE], stage='start-shared-none-postgrest')
    for _ in range(80):
        try:
            if request('/rpc/capture_is_open') == (200, False):
                break
        except (ProofFailure, ValueError, json.JSONDecodeError):
            pass
        time.sleep(0.1)
    else:
        raise ProofFailure('postgrest-not-ready')
    pg_meta = json.loads(call(['docker', 'inspect', '--format',
                              '{{json .HostConfig.NetworkMode}}', pg_name]))
    rest_meta = json.loads(call(['docker', 'inspect', '--format',
                                '{{json .HostConfig.NetworkMode}}', rest_name]))
    ports = call(['docker', 'inspect', '--format', '{{json .HostConfig.PortBindings}}', pg_name, rest_name])
    pg_id = call(['docker', 'inspect', '--format', '{{.Id}}', pg_name]).strip()
    check('isolated_network_and_no_host_ports', pg_meta == 'none' and rest_meta in ('container:' + pg_name, 'container:' + pg_id) and all(v in ('null', '{}') for v in ports.splitlines()))
    success('baseline_anonymous_capture_closed', '/rpc/capture_is_open', False)
    success('baseline_auth_owner_exists', '/rpc/current_auth_user_exists', True, 'authenticated', USER_A)
    success('baseline_deleted_uid_absent', '/rpc/current_auth_user_exists', False, 'authenticated', DELETED_USER)
    proposal = (BASE / 'gate-c-security-remediation.proposed.sql').read_text()
    sql('begin;\n' + proposal + '\ncommit;\n', 'apply-local-proposal-atomically')
    sql("notify pgrst, 'reload schema';", 'schema-cache-reload')
    success('after_reload_anonymous_capture_closed', '/rpc/capture_is_open', False)
    success('after_reload_auth_owner_exists', '/rpc/current_auth_user_exists', True, 'authenticated', USER_A)
    success('after_reload_deleted_uid_absent', '/rpc/current_auth_user_exists', False, 'authenticated', DELETED_USER)
    success('auth_without_uid_stays_false', '/rpc/current_auth_user_exists', False, 'authenticated')
    refused('anon_cannot_finalize', '/rpc/finalize_submission', '42501', body={'p_submission_id': SUBMISSION_A})
    refused('service_cannot_finalize', '/rpc/finalize_submission', '42501', 'service_role', body={'p_submission_id': SUBMISSION_A})
    refused('other_owner_cannot_finalize', '/rpc/finalize_submission', 'P0002', 'authenticated', USER_B, {'p_submission_id': SUBMISSION_A})
    refused('owner_requires_both_photo_rows', '/rpc/finalize_submission', '23514', 'authenticated', USER_A, {'p_submission_id': MISSING_PHOTOS})
    status, first = request('/rpc/finalize_submission', 'authenticated', USER_A, {'p_submission_id': SUBMISSION_A})
    check('owner_finalizes_through_invoker_adapter', status == 200 and isinstance(first, str), status)
    status, second = request('/rpc/finalize_submission', 'authenticated', USER_A, {'p_submission_id': SUBMISSION_A})
    check('owner_finalization_remains_idempotent', status == 200 and first == second, status)
    refused('auth_no_uid_cannot_finalize', '/rpc/finalize_submission', '42501', 'authenticated', body={'p_submission_id': SUBMISSION_A})
    status, value = request('/rpc/finalize_submission?p_submission_id=' + SUBMISSION_A, 'authenticated', USER_A)
    check('volatile_finalization_not_read_only_get', status >= 400, status)
    success('own_live_grant_accepts_uploads', '/rpc/my_submission_accepts_uploads', True, 'authenticated', USER_A, {'p_submission': WITHDRAWN_SUBMISSION})
    success('other_owner_upload_probe_returns_false', '/rpc/my_submission_accepts_uploads', False, 'authenticated', USER_B, {'p_submission': WITHDRAWN_SUBMISSION})
    sql("insert into public.grant_withdrawals(grant_id,reason) values('41000000-0000-4000-8000-000000000003','steward_action');", 'local-withdrawal')
    success('withdrawn_grant_upload_returns_false', '/rpc/my_submission_accepts_uploads', False, 'authenticated', USER_A, {'p_submission': WITHDRAWN_SUBMISSION})
    refused('anon_upload_probe_denied', '/rpc/my_submission_accepts_uploads', '42501', body={'p_submission': SUBMISSION_A})
    refused('private_profile_get_rejected', '/rpc/current_auth_user_exists', 'PGRST106', 'authenticated', USER_A, profile='private')
    refused('private_profile_post_rejected', '/rpc/current_auth_user_exists', 'PGRST106', 'authenticated', USER_A, body={}, profile='private')
    _, context_a = request('/rpc/http_proof_context', 'authenticated', USER_A)
    _, context_b = request('/rpc/http_proof_context', 'authenticated', USER_B)
    _, context_none = request('/rpc/http_proof_context')
    check('same_pooled_backend_resets_uid_and_role', isinstance(context_a, dict) and isinstance(context_b, dict) and isinstance(context_none, dict) and context_a['pid'] == context_b['pid'] == context_none['pid'] and context_a['uid'] == USER_A and context_b['uid'] == USER_B and context_none['uid'] is None and context_none['role'] == 'anon')
    success('prepared_rpc_owner_context_not_cached', '/rpc/my_submission_accepts_uploads', True, 'authenticated', USER_A, {'p_submission': SUBMISSION_A})
    success('prepared_rpc_other_context_not_cached', '/rpc/my_submission_accepts_uploads', False, 'authenticated', USER_B, {'p_submission': SUBMISSION_A})
    sql('revoke execute on function private.current_auth_user_exists() from authenticated;', 'local-private-execute-revoke')
    refused('warm_adapter_rechecks_private_execute_acl', '/rpc/current_auth_user_exists', '42501', 'authenticated', USER_A)
    sql('grant execute on function private.current_auth_user_exists() to authenticated;', 'local-private-execute-restore')
    success('private_execute_restore_recovers_without_reload', '/rpc/current_auth_user_exists', True, 'authenticated', USER_A)
    sql("create or replace function private.current_auth_user_exists() returns boolean language sql stable security definer set search_path='' as 'select false';", 'local-callee-replacement-deny')
    success('bound_adapter_observes_callee_replacement', '/rpc/current_auth_user_exists', False, 'authenticated', USER_A)
    original = proposal.split('create function private.current_auth_user_exists()', 1)[1].split('revoke all on function private.current_auth_user_exists()', 1)[0]
    sql('create or replace function private.current_auth_user_exists()' + original, 'local-callee-replacement-restore')
    success('bound_adapter_recovers_callee_guard', '/rpc/current_auth_user_exists', True, 'authenticated', USER_A)
    try:
        sql('drop function private.current_auth_user_exists();', 'local-callee-dependency-drop')
    except ProofFailure as error:
        check('dependency_blocks_private_callee_drop', '2BP01' in str(error))
    else:
        raise ProofFailure('dependency_did_not_block_drop')
    sql("notify pgrst, 'reload schema';", 'second-schema-cache-reload')
    success('second_reload_keeps_guarded_dispatch', '/rpc/current_auth_user_exists', True, 'authenticated', USER_A)
    success('capture_stays_closed_at_end', '/rpc/capture_is_open', False)
    check('private_namespace_usage_stays_denied', sql("select not has_schema_privilege('authenticated','private','usage') and not has_schema_privilege('anon','private','usage');", 'final-private-usage').strip() == 't')
    result_status = 'PASS_ISOLATED_LOCAL_HTTP_PROOF'
except Exception as error:
    result_status = 'LOCAL_HTTP_PROOF_FAILED'
    safe_failure = str(error) if isinstance(error, ProofFailure) else type(error).__name__
finally:
    for container in (rest_name, pg_name):
        subprocess.run(['docker', 'rm', '-f', container], capture_output=True)
    shutil.rmtree(source)
    remaining = subprocess.check_output(['docker', 'ps', '-aq', '--filter', 'name=' + suffix], text=True).strip()
    cleaned = not remaining
    jwt_material = ''

receipt = {
    'status': result_status,
    'started_at': started,
    'completed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_head': HEAD,
    'proposal_sha256': digest(BASE / 'gate-c-security-remediation.proposed.sql'),
    'proof_script_sha256': digest(Path(__file__)),
    'images': {'postgres': PG_IMAGE, 'postgrest': REST_IMAGE},
    'network': 'none; PostgREST shares the PG container namespace; loopback only',
    'host_ports': [],
    'source_mount': 'read-only immutable extracted commit',
    'api_exposed_schemas': ['public'],
    'pool_size': 1,
    'prepared_statements': True,
    'proposal_applied_in_one_local_transaction': True,
    'tests': tests,
    'passed': len(tests),
    'cleaned_containers_and_fixture_directory': cleaned,
    'production_operations': [],
    'credentials': 'Synthetic runtime-only signing bytes and JWTs; no real credentials; no token or material persisted.',
    'limits': [
        'Synthetic stand-in and cached PostgREST14.15 only, not hosted Supabase authentication or schema-cache deployment proof.',
        'HTTP write tests and ACL/body fault injection occurred only inside disposable network-isolated local containers.',
        'No actual photos, coordinate values, response rows, tokens, signing material or complete HTTP response bodies persisted.',
        'This checks sequential pooled plan/ACL lifecycle; it does not prove arbitrary concurrent DDL or every possible custom/default role grant.',
    ],
}
if result_status != 'PASS_ISOLATED_LOCAL_HTTP_PROOF':
    receipt['safe_failure'] = safe_failure
path = BASE / 'gate-c-security-remediation-http-local-proof-2026-10-12.json'
path.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': result_status, 'passed': len(tests), 'cleaned': cleaned,
                  'receipt': str(path), 'sha256': digest(path),
                  **({'safe_failure': safe_failure} if result_status != 'PASS_ISOLATED_LOCAL_HTTP_PROOF' else {})}, indent=2))
raise SystemExit(0 if result_status == 'PASS_ISOLATED_LOCAL_HTTP_PROOF' else 1)
