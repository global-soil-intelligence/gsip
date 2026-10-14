# Exact native prototype scope for review

**Status: scope proposal only, 2026-10-14. Native-code exception remains pending. No native implementation.**
Justin approved and merged [#70](https://github.com/global-soil-intelligence/gsip/pull/70),
main `6a652f94b220be7eeff49508283883c502baa527`. The v12 design direction and recommended
**passcode and recovery safeguards are approved**: require the exact passcode-bound anchor;
preserve/quarantine uncertainty; no automatic destructive reset, rollback to fit an older store,
weaker anchor class, silent new account or implicit permission to read existing private data.
Do not re-ask these choices. Only the exact native-code/file/effect scope below awaits review.

This document requests a narrow APP-2C2A exception, not implementation permission by itself.
[The machine-readable snapshot](ios-native-scope.json) enumerates **21 prospective Swift files**
and **three new Python/CI support files**. None is created here. TypeScript/Python-only remains
binding until Justin explicitly grants this exact exception and prototype go. No Objective-C,
C/C++, custom module map/header, core fork, new package/service, signing/account action or licence
change is included. I1–I15, L1–L7, B1–B8 and every prior launch/device/production gate remain.

## 1. Finite native files

All paths in this table are relative to the single prospective tracked prefix
`apps/capture-pwa/native/ios/GSIPPrivateStorePrototype/`. This is outside ignored generated
`ios/`; no folder, wildcard, sibling file or future module is implicitly authorized.
Every file remains MIT. Swift standard-library use is implicit; listed imports are ceilings,
not permission for every API in a framework. Omit unused imports. Any added native file/import,
platform, capability or generated edit requires a new review; stop for amended scope.

| Exact relative path                                                         | Responsibility and maximum imports                                                                                                  |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `Package.swift`                                                             | Core-only library/test manifest; PackageDescription only                                                                            |
| `Sources/GSIPStorageCore/StorageContract.swift`                             | Fixed bounded request/outcome/six-store types; Foundation                                                                           |
| `Sources/GSIPStorageCore/ExcludedSQLiteStore.swift`                         | Excluded-root identity, fixed SQLite/staging/receipt operations; Foundation, Darwin, SQLite3, CryptoKit SHA256                      |
| `Sources/GSIPStorageCore/KeychainAnchor.swift`                              | Exact synthetic anchor and nonce API; Foundation, Security                                                                          |
| `Sources/GSIPStorageCore/StorageCoordinator.swift`                          | Serial admission/pending/commit/clean/ack protocol; Foundation, Dispatch                                                            |
| `Tests/GSIPStorageCoreTests/ExcludedSQLiteStoreTests.swift`                 | Owned-root/SQLite conformance and faults; XCTest, Foundation, Darwin, SQLite3, GSIPStorageCore                                      |
| `Tests/GSIPStorageCoreTests/KeychainAnchorTests.swift`                      | Exact class/attributes/errors and fake/platform separation; XCTest, Foundation, Security, GSIPStorageCore                           |
| `Tests/GSIPStorageCoreTests/StorageCoordinatorTests.swift`                  | State/ordering/race/exhaustion faults; XCTest, Foundation, Dispatch, GSIPStorageCore                                                |
| `Tests/GSIPStorageCoreTests/NativeTestDoubles.swift`                        | Injected bounded synthetic root/anchor/clock/nonce/fault fixtures; Foundation, GSIPStorageCore                                      |
| `Sources/GSIPStorageHostPrototype/PrototypeHostController.swift`            | Held owned UIViewController/CAPBridgeDelegate and all startup paths; Foundation, UIKit, WebKit, Capacitor, Cordova, GSIPStorageCore |
| `Sources/GSIPStorageHostPrototype/BridgeMessageGate.swift`                  | Main-frame exact plugin/method/argument allowlist; Foundation, WebKit, Capacitor, GSIPStorageCore                                   |
| `Sources/GSIPStorageHostPrototype/AssetRequestGate.swift`                   | Owned bundled asset and opaque canary capability routes; Foundation, WebKit, Capacitor, GSIPStorageCore                             |
| `Sources/GSIPStorageHostPrototype/PrototypeDelegationHandler.swift`         | Deny cookie prompts, remote navigation/popups and unsafe ingress; Foundation, UIKit, WebKit, Capacitor, GSIPStorageCore             |
| `Sources/GSIPStorageHostPrototype/OwnedTemporaryPhotoBroker.swift`          | Native-created synthetic canary to opaque lease-bound handle only; Foundation, Darwin, CryptoKit SHA256, GSIPStorageCore            |
| `Sources/GSIPStorageHostPrototype/PrototypeStorePlugin.swift`               | Fixed typed synthetic operations over admitted coordinator; Foundation, Capacitor, GSIPStorageCore                                  |
| `Tests/GSIPStorageHostPrototypeTests/PrototypeHostControllerTests.swift`    | First-navigation/scene/storyboard/lifecycle holds; XCTest, Foundation, UIKit, WebKit, Capacitor, Cordova, GSIPStorageCore, App      |
| `Tests/GSIPStorageHostPrototypeTests/BridgeMessageGateTests.swift`          | Raw bridge, frame, alias, size and stale-lease bypass attempts; XCTest, Foundation, WebKit, Capacitor, GSIPStorageCore, App         |
| `Tests/GSIPStorageHostPrototypeTests/AssetRequestGateTests.swift`           | Traversal, alias, symlink, root and expired-handle refusal; XCTest, Foundation, WebKit, Capacitor, GSIPStorageCore, App             |
| `Tests/GSIPStorageHostPrototypeTests/PrototypeDelegationHandlerTests.swift` | Prompt/cookie/navigation/extra-host bypasses; XCTest, Foundation, UIKit, WebKit, Capacitor, GSIPStorageCore, App                    |
| `Tests/GSIPStorageHostPrototypeTests/OwnedTemporaryPhotoBrokerTests.swift`  | Native-origin synthetic ownership/lease/cleanup; XCTest, Foundation, Darwin, CryptoKit SHA256, GSIPStorageCore, App                 |
| `Tests/GSIPStorageHostPrototypeTests/PrototypeStorePluginTests.swift`       | No caller SQL/path/authority; typed-operation and reply fences; XCTest, Foundation, Capacitor, GSIPStorageCore, App                 |

`Package.swift` declares exactly `GSIPStorageCore` and `GSIPStorageCoreTests`, explicit source
lists, no resources/executable/plugin/binary target or external dependencies. Host sources/tests
are compiled only in the disposable generated App/XCTest harness below, not host SwiftPM targets.
The npm `@capacitor/ios` 8.5.2 directory is **not a standalone Swift package**; it has no root
Package.swift. Do not invent a local dependency on it. Use the freshly generated existing
CapApp-SPM Capacitor/Cordova products without changing their remote/version selection. The old
ignored local graph lacks notifications and is observational/stale, not a current CI lock.

## 2. Bounded effects and fixed identities

- Foundation: bounded value/byte coding and owned-root resource/protection metadata only.
  No URLSession, external URL load, arbitrary directory traversal, UserDefaults/session/cache
  persistence or private logging. Darwin is confined to no-follow/descriptor/identity/metadata
  checks under the synthetic root; no process/exit/socket or generic native syscall bridge.
- SQLite3: system SDK module/link only, one serialized connection, fixed prepared operations;
  exclusion/complete protection readback before open/recovery, actual DELETE/EXTRA/foreign-key/
  memory-temp readback, bounded busy/full/corrupt/IO handling and sidecar placement. No caller
  SQL/PRAGMA/path, ATTACH, extensions, VACUUM, global temp override or hot-journal deletion.
- Security: exact service/account/class queries for the prototype's own anchor only. Read
  value/attributes; add only an explicitly seeded synthetic initial fixture; update without
  delete/add; bounded SecRandomCopyBytes. No SecItemDelete, broad query, sharing group, personal
  Keychain search, biometric/Secure Enclave feature or session/token storage. Default access group
  only, `kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly`, synchronizable false. Missing/locked/
  unknown or unsupported simulator behavior holds; no weaker class or fake device pass.
- Dispatch: one coordinator serial executor and bounded timeouts/callbacks. CryptoKit: SHA256
  integrity only. No encryption/key-derivation feature or additional framework/library beyond
  the explicitly listed system modules. All counters,
  generations and epochs are nonnegative JS-safe integers through `9,007,199,254,740,991`;
  exhaustion holds rather than wraps. The v12 128 KiB chunk/512 KiB frame/256 MiB managed bounds
  remain provisional prototype capacities; no eviction/truncation or measured-memory claim.
- UIKit/WebKit/Capacitor/Cordova: owned holding root, fresh nonpersistent host and supported public
  handler/delegate/asset seams only, installed before first navigation. Allow only synthetic
  typed operations; deny raw/core cookie/HTTP/WebView mutation, class-name aliases, Cordova
  dispatch, other frames/origins, popups and alternate persistent hosts. Importing Cordova for
  public bridge types grants no Cordova-message route. No upstream swizzling/fork/private API.
  Construct the public bridge with `autoRegisterPlugins:false`. Set the public descriptor's
  `handleApplicationNotifications=false` before InstanceConfiguration/bridge construction and
  verify the readonly configuration; the synthetic JSON also sets `ios.handleApplicationNotifications:false`.
  Automatic registration control skips the generated package list only; core plugins and NotificationRouter are still constructed.
  Routing false prevents that router installing itself; neither flag disables every side effect
  or removes OS notifications. A performs no real pending/delivered enumeration, scheduling, cancellation or callbacks;
  full notification parity remains B.
- The temporary-photo broker tests only a native-created synthetic canary. It calls no camera,
  photo picker, gallery, location or ION camera API and imports no camera dependency. Real camera
  output provenance remains a separately reviewed B-stage interface gate, not a hidden A feature.

Fixed proposed host bundle: `com.globalsoilintelligence.app.storageprototype`. Core package
XCTest may have a different generated test-runner identity: bind/validate that fresh iOS runner
and its ordinary default group before any synthetic anchor call; never assume the host ID covers
both or use the ordinary app identity. The runner creates
`Library/GSIPStoragePrototype-v1/<native-run-nonce>` with database `gsip-app2c2a.sqlite3`.
Keychain service is `com.globalsoilintelligence.app.storageprototype.synthetic.v1`, account
`anchor-<native-run-nonce>`; all queries require both exact native-created identifiers.
No JS-provided nonce/path selects a namespace. Never use ordinary `com.globalsoilintelligence.app`
identity/root/session/UID or existing contributor data. Only generic outcomes/counts leave tests.

A has no ordinary auth SDK/client, endpoint configuration, network, capture/location or existing
private-data discovery. Its six-store-shaped canaries are not the actual TypeScript adapter.
Pending-plus-old/mismatch/unknown state preserves/quarantines; clean matching synthetic restart
may work offline. No automatic account, first-run initialization, reset, rollback-to-fit or erasure
UX. Harness-only fixture seeding is not an app initialization API and is never bridge-callable.
Independent runner cleanup may destroy only its own disposable synthetic simulator/root after
recording bounded results; this grants no native reset API or personal/ordinary-data deletion.

## 3. Exact support files and disposable generated edits

These **three prospective new support files** are the whole code/CI support scope:

| Exact path                                    | Permitted work                                                                                                                                                                                      |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/ios_storage_prototype.py`            | Python standard-library harness creation, source/template binding, fixed tool invocation, synthetic-only result classification and compile/link/bundle inspection                                   |
| `tests/test_ios_storage_prototype.py`         | Synthetic generator/template-drift/path/scope/artifact policy regressions; no native proof inferred from mocked tools                                                                               |
| `.github/workflows/ios-storage-prototype.yml` | Isolated macOS iOS-simulator prototype CI, existing action/tool versions only, contents:read and checkout persist-credentials:false; no secrets/environment/deploy/signing/job permission expansion |

Existing `app-build.yml`, app_build/app_permissions/native-audit helpers/tests, application
TypeScript/configuration, package manifests/lockfiles and Android rules remain unchanged. Native
source paths already match the existing app-build `apps/capture-pwa/**` trigger; no trigger/check
weakening is needed. The new prototype workflow must neither dispatch a production workflow nor
consume Supabase/GitHub/HF credentials beyond the standard read-only checkout/artifact mechanism.
Upload bounded sanitized receipts only, not app/SQLite/Keychain/fault/temporary payloads or raw
XCTest result bundles. Raw native output must be captured privately and screened before any
publication; test assertions/logging must not print canary payloads, paths or session-like values.

The helper receives a **fresh runner-owned disposable copy**, never ordinary generated App or
existing simulator/app data. Pin exact CLI version, source/templates and every generated preimage;
reject changed/missing/duplicate/unknown template anchors, links, special files and traversal before
writes. The inspected 8.5.2 iOS SPM template archive is 155,545 bytes, SHA256
`a00e318f82fcaa9bc5fa7d851fa1ce1f3a15ae59147b703afbed5dff6279556d`.
This is source/layout evidence, not a fresh native-resolution/build guarantee. Fresh actual
Package.resolved, binary/source checksums, platform floor/toolchain, licence/maintenance/payload
and selected plugin graph must match reviewed inputs; no silent new version/dependency/minimum OS.
The inspected floor is iOS15; retain the verified fresh floor or stop for amended scope.

Only these nine relative generated targets may be edited/created, inside that disposable copy:

| Exact generated target                                                   | Allowed semantic patch                                                                                                                                                                          |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `App/App.xcodeproj/project.pbxproj`                                      | Exact listed host/test compile inputs, core local-product linkage, one XCTest target, synthetic bundle identity and unsigned simulator build/test settings; retain OS/permission/privacy policy |
| `App/App/SceneDelegate.swift`                                            | Replace direct stock CAP startup/proxy forwarding with the held prototype root and synthetic lifecycle gate                                                                                     |
| `App/App/Base.lproj/Main.storyboard`                                     | Replace the sole stock root with the same held prototype controller; no alternate bootstrap                                                                                                     |
| `App/App/Info.plist`                                                     | Synthetic identity/display and required existing scene/storyboard references only; no entitlement/background/privacy relaxation                                                                 |
| `App/CapApp-SPM/Package.swift`                                           | Add only local GSIPStorageCore product/linkage; rebase existing local plugin paths if moved; preserve every remote/version/native selection                                                     |
| `App/App.xcodeproj/xcshareddata/xcschemes/GSIPStoragePrototype.xcscheme` | New explicit App/XCTest simulator scheme only; no signing/device destination                                                                                                                    |
| `App/App/public/index.html`                                              | Create inert synthetic probe HTML in an initially empty private public directory; no PWA/SDK/endpoint bundle                                                                                    |
| `App/App/public/gsip-activation.json`                                    | Exactly capture false and library-intake false                                                                                                                                                  |
| `App/App/capacitor.config.json`                                          | Synthetic identity, logging none, ios.handleApplicationNotifications false and no remote app/endpoint configuration                                                                             |

The **nine generated-template patch targets** above are distinct from **21 hash-preserving
source-copy outputs**, each fully enumerated by `generated_copies` in the JSON snapshot:

- The nine core package/manifest/test files copy to the literal sibling `GSIPPrivateStorePrototype/`
  relative to the disposable harness root, preserving each relative path from §1. Its manifest
  destination is exactly `GSIPPrivateStorePrototype/Package.swift`; its source/test subdirectories
  are exactly `GSIPPrivateStorePrototype/Sources/GSIPStorageCore/` and
  `GSIPPrivateStorePrototype/Tests/GSIPStorageCoreTests/` with only the listed basenames.
- The exact six host files copy to `App/App/GSIPStorageHostPrototype/` with their listed basenames.
- The exact six host-test files copy to `App/GSIPStorageHostPrototypeTests/` with their listed basenames.

These are 21 one-to-one, byte/hash-preserving copies, not authority to copy arbitrary sibling
files or create another package destination. They do not overlap the nine template-edit targets.
Omit the ordinary public tree while constructing the disposable copy; write only the two exact
generated public files above. This does not authorize deleting unlisted assets from an existing copy. Other tool-owned DerivedData/resolution
outputs are confined to the new run's build area, not additional source-edit permission.
`AppDelegate.swift` is not editable. Prove its inherited callback paths cannot bypass admission;
if it or any extra controller/target/native file requires change, stop for amended scope.
A package link, host target, XCTest loader or startup incompatibility is a held result, not
permission to expand this list. No generated native files are committed.

## 4. Tests and evidence needed from a later authorized A build

| Layer                  | Required proof and limit                                                                                                                                                                                                                                    |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Root/SQLite            | Exclusion/protection before open/recovery, setter/readback failure, root replacement/symlinks, sidecars/scratch, actual settings/limits, busy/full/IO/corruption, atomic six-store-shaped clears, receipts/staging/quota/counter exhaustion                 |
| Anchor/coordinator     | Exact query/class/sync/default-group handling, no delete/add/weaker fallback, pending/commit/clean/ack interruption/lost replies, matching committed receipt vs pending-old quarantine, stale owner/generation/revision/auth/lease and concurrent callbacks |
| Host/bridge/delegate   | Both startup paths, before-first-navigation holds, nonpersistent store/no cookie observer, raw bridge/prompt/class aliases, frames/origins/unknown methods/size bounds, stale leases and alternate host/navigation attempts                                 |
| Asset/canary/plugin    | Opaque native-created ownership, path/root/traversal/alias/symlink/expiry denial, no raw path/SQL/authority, private callback cleanup boundaries; actual camera remains held                                                                                |
| Generator/CI/artifacts | Every source/template and generated pre/post hash, finite patch membership, no ordinary assets/SDK, no normal-app registration, native compile/test inputs and link graph plus built-bundle exclusion of prototype/tests/fault hooks/canaries               |

Normal app isolation needs actual compiled-input/link-graph/bundle evidence bound to its exact
ordinary artifact and source, not a DEBUG flag, name-only string scan or absence from one directory.
The new workflow may build a second untouched ordinary generated copy to obtain that evidence;
it must not patch or replace its normal build rules. The synthetic app is never packaged for
Pages/store release or uploaded as a normal app artifact. Test/fault targets do not enter any
ordinary artifact in either configuration. Audit selected native binaries and source graph;
new dependency/version selection or unexpected build inclusion holds acceptance.

Future execution is limited to a newly created disposable iOS simulator owned by that run;
no existing/physical device or macOS host Keychain operations, signing/account enrollment or
passcode changes. Core package tests must target that iOS simulator, not default macOS `swift test`.
If the exact passcode-required class is unavailable in simulator, classify held and use explicitly
labelled injected doubles for state-machine tests. Never substitute a weaker class or count fake
success as platform acceptance. Source/compile/simulator/process-kill evidence is **not device or
backup proof**, power-loss proof, backend adoption or production permission. No such test runs here.

## 5. Scope boundary, assumptions and the next decision

A is synthetic primitives/host proof only. B separately integrates the actual TS queue/drafts/
library/reminder/session/UID/PKCE adapter, paging, SDK disposal and real camera provenance interface.
C separately specifies the isolated legacy exporter, freeze/copy/purge/relaunch/recovery UX.
C3 needs the separately authorized physical-device backup/restore protocol and owner inputs.
No network grant, legacy migration, user-data read, reset, store readiness, production/capture/
sign-in/photo opening or scientific accuracy follows from A or this scope review.

The next decision is approval or rejection of this **exact** native-file/import/API-effect and
support/generated-patch scope for a separately authorized synthetic A implementation. Passcode
and preserve-data recovery policy are already approved. If approved later, bind the go to the
reviewed commit/manifest; the document itself grants no implementation authority. Keep all current
acceptance boxes unchecked until their actual evidence/owner gate is met.

Assumptions: the 21-file split suffices; public APIs can enforce the host boundary; fixed-root
SQLite containment and actual platform modules/floor can meet v12; the fresh native graph matches
the reviewed selected products; all inherited startup/callbacks can be gated without extra edits.
Every assumption is a stop gate. No new dependency: prospective code is MIT; system SQLite core
is public domain and platform frameworks retain Apple terms. Actual versions, licences, upstream
maintenance dates, binary sizes and app delta are unmeasured until A and must be recorded there.
No licence change or new paid/closed service is requested.

References: [v12 mechanism](IOS_NATIVE_STORAGE_DESIGN.md), [source-only audit](IOS_STORAGE_FEASIBILITY.md),
[SwiftPM manifest/target rules](https://docs.swift.org/package-manager/PackageDescription/PackageDescription.html),
[XCTest](https://developer.apple.com/documentation/xctest),
[public bridge constructor](https://github.com/ionic-team/capacitor/blob/5e0f67871994fec94e413cd0993dc6cd495431f7/ios/Capacitor/Capacitor/CapacitorBridge.swift#L204),
[notification router flag](https://github.com/ionic-team/capacitor/blob/5e0f67871994fec94e413cd0993dc6cd495431f7/ios/Capacitor/Capacitor/NotificationRouter.swift#L3),
[exact Capacitor binary-product manifest](https://github.com/ionic-team/capacitor-swift-pm/blob/8.5.2/Package.swift),
[Apple passcode-bound class](https://developer.apple.com/documentation/security/ksecattraccessiblewhenpasscodesetthisdeviceonly).
