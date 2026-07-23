## Result

Native app builds now take validated CI version numbers and use the package marketing version. Android generated and compiled settings exclude private storage from cloud backup across all nine domains, allow explicitly separated direct transfer on Android 12+, and exclude legacy backup/transfer. Both platforms are built twice and keep build/comparison receipts alongside the two existing platform artifacts.

SPEC-first parent is #38. This is the already-authorized account-free APP-2A preparation; merge follows specification approval. Notifications and photo screening remain proposals. Signing inputs are placeholders for owner-controlled Viridis LLC organization accounts. iOS WebKit backup exclusion remains blocked/unverified, with options and physical-device gates documented in APP_STORE and the privacy draft.

## Invariants

Capture/production anonymous sign-in stay closed by owner instruction. I1–I15/B1–B8, private coordinate/upload/session handling, strong RLS, public anonymous agent reads, and MIT/ODbL/CC BY-SA stay intact. Existing permission and closed-SDK checks are preserved; the existing two-artifact workflow guard is not weakened. No dependency, paid/closed service, detector, notification plugin, signing account or owner keystore is added. No production command is executed.

## Validation performed

- 270 Python tests pass locally; four GDAL-dependent tests skip because GDAL is unavailable. Ruff and strict mypy pass.
- 93 app-build/permission/workflow tests pass; independent review ran 94 including the module guard. New negative controls cover canonical/bounded build numbers, duplicate/missing settings, all cloud domains, custom backup agents, effective compiled resource references, qualified aliases and unknown resource values. A qualified-alias bypass test failed before its fix and passes after.
- Lint, typecheck, 302 Vitest tests, capture-closed web/native bundles and both asset budgets pass.
- Actual first/repeated Android and iOS simulator builds pass version and unchanged permission checks; Android dependency scan passes. Independent reviewers also ran the actual APK/simulator checks.
- Same-run local Android APK bytes match exactly; iOS archive bytes differ while every non-directory ZIP entry matches. These precommit receipts explicitly show source_tree_clean=false and are supporting evidence, not final committed-source CI proof.
- Exact gitleaks 8.21.2 staged scan finds no leaks. Clean-source CI and artifact receipts will be linked when the PR run completes.

## Assumptions and remaining gates

- GitHub run_number retains this workflow identity/counter. The bounded Android→iOS mapping is injective; reruns keep the same numbers. Before workflow replacement/store upload, Justin checks store counters.
- Receipt comparison covers actual repeated builds within one job/generated project. Android shares its disposable debug key; iOS signing is disabled. ZIP-entry equality omits container/signing-block records; full archive hashes/byte equality include all bytes. No cross-runner reproducibility claim follows.
- Compiled Android rules prove configuration; synthetic physical-device cloud/legacy/transfer checks still gate a device-protection claim. Previously held backups cannot be retroactively erased.
- Current iOS WebKit storage and older backups may retain private work/account. No reliable iOS exclusion is claimed. A separately specified storage migration or approved native-language exception and physical-device evidence are required.
- A fresh install starts a new anonymous account once capture/auth are enabled; verified cloud exclusion would lose old private data on restore, while direct Android transfer may preserve it. Until in-app email linking, inaccessible old-account contributions use the privacy contact.
- GDAL and local pinned Chromium are unavailable; CI supplies their verification. Debug/simulator artifacts do not establish store readiness, signing or launch authorization. Justin reviews/merges.


## Changes after review — forward spec update (2026-10-12)

- Merged owner-requested #38 revisions forward at 82880d5, preserving both histories and the app implementation. Changes are limited to SPEC, BUILD_ORDER, PHOTO_PRIVACY_SCREENING and its policy regression tests. The photo-publication gate and sync-reminders-only v1 scope now match the updated specification.
- Kept the existing reproducibility comparison, CI version numbers and compiled backup rules. No dependency, signing input, permission weakening or production action.
- All 15 policy tests pass in the merged branch; current-head CI/native results are pending. Prior run6 evidence remains historical; no claim is made that it tested this new merge head.

Assumptions: the specification remains proposed until Justin approves and merges it; iOS backup exclusion/device evidence remains unresolved, and no account/signing/store-readiness claim is added.


## Changes after review — current-head CI closeout (2026-10-12)

