# GSIP current landing and deployment report

Phase 1 is complete: seven reviewed stacked PRs are open and current validation/secret checks succeed. The phone-app Android and iOS simulator artifacts exist, and its app-build acceptance box links the successful current-head run. Justin reviews and merges; no PR was merged or approved by an agent.

## Reviewed stack

| PR | Branch | Head | Checks |
| --- | --- | --- | --- |
| [#28](https://github.com/global-soil-intelligence/gsip/pull/28) | docs/spec-v3 | afadda9 | validate / gitleaks SUCCESS |
| [#29](https://github.com/global-soil-intelligence/gsip/pull/29) | wp-6b-launch-hardening | 273e768 | validate / gitleaks SUCCESS |
| [#30](https://github.com/global-soil-intelligence/gsip/pull/30) | wp-6c-priors-and-tiles | a66c4f2 | validate / gitleaks SUCCESS |
| [#31](https://github.com/global-soil-intelligence/gsip/pull/31) | wp-6d-contributor-rights | f3c7043 | validate / gitleaks SUCCESS |
| [#32](https://github.com/global-soil-intelligence/gsip/pull/32) | wp-6e-provenance | 4f76145 | validate / gitleaks SUCCESS |
| [#33](https://github.com/global-soil-intelligence/gsip/pull/33) | wp-agent-1-read-api | 5e50028 | validate / gitleaks SUCCESS |
| [#34](https://github.com/global-soil-intelligence/gsip/pull/34) | wp-app-1-phone-app | f9e1ac2 | validate / gitleaks / Android / iOS SUCCESS |

Same-repository DCO checks are skipped by policy; no Justin sign-off was added. A cancelled superseded app run remains visible beside the successful replacement. #20–22 were already closed, #24 merged. Live readback: `current-reviewed-stack-readback.json`; exact successful jobs: `approved-fix-ci-results.json`.

## Changes after review

1. `afadda988cb8619d4f3a98515629909ca761763f` on docs/spec-v3 adds Justin's exact four-line `.gitleaksignore`, with only three approved historical synthetic-fixture fingerprints, then merges forward through all seven branches. The reason is recorded under Changes after review in #28 and #33: CI scans every branch, so every branch needs the same file. No rules, `.gitleaks.toml`, redaction, full-history scan or scanner workflow changed. No further suppression was added.
2. `5e500287b2caa8990d2d658c8c8e100cccae0e21` on WP-AGENT-1 removes new scanner matches from three synthetic test values without changing assertions. Secret-format refusal and privileged-role rejection remain tested. Sixteen targeted tests, typecheck, lint and formatting passed. Merged forward to WP-APP-1.
3. Approved app commit `94e19ff7fa06a8b284165d57e612c1bda86ce4c8` resolves the macOS case-insensitive MySoil module collision by renaming the unchanged component and updating two imports, with a failing-before/passing-after module-case regression test. Recorded under Changes after review in #34. No dependency added or permission/dependency check weakened.

All original reviewed commits remain ancestors. The ignore file has exactly 383 bytes / four LF lines, SHA-256 `da6c9aacdea6441282a5bbd70c37111e592e38d45cea08eeaac8964f5560d288`. The proposal was replaced with those exact bytes.

## Required scanner proof

Actual binary version: gitleaks **8.21.2**. Full reviewed-stack command:

```sh
gitleaks git . --no-banner --redact --log-opts=--all
```

Result: **69 commits scanned, no leaks found, exit 0**, with only the three entries. The unchanged CI command also scans 69 commits and exits 0. `approved-fixture-fix-evidence.json` contains commands, redacted output, exact file/head/rule/workflow audits and assertion evidence. After importing the first follow-ups and explicit I5 guide correction, the whole clone scans **74 commits, no leaks found, exit 0** (`gitleaks-8212-followup-whole-stack.json`). The latest whole clone, including all follow-ups and the reconciliation PR, scans **79 commits, no leaks found, exit 0**, again with the same exact ignore file (`gitleaks-8212-current-whole-stack.json`). No secret or real contributor coordinate appears in these receipts.

## Phone artifacts

[App build 38189449982](https://github.com/global-soil-intelligence/gsip/actions/runs/38189449982), at f9e1ac2, succeeds for both platforms. Android artifact 11720633194 is 7,144,211 bytes; iOS simulator artifact 11720817326 is 3,323,675 bytes; neither expired at readback. #34's app-build acceptance box links this run. `approved-fix-app-artifacts.json` captures the current head and jobs. Simulator/debug outputs do not prove signing, store acceptance or device backup protection.

## Deployment checklist

| Runbook step | State | Evidence / next action |
| --- | --- | --- |
| Governing v3 documents and targets | DONE | Verified immutable handoff and original heads before import; v3 read from the reviewed branch. Target is toxldjgwkxtneoqsazym, gsip, us-east-1. |
| Disposable migration test | DONE | Current approved stack ran `scripts/db-migration-test.sh` in PostgreSQL/PostGIS/pgTAP Docker with network disabled and read-only checkout: **13/13 ok, exit 0**. Receipt: `local-migration-test-approved-stack.json`. |
| Restore and CLI authentication | DONE EXTERNALLY | target reports ACTIVE_HEALTHY, and existing CLI login can list history. Agent did not restore or perform login. Readiness grants no migration/deployment go. |
| Pre-migration counts and plan | DONE; REPAIR GO REQUIRED | Independently confirmed owner counts: 5 contributors, 25 submissions, 25 photos, 0 auth users, 0 public cells; all 52 base tables counted. Thirteen baseline timestamps differ. Owner identifies accidental Wavefunction migration/function; both foreign tables independently confirmed absent. Strict current-catalog comparison passes except six exact ownership aliases and explicitly preserved platform metadata. |
| Database migration | STOPPED ON PREFLIGHT MISMATCH | Justin approved A then B, but fresh realtime.schema_migrations count changed 81→89. All other51 counts and all18 GSIP ledger records/catalog fields match. No repair/deletion ran; accepting the new platform baseline needs a scoped go before resumption. Nine October migrations and new sign-up closure remain separately unapproved. |
| Security / capture / anonymous-auth readback | BLOCKED | Security advisor now returns lints=[]; all public tables have RLS. service_state does not yet exist, so capture_open=false cannot be read back before migration. Anonymous sign-in is now verified disabled on the exact project Auth providers page (switch 0, Save changes disabled). No settings changed. |
| Edge Functions and smoke tests | BLOCKED / GO REQUIRED | prior-attach JWT on; gsip-public JWT off. No deployment. Afterwards test protocol 200, resolution-9 cell 400 and MCP four tools. |
| Repository variables and service key | BLOCKED | Set SUPABASE_URL, publishable key, GSIP_PUBLIC_API; remove legacy VITE_SUPABASE_URL only after readiness/go. Justin supplies service-role secret through store; no secret printed or pasted. |
| Contributor-rights worker / photo QA | BLOCKED | No dispatch; database/functions/public configuration required first. |
| HF export | JUSTIN ACTION | Create global-soil-intelligence/gsip and set HF_TOKEN/HF_DATASET_REPO. Fallback viridis-research/gsip. No export until ready. |
| Tiles | POLICY PREPARED; BUILD/PUBLISH BLOCKED | #37 documents same-origin GitHub Pages, palette-version release assets, no tiles in git, <=700MB target, site <1GB, SoilGrids-only and 206 Range proof. Release assembly not yet implemented; no tiles built/published. ISRIC WMS remains fallback. |
| Pages | BLOCKED / GO REQUIRED | Closed local build verified. Production configuration, packaged tiles if enabled and explicit deploy go required; no production deployment by agent. Check prerender/llms.txt after deployment. |
| validate required check / DNS / counsel / CAPTCHA / tier / capture | JUSTIN ACTION | Require validate; WP-SITE-1D DNS cutover; counsel legal URLs; decide CAPTCHA and paid tier before launch; capture/anonymous opening only after every section 11 gate. |

Read-only preflight commands executed against the selected target (list succeeds; push dry-run fails before any migration):

```sh
pnpm exec supabase migration list --project-ref toxldjgwkxtneoqsazym
pnpm exec supabase db push --project-ref toxldjgwkxtneoqsazym --skip-vault --dry-run
```

The installed CLI 2.118.0 ran these commands via node_modules/.bin/supabase. CLI preflight initialized a temporary login role. The dry run returned DbPushMissingLocalError and suggested history repair; that suggestion was not executed. Actual migration/deployment commands await a concrete reconciled inventory and separate go. Never use production db reset.

**Merge-time deployment gate:** the existing Pages workflow deploys on pushes to main, and the GitHub Pages environment has no required-reviewer gate. Justin must reconcile this with the per-deployment go requirement before merging. No workflow/environment policy was weakened or changed.

## Independent follow-ups

| PR | Work | Current state |
| --- | --- | --- |
| [#35](https://github.com/global-soil-intelligence/gsip/pull/35) | WP-3B cross-tab queue lock | Five concurrency/fallback tests; full local web checks pass. CI validation/secret scanning/native builds succeed, artifacts present. |
| [#36](https://github.com/global-soil-intelligence/gsip/pull/36) | WP-AGENT-0 root coding guide | Commands, guardrails and API-guide link; guide usability tests. Forward explicit I5 wording plus failing-before regression test at ca275c4; Changes after review appended; validation and secret scanning succeed. |
| [#37](https://github.com/global-soil-intelligence/gsip/pull/37) | WP-SITE-1E tile-host policy | Privacy/runbook/hosting gates documented, processor contract tests; CI validation/secret scanning succeed. |
| [#38](https://github.com/global-soil-intelligence/gsip/pull/38) | Revised proposed spec v4 | Owner revisions at bc1a293: §11 data-only photo gate; bounded card-only text exception; face/scene-text first; v1 sync reminders only. 15 local policy tests pass; new-head secret scans pass and validation is pending. |
| [#39](https://github.com/global-soil-intelligence/gsip/pull/39) | WP-APP-2A build readiness | Revised spec merged forward at 82880d5. 15 local policy tests pass; new-head validation/native CI pending, secret scans pass. Prior c646724 native evidence remains historical; app code, versions, comparison and backup rules are unchanged. iOS exclusion/device proof remains blocked. |
| [#40](https://github.com/global-soil-intelligence/gsip/pull/40) | WP-OPS-2 reconciliation | Current head cf063aa: validate and both secret scans SUCCESS. Strict metadata comparator: 51 focused tests; isolated rehearsal: 64/64 assertions. Owner-private backup restoration matches 18/18 complete records. Exact history/function commands are posted for separate Gate A/B approvals; neither has run. |

Follow-up receipts: `followup-ci-results.json`. Notifications and photo screening remain proposals. WP-6f implementation stops until Justin approves and merges #38; unresolved plate-weight licensing/category coverage and calibration are further gates.

## Open owner actions and recommendation

- Owner context for the foreign migration is resolved: accidental separate Wavefunction beta deployment. Review WP-OPS-2, the full original ledger is now preserved/restored privately; separately authorize its exact history repair and one-function deletion. No foreign source is imported and no production go has been given.
- Review/merge the stack in order; no agent merges/approves. Ensure a protected Pages deployment gate before main pushes.
- Review #38 before screening implementation. Recommended detector direction: benchmark explicitly licensed open face/text candidates, keep uncleared photos private and do not select plate weights without a verified license.
- iOS backup method remains a technical decision: separately specify migration into an existing no-cloud filesystem store, or consider an explicit native-language exception with physical-device proof. Keep iOS readiness blocked until reliable evidence exists.
- Create the chosen HF destination/secrets when ready. Keep WMS until tile size/provenance/range proof and separate publication go.
- Owner-controlled Viridis store accounts/signing remain deferred; no store signing certificate or owner keystore was created. CI debug builds use disposable Gradle signing keys. Counsel, DNS, CAPTCHA and paid tier remain launch gates. Continue keeping capture/anonymous auth closed.
- No new paid/closed service or licence change is requested. The three-fingerprint exception is fulfilled; any further suppression requires explicit approval.

## Assumptions and verification limits

- Immutable handoff heads are authoritative; original history and existing workspace changes remain preserved.
- Production catalog readbacks are counts, migration digests and security metadata only. A separate owner-private ledger recovery copy includes original schema/history fields, without application/auth/Vault/Storage rows; its contents are kept outside Git and public receipts. Advisor is clean; capture-gate table is absent; anonymous sign-in is independently verified disabled in the target-bound dashboard readback. CLI preflight initialized a temporary login role; no production application migration, row update, history repair, project restore, auth-setting change or deployment occurred.
- CI results are attributed to exact heads/jobs. Required-check branch protection is an owner action, distinct from all checks succeeding.
- Local GDAL, Deno and PostgreSQL command binaries are absent from PATH; Docker supplied the isolated migration test, and CI supplied GDAL/Deno/full database checks. Local pinned Chromium executable is missing; browser results are CI evidence. Android SDK and Xcode are available; simulator builds do not replace physical-device evidence.
- Prescribed Playwright harness uses a local mock capture-live site; no such artifact was published, and the deployable local Pages artifact was rebuilt with VITE_CAPTURE_LIVE=false.
- A fresh install/cloud restore starts a new anonymous account; proven direct Android transfer may preserve it. Old contributions use the privacy contact until in-app email linking.

## Production inventory and unresolved history

Counts-only receipts: `production-complete-counts-and-comparison.json` includes all 52 non-system base tables. Public contributors and contribution_grants: 5 each; submissions, photos, prior_jobs and qa_jobs: 25 each; public gold_labels, h3_cells, predictions, priors and qa_events: 0. auth.users/sessions/identities and storage.objects: 0. No classification as real/synthetic is inferred from counts.

Independent statement digests establish eleven byte/outer-whitespace matches. Justin reports fourteen historical files differ only in comments/whitespace; that complete comment-normalized comparison is owner-supplied, not independently established by digest equality. The effective seventeen-migration baseline was independently reconstructed in PostgreSQL17.6 with no production rows/credentials. All table/column/constraint/index/trigger/public-private-function hash/grant and Storage-policy fields match after only six exact bound SQL-alias substitutions, plus three preserved platform extensions and three preserved platform schema grants. Public views are absent on both baselines. Nine independent negative controls reject weakened privacy protections (`canonical-production-equivalence-proof.json`); the checked-in helper has51 focused tests, including owners and function grantability. Full local Python suite271passed/4GDALskipped; Ruff/mypy37files pass. The cumulative reviewed repository chain is authoritative for subsequent changes; no baseline DDL replay is proposed. A network-none Docker rehearsal passed64/64 assertions, preserving application/catalog/sentinel data through modeled ledger repair and applying exactly nine pending migrations afterward. The local post-upgrade reference has capture_open=false; this is distinct from the absent live service_state table. Rehearsal models ledger insert/delete effects, with repository Auth/Storage stand-ins; no Supabase CLI repair or production migration ran.

The photo-QA historical SHA matches Git commit969076a394aef4af8c65b55a664001b68fc2bfa6; current code adds only IF NOT EXISTS to submissions.gps_accuracy_m (nullable REAL with validated nonnegative check). This effective definition matches production. The other two substantive historical files converge to the same cumulative schema/security state; source-digest difference is not ignored or misreported as byte equality. Foreign table absence: `production-foreign-table-absence.json`.

WP-APP-2A native evidence: `app-2a-pr39-run38192835277/verification.json`. Clean CI checkout merge2aab581c7b06960613436402f8115e7ab6b13b4d has PR headc646724 as parent. Run number6 produces marketing0.1.0, Androidversion6, iOS1.0.5. Androidartifact11722457181 (7,147,388 bytes), iOSartifact11722566280 (3,324,822 bytes). Actual payload hashes, compiled permissions/backup resources and receipt source cleanliness were independently verified. Android repeated APK bytes match; iOS archive bytes differ but entry payloads match. Neither proves signed-store or cross-run reproducibility. Android private cloud data is excluded; permitted modern direct transfer still needs physical proof. iOS exclusion implementation/device verification remains a recorded gate.

This report supersedes the pending-exception state in the preserved historical `REPORT.md`.

Private recovery evidence: production-history-backup-restoration-receipt.json SHA-2562ba73397813a74de66cb37cd6911580c6143ee8f1281064d6444cbe1f9f7642e. Owner-private permanent backup directory is /Users/justinhart/.supabase/gsip-recovery/2026-10-11, mode0700/files0600. Restore checks18/18 complete arrays and all six metadata fields, one user table/zero user functions; recorded foreign SQL stays inert; container removed. Private backup secret scan8.21.2 passes0findings with no suppression. A naive local structural-summary diagnostic briefly emitted partial historical SQL tokens; it was corrected before the restore, no contributor rows were dumped, and those fragments are not reused in public receipts or PRs.

Latest exact-head PR readback: `current-all-pr-readback.json` covers all thirteen open PRs. PR #40 current-head validation run [38195739800](https://github.com/global-soil-intelligence/gsip/actions/runs/38195739800) succeeds; sanitized status receipt SHA-256 `c8297ef2fddb41af43960445adf96aebb61c3f96a1f4e5383a5c8e84576b9539`. DCO is skipped by the existing same-repository policy. The original workspace remains on wp-site-public-hub; its 61-entry status digest, excluding task outputs, still matches `9f267c791a56dbfe1cbdb8f104cec8dcaa9bc912d2b8c7cfde757ce5dab63419`. Supabase CLI version was freshly verified as 2.118.0.

Preapproval production refresh: **PASS_NO_DRIFT**. All 52 count/table identities, eighteen complete history-row hashes and both schema catalogs match the bound evidence. Security advisor still reports zero findings; strict comparator at cf063aa exits 0 with no unexpected differences. Function count/name/version/JWT fields remain prior-attach v3/on and wavefunction-api v2/on, with gsip-public absent; unrelated function metadata has no prior full-receipt comparison. Private backup hashes remain unchanged. Receipt: `production-preapproval-refresh.json`, SHA-256 `fed89943b3e3e6f1366707234b95e270ad44ee3acef83c765a1f51bb52d5bc2c`. Gate A history repair and Gate B function deletion are awaiting separate explicit approvals.

Latest anonymous-auth readback: **VERIFIED_DISABLED**, exact target toxldjgwkxtneoqsazym, Sign In / Providers page. Allow anonymous sign-ins switch value 0; Save changes disabled. No toggle/save/authentication/restore/settings mutation, secret page access or screenshot. Receipt: `production-anonymous-auth-browser-readback.json`, SHA-256 `a4a543dd48dfc19abe48fd6a9df662abc208196dd627de344d95a07afdbed72e`. This supersedes the earlier unavailable readback and the unverified state recorded when PR #40 source was prepared. Live service_state remains absent until separately approved migrations.

Human-readable per-table counts for all 52 tables: [production-table-counts-before-go.md](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/production-table-counts-before-go.md>). This contains aggregate counts only and is bound to the fresh production receipt.

## 2026-10-12 authorized execution attempt and strict stop

Justin authorized the three Gate A history commands with readback18→31→18→17, then Gate B deletion only after A verifies. Fresh preflight discovered realtime.schema_migrations81→89; the other51 counts, all18 complete GSIP history hashes, primary/supplement catalogs, intended function metadata and private backup modes/hashes match. Eight current records have insertion timestamps after the prior02:37:04UTCreadback, at02:45:02–02:45:03UTC. There is no prior identity snapshot proving which exact identities were added, and actual DDL execution/cause remains unknown. **Stopped before any repair or deletion.** The acceptance question for platform baseline89 is pending; original authorization is not silently broadened. Receipts: production-preflight-approved-2026-10-12.json (SHA220f01b588ce73f5998eda66cf6d9cab1c6a48c7fb347b9602f07693238e7775) and platform-ledger-drift-investigation-2026-10-12.json (SHAc42f4cc50ef6823dac378a70f518c5311863cf1df2113aecec069faf0a70b676).

Docker Desktop was initially stopped; both disposable runs failed before assertions. After starting the installed local engine, fresh required migration test passes13/13 and rehearsal64/64; the rehearsal result hash remains4080346f1d0935d3bc93a428df227eaf7380450f03be7c2e1e1dcd6591372cef. Prior receipts were preserved. No production data/credentials/network were used.

Pages environment was changed through the authorized API: sole required reviewer JustinHart/jdhart81/user179389866, with main/gh-pages restrictions preserved. Admin bypass remains enabled; supported REST/GraphQL input has no setter. **Before any merge, Justin must deselect Allow administrators to bypass configured protection rules in Settings→Environments→github-pages and save.** Receipt pages-required-reviewer-api-receipt.json SHA4450ded0da9fca596c6e18eb0fd50763dfa7d4b76340ef11747ce751b00cb256. This is a GitHub protection change, not a Pages deployment.

Fresh Auth provider UI confirms anonymous sign-in0/off, new-user signup1/on, Email ENABLED and Confirm email1/on, with Save disabled. The July baseline allows authenticated capture writes without the October capture gate; exposure is inferred from source/config, not exercised with any signup/write test. A narrow separate signup-only go is pending: switch only Allow new users to sign up off, save once, reload; preserve other settings. No Auth setting changed. Receipt production-email-signup-browser-readback-2026-10-12.json SHAea4f307348bc02e0678e35030baeb70677517594bec10cff9667a81b75a247e8 and prepared production-auth-signup-closure-plan-2026-10-12.json SHAc518741c22f88cfcb0b4cce94ec7ec84396b717c6727ced7d56b465a595c2b0d. Gate C database migration remains unapproved.

SPEC revisions in #38 now include all four owner requests, with coordinated BUILD_ORDER/privacy-plan text and15 regression tests (13 failed before edits). Local full Python235passed/4GDALskipped; initial HF cache permission failures resolved using a private temporary cache. No dependencies/models/plugins or screening implementation were added. APP2A comparison retained. #39 inherits the revised spec with only these four documentation/test files changed. Original PR bodies remain preserved with appendices. Photo-capable QA/export dispatch must stay blocked until the proposed data-only/photo-publication gate is actually enforced; the spec change itself does not enforce it.
