"""Read-only exact-head GitHub CI inventory; no PR, branch or workflow mutation."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess
parser=argparse.ArgumentParser();parser.add_argument('--final',action='store_true');args=parser.parse_args()
BASE=Path(__file__).resolve().parent
MANAGED=Path('/Users/justinhart/.codex/worktrees/gsip-coding-guidance/GSIP 2.0')
prior=json.loads((BASE/'gate-c-all-pr-readback-2026-10-12.json').read_text())
push_path=BASE/'security-boundary-all-13-push-receipt-2026-10-12.json'
push=json.loads(push_path.read_text());assert push['remote_readback_exact']
expected={p['number']:{'branch':p['branch'],'base':p['base'],'head':push['pushed_heads'][p['branch']]} for p in prior['prs']}
context="""contexts(first:30){totalCount pageInfo{hasNextPage endCursor} nodes{__typename ... on CheckRun{name status conclusion startedAt completedAt detailsUrl databaseId} ... on StatusContext{context state targetUrl createdAt}}}"""
fragment="""number url title state headRefName headRefOid baseRefName mergedAt isDraft commits(last:1){totalCount pageInfo{hasPreviousPage} nodes{commit{oid statusCheckRollup{state CONTEXTS}}}}""".replace('CONTEXTS',context)
query='query{repository(owner:"global-soil-intelligence",name:"gsip"){'+' '.join('p'+str(n)+':pullRequest(number:'+str(n)+'){'+fragment+'}' for n in expected)+'}}'
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
run=subprocess.run(['/opt/homebrew/bin/gh','api','graphql','-f','query='+query],capture_output=True,text=True)
if run.returncode:
 print(json.dumps({'status':'READBACK_UNAVAILABLE','exit_code':run.returncode,'stderr_tail':run.stderr[-500:]}));raise SystemExit(run.returncode)
raw=json.loads(run.stdout)
assert not raw.get('errors'),raw.get('errors')
prs=[]
for n in expected:
 p=raw['data']['repository']['p'+str(n)]
 assert p and p['number']==n
 nodes=p['commits']['nodes'];assert len(nodes)==1
 commit=nodes[0]['commit'];rollup=commit['statusCheckRollup'];connection=rollup['contexts'] if rollup else None
 checks=connection['nodes'] if connection else []
 complete=not(connection and connection['pageInfo']['hasNextPage']) and (not connection or connection['totalCount']==len(checks))
 effective={}
 for c in checks:
  name=c.get('name',c.get('context'))
  stamp=c.get('startedAt') or c.get('completedAt') or c.get('createdAt') or ''
  old=effective.get(name)
  if old is None or (c.get('databaseId',0),stamp)>(old.get('databaseId',0),(old.get('startedAt') or old.get('completedAt') or old.get('createdAt') or '')):effective[name]=c
 required=sorted(set(['validate','gitleaks']+(['android','ios'] if n in [34,39] else [])+[name for name in effective if name!='dco']))
 green=lambda c:c.get('status')=='COMPLETED' and c.get('conclusion')=='SUCCESS' if c.get('__typename')=='CheckRun' else c.get('state')=='SUCCESS'
 wrong=[k for k in ['head','branch','base'] if expected[n][k]!={'head':p['headRefOid'],'branch':p['headRefName'],'base':p['baseRefName']}[k]]
 terminal_bad=[c for c in checks if c.get('conclusion') in ['FAILURE','CANCELLED','TIMED_OUT','ACTION_REQUIRED','STALE','STARTUP_FAILURE'] or c.get('state') in ['ERROR','FAILURE']]
 latest_bad=[name for name,c in effective.items() if c in terminal_bad]
 pending=[name for name in required if name not in effective or not green(effective[name])]
 if 'dco' in effective and (effective['dco'].get('status')!='COMPLETED' or effective['dco'].get('conclusion') not in ['SUCCESS','SKIPPED']):pending.append('dco')
 status='GREEN' if not pending and not latest_bad and complete and commit['oid']==p['headRefOid'] and not wrong else 'FAILURE' if latest_bad else 'PENDING'
 prs.append({'number':n,'url':p['url'],'title':p['title'],'state':p['state'],'head':p['headRefOid'],'branch':p['headRefName'],'base':p['baseRefName'],'merged_at':p['mergedAt'],'expected':expected[n],'expected_mismatches':wrong,'checked_commit_oid':commit['oid'],'check_status':status,'required_checks':required,'pending_required_checks':pending,'all_check_contexts':checks,'effective_checks':list(effective.values()),'terminal_non_success_contexts':terminal_bad,'latest_terminal_non_success_names':latest_bad,'context_coverage':{'total_count':connection['totalCount'] if connection else 0,'returned':len(checks),'has_next_page':connection['pageInfo']['hasNextPage'] if connection else False,'complete':complete}})
receipt={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'query_started_at_utc':start,'scope':'security fix forward stack exact-head read-only CI','push_receipt':push_path.name,'push_receipt_sha256':hashlib.sha256(push_path.read_bytes()).hexdigest(),'all_prs_open':all(p['state']=='OPEN' for p in prs),'all_exact_heads_bases_branches_match':all(not p['expected_mismatches'] for p in prs),'all_required_checks_green':all(p['check_status']=='GREEN' for p in prs),'coverage':{'returned_count':len(prs),'expected_count':13,'all_context_connections_exhausted':all(p['context_coverage']['complete'] for p in prs),'checked_commit_matches_head':all(p['head']==p['checked_commit_oid'] for p in prs)},'dco_skips_are_not_agent_certification':True,'mutations_performed':False,'prs':prs}
if args.final:
 assert receipt['all_prs_open'] and receipt['all_exact_heads_bases_branches_match'] and receipt['all_required_checks_green'],[(p['number'],p['check_status']) for p in prs]
 name='security-fix-all-pr-ci-final-2026-10-12.json'
else:name='security-fix-all-pr-ci-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json'
p=BASE/name
assert not p.exists(),p
p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'receipt':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'all_open':receipt['all_prs_open'],'all_expected_match':receipt['all_exact_heads_bases_branches_match'],'all_green':receipt['all_required_checks_green'],'prs':[{'number':p['number'],'state':p['state'],'head':p['head'][:7],'status':p['check_status'],'pending':p['pending_required_checks'],'failures':p['latest_terminal_non_success_names'],'mismatches':p['expected_mismatches']} for p in prs]},indent=2))