- Exact reviewed head: `82880d5863cb44d3ff9b3bc9ee5d61b9d122b341`. The current-head [CI validate run](https://github.com/global-soil-intelligence/gsip/actions/runs/38248853563) completed successfully. The current-head [secret scan](https://github.com/global-soil-intelligence/gsip/actions/runs/38248853422) also completed successfully.
- [x] App build: [run 38248853443](https://github.com/global-soil-intelligence/gsip/actions/runs/38248853443) completed with Android and iOS both successful and both existing platform artifact names present.
- Artifact `gsip-capture-android-debug`: ID `11746791476`, 7,147,349 bytes, GitHub archive digest `sha256:f165f5a74bf61d0d13743c8a5a4513fae469361e556860d45bf088ce6432b6c1`. The API binds this artifact to the exact head and successful App build run above.
- Artifact `gsip-capture-ios-simulator`: ID `11747696114`, 3,324,927 bytes, GitHub archive digest `sha256:503740d9a052b2229a0b1b636827ed9d9aa2a6e269c29ed17fe277e42e0e61a3`. The API binds this artifact to the exact head and successful App build run above.
- Evidence scope: current-head CI/check and artifact-metadata readback. These new-run artifact archives have not been downloaded or independently reverified locally; the prior run 6 local artifact checks remain historical. Debug/simulator builds do not establish release signing, store readiness or verified iOS cloud-backup exclusion.
- DCO is **SKIPPED**, as shown by the current-head check. A skipped DCO job is not a passing DCO certification, and no agent Signed-off-by for Justin was added.
- This update records validation evidence only. It changes no source, dependencies, signing inputs, permissions, deployment state or merge authority.


### Security-boundary correction and exact-head CI (2026-10-12)

Current head: `d522c770c3a7fa490c6906817a7d3121842c365b`. Existing description and earlier verification records are preserved above.

Inherited change: merge-forward carries #28’s spec-first boundary clarification and #29/#31’s additive guarded-helper/invoker and restrictive-policy fixes. The owning fixes remain on WP-6b/WP-6d; this branch does not duplicate or rewrite their SQL.

The hosted Gate C zero-findings check stopped on seven findings across the service-only rights tables and client-executable public definer functions. The correction preserves authorization rather than suppressing any advisor rule. All 26 executed migration blobs remain unchanged. No new client schema, table or column grant is added; narrow EXECUTE grants on new private helpers match the existing public callers. Public signatures and caller ACLs, owner checks, withdrawal refusal and capture-closed behavior remain intact.

Local source proof preserved the existing WP-6b 99 assertions and WP-6d 209 assertions; the new owning suites passed 16 and 21 assertions respectively, with 13 new assertions failing before the changes. The candidate complete pgTAP suite passed 299 assertions, migration testing passed 13/13, and isolated synthetic PostgREST dispatch/reload/privilege tests passed 33/33. These are local proofs; hosted advisor remediation remains unexecuted.

Exact-head CI, verified 2026-10-12 14:56:50 UTC: [validate — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265400326/job/114866173955), [gitleaks — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265400260/job/114866174618). All 13 updated PR heads are green for their required checks. DCO is SKIPPED; an agent has not certified Justin’s DCO.

- [x] Current-head app-build acceptance: [run 38265400180](https://github.com/global-soil-intelligence/gsip/actions/runs/38265400180) succeeded for both platforms at `d522c770c3a7fa490c6906817a7d3121842c365b`; published artifacts: [`gsip-capture-android-debug`](https://github.com/global-soil-intelligence/gsip/actions/runs/38265400180/artifacts/11754910963) and [`gsip-capture-ios-simulator`](https://github.com/global-soil-intelligence/gsip/actions/runs/38265400180/artifacts/11754178366). The earlier same-head run 38265399090 was cancelled and superseded by this successful run.

Both bundled build receipts were downloaded and verified: clean CI checkout `b3155ee9776827a14d24cbb82284c2735d7096b5` (the PR merge commit containing this head), marketing version `0.1.0`, run number / Android versionCode `11`, iOS CFBundleVersion `1.0.10`. Independent checks of the actual downloaded APK passed compiled backup-resource and embedded-version validation; the simulator’s built Info.plist passed version validation. Android’s two same-run builds are byte-identical using one disposable debug key. iOS unsigned simulator ZIP entry contents match while full archive bytes differ. The entry comparison excludes container metadata/signing-block bytes and is not complete artifact reproducibility. Physical-device backup verification, iOS WebKit backup exclusion and owner signing remain gated.

Assumptions: the reviewed migration owner and exposed-schema settings remain unchanged and there is no overlapping production writer; production execution must refresh these checks. Private is absent from the observed Data API exposed-schema list, but schema placement alone is not authorization. Local tests use synthetic data and do not establish the hosted advisor’s final state. Capture, sign-up and anonymous sign-in stay closed; no production mutation, deployment, new dependency, service or licence change is included in this update.


### Changes after review — owner merge exception and worker holds (2026-10-12)

Justin explicitly authorised removing the extra approving-review requirement for this owner-operated repository. Independent review, green CI, resolved conversations and protection against force pushes remain required. Agents do not submit approving reviews or certify the DCO.
Scheduled production workers now require their own explicit repository-variable opt-in; absent variables hold jobs before any secret-bearing step. Manual dispatch still requires a separate production gate. Contributor-rights schedules receive the same hold from WP-6d onward. This prevents merging workflows or adding a credential from starting unapproved production work. Regression tests failed before the relevant change and passed after it.

Assumptions: schedule opt-in variables remain unset; this merge authority does not authorise deployments, worker dispatches or capture opening. No dependencies or secret-scan exceptions were added.


### Changes after review — merged-main integration

Merged predecessor histories forward and retained both sides of additive BUILD_ORDER conflicts. Remaining follow-ups are sequenced after the merged WP-3b package so current-head CI tests their combined content. The scoped owner merge exception is reflected consistently; deployment and photo-publication gates remain unchanged. Combined local verification: 98 workflow, coding-guidance, specification and app-build tests passed; Ruff and affected formatting passed. No dependency or secret-scan policy changed.

Assumption: each predecessor will merge before this PR is retargeted to main; no protection or production gate is bypassed.
