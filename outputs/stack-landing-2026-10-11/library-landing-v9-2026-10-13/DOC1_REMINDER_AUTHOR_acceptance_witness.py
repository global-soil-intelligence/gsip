"""Private WP-DOC-1 status and complete preservation witness; not a tracked source file."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path

ROOT = Path(__file__).parent
PR_URL = "https://github.com/global-soil-intelligence/gsip/pull/63"
DOCS = {"README.md", "docs/SPEC.md", "docs/BUILD_ORDER.md"}
MAIN = "a63850591c3c54ddb7923f8072671f6dea4fe9ed"

def section(raw: bytes, start: bytes, end: bytes) -> bytes:
    return raw[raw.index(start):raw.index(end)]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tree", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    binding = json.loads((ROOT / "BASELINE_BINDING.json").read_bytes())
    edits = json.loads((ROOT / "APPROVED_STATUS_EDITS.json").read_bytes())
    baseline = {name: (ROOT / "baseline" / name).read_bytes() for name in DOCS}
    candidate = {name: (args.tree / name).read_bytes() for name in DOCS}
    checks: dict[str, bool] = {}
    checks["source_claim_has_authenticated_merged_PR63_main_baseline"] = (
        binding["base_commit"] == MAIN and binding["PR_merge_commit"] == MAIN
        and binding["merged_PR"] == 63 and binding["main_tree_equals_faab"] is True
    )
    checks["README_records_merged_APP2B_source_only"] = (
        f"Source for opt-in local sync reminders is merged in [APP-2B (#63)]({PR_URL}).".encode()
        in candidate["README.md"]
        and b"gates remain separate from source completion" in candidate["README.md"]
    )
    checks["SPEC_records_merged_APP2B_source_only"] = (
        f"**Source status:** opt-in local sync reminder source is merged in [APP-2B (#63)]({PR_URL}).".encode()
        in candidate["docs/SPEC.md"]
        and b"existing device and launch requirements below remain unchanged" in candidate["docs/SPEC.md"]
    )
    checks["BUILD_ORDER_records_merged_source_without_stale_proposal_claim"] = (
        f"APP-2B notification source is merged in [#63]({PR_URL})".encode()
        in candidate["docs/BUILD_ORDER.md"]
        and b"**WP-APP-2B: Local sync reminders in version 1 (source merged; device gates remain)**"
        in candidate["docs/BUILD_ORDER.md"]
        and b"Notification architecture remains a proposal" not in candidate["docs/BUILD_ORDER.md"]
        and b"without claiming it has been approved or implemented" not in candidate["docs/BUILD_ORDER.md"]
    )
    for name in sorted(DOCS):
        restored = candidate[name].decode()
        for edit in reversed(edits[name]):
            if edit["candidate"] in restored:
                restored = restored.replace(edit["candidate"], edit["baseline"])
        checks[f"all_nonstatus_bytes_exact_{name}"] = restored.encode() == baseline[name]
    checks["every_acceptance_checkbox_line_and_state_exact"] = all(
        re.findall(rb"(?m)^.*\[[ xX]\].*$", candidate[name])
        == re.findall(rb"(?m)^.*\[[ xX]\].*$", baseline[name])
        for name in DOCS
    )
    checks["SPEC_I1_I15_invariant_bytes_exact"] = section(
        candidate["docs/SPEC.md"], b"## 2. Invariants", b"## 3. System overview"
    ) == section(baseline["docs/SPEC.md"], b"## 2. Invariants", b"## 3. System overview")
    checks["SPEC_launch_photo_publication_gate_bytes_exact"] = section(
        candidate["docs/SPEC.md"], b"## 11. Phased roadmap", b"## 12. Risks"
    ) == section(baseline["docs/SPEC.md"], b"## 11. Phased roadmap", b"## 12. Risks")
    checks["SPEC_backup_activation_and_owner_gate_bytes_exact"] = section(
        candidate["docs/SPEC.md"], b"### 15.1 Invariants", b"### 15.3 WP-APP-2B"
    ) == section(baseline["docs/SPEC.md"], b"### 15.1 Invariants", b"### 15.3 WP-APP-2B")
    checks["SPEC_photo_privacy_science_federation_bytes_exact"] = candidate["docs/SPEC.md"].split(
        b"### 15.4 WP-6f", 1
    )[1] == baseline["docs/SPEC.md"].split(b"### 15.4 WP-6f", 1)[1]
    changed = []
    outside_exact = True
    modes_exact = True
    for row in binding["files"]:
        path = args.tree / row["path"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            changed.append(row["path"])
            if row["path"] not in DOCS:
                outside_exact = False
        modes_exact &= stat.S_IMODE(path.stat().st_mode) == (
            0o755 if row["mode"] == "100755" else 0o644
        )
    checks["all_362_other_tracked_files_byte_exact"] = outside_exact
    checks["all_365_source_modes_unchanged"] = modes_exact
    checks["only_three_allowed_document_paths_changed"] = set(changed) <= DOCS
    failures = [name for name, good in checks.items() if not good]
    report = {
        "schema": "gsip-doc1-private-acceptance-witness-v1",
        "base_commit": MAIN,
        "checked_source_files": len(binding["files"]),
        "checks": checks,
        "passed": len(checks) - len(failures),
        "failed": len(failures),
        "failed_checks": failures,
        "changed_paths": sorted(changed),
        "acceptance_checkbox_count": sum(
            len(re.findall(rb"(?m)^.*\[[ xX]\].*$", raw)) for raw in candidate.values()
        ),
        "network_or_native_or_production_action": False,
    }
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "passed", "failed", "failed_checks", "acceptance_checkbox_count", "changed_paths"
    )}, sort_keys=True))
    return bool(failures)

if __name__ == "__main__":
    raise SystemExit(main())
