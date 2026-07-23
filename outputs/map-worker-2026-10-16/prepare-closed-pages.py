from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import base64
import gzip
import json
import os
import shutil
import subprocess
import tarfile

OUT = Path(__file__).resolve().parent
ROOT = Path('/Users/justinhart/.codex/worktrees/gsip-spec-followups/GSIP 2.0')
EXPECTED = 'd53eda2e835e57b4ee01dc922fb63d5ebdeceae0'
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert head == EXPECTED
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()
variables = json.loads(subprocess.check_output(['gh', 'api', 'repos/global-soil-intelligence/gsip/actions/variables?per_page=100'], text=True))
values = {item['name']: item['value'] for item in variables['variables']}
assert values['SUPABASE_URL'] == 'https://toxldjgwkxtneoqsazym.supabase.co'
assert values['VITE_GSIP_PUBLIC_API'] == values['SUPABASE_URL'] + '/functions/v1/gsip-public'
key = values['VITE_SUPABASE_PUBLISHABLE_KEY']
if not key.startswith('sb_publishable_'):
    parts = key.split('.')
    assert len(parts) == 3, 'Expected existing public key format'
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=' * (-len(parts[1]) % 4)))
    assert payload.get('role') == 'anon', 'Only the existing public anonymous key is permitted'
env = {name: value for name, value in os.environ.items() if not name.startswith(('VITE_', 'SUPABASE_'))}
env['PATH'] = '/Users/justinhart/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'
names = ['VITE_SUPABASE_PUBLISHABLE_KEY', 'VITE_GSIP_PUBLIC_API', 'VITE_PRIOR_TILES_BASE', 'VITE_DATASET_URL', 'VITE_TERMS_URL', 'VITE_PRIVACY_URL', 'VITE_SAMPLING_RULES_URL']
for name in names:
    env[name] = values.get(name, '')
env.update(VITE_SUPABASE_URL=values['SUPABASE_URL'], VITE_CAPTURE_LIVE='false', VITE_LIBRARY_INTAKE_LIVE='false')
commands = [['pnpm', 'build:pages'], ['pnpm', 'check:map-budget'], ['pnpm', 'check:site-budget'], ['pnpm', 'check:prior-tiles']]
with (OUT / 'closed-pages-build.log').open('w') as log:
    for command in commands:
        log.write('COMMAND ' + ' '.join(command) + '\n')
        log.flush()
        subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
site = ROOT / '_site'
activation = json.loads((site / 'capture/gsip-activation.json').read_text())
assert set(activation) == {'capture_live', 'library_intake_live'} and all(value is False for value in activation.values())
worker_files = list((site / 'map/assets').glob('maplibre-gl-worker-*.js'))
assert len(worker_files) == 1
notice = site / 'map/THIRD_PARTY_LICENSES.md'
assert (ROOT / 'apps/map-web/node_modules/maplibre-gl/LICENSE.txt').read_text().strip() in notice.read_text()
preview = OUT / 'pages-preview'
assert not preview.exists(), 'Preserve any existing prepared artifact'
shutil.copytree(site, preview)
files = []
for path in sorted(preview.rglob('*')):
    assert not path.is_symlink()
    if path.is_file():
        raw = path.read_bytes()
        files.append({'path': path.relative_to(preview).as_posix(), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()})
archive = OUT / 'gsip-site-1g-closed-pages.tar.gz'
with archive.open('wb') as output:
    with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as tar:
            for item in files:
                path = preview / item['path']
                info = tar.gettarinfo(str(path), arcname=item['path'])
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ''
                info.mode = 0o644
                with path.open('rb') as source:
                    tar.addfile(info, source)
receipt = {'status': 'PREPARED_NOT_DEPLOYED_OWNER_MERGE_AND_PAGES_GO_PENDING', 'prepared_at_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': head, 'source_branch': 'wp-site-1g-map-worker', 'repository': 'global-soil-intelligence/gsip', 'activation': activation, 'archive': archive.name, 'archive_bytes': archive.stat().st_size, 'archive_sha256': sha256(archive.read_bytes()).hexdigest(), 'files_count': len(files), 'files_bytes': sum(item['bytes'] for item in files), 'map_bytes': sum(item['bytes'] for item in files if item['path'].startswith('map/')), 'map_budget_bytes': 5 * 1024 * 1024, 'worker': worker_files[0].name, 'commands_passed': commands, 'configuration': 'Matches Pages workflow variable mapping; existing public key validated without printing or storing it separately; upload flags forced false', 'variable_hashes': {name: sha256(env[name].encode()).hexdigest() for name in names + ['VITE_SUPABASE_URL']}, 'files': files, 'limitations': ['Local prepared artifact is not a GitHub Pages workflow run or a production deployment', 'Pages permits only main/gh-pages; owner merge go precedes a valid protected run', 'After merge, inspect and bind the actual main run/source/artifact before requesting deployment go']}
(OUT / 'closed-pages-artifact-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({key: receipt[key] for key in ['status', 'source_commit', 'activation', 'files_count', 'files_bytes', 'map_bytes', 'archive_bytes', 'archive_sha256', 'worker']}, indent=2))
