## Problem and result

The draft privacy notice still left the map tile host undecided. WP-SITE-1E records Justin's conditional choice of repository-owned, same-origin GitHub Pages, updates the runbook and adds `docs/PRIOR_TILE_HOSTING.md`. ISRIC WMS remains the active fallback.

## Invariants and acceptance

- [x] Only SoilGrids-derived values enter prior archives; no contributor data or photos.
- [x] Tiles never enter git history; palette-version release assets are assembled into Pages at deploy time.
- [x] Tile target <=700 MB; complete site well below 1 GB; actual archive URLs must answer ranges with 206 and correct bytes.
- [x] No release, variable, host activation or Pages publication is authorized by destination approval.
- [x] Draft privacy-host disclosure and separate preparation/publication/activation evidence are documented.

## Verification

Six processor/privacy tests, targeted Ruff/mypy, terminology, changed-document Prettier and diff checks passed. New disclosure assertions failed without the update; ten local hosting links resolve. PR CI is pending.

Assumptions and limits: this is a documented hosting policy, not implemented release retrieval or asset assembly. No archives were built; size, byte-range support and published provenance remain unverified. Counsel approval of the legal pack and Justin's per-step publication go remain required.

## Authority and assumptions

- Justin Hart is product owner and human of record; Codex wrote this follow-up. Justin reviews and merges. No merge, approval, deployment or capture opening occurred.
- This PR starts from green WP-APP-1 head `f9e1ac2` and stays stacked there until the reviewed stack merges. Existing reviewed commits are preserved.
- Capture and production anonymous sign-in stay closed. I5, I7, I12 and B1–B8 remain binding. MIT code, ODbL 1.0 data and CC BY-SA 4.0 photos are unchanged. No dependency added.


## Changes after review
### Security-boundary correction and exact-head CI (2026-10-12)

Current head: `a325c617d3e06cbb4fe5eb6cbbb7c913f493e87f`. Existing description and earlier verification records are preserved above.

Inherited change: merge-forward carries #28’s spec-first boundary clarification and #29/#31’s additive guarded-helper/invoker and restrictive-policy fixes. The owning fixes remain on WP-6b/WP-6d; this branch does not duplicate or rewrite their SQL.

The hosted Gate C zero-findings check stopped on seven findings across the service-only rights tables and client-executable public definer functions. The correction preserves authorization rather than suppressing any advisor rule. All 26 executed migration blobs remain unchanged. No new client schema, table or column grant is added; narrow EXECUTE grants on new private helpers match the existing public callers. Public signatures and caller ACLs, owner checks, withdrawal refusal and capture-closed behavior remain intact.

Local source proof preserved the existing WP-6b 99 assertions and WP-6d 209 assertions; the new owning suites passed 16 and 21 assertions respectively, with 13 new assertions failing before the changes. The candidate complete pgTAP suite passed 299 assertions, migration testing passed 13/13, and isolated synthetic PostgREST dispatch/reload/privilege tests passed 33/33. These are local proofs; hosted advisor remediation remains unexecuted.

Exact-head CI, verified 2026-10-12 14:56:50 UTC: [validate — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265398972/job/114866169822), [gitleaks — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265402656/job/114866182054). All 13 updated PR heads are green for their required checks. DCO is SKIPPED; an agent has not certified Justin’s DCO.

Assumptions: the reviewed migration owner and exposed-schema settings remain unchanged and there is no overlapping production writer; production execution must refresh these checks. Private is absent from the observed Data API exposed-schema list, but schema placement alone is not authorization. Local tests use synthetic data and do not establish the hosted advisor’s final state. Capture, sign-up and anonymous sign-in stay closed; no production mutation, deployment, new dependency, service or licence change is included in this update.


### Changes after review — owner merge exception and worker holds (2026-10-12)

Justin explicitly authorised removing the extra approving-review requirement for this owner-operated repository. Independent review, green CI, resolved conversations and protection against force pushes remain required. Agents do not submit approving reviews or certify the DCO.
Scheduled production workers now require their own explicit repository-variable opt-in; absent variables hold jobs before any secret-bearing step. Manual dispatch still requires a separate production gate. Contributor-rights schedules receive the same hold from WP-6d onward. This prevents merging workflows or adding a credential from starting unapproved production work. Regression tests failed before the relevant change and passed after it.

Assumptions: schedule opt-in variables remain unset; this merge authority does not authorise deployments, worker dispatches or capture opening. No dependencies or secret-scan exceptions were added.
