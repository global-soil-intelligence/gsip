"""Immutable counts-only GitHub metadata preflight; no mutations or binary downloads."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

BASE = Path(__file__).resolve().parent
REPO = "repos/global-soil-intelligence/gsip"
EXPECTED_MAIN = "7a2c082ced29a9da2e731484590ea5aedfe5a657"
WORKERS = {"prior": 372625971, "qa": 372626162, "export": 372626465}
NONTERMINAL = ["queued", "in_progress", "waiting", "pending", "requested"]
NATIVE = {
    34: ("19e626c8a95fae32dbd8ad0ff96bc96aba541a0f", 38265397710),
    39: ("d522c770c3a7fa490c6906817a7d3121842c365b", 38265400180),
}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def api(endpoint, paginate=False):
    command = ["/opt/homebrew/bin/gh", "api", "--method", "GET"]
    if paginate:
        command.extend(["--paginate", "--slurp"])
    command.append(endpoint)
    raw = subprocess.check_output(command, text=True)
    return {"queried_at": now(), "endpoint": endpoint, "pages": json.loads(raw) if paginate else [json.loads(raw)]}


queries = {
    "main": (f"{REPO}/commits/main", False),
    "workflows": (f"{REPO}/actions/workflows?per_page=100", True),
    **{name: (f"{REPO}/actions/workflows/{ident}/runs?per_page=100", True) for name, ident in WORKERS.items()},
    **{f"active_{status}": (f"{REPO}/actions/runs?status={status}&per_page=100", True) for status in NONTERMINAL},
    **{f"pr_{pr}": (f"{REPO}/pulls/{pr}", False) for pr in NATIVE},
    **{f"run_{pr}": (f"{REPO}/actions/runs/{run}", False) for pr, (_, run) in NATIVE.items()},
    **{f"artifacts_{pr}": (f"{REPO}/actions/runs/{run}/artifacts?per_page=100", True) for pr, (_, run) in NATIVE.items()},
}
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {name: executor.submit(api, *query) for name, query in queries.items()}
    responses = {name: future.result() for name, future in futures.items()}

observations = {}
for name, response in responses.items():
    if name.startswith(("pr_", "run_", "artifacts_")):
        continue
    pages = response["pages"]
    if name == "main":
        data = {"sha": pages[0]["sha"], "committed_at": pages[0]["commit"]["committer"]["date"]}
    elif name == "workflows":
        workflows = [workflow for page in pages for workflow in page["workflows"]]
        data = {"total_counts": [page["total_count"] for page in pages], "returned_workflows": len(workflows), "workflows": [{key: workflow[key] for key in ["id", "name", "path", "state"]} for workflow in workflows]}
    else:
        runs = [run for page in pages for run in page["workflow_runs"]]
        data = {"total_counts": [page["total_count"] for page in pages], "returned_runs": len(runs), "runs": [{key: run.get(key) for key in ["id", "workflow_id", "name", "path", "status", "conclusion", "event", "head_branch", "head_sha", "created_at", "updated_at", "html_url"]} for run in runs]}
    observations[name] = {"queried_at": response["queried_at"], "endpoint": response["endpoint"], "pages": len(pages), "data": data}

failures = []
baseline_path = BASE / "production-worker-quiescence-2026-10-12.json"
baseline = json.loads(baseline_path.read_text())
if observations["main"]["data"]["sha"] != EXPECTED_MAIN:
    failures.append("main differs from the bound preflight source")
inventory = observations["workflows"]["data"]
if inventory["total_counts"][0] != inventory["returned_workflows"] or len({item["id"] for item in inventory["workflows"]}) != inventory["returned_workflows"]:
    failures.append("workflow inventory pagination incomplete or duplicated")
for name, ident in WORKERS.items():
    matched = [workflow for workflow in inventory["workflows"] if workflow["id"] == ident]
    if len(matched) != 1 or matched[0]["state"] != "disabled_manually":
        failures.append(f"{name} worker disabled state mismatches")
    runs = observations[name]["data"]
    if runs["total_counts"][0] != runs["returned_runs"] or len({run["id"] for run in runs["runs"]}) != runs["returned_runs"]:
        failures.append(f"{name} worker history pagination incomplete or duplicated")
    if any(run["status"] != "completed" for run in runs["runs"]):
        failures.append(f"{name} worker has a nonterminal run")
    if runs != baseline["observations"][name]["data"]:
        failures.append(f"{name} worker history differs from the bound baseline")
if {item["id"]: item for item in inventory["workflows"]} != {item["id"]: item for item in baseline["observations"]["workflows"]["data"]["workflows"]}:
    failures.append("workflow inventory differs from the bound baseline")
for status in NONTERMINAL:
    active = observations[f"active_{status}"]["data"]
    if active["total_counts"][0] != active["returned_runs"]:
        failures.append(f"repository {status} coverage incomplete")
    if active["returned_runs"]:
        failures.append(f"repository has {status} runs")

records = []
for pr, (head, run_id) in NATIVE.items():
    live_pr = responses[f"pr_{pr}"]["pages"][0]
    run = responses[f"run_{pr}"]["pages"][0]
    artifact_pages = responses[f"artifacts_{pr}"]["pages"]
    artifacts = [artifact for page in artifact_pages for artifact in page["artifacts"]]
    if live_pr["state"] != "open" or live_pr["head"]["sha"] != head:
        failures.append(f"PR {pr} state or head differs")
    if run["head_sha"] != head or run["status"] != "completed" or run["conclusion"] != "success":
        failures.append(f"PR {pr} exact-head native run is not successful")
    if artifact_pages[0]["total_count"] != len(artifacts) or len(artifacts) != 2:
        failures.append(f"PR {pr} artifact coverage differs")
    if {artifact["name"] for artifact in artifacts} != {"gsip-capture-android-debug", "gsip-capture-ios-simulator"}:
        failures.append(f"PR {pr} artifact names differ")
    if any(artifact["expired"] or artifact["size_in_bytes"] <= 0 for artifact in artifacts):
        failures.append(f"PR {pr} artifact expired or empty")
    records.append({"pr": pr, "head": head, "run": {key: run[key] for key in ["id", "name", "event", "head_sha", "head_branch", "status", "conclusion", "html_url", "created_at", "updated_at", "run_attempt"]}, "artifact_coverage": {"pages": len(artifact_pages), "total_count": artifact_pages[0]["total_count"], "returned_count": len(artifacts), "complete": artifact_pages[0]["total_count"] == len(artifacts)}, "artifacts": [{key: artifact.get(key) for key in ["id", "name", "size_in_bytes", "expired", "created_at", "updated_at", "expires_at", "digest"]} for artifact in artifacts]})

receipt = {"observed_at": now(), "kind": "Read-only Gate D worker and native artifact readiness refresh", "production_project": "toxldjgwkxtneoqsazym", "status": "PASS" if not failures else "STOP_MISMATCH", "failures": failures, "worker_baseline": {"path": baseline_path.name, "sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest()}, "observations": observations, "native_records": records, "mutations_performed": False, "coverage": "Complete paginated registered worker workflow histories and inventory, plus all five repository nonterminal status filters. Native run/artifact metadata refreshed independently at exact current PR heads.", "limits": ["Snapshot is not a lock and cannot exclude external operators or direct production invocations. Root owns separate database activity and cron preflight.", "No GitHub workflow state, dispatch, review, merge, source, production setting or database changed.", "Native archives remain unexpired and nonempty; immutable binaries were verified earlier, and are not downloaded again in this refresh."]}
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
path = BASE / f"gate-d-worker-native-readiness-{stamp}.json"
with path.open("x") as handle:
    handle.write(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"receipt": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "status": receipt["status"], "failures": failures, "worker_runs": {name: observations[name]["data"]["returned_runs"] for name in WORKERS}, "nonterminal_counts": {status: observations[f"active_{status}"]["data"]["returned_runs"] for status in NONTERMINAL}, "native": [{"pr": record["pr"], "run": record["run"]["html_url"], "artifact_ids": [artifact["id"] for artifact in record["artifacts"]]} for record in records]}, indent=2))
if failures:
    raise SystemExit(2)
