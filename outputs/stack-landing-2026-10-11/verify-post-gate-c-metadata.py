"""Read-only post-C metadata/aggregate receipt; does not connect to production."""
import datetime, hashlib, json, pathlib, re, stat, subprocess

B = pathlib.Path(__file__).resolve().parent
OP = B / 'repo'
OPS = pathlib.Path('/Users/justinhart/.codex/worktrees/gsip-spec-followups/GSIP 2.0')
HEAD = 'f9e1ac2f8a88671f99b959e476499392297bd30f'
OPS_HEAD = 'cf063aa5865a86eb86250e3a1f8287545e51f037'

def read(name):
    return json.loads((B / name).read_text())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git(repo, *args):
    p = subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError('Local Git metadata read failed; stderr suppressed')
    return p.stdout.strip()

pre = read('production-pre-gate-c-preflight-2026-10-12.json')
post = read('production-post-c-metadata-2026-10-12.json')
root = read('gate-c-root-ledger-capture-readback-2026-10-12.json')
backfill = read('production-post-gate-c-backfill-verification-2026-10-12.json')
prior = read('production-post-c-prior-k-checks-2026-10-12.json')
advisor = read('production-post-c-security-advisor-2026-10-12.json')
checks = {}
old = {c['table_name']: c['row_count'] for c in pre['counts']}
new = {c['table_name']: c['row_count'] for c in post['counts']}
expected = dict(old)
expected['supabase_migrations.schema_migrations'] = 26
expected.update({
    'public.actors': backfill['aggregate_counts']['contributor_count'],
    'public.attribution_reviews': 0,
    'public.dataset_releases': 0,
    'public.deletion_requests': 0,
    'public.grant_withdrawals': 0,
    'public.prior_cell_cache': 0,
    'public.service_state': 1,
    'public.terms_versions': backfill['aggregate_counts']['terms_expected_count'],
    'public.upstream_buckets': 3,
})
checks['all_61_table_names_and_counts_exact'] = new == expected and len(new) == 61
checks['table_inventory_exact'] = len(post['table_inventory']) == 61 and {t['table_name'] for t in post['table_inventory']} == set(expected)
checks['accepted_realtime_baseline_89'] = new.get('realtime.schema_migrations') == 89
checks['only_original_count_change_is_gsip_ledger_17_to_26'] = [n for n in old if old[n] != new.get(n)] == ['supabase_migrations.schema_migrations']
checks['known_17_whole_row_hashes_preserved'] = all(r in root['ledger'] for r in pre['ledger']) and len(pre['ledger']) == 17
files = git(OP, 'ls-tree', '--name-only', HEAD, 'supabase/migrations/').splitlines()
if len(files) == 1 and files[0] == 'supabase/migrations/':
    files = git(OP, 'ls-tree', '-r', '--name-only', HEAD, 'supabase/migrations/').splitlines()
identities = []
for f in files:
    m = re.fullmatch(r'supabase/migrations/(\d{14})_(.+)\.sql', f)
    if m:
        identities.append({'version': m.group(1), 'name': m.group(2)})
actual = [{'version': r['version'], 'name': r['name']} for r in root['ledger']]
checks['ledger_exact_26_canonical_identities'] = len(identities) == 26 and sorted(actual, key=lambda r:r['version']) == sorted(identities, key=lambda r:r['version'])
checks['ledger_full_row_hashes_valid'] = len(root['ledger']) == 26 and all(re.fullmatch('[0-9a-f]{64}', r['history_row_sha256']) for r in root['ledger'])
checks['capture_singleton_false'] = root['capture'] == {'row_count':1,'capture_true_count':0,'capture_false_count':1} and root['capture_is_open'] is False
checks['independent_backfill_pass'] = backfill['status'] == 'PASS_READONLY_GATE_C_BACKFILL_AGGREGATES' and all(backfill['checks'].values())
checks['public_cell_and_prior_initialization_pass'] = prior['public_cells'] == 0 and prior['prior_cache_rows'] == 0 and prior['upstream_bucket_rows'] == 3 and all(prior[k] == 0 for k in ['k_anonymity_violations','upstream_bucket_config_mismatch','prior_jobs_nonempty_new_empty_sources'])
checks['prior_attach_only_unchanged_version_and_jwt'] = len(post['edge_inventory']) == 1 and post['edge_inventory'][0]['name'] == 'prior-attach' and post['edge_inventory'][0]['version'] == 3 and post['edge_inventory'][0]['verify_jwt'] is True and post['edge_inventory'][0]['status'] == 'ACTIVE'
checks['security_advisor_zero_findings'] = len(advisor) == 0

