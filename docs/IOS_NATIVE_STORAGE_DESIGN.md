# Proposed iOS native private-storage design

**Proposal only — v12, 2026-10-14. No backend is admitted. No native-language exception is granted.**
Justin approved merging the source-only APP-2C1 audit in [#69](https://github.com/global-soil-intelligence/gsip/pull/69),
now main `de9d1221b7c73e9be5c7e25ccaa24dcfa7903934`. That audit found no complete existing mechanism.
This document proposes a candidate for a separately authorized, synthetic native prototype;
it implements no store, migration, native code or device experiment. iOS protection remains
**blocked/unverified**. Design approval alone is not implementation permission.

I1–I15, L1–L7 and B1–B8, SPEC §11/§15.1–15.10 and the [complete inventory](IOS_PRIVATE_STORAGE.md)
remain binding. Web/Android behavior and Android backup rules remain unchanged. No production,
Pages, worker, capture/sign-in, photo-publication, account/signing or store permission changes.
I12 public/agent readers receive no session or privileged key. Tests and reports contain synthetic
canaries only, generic outcomes and counts; no real contributor data, coordinates, tokens or paths.

## 1. Candidate and authority boundary

Propose an app-owned MIT native coordinator, system SQLite and a typed TypeScript facade,
with a fresh nonpersistent Capacitor host. The coordinator runs **before ordinary JavaScript**,
auth SDK initialization, sync or reminder callbacks. Neither IndexedDB/localStorage nor a
filesystem plugin web implementation is a fallback for a failed iOS backend. No fallback or
new anonymous account follows an unknown, locked, corrupt, restored or inconsistent state.

A possible Swift/native-test exception would cover only the outer startup coordinator/owned host,
excluded store/Keychain coordinator, bounded bridge/host enforcement and their direct fault tests.
Generated-project wiring stays pinned/tested Python; application logic stays TypeScript.
Before code, Justin must explicitly approve that exception and its exact proposed file/patch scope.
No global language rule changes; Objective-C, a core fork or additional native capability would
need another architecture/owner review. If supported public host seams cannot enforce this
boundary, stop rather than fork Capacitor or relax a privacy/dependency/permission check.

This selects **no new third-party dependency**, SaaS, push service or package/lockfile change.
SQLite's core is public domain; Apple's platform distribution is a system component under its
platform terms, not an MIT iOS binary. The local coordinator would be MIT. Actual runtime SQLite
version/source ID/compile options/VFS, native resolution, applicable licences, maintenance signal,
linked payload and app-size delta are **unmeasured** admission inputs. No third-party encryption
plugin or replacement database engine is selected. iOS Data Protection is additional protection,
not cloud exclusion; encryption cannot substitute for the approved no-cloud policy.

## 2. Excluded root and database admission

Create an empty, dedicated, non-shared app-owned Library subroot using a native fixed identifier,
not a caller path. Establish containment, reject symlink/alias/redirection/replacement, set the
backup-exclusion resource flag with propagated errors and require explicit true exclusion readback
**before SQLite open or recovery** can create or change private bytes. Set and verify the chosen
complete file-protection class; unavailable protected data holds admission. tmp/Caches are not the
durable store. A root handle/path-identity strategy and descendant coverage need prototype proof.

Keep the root stable. Check containment, exclusion and protection before/after transactions,
replacement, schema upgrade and restart; a failed post-check withholds acknowledgment and future
use. Reapplying a flag after writing does not close an earlier window. Apple describes exclusion
as guidance: these checks alone do not prove every backup transport. Effective descendant/journal
inheritance and replacement behavior remain physical-device gates.

Use one connection and a **single native writer** on a serial executor. Fixed prepared operations
only: **no caller SQL**, PRAGMA, ATTACH, extension loading, VACUUM or arbitrary export, and
**no caller path**. Required initial settings are `journal_mode=DELETE`, `synchronous=EXTRA`
(numeric 3), `foreign_keys=ON` and `temp_store=MEMORY`, with bounded busy time and limits.
Read actual values back; unknown PRAGMAs can be silently ignored. Refuse unsupported settings.
EXTRA adds the DELETE journal-unlink directory sync; FULL alone is insufficient for the proposed
rollback-mode power-loss contract. Requesting/readback of `fullfsync` is best effort, not proof
of the actual iOS SQLite/VFS flush path. Record process-kill and power-loss evidence separately.

`temp_store=MEMORY` does not eliminate rollback/statement journals or every scratch file.
Prove the fixed operation set's journal, statement, temp, upgrade and recovery placement inside
the excluded boundary; do not guess a global temp-directory setting. Never delete a hot journal:
SQLite must recover its matching journal only after root admission. No shared connection, live
file replacement or guessed WebKit database manipulation. Low space, busy timeout, corruption,
failed commit/rollback or uncertain flush returns a bounded held outcome, never a successful save.

## 3. Logical data and atomic operations

Use logical tables in the same excluded database for every current store, photo/instrument
payload, session/UID, private control, staging and idempotency receipt. Preserve missing/null,
number, timestamp, Blob/Uint8Array and schema semantics exactly; no lossy JSON conversion.

| Existing store     | Proposed transaction responsibility                                                              |
| ------------------ | ------------------------------------------------------------------------------------------------ |
| `submissions`      | Original owner, queue record/revision, image bytes, declaration and retry/held/dead-letter state |
| `draftPhotos`      | Draft photo bytes and original draft binding                                                     |
| `libraryDraft`     | Exact private context and bounded declaration bytes                                              |
| `libraryNamespace` | Existing owner/node binding; no account reassignment by import                                   |
| `queueState`       | Monotonically advanced queue generation within admitted state                                    |
| `syncReminder`     | Owner/epoch/revision, opt-in, cleanup-pending and cycle/consumption fences                       |

The **six-store clear** clears the same **four payload/namespace stores**, advances generation,
and retains disabled/advanced cleanup-pending reminder fences in one transaction. It also fences
and removes incomplete staging for the old generation. This is not a new per-record tombstone
policy. OS cancellation remains separate: database commit does not establish pending/delivered
notification absence; cleanup-pending survives until verified cancellation. An uncertain server
rights response holds data under current behavior, not an invented blanket deletion policy.

Map the complete existing exported API before changing callers:

- Queue: `enqueue`, `queued`, `removeQueued`, `clearQueue`, `queueRevision`, `putIfCurrent`,
  `discardHeld`, `discardLibraryConflicts`, `releaseHeld`, `reconfirmTerms`, `retryDeadLettered`.
- Drafts/library: `saveDraftPhoto`, `draftPhotos`, `clearDraftPhotos`, `savedLibraryDraft`,
  `saveLibraryDraft`, `libraryNodeForOwner`, `bindLibraryOwner`, `rememberLibraryOwner`,
  `clearLibraryDraft`, `libraryNamespaceOwner`.
- Reminders: `queueReminderContext` and the `indexedDbReminderStore` contract; preserve the
  `indexedDbQueue` generation/revision/isCurrent/list/put/remove semantics in the platform facade.

Each native operation checks original owner, auth epoch, launch lease, expected queue generation
and record revision, and a bounded operation ID. Commit the operation receipt with the mutation.
A lost reply can be retried with the same identity; changed payload/owner reuse is refused.
Receipt pruning must not permit replay across generation/lease fences. Bound all IDs, nonces,
revisions, generations and epochs in the A-entry contract; reject invalid values and hold
on counter exhaustion rather than wrap or reuse. No transaction across
network calls, JavaScript callbacks or user interaction. No global JS mutex is accepted as the
native transaction primitive. Competing contexts and callbacks must be rejected or serialized.

Provisional prototype limits: at most 128 KiB binary chunks, 512 KiB total IPC frames and 256 MiB
managed private bytes including staging, receipts and journals; these are planning bounds, not
measured capacity. Reserve space before accepting work, with **no eviction or truncation** on quota.
Keep existing photo and 2,000,000-byte declaration/envelope bounds; do not invent a smaller metadata
cap that discards valid library declarations. Incomplete staging is bound to operation/lease/owner/
generation, excluded from usable records and **not acknowledged**. Verify exact length/hash and
complete bytes before the final atomic save. Bound staging cleanup after interruption.

The current drain **currently materializes** `store.list()` and photo arrays. APP-2C2B must specify
and test a bounded paged/native record reader and streamed payload access before claiming bounded
bridge memory. Preserve ordering, retry/idempotency and revision fences, with the existing list
fallback for web/Android. Do not hold an SQLite read transaction across uploads. End-to-end memory
and device performance are unmeasured; these proposed limits confer no runtime capacity claim.

## 4. Independent restore anchor and acknowledgment

Co-restored local flags, hashes and revision counters cannot distinguish every older backup
from a valid old state. Propose a separate small Keychain anchor with
`kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly`, `synchronizable=false`, no sharing or additional access group
(use only the app’s ordinary default access group), and no photo, session or token payload. This is a **passcode-required** product choice, pending
Justin. Other ThisDeviceOnly classes can restore to the original device; they are not substitutes.
Passcode removal/reset invalidates this class; Keychain items may survive reinstall. Neither an
absent database nor a missing/inaccessible anchor is proof of a fresh install.

Use public Keychain APIs off the UI thread, read back actual accessibility/synchronizable
attributes and bounded data, and update an existing item without a delete/add gap. Missing
attributes, denial, locked state or an unknown error is not an empty item. The anchor is
**not a hardware monotonic counter** and **not atomic with SQLite**; no cross-store CAS,
crash-durability or universal rollback proof is claimed. Prototype these limitations explicitly.

Candidate acknowledgment protocol, serialized with all private writes:

1. Require an admitted clean anchor and matching database installation nonce/revision `r`.
2. Write/read back a **pending anchor** with base `r`, next `r+1`, fresh commit nonce and bounded
   operation identity/kind/digest. Do not acknowledge yet.
3. Commit the fixed SQLite mutation, next revision/nonce and operation receipt together.
4. Write/read back the **clean anchor** at the matching next revision. Recheck containment,
   exclusion/protection and active lease. Only then acknowledge success to the app.

| Restart observation                                                                                          | Required candidate behavior                                                                        |
| ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| Clean anchor plus exactly matching DB/receipt schema                                                         | Admit after protected-data/root checks; ordinary offline restart remains possible                  |
| Pending anchor plus matching committed next DB and exact operation receipt                                   | Finalize only after all checks/readback; retry lost reply without applying twice                   |
| Pending-plus-old database                                                                                    | QUARANTINE; preserve bytes and anchor, never roll anchor back to fit DB                            |
| Clean/DB nonce or revision mismatch, missing DB, anchor absent/inaccessible, unknown receipt or newer schema | QUARANTINE; no active use, import, sync, SDK boot or automatic account creation                    |
| Both absent                                                                                                  | Classify lifecycle with an approved fresh-install/reset protocol; absence alone cannot prove fresh |

A crash after pending but before SQLite commit may leave previously acknowledged bytes intact
but unavailable. Recovery for that state is unresolved: **preserve quarantined bytes**, do not
claim availability or erase permission. There is **no automatic destructive reset**. Loss of
passcode/anchor, reinstall and restore require a reviewed classification/reset UX before adoption.
A documented user-confirmed fresh start, if later approved, loses unsynced work and begins a new
anonymous account only under then-current capture/auth gates; inaccessible old contributions
use the privacy contact until e-mail linking exists. Older provider backups cannot be retracted.

A clean same-install admission permits ordinary offline restart without a mandatory server call
at every launch. Local anchor admission never supplies hosted authority: sync and any restored
ownership require current server rights, grants, account and activation checks before hosted use.
If the separate-anchor protocol cannot safely admit the required lifecycle, retain the iOS hold;
co-local flags or a silent new account are not an alternative.

## 5. Host, authentication and residual containment

Only after native admission construct an app-owned `UIViewController` conforming to public
`CAPBridgeDelegate`, using the public `CapacitorBridge` initializer, an audited
`WebViewAssetHandler` subclass and a fresh nonpersistent `WKWebsiteDataStore`. This is a larger
host-compatibility scope than a view-controller override. The stock `CAPBridgeViewController`
has final `loadView`, constructs its own handler, and serves `/_capacitor_file_` before a custom
router: a subclass/router alone cannot enforce an owned-file capability boundary.

Construct the configuration without invoking the default persistent configuration/cookie
observer path; retain required audited scheme, lifecycle and plugin behavior. Intercept the
special-file route in the owned asset handler: deny arbitrary filesystem URLs/paths and map only
bounded native-issued owned-temp capabilities, including camera results, after proving their
provenance and expiry. Nonpersistent WebKit is an ephemeral UI host, not the durable store.
Bind the exact Capacitor/native version and built entitlements; no new minimum iOS version is
assumed here. No public seam or compatibility claim is admitted without prototype proof.

Capacitor 8.5.2 registers core Cookies/HTTP even when automatic registration is off. `enabled=false`
alone does not block direct native methods or cookie prompts, which can reach the default WebKit
store and native cookie jar. Same-name rejecting plugin facades alone are insufficient: a class-name
plugin ID can trigger dynamic loading of a linked plugin. This must be blocked before navigation.

In synchronous owned-host construction, replace the public content controller's `bridge` message
handler with a bounded **main-frame** exact plugin-ID/method **allowlist**, forwarding only admitted
calls to the retained public bridge delegation handler. Deny class-name aliases, unknown/Cordova
messages, malformed/oversized bodies and unapproved origins/frames. Also replace and audit the
prompt/UI delegate to deny core cookie prompt routes. Set/read native cookie policy `.never`
inside the owned host before first navigation; do not invoke stock preparation, which sets
`.always`. Omit the observer and prove no alternate
ingress, callback or later re-registration bypasses the gate. This is an unproved public seam
candidate, not a working sandbox or authorization to modify/fork upstream core.

Allow only audited app operations: bounded native private-store facade, required camera/location,
owned temporary-photo cleanup and generic local notifications. Deny raw filesystem write/copy/path,
HTTP/cookie methods, WebView persisted path changes and arbitrary navigation; audit every exposed
method, including linked core classes. Preserve the existing camera cleanup through a bounded
owned-temp handle, not arbitrary caller URLs. Current `Camera.takePhoto` returns a temporary URI
and provides no native output-handle broker. Prototype an exact supported callback/provenance seam
or stop for another scope review; do not assume a filename or caller URI proves ownership. The
current native camera writes a temporary JPEG and termination cleanup is best effort. Prove its
system-excluded temporary class or a separately scoped native redirection before admission;
nonpersistent WebKit alone does not cover camera files. Prove packaged assets/offline load and existing
camera/picker/location/reminder flows work. No external script/origin injection, private console
logging or unaudited response-cache path. Unknown methods hold; no relaxed SDK/permission checks.

Use the SDK's asynchronous custom storage adapter only after native admission, plus native storage
for `gsip-last-auth-uid`, actual compatible legacy user storage and PKCE slots. A UID hint is not
authorization. **Unknown is not empty**: read errors must not trigger replacement sessions or a
new anonymous identity. Fence late auth callbacks with an auth epoch/launch lease before account
switch, sign-out or rights clear, stop/dispose the old client and serialize SDK key writes.
Refresh failure is not evidence of an empty store. Exact SDK callback/lock behavior needs tests.

Inventory WebKit/cookie/cache/preferences, SDK settings, camera/picker temporary files and OS
notification state even where no sensitive value is observed. Native cookie cleanup must be
GSIP-scoped after verifying actual entitlement/sharing ownership; never blanket-delete an unknown
shared jar. System/picker originals remain outside GSIP control. Prove exact app-owned temporary
creation/cleanup and exclude/hold every private intermediate; do not delete arbitrary files.

## 6. Legacy migration — held after primitive and host proof

Use an **isolated legacy exporter** with **no ordinary app**, React, Capacitor plugins, auth SDK,
network, refresh or sync/reminder writers. A purpose-built bundled TypeScript exporter in a plain
WKWebView must reach the exact old `capacitor://localhost` origin and its app-owned persistent store.
First prove that supported configuration loads that origin and can freeze every other writer;
if not, stop for another design review. Open the known IndexedDB without creation or upgrade;
distinguish absent, unknown-schema and read-error states, never an empty-account fallback. Prove
snapshot consistency across bounded batches after writers are frozen. Never boot the old
application to discover its state.

Export all six stores, original owner/generation/reminder fences, session/UID and actual supported
SDK keys. Keep IndexedDB work local: **no bridge await inside** a live IndexedDB transaction.
A frozen writer plus bounded cursor/chunk snapshot protocol must verify starting/ending keys,
generation, counts and byte digests without an unbounded `getAll()` payload. Drift aborts before
purge. Treat precise/photo/session data as private; only generic synthetic results leave the device.

Stage excluded native copies, validate binary/optional/schema/account semantics and commit the
verified target under the anchor protocol. **Verified copy before deletion** is mandatory. The
legacy generation remains authoritative until complete target verification; ordinary native use
stays quarantined during dual-state/purge. A partial copy/commit, quota error or lost reply cannot
permit use or deletion of the old authoritative state. Resume with bound migration identity, not
an unqualified re-import; incompatible/downgraded code must hold instead of invoking a web fallback.

Use supported WebKit website-data removal and app-owned native cookie/cache cleanup only.
`WKWebsiteDataRecord.displayName` is not a reliable exact-origin selector; verify a wholly app-owned
store boundary or keep purge held. Wait for callbacks, re-enumerate expected data types, destroy the
exporter, then require an ordinary user-driven full relaunch with readback/revalidation before
the ordinary host. No programmatic process exit. WebKit completion supplies no detailed error
result and is **not physical erasure** or backup proof. Residual/journal coverage needs separate
APP-2C3 evidence; do not rewrite guessed live WebKit internals or claim a purge callback proves no
old bytes. Unknown old/restore/purge state stays quarantined; no silent fall back or reset.

## 7. Proposed work sequence and admission evidence

These are future packages; every implementation criterion remains unchecked in BUILD_ORDER.

| Package        | Scope and entry gate                                                                                                                                | Required exit evidence                                                                                                                                                                                           |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| APP-2C2A, held | Synthetic native primitives/host prototype only after this architecture, exact native-language exception and passcode/recovery choices are approved | Exclusion-before-open, actual SQLite settings/temp/journal placement, pending/commit/ack fault matrix, unknown lifecycle quarantine, no bridge/prompt/native-route bypass; exact native/dependency/build binding |
| APP-2C2B, held | TypeScript facade/account/reminder integration after A independently reviewed and green                                                             | All mapped operations/bytes, bounded paging/staging, owner/generation/revision/auth/lease races, SDK storage errors and lost replies, notification cleanup separation; web/Android regressions                   |
| APP-2C2C, held | Legacy migration/recovery after B and a separately approved exact exporter/purge/reset protocol                                                     | Frozen bounded exact copy, kill/quota/corrupt/retry at every transition, no premature purge/use, unknown restore/downgrade quarantine and residual limits                                                        |
| APP-2C3, held  | Separately authorized physical-device protocol, owner device/account/signing inputs                                                                 | Synthetic canaries only; exact build/OS/transport/update/interruption/backup/restore evidence; no private cloud bytes in the tested scope, honest residual coverage                                              |

Process-kill tests cannot certify power loss; source/policy tests, simulator builds, readbacks and
artifact success cannot certify backup exclusion. **No device experiment** has run for this design.
No backend adoption until the full v11 mechanism gate is satisfied; A's prototype evidence alone
cannot close C2C/C3, store/legal, notification-device, calibration/publication or production gates.
No real-data read, generated native project change, dependency adoption or native API call occurs
in this specification package. Current runtime remains unchanged.

## 8. Owner decisions and assumptions

All choices below are **pending**; preparing this proposal grants none of them.

| Decision                          | Recommendation                                                                                                              | Alternative / consequence                                                                             |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Design direction                  | Review this candidate for a bounded synthetic prototype, with exact scope/failure gates                                     | Keep iOS held and research another supported mechanism                                                |
| Native-language exception         | Consider only the narrowly listed Swift coordinator/host/bridge and direct native tests, with exact patch scope before code | Keep TypeScript/Python-only and iOS held                                                              |
| Independent anchor product policy | Require a device passcode; lock/anchor loss holds use and unsynced work                                                     | Keep iOS held; another anchor/policy needs a new amendment                                            |
| Ambiguous recovery                | Preserve quarantined bytes; no automatic destructive reset; separately review recovery/fresh-start UX                       | An explicit later user-confirmed reset loses unsynced work/account access; no reset is authorized now |

Assumptions: single app-owned, non-shared root/legacy store; current six-store and SDK source
semantics; platform SQLite/Keychain availability; public Capacitor seams can be safely bounded;
current supported OS/version matrix can meet the contract without silent target changes. Every
assumption is an admission test, not a fact proven by prose. The pending passcode requirement and
quarantine availability cost are product trade-offs, not already approved no-cloud policy details.
No new licence/service, account/signing input or scientific accuracy is claimed.

## 9. Primary references and source limits

The [APP-2C1 exact-source catalog](IOS_STORAGE_FEASIBILITY.md) remains the observed source baseline;
its generated native resolution is not a universal native lock. Later implementation must refresh
all actual versions, source hashes, transitive/native licences, dates and payload measurements.
Public platform documentation describes APIs; it is not observed device behavior.

- [Apple backup guidance](https://developer.apple.com/documentation/foundation/optimizing-your-app-s-data-for-icloud-backup), [protected data availability](https://developer.apple.com/documentation/uikit/uiapplication/isprotecteddataavailable), [complete file protection](https://developer.apple.com/documentation/foundation/fileprotectiontype/complete).
- [SQLite PRAGMAs](https://www.sqlite.org/pragma.html), [temporary files](https://www.sqlite.org/tempfiles.html), [atomic commit and failure assumptions](https://www.sqlite.org/atomiccommit.html), [runtime identity](https://www.sqlite.org/c3ref/libversion.html), [public-domain core](https://www.sqlite.org/copyright.html).
- [Apple Keychain data protection](https://support.apple.com/guide/security/keychain-data-protection-secb0694df1a/web), [SecItemCopyMatching](<https://developer.apple.com/documentation/security/secitemcopymatching(_:_:)>), [SecItemUpdate](<https://developer.apple.com/documentation/security/secitemupdate(_:_:)>), [Keychain synchronizable attribute](https://developer.apple.com/documentation/security/ksecattrsynchronizable).
- Capacitor 8.5.2 [host lifecycle/configuration](https://github.com/ionic-team/capacitor/blob/8.5.2/ios/Capacitor/Capacitor/CAPBridgeViewController.swift), [plugin registration and dynamic call dispatch](https://github.com/ionic-team/capacitor/blob/8.5.2/ios/Capacitor/Capacitor/CapacitorBridge.swift), [cookie persistence](https://github.com/ionic-team/capacitor/blob/8.5.2/ios/Capacitor/Capacitor/Plugins/CapacitorCookieManager.swift), [message/prompt delegates](https://github.com/ionic-team/capacitor/blob/8.5.2/ios/Capacitor/Capacitor/WebViewDelegationHandler.swift).
- [Capacitor 8.5.2 special-file asset handler](https://github.com/ionic-team/capacitor/blob/8.5.2/ios/Capacitor/Capacitor/WebViewAssetHandler.swift) and [public bridge/delegate interfaces](https://github.com/ionic-team/capacitor/blob/8.5.2/ios/Capacitor/Capacitor/CAPBridgeDelegate.swift).
- [Nonpersistent WebKit](<https://developer.apple.com/documentation/webkit/wkwebsitedatastore/nonpersistent()>) and [supported website-data removal](<https://developer.apple.com/documentation/webkit/wkwebsitedatastore/removedata(oftypes:modifiedsince:completionhandler:)>).
- [WebKit profiles and store scope](https://webkit.org/blog/14423/building-profiles-with-new-webkit-api/), [native cookie storage](https://developer.apple.com/documentation/foundation/httpcookiestorage), [Supabase async storage](https://supabase.com/docs/reference/javascript/initializing).
