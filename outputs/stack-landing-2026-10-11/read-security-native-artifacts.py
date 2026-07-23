"""Read-only exact-head native workflow/artifact metadata; no downloads or mutation."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess
parser=argparse.ArgumentParser();parser.add_argument('snapshot');args=parser.parse_args()
BASE=Path(__file__).resolve().parent;snapshot=BASE/args.snapshot;data=json.loads(snapshot.read_text());records=[]
for number in [34,35,39]:
 p=next(p for p in data['prs'] if p['number']==number)
 jobs=[c for c in p['effective_checks'] if c.get('name') in ['android','ios']]
 assert len(jobs)==2 and all(c['status']=='COMPLETED' and c['conclusion']=='SUCCESS' for c in jobs)
 run_ids={int(re.search(r'/actions/runs/(\d+)/',c['detailsUrl']).group(1)) for c in jobs};assert len(run_ids)==1
 run_id=run_ids.pop()
 def api(url):return json.loads(subprocess.check_output(['/opt/homebrew/bin/gh','api',url],text=True))
 run=api(f'repos/global-soil-intelligence/gsip/actions/runs/{run_id}')
 assert run['head_sha']==p['head'] and run['status']=='completed' and run['conclusion']=='success'
 artifacts=api(f'repos/global-soil-intelligence/gsip/actions/runs/{run_id}/artifacts?per_page=30')
 assert artifacts['total_count']==len(artifacts['artifacts'])==2
 assert {a['name'] for a in artifacts['artifacts']}=={'gsip-capture-android-debug','gsip-capture-ios-simulator'}
 assert all(not a['expired'] and a['size_in_bytes']>0 for a in artifacts['artifacts'])
 records.append({'pr':number,'head':p['head'],'run':{k:run[k] for k in ['id','name','event','head_sha','head_branch','status','conclusion','html_url','created_at','updated_at','run_attempt']},'artifact_coverage':{'total_count':artifacts['total_count'],'returned_count':len(artifacts['artifacts']),'complete':True},'artifacts':[{k:a.get(k) for k in ['id','name','size_in_bytes','expired','created_at','updated_at','expires_at','digest']} for a in artifacts['artifacts']]})
p=BASE/'security-fix-native-artifacts-readback-2026-10-12.json';assert not p.exists()
p.write_text(json.dumps({'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','snapshot':snapshot.name,'snapshot_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'records':records,'mutations_performed':False,'limits':['Artifact metadata and successful strict upload jobs establish CI archives; this readback does not download or independently rebuild the binaries.']},indent=2)+'\n')
print(json.dumps({'receipt':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'runs':[{ 'pr':v['pr'],'run':v['run']['html_url'],'artifact_ids':[a['id'] for a in v['artifacts']]} for v in records]},indent=2))
