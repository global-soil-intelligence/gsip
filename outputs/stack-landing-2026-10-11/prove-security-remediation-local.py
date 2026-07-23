"""Isolated no-network PostgreSQL proof; never connects to production or edits source."""
from pathlib import Path
import datetime, hashlib, json, re, shutil, subprocess, tempfile
BASE=Path(__file__).resolve().parent
REPO=BASE/'repo'
SOURCE='f9e1ac2f8a88671f99b959e476499392297bd30f'
IMAGE='sha256:521e67f2812db505fe6d462b1820136394824d7f5c6016a19234b07ac93d6760'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
source=Path(tempfile.mkdtemp(prefix='gsip-security-proposal-',dir='/private/tmp'))
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',SOURCE,'supabase/migrations','supabase/tests/database'],cwd=REPO,text=True).splitlines()+['supabase/migration-tests/stand_in.sql','supabase/seed.sql']
for name in paths:
 if not name.endswith('.sql'): continue
 p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',f'{SOURCE}:{name}'],cwd=REPO))
for name in ['catalog-snapshot.sql','catalog-snapshot-supplement.sql','gate-c-security-remediation.proposed.sql','gate-c-security-remediation-role-tests.sql']:
 shutil.copy2(BASE/name,source/name)
official=(BASE/'official-splinter-splinter.sql').read_text()
assert digest(BASE/'official-splinter-splinter.sql')=='d8d558baad3e03832e521c527907fa50a9a172fabd899dd0f5c2504a5a0e9349'
parts=official.split('\nunion all\n')
names=['rls_enabled_no_policy','anon_security_definer_function_executable','authenticated_security_definer_function_executable']
slices=[next(v for v in parts if "'"+name+"' as name" in v) for name in names]
rule_sql="set pgrst.db_schemas = 'public';\nselect coalesce(json_agg(row_to_json(lint)), '[]'::json) from (\n"+'\nunion all\n'.join(slices)+'\n) lint;\n'
(source/'official-scoped-lint.sql').write_text(rule_sql);(BASE/'official-scoped-security-lint.sql').write_text(rule_sql)
script=r'''set -euo pipefail
PG_BIN="$(pg_config --bindir)";work=/tmp/gsip-security-role-proof;mkdir -p "$work"
trap '"$PG_BIN/pg_ctl" -D "$work/data" -m immediate stop >/dev/null 2>&1 || true' EXIT
"$PG_BIN/initdb" -D "$work/data" -A trust -U postgres >/dev/null
"$PG_BIN/pg_ctl" -D "$work/data" -l "$work/server.log" -w -o "-k $work -p 55499 -c listen_addresses=" start >/dev/null
PSQL=("$PG_BIN/psql" -X -q -t -A -v ON_ERROR_STOP=1 -h "$work" -p 55499 -U postgres -d postgres)
"${PSQL[@]}" -f /source/supabase/migration-tests/stand_in.sql >/dev/null
for f in /source/supabase/migrations/*.sql;do "${PSQL[@]}" -f "$f" >/dev/null 2>"$work/step.err";done
"${PSQL[@]}" -f /source/supabase/seed.sql >/dev/null
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
printf 'VERSION\n';"${PSQL[@]}" -c "select current_setting('server_version')"
printf 'BEFORE_PRIMARY\n';"${PSQL[@]}" -f /source/catalog-snapshot.sql
printf 'BEFORE_SUPPLEMENT\n';"${PSQL[@]}" -f /source/catalog-snapshot-supplement.sql
printf 'BEFORE_LINT\n';"${PSQL[@]}" -f /source/official-scoped-lint.sql
printf 'BEFORE_CONTRACT\n';"${PSQL[@]}" -f /source/gate-c-security-remediation-role-tests.sql
printf 'BEFORE_CONTRACT_END\n'
# Local synthetic browser/database fixture gate only, as prescribed by the checked-in suite.
"${PSQL[@]}" -c "update public.service_state set capture_open=true where singleton" >/dev/null
for f in /source/supabase/tests/database/*.sql;do printf 'BASELINE_TEST:%s\n' "$(basename "$f")";"${PSQL[@]}" -f "$f";printf 'BASELINE_TEST_END\n';done
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
"${PSQL[@]}" -f /source/gate-c-security-remediation.proposed.sql >/dev/null
printf 'AFTER_PRIMARY\n';"${PSQL[@]}" -f /source/catalog-snapshot.sql
printf 'AFTER_SUPPLEMENT\n';"${PSQL[@]}" -f /source/catalog-snapshot-supplement.sql
printf 'AFTER_LINT\n';"${PSQL[@]}" -f /source/official-scoped-lint.sql
printf 'AFTER_CONTRACT\n';"${PSQL[@]}" -f /source/gate-c-security-remediation-role-tests.sql
printf 'AFTER_CONTRACT_END\n'
"${PSQL[@]}" -c "update public.service_state set capture_open=true where singleton" >/dev/null
for f in /source/supabase/tests/database/*.sql;do printf 'AFTER_TEST:%s\n' "$(basename "$f")";"${PSQL[@]}" -f "$f";printf 'AFTER_TEST_END\n';done
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
printf 'CAPTURE_FINAL\n';"${PSQL[@]}" -c "select json_build_object('rows',count(*),'open_rows',count(*) filter(where capture_open)) from public.service_state"
'''
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=subprocess.run(['docker','run','--rm','--network','none','--user','postgres','--entrypoint','/bin/bash','-v',str(source)+':/source:ro',IMAGE,'-c',script],capture_output=True,text=True)
if result.returncode:
 # Show only the error class, not fixture SQL or any row contents.
 print(json.dumps({'status':'LOCAL_PROOF_ERROR','exit_code':result.returncode,'safe_error_lines':[v for v in result.stderr.splitlines() if 'ERROR:' in v],'stdout_stage':result.stdout.splitlines()[-1][:100] if result.stdout else None}));raise SystemExit(result.returncode)
