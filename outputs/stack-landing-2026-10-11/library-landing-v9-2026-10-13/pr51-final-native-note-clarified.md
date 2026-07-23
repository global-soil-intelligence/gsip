WP-LIB-4C connects optional phone sample drafts to the owner-private intake in SPEC §16.8 and LIB-4A/B. Depth/condition and one bounded strict instrument declaration survive restart and stay bound to stable submission/sample/intake IDs. Legacy queues keep their existing capture path without invented library metadata.

Invariants: I1–I15, B1–B8 and L1–L7 preserved. VITE_LIBRARY_INTAKE_LIVE defaults false, with capture independently closed. Default builds render the established form and send no new library RPC. Capability absence/incompatibility holds a library record before anonymous sign-in or partial capture. The existing capture query remains unchanged. Native and Pages packaging verify a two-flag closed activation receipt.

Queue completion requires matching stored_private_unverified/already_stored receipt after the existing grant/submission/photos/finalize stages. Lost responses retain exact IDs/context/bytes and durable checkpoints; temporary activation holds consume no retry attempts. Namespace/account binding prevents silent cross-account reassignment. Conflicts are retained for explicit discard; only confirmed WD001 withdrawal auto-removes covered queued data. Clear/withdraw/account deletion erase drafts and declarations with generation/cross-tab fencing.

Validation: independent exact24-file review found no blocker, with60 scoped app tests and53 artifact-policy tests passing. Root combined suite424 web tests and455 Python tests passed (four GDAL skips), plus full lint/typecheck/Ruff/mypy51 files, normal web and app asset builds, map/site budgets. Built activation receipt has capture_live=false and library_intake_live=false. Full-history gitleaks8.21.2 scanned123 commits and found no leaks with only the three approved historical fingerprints. Hosted CI and compiled APK/simulator artifacts pending; no local Android SDK/Xcode or real-device backup proof.

## Changes after review

- Unify camera/file-picker intent ordering so a delayed earlier capture cannot overwrite a newer selected image; bidirectional race regressions pass.
- Clear local covered drafts after any confirmed deletion outcome, including already_open on another device; uncertain server responses still preserve data.
- Reserve the namespace's authoritative owner atomically before fallback checkpointing, preventing concurrent drains from assigning it to different accounts.
- Conditional catch-branch writes and completed-record/generation fences prevent discarded drafts or completed queue records from being resurrected.
- Keep immutable conflicts held with their original IDs and bytes; provide explicit discard rather than silent UUID replacement or data loss.

Assumptions:
- A private receipt proves storage of declarations only, without source/calibration/pairing, QA, consent certification or scientific eligibility.
- Android blanket WebView/photo cloud-backup exclusions cover the added IndexedDB stores; direct device transfer policy remains as approved. iOS WebKit backup exclusion still requires real-device proof and is not claimed here.
- Default app/Pages artifacts must remain closed despite ambient environment variables. Activation is a later separately authorized package/deployment after launch gates.
- Original imported files outside GSIP storage and disconnected-device copies remain outside this app's erasure control.
- Version1 has no node federation, same-sample recapture or account transfer. Returning to original account or local discard is required for held library records.
- Justin authorizes ordered merges after independent review and green CI; no production deployment, worker dispatch, account creation or capture/auth opening is authorized. No dependency or new paid/closed service.

Authored by Codex for human of record Justin Hart; no agent DCO certification or approving GitHub review.


### Browser CI packaging correction

The initial CI run correctly rejected the existing Playwright configuration: it tried to package a synthetic capture-live build as Pages. Commit `bb9bd8a` keeps the Pages activation guard unchanged and builds the deployable `_site` with both flags false. A test-only Python server builds mock capture into a temporary directory, serves that route on loopback with fixed `.test` endpoints, discards inherited build activation/connection variables, refuses stale-server reuse and cleans the temporary fixture on exit. Nothing copies mock capture into Pages or native artifacts. Eight new unit/mock regressions passed; the combined harness/native-policy suite passed 61 tests, and lint, types, Ruff and mypy passed. Local live-fixture execution remains held by the earlier automatic approval rejection; CI will run the browser suite. Assumption: this isolated synthetic CI harness does not authorize any production capture or publication. Independent review and fresh exact-head CI remain required before merge.


