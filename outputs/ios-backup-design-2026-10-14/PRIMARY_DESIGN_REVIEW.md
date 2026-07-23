# Independent iOS backup feasibility review — 2026-10-14

Conclusion: Keep iOS backup protection blocked/unverified. A feasibility-only v11 amendment is justified. Do not select an existing TypeScript-only LibraryNoCloud migration as an established solution. No native-language exception or implementation is authorized by this review.

## Evidence and scope

Private evidence receipt: EVIDENCE.json, SHA-256 ef8048b59591589267a2cee7798b655cdfe2ff902180075b8e7e6f4037325fe0. Five exact public source files are preserved adjacent to this review; eleven local source inputs are hash-bound. No source or Git was mutated. No credentials, contributor/device data, build, signing, native device, production query/change or deployment was used.

NPM source inventory pins @capacitor/filesystem 8.1.3 and Capacitor core/iOS 8.5.2. The locally generated Package.resolved observes ion-ios-filesystem 1.1.4 at 56bd6f9e77cb4f2269c03f2d92a9fe58fe168a1c and ion-ios-camera 2.0.0 at 00c3dfdd6267f80db299d9c5a0bad522156b6cbc. That generated file is not a repository-tracked native lock and does not prove every CI run resolves those versions. The plugin's Package.swift uses from:1.1.1, so a future implementation must bind actual resolved native source and receipts. This review did not independently refetch/reverify the npm package archive integrity.

## Primary references and exact facts

1. Apple Foundation backup guidance:
   https://developer.apple.com/documentation/foundation/optimizing-your-app-s-data-for-icloud-backup
   Machine-readable source saved as apple-backup.json:
   https://developer.apple.com/tutorials/data/documentation/foundation/optimizing-your-app-s-data-for-icloud-backup.json
   Excludes tmp and Library/Caches by default because those directories are purgeable; do not put durable offline work there. isExcludedFromBackup marks file/directory guidance. Certain writes can reset the flag; reapply after save. Apple explicitly does not guarantee absence from every backup/restore. A resource flag or native build is not physical-device proof. Earlier provider-held backups cannot be retracted by application migration.

2. Exact ION filesystem source:
   https://github.com/ionic-team/ion-ios-filesystem/blob/56bd6f9e77cb4f2269c03f2d92a9fe58fe168a1c/IONFilesystemLib/IONFILEManager.swift
   - lines 252–278: directory-mode URL joins then canonical symlink-resolved containment check.
   - lines 280–295: omitted directory uses raw path/URL resolution, so a new wrapper must always select the intended directory and use bounded fixed relative names; do not accept arbitrary caller paths.
   - lines 337–368: .notSyncedLibrary maps to Library/NoCloud, attempts isExcludedFromBackup=true via try? before caller creates the directory; no flag readback or propagated exclusion error.
   - lines 114–131: binary Data.write lacks atomic options; textual write explicitly atomically:false.
   - lines 170–180 and 297–307: rename calls a helper that deletes an existing destination before moveItem; not an atomic-replace commit primitive.
   - append lines 135–157 writes through FileHandle; no transaction, durability sync or CAS contract is exposed.
   First creation can therefore swallow a failed exclusion attempt. Later directory API calls can retry once the root exists, but their success still does not expose actual exclusion status. ReadFile/GetUri/Stat do not return backup flag evidence. A data write that resolves is not a proof of excluded and durable storage.

3. Filesystem plugin mapping and encoding:
   https://github.com/ionic-team/capacitor-filesystem/blob/v8.1.3/ios/Sources/FilesystemPlugin/IONFileStructures%2BConverters.swift
   https://github.com/ionic-team/capacitor-filesystem/blob/v8.1.3/ios/Sources/FilesystemPlugin/CAPPluginCall%2BAccelerators.swift
   https://github.com/ionic-team/capacitor-filesystem/blob/v8.1.3/ios/Sources/FilesystemPlugin/FilesystemOperationExecutor.swift
   https://github.com/ionic-team/capacitor-filesystem/blob/v8.1.3/Package.swift
   Local installed mapping confirms LIBRARY_NO_CLOUD→notSyncedLibrary, unspecified encoding→base64 byte buffer, string encodings→UTF8/UTF16/ASCII. Use explicit UTF8 for bounded JSON and no encoding plus canonical base64 for bytes; enforce decoder bounds and round-trip bytes. Web fallback in dist/esm/web.js uses IndexedDB, so native backup backend must refuse unsupported/web/unknown platforms rather than silently use it. Public API reference: https://capacitorjs.com/docs/apis/filesystem .

4. WebKit semantics:
   https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/API/Cocoa/WKWebsiteDataStore.h#L35-L54
   https://webkit.org/blog/14423/building-profiles-with-new-webkit-api/
   WKWebsiteDataStore includes cookies, memory/disk caches, IndexedDB and localStorage. Nonpersistent store avoids filesystem writes and does not retain across sessions. Alone it loses current durable offline queue and session, so cannot satisfy the app. Named persistent profiles are still persistent and do not imply no-backup semantics. Main WebKit source describes current API, not a pinned proof of every supported iOS implementation.

