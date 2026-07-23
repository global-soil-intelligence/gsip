# GSIP landing and build report — 2026-10-13, 15:38 UTC

The requested #51–#56 stack is merged in order after independent review and exact-head green CI. The authorized follow-up LIB-5A contracts (#58) and local-accounting specification (#60) are also merged. Main is `d7ed716ed0921381da04f542e90902ede36cb462`. LIB-5B simulator and APP-2B reminders are being corrected after independent review; neither has a PR or readiness claim yet. No production changes, deployments, capture opening, approving GitHub review, protection bypass, history rewrite or human DCO certification occurred in this continuation.

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
- APP-2B core v2 fixes late native listener removal and a cross-context durable-hold/schedule race. Independent original 8-case replay passes; additional review found another lifecycle defect below. Native dependency-audit defects are also below. Neither package is claimed cleared.

## Current independent-review holds

LIB-5B [issue #61](https://github.com/global-soil-intelligence/gsip/issues/61) is five uncommitted files on `wp-lib-5b-private-exchange-ledger`. Root whole Python on exact v2 ran 1,068 passing tests, four existing GDAL skips, zero failures/errors; Ruff, mypy, lint and pinned authored scan passed. [Actual local v2 receipt](lib5b-root-v2-integration-validation.json), SHA-256 `b6e066f34d72dbc6bc75c77d895a0431ae7d21e6d183c7ef8b5a229ae9e09f50`. V2 closes the original metadata-saturation and exact-measurement-authority witnesses. Fresh full review still found an initial-admission defect: restrictions already known on sibling measurements are applied only on a later load. A sealed sibling permits one initial payload/charge; a synthetic-restricted sibling initially leaves the claim false. [V2 findings](lib5b-full-v2-independent-findings.json), SHA-256 `8846de78d4cf359f978f77060439cbef113258923cae4ee57ae891662f044bdd`, and [companion](lib5b-full-v2-independent-supplement.json), SHA-256 `4c7e1598ac5dba94fbb25c7b8968d0f549829aeadce54319d6004ef5105df607`. V3 correction and full 33-card closure are pending. Reduced serializer-budget projections are not claimed as actual 32 MB simulator fills; the store has separate actual-bound tests.

APP-2B [issue #62](https://github.com/global-soil-intelligence/gsip/issues/62) is isolated source only. It adds opt-in generic native sync reminders, without push, nearby/location features or a capture invitation when closed. CORE v3 has 242 authored capture cases, 81 Python checks, fourteen meaningful guard-removal mutations, static/closed-build results and author replay of 32 independent probes. The earlier listener, durable-hold and disposed-refresh findings are closed by those replays. Fresh independent review reproduces a final stale tap-focus callback after disposal; correction and independent final closure remain pending. Native builds and physical-device/iOS backup proof are unverified.

Native audit v3 closes the prior four path/POM/content-free-receipt/SPM-binding witnesses; independent original seven probes and 165 baseline tests pass. Expanded review still found a strict-comparison-receipt P2: empty comparisons, invalid reference/version values and unexpected nested fields can pass and reach output. [V3 native receipt](app2b-native-v3-independent-findings.json), SHA-256 `c4f0ee8a5cccb0728039c76373b9352cfaa85600a2b5073a5ca64c960aa9eaf4`. Five new refusal assertions fail and one positive control passes. V4 correction and expanded independent closure remain pending. No APK/simulator, native graph, size-delta or device pass is claimed for APP-2B yet.

Pinned proposed dependency `@capacitor/local-notifications` 8.3.1: MIT; published 2026-08-19; 82,938 compressed / 506,577 unpacked bytes; no JavaScript runtime dependencies; peer Capacitor >=8. Archive SHA-256 `f5772636102fdcbdba564a9bcb32db5d799bb6e27fdeaebc39b2abffe727c287`. Actual resolved Android/iOS licenses, native permissions, build impact and reproducibility need the new exact-head CI evidence. Package metadata alone is insufficient.

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

Fresh [GET-only source/hold audit](READ_ONLY_SOURCE_HOLD_AUDIT_20261013T150431Z.json), SHA-256 `5ef2ed93a5e5bfeb197237a20cb646830c6a1f67cc809c25e53d3804528053a8`, confirms main and all eight merge readbacks, reviewer `jdhart81`, bypass false, all five guards 404/missing-held and complete nonterminal inventory with zero worker runs. It reads no secret values and does not approve a waiting deploy.

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

Assumptions: standing keep-building/merge authority covers separately reviewed and green source packages only. Fake authority/transport and private test roots model local ordering, not real consent, useful scientific adoption, distributed erasure or physical verification. Local missing GDAL/Deno/Android SDK/Xcode results rely on actual CI; simulator artifacts never substitute for device evidence. Temporary CI-generated Gradle inspection is tooling emitted from maintained Python, not shipped app code; that assumption will be flagged in APP-2B's PR. Code remains MIT, data ODbL 1.0 and photos CC BY-SA 4.0.

[Preserved chronological progress/evidence](LANDING_AND_BUILD_REPORT_HISTORY_THROUGH_20261013T1348Z.md) contains superseded candidate states; use this report's current sections for readiness.
