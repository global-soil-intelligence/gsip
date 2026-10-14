# iOS private storage: feasibility before migration

Status: v11 specification approved and merged in [#68](https://github.com/global-soil-intelligence/gsip/pull/68); iOS protection remains **blocked/unverified**. **No backend is selected.**
[APP-2C1](IOS_STORAGE_FEASIBILITY.md) records the source-only capability review and offline evidence checker.
This package contains no migration or runtime implementation. It selects no new dependency,
native code, account, signing material or service. It grants no deployment or capture authority.

The existing policy remains: exclude the private queue, draft photos, sample context and session
from cloud backups while preserving durable offline work and contributor rights. A directory
name or successful simulator build cannot establish that protection.

## Exact source findings, not device evidence

Reviewed baseline: main `2c6caa15cbc381eb1c0e3a0b47f40847ef2210c1`.

| Input                                                                     | Observation and limit                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `@capacitor/filesystem` 8.1.3                                             | `LibraryNoCloud` maps to the native not-synced-library path. Its web fallback uses IndexedDB. Selecting the plugin name alone supplies no protection proof.                                                                                                                                                       |
| ION filesystem 1.1.4, revision `56bd6f9e77cb4f2269c03f2d92a9fe58fe168a1c` | Attempts the exclusion flag with `try?` before root creation, without propagated failure or readback. Its writes are non-atomic; rename deletes an existing destination before moving the source. Those operations do not provide an atomic replacement or multi-store transaction contract.                      |
| Capacitor iOS/core 8.5.2                                                  | Creates a default persistent WebKit configuration and installs a cookie observer. Existing configuration exposes no TypeScript switch for a nonpersistent store. WebKit cookies can be mirrored into the native shared cookie store; this is a surface to audit, not evidence of actual GSIP auth-cookie leakage. |
| `@supabase/supabase-js` / `auth-js` 2.117.2                               | GSIP uses persisted bearer sessions, with default localStorage and its own last-account key. The SDK accepts an asynchronous storage adapter. Custom session storage does not relocate GSIP's IndexedDB or WebKit/native residuals.                                                                               |
| Current camera photo result                                               | The reviewed ION camera 2.0.0 path uses temporary files, not a claimed Documents destination. App cleanup is best effort; crash or deletion failure can leave a temporary copy. OS/picker originals are outside GSIP's deletion control.                                                                          |

The ION versions above came from an observed generated resolution and exact public source.
That generated resolution is **not a repository-native lock** and does not prove every CI run
selects the same native code. Any later implementation must bind actual resolution, source,
licences, maintenance and payload size to its own build receipts.

Primary references:

- [Apple backup guidance](https://developer.apple.com/documentation/foundation/optimizing-your-app-s-data-for-icloud-backup).
  Backup exclusion is guidance, not a universal guarantee; some saves can reset its flag.
  tmp/Caches are unsuitable for durable offline work because the system may purge them.
- [Exact ION file manager](https://github.com/ionic-team/ion-ios-filesystem/blob/56bd6f9e77cb4f2269c03f2d92a9fe58fe168a1c/IONFilesystemLib/IONFILEManager.swift#L114),
  [replacement helper](https://github.com/ionic-team/ion-ios-filesystem/blob/56bd6f9e77cb4f2269c03f2d92a9fe58fe168a1c/IONFilesystemLib/IONFILEManager.swift#L297)
  and [exclusion attempt](https://github.com/ionic-team/ion-ios-filesystem/blob/56bd6f9e77cb4f2269c03f2d92a9fe58fe168a1c/IONFilesystemLib/IONFILEManager.swift#L337).
- [Filesystem mapping](https://github.com/ionic-team/capacitor-filesystem/blob/v8.1.3/ios/Sources/FilesystemPlugin/IONFileStructures%2BConverters.swift)
  and [dependency range](https://github.com/ionic-team/capacitor-filesystem/blob/v8.1.3/Package.swift).
- [WebKit data-store scope](https://webkit.org/blog/14423/building-profiles-with-new-webkit-api/),
  [Capacitor configuration](https://github.com/ionic-team/capacitor/blob/8.5.2/ios/Capacitor/Capacitor/CAPBridgeViewController.swift#L118)
  and [native cookie observer](https://github.com/ionic-team/capacitor/blob/8.5.2/ios/Capacitor/Capacitor/Plugins/CapacitorCookieManager.swift#L3).
- [Exact camera temporary-file helper](https://github.com/ionic-team/ion-ios-camera/blob/00c3dfdd6267f80db299d9c5a0bad522156b6cbc/Sources/IONCameraLib/Interfaces/Extensions/URL%2BTransformations.swift#L49)
  and [Supabase custom storage](https://supabase.com/docs/reference/javascript/initializing).

## Complete persistence inventory

The initial application inventory is derived from `apps/capture-pwa/src/queue.ts`,
`supabase.ts`, the platform adapters and the exact native SDK sources. A later dependency or
storage change must refresh it; this list is not a claim that the operating system was inspected.

- IndexedDB `gsip-capture-v1`, version 4: `submissions` (including photo blobs and attached
  private library declarations), `draftPhotos`, `libraryDraft`, `libraryNamespace`,
  `queueState` and `syncReminder`.
- `queueState` retains queue generation. `syncReminder` retains owner/epoch/revision and
  disabled, cleanup-pending fences. There is no separate per-record phone tombstone store.
  Current `clearQueue` uses one combined transaction across all six stores: it clears four
  payload/namespace stores, advances generation and preserves fenced reminder state.
- App localStorage `gsip-last-auth-uid`; the SDK's session, compatible legacy user storage and
  any PKCE verifier slots/index if those flows are reached. Do not invent a persisted Supabase
  mutex: the reviewed SDK defaults to lockless refresh coordination. A future storage adapter
  must preserve the actual supported SDK contract and account binding.
- WebKit database pages, journals/WALs, localStorage, cookies and response/HTTP caches;
  native shared cookie storage and SDK preferences/version/configuration files. Classify which
  values are sensitive. Do not assert the presence of private cookies or sensitive cache bytes
  without evidence; do not infer their absence from bearer authentication or `no-cache`.
- Current camera/picker output and best-effort cleanup, temporary import/staging copies,
  proposed transaction journal/recovery files, and any file-generation/replacement remnants.
  Respect system-owned originals; do not delete arbitrary external files.
- Private notification intent belongs to IndexedDB; generic scheduled/delivered notification
  payloads belong to the OS and have their existing separate cancellation and privacy rules.

## Proof required before a backend can be selected

1. Establish bounded, app-owned, non-shared excluded containment **before any private byte is
   written**, including temporary/journal copies. Create the root safely, propagate exclusion
   errors, and verify readback. Verify effective coverage after each save, replacement, move,
   upgrade and restart. Reapplying a flag afterward alone leaves an unproved initial window.
2. Demonstrate a real crash-safe commit primitive and durable transaction contract, including
   single-writer ownership or a proven multi-context coordination mechanism. Preserve acknowledged
   writes, the current six-store combined transaction, stale-drain rejection, queue generation,
   original-account ownership and notification fencing. A fulfilled write/rename promise,
   JavaScript mutex, append-only file or checksum alone does not prove these properties.
3. Make unavailable, unknown, corrupt, quota-limited, exclusion-failed and interrupted states
   hold private use and sync. **No fallback to IndexedDB or localStorage** for an iOS private
   backend failure; never silently use the filesystem plugin's web implementation. Web and
   Android keep their current behavior and backup rules.
4. Account for legacy and future WebKit/native residuals at supported lifecycle boundaries.
   Deleting keys or a database establishes logical visibility, not physical erasure of pages,
   journals, cookies or caches. Do not guess or rewrite WebKit's internal database paths while
   live. A nonpersistent WebKit store alone discards the current durable queue and is unsuitable;
   native cookie mirroring also needs explicit treatment.
5. Use generic bounded errors and counts. No photo, precise point, session/token, incoming path,
   private namespace or queue metadata enters logs, PRs, fixtures or public artifacts. Tests use
   synthetic records only; an adapter has no service-role key and changes no hosted grants/RLS.

## Migration and recovery contract, still held

An implementation proposal must specify its exact backend API, limits, transaction and lifecycle
mechanism before code. Do not fill those gaps with a speculative TypeScript file-store format.

The proposal must provide verified copy before deletion, bounded binary round-trip/length/hash
checks and crash recovery at every migration step. Hold the current writer, SDK initialization,
sync and reminder callbacks until migration state and current ownership are known. Preserve
revision-conditional writes and account changes in either order; an error or lost reply cannot
transfer a namespace or turn pending erasure into success. No resurrection after discard,
withdrawal, deletion or sign-out is permitted through the new store, old store or stale callback.

Migration must be idempotent, fail closed on copy/commit/verify/purge failures and retain a
recoverable authoritative generation without keeping an unprotected plaintext backup. It must
not report completion while an old sensitive store remains unaccounted for. Rollback, downgrade
and restore must not silently re-import old data into an active account or move private data back
to WebKit. Restored or downgraded private state remains held until current ownership and server
rights fences are checked. Local state cannot prove that every historical backup was revoked:
older provider backups cannot be retracted by the app.

## Options for the owner and implementation reviewer

| Option                                                         | Benefit                                                                             | Required evidence / decision                                                                                                                                                                                       |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Keep iOS release held; complete only the feasibility contract  | Preserves the approved languages and avoids an unproved migration. Recommended now. | This proposal selects no backend. Android/PWA and library work retain their independent gates.                                                                                                                     |
| Audit a suitable upstream open plugin/lifecycle solution       | Could preserve TypeScript/Python authored application code.                         | Exact source/native resolution, licences, maintenance/size, exclusion readback, safe transactions and WebKit/native residual handling must all satisfy the proof gate. No candidate currently has that acceptance. |
| Separately specify a native bootstrap/storage/lifecycle bridge | Could expose the missing native guarantees.                                         | Justin's explicit **native-language exception** is required before custom native implementation, plus architecture review, audits and device evidence. No exception is inferred from approving this document.      |

These are alternatives for a later concrete mechanism review, not permission to add Swift,
Objective-C, a new SDK, signing keys, a paid service or an app-store account. Encryption or a
directory name cannot substitute for the approved no-cloud policy. If the policy cannot be met,
keep iOS capture/store readiness held and report the residual risk rather than relax it.

## Evidence sequence and acceptance

1. **APP-2C1, feasibility only:** bind source/native resolutions; retain a complete classified
   inventory and capability/failure table; document owner choices. Tests keep the storage and
   device gates explicit. Source inspection and synthetic adapters are not storage implementation.
2. **APP-2C2, migration held:** only after C1 review, a separately reviewed exact mechanism and
   any needed native-language exception. Add real backend conformance and fault tests: every
   write/replace/commit/purge boundary, kill/lost reply, low space, corrupt input, competing contexts,
   rights clear and account switch in both orders. Distinguish process-kill from power-loss scope.
3. **APP-2C3, physical-device backup/restore:** synthetic canaries only, with a private protocol
   bound to exact signed build, OS/device class, transport and store-generation inputs. Cover
   fresh install, restart/reboot, update/migration, writes and replacements before/during backup,
   interrupted cleanup and actual restore onto another device. Inspect only this app's synthetic
   container/canaries; do not expose a person's unrelated backup, credentials or files. Account,
   device and signing actions need their own owner inputs; do not enable production sign-in or
   capture to run an experiment. Computer backups and device transfer need separately stated
   scopes; do not infer them from an iCloud result.

The desired observed result is local restart durability plus absence of private queue, images,
sample context, session/last UID and fenced intent in the tested cloud backup/restore. Record
counts/outcomes and reviewed limitations privately; no universal exclusion claim follows from
one device. A verified fresh cloud restore starts a new anonymous account and loses unsynced
work. Until in-app e-mail linking exists, inaccessible old-account contributions are withdrawn
through the privacy contact. Existing Android direct-transfer rules remain unchanged.

**Evidence status:** source review only. No device or backup experiment has run for this proposal.
Simulator success, policy tests, current native artifacts and an upstream benchmark cannot close
the device gate. iOS backup protection remains blocked/unverified; APP-2B device notification
checks, store/legal review, production and SPEC §11 launch/photo-publication gates remain separate.
