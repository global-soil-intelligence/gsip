# Gate G — one contributor-rights worker run, prepared only

Target: Supabase `gsip`, `toxldjgwkxtneoqsazym`, us-east-1. Repository: `global-soil-intelligence/gsip`.
Source: merged `main`, `665506fd7a2e4d972bb9fe03c4faf0f174c4675b`.
Source hashes: `gate-g-merged-main-manifest-20261012.json`. No dispatch has occurred.

## Invariants and preflight

Refresh all production counts, complete ledger hashes/catalog/ACLs, zero security findings,
capture closed, signup/anonymous sign-in off, function versions and JWT settings, secret-name
presence, target repository URL, current-head CI and absence of competing worker runs.
Never inspect or print secret values or contributor contents. Never call mutation RPCs as probes.
Stop if main or any manifest hash differs, any production invariant differs, or any request,
canonical orphan or storage object exists. Present changed counts and a revised gate to Justin.

Fresh merge-time readback: ledger 28; contributors 5; submissions 25; photos 25; auth users 0;
requests/open requests 0; storage objects 0; capture-open rows 0; security findings 0.
Canonical-orphan, full-table/catalog and Auth-setting evidence must be refreshed before a go is executed.
The GitHub secret name is present; its value/project correctness remains unverified until an authorised run succeeds.

## Exact proposed dispatch — wait for Justin's go

```sh
gh workflow run rights-worker.yml --repo global-soil-intelligence/gsip --ref main
```

The workflow invokes:

```sh
uv run python -m pipeline.rights_worker --budget-seconds 1200
```

The proposed authority covers exactly one manual run and its existing generic failure-alert
issue/comment action, which contains only a failure notice and run URL. Credentials flow only
from GitHub Actions secret storage. No key rotation, workflow enabling, retry, schedule opt-in,
deployment, QA, prior enrichment, export, cleanup, Pages approval or capture opening is included.

## Verification

Require the run event to be `workflow_dispatch` and its source SHA to equal the bound main SHA.
Require the process job and count-only summary to pass: zero completed/failed requests and zero
rows/objects/orphans deleted, with no overdue or budget warning. Re-read every production invariant
and the full unchanged count/catalog/ACL baseline. On failure or mismatch, stop without retry.
Schedules remain held by absent `GSIP_*_SCHEDULE_ENABLED` variables; a manual run does not enable them.

## Open concerns and assumptions

Four newly surfaced dependency alerts remain open: fsspec/high (fixed 2026.6.0), source-map-js/high
(fixed 1.2.2), multidict/moderate (fixed 6.9.1), uuid/moderate (fixed 11.1.1). These are not Supabase
advisor findings. Recommend a separate tested dependency-remediation package before further
worker execution; this document does not claim their exploitability has been resolved.

Assumptions: the empty-queue seed baseline remains unchanged when refreshed; no other authorised
writer advances main between its final source verification and dispatch. If either assumption
fails, stop and rebind the plan. Human signing, legal approval, photo calibration, tiles and
export destinations retain their own gates.
