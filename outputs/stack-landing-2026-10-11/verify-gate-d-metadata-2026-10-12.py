"""Verify read-only Gate D metadata against fixed, previously reviewed references."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

B = Path(__file__).resolve().parent
OPS = Path("/Users/justinhart/.codex/worktrees/gsip-spec-followups/GSIP 2.0")
SOURCE = Path("/Users/justinhart/.codex/worktrees/gsip-coding-guidance/GSIP 2.0")
EXPECTED_HELPER = "2ea3ce49a3a68a9ba4e42b4b0314d8c118bc0098f702d540b82fba9f8207e620"
EXPECTED_SOURCE = "19e626c8a95fae32dbd8ad0ff96bc96aba541a0f"
EXPECTED_ALIASES = {"gold_labels_select_own", "photos_select_own", "predictions_select_own", "priors_select_own", "qa_events_select_own"}
NEW_IDENTITIES = [{"version":"20261012141828","name":"wp6b_invoker_boundary"},{"version":"20261012142348","name":"wp6d_private_rights_boundary"}]

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text())

def security_identity(rows):
    return sorted(json.dumps({"name":r["name"],"title":r["title"],"level":r["level"],"facing":r["facing"],"categories":r["categories"],"remediation":r["remediation"],"count":r["count"],"metadata":sorted([f["metadata"] for f in r["findings"]],key=lambda v:json.dumps(v,sort_keys=True))},sort_keys=True) for r in rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["pre","post"], required=True)
    parser.add_argument("--stamp", required=True)
    parser.add_argument("--pre-stamp", default="20261012T191950Z")
    args=parser.parse_args()
    phase=args.phase
    paths={n:B/f"production-gate-d-{phase}-{n}-{args.stamp}.json" for n in ["catalog","supplement","counts","ledger","table_inventory","capture","default_acls","security_advisor","edge_inventory","query-inputs","query-response-times"]}
    current={n:read(p) for n,p in paths.items()}
    old={n:read(B/f"production-pre-gate-d-{n}-20261012T144433Z.json") for n in ["catalog","supplement","counts","ledger","table_inventory","capture","security_advisor","edge_inventory"]}
    pre={n:read(B/f"production-gate-d-pre-{n}-{args.pre_stamp}.json") for n in ["catalog","supplement","counts","ledger","table_inventory","capture","default_acls","security_advisor","edge_inventory"]}
    checks={}
    target=26 if phase=="pre" else 28
    expected_counts={r["table_name"]:r["row_count"] for r in pre["counts"]}
    expected_counts["supabase_migrations.schema_migrations"]=target
    actual_counts={r["table_name"]:r["row_count"] for r in current["counts"]}
    checks["all61_table_names_and_counts_exact_except_authorized_ledger_delta"]=len(actual_counts)==61 and actual_counts==expected_counts
    checks["all61_table_inventory_exact"]=len(current["table_inventory"])==61 and current["table_inventory"]==old["table_inventory"]
    old_ledger=old["ledger"] if phase=="pre" else pre["ledger"]
    actual_ledger=current["ledger"]
    checks["all26_complete_historical_row_hashes_preserved"]=len(old_ledger)==26 and all(r in actual_ledger for r in old_ledger)
    checks["ledger_exact_expected_identities"]=len(actual_ledger)==target and ([{"version":r["version"],"name":r["name"]} for r in actual_ledger]==[{"version":r["version"],"name":r["name"]} for r in old_ledger]+([] if phase=="pre" else NEW_IDENTITIES))
    checks["all_full_ledger_hashes_valid"]=all(re.fullmatch("[0-9a-f]{64}",r["history_row_sha256"]) for r in actual_ledger)
    checks["capture_exactly_one_closed_singleton"]=current["capture"]==[{"row_count":1,"capture_true_count":0,"capture_false_count":1,"singleton_true_count":1}]
    checks["postgres_global_private_default_function_acls_still_empty"]=current["default_acls"]==[]
    checks["complete_edge_metadata_unchanged"]=current["edge_inventory"]==old["edge_inventory"]
    checks["prior_attach_v3_only_active_jwt_on"]=len(current["edge_inventory"])==1 and all(current["edge_inventory"][0][k]==v for k,v in {"name":"prior-attach","slug":"prior-attach","version":3,"verify_jwt":True,"status":"ACTIVE"}.items())
    checks["strict_comparator_source_unchanged"]=digest(OPS/"scripts/reconciliation.py")==EXPECTED_HELPER
    if phase=="pre":
        checks["complete_primary_catalog_exact_prior_baseline"]=current["catalog"]==old["catalog"]
        checks["complete_supplement_catalog_exact_prior_baseline"]=current["supplement"]==old["supplement"]
        checks["same_exact7_security_instances"]=security_identity(current["security_advisor"])==security_identity(old["security_advisor"]) and sum(x["count"] for x in current["security_advisor"])==7
    else:
        checks["complete_hosted_security_advisor_zero_findings"]=current["security_advisor"]==[]
        for section in ["table_grants","column_grants"]:
            checks[section+"_unchanged"]=current["catalog"][section]==pre["catalog"][section]
        for section in ["schema_grants","storage_policies"]:
            checks[section+"_unchanged"]=current["supplement"][section]==pre["supplement"][section]
        old_public={(x["name"],x["arguments"]):x for x in pre["catalog"]["functions"]}
        new_public={(x["name"],x["arguments"]):x for x in current["catalog"]["functions"]}
        checks["all_public_signatures_owners_complete_caller_acls_unchanged"]=set(old_public)==set(new_public) and all(old_public[k]["owner"]==new_public[k]["owner"] and old_public[k]["grants"]==new_public[k]["grants"] and old_public[k]["result"]==new_public[k]["result"] for k in old_public)
        helpers={x["name"]:x for x in current["supplement"]["private_functions"] if x["name"] in {"finalize_submission","current_auth_user_exists","my_submission_accepts_uploads"}}
        reference=read(B/"canonical-supplement-target28.json")
        expected_helpers={x["name"]:x for x in reference["private_functions"] if x["name"] in {"finalize_submission","current_auth_user_exists","my_submission_accepts_uploads"}}
        checks["three_new_private_helpers_exact_reviewed_definitions_owners_and_complete_acls"]=len(helpers)==3 and helpers==expected_helpers
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=SOURCE,capture_output=True,text=True)
    clean=subprocess.run(["git","status","--porcelain"],cwd=SOURCE,capture_output=True,text=True)
    checks["source_exact_candidate_and_clean"]=head.returncode==clean.returncode==0 and head.stdout.strip()==EXPECTED_SOURCE and clean.stdout==""
    ref_catalog=B/f"canonical-catalog-target{target}.json"
    ref_supplement=B/("canonical-catalog-target26-supplement.json" if target==26 else "canonical-supplement-target28.json")
    command=["python3","-B","-m","scripts.reconciliation","--reference-catalog",str(ref_catalog),"--observed-catalog",str(paths["catalog"]),"--reference-supplement",str(ref_supplement),"--observed-supplement",str(paths["supplement"])]
    p=subprocess.run(command,cwd=OPS,capture_output=True,text=True)
    try:
        result=json.loads(p.stdout)
    except ValueError:
        raise RuntimeError("Strict comparator failed to return structured metadata; raw output withheld")
    checks["strict_target_catalog_comparator_pass"]=p.returncode==0 and result.get("ok") is True and result.get("unexpected_differences")==[]
    aliases={x["identifier"] for x in result.get("allowed_differences",[]) if x["kind"]=="exact_submission_alias"}
    checks["exactly_same5_bound_ownership_aliases"]=aliases==EXPECTED_ALIASES
    receipt={"state":"PASS_READONLY_GATE_D_"+phase.upper() if all(checks.values()) else "STOP_GATE_D_"+phase.upper(),"target_project_ref":"toxldjgwkxtneoqsazym","completed_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"production_mutations_by_this_agent":0,"checks":checks,"failed_checks":[k for k,v in checks.items() if not v],"table_counts":current["counts"],"ledger":actual_ledger,"capture":current["capture"],"default_function_acls":current["default_acls"],"security_categories":len(current["security_advisor"]),"security_instance_count":sum(x["count"] for x in current["security_advisor"]),"strict_comparator":{"source_sha256":digest(OPS/"scripts/reconciliation.py"),"command":command,"exit_code":p.returncode,"result":result},"scope_limits":["Metadata, hashes and aggregate counts only; no real contributor contents, precise coordinates, keys or raw uploads.","This agent never runs the migration push or any production mutation.","Auth flags, exposed schema configuration, worker quiescence and anonymous hosted RPC probe are separately verified by root.","Post-phase claims require fresh reads after root explicitly announces completed execution."],"bound_inputs":[{"path":str(p),"sha256":digest(p)} for p in [*paths.values(),ref_catalog,ref_supplement,B/"production-pre-gate-d-refresh-20261012T144433Z.json",Path(__file__)]]}
    out=B/f"production-gate-d-{phase}-metadata-verification-{args.stamp}.json"
    if out.exists():
        raise RuntimeError("Immutable receipt already exists; choose a new stamp")
    raw=(json.dumps(receipt,indent=2,sort_keys=True)+"\n").encode()
    out.write_bytes(raw)
    print(json.dumps({"path":str(out),"sha256":hashlib.sha256(raw).hexdigest(),"state":receipt["state"],"checks_passed":sum(checks.values()),"checks_total":len(checks),"failed_checks":receipt["failed_checks"]}))

if __name__=="__main__":
    main()
