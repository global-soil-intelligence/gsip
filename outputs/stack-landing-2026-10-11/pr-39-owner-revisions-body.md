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
