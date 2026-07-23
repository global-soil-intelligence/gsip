# GSIP landing and build report — 2026-10-13, 22:04 UTC

The requested #51–#56 stack is merged in order after exact-head green CI and only the exact approved fixture exception. Follow-up source packages LIB-5A(#58), specv10(#60), synthetic local ledger LIB-5B(#64) and source-status documentation WP-DOC-1(#65) are merged. Main is **`7d6777fc219c48792b8e1e2f4912d5c276b477c1`**. APP-2B(#63) remains unmerged at748146d: general CI/scans and fresh iOS proof pass, Android fails with its underlying causeUNKNOWN. A build-level diagnostic observer is being reviewed; no further behavioral fix or native acceptance is claimed. **No production change, deployment or capture opening occurred.** No approving GitHub review, protection bypass, history rewrite or human DCO certification occurred.

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
| [#65](https://github.com/global-soil-intelligence/gsip/pull/65) | Green; independent factual source-status review | `7d6777fc219c48792b8e1e2f4912d5c276b477c1` |

DCO skipped under the unchanged same-repository policy; it is not reported as a human certification. [Six-PR check register](ALL_GREEN_BEFORE_ORDERED_MERGES.json), [ordered merge register](ORDERED_MERGE_REGISTER.json). #58 [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38398436566) actually passed 881 Python tests with GDAL, 12 browser tests, 593 database assertions and configured migration/Deno/static/build checks. Its [native run](https://github.com/global-soil-intelligence/gsip/actions/runs/38398436463) produced APK 7,221,644 bytes and simulator 3,385,561 bytes at exact head f07a876; artifact/configuration evidence does not prove physical-device protection. #60 [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38399279214) passed at exact source 59044d3.

Historical main710 [CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38443032588) and [secret scan](https://github.com/global-soil-intelligence/gsip/actions/runs/38443032236) passed at 710d144. [Pages](https://github.com/global-soil-intelligence/gsip/actions/runs/38443032217) remains waiting for Justin’s approval. Waiting is not deployed or green; no approval was given.

#64 [CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38440865646) passed at exact reviewed source `7934aaa8b729e42ce373977cabfd9f18e5784c18`: 1,136 Python with required GDAL/zero skips, 529 JavaScript, 12 browser, 593 pgTAP assertions/11 files, Deno and existing-data migration compatibility. Both push/PR gitleaks passed; DCO skipped under unchanged policy. [Independent terminal CI receipt](LIB5B_PR64_TERMINAL_CI_RECEIPT.json), SHA-256 `d163a4fbfe97df9e2e0f8a3515f8f4ad568c778ec85b59d0a5cc7be2d2240a4e`; [source merge receipt](owner-authorized-merge-64.json). No native workflow was expected or claimed for its five Python/doc files. The operational clone is clean and fast-forwarded to main 710d144.

#65 [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38473072529) passed at exacta2ad2d8:1,136 Python with requiredGDAL/zero skips,529 JavaScript/39files,12browser,593pgTAP/11files,Deno2,static/build/map-budget and existing-data migration compatibility. No separate site-budget or native run is claimed. Both hosted8.21.2 scans passed148commits/zero; DCO skipped. [Terminal receipt](DOC1_PR65_TERMINAL_CI_RECEIPT.json), SHA-256`416b0b00d3b1bdf6328d6b5715b3d2c51af3f33d1a1f637ca92ab9dadf63b723`; [merge receipt](owner-authorized-merge-65.json). [Clean main fast-forward/tree/parents/metadata](DOC1_MAIN_FAST_FORWARD.json), SHA-256`c68f5bca854c4067baae5586f21d52181b9991c3329d229bc7eec3815685b754`. Main7d CI/Pages are separate new runs; no result/deployment is inferred from pre-merge CI.

## Exact approved exception

The original four `.gitleaksignore` lines were preserved byte for byte. Only this owner-approved historical noncredential fixture fingerprint was appended:

```
bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32
```

Commit 173e193 owns that change and its AGENTS authority record; it was merged forward without rewriting history. Scanner configuration, rules, redaction, workflow and full-history coverage are unchanged. Any further suppression requires explicit approval. Pinned gitleaks 8.21.2 reproduced one finding before and zero after the exact exception, propagation and merges. An isolated new-commit fixture correctly fails with a new fingerprint. [Scan proof](PRE_MERGE_SCAN_PROOF.json), [negative witness](future-fingerprint-negative-receipt.json), [current main full-history report](gitleaks-current-main-spec10-all-history.json). Latest app-branch full-history scan covered147 scanner-reported commits with zero leaks: [pinned8.21.2 report](app2b-producer-full-history-gitleaks.json).

## Changes after review

- WP-DOC-1 corrects stale source/specification completion status and two README anchors; no architecture/runtime/dependency/lock/workflow change. Every122 acceptance box and12 bound normative gate sections remains unchanged. Independent closure SHA-256`30d93f0a6a47b06b8f31cb8981f445d78f624392f05deeae0e4f41c679062124`, [receipt](DOC1_INDEPENDENT_CLOSURE.json). Root18 existing documentation checks/lint passed; all349 other sourcefiles unchanged. APP63 and every external readiness gate remain held.

- Added only the approved historical fixture fingerprint and its explicit authority record; merged it forward and preserved PR descriptions. Scanner rules/redaction/history/workflow remain unchanged.
- LIB-5A closes input-bearing TypeScript exceptions and spoofed byte-size bounds, with original-byte/unsigned-token/immutable-tuple contract clarification first. Independent fail-before closure receipt `148c492f58bbe633fc8df8835d349399376c7ec5d61f10183f6ec8175af63f25`.
- Spec v10 defines local retained-byte/metadata/staging limits, permanent pre-reserved fences, separate first-durable daily admission views and one-root fake aggregate authority. It does not select a real peer-sharing policy. Independent receipt `1a647db2e57b3d16dd8eebd23bf0cb80fd9592926cce72e282fbbc55741164a3`.
- LIB-5B closes final-directory/path guards, PID/thread session affinity and foreign-thread teardown; current-source authority, sibling restrictions, exact retirement identity/head, changed-byte retries, full binding-map coverage and referenced stream consistency remain enforced before admission/use. These synthetic/local and corrupt-metadata controls do not prove real peer consent or distributed erasure. Final full 33-card independent review: 348 cases and 21 meaningful guard-removal experiments, no unresolved material finding; [receipt](lib5b-final-v5-independent-full33-closure.json), SHA-256 `a9b74906a78c873c0ee07ac05ad689aa16a3c4fcd091ef1fef3247eef562757f`. Five files, no new dependency.
- APP-2B core fixes lazy SDK promise assimilation, late/overlapping listener cleanup, stale ownership/lifecycle actions and callbacks, final durable scheduling holds and tap-focus lifetime. Independent 57 preserved adversarial probes, 303 capture and 87 Python/static cases close all 12 core cards; [receipt](app2b-core-v4-independent-closure.json), SHA-256 `f78f2fb3fa8547e4ae4d1f8bb873c84893520c58339aab03d09e1e7896eece60`.
- APP native audit fixes canonical project/artifact/POM identity and complete strict build/repeat proof. Actual first CI exposed the incorrect single-pin iOS assumption; final fixes bind four selected packages, three actual resolution files, exact source trees/revisions/licenses and complete Capacitor manifest/source/published binary content. Unknown inputs, both Android variants and closed-SDK/permission/license refusal remain mandatory.
- APP audit refuses nonregular files promptly using nonblocking open plus retained descriptor-bound nofollow/regular/single-link/size checks. Both unchanged independent FIFO witnesses pass and fail again after removal of only the new flag. Fixed stage/error-class/source-line/count diagnostics expose the next actual Android error safely; no guessed release-artifact producer fix is claimed.
- APP privacy notice adds only `codeload.github.com` to its existing CI-only public-build host row, plus required formatting. Independent processor/semantic closure `448a35e932141c12e1711c8323d4543f8c13fb5a845a78bce8ee7c24d09fedc4` proves no other notice semantics or runtime/contributor disclosure changed. Notices remain counsel drafts.

Earlier findings, initial failed cache invocations, corrected reviewer counts/manifest labels and superseded candidate states remain in immutable chronological snapshots and original receipts. No failure or old review was relabeled as a pass.

## Current APP-2B build

**Latest exact748 result is terminal, not pending:** [generalCI](https://github.com/global-soil-intelligence/gsip/actions/runs/38471987275) and both scans pass; DCO skipped. Actual hosted1550Python pass/**seven verified-tool-unavailable skips**,597JS/44files,12browser,593pgTAP/11files,Deno2/existing-data migration pass. The seven skipped cases were actually run locally and independently; they are not called hosted passes. Fresh [native run48](https://github.com/global-soil-intelligence/gsip/actions/runs/38471987452) has verified iOS artifact11852231660/13,914,793B/digest`033a629b46c3348936b46f8a97c1daa9f2c238d7f95aca9b0e89a693d095a2c2`; exact-helper/source/main710+748 merge/parentd7/fresh run48/license/repeat/four-ZIP-bounds comparison replay passes. FeatureZIPdelta169,800B; entries equal/full bytes differ. [CI/iOS receipt](APP2B_PR63_748_CI_IOS_CLOSURE.json), SHA-256`ae7884a8ee35954766abbc3447e4ae5626018dc1b0214476af72baa5f0d6ebee`.

Android failed with fixedfaultUNKNOWN and unchanged oversized-stderr refusal, no APK/combined acceptance. [Failure receipt](APP2B_PR63_748_ANDROID_CLOSEOUT.json), SHA-256`3b8f6d4dc316c07a18662b58d38fac438e40b70e6a3d33e326f2564029e5b3cb`. A bounded GET-only diagnosis found no attributable Gradle failure text because inspection streams are captured by the helper; raw logs were not printed/persisted. [Diagnosis](APP2B_PR63_748_READONLY_CAUSE.json), SHA-256`4943566d825acc4b2377c5716c99c5e45090c40e3afa556e22a34cffa0cbe5a7`. Build failures before task execution are empirically uncovered by the current fixed channel; the diagnostic-only observer candidate is in preparation/review, with original status,65K/256bounds and every proof guard retained. No new source is integrated/pushed yet. Its public/deprecated pinned8.14.3 lifecycle API and lack of configuration-cache support will be explicit assumptions. No guessed cause is claimed.

The documentation source package is now merged independently as#65. Before the next app push, main7d must be merged forward and the final source/CI proof rebound; current748CI authenticates historicalmain710, not the new integration.


Current [draft#63](https://github.com/global-soil-intelligence/gsip/pull/63) is open/unmerged at **`748146da663e692f6637a5a11a43ad063c49cd4f`**. Normal push/remote/PR exact-head and original-description prefix were verified. [Receipt](APP2B_PR63_PRODUCER_PUSH.json), SHA-256 `d3ed35d2ca22fed302a8e4c73dc9009f726095a6fd92ec6d248af6022a259b23`. Exact-head hosted outcome is recorded above; no APK or combined native acceptance is claimed.

Commit748146d adds only195bytes/five lazy public `buildDependencies` task lines for both runtime configurations before inspection. Removing the block restores the whole prior helper byte for byte, and all old Python function ASTs/task remainder/396test-prefix bytes/362other sourcefiles remain. Existing graph/view/source/license/repeat/permission/backup/fault/cap/status proof remains mandatory. [Independent finite closure](APP2B_PRODUCER_INDEPENDENT_CLOSURE.json), SHA-256 `ae8a4c6bbd034aeaa337b6c1da80438b3dde311f7327c899b643a4e3a401c8ff`:213unique cases, all seven real Gradle8.14.3/Java21 controls, original/full-block and per-variant failures, disabled/failing producers, missing config and foreign selection refusal, plus byte-identical same-project prebuilt graph. The corrected cached-transform harness assertion is disclosed and old attempt preserved; no source finding remains.

Root passed **1,553 Python/four existing localGDAL skips**, including all seven meaningful new actual Gradle controls without skips, plus Ruff/mypy/lint/language/format. [Checks](APP2B_ROOT_PRODUCER_CHECKS.json). Authored and full-history pinned **gitleaks8.21.2 zero**,147 scanner-reported commits, [report](app2b-producer-full-history-gitleaks.json). Default general CI explicitly skips these seven tool-dependent controls when verified Gradle opt-in is unavailable; they were actually run locally and independently, and every existing hosted native proof remains mandatory. Public existing Gradle/Java build tools add no runtime dependency or owner signing input. The local producer defect is confirmed; the specific original hosted cause remainsUNKNOWN.

WP-DOC-1 is now source-merged as#65, with all gates retained and no APP63merge or production readiness claimed.

### Preceding e9 hosted result (historical, separate from new-head acceptance)


Preceding source was `e9a6893ee980bfe62a8ecf0b2664e3ab2ec9f0c3`. [General CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38468020313) passed: **1,550 Python with required GDAL/zero skips**, 597 JavaScript/44 files, 12 browser, 593 pgTAP assertions/11 files, two Deno checks and existing-data migration compatibility. Both pinned8.21.2 secret scans passed; DCO skipped under unchanged policy.

[Native run](https://github.com/global-soil-intelligence/gsip/actions/runs/38468020431) has **iOS success and Android failure**. The private bounded fault receipt establishes Android `DEBUG_ARTIFACTS / UNKNOWN`; the specific underlying cause remains unknown. Raw stderr exceeded the unchanged65,536-byte cap and was not printed or persisted. No APK or combined native acceptance is claimed. [Android receipt](APP2B_PR63_E9_ANDROID_CLOSEOUT.json), SHA-256 `604a987a3432b9a07c5a1ffd61bb15ed9c31ab47fd57a2b3a1e824e2ba720012`.

Fresh iOS artifact11850656632/13,914,703 bytes/digest`9ac0bdffd71f44aabf35a6138a2904f58805cb0d69169c217941f70426346eb9` passed exact-helper replay, authenticated merge/source/parent/run47/native/license/repeat/reference and four ZIP bounds. Overall featureZIPdelta169,797 bytes; repeat ZIP entry contents equal, full archive bytes different. This does not prove bitwise reproducibility, physical-device delivery or reliable iOS backup exclusion. [CI/iOS closure](APP2B_PR63_E9_CI_IOS_CLOSURE.json), SHA-256 `efa1c9c45247a46b02c99fd8eb080f20a8f09f9fdfc10d455991734edf7df883`. Omitted API step arrays are unavailable detail, not zero executed steps.

Preceding root source passed **1,546 Python/four existing localGDAL skips**, Ruff, mypy and lint/language/format. [Checks](APP2B_ROOT_CHANNEL_CHECKS.json). Authored scan zero; pinned **gitleaks8.21.2 full history146 scanner-reported commits/zero leaks**, [report](app2b-channel-full-history-gitleaks.json). [Normal push/body-prefix readback](APP2B_PR63_CHANNEL_PUSH.json). The original PR description remains a prefix with evidence appended; native acceptance stays unchecked.

The new bounded fixed-fault channel was independently reviewed:206 cases/zero failures, original collector/main/task operation projections preserved, three fail-before cases and five effective guards. It binds only fixed phase/cause metadata to the exact failed process/command/stage and retains original exceptions/nonzero status, all raw-output/file bounds and every proof/permission/backup/license rule. [Closure](APP2B_CHANNEL_INDEPENDENT_CLOSURE.json), SHA-256 `d193dbd1f700b6cb54e4f0a270b1fd2209794c94b9464b878caa93a0623ea299`.

The producer-order correction is now reviewed/pushed at748146d as recorded above; fresh hosted acceptance remains required.

Core12-card independent closure:57 preserved adversarial probes,303 capture and87 Python/static cases, SHA-256 `f78f2fb3fa8547e4ae4d1f8bb873c84893520c58339aab03d09e1e7896eece60`, [receipt](app2b-core-v4-independent-closure.json). Native four-card source closure:495 cases, SHA-256 `5297ce5e3be9853b059204941e333629ad91d66fd0b7904b3d768179a9fb1783`, [receipt](app2b-native-v7-independent-closure.json). Source/fixture review is separate from hosted build acceptance.

Dependency: `@capacitor/local-notifications`8.3.1, MIT; published2026-08-19;82,938 compressed/506,577 unpacked bytes; zero JS runtime dependencies; existing Capacitor>=8 peer. Archive SHA-256 `f5772636102fdcbdba564a9bcb32db5d799bb6e27fdeaebc39b2abffe727c287`. Exact primary source/binary/license receipts retained. No new Python dependency, paid/closed service or signing input.

Assumptions: main710 adds only five LIB-5B Python/doc files; app/package/lock/native workflow inputs before this feature match reviewed parentd7ed716. Temporary Gradle inspection is emitted by maintained Python and adds no shipped native source. Synthetic controls prove ordering and refusal behavior, not Android-specific correctness or field adoption. AndroidSDK/GDAL/Deno/PostgreSQL tools are absent locally; Xcode27.0 command version is verified, but no local native/device build ran. Hosted CI supplies required database/GDAL/native results. Physical-device prompts/denial/delivery/cancellation/reboot, reliable iOS backup exclusion, owner accounts/signing/store acceptance remain open.

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

Fresh [GET-only source/hold audit](READ_ONLY_SOURCE_HOLD_AUDIT_20261013T202553Z.json), SHA-256 `c52ed05e4c62caef5d9c18aa2e411728b02f5c9435e2a08bea1b262c8a042292`, confirms main 710d144 and all nine merge readbacks, reviewer `jdhart81`, bypass false, all five guards 404/missing-held and complete nonterminal inventory with zero worker runs. It reads no secret values and does not approve a waiting deploy.

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

Earlier diagnostic attempts, failed source states and corrected receipt arithmetic remain in [the immutable detailed history](LANDING_AND_BUILD_REPORT_HISTORY_PRE_PRODUCER_FIX_20261013T212110Z.md); none is relabeled as current acceptance. The [next-work assessment](NEXT_SOURCE_WORK_ASSESSMENT.json), SHA-256 `0878b861c8e8f8a29a4fa4f94d53c8ee2f5bcac9ff8eff4a264d458d52eda3a8`, confirms the remaining specified work beyond APP-2B requires owner sharing decisions, scientific/privacy evidence, devices or a separately reviewed specification. No new package or real sharing/training authority is invented.

[Preserved pre-producer CI report](LANDING_AND_BUILD_REPORT_HISTORY_PRE_PRODUCER_CI_20261013T213911Z.md).

## Latest source/deployment hold evidence

[GET-only readback at22:01UTC](READ_ONLY_SOURCE_HOLD_AUDIT_20261013T220107Z.json), SHA-256`b7cd9984e1cc692861f5dbfb42a568bc037708bfd5770d42bbf89afb0018e2d7`, confirms main7d/all10 source merges, Pages sole reviewerjdhart81/admin bypassfalse, all five schedule guards404missing-held, complete nonterminal inventory/zero worker runs. No Supabase or secret-value query, deployment approval or dispatch. [Combined current app/docs/all-ref scan](COMBINED_APP_DOC_HISTORY_SCAN.json), SHA-256`891a4dc5dedd2a1a257212d5a89ed46fda8d8410d9c08d6bc9eff28f65ff5cf0`, pinned8.21.2/148commits/zero leaks; new suppressionnone.

[Preserved pre-DOC65 status](LANDING_AND_BUILD_REPORT_HISTORY_PRE_DOC65_MERGE_20261013T220414Z.md).
