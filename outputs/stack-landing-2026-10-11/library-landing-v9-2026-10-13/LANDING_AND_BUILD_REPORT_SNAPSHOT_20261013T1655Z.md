# GSIP landing and build report — 2026-10-13, 16:55 UTC

The requested #51–#56 stack is merged in order after independent review and exact-head green CI. The authorized follow-up LIB-5A contracts (#58) and local-accounting specification (#60) are also merged. Main is `d7ed716ed0921381da04f542e90902ede36cb462`. LIB-5B v4 simulator remains uncommitted: the withdrawal-sync repair and root checks pass; full independent closure is in progress. APP-2B reminders are draft [#63](https://github.com/global-soil-intelligence/gsip/pull/63): general validation and both secret scans passed; the first native run failed at its additive evidence audits. Fixes are being prepared without changing production. No production changes, deployments, capture opening, approving GitHub review, protection bypass, history rewrite or human DCO certification occurred in this continuation.

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

DCO skipped under the unchanged same-repository policy; it is not reported as a human certification. [Six-PR check register](ALL_GREEN_BEFORE_ORDERED_MERGES.json), [ordered merge register](ORDERED_MERGE_REGISTER.json). #58 [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38398436566) actually passed 881 Python tests with GDAL, 12 browser tests, 593 database assertions and configured migration/Deno/static/build checks. Its [native run](https://github.com/global-soil-intelligence/gsip/actions/runs/38398436463) produced APK 7,221,644 bytes and simulator 3,385,561 bytes at exact head f07a876; artifact/configuration evidence does not prove physical-device protection. #60 [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38399279214) passed at exact source 59044d3.