5. Locked Capacitor iOS 8.5.2 behavior:
   https://github.com/ionic-team/capacitor/blob/8.5.2/ios/Capacitor/Capacitor/CAPBridgeViewController.swift
   - exact public source lines 118–148 (creation at 120, observer at 121): creates default WKWebViewConfiguration, installs cookie observer, does not select nonpersistent websiteDataStore. Browser-normalized rendering has different line numbering; use these physical source lines for GitHub links.
   - prepareWebView sets HTTPCookieStorage.shared cookie policy and uses that config. CLI iOS declaration exposes no data-store-mode switch.
   https://github.com/ionic-team/capacitor/blob/8.5.2/ios/Capacitor/Capacitor/Plugins/CapacitorCookieManager.swift#L3-L14
   Observer mirrors all WebKit cookies to HTTPCookieStorage.shared. This is an additional surface to audit; no evidence says GSIP has actual sensitive auth cookies. Supabase currently stores bearer session in localStorage, separately from these cookies.
   https://github.com/ionic-team/capacitor/blob/8.5.2/ios/Capacitor/Capacitor/WebViewAssetHandler.swift
   Asset handler emits Cache-Control:no-cache. It is not proof that no sensitive response bytes persist in any cache.

6. Exact current camera photo-result path:
   https://github.com/ionic-team/ion-ios-camera/blob/00c3dfdd6267f80db299d9c5a0bad522156b6cbc/Sources/IONCameraLib/Interfaces/IONCAMRMediaResultGenerator.swift#L78-L85
   https://github.com/ionic-team/ion-ios-camera/blob/00c3dfdd6267f80db299d9c5a0bad522156b6cbc/Sources/IONCameraLib/Interfaces/Extensions/Data%2BTransformations.swift#L3-L8
   https://github.com/ionic-team/ion-ios-camera/blob/00c3dfdd6267f80db299d9c5a0bad522156b6cbc/Sources/IONCameraLib/Interfaces/Extensions/URL%2BTransformations.swift#L49-L55
   Photo-result image is written to NSTemporaryDirectory, system-excluded by documented location. Current GSIP camera options saveToGallery:false; GSIP deletes returned URI best-effort in finally. Crash or deletion failure can leave a tmp copy. Do not assert current photo flow writes private photos to Documents: a separate video permanent helper exists but is not current GSIP photo behavior. App-picker/OS-owned original files are distinct and outside GSIP's deletion control. Source inspection is not on-device backup proof.

## Why a TypeScript-only migration is presently unproven

Migrating six GSIP IndexedDB stores plus Supabase auth and last UID is necessary but not sufficient. Existing WebKit database pages/WALs, browser caches/cookies, native cookie storage, temporary plugin copies and restored older state must be inventoried. IndexedDB.deleteDatabase/localStorage.removeItem prove API visibility, not physical erasure or exclusion of WebKit files. No reviewed existing JS API here selects nonpersistent WebKit before page creation, conclusively removes old WebKit stores at native lifecycle boundaries, or checks/reapplies arbitrary resource exclusions with errors propagated. Never edit/rename WebKit's private internals using guessed paths while live.

No-cloud root creation must precede private bytes; native provider must report reliable flag-setting/readback failures and fail closed. Crash-safe transaction/durability behavior cannot be inferred from rename/write promise completion. Immutable generations/journal may be studied in TypeScript, but do not claim native power-loss durability without an actual proven primitive and fault tests. Migration must preserve queue generation fences, rights tombstones, current auth ownership and no resurrection.

## Bounded recommendation/options

A. Keep current iOS release held and specify/test backend interfaces with synthetic adapters only; no production storage backend is selected. Recommended now.
B. Seek an upstream open plugin release that exposes strict private durable storage/exclusion readback and lifecycle-safe residual cleanup. Audit exact code/license/maintenance/size and actual native resolution before selection. This may preserve TS/Python authored languages; an API name is not evidence. It still must address WebKit and native cookie/cache surfaces.
C. Ask separately for a narrow native-language exception, then independently design/audit bootstrap storage/WebKit lifecycle handling. A promising study is durable no-backup native storage plus nonpersistent WebKit, but cookie mirroring and migration cleanup must also be solved. This is not selected or approved, and even it needs device evidence.
D. Ephemeral WebKit alone or moving the queue into tmp/Caches fails durable offline behavior and is unsuitable.

## Acceptance tests for the later implementation

- Unit/conformance: six IndexedDB stores and all binary blobs, library attachment bytes, owner/session/last UID/reminder intent retained; web/Android behavior unchanged; unsupported native backend fails closed and never falls back into IndexedDB.
- Typed/bounded file path and JSON/base64 corpus: Unicode, empty/max bytes, exact hashes; reject unknown/traversal/raw/encoded/symlink escapes, corrupt/partial/truncated/oversized/unknown-version records without exposing contents to diagnostics.
- Fault injection at every write/commit/cleanup boundary: no half transaction, no loss of acknowledged queue writes, no revival after discard/rights withdrawal, concurrent stale-drain fence and auth change preserved. Define power-loss scope separately from process-kill scope.
- Migration old app→new app interrupted after every step: verified new bytes and ownership before deleting old logical stores; preflight blocked if backend cannot prove required capabilities; rollback cannot silently copy private records back to WebKit; repeated migration idempotent.
- Native integration/artifact: exact dependency+generated config receipts, fail closed on exclusion-set/readback error and every replacement, cold start clears/isolates legacy WebKit data before sensitive use; no guessed private WebKit path; camera temp/import/cache/cookies reviewed; no secrets/locations in diagnostics.
- Physical iOS devices across supported versions: fresh install, force quit, reboot, low space, app update, backup while queued and immediately after changes, cloud backup→different device restore, authenticated computer backup if in scope, old backup restore→new app migration, and unchanged Android policy. Use synthetic canary records only. Inspect actual backup/restore outcomes for queue/photos/instrument metadata/session/last UID/reminder intent and residual paths. Confirm unsynced work survives local restart yet cloud restore starts clean/new anonymous account; no automatic sign-in/capture opening for tests. Signed/device builds are owner-gated.
- Device notification evidence remains a separate APP-2B gate. Never infer iOS backup protection from passing simulator/native CI.
