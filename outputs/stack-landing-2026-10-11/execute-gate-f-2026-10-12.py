"""Execute only Justin's approved two-variable Gate F; never print key values."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

B = Path(__file__).resolve().parent
REPO = "global-soil-intelligence/gsip"
API = "repos/" + REPO
GH = "/opt/homebrew/bin/gh"
NEW = {
    "SUPABASE_URL": "https://toxldjgwkxtneoqsazym.supabase.co",
    "VITE_GSIP_PUBLIC_API": "https://toxldjgwkxtneoqsazym.supabase.co/functions/v1/gsip-public",
}
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
receipt = {
    "state": "STARTED",
    "repository": REPO,
    "authorization": "Justin: Gate F go; set only two new variables, retain existing key and old URL; no deployment, merge or capture opening.",
    "started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "commands": [],
    "checks": {},
    "deployments": [],
    "merges": [],
    "workflow_dispatches": [],
    "secret_changes": [],
}

def run(argv):
    p = subprocess.run(argv, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError("Command failed; output withheld, exit=" + str(p.returncode))
    return p.stdout

def api(endpoint):
    return json.loads(run([GH, "api", "--method", "GET", endpoint]))

def variables():
    x = api(API + "/actions/variables?per_page=100")
    assert x["total_count"] == len(x["variables"]), "Incomplete variable inventory"
    return {v["name"]: v["value"] for v in x["variables"]}

def protections():
    pages = api(API + "/environments/github-pages")
    rules = pages["protection_rules"]
    reviewers = [u["reviewer"]["login"] for r in rules if r["type"] == "required_reviewers" for u in r["reviewers"]]
    assert reviewers == ["jdhart81"] and pages["can_admins_bypass"] is False
    workers = {str(i): api(API + "/actions/workflows/" + str(i))["state"] for i in [372625971, 372626162, 372626465]}
    assert all(s == "disabled_manually" for s in workers.values())
    return {"pages_admin_bypass": False, "pages_required_reviewers": reviewers, "worker_states": workers, "main": api(API + "/commits/main")["sha"]}

try:
    old = variables()
    assert set(old) == {"VITE_SUPABASE_URL", "VITE_SUPABASE_PUBLISHABLE_KEY"}, "Variable baseline changed; stop"
    assert old["VITE_SUPABASE_URL"] == NEW["SUPABASE_URL"], "Old URL baseline mismatch"
    assert old["VITE_SUPABASE_PUBLISHABLE_KEY"].startswith("sb_publishable_"), "Key format mismatch"
    pre = protections()
    receipt["preflight"] = pre
    expected = dict(old)
    for name, value in NEW.items():
        command = [GH, "variable", "set", name, "--repo", REPO, "--body", value]
        start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        p = subprocess.run(command, capture_output=True, text=True)
        receipt["commands"].append({"argv": command, "started_at_utc": start, "exit_code": p.returncode, "stdout_sha256": hashlib.sha256(p.stdout.encode()).hexdigest(), "stderr_sha256": hashlib.sha256(p.stderr.encode()).hexdigest()})
        assert p.returncode == 0, "Variable set failed; stop, no retry"
        expected[name] = value
        actual = variables()
        receipt["checks"][name + "_exact_readback_and_other_variables_unchanged"] = actual == expected
        assert actual == expected, "Variable readback mismatch; stop"
    post = protections()
    receipt["checks"]["protection_workers_and_main_unchanged"] = post == pre
    assert post == pre, "Repository protection/worker/main mismatch"
    receipt["postflight"] = post
    receipt["verified_urls"] = NEW
    receipt["checks"]["existing_publishable_key_unchanged"] = actual["VITE_SUPABASE_PUBLISHABLE_KEY"] == old["VITE_SUPABASE_PUBLISHABLE_KEY"]
    receipt["checks"]["old_url_unchanged"] = actual["VITE_SUPABASE_URL"] == old["VITE_SUPABASE_URL"]
    receipt["variable_names"] = sorted(actual)
    secrets = api(API + "/actions/secrets?per_page=100")
    assert secrets["total_count"] == len(secrets["secrets"]), "Incomplete secret-name inventory"
    receipt["service_role_secret_present_name_only"] = "SUPABASE_SERVICE_ROLE_KEY" in {s["name"] for s in secrets["secrets"]}
    receipt["state"] = "PASS_GATE_F_TWO_VARIABLES_VERIFIED"
except Exception as e:
    receipt["state"] = "STOP_GATE_F"
    receipt["reason"] = str(e)
finally:
    receipt["completed_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    path = B / ("gate-f-execution-receipt-" + stamp + ".json")
    assert not path.exists()
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"], "receipt": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "checks": receipt["checks"], "service_role_secret_present_name_only": receipt.get("service_role_secret_present_name_only"), "reason": receipt.get("reason")}))
if receipt["state"].startswith("STOP"):
    raise SystemExit(1)
