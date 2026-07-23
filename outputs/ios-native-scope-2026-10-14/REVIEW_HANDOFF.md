# Exact iOS native scope review handoff — 2026-10-14

Owner instruction: merge #70, prepare exact native-code scope, use the recommended passcode/recovery safeguards. No production changes or capture opening.

## Source outcome and next review

- [#70](https://github.com/global-soil-intelligence/gsip/pull/70) merged exact approved head `06902edf36810c55e51b169dcb813e81b22206b0` at `6a652f94b220be7eeff49508283883c502baa527`, 2026-10-14 23:13:31 UTC. Conventional merge metadata and Codex trailer verified; no Signed-off-by, history rewrite or protection bypass.
- Main [CI passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38652748021) and [secret scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38652748032).
- [#71](https://github.com/global-soil-intelligence/gsip/pull/71), `docs/spec-v13`, head `e9f5bade7a54601ded41ea7eda09e9b96c2c21bc`, is the exact native-code scope proposal. It remains open/unmerged. Final hosted CI status is appended after readback below.
- Passcode-required and preserve/quarantine/no-automatic-reset safeguards are approved by Justin. Do not re-ask those choices. Only the exact native-file/import/API-effect/support/generated-patch exception and synthetic implementation go await review. Preparing/merging a scope document alone grants no code/data/device/production authority.

## Scope prepared, not implemented

The proposal lists 21 future Swift paths (one core-only package manifest, ten sources and ten direct test/helper files), three future Python/CI support paths, nine disposable template-edit targets and 21 one-to-one hash-preserving source-copy destinations. Every import and effect is bounded; source copies and editable templates are separate. No Swift/support/harness implementation file exists in this change. All ordinary application code/configuration/workflows/locks and Android rules are unchanged.

The host uses a fresh nonpersistent view and the existing resolved Capacitor/Cordova products; npm's iOS directory is not a standalone Swift package. It uses its own synthetic bundle/root/Keychain identities, a separately verified core XCTest runner identity, constructor plugin and application-notification controls and exact frame/plugin/method/asset capabilities. No normal App registration, SDK/queue integration, legacy migration/reset, network, real camera/picker/location, signing, entitlement or device/backup action is included.

A is an isolated synthetic primitive/host prototype. B actual client/session/reminder/camera integration, C isolated legacy migration/recovery and C3 physical-device backup/restore remain separate. No backend adoption/store readiness follows from source, mocks, compile, simulator or process-kill success.

## Changes after review and why

1. Core-only Swift package and copied current generated graph replace the invalid assumption that npm @capacitor/ios has a root Package.swift. Fresh native inputs must be checked; the ignored old generated graph is stale.
2. Added explicit autoRegisterPlugins:false and descriptor/JSON handleApplicationNotifications false before configuration/bridge construction, with readback. Core plugins/NotificationRouter still construct; no real notification operations in A. Core test-runner identity is not assumed equal to the prototype App.
3. A formatted draft initially missed the construction paragraph despite JSON flags. Inserted it with a checked unique anchor; a new section-local regression failed on that pre-fix document and passed after correction.
4. Unsafe prose changing No SecItemDelete/No URLSession to Allow survived initial global guards. Pinned actual per-effect prohibitions; both now fail. Final independent review rejects all21 external unsafe mutations, including constructor, SQL and copy-boundary edits.
5. Named the core sibling and all21 copy destinations separately from nine patch targets; reject wrong/missing/aliased destinations. Fixed the initial overlong test line and normalized formatting-only whitespace for prose checks without weakening semantic requirements.

## Verification actually run

Local full lint (ESLint, language, Prettier), Ruff, strict mypy80 files and diff whitespace passed. Related suite131 passed, zero failures/errors/skips. Final38 new tests fail on unchanged main as expected, zero errors/skips, independently repeated. The tests validate a document/manifest contract, not actual native storage behavior.

Independent review bound all377 final blobs/modes,371 unchanged existing files, prior normative content and all138 prior acceptance lines/states. Two new admission criteria remain unchecked. Exactly six paths changed; native-design edits record only owner approval/status. Final manifest SHA `06710bba4738a0a4cebfea27b4c5d34ea282ad21fd40e80a5670e47970364402`; independent review SHA `723abe162abca417883687ab03994502899e51c1924227a5dc307d223155e6f4`; exact-commit closure SHA `cd9b1f64982206adab33090f415eaf581b4abf0ae35af0de76e67d239cae453f`.

Core fact closure SHA `53aabfbb67a0c8788893940540eed5dcf884f97b4c678dea0ee6b934105c13d4`; host/build fact closure SHA `f05bef4e76730b63f2471f58a1a9e7c327f84fc2b39eff2a9061f97f755f32c7`. Receipts preserved here. Earlier draft mismatch/survivor records remain in private review evidence and are not called final passes.

Gitleaks8.21.2 scanned160 reported commits over non-shallow full history/all refs with redaction:zero findings. Ignore SHA `bb3e40f995ae51b8e1b9300bd2d079aa5a1b482f259642f52074366b908310e5`; config SHA `e846bacbb1ce5c41f571a10cdaf0e1fde7bfa399fc5c876480b57124059cc760`; unchanged. No suppression/rule/workflow weakening.

No local GDAL/PostGIS/pgTAP/Deno/native/device/backup claim is made for this docs-only scope. Required hosted source CI supplies its disposable database/tools; no native artifacts are expected from these paths.

## Deployment/activation checklist for this turn

| Item | State/evidence |
| --- | --- |
| Production project/database/functions/Auth | Held; no production project API/CLI access, query or change. Production counts/advisor/capture state not refreshed or re-certified. |
| Capture/library/sign-in opening | None performed. Ordinary source activation flags remain unchanged/closed. |
| Pages | [#70 main run](https://github.com/global-soil-intelligence/gsip/actions/runs/38652748052) waiting behind sole reviewer jdhart81; admin bypass false. No approval or deployment performed. |
| Workers | All five GSIP_PRIOR/EXPORT/QA/RIGHTS/CLEANUP_SCHEDULE_ENABLED names remain absent; no dispatch. Observed scheduled cleanup run was skipped. |
| Native/code/device | No native code or API, simulator, generated project, private application data, Keychain, signing/account or physical-device action. Exact exception/implementation go pending. |
| Merges | #70 only, explicitly authorized. #71 remains unmerged; no auto-merge. |

## Pending decision and assumptions

Next: Justin reviews #71 and its exact scope; approve or decline a narrow synthetic A exception/go bound to the reviewed commit and complete MD/JSON scope. The recommended course is this finite prototype; alternative is keep iOS held and revise scope/mechanism. Already accepted passcode and preservation policy are resolved.

Assumptions: the finite file split and generated wiring suffice; inherited AppDelegate/startup paths can be held without another source edit; public native APIs/system modules/floor can meet v12; fresh selected dependency graph matches reviewed inputs; ordinary compiled/link/bundle exclusion can be proven. Any failed assumption stops for amended scope. Planned counters/chunk/frame/storage bounds are not measured capacity. Actual native/transitive licences, maintenance dates, payload and app delta must be measured in A. No new third-party service/package, licence change or scientific claim.

Existing production, legal/store, notification-device, calibration/publication, real sharing, account/signing and capture decisions retain their prior gates. No operation in this preparation opens them.

## Final hosted CI closure

Exact head `e9f5bade7a54601ded41ea7eda09e9b96c2c21bc`: [validate passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38655092072), [PR scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38655092125), [branch scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38655000926). Required checks green; DCO skipped by unchanged workflow, not agent-certified. Hosted results: 2,069 Python passed/31 skipped/37 warnings; 12 browser passed; mypy80 files; 593 pgTAP assertions/11 files; Deno; existing-data migration suites13/13,19/19,13/13. All lint/typecheck/JavaScript/build/map-budget and disposable database steps passed.

Final readback: main still `6a652f94b220be7eeff49508283883c502baa527`, #71 OPEN/unmerged/no auto-merge, Pages waiting with sole jdhart81 reviewer/admin bypass false, all five worker schedule enable names absent. No production project, native/device/backup, signing/account, deployment/dispatch or capture opening action occurred. Saved final check/job, main, Pages/variable and safe test summary readbacks here. #70 description received an appended owner-merge/policy/main-CI record; #71 description preserved with its CI checkbox completed and final evidence appended.

Next action: Justin reviews #71's exact native exception/prototype scope. The accepted passcode/recovery policy is resolved; native implementation remains held for a separate exact go. No other PR was merged.
