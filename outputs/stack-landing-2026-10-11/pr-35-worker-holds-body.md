## Problem and behavior

Two website tabs can concurrently send the same IndexedDB queue record. WP-3b wraps the complete queue drain in `navigator.locks.request('gsip-sync', { ifAvailable: true }, …)`. A busy context returns without reading or mutating the queue; browsers without Web Locks keep existing idempotent behavior.

## Invariants and acceptance

- [x] One same-origin drain owns the lock until its promise settles; no waiting when busy.
- [x] Account, withdrawal, generation/cancellation, retry/backoff and dead-letter semantics stay unchanged. Private queue data remains private.
- [x] Unsupported Web Locks retain the previous drain.
- [x] Regression tests cover concurrent contexts, busy/no queue access, unsupported contexts and exception release. Three failed without the implementation; all five pass.

## Verification

Local: 307 Vitest; 220 pytest with four GDAL skips; lint, typecheck, Python Ruff/mypy, closed-capture web/app builds, map/site budgets and pinned Gitleaks 8.21.2 staged scan passed. Current PR CI is pending. GDAL and Deno were unavailable locally; a real two-tab browser smoke was not run.

Assumptions: the browser supplies standards-compliant origin-scoped Web Locks; the tests simulate two contexts with a shared manager. Existing online/30-second triggers retry a skipped drain. The existing per-screen generation counter and separate queue mutations are outside this lock's scope.

## Authority and assumptions

- Justin Hart is product owner and human of record; Codex wrote this follow-up. Justin reviews and merges. No merge, approval, deployment or capture opening occurred.
- This PR starts from green WP-APP-1 head `f9e1ac2` and stays stacked there until the reviewed stack merges. Existing reviewed commits are preserved.
- Capture and production anonymous sign-in stay closed. I5, I7, I12 and B1–B8 remain binding. MIT code, ODbL 1.0 data and CC BY-SA 4.0 photos are unchanged. No dependency added.


## Changes after review
### Security-boundary correction and exact-head CI (2026-10-12)

Current head: `79baf1edb976909428642d8548876ac6b7243f59`. Existing description and earlier verification records are preserved above.

Inherited change: merge-forward carries #28’s spec-first boundary clarification and #29/#31’s additive guarded-helper/invoker and restrictive-policy fixes. The owning fixes remain on WP-6b/WP-6d; this branch does not duplicate or rewrite their SQL.

The hosted Gate C zero-findings check stopped on seven findings across the service-only rights tables and client-executable public definer functions. The correction preserves authorization rather than suppressing any advisor rule. All 26 executed migration blobs remain unchanged. No new client schema, table or column grant is added; narrow EXECUTE grants on new private helpers match the existing public callers. Public signatures and caller ACLs, owner checks, withdrawal refusal and capture-closed behavior remain intact.

Local source proof preserved the existing WP-6b 99 assertions and WP-6d 209 assertions; the new owning suites passed 16 and 21 assertions respectively, with 13 new assertions failing before the changes. The candidate complete pgTAP suite passed 299 assertions, migration testing passed 13/13, and isolated synthetic PostgREST dispatch/reload/privilege tests passed 33/33. These are local proofs; hosted advisor remediation remains unexecuted.

Exact-head CI, verified 2026-10-12 14:56:50 UTC: [validate — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265398397/job/114866168822), [gitleaks — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265398853/job/114866169759). All 13 updated PR heads are green for their required checks. DCO is SKIPPED; an agent has not certified Justin’s DCO.

Assumptions: the reviewed migration owner and exposed-schema settings remain unchanged and there is no overlapping production writer; production execution must refresh these checks. Private is absent from the observed Data API exposed-schema list, but schema placement alone is not authorization. Local tests use synthetic data and do not establish the hosted advisor’s final state. Capture, sign-up and anonymous sign-in stay closed; no production mutation, deployment, new dependency, service or licence change is included in this update.


### Changes after review — owner merge exception and worker holds (2026-10-12)

Justin explicitly authorised removing the extra approving-review requirement for this owner-operated repository. Independent review, green CI, resolved conversations and protection against force pushes remain required. Agents do not submit approving reviews or certify the DCO.
Scheduled production workers now require their own explicit repository-variable opt-in; absent variables hold jobs before any secret-bearing step. Manual dispatch still requires a separate production gate. Contributor-rights schedules receive the same hold from WP-6d onward. This prevents merging workflows or adding a credential from starting unapproved production work. Regression tests failed before the relevant change and passed after it.

Assumptions: schedule opt-in variables remain unset; this merge authority does not authorise deployments, worker dispatches or capture opening. No dependencies or secret-scan exceptions were added.
