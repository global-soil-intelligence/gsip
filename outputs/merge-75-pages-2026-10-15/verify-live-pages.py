from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
import json
import time

out = Path(__file__).resolve().parent
expected = json.loads((out/'artifact-verification.json').read_text())
base = 'https://global-soil-intelligence.github.io/gsip/'
headers = {'User-Agent':'GSIP-owner-authorized-release-verification/1.0', 'Cache-Control':'no-cache', 'Accept-Encoding':'identity'}

def fetch(item):
    path = item['path']
    request = Request(base + quote(path, safe='/'), headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            data = response.read(10 * 1024 * 1024)
            actual = sha256(data).hexdigest()
            result = {'path':path,'status':response.status,'url':response.url,'bytes':len(data),'content_type':response.headers.get('Content-Type'),'sha256':actual,'matches_approved_artifact':actual == item['sha256'] and len(data) == item['bytes']}
        if path=='capture/gsip-activation.json':
            activation = json.loads(data)
            assert set(activation)=={'capture_live','library_intake_live'}
            assert all(type(v) is bool and v is False for v in activation.values())
            result['activation'] = activation
        return result
    except Exception as error:
        return {'path':path,'error_type':type(error).__name__,'matches_approved_artifact':False}

attempts = []
for attempt in range(1,4):
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(fetch, expected['files']))
    failures = [r for r in results if not r['matches_approved_artifact'] or r.get('status')!=200]
    attempts.append({'attempt':attempt,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'matched':len(results)-len(failures),'failed_paths':[r['path'] for r in failures]})
    if not failures:
        break
    if attempt<3:
        time.sleep(10)
receipt = {'status':'LIVE_MATCHES_APPROVED_CLOSED_ARTIFACT' if not failures else 'LIVE_VERIFICATION_MISMATCH','checked_at_utc':datetime.now(timezone.utc).isoformat(),'base_url':base,'run_id':38821460183,'source_commit':expected['source_commit'],'artifact_id':expected['artifact_id'],'artifact_sha256':expected['zip_sha256'],'files_verified':len(results)-len(failures),'files_expected':len(expected['files']),'activation':next((r.get('activation') for r in results if r['path']=='capture/gsip-activation.json'),None),'attempts':attempts,'files':results,'data_submission':'NONE','auth_or_production_service_mutation':'NONE'}
(out/'live-http-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ['status','base_url','run_id','files_verified','files_expected','activation','attempts']}))
raise SystemExit(1 if failures else 0)
