import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path('/Users/justinhart/.codex/worktrees/gsip-sync-lock/GSIP 2.0')
OUTPUT = Path('/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/ios-storage-prototype-2026-10-14')
head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip()
assert head == sys.argv[1]
assert not subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain', '--untracked-files=no'])
short = head[:7]
run = Path(tempfile.mkdtemp(prefix='gsip-app2c2a-final-' + short + '-', dir='/private/tmp'))
source = run / 'ordinary-source'
env = os.environ.copy()
env['PATH'] = '/Users/justinhart/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:' + env['PATH']
env['DEVELOPER_DIR'] = '/Applications/Xcode.app/Contents/Developer'
env['VITE_CAPTURE_LIVE'] = 'false'
env['VITE_LIBRARY_INTAKE_LIVE'] = 'false'
record = {'root': str(run), 'commit': head, 'status': 'running'}

def save():
    (OUTPUT / ('local-final-run-' + short + '.json')).write_text(json.dumps(record, indent=2) + '\n')

def call(args, cwd, name):
    record['current_step'] = name
    save()
    with (run / name).open('wb') as log:
        subprocess.run(args, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=3600)

save()
try:
    call(['git', 'clone', '--no-hardlinks', '--no-checkout', str(ROOT), str(source)], run, 'clone.log')
    call(['git', 'checkout', '--detach', head], source, 'checkout.log')
    assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD']).decode().strip() == head
    call(['pnpm', 'install', '--frozen-lockfile', '--package-import-method', 'copy'], source, 'install.log')
    call(['pnpm', '--filter', '@gsip/capture-pwa', 'build:app'], source, 'app-build.log')
    call(['pnpm', 'exec', 'cap', 'add', 'ios'], source / 'apps/capture-pwa', 'ordinary-generate.log')
    call([str(ROOT / '.venv/bin/python'), '-m', 'scripts.ios_storage_prototype', 'run', str(ROOT),
          str(source / 'apps/capture-pwa/ios'), str(run / 'prototype')], ROOT, 'prototype.log')
    assert subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip() == head
    public = run / 'prototype/public-receipt.json'
    record.update(status='passed', public_receipt=str(public))
    (OUTPUT / ('local-public-receipt-' + short + '.json')).write_bytes(public.read_bytes())
    print('Exact-head local native and ordinary-artifact verification passed.')
except subprocess.CalledProcessError as exc:
    record.update(status='failed', exit_code=exc.returncode)
    print('Exact-head local verification failed; private evidence retained.')
    raise
finally:
    save()