Main [CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38400202152) and [secret scan](https://github.com/global-soil-intelligence/gsip/actions/runs/38400202221) passed at d7ed716. [Pages](https://github.com/global-soil-intelligence/gsip/actions/runs/38400202149) built successfully; deploy remains waiting for Justin. Waiting is not deployed or green.

## Exact approved exception

The original four `.gitleaksignore` lines were preserved byte for byte. Only this owner-approved historical noncredential fixture fingerprint was appended:

```
bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32
```

Commit 173e193 owns that change and its AGENTS authority record; it was merged forward without rewriting history. Scanner configuration, rules, redaction, workflow and full-history coverage are unchanged. Any further suppression requires explicit approval. Pinned gitleaks 8.21.2 reproduced one finding before and zero after the exact exception, propagation and merges. An isolated new-commit fixture correctly fails with a new fingerprint. [Scan proof](PRE_MERGE_SCAN_PROOF.json), [negative witness](future-fingerprint-negative-receipt.json), [current main full-history report](gitleaks-current-main-spec10-all-history.json). Latest actual history scan covered 139 scanner-reported commits with zero leaks.

## Changes after review

- Added only the approved historical fingerprint and explicit authority record; preserved existing PR bodies and appended fixes/reasons. Immutable history still contains the cleaned-forward synthetic fixture.
- Propagated that file forward; every stacked CI checkout needs its approved historical exception. A canceled native run was genuinely rerun at the same head, rather than skipped.
- Clarified the approved exchange contract before implementation: strict original bytes, unsigned integer tokens, stable immutable tuple identities and monotonic restrictions. Public/capture/library gates stay unchanged.
- LIB-5A fixed input-bearing TypeScript property exceptions and spoofed byte-size bounds in both languages. Independent fail-before probes closed both defects; final independent original/expanded suites passed. Receipt SHA-256 `148c492f58bbe633fc8df8835d349399376c7ec5d61f10183f6ec8175af63f25`.
- Spec v10 resolves local retained-byte/metadata/staging bounds, pre-reserved permanent fences, separate first-durable daily admission views and one-root fake aggregate authority. It selects no real peer-sharing policy. Independent receipt `1a647db2e57b3d16dd8eebd23bf0cb80fd9592926cce72e282fbbc55741164a3`.
- Uncommitted LIB-5B store fixes close reproduced final directory/path guards, PID/thread session affinity and foreign-thread context teardown defects. Root replay of 15 unchanged independent boundary probes and 111 store cases passed; [closure](lib5b-store-v3-root-independent-closure.json), SHA-256 `c4ab674e75a81aaea3ac3521ad9d1c4679b9379dd91df7ca1be04c433001bf22`. This closes store witnesses only, not full simulator review.
- APP-2B core v4 fixes late listeners, cross-context durable holds, disposed ownership callbacks and final tap focus. Independent exact-core closure passed 57 preserved adversarial probes, 303 capture cases and 87 Python/static checks; [receipt](app2b-core-v4-independent-closure.json), SHA-256 `f78f2fb3fa8547e4ae4d1f8bb873c84893520c58339aab03d09e1e7896eece60`.
- APP-2B native v4 closes canonical artifact/POM/source-binding/strict nested-proof witnesses. Independent source/synthetic closure passed 159 focused, 13 prior and 40 expanded probes, with 289 combined cases; [receipt](app2b-native-v4-independent-closure.json), SHA-256 `2e74eec39e21f2bab0bdb5ce62d330121895ec672205e5ed806361baa7ee5360`. Actual CI then exposed adapter assumptions below; synthetic closure is not actual native acceptance.
- LIB-5B v3 closes the initial sibling restriction defect with same-human/sample restriction aggregation and durable pre-admission fences. Independent full review found the remaining retirement identity/head defect below; v4 repairs are in progress.

## Current candidates and review holds

LIB-5B [issue #61](https://github.com/global-soil-intelligence/gsip/issues/61) is five uncommitted exact-v4 files on `wp-lib-5b-private-exchange-ledger`. Frozen patch SHA-256 `92c7b415e94f0ca44b8ecdb974d0c38d6364511bda739a439ec95e1e69164014`; root applied only three v3→v4 files, with store/test-store and all 347 base files unchanged. Root actually ran **1,108 passing Python tests, four existing local GDAL skips**, whole Ruff/mypy/lint and pinned authored scan zero. [Root v4 validation](LIB5B_ROOT_V4_INTEGRATION_VALIDATION.json), SHA-256 `fa531ce19923a68b28de3320519a5bf4ae77b8c3efce1f3c0b97d924319b6404`. Three first invocations failed before execution on the default uv cache write restriction; logs are preserved and unchanged checks ran successfully with the approved task cache.

V4 retains checked recipient retirement sequence/head/exact byte identity after working aliases are erased, commits no contradictory predecessor chain and refuses changed-byte retries. It preserves current cleanup authority, permanent fences, payload erasure and conservative capacity behavior. Author ran 22 fail-before regressions, seven unchanged witness replays, 27 external engineering probes and 42 meaningful mutations. Those are not final independent closure: the full 33-card review now runs against an independently reconstructed frozen copy. [Preserved v3 findings](lib5b-full-v3-independent-findings.json), SHA-256 `52fe8f94e7b0569f824e0ecd43de355ee21dfdc9c0ddf7924d561287a4c32e2f`, remain historical evidence. Actual storage byte bounds remain distinguished from projected logical simulator capacities. No commit, push, PR or readiness claim until independent findings close.

APP-2B [draft #63](https://github.com/global-soil-intelligence/gsip/pull/63), exact source `bb3910164cc47eae72958ad521b2186684584978`, has reviewed reminder core and native source. Root frozen pnpm/uv installs succeeded, 597 JavaScript tests passed, 1,046 Python passed with four local GDAL skips, and static/build/budget/pinned full-history checks passed. [Root validation](APP2B_ROOT_V4_INTEGRATION_VALIDATION.json), SHA-256 `9051973c3e6bf2c316357c626963fd4608f296ff0ed6af4cf42742f565b12ef5`. Xcode **27.0 (27A266a) is available locally**; the old unavailable statement is superseded. No local native/device build ran. Deno/GDAL/Android SDK execution relies on actual CI.

The [first APP native run](https://github.com/global-soil-intelligence/gsip/actions/runs/38429415336) compiled Android and iOS and passed their existing permissions/version/backup/repeat checks, then **both additive audits failed; zero artifacts were uploaded**. General `validate` and both gitleaks checks passed at that exact head; DCO skipped under unchanged policy. iOS actually selects Capacitor 8.5.2 plus ION camera 2.0.0, filesystem 1.1.4 and geolocation 2.1.1, while the audit expects one pin. Its source tree also contains two upstream build-tool resolution files requiring explicit binding/classification. The repair must audit the full actual graph, source/license/revision evidence and exact file inventory, preserving strict unknown/binary refusal. Android's exact failing stage is still unconfirmed; bounded enum-only diagnostics are being added first. No guessed artifact substitute or dependency suppression is approved. [Read-only CI triage](ci-pr63-readonly/pr63-native-audit-failure-closeout.json), SHA-256 `7920921f43a696615e2aa256bf640ca40a6b2eec975f9b16dae9b69cd5efabd5`.

Root has now integrated **uncommitted native v5 plus reviewed privacy wording**, changing only the audit script, its tests/doc and the existing privacy notice; the workflow and core18 files are byte-identical. Complete four-pin/three-lock/source/archive binding replaces the incorrect single-pin schema, while Android adds enum/count/class/source-line-only diagnostics without a guessed producer change. The notice adds only literal `codeload.github.com` to its CI-only public-build row, plus required table formatting. Independent disclosure closure proves processor fail-before 1/5→6 passing and no other semantic change; [receipt](APP2B_REVIEWED_CODELOAD_INDEPENDENT_CLOSURE.json), SHA-256 `448a35e932141c12e1711c8323d4543f8c13fb5a845a78bce8ee7c24d09fedc4`.

Root v5 actually passes **1,098 Python tests with four GDAL skips**, whole Ruff/mypy/lint and pinned authored scan zero; [validation](APP2B_ROOT_V5_INTEGRATION_VALIDATION.json), SHA-256 `ba3d8cc9c59a55e71b4e4b9fccd098ba6ecc497775a3ed17fa6e4e03503814e3`. The frozen native four-file receipt is `394ac613d2da1e6031f8b7f2945287003153f7dae8929b2594995d913f1abd8e`; expanded independent v5 review is in progress before committing/pushing. These working-tree results do not replace the current PR head's failed native CI. New exact-head CI/artifacts and actual Android cause remain pending.

Pinned plugin `@capacitor/local-notifications` 8.3.1: MIT; published 2026-08-19; 82,938 compressed / 506,577 unpacked bytes; zero JavaScript runtime dependencies; peer Capacitor >=8. Archive SHA-256 `f5772636102fdcbdba564a9bcb32db5d799bb6e27fdeaebc39b2abffe727c287`. Actual native license/repeat/feature-size proof, artifacts, physical-device behavior and iOS backup proof remain open. No device, store-readiness or guideline 4.2 acceptance is claimed.

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

Fresh [GET-only source/hold audit](READ_ONLY_SOURCE_HOLD_AUDIT_20261013T164009Z.json), SHA-256 `1050deaff6c1820421e1abc8fdd39cdd503138d8b09ca464ec3ffcf8f305bedb`, confirms main and all eight merge readbacks, reviewer `jdhart81`, bypass false, all five guards 404/missing-held and complete nonterminal inventory with zero worker runs. It reads no secret values and does not approve a waiting deploy.

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

[Preserved chronological progress/evidence](LANDING_AND_BUILD_REPORT_HISTORY_THROUGH_20261013T1348Z.md) contains superseded candidate states; use this report's current sections for readiness.
