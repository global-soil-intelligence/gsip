"""Source-bound 26-to-28 fresh/upgrade proof in isolated PostgreSQL; output only."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,shutil,subprocess,tempfile
parser=argparse.ArgumentParser();parser.add_argument('head');args=parser.parse_args()
BASE=Path(__file__).resolve().parent
SOURCE_REPO=Path('/Users/justinhart/.codex/worktrees/gsip-coding-guidance/GSIP 2.0')
BASELINE_REPO=BASE/'repo'
BASELINE='f9e1ac2f8a88671f99b959e476499392297bd30f'
IMAGE='sha256:521e67f2812db505fe6d462b1820136394824d7f5c6016a19234b07ac93d6760'
def git(repo,*args):return subprocess.check_output(['git',*args],cwd=repo)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(repo,head,path):return git(repo,'ls-tree','-r','--name-only',head,path).decode().splitlines()
old_migrations=tree(BASELINE_REPO,BASELINE,'supabase/migrations')
new_migrations=tree(SOURCE_REPO,args.head,'supabase/migrations')
assert len(old_migrations)==26 and len(new_migrations)==28,(len(old_migrations),len(new_migrations))
assert all(git(BASELINE_REPO,'show',BASELINE+':'+v)==git(SOURCE_REPO,'show',args.head+':'+v) for v in old_migrations)
pending=sorted(set(new_migrations)-set(old_migrations));assert len(pending)==2
assert pending[0].endswith('_wp6b_invoker_boundary.sql') and pending[1].endswith('_wp6d_private_rights_boundary.sql')
assert pending[0]>max(old_migrations)
source=Path(tempfile.mkdtemp(prefix='gsip-final-security-proof-',dir='/private/tmp'))
try:
 for folder,repo,head in [('baseline',BASELINE_REPO,BASELINE),('target',SOURCE_REPO,args.head)]:
  paths=tree(repo,head,'supabase/migrations')+tree(repo,head,'supabase/tests/database')+tree(repo,head,'supabase/migration-tests')+['supabase/seed.sql']
  if folder=='target':paths+=['scripts/db-migration-test.sh']
  for name in paths:
   p=source/folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(git(repo,'show',head+':'+name))
 assert (source/'baseline/supabase/seed.sql').read_bytes()==(source/'target/supabase/seed.sql').read_bytes()
 for name in ['catalog-snapshot.sql','catalog-snapshot-supplement.sql','official-scoped-security-lint.sql']:shutil.copy2(BASE/name,source/name)
 count_sql=r'''create temp table gsip_safe_counts(table_name text primary key, row_count bigint);
do $$ declare r record;begin
 for r in select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname in ('public','private','auth','storage') and c.relkind in ('r','p') loop
  execute format('insert into gsip_safe_counts select %L,count(*) from %I.%I',r.nspname||'.'||r.relname,r.nspname,r.relname);
 end loop;
end $$;
select json_object_agg(table_name,row_count order by table_name) from gsip_safe_counts;
'''
 (source/'counts.sql').write_text(count_sql)
 script=r'''set -euo pipefail
PG_BIN="$(pg_config --bindir)";work=/tmp/gsip-final-security-proof;mkdir -p "$work"
trap '"$PG_BIN/pg_ctl" -D "$work/data" -m immediate stop >/dev/null 2>&1 || true' EXIT
"$PG_BIN/initdb" -D "$work/data" -A trust -U postgres >/dev/null
"$PG_BIN/pg_ctl" -D "$work/data" -l "$work/server.log" -w -o "-k $work -p 55499 -c listen_addresses=" start >/dev/null
PSQL=("$PG_BIN/psql" -X -q -t -A -v ON_ERROR_STOP=1 -h "$work" -p 55499 -U postgres -d postgres)
"${PSQL[@]}" -f /source/baseline/supabase/migration-tests/stand_in.sql >/dev/null
for f in /source/baseline/supabase/migrations/*.sql;do "${PSQL[@]}" -f "$f" >/dev/null 2>"$work/step.err";done
"${PSQL[@]}" -f /source/baseline/supabase/seed.sql >/dev/null
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
printf 'BEFORE_PRIMARY\n';"${PSQL[@]}" -f /source/catalog-snapshot.sql
printf 'BEFORE_SUPPLEMENT\n';"${PSQL[@]}" -f /source/catalog-snapshot-supplement.sql
printf 'BEFORE_COUNTS\n';"${PSQL[@]}" -f /source/counts.sql
printf 'BEFORE_LINT\n';"${PSQL[@]}" -f /source/official-scoped-security-lint.sql
for f in /source/target/supabase/tests/database/*boundary.test.sql;do printf 'BEFORE_NEW:%s\n' "$(basename "$f")";"${PSQL[@]}" -f "$f";printf 'BEFORE_NEW_END\n';done
"${PSQL[@]}" -c "update public.service_state set capture_open=true where singleton" >/dev/null
for f in /source/baseline/supabase/tests/database/*.sql;do printf 'BASELINE_TEST:%s\n' "$(basename "$f")";"${PSQL[@]}" -f "$f";printf 'BASELINE_TEST_END\n';done
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
APPLY_PENDING
printf 'AFTER_PRIMARY\n';"${PSQL[@]}" -f /source/catalog-snapshot.sql
printf 'AFTER_SUPPLEMENT\n';"${PSQL[@]}" -f /source/catalog-snapshot-supplement.sql
printf 'AFTER_COUNTS\n';"${PSQL[@]}" -f /source/counts.sql
printf 'AFTER_LINT\n';"${PSQL[@]}" -f /source/official-scoped-security-lint.sql
"${PSQL[@]}" -c "update public.service_state set capture_open=true where singleton" >/dev/null
for f in /source/target/supabase/tests/database/*.sql;do printf 'AFTER_TEST:%s\n' "$(basename "$f")";"${PSQL[@]}" -f "$f";printf 'AFTER_TEST_END\n';done
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
printf 'CAPTURE_FINAL\n';"${PSQL[@]}" -c "select json_build_object('rows',count(*),'open_rows',count(*) filter(where capture_open)) from public.service_state"
"$PG_BIN/createdb" -h "$work" -p 55499 -U postgres fresh_install
PSQL=("$PG_BIN/psql" -X -q -t -A -v ON_ERROR_STOP=1 -h "$work" -p 55499 -U postgres -d fresh_install)
"${PSQL[@]}" -f /source/target/supabase/migration-tests/stand_in.sql >/dev/null
for f in /source/target/supabase/migrations/*.sql;do "${PSQL[@]}" -f "$f" >/dev/null 2>"$work/step.err";done
"${PSQL[@]}" -f /source/target/supabase/seed.sql >/dev/null
"${PSQL[@]}" -c "update public.service_state set capture_open=false where singleton" >/dev/null
printf 'FRESH_PRIMARY\n';"${PSQL[@]}" -f /source/catalog-snapshot.sql
printf 'FRESH_SUPPLEMENT\n';"${PSQL[@]}" -f /source/catalog-snapshot-supplement.sql
printf 'FRESH_COUNTS\n';"${PSQL[@]}" -f /source/counts.sql
printf 'MIGRATION_REHEARSAL\n';bash /source/target/scripts/db-migration-test.sh
printf 'MIGRATION_REHEARSAL_END\n'
'''
 script=script.replace('APPLY_PENDING','\n'.join('"${PSQL[@]}" -f /source/target/'+v+' >/dev/null' for v in pending))
 started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 run=subprocess.run(['docker','run','--rm','--network','none','--user','postgres','--entrypoint','/bin/bash','-v',str(source)+':/source:ro',IMAGE,'-c',script],capture_output=True,text=True)
 if run.returncode:
  print(json.dumps({'exit_code':run.returncode,'errors':[v for v in run.stderr.splitlines() if 'ERROR:' in v],'last_stage':run.stdout.splitlines()[-1][:100] if run.stdout else None}));raise SystemExit(run.returncode)
 def after(label):return json.loads(run.stdout.split(label+'\n',1)[1].splitlines()[0])
 def block(start,end):return run.stdout.split(start+'\n',1)[1].split(end+'\n',1)[0]
 def tap(s):
  rows=s.splitlines();return {'planned':sum(int(re.match(r'^1\.\.([0-9]+)',v).group(1)) for v in rows if re.match(r'^1\.\.([0-9]+)',v)),'passed':sum(bool(re.match(r'^ok [0-9]+',v)) for v in rows),'failed':sum(bool(re.match(r'^not ok [0-9]+',v)) for v in rows),'failures':[v for v in rows if re.match(r'^not ok [0-9]+',v)]}
 def suites(prefix):
  out={}
  for f in run.stdout.split(prefix+':')[1:]:
   name,rest=f.split('\n',1);out[name]=tap(rest.split(prefix+'_END\n',1)[0])
  return out
 baseline=suites('BASELINE_TEST');new_before=suites('BEFORE_NEW');final=suites('AFTER_TEST')
 assert all(v['failed']==0 and v['passed']==v['planned'] for v in baseline.values()),baseline
 assert sum(v['passed'] for v in baseline.values())==262
 assert sum(v['failed'] for v in new_before.values())==13,new_before
 assert all(v['failed']==0 and v['passed']==v['planned'] for v in final.values()),final
 assert sum(v['passed'] for v in final.values())==299,final
 before=after('BEFORE_PRIMARY');final_primary=after('AFTER_PRIMARY');bs=after('BEFORE_SUPPLEMENT');final_supp=after('AFTER_SUPPLEMENT')
 assert final_primary==after('FRESH_PRIMARY')
 assert final_supp==after('FRESH_SUPPLEMENT')
 counts=after('AFTER_COUNTS');assert counts==after('BEFORE_COUNTS')==after('FRESH_COUNTS')
 for k in ['column_grants','columns','constraints','extensions','indexes','table_grants','tables','triggers']:assert before[k]==final_primary[k],k
 for k in ['schema_grants','storage_policies','views']:assert bs[k]==final_supp[k],k
 old={v['name']:v for v in before['functions']};new={v['name']:v for v in final_primary['functions']}
 assert old.keys()==new.keys();assert all(old[k]['grants']==new[k]['grants'] and old[k]['owner']==new[k]['owner'] for k in old)
 op={v['name']:v for v in bs['private_functions']};np={v['name']:v for v in final_supp['private_functions']}
 assert all(np[k]==v for k,v in op.items());assert set(np)-set(op)=={'finalize_submission','current_auth_user_exists','my_submission_accepts_uploads'}
 for name in ['finalize_submission','current_auth_user_exists','my_submission_accepts_uploads']:
  f=np[name];assert f['owner']=='postgres' and f['security_definer'] is True and f['config']==['search_path=\"\"']
  expected=[{'role':'authenticated','privilege':'EXECUTE','grantable':False},{'role':'postgres','privilege':'EXECUTE','grantable':False}]
  if name!='finalize_submission':expected.append({'role':'service_role','privilege':'EXECUTE','grantable':False})
  assert f['grants']==expected,(name,f['grants'])
 lints_before=after('BEFORE_LINT');lints_after=after('AFTER_LINT');assert len(lints_before)==7 and lints_after==[]
 capture=after('CAPTURE_FINAL');assert capture=={'rows':1,'open_rows':0}
 rehearsal=block('MIGRATION_REHEARSAL','MIGRATION_REHEARSAL_END').splitlines()
 tally=[re.match(r'^(.*): ([0-9]+)/([0-9]+) ok$',v) for v in rehearsal];tally=[v for v in tally if v]
 assert tally and all(v.group(2)==v.group(3) for v in tally),rehearsal
 assert sum(int(v.group(2)) for v in tally)==13,rehearsal
 artifacts={}
 for name,data in [('canonical-catalog-target28.json',final_primary),('canonical-supplement-target28.json',final_supp),('canonical-counts-target28-synthetic.json',counts)]:
  p=BASE/name;p.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n');artifacts[name]=sha(p)
 receipt={'status':'PASS_LOCAL_SOURCE_26_TO_28','started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline_head':BASELINE,'target_head':args.head,'image_id':IMAGE,'source_mount':'read-only','network':'none','host_ports':[],'old_migrations_byte_identical':True,'pending_migrations':[{'path':v,'sha256':sha(source/'target'/v)} for v in pending],'baseline_migration_count':26,'target_migration_count':28,'baseline_existing_suites':baseline,'new_suites_before':new_before,'target_all_suites':final,'existing_counts_unchanged':True,'table_count_compared':len(counts),'fresh_install_matches_forward_upgrade_catalog_supplement_counts':True,'existing_public_owners_callers_and_other_grants_unchanged':True,'old_private_function_records_unchanged':True,'new_private_complete_acls_exact':True,'private_helpers_owner_and_pinned_search_path_verified':True,'official_scoped_lints_before':lints_before,'official_scoped_lints_after':lints_after,'capture_final_counts':capture,'migration_rehearsal_summaries':[v.group(0) for v in tally],'artifacts':artifacts,'production_operations':[],'limits':['Synthetic isolated Supabase stand-in; does not replace hosted security advisor or production postchecks.','Seed table counts are synthetic reference counts; do not assert hosted counts equal these.','Official scoped rule proof covers0008,0028,0029 with pgrst.db_schemas=public.','Capture was temporarily open only for checked-in synthetic local fixtures; final state false.']}
 p=BASE/'security-target28-fresh-upgrade-local-proof-2026-10-12.json';p.write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'receipt':str(p),'sha256':sha(p),'target_head':args.head,'assertions':299,'migration_rehearsal_assertions':13,'fresh_upgrade_equal':True,'table_count_compared':len(counts),'artifacts':artifacts},indent=2))
finally:shutil.rmtree(source)
