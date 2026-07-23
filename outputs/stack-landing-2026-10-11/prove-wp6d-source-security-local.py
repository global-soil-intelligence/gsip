"""Output-only isolated owner-branch SQL proof; no source or production mutation."""
from pathlib import Path
import datetime,hashlib,json,re,shutil,subprocess,tempfile
BASE=Path(__file__).resolve().parent
REPO=BASE/'repo'
IMAGE='sha256:521e67f2812db505fe6d462b1820136394824d7f5c6016a19234b07ac93d6760'
STAND_IN='f9e1ac2f8a88671f99b959e476499392297bd30f'
BRANCHES=[('wp6d','4fcfd955eb119381d703cf07d045bc32e5ebc5b8')]
MANAGED=Path('/Users/justinhart/.codex/worktrees/gsip-coding-guidance/GSIP 2.0')
SOURCE_SQL=MANAGED/'supabase/migrations/20261012142348_wp6d_private_rights_boundary.sql'
SOURCE_TEST=MANAGED/'supabase/tests/database/wp6d_private_rights_boundary.test.sql'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tap(s):
 rows=s.splitlines()
 return {'planned':sum(int(re.match(r'^1\.\.([0-9]+)',v).group(1)) for v in rows if re.match(r'^1\.\.([0-9]+)',v)),'passed':sum(bool(re.match(r'^ok [0-9]+',v)) for v in rows),'failed':sum(bool(re.match(r'^not ok [0-9]+',v)) for v in rows),'failures':[v for v in rows if re.match(r'^not ok [0-9]+',v)]}
