import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

source = Path('/Users/justinhart/.codex/worktrees/gsip-spec-followups/GSIP 2.0')
out = Path(__file__).resolve().parent
safe = {key:value for key,value in os.environ.items() if not key.startswith(('VITE_', 'SUPABASE_'))}
safe['PATH'] = '/Users/justinhart/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:' + safe['PATH']
names = ['SUPABASE_URL', 'VITE_SUPABASE_PUBLISHABLE_KEY', 'VITE_PRIOR_TILES_BASE', 'VITE_DATASET_URL', 'VITE_GSIP_PUBLIC_API', 'VITE_TERMS_URL', 'VITE_PRIVACY_URL', 'VITE_SAMPLING_RULES_URL']
configured = {}
for name in names:
    result = subprocess.run(['gh','api',f'repos/global-soil-intelligence/gsip/actions/variables/{name}','--jq','.value'], capture_output=True, text=True)
    if result.returncode and '404' not in result.stderr:
        raise SystemExit('Repository variable lookup failed: ' + name)
    value = result.stdout.strip() if result.returncode == 0 else ''
    safe['VITE_SUPABASE_URL' if name == 'SUPABASE_URL' else name] = value
    configured[name] = bool(value)
safe['VITE_CAPTURE_LIVE'] = 'false'
safe['VITE_LIBRARY_INTAKE_LIVE'] = 'false'
commands = [['pnpm','build:pages'], ['pnpm','check:map-budget'], ['pnpm','check:prior-tiles'], ['pnpm','check:site-budget']]
with (out/'pages-build.log').open('w') as log:
    for command in commands:
        log.write('COMMAND: ' + ' '.join(command) + '\n');log.flush()
        result = subprocess.run(command, cwd=source, env=safe, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise SystemExit('Build/check failed: ' + ' '.join(command))
activation = json.loads((source/'_site/capture/gsip-activation.json').read_text())
if activation != {'capture_live':False, 'library_intake_live':False}:
    raise SystemExit('Activation mismatch; artifact refused')
preview = out/'pages-preview'
if preview.exists():shutil.rmtree(preview)
shutil.copytree(source/'_site', preview)
files = [{'path':str(p.relative_to(preview)), 'bytes':p.stat().st_size, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(preview.rglob('*')) if p.is_file()]
receipt = {'status':'PREPARED_NOT_DEPLOYED', 'source_branch':'wp-site-1f-spectral-library', 'base_commit':'ccbe716caf8406dda7ffd58ecb9cab62ea0702bf', 'activation':activation, 'repository_variables_configured':configured, 'commands':commands, 'file_count':len(files), 'total_bytes':sum(item['bytes'] for item in files), 'files':files}
(out/'pages-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({key:receipt[key] for key in ['status','activation','file_count','total_bytes']}))
