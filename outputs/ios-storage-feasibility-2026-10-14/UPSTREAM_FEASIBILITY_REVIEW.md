# APP-2C1 independent upstream feasibility review — 2026-10-14

Outcome: BLOCKED; no backend selected. Three credible open components were inspected from exact public npm archives with SHA-512 SRI verification and crucial source files matched to immutable public commits. None closes the full v11 storage/lifecycle contract, individually or as an evidenced combination. This is source review only, with no install, app/native runtime, build, signing, device/backup experiment, real app-data, Git/GitHub mutation, production read/change or capture activation.

## Invariants and comparison

Preserve private-data cloud exclusion, durable acknowledged offline work, the six-store combined rights/generation/reminder fences, original-account ownership and public-agent isolation. No fallback into IndexedDB/localStorage on native storage failure. A storage method name, encryption, write promise, simulator or source finding does not prove native exclusion/durability/erasure. Any custom native code needs Justin's separate language exception.

| Exact candidate | Possible component role | Licence and maintenance signal | Measured package size only | Full v11 outcome |
| --- | --- | --- | --- | --- |
| @capacitor-community/sqlite 8.1.1, npm gitHead 3f3f71606c8f292a3d6d841937bcfc5b5c45aeb5 | Native SQL transactions could hold all six logical stores and session/ownership state in a reviewed schema | MIT included LICENSE; npm published 2026-08-06; Capacitor>=8 peer and native sources supplied. Publication/compatibility declaration are maintenance signals, not quality proof | SRI-verified tgz 271,508 bytes; registry unpacked 2,034,996 bytes | BLOCKED: incomplete exclusion/readback/restart contract, residual WebKit/native state, logs and native payload audit |
| @aparajita/capacitor-secure-storage 8.0.1, release tag peeled commit 3b0d3144f344ec67ffa51b96a3ca986ad3c608f7 | A narrowly specified session/key component, not a whole photo/queue database | MIT included LICENSE; npm published 2026-09-23; Capacitor8 compatibility and configurable Keychain access. Publication is not tested compatibility | SRI-verified tgz 21,145 bytes; registry unpacked 96,368 bytes | BLOCKED: defaults permit backed-up keychain semantics; selected-access attribute verification, missing-vs-error handling, replacement/combined transaction and residual cleanup unproved |
| @capgo/capacitor-inappbrowser 8.24.0, npm gitHead 3ad4979e77317fcd106ad4e06e945dca46deb4a2 | Shows a maintained JS-exposed nonpersistent WKWebView/data-removal implementation for plugin-owned browser windows | MPL-2.0 included LICENSE; npm published 2026-10-13; Capacitor>=8 peer; public sources | SRI-verified tgz 352,784 bytes; registry unpacked 1,973,127 bytes | REJECT for GSIP host lifecycle role: deliberately excludes Capacitor host store; not durable storage and no host-bootstrap replacement |

These are package archive figures, not app download/installed/native payload sizes. No candidate is installed. Transitive native resolutions, binary payload sizes, final app licences/notices, Android dependency/permission/closed-SDK checks, toolchain compatibility and device behavior remain unmeasured. Source inspection did not verify npm signatures or provenance attestations; it verified declared SRI and selected exact source bytes.

## 1. Community SQLite 8.1.1

Immutable source: https://github.com/capacitor-community/sqlite/tree/3f3f71606c8f292a3d6d841937bcfc5b5c45aeb5

- ios/Plugin/Utils/UtilsFile.swift lines40–72 creates a configured root then sets exclusion only when that directory did not exist. Existing-root paths skip setting/checking. Internal getExcludeFromiCloudBackup lines629–634 exists but has no callsite in the inspected package and no reviewed JS readback API. Current code therefore does not establish exclusion health before every use, save/replacement or restart.
- ios/Plugin/Utils/UtilsSQLCipher.swift lines380–435 invokes actual BEGIN/COMMIT/ROLLBACK TRANSACTION, and src/definitions.ts2324–2385 exposes a transaction wrapper. This is a genuine stronger primitive than loose file replacement, but no native run, failure ordering, power-loss/sync configuration or GSIP all-store transaction test ran. Do not call it proven durable queue behavior.
- Database.swift83 unconditionally prints the database path. Raw SQLite error text is incorporated into errors. Integration must establish generic I7-safe diagnostics; Capacitor loggingBehavior:none does not prove direct Swift print suppression.
- Configured non-default path creation also attempts migration of existing Documents databases. This behavior must not silently migrate unexpected app state. WebKit databases/localStorage/cookies, native cookie storage, camera/picker output and old restores remain outside this database API.
- Package.swift declares SQLCipher.swift from4.14.0 and ZIPFoundation from0.9.0, plus Capacitor from8.0.0; no actual native graph was resolved here. SQLCipher.swift4.14.0 commit180be9a4dd130d838765a156b709e02f3bc3e7cd declares a binary XCFramework release URL and checksum. Its source licence begins with the community open-source BSD-style terms. The actual binary/source correspondence, complete third-party notices and payload size were not verified. An MIT plugin wrapper does not complete that audit. No paid edition was requested or selected.

