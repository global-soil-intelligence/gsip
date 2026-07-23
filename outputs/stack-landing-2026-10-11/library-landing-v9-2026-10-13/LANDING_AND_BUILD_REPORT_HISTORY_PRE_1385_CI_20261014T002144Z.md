# GSIP landing and build report — refreshed 20261014T001153Z

The requested **#51–#56 are merged in order**, after exact-head green CI and only the approved one-fixture exception. Independently reviewed source follow-ups #58, #60, #64 and #65 are merged. Main remains **`7d6777fc219c48792b8e1e2f4912d5c276b477c1`**. The sync-reminder follow-up [draft #63](https://github.com/global-soil-intelligence/gsip/pull/63) is unmerged at **`e0cebc9eda6b7c4a6ae7134e3d4218d02cfe5c8d`**. Its fresh general CI, both scans and iOS artifact verification passed; Android failed at native audit and produced no uploaded APK. A concrete generated-archive and build-target correction is under independent review; it requires fresh checks and artifacts before merge.

**No production change, deployment, worker dispatch, capture opening, approving GitHub review, protection bypass, history rewrite or human DCO certification occurred.** All earlier failures and superseded states are preserved in [LANDING_AND_BUILD_REPORT_HISTORY_PRE_E0_CLOSEOUT_20261014T001153Z.md](LANDING_AND_BUILD_REPORT_HISTORY_PRE_E0_CLOSEOUT_20261014T001153Z.md); that historical report retains the full chronological receipts.

## Current APP-2B checks and remaining source work

