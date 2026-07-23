"""Disposable, network-free ledger/RLS rehearsal. Never connects to production.

Run from any directory with Python 3 and the installed Docker image. Inputs/receipts stay
outside the source checkout. The ledger changes model documented insert/delete effects;
this driver does not execute Supabase CLI repair or deploy commands.
"""
from __future__ import annotations
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE / 'repo'
SOURCE = 'f9e1ac2f8a88671f99b959e476499392297bd30f'
IMAGE = 'sha256:521e67f2812db505fe6d462b1820136394824d7f5c6016a19234b07ac93d6760'
EXPECTED_ASSERTIONS = 64
CANONICAL_EXPR = '(submission_id IN ( SELECT submissions.id\n   FROM public.submissions\n  WHERE (submissions.contributor_id = public.current_contributor_id())))'
ALIAS_EXPR = '(submission_id IN ( SELECT s.id\n   FROM public.submissions s\n  WHERE (s.contributor_id = public.current_contributor_id())))'
SELECT_ALIAS_NAMES = {'photos_select_own','gold_labels_select_own','predictions_select_own','priors_select_own','qa_events_select_own'}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def rows(value: list[dict]) -> set[str]:
    serialized = [json.dumps(v,sort_keys=True) for v in value]
    assert len(serialized) == len(set(serialized)), 'duplicate catalog metadata record'
    return set(serialized)


def exact_catalog(left: dict, right: dict) -> bool:
    return set(left) == set(right) and all(rows(left[k]) == rows(right[k]) for k in left)


def normalize_target(value: dict) -> dict:
    result = json.loads(json.dumps(value))
    normalized = set()
    for policy in result['policies']:
        if policy['name'] in SELECT_ALIAS_NAMES:
            assert policy['using'] == ALIAS_EXPR, 'target alias difference exceeded reviewed expression'
            policy['using'] = CANONICAL_EXPR
            normalized.add(policy['name'])
    assert normalized == SELECT_ALIAS_NAMES, 'target ownership policy missing'
    return result


def rls_sql(label: str) -> str:
    # Each owner has two photos and one row in every other tested child table.
    return f"""do $test$
    declare
      uid uuid; own_submission uuid; foreign_submission uuid;
      object text; visible integer; expected integer; checks integer := 0;
    begin
      for owner in 1..2 loop
        uid := ('ee000000-0000-4000-8000-00000000000' || owner)::uuid;
        own_submission := ('bb000000-0000-4000-8000-00000000000' || owner)::uuid;
        foreign_submission := ('bb000000-0000-4000-8000-00000000000' || (3-owner))::uuid;
        execute 'set local role authenticated';
        perform set_config('request.jwt.claim.sub',uid::text,true);
        foreach object in array array['photos','priors','gold_labels','predictions','qa_events'] loop
          execute format('select count(*) from public.%I',object) into visible;
          expected := case when object='photos' then 2 else 1 end;
          if visible <> expected then raise exception 'synthetic own-row visibility failed for %',object; end if;
          checks := checks+1;
        end loop;
        -- The artificial exception rolls back the successful own insert and its QA job.
        begin
          insert into public.photos(submission_id,shot_type,storage_path)
          values(own_submission,'C','synthetic-local-proof-own-insert');
          checks := checks+1;
          raise exception 'rollback synthetic own insert' using errcode='P9999';
        exception when sqlstate 'P9999' then null;
        end;
        begin
          insert into public.photos(submission_id,shot_type,storage_path)
          values(foreign_submission,'C','synthetic-local-proof-foreign-insert');
          raise exception 'foreign photo insert unexpectedly succeeded';
        exception when insufficient_privilege then checks := checks+1;
        end;
        execute 'reset role';
      end loop;
      execute 'set local role authenticated';
      perform set_config('request.jwt.claim.sub','ee000000-0000-4000-8000-000000000009',true);
      select count(*) into visible from public.photos;
      if visible <> 0 then raise exception 'unlinked synthetic actor sees private rows'; end if;
      checks := checks+1;
      begin
        update public.photos set camera_metadata_private='{{}}'::jsonb;
        raise exception 'client metadata write unexpectedly succeeded';
      exception when insufficient_privilege then checks := checks+1;
      end;
      foreach object in array array['prior_jobs','qa_jobs'] loop
        begin
          execute format('select count(*) from public.%I',object) into visible;
          raise exception 'client queue read unexpectedly succeeded';
        exception when insufficient_privilege then checks := checks+1;
        end;
      end loop;
      execute 'reset role';
      execute 'set local role anon';
      begin
        select count(*) into visible from public.photos;
        raise exception 'anonymous photo read unexpectedly succeeded';
      exception when insufficient_privilege then checks := checks+1;
      end;
      begin
        perform geom_precise from public.submissions;
        raise exception 'anonymous geometry read unexpectedly succeeded';
      exception when insufficient_privilege then checks := checks+1;
      end;
      execute 'reset role';
      if checks <> 20 then raise exception 'unexpected RLS assertion count %',checks; end if;
      raise notice 'RLS_PROOF {label} %',checks;
    end;
    $test$;
"""


