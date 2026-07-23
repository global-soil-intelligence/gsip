## Problem and result

Repository coding agents had no root guide collecting the governing documents, verification commands and owner authority. WP-AGENT-0 adds `AGENTS.md`, links the separate API-consumer `docs/AGENTS.md`, and registers the package in BUILD_ORDER.

## Invariants and acceptance

- [x] Reviewed stack immutability, owner-only approvals/merges and per-step production go remain explicit.
- [x] Privacy, public-only agent access, fixed licences, secret stores and closed-capture rules remain explicit.
- [x] Read-first links, root/workspace check commands, browser project and database/Deno targets resolve in usability tests. Both tests failed before the guide and pass afterward.

## Verification

Two guide usability tests, targeted Ruff/mypy, terminology check, changed-document Prettier and diff checks passed. PR CI is pending.

Assumptions: this consolidates existing authority without granting new permission. The prescribed browser harness produces synthetic local mock output, which is never published; deployable Pages must be rebuilt with capture closed.

## Authority and assumptions

- Justin Hart is product owner and human of record; Codex wrote this follow-up. Justin reviews and merges. No merge, approval, deployment or capture opening occurred.
- This PR starts from green WP-APP-1 head `f9e1ac2` and stays stacked there until the reviewed stack merges. Existing reviewed commits are preserved.
- Capture and production anonymous sign-in stay closed. I5, I7, I12 and B1–B8 remain binding. MIT code, ODbL 1.0 data and CC BY-SA 4.0 photos are unchanged. No dependency added.

## Changes after review

- `6d679f0` makes I5 explicit in the root coding guide: UI and API copy never says "soil test". The generic terminology reference alone did not state the owner's prohibition clearly enough.
- `ca275c4` adds a semantic regression assertion requiring the I5 prohibition to cover both UI and API copy. It fails against the pre-correction guide at `0a3fad1` and passes the corrected guide. All three guide tests, targeted Ruff/mypy, changed-document Prettier, the language guard and diff checks passed locally. No dependency, workflow or deployment authority changed.
- [CI validation](https://github.com/global-soil-intelligence/gsip/actions/runs/38192685396) passed at `ca275c4`; the secret scan also passed. This supersedes the earlier pending CI note while preserving the original verification record.


### Security-boundary correction and exact-head CI (2026-10-12)

Current head: `505a0e89db3470e493af73b52b43d8fe15f3d20e`. Existing description and earlier verification records are preserved above.

Inherited change: merge-forward carries #28’s spec-first boundary clarification and #29/#31’s additive guarded-helper/invoker and restrictive-policy fixes. The owning fixes remain on WP-6b/WP-6d; this branch does not duplicate or rewrite their SQL.

The hosted Gate C zero-findings check stopped on seven findings across the service-only rights tables and client-executable public definer functions. The correction preserves authorization rather than suppressing any advisor rule. All 26 executed migration blobs remain unchanged. No new client schema, table or column grant is added; narrow EXECUTE grants on new private helpers match the existing public callers. Public signatures and caller ACLs, owner checks, withdrawal refusal and capture-closed behavior remain intact.

Local source proof preserved the existing WP-6b 99 assertions and WP-6d 209 assertions; the new owning suites passed 16 and 21 assertions respectively, with 13 new assertions failing before the changes. The candidate complete pgTAP suite passed 299 assertions, migration testing passed 13/13, and isolated synthetic PostgREST dispatch/reload/privilege tests passed 33/33. These are local proofs; hosted advisor remediation remains unexecuted.

Exact-head CI, verified 2026-10-12 14:56:50 UTC: [validate — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265400884/job/114866177248), [gitleaks — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265400802/job/114866176970). All 13 updated PR heads are green for their required checks. DCO is SKIPPED; an agent has not certified Justin’s DCO.

Assumptions: the reviewed migration owner and exposed-schema settings remain unchanged and there is no overlapping production writer; production execution must refresh these checks. Private is absent from the observed Data API exposed-schema list, but schema placement alone is not authorization. Local tests use synthetic data and do not establish the hosted advisor’s final state. Capture, sign-up and anonymous sign-in stay closed; no production mutation, deployment, new dependency, service or licence change is included in this update.


### Changes after review — owner merge exception and worker holds (2026-10-12)

Justin explicitly authorised removing the extra approving-review requirement for this owner-operated repository. Independent review, green CI, resolved conversations and protection against force pushes remain required. Agents do not submit approving reviews or certify the DCO.
Scheduled production workers now require their own explicit repository-variable opt-in; absent variables hold jobs before any secret-bearing step. Manual dispatch still requires a separate production gate. Contributor-rights schedules receive the same hold from WP-6d onward. This prevents merging workflows or adding a credential from starting unapproved production work. Regression tests failed before the relevant change and passed after it.

Assumptions: schedule opt-in variables remain unset; this merge authority does not authorise deployments, worker dispatches or capture opening. No dependencies or secret-scan exceptions were added.
