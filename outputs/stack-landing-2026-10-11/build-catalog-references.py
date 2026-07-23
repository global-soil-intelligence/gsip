"""Export metadata-only GSIP reference stages in a disposable no-network PostgreSQL DB."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tempfile
BASE=Path(__file__).resolve().parent
REPO=BASE/'repo'
SOURCE='f9e1ac2f8a88671f99b959e476499392297bd30f'
IMAGE='sha256:521e67f2812db505fe6d462b1820136394824d7f5c6016a19234b07ac93d6760'
QUERIES={'catalog-snapshot.sql':'89028b8da3460182b59ca9a87b57c6fb1e9be32660dc5806995149d0f9a1db0f','catalog-snapshot-supplement.sql':'92831e8adcefae9ecd0a1141b833bab1de031d63b385bc7a1c7143ee5d8cd2c9'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=Path(tempfile.mkdtemp(prefix='gsip-catalog-v2-',dir='/private/tmp'))
files=subprocess.check_output(['git','ls-tree','-r','--name-only',SOURCE,'supabase/migrations'],cwd=REPO,text=True).splitlines()
assert len(files)==26
for name in files+['supabase/migration-tests/stand_in.sql']:
 p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',f'{SOURCE}:{name}'],cwd=REPO))
for name,sha in QUERIES.items():assert digest(BASE/name)==sha;shutil.copy2(BASE/name,source/name)
script='''set -euo pipefail
PG_BIN="$(pg_config --bindir)";work=/tmp/gsip-canonical-reference;mkdir -p "$work"
trap '"$PG_BIN/pg_ctl" -D "$work/data" -m immediate stop >/dev/null 2>&1 || true' EXIT
"$PG_BIN/initdb" -D "$work/data" -A trust -U postgres >/dev/null
"$PG_BIN/pg_ctl" -D "$work/data" -l "$work/server.log" -w -o "-k $work -p 55498 -c listen_addresses=" start >/dev/null
PSQL=("$PG_BIN/psql" -X -q -t -A -v ON_ERROR_STOP=1 -h "$work" -p 55498 -U postgres -d postgres)
"${PSQL[@]}" -f /source/supabase/migration-tests/stand_in.sql >/dev/null
count=0
for migration in /source/supabase/migrations/*.sql;do
 "${PSQL[@]}" -f "$migration" >/dev/null 2>"$work/step.err"
 count=$((count+1))
 if [ "$count" = 17 ] || [ "$count" = 26 ];then
  printf 'PRIMARY%s\\n' "$count";"${PSQL[@]}" -f /source/catalog-snapshot.sql
  printf 'SUPPLEMENT%s\\n' "$count";"${PSQL[@]}" -f /source/catalog-snapshot-supplement.sql
 fi
done
[ "$count" = 26 ]
printf 'VERSION\\n';"${PSQL[@]}" -c "select current_setting('server_version')"
'''
result=subprocess.run(['docker','run','--rm','--network','none','--user','postgres','--entrypoint','/bin/bash','-v',str(source)+':/source:ro',IMAGE,'-c',script],capture_output=True,text=True)
if result.returncode:print(json.dumps({'status':'FAILED','safe_error':result.stderr[-1500:]}));raise SystemExit(result.returncode)
lines=result.stdout.splitlines();exports={}
for label,name in [('PRIMARY17','canonical-catalog-baseline17.json'),('SUPPLEMENT17','canonical-catalog-baseline17-supplement.json'),('PRIMARY26','canonical-catalog-target26.json'),('SUPPLEMENT26','canonical-catalog-target26-supplement.json')]:
 catalog=json.loads(lines[lines.index(label)+1]);p=BASE/name;p.write_text(json.dumps(catalog,indent=2,sort_keys=True)+'\n');exports[name]={'sha256':digest(p),'counts':{k:len(v) for k,v in catalog.items()}}
receipt={'status':'PASS','extractor_version':2,'source_commit':SOURCE,'source_path':str(REPO),'sha256':{name:digest(source/name) for name in files+['supabase/migration-tests/stand_in.sql']},'image_id':IMAGE,'image_digest':'public.ecr.aws/supabase/postgres@sha256:ca7871b587ca2c401ac0f325df6249c9aa0d25647ded34631158efc51176767f','image_architecture':'arm64','postgres_version':lines[lines.index('VERSION')+1],'query_sha256':QUERIES,'network':'none','user':'postgres','source_mount':'read-only','host_ports':[],'seed_fixtures_loaded':False,'migration_counts':{'baseline':17,'target':26},'catalog_exports':exports,'generator_sha256':digest(Path(__file__)),'scope_limits':['Auth/Storage/default ACL bootstrap is a repository stand-in','No contributor rows, production credentials, network or production operations','Function bodies SHA-only; table/function owners and function ACL delegation included','Zero pgTAP assertions run in metadata-only reference export'],'production_operations':[]}
p=BASE/'canonical-catalog-source-receipt.json';p.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'status':'PASS','catalog_exports':exports,'receipt_sha256':digest(p)}));shutil.rmtree(source)