Relevant official SQLite background: https://sqlite.org/atomiccommit.html and https://sqlite.org/pragma.html#pragma_synchronous . Engine atomicity depends on journal/sync/VFS/filesystem behavior; it does not establish this plugin's runtime configuration or exclusion of every journal/temp/upgrade backup. SQLite is worth a later narrow upstream-capability review, but is not ready for APP-2C2 selection.

## 2. Aparajita Secure Storage 8.0.1

Immutable source: https://github.com/aparajita/capacitor-secure-storage/tree/3b0d3144f344ec67ffa51b96a3ca986ad3c608f7

SRI-bound dist/esm/base.js defaults sync=false and KeychainAccess.whenUnlocked. Neither encryption nor synchronization disabled means absence from a device/cloud backup. Plugin.swift125–145 accepts ThisDeviceOnly and whenPasscodeSetThisDeviceOnly classes, but exposes no readback of the persisted item's actual class. Plugin.swift172–176 propagates write failure; getData180–182 returns KeychainSwift.get without distinguishing underlying OS error from no value, so a new session must not be created on an assumed empty response.

Package.swift declares KeychainSwift from21.0.0; this is a range, not an observed resolved native lock. The inspected minimum21.0.0 commit265806607b45687a3d646e4c9837c31c90f202e8 is MIT, and Sources/KeychainSwift.swift85–112 deletes an old key before SecItemAdd. The library lock is thread coordination, not an atomic item replacement or six-store transaction. Do not claim a future resolver chooses that exact version. Package npm dependencies also include Capacitor app and keyboard plugins and native platforms, so the current Android/native allowlist and added payload must be reviewed before adoption.

Official distinction: https://developer.apple.com/documentation/security/restricting-keychain-item-accessibility and https://support.apple.com/guide/security/secb0694df1a/web . Generic ThisDeviceOnly classes may restore to the original device and do not mean no backup. The passcode-set-only class is documented as not backed up/synced, but requires a passcode and loses access when it is removed/reset. Those availability/loss semantics require a concrete product design, not an inferred approval. A session/key component still cannot provide queued photo durability, combined rights clearing or WebKit/native residual cleanup. No hard maximum Keychain payload size is claimed; large-photo/queue suitability was not established.

The web implementation uses localStorage; any native-path failure must hold rather than reach it. No user/secret was read and no Keychain API ran.

## 3. Capgo InAppBrowser 8.24.0

Immutable source: https://github.com/Cap-go/capacitor-inappbrowser/tree/3ad4979e77317fcd106ad4e06e945dca46deb4a2

InAppBrowserPlugin.swift293–308 returns .nonPersistent() when persistWebViewData=false for its managed windows. Lines311–337 explicitly filter out WKWebsiteDataStore.default(), the Capacitor host store, from clearAllBrowsingData; lines1130–1147 remove data from the collected managed stores. This is credible evidence of an exposed lifecycle component, but its stated scope intentionally does not solve GSIP's host store or native cookie jar. Moving the main app into a browser window would be a new architecture with bridge, auth, offline, permissions and residual implications; it is not an accepted workaround.

No storage transaction, exclusion-before-write, durable queue or GSIP account/rights fence follows from the nonpersistent browser. MPL-2.0 applies to this candidate component; no GSIP licence is changed, no dependency selected and no legal compatibility/notice approval is inferred.

## Cross-cutting residual and restore limits

Reuse the exact baseline evidence receipt ef8048b59591589267a2cee7798b655cdfe2ff902180075b8e7e6f4037325fe0 and public supplement568dcad2dc80cfbb00490635af23c406794a67a1a03bfdb4afd17d6793723994. Current default Capacitor WebKit remains persistent and mirrors cookies to the shared jar; current camera photo output is tmp with best-effort app deletion, not a claimed Documents photo flow. The existing Filesystem no-cloud API has swallowed flag errors and non-atomic writes/replacement. All candidates leave some combination of old WebKit database pages/WALs/localStorage, caches/cookies, preferences/plugin output, migration generations and prior-backup restore behavior unaccounted for. No actual sensitive cookies/cache contents were observed; these are surfaces to classify. Logical API deletion does not prove physical erasure. None of these components implements GSIP owner/server-rights checks or anti-resurrection fences by itself.

## Recommendation and next gate

Keep APP-2C2 and iOS capture/store readiness held. Preserve TypeScript/Python authored languages and record the negative capability matrix in APP-2C1. No new owner question is necessary merely to accept this source-only blocked result, and no native-language exception should be requested without a concrete mechanism worth review.

A next useful preparation is an exact upstream capability proposal for one app-host lifecycle + excluded durable transactional backend: create/exclude/read back before bytes; validate after restart/replacement; fail closed; safe journal/temp/upgrade coverage; generic diagnostics; legacy WebKit/native-cookie cleanup at a supported lifecycle boundary; current ownership/rights/restored-generation hold. It must bind native source and full licence/payload evidence before APP-2C2. If solving those capabilities needs custom native code, show that exact bounded proposal to Justin and request the language exception separately. Source design approval alone grants neither exception nor implementation/deployment/device authority.