| Exact e0 check | Result and evidence |
| --- | --- |
| [General CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38487570740) | SUCCESS; 1,682 Python passed / 30 tool-dependent skips, GDAL required; 597 JS / 44 files; 12 browser; 593 pgTAP assertions / 11 files; 2 Deno checks; lint, types, build, migration compatibility and map budget observed. Site-budget execution was not observed. [Independent terminal receipt](APP2B_E0_GENERAL_CI_CLOSURE.json), SHA-256 `d346f1f2b54a943a8c87b081fb26a1a48b22f0ad99607751c7892925402d3737` |
| [Native run 50](https://github.com/global-soil-intelligence/gsip/actions/runs/38487570722) / Android | FAILURE, job `115604811427`, step 18 native audit. No uploaded Android artifact. Safe fixed diagnostic identifies `android-project-sources / AUDIT_REFUSAL / source_line 198 / project_inputs 6`; it does not uniquely attribute the hosted cause to one local finding. Raw log was hashed and discarded, not printed or persisted. |
| Same native run / iOS | SUCCESS, job `115604811186`. Fresh artifact `11860605852`, 13,914,760 bytes, SHA-256 `8d4b29388ebe9e6f5733fe387c9f26745a495cf22ffc22fff227eeb760bfc41f`. Single-download digest, exact nine-source/parent bindings, four Swift package pins, native licences, repeat/reference ZIP proofs and byte-identical comparison regeneration passed. [Independent receipt](APP2B_E0_IOS_ARTIFACT_CLOSURE.json), SHA-256 `f22bf3832b0e2916d5822f3048da2d430cbf1b6cb4a4195426c63bd811b7c629`. This is e0 evidence only; the next corrected source requires fresh iOS evidence too. |
| [PR scan](https://github.com/global-soil-intelligence/gsip/actions/runs/38487570698) and [push scan](https://github.com/global-soil-intelligence/gsip/actions/runs/38487563868) | SUCCESS, pinned gitleaks 8.21.2, 150 reported commits each / no leaks. No new suppression. |
| [DCO](https://github.com/global-soil-intelligence/gsip/actions/runs/38487570885) | SKIPPED under unchanged same-repository policy; not a human certification. |

Actual local Gradle producers revealed the additional `compile_library_classes_jar/.../classes.jar`: it contains exactly the same verified 330-byte generated resource stub as the existing allowed R archive. The next narrow guard change will recognize only that precise owned debug/release role through the unchanged strict content validator; altered classes, extra payload and unrelated archives remain refused.

Actual task-graph dry runs on both the exact d7 parent and candidate additionally show that unqualified `assembleDebug` selects the empty Cordova library's own `bundleDebugAar`; `:app:assembleDebug` omits the non-app aggregate/bundle tasks while retaining the identical 43 app tasks and required compile-library producer. The proposed four workflow target qualifications preserve all flags, checks and app transitive dependencies, and preserve the ban on AARs in the supposedly empty generated project. [Dry-run receipt](APP2B_ACTUAL_APP_TASK_SCOPE_DRY_RUNS.json), SHA-256 `ad75f7562de39abbe37c34dd9df1a540ab0b7c5e62fea77696757aaf68b47eb8`. This is task-graph proof, not a full APK/device result. The combined fix is still isolated, uncommitted and subject to independent review.

The PR remains draft and its native acceptance box remains unchecked. The preceding iOS successes, local collector results and source reviews cannot substitute for corrected-head Android/iOS artifacts.

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

The original four `.gitleaksignore` lines are byte-identical, with only the owner-approved historical noncredential fixture fingerprint appended:

```
bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32
```

The five-line file's SHA-256 is `bb3e40f995ae51b8e1b9300bd2d079aa5a1b482f259642f52074366b908310e5`. Commit `173e19363df60d029b2ffeb4a7df2e27d6ccd6b6` owns the exception and authority record, propagated forward without rewriting. Scanner rules, configuration, redaction, workflow and full-history coverage remain unchanged. Every additional suppression requires explicit owner approval. The pinned 8.21.2 before/after and new-fingerprint negative witness remain in [scan proof](PRE_MERGE_SCAN_PROOF.json) and [negative witness](future-fingerprint-negative-receipt.json).

The latest actual local full-history scan after e0 covered **150 scanner-reported commits, zero findings**, with unchanged five-line ignore file: [receipt](APP2B_REVIEWED_NATIVE_FULL_HISTORY_SCAN.json), SHA-256 `ea1630c219838960d79d1b1d0e7577883562ce4d09a5ebac325e8573a94620af`. The four authored files also passed an ignore-inline-disabled 8.21.2 scan: [receipt](APP2B_ROOT_FINAL_FOUR_AUTHORED_SCAN.json).

## Changes after review

The complete prior change register, findings, reasons and immutable evidence are preserved in [LANDING_AND_BUILD_REPORT_HISTORY_PRE_E0_CLOSEOUT_20261014T001153Z.md](LANDING_AND_BUILD_REPORT_HISTORY_PRE_E0_CLOSEOUT_20261014T001153Z.md). Current e0 changes, committed conventionally with the Codex trailer and normally pushed, are:

- Android inspection uses separate public artifact views for raw module binaries and typed non-root project classes, retaining the original graph/consumer attributes, exact pinned AGP gate, both views' lazy producer dependencies and strict completeness. Unknown AGP and missing/ambiguous inputs still refuse.
- Empty Cordova input inspection rejects source/native binaries, links, hardlinks, FIFOs, unreadable subtrees and unrelated archives. It recognizes only bounded canonical empty runtime ZIPs and the exact verified generated R stub in owned roles. Earlier root findings for swallowed walk errors and standalone `.so` files were fixed with failing-before tests. The newly exposed compile role above remains the next fix.
- Six exact public POM contexts classify pre-existing runtime licences by complete identity, digest/size, packaging, parent and full ordered declarations. Generic vague aliases remain refused in both collection and offline replay. No dependency or project licence changes; factual classification is not legal or distribution approval. [Independent classification closure](APP2B_REVIEWED_NATIVE_V3A_CLASSIFICATION_CLOSURE.json), SHA-256 `1e11ec2c4fab261c0e2c94c70dd9695754e40acc5776a364703b75a4dc648316`.
- The privacy draft adds one row for four passive public licence-reference hosts. Reviewers may visit them manually; the app and collector do not request those links. The initial full Python run caught the missing notice row. The existing host check was preserved, the notice corrected, and all six processor checks passed. [Independent closure](APP2B_PRIVACY_REFERENCE_HOSTS_INDEPENDENT_CLOSURE.json), SHA-256 `f8e3cd0fc1474f8db1dc20c5fe01cbad1dc1c7d6e2adf1b62a42e381f04c82c5`. Counsel gates remain open.

Root's full e0-source Python run actually produced **1,707 passed, one privacy-documentation failure, four existing GDAL skips**, including **all 30 real Gradle controls executed/passed**. That failure is retained in [original receipt](APP2B_ROOT_REVIEWED_NATIVE_V3_PYTHON_CHECKS.json) and [XML summary](APP2B_ROOT_REVIEWED_NATIVE_V3_XML_INITIAL_FAILURE.json). After the notice-only correction all six existing processor checks passed, together with lint/language/diff checks: [remediation](APP2B_ROOT_PRIVACY_GATE_REMEDIATION.json). No second atomic all-pass local full-suite result is claimed. The fresh hosted e0 general run above is separately terminal and green.

Ruff lint, mypy (75 files), pnpm lint, language and diff checks ran successfully: [static receipt](APP2B_ROOT_REVIEWED_NATIVE_V3_STATIC_CHECKS.json). Optional nonrequired Ruff formatting had existing baseline and candidate failures; it is not reported as a pass or used to rewrite retained tests.

Both actual Android roots passed genuine runtime collection with exact final e0 helper before later producer probes introduced the new compile archive: 75 modules per configuration, 78/79 binaries and 150 selected POM-chain validations per root. [Independent actual collector closure](APP2B_REVIEWED_NATIVE_V3A_ACTUAL_COLLECTORS_CLOSURE.json), SHA-256 `da4309e66bbddcdc553680c7ec72a13ec7fd32f740c202b5f8715e2ff42ce352`. Those inputs are not a full APK or whole-native acceptance, and replay with the newly generated compile archive requires the pending corrected guard.

[Commit receipt](APP2B_REVIEWED_NATIVE_FIX_COMMIT.json), [push/append-only PR description receipt](APP2B_REVIEWED_NATIVE_FIX_PUSH.json). Original description prefix is preserved; 361 unrelated source files were unchanged by e0. No native acceptance was ticked. Existing core listener/lifecycle/queue/tap fixes, diagnostic observer, strict iOS package/source proofs and original independent closures remain detailed in the preserved report and PR.

## Deployment checklist and source boundary

No Supabase, secret-value or production query occurred in this continuation. Earlier production Gate A–D receipts are historical and do not establish current database/API health.

| Step | State |
| --- | --- |
| Database and Edge Functions | No migrations, deployments or hosted smoke tests; any next step requires exact target/commands and separate owner go |
| Repository variables/secrets | No changes or secret-value reads |
| Rights / QA / export / cleanup / prior workers | No dispatch; all five schedule guards missing/held at latest successful readback |
| Tiles / Hugging Face | No publication or upload; separate gates remain |
| Pages | Owner-only approval required; admin bypass disabled; no approval or deployment by this work |
| Capture / anonymous sign-in / photos | No opening; launch, screening and calibration gates remain |

[GET-only source readback at 00:05 UTC](READ_ONLY_SOURCE_HOLD_AUDIT_20261014T000552Z.json), SHA-256 `7ed81030d021cc1d1831b7c8937cdbddfe8650b7770c3b06d964e02c4cab1b67`, confirms unchanged main7d, all ten merged PRs, Pages sole reviewer `jdhart81` / bypass false, and all five guards missing/held. The nonterminal listing changed during collection (count/list mismatch), so **that snapshot is incomplete** and is not proof of absence of worker runs. A later sandbox network-unavailable attempt is preserved as unavailable, not zero. A complete GET-only refresh at 00:10 UTC subsequently confirms unchanged main7d/all ten merges, sole Pages reviewer and bypass false, five missing/held guards, and a complete nonterminal inventory with zero worker runs: [receipt](READ_ONLY_SOURCE_HOLD_AUDIT_20261014T001054Z.json), SHA-256 `1476aabf712823ca8218f6781f2afe9ad66670a644d84579c948b8af84457dfd`. No deployment approval follows from these readbacks.

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

Assumptions: standing keep-building/merge authority covers separately reviewed and green source packages only. Fake authority/transport and private test roots model local ordering, not real consent, useful scientific adoption, distributed erasure or physical verification. Local missing GDAL/Deno results rely on actual CI; Android SDK presence outside PATH and an actual local inspection have now been verified, but no local APK/signing or current hosted Android acceptance is proved. Local Xcode version is verified but no local iOS native build ran; simulator artifacts never substitute for device evidence. Temporary CI-generated Gradle inspection is tooling emitted from maintained Python, not shipped app code; that assumption will be flagged in APP-2B's PR. Code remains MIT, data ODbL 1.0 and photos CC BY-SA 4.0.