proofs=[]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
for owner,head in BRANCHES:
 source=Path(tempfile.mkdtemp(prefix='gsip-owner-security-proof-',dir='/private/tmp'))
 try:
  paths=subprocess.check_output(['git','ls-tree','-r','--name-only',head,'supabase/migrations','supabase/tests/database'],cwd=MANAGED,text=True).splitlines()+['supabase/seed.sql']
  for name in paths:
   if not name.endswith('.sql'):continue
   p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',head+':'+name],cwd=MANAGED))
  p=source/'stand_in.sql';p.write_bytes(subprocess.check_output(['git','show',STAND_IN+':supabase/migration-tests/stand_in.sql'],cwd=REPO))
  for name in ['wp6b-security-remediation.proposed.sql','wp6d-security-remediation.proposed.sql',owner+'-security-remediation.tests.proposed.sql','official-scoped-security-lint.sql']:
   shutil.copy2(BASE/name,source/name)
  (source/'wp6d-security-remediation.proposed.sql').write_bytes(SOURCE_SQL.read_bytes())
  (source/'wp6d-security-remediation.tests.proposed.sql').write_bytes(SOURCE_TEST.read_bytes())
  for name in ['catalog-snapshot.sql','catalog-snapshot-supplement.sql']:shutil.copy2(BASE/name,source/name)
  core_first='' # Actual inherited WP6b source is already in the immutable parent migration tree.
  script=r'''set -euo pipefail
PG_BIN="$(pg_config --bindir)";work=/tmp/gsip-owner-proof;mkdir -p "$work"
trap '"$PG_BIN/pg_ctl" -D "$work/data" -m immediate stop >/dev/null 2>&1 || true' EXIT
"$PG_BIN/initdb" -D "$work/data" -A trust -U postgres >/dev/null
"$PG_BIN/pg_ctl" -D "$work/data" -l "$work/server.log" -w -o "-k $work -p 55499 -c listen_addresses=" start >/dev/null
PSQL=("$PG_BIN/psql" -X -q -t -A -v ON_ERROR_STOP=1 -h "$work" -p 55499 -U postgres -d postgres)
"${PSQL[@]}" -f /source/stand_in.sql >/dev/null
for f in /source/supabase/migrations/*.sql;do "${PSQL[@]}" -f "$f" >/dev/null 2>"$work/step.err";done
"${PSQL[@]}" -f /source/supabase/seed.sql >/dev/null
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
CORE_FIRST
printf 'BEFORE_PRIMARY\n';"${PSQL[@]}" -f /source/catalog-snapshot.sql
printf 'BEFORE_SUPPLEMENT\n';"${PSQL[@]}" -f /source/catalog-snapshot-supplement.sql
printf 'BEFORE_LINT\n';"${PSQL[@]}" -f /source/official-scoped-security-lint.sql
printf 'BEFORE_CONTRACT\n';"${PSQL[@]}" -f /source/OWNER-security-remediation.tests.proposed.sql
printf 'BEFORE_CONTRACT_END\n'
"${PSQL[@]}" -c "update public.service_state set capture_open=true where singleton" >/dev/null
for f in /source/supabase/tests/database/*.sql;do printf 'BEFORE_TEST:%s\n' "$(basename "$f")";"${PSQL[@]}" -f "$f";printf 'BEFORE_TEST_END\n';done
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
"${PSQL[@]}" -f /source/OWNER-security-remediation.proposed.sql >/dev/null
printf 'AFTER_PRIMARY\n';"${PSQL[@]}" -f /source/catalog-snapshot.sql
printf 'AFTER_SUPPLEMENT\n';"${PSQL[@]}" -f /source/catalog-snapshot-supplement.sql
printf 'AFTER_LINT\n';"${PSQL[@]}" -f /source/official-scoped-security-lint.sql
printf 'AFTER_CONTRACT\n';"${PSQL[@]}" -f /source/OWNER-security-remediation.tests.proposed.sql
printf 'AFTER_CONTRACT_END\n'
"${PSQL[@]}" -c "update public.service_state set capture_open=true where singleton" >/dev/null
for f in /source/supabase/tests/database/*.sql;do printf 'AFTER_TEST:%s\n' "$(basename "$f")";"${PSQL[@]}" -f "$f";printf 'AFTER_TEST_END\n';done
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
printf 'CAPTURE_FINAL\n';"${PSQL[@]}" -c "select json_build_object('rows',count(*),'open_rows',count(*) filter(where capture_open)) from public.service_state"

# Compare the forward-upgraded database against a sorted fresh install.
"$PG_BIN/createdb" -h "$work" -p 55499 -U postgres fresh_install
PSQL=("$PG_BIN/psql" -X -q -t -A -v ON_ERROR_STOP=1 -h "$work" -p 55499 -U postgres -d fresh_install)
"${PSQL[@]}" -f /source/stand_in.sql >/dev/null
for f in /source/supabase/migrations/*.sql;do "${PSQL[@]}" -f "$f" >/dev/null 2>"$work/step.err";done
"${PSQL[@]}" -f /source/OWNER-security-remediation.proposed.sql >/dev/null
"${PSQL[@]}" -f /source/supabase/seed.sql >/dev/null
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
printf 'FRESH_PRIMARY\n';"${PSQL[@]}" -f /source/catalog-snapshot.sql
printf 'FRESH_SUPPLEMENT\n';"${PSQL[@]}" -f /source/catalog-snapshot-supplement.sql
'''.replace('CORE_FIRST',core_first).replace('OWNER',owner)
  run=subprocess.run(['docker','run','--rm','--network','none','--user','postgres','--entrypoint','/bin/bash','-v',str(source)+':/source:ro',IMAGE,'-c',script],capture_output=True,text=True)
  if run.returncode:
   print(json.dumps({'owner':owner,'exit_code':run.returncode,'errors':[v for v in run.stderr.splitlines() if 'ERROR:' in v]}));raise SystemExit(run.returncode)
  def block(start,end):return run.stdout.split(start+'\n',1)[1].split(end+'\n',1)[0]
  def after(label):return json.loads(run.stdout.split(label+'\n',1)[1].splitlines()[0])
  def suite(prefix):
   out={}
   for fragment in run.stdout.split(prefix+':')[1:]:
    name,rest=fragment.split('\n',1);out[name]=tap(rest.split(prefix+'_END\n',1)[0])
   return out
  before=tap(block('BEFORE_CONTRACT','BEFORE_CONTRACT_END'));after_contract=tap(block('AFTER_CONTRACT','AFTER_CONTRACT_END'))
  baseline=suite('BEFORE_TEST');final=suite('AFTER_TEST')
  assert before['failed']>0,before
  assert after_contract['failed']==0 and after_contract['passed']==after_contract['planned'],after_contract
  assert all(v['failed']==0 and v['passed']==v['planned'] for v in baseline.values()),baseline
  assert all(v['failed']==0 and v['passed']==v['planned'] for v in final.values()),final
  capture=after('CAPTURE_FINAL');assert capture=={'rows':1,'open_rows':0}
  assert after('AFTER_PRIMARY')==after('FRESH_PRIMARY'),'fresh/upgrade primary metadata mismatch'
  assert after('AFTER_SUPPLEMENT')==after('FRESH_SUPPLEMENT'),'fresh/upgrade supplement mismatch'
  b=after('BEFORE_PRIMARY');a=after('AFTER_PRIMARY');sb=after('BEFORE_SUPPLEMENT');sa=after('AFTER_SUPPLEMENT')
  for key in ['column_grants','columns','constraints','extensions','indexes','table_grants','tables','triggers']:assert b[key]==a[key],key
  for key in ['schema_grants','storage_policies','views']:assert sb[key]==sa[key],key
  old={v['name']:v for v in b['functions']};new={v['name']:v for v in a['functions']}
  assert old.keys()==new.keys()
  assert all(old[k]['grants']==new[k]['grants'] and old[k]['owner']==new[k]['owner'] for k in old)
  old_private={v['name']:v for v in sb['private_functions']};new_private={v['name']:v for v in sa['private_functions']}
  assert all(new_private[k]==v for k,v in old_private.items())
  assert set(new_private)-set(old_private)=={'current_auth_user_exists','my_submission_accepts_uploads'}
  proofs.append({'owner':owner,'baseline_head':head,'core_proposal_inherited':owner=='wp6d','migration_files':len([p for p in paths if p.startswith('supabase/migrations/')]),'new_contract_before':before,'new_contract_after':after_contract,'existing_suites_before':baseline,'existing_suites_after':final,'official_lints_before':after('BEFORE_LINT'),'official_lints_after':after('AFTER_LINT'),'capture_final':capture,'source_migration':str(SOURCE_SQL),'sql_sha256':sha(SOURCE_SQL),'source_tests':str(SOURCE_TEST),'tests_sha256':sha(SOURCE_TEST),'existing_metadata_grants_owners_unchanged':True,'fresh_install_equals_forward_upgrade_primary_and_supplement':True})
 finally:shutil.rmtree(source)
receipt={'status':'PASS_LOCAL_WP6D_SOURCE_BOUNDARY','started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'image_id':IMAGE,'network':'none','source_mount':'read-only','host_ports':[],'production_operations':[],'proofs':proofs,'limits':['Actual uncommitted source files are hash-bound; root alone owns source commit and propagation.','Inherited WP6b source migration/test are present in the exact immutable parent tree; no proposal is substituted.','Scoped official rules are not a production advisor result.','Only disposable synthetic local tests temporarily open the fixture gate; final capture is false.']}
p=BASE/'wp6d-private-rights-boundary-local-proof-2026-10-12.json';p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'receipt':str(p),'sha256':sha(p),'branches':[{'owner':v['owner'],'new_before_failed':v['new_contract_before']['failed'],'new_after':v['new_contract_after'],'existing_after_assertions':sum(w['passed'] for w in v['existing_suites_after'].values()),'lint_before':len(v['official_lints_before']),'lint_after':len(v['official_lints_after'])} for v in proofs]},indent=2))
