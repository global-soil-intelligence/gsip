# GSIP landing and build report — 2026-10-13, 18:59 UTC

The requested #51–#56 stack is merged in order after independent review and exact-head green CI. The authorized LIB-5A contracts (#58), local-accounting specification (#60) and synthetic local ledger/rights rehearsal (#64) are also merged. Main is `710d144db94097be71989c67b5d3b4bb48135ad8`. APP-2B reminders remain draft #63 at new exact head `d74ba2add9ce9bb5494be60c5f11883d3f5137ef`: both narrow build-evidence repairs passed independent review and root checks and are pushed; general CI and iOS passed, but Android failed its runtime inspection and remains unmerged. The preceding heads’ failures remain preserved. No production change, deployment, capture opening, approving GitHub review, protection bypass, history rewrite or human DCO certification occurred in this continuation.

## Merged PRs and check evidence

| PR | Check status before merge | Merge commit |
| --- | --- | --- |
| [#51](https://github.com/global-soil-intelligence/gsip/pull/51) | Green; native artifacts verified | `5a26ca2f1cb47233b8d82228d96d4df0aea9a4b3` |
| [#52](https://github.com/global-soil-intelligence/gsip/pull/52) | Green | `ffd056dc506911a1a60541ceb2eedc668b7d1576` |
| [#53](https://github.com/global-soil-intelligence/gsip/pull/53) | Green; same-head native rerun/artifacts verified | `1dc380a16f8d6494f20ac59901a5347e2f31b64a` |
| [#54](https://github.com/global-soil-intelligence/gsip/pull/54) | Green | `9a51ec4564358068d1ba245455f6f5d3ea68f286` |
| [#55](https://github.com/global-soil-intelligence/gsip/pull/55) | Green | `c804e1516ccb29c3f2535bc0a685ab1a907a32fe` |
| [#56](https://github.com/global-soil-intelligence/gsip/pull/56) | Green | `1d105bde4d009403d114c844c52d5bf6aaf4565e` |
| [#58](https://github.com/global-soil-intelligence/gsip/pull/58) | Green; native artifacts verified | `333f1492713d41c0ade42d6b16c4453cdfb1b783` |
| [#60](https://github.com/global-soil-intelligence/gsip/pull/60) | Green | `d7ed716ed0921381da04f542e90902ede36cb462` |
| [#64](https://github.com/global-soil-intelligence/gsip/pull/64) | Green; full independent 33-card review | `710d144db94097be71989c67b5d3b4bb48135ad8` |

DCO skipped under the unchanged same-repository policy; it is not reported as a human certification. [Six-PR check register](ALL_GREEN_BEFORE_ORDERED_MERGES.json), [ordered merge register](ORDERED_MERGE_REGISTER.json). #58 [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38398436566) actually passed 881 Python tests with GDAL, 12 browser tests, 593 database assertions and configured migration/Deno/static/build checks. Its [native run](https://github.com/global-soil-intelligence/gsip/actions/runs/38398436463) produced APK 7,221,644 bytes and simulator 3,385,561 bytes at exact head f07a876; artifact/configuration evidence does not prove physical-device protection. #60 [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38399279214) passed at exact source 59044d3.

Current main [CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38443032588) and [secret scan](https://github.com/global-soil-intelligence/gsip/actions/runs/38443032236) passed at 710d144. [Pages](https://github.com/global-soil-intelligence/gsip/actions/runs/38443032217) remains waiting for Justin’s approval. Waiting is not deployed or green; no approval was given.

#64 [CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38440865646) passed at exact reviewed source `7934aaa8b729e42ce373977cabfd9f18e5784c18`: 1,136 Python with required GDAL/zero skips, 529 JavaScript, 12 browser, 593 pgTAP assertions/11 files, Deno and existing-data migration compatibility. Both push/PR gitleaks passed; DCO skipped under unchanged policy. [Independent terminal CI receipt](LIB5B_PR64_TERMINAL_CI_RECEIPT.json), SHA-256 `d163a4fbfe97df9e2e0f8a3515f8f4ad568c778ec85b59d0a5cc7be2d2240a4e`; [source merge receipt](owner-authorized-merge-64.json). No native workflow was expected or claimed for its five Python/doc files. The operational clone is clean and fast-forwarded to main 710d144.

## Exact approved exception

The original four `.gitleaksignore` lines were preserved byte for byte. Only this owner-approved historical noncredential fixture fingerprint was appended:

```
bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32
```

Commit 173e193 owns that change and its AGENTS authority record; it was merged forward without rewriting history. Scanner configuration, rules, redaction, workflow and full-history coverage are unchanged. Any further suppression requires explicit approval. Pinned gitleaks 8.21.2 reproduced one finding before and zero after the exact exception, propagation and merges. An isolated new-commit fixture correctly fails with a new fingerprint. [Scan proof](PRE_MERGE_SCAN_PROOF.json), [negative witness](future-fingerprint-negative-receipt.json), [current main full-history report](gitleaks-current-main-spec10-all-history.json). Latest actual combined app-branch history scan covered 142 scanner-reported commits with zero leaks: [pinned 8.21.2 report](app2b-reviewed-v7-combined-full-history-gitleaks.json).

## Changes after review

- Added only the approved historical fixture fingerprint and its explicit authority record; merged it forward and preserved PR descriptions. Scanner rules/redaction/history/workflow remain unchanged.
- LIB-5A closes input-bearing TypeScript exceptions and spoofed byte-size bounds, with original-byte/unsigned-token/immutable-tuple contract clarification first. Independent fail-before closure receipt `148c492f58bbe633fc8df8835d349399376c7ec5d61f10183f6ec8175af63f25`.
- Spec v10 defines local retained-byte/metadata/staging limits, permanent pre-reserved fences, separate first-durable daily admission views and one-root fake aggregate authority. It does not select a real peer-sharing policy. Independent receipt `1a647db2e57b3d16dd8eebd23bf0cb80fd9592926cce72e282fbbc55741164a3`.
- LIB-5B closes final-directory/path guards, PID/thread session affinity and foreign-thread teardown; current-source authority, sibling restrictions, exact retirement identity/head, changed-byte retries, full binding-map coverage and referenced stream consistency remain enforced before admission/use. These synthetic/local and corrupt-metadata controls do not prove real peer consent or distributed erasure. Final full 33-card independent review: 348 cases and 21 meaningful guard-removal experiments, no unresolved material finding; [receipt](lib5b-final-v5-independent-full33-closure.json), SHA-256 `a9b74906a78c873c0ee07ac05ad689aa16a3c4fcd091ef1fef3247eef562757f`. Five files, no new dependency.
- APP-2B core fixes lazy SDK promise assimilation, late/overlapping listener cleanup, stale ownership/lifecycle actions and callbacks, final durable scheduling holds and tap-focus lifetime. Independent 57 preserved adversarial probes, 303 capture and 87 Python/static cases close all 12 core cards; [receipt](app2b-core-v4-independent-closure.json), SHA-256 `f78f2fb3fa8547e4ae4d1f8bb873c84893520c58339aab03d09e1e7896eece60`.
- APP native audit fixes canonical project/artifact/POM identity and complete strict build/repeat proof. Actual first CI exposed the incorrect single-pin iOS assumption; final fixes bind four selected packages, three actual resolution files, exact source trees/revisions/licenses and complete Capacitor manifest/source/published binary content. Unknown inputs, both Android variants and closed-SDK/permission/license refusal remain mandatory.
- APP audit refuses nonregular files promptly using nonblocking open plus retained descriptor-bound nofollow/regular/single-link/size checks. Both unchanged independent FIFO witnesses pass and fail again after removal of only the new flag. Fixed stage/error-class/source-line/count diagnostics expose the next actual Android error safely; no guessed release-artifact producer fix is claimed.
- APP privacy notice adds only `codeload.github.com` to its existing CI-only public-build host row, plus required formatting. Independent processor/semantic closure `448a35e932141c12e1711c8323d4543f8c13fb5a845a78bce8ee7c24d09fedc4` proves no other notice semantics or runtime/contributor disclosure changed. Notices remain counsel drafts.

Earlier findings, initial failed cache invocations, corrected reviewer counts/manifest labels and superseded candidate states remain in immutable chronological snapshots and original receipts. No failure or old review was relabeled as a pass.

## Current APP-2B source and checks

[Draft #63](https://github.com/global-soil-intelligence/gsip/pull/63) has final reviewed fix commit `51ec94711692964fd7a0cf5fd487db69de2ed0eb` plus main-forward merge `8130d0935ba355ce64309a39922ff6d0e458c422`. Root verified all 23 app files, unchanged core/workflow hashes and only the five exact reviewed LIB-5B files introduced by main. No history rewrite/force push. The original PR description is preserved as a prefix with appended fixes/evidence. [Push receipt](APP2B_PR63_REVIEWED_V7_PUSH.json).

Final independent native v7 review closes all four source cards: **495 passed, zero failures/skips**, with all prior banks and blocked receipts preserved; [receipt](app2b-native-v7-independent-closure.json), SHA-256 `5297ce5e3be9853b059204941e333629ad91d66fd0b7904b3d768179a9fb1783`. These are source/fixture/retained-primary-byte proofs, not hosted builds.

Root actually ran the combined source: **1,383 Python passed, four existing local GDAL skips**, Ruff and mypy (74 files). Pinned **gitleaks 8.21.2**, 142 commits, zero leaks. Unchanged exact core retains its actual 597 JavaScript checks, types, lint/language/format, closed website/app builds and budgets. [Combined exact-head receipt](APP2B_COMBINED_REVIEWED_EXACT_HEAD.json), SHA-256 `d8c7fbdd16c22a53aa0b153654e02a6964b75a41ebe8a20f38d4310410136735`.

New exact-head [general CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38445553218) and both secret scans passed; DCO skipped under unchanged same-repository policy. [Android/iOS app build](https://github.com/global-soil-intelligence/gsip/actions/runs/38445551423) failed with zero uploaded artifacts. iOS candidate compilation/repeat/native source audit passed; parent local clone could not read the exact baseline tree before checkout/install. Android compilation/repeat/existing policy checks passed; Gradle evidence inspection failed with fixed `BUILD_TOOL` diagnostics. Canonical isolated parent-fetch correction and safe bounded tool-reason classification are being prepared; no guessed Android producer correction or acceptance bypass. [Finite terminal receipt](APP2B_PR63_SECOND_NATIVE_CI_FINITE_WATCH.json), SHA-256 `2678df914ed4ca4794cc8ed7a389e03a0f22fcc5132fb1abf66b19c2d25163c0`. The app remains draft and no native/device acceptance or merge readiness is asserted.

Historical first native run `38429415336` compiled both apps and passed existing permission/version/backup/repeat steps, then failed both additive audits and uploaded zero artifacts. [Safe failed-CI evidence](ci-pr63-readonly/pr63-native-audit-failure-closeout.json), SHA-256 `7920921f43a696615e2aa256bf640ca40a6b2eec975f9b16dae9b69cd5efabd5`. Actual Android failure cause remains unknown until the new diagnostics; first-run success of compilation does not count as audit acceptance.

Dependency: `@capacitor/local-notifications` 8.3.1, MIT; published 2026-08-19; 82,938 compressed / 506,577 unpacked bytes; zero JS runtime dependencies; existing Capacitor >=8 peer. Archive SHA-256 `f5772636102fdcbdba564a9bcb32db5d799bb6e27fdeaebc39b2abffe727c287`. Exact primary ION/Capacitor source and binary receipts are retained in the native audit; no new Python dependency or paid/closed service.

Assumption: merged main contributes only LIB-5B Python/docs; all app/package/lock/script/native workflow inputs are byte-unchanged from fixed feature parent `d7ed716ed0921381da04f542e90902ede36cb462` before this APP change. Same runner/toolchain/build number and shared disposable default Gradle debug identity are compared. No owner signing material is created or read. Local Xcode 27.0 is available but no local native/device build ran; local Android SDK/Deno/GDAL execution relies on actual CI. Physical-device prompt/denial/delivery/cancellation/reboot and reliable iOS WebKit backup exclusion, signing/accounts/stores/4.2 and deployment remain separate open gates.

## Deployment checklist and evidence boundary

No Supabase, secret-value or production query was performed during this continuation. Earlier Gate A–D production receipts are historical; this source work does not assert current database or hosted API health.

| Step | Current action/status |
| --- | --- |
| Database / migrations | No new changes; any further step needs exact target/commands and separate owner go |
| Edge Functions / smoke tests | No deploy or hosted smoke in this continuation |
| Repository variables / secrets | No changes or secret-value reads |
| Rights / QA / export / cleanup workers | No dispatch; all five schedule guards remain missing/held; no nonterminal worker runs |
| Prior tiles / Hugging Face | No upload/publication; separately gated |
| Pages | Source build passed; deploy waiting; sole owner reviewer and admin bypass disabled |
| Capture / anonymous sign-in / library / photo publication | No opening; all release prerequisites remain independent |

Fresh [GET-only source/hold audit](READ_ONLY_SOURCE_HOLD_AUDIT_20261013T181846Z.json), SHA-256 `64143b55d31fa3c7a91c7e2d99a14d4d67b05dbd1077cb454e33eb74dc1fb4e8`, confirms main 710d144 and all nine merge readbacks, reviewer `jdhart81`, bypass false, all five guards 404/missing-held and complete nonterminal inventory with zero worker runs. It reads no secret values and does not approve a waiting deploy.

## Open owner/external decisions and recommendations

| Gate | Options / recommendation |
| --- | --- |
| Production / tier | Existing approved gsip target; defer paid upgrade while closed; separate go for every production step |
| Hugging Face | Owner creates `global-soil-intelligence/gsip` and stored token; fallback `viridis-research/gsip`; keep export held |
| Tiles | Conditionally approved same-origin Pages release assets; prove size, range 206, SoilGrids-only content/privacy notice before publishing; WMS fallback |
| CAPTCHA / capture / anonymous sign-in | Defer; keep closed until launch gates; any closed provider needs owner approval |
| App signing / stores / device proof | Owner-controlled Viridis accounts; no credentials/certificates/keystores created; defer release pending physical-device checks and reliable iOS backup exclusion |
| Photo publication | Keep held until server screening, exact licensed runtime/model audit and calibration approval; structured-data releases only meanwhile |
| Real peer exchange (LIB-5C) | Owner consent, purpose, retention, peer credentials and cleanup/digest policy needed; continue synthetic-only preparation |
| Scientific validation / training | Real consented instrument/lab pairs and evaluation/release prerequisites remain LIB-6/7; no measured spectrum or biome label inferred from ordinary phone RGB |
| Legal / DNS / paid services / licenses | Owner/counsel gates remain; no new closed service, paid spend or license change |

Assumptions: standing keep-building/merge authority covers separately reviewed and green source packages only. Fake authority/transport and private test roots model local ordering, not real consent, useful scientific adoption, distributed erasure or physical verification. Local missing GDAL/Deno/Android SDK results rely on actual CI; local Xcode version is verified but no local native build ran; simulator artifacts never substitute for device evidence. Temporary CI-generated Gradle inspection is tooling emitted from maintained Python, not shipped app code; that assumption will be flagged in APP-2B's PR. Code remains MIT, data ODbL 1.0 and photos CC BY-SA 4.0.

[Preserved earlier chronological report](LANDING_AND_BUILD_REPORT_HISTORY_PRE_APP_V7_PUSH_20261013T181946Z.md) records superseded candidate states and original evidence links. Current readiness is stated above.

The [head-bound next-work assessment](NEXT_SOURCE_WORK_ASSESSMENT.json), SHA-256 `0878b861c8e8f8a29a4fa4f94d53c8ee2f5bcac9ff8eff4a264d458d52eda3a8`, confirms existing coding-agent/sync/security packages are merged. Beyond APP-2B, the remaining specified implementation requires owner sharing decisions, real scientific/privacy evidence, physical devices or a separately reviewed specification; no new work package is invented.

## Latest source repair and CI — supersedes prior draft-head state

Reviewed commit `d74ba2add9ce9bb5494be60c5f11883d3f5137ef` changes only the six bounded workflow/test/doc/diagnostic files. Parent checkout closure `c50cdae9a0d21593062ee1c633cfa73db5bc54cc47726af5daea89e7c93bbfb1` confirms exact immutable isolated baseline and every later workflow command unchanged; 41 focused cases, four independent Git controls and two actual old-prefix failures preserved. Diagnostic closure `c12bdd043f4b2a3ff09980199ba11f71324281c90697251a2035806ddf7a2160` confirms 100 focused cases, five fail-before controls and four meaningful guard removals, with all other proof AST/task/fixture bytes unchanged.

Root actually passed **1,441 Python checks/four existing GDAL skips**, Ruff/mypy75/lint, pinned authored scan zero and **8.21.2 full-history scan143 commits/zero leaks**. [Root validation](APP2B_ROOT_SECOND_CI_REPAIR_VALIDATION.json); [verified push receipt](APP2B_PR63_SECOND_CI_REPAIR_PUSH.json), SHA-256 `ae578967068087f505ed3498f33cc572b4fad34c80b42b3225de4a33616d9e51`. Immediate PR-head readback lagged behind the branch ref; completion stopped until GET-only refresh verified exact head/body. No duplicate source mutation.

New [general CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38450975194) is running; [native CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38450975177) is queued. Both secret scans passed and DCO skipped under unchanged policy. No actual new native/artifact/device or merge readiness claim. Android’s actual cause remains unknown until its fixed safe diagnostic runs. All production/worker/Pages/capture gates remain unchanged.

## Latest terminal hosted results

At exact d74, general CI and both scans passed; DCO skipped under unchanged policy. Native run38450975177 failed overall: **iOS passed all steps**, actual unexpired artifact11841256545/13,914,776 bytes/digest `f3c1a9a30f02e5c158f6aaf648a7e2718ac7969d227ee5327ac079f6f20ff27a`; **Android failed only inspection18**, fixed generic BUILD_TOOL/source354, no APK. [Terminal receipt](APP2B_PR63_D74_TERMINAL_CI.json), SHA-256 `6b161a087ecae231da29ca16ed5ac46100a48dca3509481314db71fdacf2331a`. Parent checkout correction is verified in hosted iOS; actual Android cause remains unknown. Minimal actual Gradle8.14.3 task reproduction passes (no AndroidSDK), so no general API/script defect is claimed. Real captured-stream classification and Android-specific inputs remain under investigation. No source/package merge or combined native/device acceptance yet.