def main() -> None:
    inputs = BASE / 'canonical-rehearsal-inputs'
    inputs.mkdir(exist_ok=True)
    snapshot = Path(tempfile.mkdtemp(prefix='gsip-ledger-rehearsal-',dir='/private/tmp'))
    mapping = json.loads((BASE/'canonical-migration-timestamp-map.json').read_text())
    files = [r['canonical_filename'] for r in mapping['baseline_migrations']]
    names = subprocess.check_output(['git','ls-tree','-r','--name-only',SOURCE,'supabase/migrations'],cwd=REPO,text=True).splitlines()
    assert len(names) == 26 and len(files)==17
    for relative in names+['supabase/migration-tests/stand_in.sql']:
        path=snapshot/relative;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(subprocess.check_output(['git','show',f'{SOURCE}:{relative}'],cwd=REPO))
    for row in mapping['baseline_migrations']:
        assert digest(snapshot/'supabase/migrations'/row['canonical_filename'])==row['canonical_sql_sha256']
    for name,sha in [('catalog-snapshot.sql','89028b8da3460182b59ca9a87b57c6fb1e9be32660dc5806995149d0f9a1db0f'),('catalog-snapshot-supplement.sql','92831e8adcefae9ecd0a1141b833bab1de031d63b385bc7a1c7143ee5d8cd2c9')]:
        assert digest(BASE/name)==sha;shutil.copy2(BASE/name,snapshot/name)
    seed="""create schema rehearsal_control;
create table rehearsal_control.sentinel(id integer primary key, value text not null);
insert into rehearsal_control.sentinel values(1,'synthetic unrelated state must survive');
insert into auth.users(id) values('ee000000-0000-4000-8000-000000000001'),('ee000000-0000-4000-8000-000000000002');
insert into public.contributors(id,auth_uid,handle) values
('dd000000-0000-4000-8000-000000000001','ee000000-0000-4000-8000-000000000001','synthetic-owner-one'),
('dd000000-0000-4000-8000-000000000002','ee000000-0000-4000-8000-000000000002','synthetic-owner-two');
insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,attribution_name) values
('ff000000-0000-4000-8000-000000000001','dd000000-0000-4000-8000-000000000001','2026-07-22-v1','2026-09-01','Anonymous soil contributor'),
('ff000000-0000-4000-8000-000000000002','dd000000-0000-4000-8000-000000000002','2026-07-22-v1','2026-09-01','Anonymous soil contributor');
insert into public.submissions(id,contributor_id,grant_id,geom_precise,captured_at,is_synthetic) values
('bb000000-0000-4000-8000-000000000001','dd000000-0000-4000-8000-000000000001','ff000000-0000-4000-8000-000000000001',extensions.st_geomfromtext('POINT EMPTY',4326),'2026-09-01',true),
('bb000000-0000-4000-8000-000000000002','dd000000-0000-4000-8000-000000000002','ff000000-0000-4000-8000-000000000002',extensions.st_geomfromtext('POINT EMPTY',4326),'2026-09-01',true);
insert into public.photos(submission_id,shot_type,storage_path)
select s.id,shot,'ee000000-0000-4000-8000-00000000000'||owner||'/'||s.id||'/'||shot||'/aa000000-0000-4000-8000-00000000000'||owner||'.jpg'
from (values (1,'bb000000-0000-4000-8000-000000000001'::uuid),(2,'bb000000-0000-4000-8000-000000000002'::uuid)) sample(owner,id)
join public.submissions s using(id) cross join (values('A'),('B')) shots(shot);
update public.qa_jobs set status='completed',completed_at=now();
insert into public.priors(submission_id,source,property,value,unit,depth_top_cm,depth_bottom_cm)
select id,'soilgrids','soc',1,'g/kg',0,5 from public.submissions;
insert into public.gold_labels(submission_id,lab_name,property,value,unit,depth_top_cm,depth_bottom_cm)
select id,'Synthetic local reference','soc',1,'g/kg',0,5 from public.submissions;
insert into public.predictions(submission_id,model_version,property,value,ci_lo,ci_hi,basis,unit)
select id,'synthetic-local-v1','soc',1,0,2,'prior','g/kg' from public.submissions;
insert into public.qa_events(submission_id,check_name,passed)
select id,'synthetic_local_check',true from public.submissions;
"""
    alias_sql=''
    deployed=json.loads((BASE/'production-catalog-before-reconciliation.json').read_text())
    allowed=SELECT_ALIAS_NAMES|{'photos_insert_own'}
    for p in deployed['policies']:
        if p['name'] not in allowed:continue
        field='check' if p['name']=='photos_insert_own' else 'using'
        assert p[field]==ALIAS_EXPR and p['roles']==['authenticated'] and p['permissive'] is True
        operation='insert' if p['command']=='a' else 'select'
        assert (operation=='insert')==(p['name']=='photos_insert_own')
        clause='with check' if operation=='insert' else 'using'
        alias_sql+=f"drop policy {p['name']} on public.{p['table']};\ncreate policy {p['name']} on public.{p['table']} for {operation} to authenticated {clause} ({p[field]});\n"
    baseline=json.loads((BASE/'canonical-catalog-baseline17.json').read_text())
    data_sql='select jsonb_build_object('+','.join(quote(table['table'])+f",(select encode(sha256(convert_to(coalesce(jsonb_agg(to_jsonb(x) order by to_jsonb(x)::text),'[]'::jsonb)::text,'UTF8')),'hex') from public.{table['table']} x)" for table in baseline['tables'])+",'unrelated_sentinel',(select encode(sha256(convert_to(jsonb_agg(to_jsonb(x) order by x.id)::text,'UTF8')),'hex') from rehearsal_control.sentinel x));\n"
    remote_rows=[(r['recorded_remote_version'],r['name']) for r in mapping['baseline_migrations']]+[('20260730174047','wavefunction_beta_schema')]
    ledger_seed='create schema supabase_migrations; create table supabase_migrations.schema_migrations(version text primary key,name text,statements text[]);\ninsert into supabase_migrations.schema_migrations(version,name) values '+','.join(f'({quote(v)},{quote(n)})' for v,n in remote_rows)+';\n'
    add='insert into supabase_migrations.schema_migrations(version,name) values '+','.join(f"({quote(r['canonical_local_version'])},{quote(r['name'])})" for r in mapping['timestamp_remappings'])+';\n'
    retire='delete from supabase_migrations.schema_migrations where version in ('+','.join(quote(r['recorded_remote_version']) for r in mapping['timestamp_remappings'])+');\n'
    stray="delete from supabase_migrations.schema_migrations where version='20260730174047';\n"
    ledger_sql="select jsonb_agg(jsonb_build_object('version',version,'name',name) order by version) from supabase_migrations.schema_migrations;\n"
    post="""do $test$
declare checks integer:=0;
begin
if (select count(*) from public.contributors)<>2 then raise exception 'contributors changed'; end if; checks:=checks+1;
if (select count(*) from public.contribution_grants)<>2 then raise exception 'grants changed'; end if; checks:=checks+1;
if (select count(*) from public.submissions where is_synthetic and provenance_tier=-1 and actor_id is not null)<>2 then raise exception 'synthetic submission provenance failed'; end if; checks:=checks+1;
if (select count(*) from public.photos where provenance_tier=-1 and qa_status='pass')<>4 then raise exception 'photo backfill failed'; end if; checks:=checks+1;
if (select count(*) from public.submissions where finalized_at is not null)<>2 then raise exception 'legacy finalization failed'; end if; checks:=checks+1;
if (select count(*) from public.actors where kind='human' and status='active' and operator_id is null)<>2 then raise exception 'actor backfill failed'; end if; checks:=checks+1;
if (select count(*) from public.service_state where not capture_open)<>1 then raise exception 'capture gate not closed'; end if; checks:=checks+1;
if (select count(*) from public.contribution_grants where received_at is null)<>2 then raise exception 'legacy receipts rewritten'; end if; checks:=checks+1;
if checks<>8 then raise exception 'post-migration assertion count mismatch'; end if;
raise notice 'POST_PROOF %',checks;
end;
$test$;
"""
    generated={'seed.sql':seed,'rls-canonical.sql':rls_sql('canonical'),'rls-alias.sql':rls_sql('alias'),'alias.sql':alias_sql,'fingerprint.sql':data_sql,'ledger-seed.sql':ledger_seed,'ledger-add.sql':add,'ledger-retire.sql':retire,'ledger-stray.sql':stray,'ledger-read.sql':ledger_sql,'post-upgrade.sql':post}
    for name,text in generated.items():
        (inputs/name).write_text(text);shutil.copy2(inputs/name,snapshot/name)
    shell="""set -euo pipefail
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
printf 'NEGATIVE_RLS_REJECTED\\n'
"${PSQL[@]}" -f /source/alias.sql >/dev/null
for item in CATALOG_BEFORE:catalog-snapshot.sql SUPPLEMENT_BEFORE:catalog-snapshot-supplement.sql DATA_BEFORE:fingerprint.sql; do printf '%s\\n' "${item%%:*}";"${PSQL[@]}" -f "/source/${item#*:}";done
"${PSQL[@]}" -f /source/ledger-seed.sql >/dev/null
printf 'LEDGER18\\n';"${PSQL[@]}" -f /source/ledger-read.sql
"${PSQL[@]}" -f /source/ledger-add.sql >/dev/null
printf 'LEDGER31\\n';"${PSQL[@]}" -f /source/ledger-read.sql
"${PSQL[@]}" -f /source/ledger-retire.sql >/dev/null
printf 'LEDGER18_AFTER_RETIRE\\n';"${PSQL[@]}" -f /source/ledger-read.sql
"${PSQL[@]}" -f /source/ledger-stray.sql >/dev/null
printf 'LEDGER17\\n';"${PSQL[@]}" -f /source/ledger-read.sql
for item in CATALOG_AFTER:catalog-snapshot.sql SUPPLEMENT_AFTER:catalog-snapshot-supplement.sql DATA_AFTER:fingerprint.sql; do printf '%s\\n' "${item%%:*}";"${PSQL[@]}" -f "/source/${item#*:}";done
count=0
for migration in /source/supabase/migrations/202610*.sql;do
 "${PSQL[@]}" -f "$migration" >/dev/null 2>"$work/step.err"
 stem="$(basename "$migration" .sql)";version="${stem%%_*}";name="${stem#*_}"
 "${PSQL[@]}" -c "insert into supabase_migrations.schema_migrations(version,name) values('$version','$name')" >/dev/null
 count=$((count+1))
done
printf 'PENDING_COUNT\\n%s\\n' "$count"
"${PSQL[@]}" -f /source/post-upgrade.sql >/dev/null
for item in TARGET:catalog-snapshot.sql TARGET_SUPPLEMENT:catalog-snapshot-supplement.sql LEDGER26:ledger-read.sql DATA_TARGET:fingerprint.sql;do printf '%s\\n' "${item%%:*}";"${PSQL[@]}" -f "/source/${item#*:}";done
"""
    (inputs/'container-rehearsal.sh').write_text(shell)
    result=subprocess.run(['docker','run','--rm','--network','none','--user','postgres','--entrypoint','/bin/bash','-v',str(snapshot)+':/source:ro',IMAGE,'-c',shell],capture_output=True,text=True)
    if result.returncode:
        print(json.dumps({'status':'FAILED','exit_code':result.returncode,'safe_error':result.stderr[-2400:]}));raise SystemExit(result.returncode)
    lines=result.stdout.splitlines()
    def value(label:str):return json.loads(lines[lines.index(label)+1])
    checks=[]
    def check(name:str,passed:bool,count:int=1):
        if not passed:raise AssertionError(name)
        checks.append({'name':name,'passed':True,'assertions':count})
    check('Canonical ownership behavior', 'RLS_PROOF canonical 20' in result.stderr,20)
    check('Exact deployed aliases preserve ownership behavior','RLS_PROOF alias 20' in result.stderr,20)
    check('Unsafe permissive policy rejected','NEGATIVE_RLS_REJECTED' in lines)
    expected_original=sorted([{'version':v,'name':n} for v,n in remote_rows],key=lambda r:r['version'])
    canonical=[{'version':r['canonical_local_version'],'name':r['name']} for r in mapping['baseline_migrations']]
    canonical=sorted(canonical,key=lambda r:r['version'])
    check('Initial eighteen historical ledger identities',value('LEDGER18')==expected_original)
    check('Adding thirteen produces exact thirty-one identity set',rows(value('LEDGER31'))==rows(expected_original)|rows(canonical))
    retained18=canonical+[{'version':'20260730174047','name':'wavefunction_beta_schema'}]
    check('Retiring thirteen leaves exact eighteen identities',rows(value('LEDGER18_AFTER_RETIRE'))==rows(retained18))
    check('Retiring stray leaves exact seventeen canonical identities',value('LEDGER17')==canonical)
    check('Public application catalog unchanged across ledger writes',exact_catalog(value('CATALOG_BEFORE'),value('CATALOG_AFTER')))
    check('Private functions/views/storage/schema ACLs unchanged across ledger writes',exact_catalog(value('SUPPLEMENT_BEFORE'),value('SUPPLEMENT_AFTER')))
    before,after=value('DATA_BEFORE'),value('DATA_AFTER')
    check('Synthetic application row digests unchanged across ledger writes',{k:v for k,v in before.items() if k!='unrelated_sentinel'}=={k:v for k,v in after.items() if k!='unrelated_sentinel'})
    check('Unrelated sentinel unchanged across ledger writes',before['unrelated_sentinel']==after['unrelated_sentinel'])
    check('Only nine pending migrations applied',value('PENDING_COUNT')==9)
    full=[{'version':Path(name).stem.split('_',1)[0],'name':Path(name).stem.split('_',1)[1]} for name in names]
    check('Final ledger is exact twenty-six reviewed identities',value('LEDGER26')==sorted(full,key=lambda r:r['version']))
    target=json.loads((BASE/'canonical-catalog-target26.json').read_text());supp=json.loads((BASE/'canonical-catalog-target26-supplement.json').read_text())
    check('Target catalog equals clean twenty-six chain apart from five exact surviving aliases',exact_catalog(target,normalize_target(value('TARGET'))))
    check('Target supplemental catalog equals clean twenty-six chain',exact_catalog(supp,value('TARGET_SUPPLEMENT')))
    check('Legacy backfill/synthetic provenance/closed capture checks','POST_PROOF 8' in result.stderr,8)
    check('Unrelated sentinel survives nine pending migrations',before['unrelated_sentinel']==value('DATA_TARGET')['unrelated_sentinel'])
    missing_first=[r for r in value('LEDGER17') if r['version']!='20260722164727']
    check('Removing an unchanged first identity rejected',missing_first!=canonical)
    premature=value('LEDGER17')+[r for r in full if r['version'].startswith('202610')][:1]
    check('Prematurely marking October applied rejected',premature!=canonical)
    total=sum(c['assertions'] for c in checks);assert total==EXPECTED_ASSERTIONS
    for label,name in [('CATALOG_BEFORE','rehearsal-catalog-before.json'),('TARGET','rehearsal-catalog-target26.json'),('TARGET_SUPPLEMENT','rehearsal-catalog-target26-supplement.json')]:
        (BASE/name).write_text(json.dumps(value(label),indent=2,sort_keys=True)+'\n')
    proof={'status':'PASS','assertions_passed':total,'expected_assertions':EXPECTED_ASSERTIONS,'failed':0,'checks':checks,'source_commit':SOURCE,'source_migration_sha256':{name:digest(snapshot/name) for name in names},'input_sha256':{str(p.relative_to(BASE)):digest(p) for p in sorted(inputs.iterdir()) if p.is_file()},'query_sha256':{name:digest(snapshot/name) for name in ('catalog-snapshot.sql','catalog-snapshot-supplement.sql')},'image_id':IMAGE,'image_digest':'public.ecr.aws/supabase/postgres@sha256:ca7871b587ca2c401ac0f325df6249c9aa0d25647ded34631158efc51176767f','postgres_version':'17.6','user':'postgres','network':'none','host_ports':[],'source_mount':'read-only','synthetic_geometry':'POINT EMPTY; no coordinate literals','ledger_sequence_counts':[18,31,18,17,26],'pending_migrations_applied':9,'target_aliases_preserved':sorted(SELECT_ALIAS_NAMES),'scope_limits':['SQL-modeled documented ledger insert/delete effects; no Supabase CLI repair command executed','Auth/Storage are repository stand-ins; no production data, credentials, or network used','Metadata history statements are NULL placeholders; no foreign application SQL imported or executed','Synthetic backfill proof cannot establish historical effects or provenance of live rows','No pgTAP assertions run here; mandatory db-migration-test.sh remains separately required'],'production_mutations_performed':[],'driver_sha256':digest(Path(__file__)),'reference_sha256':{name:digest(BASE/name) for name in ('canonical-catalog-target26.json','canonical-catalog-target26-supplement.json','production-catalog-before-reconciliation.json','canonical-migration-timestamp-map.json')},'output_sha256':{name:digest(BASE/name) for name in ('rehearsal-catalog-before.json','rehearsal-catalog-target26.json','rehearsal-catalog-target26-supplement.json')}}
    output=BASE/'canonical-ledger-reconciliation-rehearsal.json';output.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({'status':'PASS','assertions_passed':total,'expected_assertions':EXPECTED_ASSERTIONS,'ledger_sequence_counts':proof['ledger_sequence_counts'],'output':str(output),'sha256':digest(output),'driver_sha256':digest(Path(__file__))}))
    shutil.rmtree(snapshot)

if __name__=='__main__':
    main()
