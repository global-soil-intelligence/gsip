# APP-2B: private local sync reminders

This package implements approved SPEC §15.3: optional sync reminders inside the native app.
Nearby suggestions, push notifications, location calculations, signing and store submission
remain outside this package. All deployable artifacts retain closed capture and library flags.
A source merge or an unsigned artifact does not authorize production changes or store readiness.

## Behavior and privacy

Only **Enable sync reminders** requests OS notification permission. A denied or unknown response
leaves capture usable and does not create a background prompt loop. The website returns
unsupported before importing the plugin and never uses the browser Notification API.

A known signed-in account, known-open existing capture gate and a queue belonging entirely to
that account are required. Foreign-owner, held, dead-letter, terms-expired, library-conflict or
paused-library work holds reminders until resolved. Unknown access or capture state cancels.
The feature reuses existing auth and service-state outcomes; it adds no Supabase client, account,
RPC, credential store, location request or external service.

One backlog cycle receives at most one scheduling attempt, for about 24 hours later. The fixed
local ID is `471031`; title is `GSIP sync reminder`; body is `Open GSIP to review unsynced work.`
No notification contains counts, queue records, photo/sample identities, contributor names,
coordinates, addresses, account IDs, session tokens, extras, attachments or navigation URLs.
The plugin receives inexact flags on the notification object and a nonrepeating `schedule.at`
with `allowWhileIdle:false`. GSIP never opens exact-alarm settings. Selecting an owned reminder
focuses the existing queue view only after fresh local ownership/gate/permission checks; it
never syncs, signs in, requests location or follows callback-supplied data.

Consumed-cycle state survives refresh, partial sync and restart. Restart first clears owned
pending and delivered notifications, and does not recreate an already consumed cycle. A new
empty-to-nonempty transition permits another attempt. This deliberately favors avoiding repeated
alerts over guaranteeing an alert after an app restart. Opt-out never discards unsynced content.

## Durable cancellation

IndexedDB version 4 adds only a private reminder-intent store, preserving earlier queue,
photo-draft, library and generation stores. Intent contains the existing account binding,
opt-in boolean, epoch/revision, backlog/consumed booleans and cleanup marker, never a credential
or session object. Queue clearing disables intent and increments its epoch in the same transaction.

Native operations are serialized under a cross-context Web Lock. Devices without that lock hold
scheduling and can still attempt owned-ID cleanup; capture remains available. Opt-out, sign-out,
account changes, rights requests, disposal and observed gate changes immediately invalidate the
local epoch and persist cleanup intent. A schedule already submitted may finish later: cleanup
runs **after** that completion, cancelling pending and removing delivered notifications by ID,
then reading both inventories. A void cancel response alone is never proof of absence.

An uncertain native reply/readback leaves cleanup pending and prevents another scheduling
attempt. A request whose native reply never settles can hold that native-operation chain until
restart; the durable rights fence does not wait for it. Confirmed withdrawal/deletion proceeds
through the existing server request and queue clearing. Device cleanup uncertainty cannot change
its successful result into an apparent server failure; failed server requests preserve queued
content. Reopening clears owned OS state before considering any new reminder.

**Limits:** an already displayed alert or OS dialog cannot be retracted retroactively. An offline
or background app cannot instantly observe a remote capture closure; cancellation follows the
next observed transition. OS permission can change between checking it and invoking the pinned
plugin, whose scheduling API may request permission. A fresh durable epoch, opt-in, owner and gate check after lazy import, followed by a synchronous
local lifecycle/epoch fence immediately before dispatch, prevents already invalidated intent from
reaching the SDK. Late listener registrations remove their own handles after disposal; stale
callbacks do not read or mutate shared storage. Disposed refresh, auth/queue callbacks and queued
operations cannot observe or rewrite a replacement lifetime. Cleanup owns only the persisted
epoch/account it originally fenced; a changed generation stops its pending/delivered cleanup.
An already admitted transaction that becomes stale returns its original state without another write. These checks do not promise OS/database atomicity or
instant cross-process cancellation. Device tests must measure those races. No exact delivery
time, iOS storage-backup protection or App Store guideline 4.2 acceptance is inferred from mocks
or a native build.

## Dependency and permissions

