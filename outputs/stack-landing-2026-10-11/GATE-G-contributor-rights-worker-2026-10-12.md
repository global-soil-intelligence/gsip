# Gate G: one contributor-rights worker run — prepared, not authorised

Repository: global-soil-intelligence/gsip. Production: gsip, toxldjgwkxtneoqsazym. No worker run, deployment, merge or capture opening has occurred during preparation.

Before execution: Justin saves the existing project's legacy service_role JWT directly in GitHub as SUPABASE_SERVICE_ROLE_KEY. The agent checks only the secret name and creation/update metadata. GitHub cannot disclose its value; presence does not prove project/key correctness. Only the later authorised worker can validate authentication. This worker uses the key as both apikey and Bearer credential, and prior-attach retains JWT verification. Do not substitute a publishable key or a new sb_secret key in this gate. No key rotation.

## Invariants

Ledger stays 28; all source-bound schemas, permissions and data counts remain unchanged under the current empty-queue baseline. Capture/sign-up/anonymous off; photo publication, QA, prior enrichment, export, quarantine cleanup and Pages held. No real contents, object paths, auth identifiers, coordinates or key values in logs or evidence. Counts only. No failed run retry, rollback, workflow enabling or schedule change is included.

The rights worker may physically delete requested submissions/photos/auth users and canonical orphaned objects. Fresh preparation counted requests 0/open 0/overdue 0, canonical orphans 0, storage objects 0, contributors 5/submissions 25/photos 25/auth users 0/ledger 28/capture-open rows 0. Therefore this narrowly proposed initial run expects zero deletion and unchanged counts. Stop before execution if any queue/orphan/count changes; present the changed counts to Justin for a revised gate. Never call claiming/applying/completing RPCs as preflight probes.

## Prerequisites and exact future command

Rights-worker.yml is absent from current main; GitHub manual dispatch requires the workflow on the default branch. Justin must merge the relevant workflow updates. Merges remain Justin's action. After merge, refresh workflow registration, exact remote source head and pinned worker/workflow/lockfile hashes, current CI, secret-name presence, exact target URL, all production invariants and absence of active writers/runs.

The proposed dispatch selects the already reviewed branch whose current head is 19e626c8a95fae32dbd8ad0ff96bc96aba541a0f. If the branch moves or is deleted, stop and prepare a new exact-source plan rather than dispatching another ref.

```sh
gh workflow run rights-worker.yml --repo global-soil-intelligence/gsip --ref wp-app-1-phone-app
```

The workflow's exact worker invocation is:

```sh
uv run python -m pipeline.rights_worker --budget-seconds 1200
```

Credentials are supplied only by GitHub Actions secrets, never local shell/chat. Authorisation must explicitly cover the run and the workflow's existing failure-alert issue/comment action; it posts only a generic failure notice and run URL. No alert action is authorised during preparation.

GitHub registers new hourly rights and quarantine schedules when their workflows reach main. Adding the secret alone does not dispatch a workflow, but owner merges can make those schedules runnable. Review scheduled-worker holds before merging; a one-off Gate G approval must not be treated as blanket permission to enable recurring production work. If the workflow is disabled, do not enable it under this proposed dispatch alone; prepare any required schedule-control change separately.

## Readback after a separately approved run

Record the exact run URL/id and verify event workflow_dispatch, head 19e626c..., expected workflow file, no competing run. Require process job completed/success and actual count-only worker summary: zero completed/failed requests, zero submissions/objects/orphans deleted, no overdue or time-budget warning. If a job fails, stop; no retry or key replacement. Then re-read all table counts, full ledger hashes/catalog/ACLs, full security advisor zero, capture/Auth off, Edge Functions unchanged (prior v4 JWTon; public v1 JWToff), and worker holds. The stored secret's validity remains unverified until this succeeds.

## Other workers remain outside Gate G

Photo QA may modify or strip original uploads; it needs its own bounded gate. Photo publication and export remain held until the WP-6f screening/calibration and structured-data-only release gates are satisfied. Hugging Face remains Justin's setup. Prior enrichment invokes upstream APIs and is a separate gate. No worker or deployment runs are authorised by preparation.

Assumptions: current empty queue/orphan state holds only for this snapshot and must be refreshed. No real contributor data is inspected. The existing service_role JWT is used to match reviewed code; a migration to newer secret-key authentication is a separate future change. Local worker tests are not rerun or claimed here; current-head CI is the existing validation evidence. Source manifest and counts receipt are saved beside this plan.
