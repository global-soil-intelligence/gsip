# GSIP approved stack landing and next build — 2026-10-13

The owner-approved #51–#56 stack is merged in order, closing at `1d105bde4d009403d114c844c52d5bf6aaf4565e`; that merge tree exactly matches the reviewed final v9 source head. Follow-up #58 and specification #60 are also merged after independent review and green exact-head CI. Current main is `d7ed716ed0921381da04f542e90902ede36cb462`. Independent review and green exact-head checks preceded every merge. No approving review, bypass, force-push, rebase, human DCO certification, production change or capture opening occurred.

| PR | Status | Merge commit |
| --- | --- | --- |
| [#51](https://github.com/global-soil-intelligence/gsip/pull/51) | Merged from exact green head | `5a26ca2f1cb47233b8d82228d96d4df0aea9a4b3` |
| [#52](https://github.com/global-soil-intelligence/gsip/pull/52) | Merged from exact green head | `ffd056dc506911a1a60541ceb2eedc668b7d1576` |
| [#53](https://github.com/global-soil-intelligence/gsip/pull/53) | Merged from exact green head | `1dc380a16f8d6494f20ac59901a5347e2f31b64a` |
| [#54](https://github.com/global-soil-intelligence/gsip/pull/54) | Merged from exact green head | `9a51ec4564358068d1ba245455f6f5d3ea68f286` |
| [#55](https://github.com/global-soil-intelligence/gsip/pull/55) | Merged from exact green head | `c804e1516ccb29c3f2535bc0a685ab1a907a32fe` |
| [#56](https://github.com/global-soil-intelligence/gsip/pull/56) | Merged from exact green head | `1d105bde4d009403d114c844c52d5bf6aaf4565e` |

## Approved exception and verification

The original four `.gitleaksignore` lines were preserved byte for byte and only the exact approved historical browser-fixture fingerprint was appended. AGENTS records Justin's 2026-10-13 authority and still requires explicit approval for every further suppression. The scanner configuration, detection rules, workflow, redaction and history coverage are unchanged. Commit173e193 owns the change; it was merged forward through the stack without rewriting history. Existing PR descriptions were retained and fixes/reasons appended.

Pinned gitleaks8.21.2 whole-stack scans reproduced one finding before the change and zero after the exact approved file, after propagation, before ordered merges and after all six merges. An isolated synthetic negative witness recreates the same file/line/fixture in a new commit and correctly fails with one new fingerprint, proving future matches remain unsuppressed. [Scan proof](PRE_MERGE_SCAN_PROOF.json), [post-merge redacted report](gitleaks-after-six-merges.json), [future-match witness](future-fingerprint-negative-receipt.json), [independent exception review](approved-exception-independent-review.json).

All six PRs passed every listed check, except DCO skipped under the unchanged same-repository policy. [Complete pre-merge check register](ALL_GREEN_BEFORE_ORDERED_MERGES.json), [ordered merge register](ORDERED_MERGE_REGISTER.json), [current merge readback](six-merged-current-readback.json). A native run canceled by overlapping automatic runs was genuinely rerun at the same head and passed; no canceled check was ignored or weakened. Current-head APK/simulator artifacts for #51 and #53 are unexpired and nonempty, with exact run-head bindings in their native receipts. Simulator artifacts do not prove device backup exclusion.

Final spec CI at eacb8 passed779Python withGDAL,593database assertions and the configured browser/concurrency/static/build checks. It verifies the existing stacked runtime, not a LIB-5 implementation. [Actual final run](pr56-approved-final-validate.json), [log](pr56-approved-final-validate.log). [Post-merge main CI](main-after-six-final-validate.json) also passed at merge1d105b, with779Python tests and593database assertions; Pages waits for Justin's environment approval; no deployment approval was given.

## Changes after review

- Exact historical fingerprint suppression plus its explicit governing-document record; reason: immutable history retains a synthetic noncredential fixture even though its current value was cleaned forward.
- Forward-only propagation through all six branches; reason: each CI checkout needs the same exact historical exception.
- SPEC/BUILD_ORDER now record owner approval for local LIB-5A contracts and LIB-5B synthetic preparation, effective after specification merge. Real LIB-5C purpose/consent/retention/peer/credential/cleanup choices remain held.
- Before code, clarified exchange-only UTF-8/BOM/surrogate/depth rules, unsigned integer tokens, immutable stream/sample/measurement tuple binding and monotonic synthetic restrictions. Exact event identity still uses original bytes. Existing LIB-1/4 contracts and SPEC16.1–16.8 are unchanged. Independent fresh-context two-document review closed with no blocking finding ([receipt](spec9-clarifications-independent-review.json)).
- Native cancellation was rerun rather than skipped. Both required native platforms passed at the unchanged exact source head.

## Next build

LIB-5A is being authored in an isolated copy from merged main: pure TS/Python parsing, exact-byte integrity/retry classification and a shared synthetic conformance corpus. It makes no filesystem/network/environment/credential lookup, adds no dependency or CLI and establishes no grant, peer identity or scientific verification. Independent adversarial probes are prepared separately. LIB-5B planning is read-only until 5A is reviewed/merged; it will add only the approved fake-authority private local ledger/rights simulation.

The author's frozen offline snapshot setup lacked two cached packages. Existing frozen dependency runtimes may be reused read-only for focused checks; lockfiles are untouched. Root integration and actual CI results will be reported separately. No candidate test is reported passing before it runs.

## Deployment and remaining owner gates

No production query or mutation was performed in this continuation. Historical production receipts are separate evidence, not current health assertions. No database migration, Edge Function deployment, worker dispatch, Hub/tile upload, secret/URL/auth setting change or store signing action occurred.

Pages still has sole reviewerjdhart81 with administrator bypassfalse. The deployment remains waiting; build artifacts have capture/intake flagsfalse. Prior/QA/export workflow holds remain, and rights/cleanup jobs are held because their schedule guard variables are absent rather than equal totrue. No existing hold was lifted. No capture or anonymous sign-in opening occurred.

Keep these gates explicit: separate 50-photo soil/photo QA pilot; permissioned privacy-detector calibration and exact runtime/model licence audit; legal approval and URLs; canonical-domain/DNS/crawlable-site readiness; conditional prior tiles publication; paid launch tier and green workers; owner-created HF dataset/token; owner-controlled signing/accounts and real-device iOS backup verification. Real peer-sharing purpose/consent/retention/authority and digest/lineage policy remain undecided. Real instrument/lab pairs, scientific validation, spectral privacy review and open model/release gates remain LIB-6/7 work.

Assumptions: owner merge/build authority covers source and synthetic local preparation only. It never substitutes for production or real-data sharing approval. No new dependency, paid/closed service or project licence change was introduced by landing. Code remainsMIT, dataODbL1.0 and photosCCBY-SA4.0.

## LIB-5A candidate review — in progress

The frozen v1 seven-file candidate passed 304 schema tests and 876 Python tests with four existing local GDAL skips. Root lint/typecheck/Ruff/mypy passed. Root workspace unit testing failed in the preexisting map-tile command test because sandbox policy denied its loopback listener (`EPERM`); that is not reported as a pass and will be rerun with the needed local listener permission. Native SDKs, Xcode, GDAL and Deno are absent locally; actual CI supplies those checks.

Independent v1 review found two P2 blockers despite the ordinary suites passing: decoded TypeScript helper/schema property access can propagate an input-bearing exception, and overridden byte-size properties in both languages can bypass the pre-copy 2 MB bound. The reviewer ran 155 independent wire probes in both languages; its extended TS results were 161/171 and Python 162/163. Findings receipt SHA-256: `005e9f7d307179d31c9e78c02a15b07161ea6b6593799f3a33f31ed0a3c80331`. V1 remains uncommitted. The author is producing a separately frozen v2 with generic boundary guards, trusted intrinsic byte bounds and regressions that fail on v1. No findings are claimed closed yet. Required issue: https://github.com/global-soil-intelligence/gsip/issues/57.

LIB-5B planning identified four local accounting/transaction ambiguities. A specification-only v10 proposal is being prepared before simulator implementation; real consent, retention, credential and peer choices remain unresolved and held. No simulator code is written under that proposal.

## LIB-5A landed; v10 specification pending CI

LIB-5A [#58](https://github.com/global-soil-intelligence/gsip/pull/58) is merged after exact-head green checks and independent closure. Authored source `f07a876defbc3ee208996747f3f4b596b7606614`; merge `333f1492713d41c0ade42d6b16c4453cdfb1b783`. Both v1 P2 findings closed with fail-before regressions. Final independent review SHA-256 `148c492f58bbe633fc8df8835d349399376c7ec5d61f10183f6ec8175af63f25`; its original 171 TS / 163 Python probes and expanded 280 / 268 focused suites passed. Final doc copy distinguishes TS arrays from Python typed sequences. No unresolved finding remains in the merged candidate.

Root v2 integration actually passed 529 TypeScript / 877 Python with four local GDAL skips, full static checks, production builds, both budgets and closed app build. Actual [CI 38398436566](https://github.com/global-soil-intelligence/gsip/actions/runs/38398436566) passed 881 Python with GDAL, 12 browser tests, 593 database assertions and all configured existing-data/Deno/build checks. [Native run 38398436463](https://github.com/global-soil-intelligence/gsip/actions/runs/38398436463) passed both platforms with unchanged SDK/permission/backup/activation checks. Exact-head unexpired artifacts: Android 7,221,644 bytes, iOS simulator 3,385,561 bytes. This is artifact/configuration evidence, not real-device/iOS backup protection. Both secret scans passed; DCO skipped under unchanged same-repository policy. Source merge used Conventional/Co-Authored-By metadata and no bypass or approving review.

[Specification #60](https://github.com/global-soil-intelligence/gsip/pull/60), authored `59044d3b62265d56d2983b17924bb72765b08556`, has exactly two document changes resolving [underspecification #59](https://github.com/global-soil-intelligence/gsip/issues/59). It preserves original queued limits and adds conserved retained-byte/metadata/staging bounds, reserved permanent scope fence/pending state, explicit separate first-durable daily admission views, and one-root fake aggregate authority. Exact-hash independent review found no actionable findings (receipt `1a647db2e57b3d16dd8eebd23bf0cb80fd9592926cce72e282fbbc55741164a3`). Root lint/language/formatting and pinned authored-doc scan passed. It was retargeted to main after #58 merged; CI is running. No LIB-5B code or tests have been written, and no implementation result is claimed by the spec.

Pinned gitleaks 8.21.2 full-history scans remain zero after the new source commit/merge and spec commit. The exact approved exception file/config/workflow are unchanged. All production/capture/intake/photo/worker holds remain unchanged; no production read or mutation occurred. Real source/consent/retention/peer/cleanup credentials stay LIB-5C decisions. The standing source-only merge/build authority is the assumption for the local v10 engineering clarification, not a real-sharing or deployment go.

## Current source state: v10 merged, synthetic ledger authoring

Specification [#60](https://github.com/global-soil-intelligence/gsip/pull/60) merged as `d7ed716ed0921381da04f542e90902ede36cb462`; its exact-head validate run passed 881 Python with GDAL, 12 browser tests and 593 database assertions. Actual main CI `38400202152` and secret scan `38400202221` passed at that main head. Pages `38400202149` built successfully and its deployment waits for Justin; waiting is not deployed or green.

Bounded read-only [source/hold audit](READ_ONLY_SOURCE_HOLD_AUDIT_20261013T130021Z.json) confirms all eight source PRs merged/checks successful apart from policy-skipped DCO, sole Pages reviewer `jdhart81`, administrator bypass false, all five schedule guards missing/held and no nonterminal worker runs. Audit SHA-256 `b432b9aa5554ad505359e5d2c2273662c1f3b0d914d919147b4b900a1ccafd78`; its API snapshot is 12:57:02–12:57:15 UTC. It made no mutation, Supabase or secret-value call.

LIB-5B [work-package #61](https://github.com/global-soil-intelligence/gsip/issues/61) is being authored only in an isolated copy from the verified main snapshot. A separate author owns private filesystem transaction code/tests; the lead owns the fake-authority simulator/tests/docs, with 33 independently prepared adversarial test cards. No candidate readiness or test pass is claimed before freezing/integration/review. Root owns operational source/Git changes. No production/capture/auth/publication/worker hold was lifted.

The already specified APP-2B reminder dependency has been re-audited read-only from primary npm metadata/archive: `@capacitor/local-notifications` 8.3.1 is MIT, published 2026-08-19, 82,938 compressed / 506,577 unpacked bytes, no JavaScript runtime dependencies and peer Capacitor >=8. Archive SHA-256 `f5772636102fdcbdba564a9bcb32db5d799bb6e27fdeaebc39b2abffe727c287`, integrity verified. No package was installed or executed. Full resolved Android license/SDK audit, measured native build impact and implementation/device proof remain pending; package metadata alone supplies no native readiness.

## Local ledger review and app reminder preparation — 13:48 UTC

LIB-5B remains uncommitted and isolated. Its frozen store v1 passed 89 baseline cases, including 31 real-process crash cases; 11 isolated guard/order mutations correctly failed. Independent review then reproduced 11 failures in 13 new probes: two P2 findings cover missing final live directory guards and active session reuse across threads/forked processes. False private-read/absence success and inherited-lock mutation are blocked from landing. The author is adding final-boundary checks and PID/thread affinity with fail-before regressions. [Exact v1 findings](lib5b-store-v1-independent-findings.json), SHA-256 `46a8c75a476e2fb14a8832fc6b447b15f76c8f554b19a4eac5ca5e6f7d4ab139`. Passing original suites is not closure of these findings. The simulator's behavioral suite and complete independent review remain pending.

APP-2B [work-package #62](https://github.com/global-soil-intelligence/gsip/issues/62) has started in a separate synthetic author copy from d7ed716, under the already approved SPEC section 15.3. It adds bounded, generic, explicit native opt-in sync reminders only; no push/location/nearby feature, production or capture change. [Source snapshot and invariants](APP2B_AUTHOR_SNAPSHOT.json), SHA-256 `a0310e516bf979ecc100cbfbcc6b78983543b62c48165300f784189fd0ecf5b1`. No candidate test, installation, native measurement or device pass is claimed yet. The exact plugin archive was audited read-only; resolved native dependencies, artifact impact, race/cancellation/logging and real-device proof remain separate requirements. Physical iOS WebKit backup proof and owner signing/accounts remain held.
