#70 established the conditional iOS storage design. Justin approved its merge and the recommended passcode-required/preserve-quarantine/no-automatic-reset policy. This PR prepares the **exact requested native-code scope**: 21 prospective Swift files, three Python/CI support files, nine generated-template edit targets and 21 literal hash-preserving copy destinations for a separate synthetic APP-2C2A prototype.

**No Swift, harness, device operation or runtime implementation is added. The native-language exception and implementation go remain pending.** The accepted passcode/recovery choices are recorded without asking again. Current TypeScript/Python-only and all existing production/launch/device gates remain binding.

[Exact scope and API effects](https://github.com/global-soil-intelligence/gsip/blob/e9f5bade7a54601ded41ea7eda09e9b96c2c21bc/docs/IOS_NATIVE_SCOPE.md) · [Finite scope snapshot](https://github.com/global-soil-intelligence/gsip/blob/e9f5bade7a54601ded41ea7eda09e9b96c2c21bc/docs/ios-native-scope.json).

### Explicit invariants and acceptance

- [x] Preserve I1–I15, L1–L7 and B1–B8. SPEC sections 1–13, every prior section 15 requirement and the entire section 16 contract are byte-identical. All 138 prior acceptance lines/states remain unchanged; two new admission criteria stay unchecked. Exactly six paths change; all 371 other existing files/modes remain identical.
- [x] Enumerate every future native/support file, per-file imports and bounded API effects. No wildcard, extra source/module, new dependency/version, ordinary App wiring, signing/entitlement, network, data/SDK/migration/reset or real camera/picker/location capability is implied.
- [x] Isolate native prototype identities and future simulator work from the ordinary app/private data. Bind the separate generated core XCTest identity; no current Keychain/device/data access is authorized. Keep unsupported passcode-class behavior held, never replaced by a weaker class or fake platform pass.
- [x] Bind the core-only package, existing fresh Capacitor/Cordova linkage, fixed synthetic host/bridge/asset gates, disabled plugin/application-notification routing, exact disposable generated edits and source-copy map. Unknown template/API/build drift stops for scope review.
- [x] Require actual ordinary compiled-input/link-graph/bundle isolation evidence, rather than DEBUG-only or filename-only proof. No prototype/test/fault payload in ordinary artifacts; no native acceptance inferred from policy/source/CI/simulator results.
- [x] Independent final review closed: 131 related tests passed, 38 expected baseline failures, 21 external unsafe mutations rejected; all 377 final hashes/modes and prior normative/status boundaries verified. Separate core and host source-fact reviews closed without blockers.
- [x] Exact-head required hosted CI green (evidence below).

### Verification actually run

Full local lint (ESLint, language, Prettier), Ruff, strict mypy over 80 source files and diff whitespace passed. Related specification/storage/scope suite: 131 passed, no failures/errors/skips. The 38 new document/manifest contract tests failed on unchanged main as expected, with zero errors/skips; an independent reviewer repeated both outcomes. The tests check written scope/refusal boundaries and accept no native/device claim.

Pinned Gitleaks 8.21.2 scanned the non-shallow full history/all refs with redaction: zero findings; the approved ignore/config hashes are unchanged. No suppression/rule/workflow change. No local GDAL/PostGIS/pgTAP/Deno/native/device/backup result is claimed; hosted source CI supplies its disposable environment. These docs/tests paths do not trigger app-build artifacts.

### Changes after review

- An owned package host cannot rely on an npm-root Swift manifest that does not exist. Scope now uses a core-only package and a finite disposable App/XCTest host with the existing fresh resolved products. The old ignored generated graph is stale and is not CI proof.
- Explicitly bound constructor order: autoRegisterPlugins:false, descriptor handleApplicationNotifications=false before configuration/bridge creation, JSON ios flag false and readback. Core plugins/router still construct; no real notification management/callbacks in A, full parity held for B.
- A formatted draft initially missed that construction paragraph. Inserted it explicitly and added a section-local regression which failed on the missing paragraph before correction.
- Independent unsafe prose edits allowing SecItemDelete or URLSession initially survived global checks. Tightened the existing test around the actual Foundation/SQLite/Security prohibitions; both now fail, along with constructor and SQL-boundary corruptions.
- Named the exact core-package sibling and all 21 source-copy destinations, separately from nine template edits. Tests reject wrong, missing or aliased copies. Fixed one overlong test line and made wording checks insensitive to formatting-only line wraps; no detection or acceptance rule was weakened.

### What Justin is reviewing next

Approve or decline only the exact native-file/import/API-effect/support/generated-patch scope for a separately authorized synthetic APP-2C2A implementation. Any go should bind this reviewed commit and scope snapshot. Preparing or merging a scope proposal alone grants no implementation permission. Passcode-required and preserve-quarantine/no-automatic-reset policy are already approved and are not being asked again.

APP-2C2B actual queue/auth/reminder/camera integration, APP-2C2C legacy migration/recovery and APP-2C3 physical-device backup/restore remain separate. No backend, store readiness or production permission is selected.

### Assumptions and limits

- Justin authorized only #70 merge and exact-scope preparation under the accepted safeguards. No additional merge, production query/change, deployment approval, worker dispatch, capture/sign-in opening, account/signing, native API or device operation occurred.
- The 21-file split and nine-template/21-copy wiring are sufficient; all inherited AppDelegate/startup/callback paths can be safely held without another edit. If not, stop for amended scope, not extra files.
- Public host APIs, platform SQLite/Keychain modules and the existing verified iOS floor/toolchain can meet v12. Actual root containment, cross-store durability, simulator limitations and physical backup remain unproved. No weaker class/fallback/reset solves a failed mechanism.
- Existing remote/native products can be reused unchanged. Fresh actual resolution, source/binary hashes, platform/toolchain and transitive licence/maintenance/payload evidence are required in A; the observed local graph is not a universal lock. No new dependency/service or licence change. Prospective authored code remains MIT; system SQLite core is public domain, platform frameworks retain Apple terms. Actual app size delta is unmeasured until implementation.
- Counter/chunk/frame/managed-space bounds are proposed engineering limits, not measured capacity or memory performance. Core/host test identities differ and must each be verified before synthetic anchor access.
- Source/contract tests and compile/simulator/process-kill results cannot certify physical erasure, power loss or backup transport. Older provider-held backups remain outside retraction control. Legal/store, notification-device, calibration/publication, scientific and production/capture gates remain independent.
- Codex authored this proposal/integration/tests; independent agents reviewed source facts and adversarial boundaries. Justin remains human of record. No agent approval or DCO certification is asserted.


### Final exact-head CI and scope review evidence (2026-10-14)

Head `e9f5bade7a54601ded41ea7eda09e9b96c2c21bc`: [validate passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38655092072), [PR secret scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38655092125), [branch secret scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38655000926). DCO was skipped by the unchanged workflow; no agent certification is asserted.

CI verified 2,069 Python passes/31 skips/37 warnings, 12 browser passes, mypy 80 source files, 593 pgTAP assertions in 11 files, Deno and data-preserving migration suites 13/13, 19/19 and 13/13. Lint/typecheck/JavaScript/build/map-budget and disposable database lifecycle all passed. No native/device/backup acceptance is implied; no native artifacts are expected from these paths.

Final independent review repeated 131 related passes/38 expected baseline failures and rejected all 21 external unsafe mutations. All 377 blobs/modes match reviewed manifest `06710bba4738a0a4cebfea27b4c5d34ea282ad21fd40e80a5670e47970364402`; 371 existing files and all 138 prior acceptance states remain unchanged. Independent report SHA `723abe162abca417883687ab03994502899e51c1924227a5dc307d223155e6f4`; exact-commit closure SHA `cd9b1f64982206adab33090f415eaf581b4abf0ae35af0de76e67d239cae453f`. Exact parent, six paths, clean checkout, Conventional Commit and Codex co-author trailer verified; no Signed-off-by. Gitleaks 8.21.2 scanned 160 reported commits over non-shallow full history/all refs with redaction: zero findings, no scanner/ignore change.

#70 is merged at `6a652f94b220be7eeff49508283883c502baa527`, main CI green. This PR is open/unmerged, no auto-merge. Passcode and preserve-quarantine/no-automatic-reset policy are approved; exact native exception and implementation go remain pending. Pages is waiting behind sole reviewer jdhart81/admin bypass disabled; all five worker schedule enable-variable names remain absent. No production project operation, deployment approval, worker dispatch, capture/sign-in opening, native code/API, device/backup or account/signing action occurred. No scope implementation or readiness criterion is closed by this review package.