### Final harness placement and current holds

CI ran the isolated browser harness: all 12 desktop browser checks now pass, including the public site's closed-capture label and launch-status link. Its processor-host audit then correctly flagged the test-only server when it lived under production scripts. The server now lives under test sources; the production-host audit remains unchanged. Local harness/processor regressions passed 14 tests and mypy passed 53 source files. The fixture placeholder cleanup and test-only move have been merged forward to this branch without rewriting history. Independent harness and specification reviews found no code/architecture blocker. Fresh complete CI remains required.

The current full-history gitleaks 8.21.2 finding is exactly `bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32`, a historical noncredential browser placeholder. The current edited fixture scans clean. No ignore entry or scanner change has been applied; Justin's explicit approval for this single additional historical fingerprint is pending, so all further merges are held.

### Verified CI and remaining merge hold (2026-10-13)

At exact head `14c4188280025c274ac7c58d1fc40138ee3922bb`, [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38342977588) is successful, and [Android/iOS app-build](https://github.com/global-soil-intelligence/gsip/actions/runs/38342977592) is successful. API readback verified nonempty, unexpired artifacts tied to this exact head: Android debug APK archive 7,220,048 bytes and iOS simulator archive 3,383,660 bytes.

- [x] app-build: APK and iOS simulator artifacts exist in the linked successful run.

The two full-history gitleaks checks remain failed solely for the historical synthetic fingerprint above. No additional suppression has been applied; this PR is held for Justin's explicit exception decision. Passing build checks do not authorize production deployment or capture opening.

## Changes after review — owner-approved exact historical fixture exception (2026-10-13)

Justin explicitly approved only the exact historical noncredential browser-fixture fingerprint `bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32`. Commit `173e19363df60d029b2ffeb4a7df2e27d6ccd6b6` on the owning LIB-4C branch preserves the original four ignore lines and adds that single entry, with the approval recorded in AGENTS. It was merged forward through the ordered stack without force, rebase or history rewrite. The current test fixture was already cleaned forward; a new matching commit remains a failure. Detection rules, scanner configuration/workflow, redaction and history coverage are unchanged.

Before/after pinned gitleaks 8.21.2 whole-stack runs reproduced the exact one finding and then zero findings. The fresh scan after forward commits also reports zero. Independent narrow exception review passed (receipt SHA256 `258c1db45a803cfcac81b7234593df8a12f43f017496870f89e2d10f6ad23ef3`). Exact-head CI is being read back before merge; no previous-head pass is used as a new-head pass.

Assumptions: this approval covers only the named immutable fingerprint; every further suppression still requires explicit owner approval. No dependency/licence or runtime behavior change is introduced by this exception. Source merge authority does not authorize production deployments, worker dispatch, peer sharing or capture opening. Existing PR text is preserved.

## Verification — owner-approved ordered merge completed

Exact head `173e19363df60d029b2ffeb4a7df2e27d6ccd6b6` passed all listed checks before merge; DCO was skipped under the unchanged same-repository policy. Validate evidence: [run](https://github.com/global-soil-intelligence/gsip/actions/runs/38390370455). Merge commit `5a26ca2f1cb47233b8d82228d96d4df0aea9a4b3` uses a Conventional Commit subject and the Codex co-author trailer. No agent approving review, bypass, force-push, history rewrite, production change or capture opening occurred.

- [x] App-build acceptance: [exact-head Android APK and iOS simulator run](https://github.com/global-soil-intelligence/gsip/actions/runs/38390370143); both artifacts are unexpired and nonempty. The canceled overlapping run was genuinely rerun, not excluded. Simulator evidence does not prove real-device backup behavior.

## Native acceptance note clarification

The overlapping-run cancellation/rerun note above pertains to PR #53. PR #51's linked exact-head native run passed both platforms without a rerun. The artifact sizes, head bindings and acceptance evidence remain correct.
