"""Output-only isolated owner-branch SQL proof; no source or production mutation."""
from pathlib import Path
import datetime,hashlib,json,re,shutil,subprocess,tempfile
BASE=Path(__file__).resolve().parent
REPO=BASE/'repo'
IMAGE='sha256:521e67f2812db505fe6d462b1820136394824d7f5c6016a19234b07ac93d6760'
STAND_IN='f9e1ac2f8a88671f99b959e476499392297bd30f'
BRANCHES=[('wp6b','273e76889dccc7ff2e17ba3a689f8b2d4d6a396a'),('wp6d','f3c7043d4bb91f0d2a8d49da3b3971be42f58429')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tap(s):
 rows=s.splitlines()
 return {'planned':sum(int(re.match(r'^1\.\.([0-9]+)',v).group(1)) for v in rows if re.match(r'^1\.\.([0-9]+)',v)),'passed':sum(bool(re.match(r'^ok [0-9]+',v)) for v in rows),'failed':sum(bool(re.match(r'^not ok [0-9]+',v)) for v in rows),'failures':[v for v in rows if re.match(r'^not ok [0-9]+',v)]}
proofs=[]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
for owner,head in BRANCHES:
 source=Path(tempfile.mkdtemp(prefix='gsip-owner-security-proof-',dir='/private/tmp'))
 try:
  paths=subprocess.check_output(['git','ls-tree','-r','--name-only',head,'supabase/migrations','supabase/tests/database'],cwd=REPO,text=True).splitlines()+['supabase/seed.sql']
  for name in paths:
   if not name.endswith('.sql'):continue
   p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',head+':'+name],cwd=REPO))
  p=source/'stand_in.sql';p.write_bytes(subprocess.check_output(['git','show',STAND_IN+':supabase/migration-tests/stand_in.sql'],cwd=REPO))
  for name in ['wp6b-security-remediation.proposed.sql','wp6d-security-remediation.proposed.sql',owner+'-security-remediation.tests.proposed.sql','official-scoped-security-lint.sql']:
   shutil.copy2(BASE/name,source/name)
  core_first='"${PSQL[@]}" -f /source/wp6b-security-remediation.proposed.sql >/dev/null' if owner=='wp6d' else ''
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
printf 'BEFORE_LINT\n';"${PSQL[@]}" -f /source/official-scoped-security-lint.sql
printf 'BEFORE_CONTRACT\n';"${PSQL[@]}" -f /source/OWNER-security-remediation.tests.proposed.sql
printf 'BEFORE_CONTRACT_END\n'
"${PSQL[@]}" -c "update public.service_state set capture_open=true where singleton" >/dev/null
for f in /source/supabase/tests/database/*.sql;do printf 'BEFORE_TEST:%s\n' "$(basename "$f")";"${PSQL[@]}" -f "$f";printf 'BEFORE_TEST_END\n';done
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
"${PSQL[@]}" -f /source/OWNER-security-remediation.proposed.sql >/dev/null
printf 'AFTER_LINT\n';"${PSQL[@]}" -f /source/official-scoped-security-lint.sql
printf 'AFTER_CONTRACT\n';"${PSQL[@]}" -f /source/OWNER-security-remediation.tests.proposed.sql
printf 'AFTER_CONTRACT_END\n'
"${PSQL[@]}" -c "update public.service_state set capture_open=true where singleton" >/dev/null
for f in /source/supabase/tests/database/*.sql;do printf 'AFTER_TEST:%s\n' "$(basename "$f")";"${PSQL[@]}" -f "$f";printf 'AFTER_TEST_END\n';done
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
printf 'CAPTURE_FINAL\n';"${PSQL[@]}" -c "select json_build_object('rows',count(*),'open_rows',count(*) filter(where capture_open)) from public.service_state"
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
  proofs.append({'owner':owner,'baseline_head':head,'core_proposal_inherited':owner=='wp6d','migration_files':len([p for p in paths if p.startswith('supabase/migrations/')]),'new_contract_before':before,'new_contract_after':after_contract,'existing_suites_before':baseline,'existing_suites_after':final,'official_lints_before':after('BEFORE_LINT'),'official_lints_after':after('AFTER_LINT'),'capture_final':capture,'sql_sha256':sha(BASE/(owner+'-security-remediation.proposed.sql')),'tests_sha256':sha(BASE/(owner+'-security-remediation.tests.proposed.sql'))})
 finally:shutil.rmtree(source)
receipt={'status':'PASS_LOCAL_OWNER_SPLIT_PROPOSALS','started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'image_id':IMAGE,'network':'none','source_mount':'read-only','host_ports':[],'production_operations':[],'proofs':proofs,'limits':['Proposal files only; actual generated migration files require their own source-bound checks.','WP6d uses the same core proposal as an inherited fix-forward prerequisite.','Scoped official rules are not a production advisor result.','Only disposable synthetic local tests temporarily open the fixture gate; final capture is false.']}
p=BASE/'gate-c-security-remediation-owner-split-local-proof-2026-10-12.json';p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'receipt':str(p),'sha256':sha(p),'branches':[{'owner':v['owner'],'new_before_failed':v['new_contract_before']['failed'],'new_after':v['new_contract_after'],'existing_after_assertions':sum(w['passed'] for w in v['existing_suites_after'].values()),'lint_before':len(v['official_lints_before']),'lint_after':len(v['official_lints_after'])} for v in proofs]},indent=2))