command = ['python3','-m','scripts.reconciliation','--reference-catalog',str(B/'canonical-catalog-target26.json'),'--observed-catalog',str(B/'production-post-c-catalog-2026-10-12.json'),'--reference-supplement',str(B/'canonical-catalog-target26-supplement.json'),'--observed-supplement',str(B/'production-post-c-supplement-2026-10-12.json')]
p = subprocess.run(command,cwd=OPS,capture_output=True,text=True)
try:
    comparison = json.loads(p.stdout)
except (ValueError, TypeError):
    raise RuntimeError('Strict catalog helper did not return JSON; output suppressed')
expected_aliases = {'gold_labels_select_own','photos_select_own','predictions_select_own','priors_select_own','qa_events_select_own'}
actual_aliases = {r['identifier'] for r in comparison.get('allowed_differences',[]) if r['kind'] == 'exact_submission_alias'}
checks['target_26_strict_catalog_exact_except_bound_allowances'] = p.returncode == 0 and comparison.get('ok') is True and comparison.get('unexpected_differences') == []
checks['exactly_5_surviving_select_policy_aliases'] = actual_aliases == expected_aliases
local = {}
for label,repo,expected_head in [('operational',OP,HEAD),('ops',OPS,OPS_HEAD)]:
    head = git(repo,'rev-parse','HEAD')
    clean = git(repo,'status','--porcelain') == ''
    local[label] = {'path':str(repo),'head':head,'clean':clean}
    checks[label+'_source_head_and_clean'] = head == expected_head and clean
private = pathlib.Path('/Users/justinhart/.supabase/gsip-recovery/2026-10-11')
backup = {'path':str(private),'directory_mode':oct(stat.S_IMODE(private.stat().st_mode)),'files':[]}
expected_backups = {'original-history-schema.sql':'ae56295c7e66a8b46ab50df6f00cf57f7866f2478a17fbe3910d9def39e836ab','original-history.sql':'612b05231c79eac1e52cc4bf5da49ec2e9d4755358b461c902af69f6f089c857'}
for name,sha in expected_backups.items():
    path = private/name
    backup['files'].append({'name':name,'sha256':digest(path),'mode':oct(stat.S_IMODE(path.stat().st_mode)),'size_bytes':path.stat().st_size,'matches':digest(path)==sha})
checks['private_backup_unchanged_with_restrictive_modes'] = backup['directory_mode']=='0o700' and all(r['matches'] and r['mode']=='0o600' for r in backup['files'])
local['private_backup'] = backup
refs = [
'production-pre-gate-c-preflight-2026-10-12.json','gate-c-01-db-push-command-2026-10-12.json','gate-c-root-ledger-capture-readback-2026-10-12.json','production-post-gate-c-backfill-verification-2026-10-12.json','production-post-c-metadata-2026-10-12.json','production-post-c-security-advisor-2026-10-12.json','production-post-c-prior-k-checks-2026-10-12.json','production-post-c-table-counts-2026-10-12.sql','production-post-c-prior-k-aggregates-2026-10-12.sql','catalog-snapshot.sql','catalog-snapshot-supplement.sql','canonical-catalog-target26.json','canonical-catalog-target26-supplement.json']
receipt = {
 'state':'PASS' if all(checks.values()) else 'STOP',
 'target':'toxldjgwkxtneoqsazym',
 'completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'production_mutations_by_this_agent':0,
 'checks':checks,
 'failed_checks':[k for k,v in checks.items() if not v],
 'original_52_count_changes':[{'table_name':n,'before':old[n],'after':new.get(n)} for n in old if old[n]!=new.get(n)],
 'new_table_counts':[c for c in post['counts'] if c['table_name'] not in old],
 'catalog_helper':{'command':command,'exit_code':p.returncode,'source_sha256':digest(OPS/'scripts/reconciliation.py'),'result':comparison},
 'security_advisor':advisor,
 'security_advisor_categories':len(advisor),
 'security_advisor_object_findings':sum(l['count'] for l in advisor),
 'local_checks':local,
 'bound_receipts':[{'path':str(B/n),'sha256':digest(B/n)} for n in refs],
 'source_driver_sha256':digest(pathlib.Path(__file__)),
 'scope_limits':['Metadata and aggregate readbacks only; no contributor row contents or coordinates were read.','Ledger and capture readbacks independently executed by root; backfill readbacks independently executed by coding_guidance; their files are hash-bound.','No security finding is waived or hidden. Exact target catalog equality is not a zero-advisor-findings result.','The prior separately authorized signup-off verification is not re-performed here. Table counts do not prove auth settings.','No claims about concurrent or future operators beyond the pre-C point-in-time aggregate probe.','No function deployment, worker dispatch, tile publication, Pages deployment, capture opening or anonymous sign-in enabling was performed.']
}
raw = (json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode()
path = B/'production-post-gate-c-verification-2026-10-12.json'
path.write_bytes(raw)
print(json.dumps({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'state':receipt['state'],'failed_checks':receipt['failed_checks'],'passed_checks':sum(checks.values()),'total_checks':len(checks)}))