lines=result.stdout.splitlines()
def after(label): return json.loads(lines[lines.index(label)+1])
before_primary=after('BEFORE_PRIMARY');after_primary=after('AFTER_PRIMARY');before_supp=after('BEFORE_SUPPLEMENT');after_supp=after('AFTER_SUPPLEMENT')
def tap(block):
 l=block.splitlines();return {'planned':sum(int(re.match(r'^1\.\.([0-9]+)',v).group(1)) for v in l if re.match(r'^1\.\.([0-9]+)',v)),'passed':sum(bool(re.match(r'^ok [0-9]+',v)) for v in l),'failed':sum(bool(re.match(r'^not ok [0-9]+',v)) for v in l),'failures':[v for v in l if re.match(r'^not ok [0-9]+',v)]}
def block(start,end): return result.stdout.split(start+'\n',1)[1].split(end+'\n',1)[0]
before_contract=tap(block('BEFORE_CONTRACT','BEFORE_CONTRACT_END'));after_contract=tap(block('AFTER_CONTRACT','AFTER_CONTRACT_END'))
def suites(prefix):
 out={}
 for fragment in result.stdout.split(prefix+':')[1:]:
  name,rest=fragment.split('\n',1);out[name]=tap(rest.split(prefix+'_END\n',1)[0])
 return out
baseline=suites('BASELINE_TEST');final=suites('AFTER_TEST')
assert before_contract['failed']==5 and before_contract['passed']==23, before_contract
assert after_contract['failed']==0 and after_contract['passed']==28, after_contract
assert all(v['failed']==0 and v['passed']==v['planned'] for v in baseline.values()), baseline
assert all(v['failed']==0 and v['passed']==v['planned'] for v in final.values()), final
unchanged_sections=['column_grants','columns','constraints','extensions','indexes','table_grants','tables','triggers']
assert all(before_primary[k]==after_primary[k] for k in unchanged_sections)
assert before_supp['schema_grants']==after_supp['schema_grants']
assert before_supp['storage_policies']==after_supp['storage_policies']
assert before_supp['views']==after_supp['views']
old_functions={v['name']:v for v in before_primary['functions']};new_functions={v['name']:v for v in after_primary['functions']}
assert old_functions.keys()==new_functions.keys()
function_acl_diffs={k:{'before':old_functions[k]['grants'],'after':new_functions[k]['grants']} for k in old_functions if old_functions[k]['grants']!=new_functions[k]['grants']}
if function_acl_diffs: print(json.dumps({'function_acl_diffs':function_acl_diffs}))
assert not function_acl_diffs
assert all(old_functions[k]['owner']==new_functions[k]['owner'] for k in old_functions)
priv_before={v['name']:v for v in before_supp['private_functions']};priv_after={v['name']:v for v in after_supp['private_functions']}
assert all(priv_after[k]==v for k,v in priv_before.items())
assert set(priv_after)-set(priv_before)=={'finalize_submission','current_auth_user_exists','my_submission_accepts_uploads'}
before_lint=after('BEFORE_LINT');after_lint=after('AFTER_LINT');assert len(before_lint)==7;assert len(after_lint)==0
capture=after('CAPTURE_FINAL');assert capture=={'rows':1,'open_rows':0}
receipt={'status':'PASS_ISOLATED_LOCAL_PROPOSAL_PROOF','started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_head':SOURCE,'image_id':IMAGE,'postgres_version':lines[lines.index('VERSION')+1],'network':'none','host_ports':[],'user':'postgres','source_mount':'read-only','source_changes':False,'production_operations':[],'official_rule_source_sha256':digest(BASE/'official-splinter-splinter.sql'),'official_scoped_rule_sha256':digest(BASE/'official-scoped-security-lint.sql'),'sql_proposal_sha256':digest(BASE/'gate-c-security-remediation.proposed.sql'),'new_test_sql_sha256':digest(BASE/'gate-c-security-remediation-role-tests.sql'),'new_contract_before':before_contract,'new_contract_after':after_contract,'baseline_existing_suites':baseline,'after_existing_suites':final,'unchanged_metadata_sections':unchanged_sections+['schema_grants','storage_policies','views'],'public_function_names_callers_and_owners_unchanged':True,'all_old_private_function_records_unchanged':True,'new_private_function_names':sorted(set(priv_after)-set(priv_before)),'official_scoped_lints_before':before_lint,'official_scoped_lints_after':after_lint,'capture_final_counts':capture,'limits':['Disposable synthetic stand-in; not production remediation or production advisor result.','Scoped immutable official SQL checks only0008,0028,0029 with local pgrst.db_schemas=public; hosted API config must still prove private not exposed.','No pgTAP fixture data, SQL row contents or coordinates persisted in the receipt.','Spec-first architecture and owning-branch fix-forward decision remain required before source implementation.']}
p=BASE/'gate-c-security-remediation-local-proof-2026-10-12.json';p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'receipt':str(p),'sha256':digest(p),'new_before':before_contract,'new_after':after_contract,'existing_assertions_each_stage':sum(v['passed'] for v in final.values()),'existing_files':len(final),'lints_before':len(before_lint),'lints_after':len(after_lint),'postgres_version':receipt['postgres_version'],'capture_final':capture},indent=2))
shutil.rmtree(source)