| Dependency                                            | Licence                                     | Maintenance signal                                                      | Size                                                 |
| ----------------------------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------- |
| `@capacitor/local-notifications` **8.3.1**, exact pin | MIT; published archive includes its licence | Official Ionic repository; npm release 2026-08-19, inspected 2026-10-13 | 82,938 compressed bytes; 506,577 unpacked file bytes |

Primary evidence: [exact npm metadata](https://registry.npmjs.org/@capacitor/local-notifications/8.3.1),
[published archive](https://registry.npmjs.org/@capacitor/local-notifications/-/local-notifications-8.3.1.tgz),
[official source](https://github.com/ionic-team/capacitor-local-notifications),
[official API documentation](https://capacitorjs.com/docs/apis/local-notifications).
Archive SHA-256: `f5772636102fdcbdba564a9bcb32db5d799bb6e27fdeaebc39b2abffe727c287`.
The archive declares no JS runtime dependency, a Capacitor core >=8 peer, and no JAR/AAR files.
That does not license its resolved native dependencies or measure its APK impact.

Android registration adds only this plugin alongside camera/filesystem; geolocation remains
excluded on Android. `POST_NOTIFICATIONS` is the new opt-in sensitive allowance.
`RECEIVE_BOOT_COMPLETED` supports the plugin's pending-reminder restore receiver after unlock.
`WAKE_LOCK` is removed: no acquisition was found in the inspected exact plugin/core code and
this schedule uses nonwaking RTC. `SCHEDULE_EXACT_ALARM` and `USE_EXACT_ALARM` are removed and
explicitly rejected in ordinary and SDK-qualified generated manifests and compiled APK dumps.
Every earlier sensitive-permission and closed-SDK rejection remains effective. iOS adds no usage
string, background mode or remote-notification permission. Existing all-domain Android cloud
exclusions include native SharedPreferences and the new private IndexedDB state; physical-device
backup/transfer checks remain separate. iOS WebKit backup exclusion remains blocked/unverified.

Direct Android declarations include Capacitor Android and AndroidX AppCompat (default 1.7.1),
with Kotlin 2.0.21 and AGP 8.13.0 build defaults. Actual selected runtime coordinates, binary
hash/size, POM and licence/notice evidence must come from the exact-head native CI audit, not
from these defaults. iOS requires actual SwiftPM resolution and separate Capacitor/Cordova
provenance; an MIT npm wrapper does not imply an MIT binary. [The native CI audit](APP_NOTIFICATION_NATIVE_AUDIT.md) records runtime evidence. Native artifact comparison must
use the exact parent, same runner/toolchain/run number/closed flags/signing inputs, and report
an overall feature delta including UI/resources/Kotlin. It is not plugin-only attribution and
npm archive bytes are not native build impact.

## Verification and remaining gates

Behavior tests cover the generic native/web seam, explicit permission/denial/error, one-cycle
bounds, fresh account/queue/gate checks, stale permission/schedule replies, persistent cleanup,
restart/overlap, taps that ignore injected data, and existing rights outcomes with never-settling
OS replies. Additive database-upgrade tests retain legacy submission/draft/library bytes. Permission
tests independently exercise generated removals and compiled rejection, including SDK-qualified
exact-alarm names and all previous sensitive/closed SDK cases. Exact commands/outcomes and
independent-review closure belong in the PR evidence, not an assumed pass here.

Native CI supplies unsigned Android/iOS artifacts and runtime/build comparison evidence. Local
Android SDK/Xcode and physical devices were unavailable during authoring. Before enabling this
feature for real contributors, stage Android 12/13+ and iPhone checks with synthetic data:
opt-in/denial/revocation, foreground/background/killed/offline, delivery/cancellation, reboot/unlock,
opt-out reboot, stale-dialog/schedule races, fresh access on tap, no exact-alarm settings,
pending/delivered absence and generic native logs. Record Doze/OEM/iOS delays and unsupported
behavior honestly. Signing/accounts, backup/device proofs, counsel, capture and production gates
remain owner actions.

**Implementation assumptions:** one 24-hour attempt per nonempty cycle; conservative refusal of
mixed/unknown-owner or unresolved work; persistent opt-in is account-bound; a restart cancels the
old attempt and consumes that cycle; unsupported Web Locks hold reminders; DOM focus/visibility
refresh is the initial lifecycle signal and needs device proof. These are bounded local UX choices,
not a new data-sharing, retention or scientific-authority policy.
