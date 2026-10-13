# GSIP phone app: store readiness

The GSIP phone app (WP-APP-1) is the capture app in `apps/capture-pwa` wrapped with Capacitor
(`com.globalsoilintelligence.app`, "GSIP Capture"). It is the main contribution funnel (SPEC
section 4). This page records what the stores will ask and what GSIP answers. Signing, store
listings and upload are not built yet (WP-APP-2); items marked **[DECISION]** need the product
owner or counsel.

## How the app is built

- `.github/workflows/app-build.yml` builds the web assets with
  `pnpm --filter @gsip/capture-pwa build:app`: the capture app without its service worker, which
  would serve a stale version after an app update. It then generates the iOS and Android projects
  with `cap add`, applies the permissions with `scripts/app_permissions.py`, refuses closed SDKs
  in the Android dependency tree, and applies CI versions and Android backup rules with
  `scripts/app_build.py`. It builds an Android debug APK (signed by Gradle's disposable debug
  key) and an unsigned iOS simulator app. Both are kept as artifacts for 14 days; CI checks
  their effective permissions, versions and the APK's compiled backup rules. Each platform is
  built twice with the same inputs and a separate JSON receipt records the comparison.
- The native projects are generated, never committed (`apps/capture-pwa/android/` and `ios/` are
  ignored). To work on them locally: `pnpm --filter @gsip/capture-pwa build:app`, then
  `pnpm exec cap add android` (or `ios`) in `apps/capture-pwa`, then
  `python scripts/app_permissions.py apply-android apps/capture-pwa/android/app/src/main/AndroidManifest.xml`
  (or `apply-ios apps/capture-pwa/ios/App/App/Info.plist`). Then apply the versions and backup
  settings: `python scripts/app_build.py apply-android apps/capture-pwa/android/app 101
apps/capture-pwa/package.json` (or `apply-ios apps/capture-pwa/ios/App/App/Info.plist 101
apps/capture-pwa/package.json`). Local build number `101` is synthetic, never a store upload.
- Builds use the same public configuration as the website (`SUPABASE_URL`,
  `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_CAPTURE_LIVE` and the legal links). Like the website,
  the app accepts observations only in builds made with `VITE_CAPTURE_LIVE=true`, and the
  database's capture switch decides the rest.
- Plugins: camera, file and optional local-notification plugins on both platforms; the geolocation plugin on iOS only. On
  Android it would compile Google's closed Play services location SDK into the app, which
  BUILD_ORDER guardrail 6 does not allow without sign-off, so the Android app uses its web view's
  own location API, which asks for the same permissions.
- Capacitor never writes plugin results to the device log (`loggingBehavior: 'none'`), so
  positions do not reach test devices' logs either.

## Permissions

The app asks for camera/location when those features are used, and notifications only after explicit reminder opt-in:

| Platform    | Permission                                                               | When it is asked                 | Purpose string                                                                                                                  |
| ----------- | ------------------------------------------------------------------------ | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| iOS         | Camera (`NSCameraUsageDescription`)                                      | First "Take photo"               | GSIP uses the camera to photograph soil beside the printed reference card.                                                      |
| iOS         | Location when in use (`NSLocationWhenInUseUsageDescription`)             | First "Use my current location"  | GSIP records where each soil photo was taken, privately. Only a broad area shared by at least 3 contributors is ever published. |
| Android     | Location while in use (`ACCESS_COARSE_LOCATION`, `ACCESS_FINE_LOCATION`) | First "Use my current location"  | Android shows its own prompt; the form explains the use beside the button.                                                      |
| iOS/Android | Local notifications (`POST_NOTIFICATIONS` on Android 13+)                | Explicit "Enable sync reminders" | One generic reminder to review unsynced work; denial leaves capture usable.                                                     |

- **Android camera.** The app declares no camera permission, and removes one if a library brings
  it in. "Take photo" opens the system camera app, which then needs none, so Android never asks.
- **Saved photos.** "Use a saved photo" is the web view's file input on both platforms. Its
  system picker needs no permission and shares only the photo chosen, and iOS converts HEIC
  photos to JPEG for it. The camera plugin links the iOS photo-library APIs, so iOS still
  requires two purpose strings, which the app never triggers: `NSPhotoLibraryUsageDescription`
  ("GSIP lets you choose a saved soil photo with the system picker, which shares only the photo
  you pick.") and `NSPhotoLibraryAddUsageDescription` ("GSIP keeps your soil photos inside the
  app and does not save them to your library.").
- **Reminders.** [APP-2B](APP_SYNC_REMINDERS.md) adds one inexact 24-hour scheduling attempt per backlog cycle, with no private notification payload, push service or location calculation. Android adds normal `RECEIVE_BOOT_COMPLETED` for bounded restoration after unlock; exact-alarm permissions and `WAKE_LOCK` are removed/rejected, including SDK-qualified forms. Opt-out/sign-out/rights/sync/empty or observed closed gates clear the owned pending/delivered reminder; uncertain cleanup stays held. Device behavior is not proven by the native build.
- **Never requested.** Background location, the microphone, contacts, storage and media
  permissions, and the advertising ID. `scripts/app_permissions.py` removes any of these that a
  library brings into the Android manifest, and CI fails if the built APK or the built iOS app
  holds any of them (`check-apk`, `check-ios`).
- If App Store Connect reports a missing `NSLocationAlwaysAndWhenInUseUsageDescription` (ITMS-90683)
  because the location library links the always-authorization API, GSIP still never requests it.
  Adding that key needs a conscious change to `IOS_PURPOSES` in the script, and the check will
  then require it. **[DECISION]** if it happens.

## Privacy labels

Answers for Apple's App Privacy details and Google Play's Data safety form. They follow
`docs/legal/PRIVACY.md`, which counsel must approve first.

| Data                                                            | Collected                      | Linked to the person                | Purpose                                              | Shared                                                                                                                                                                            |
| --------------------------------------------------------------- | ------------------------------ | ----------------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Precise location (the observation's point and its accuracy)     | Yes                            | Yes: the device's anonymous account | App functionality (quality checks, soil-map context) | No. Only a hexagonal area shared by at least 3 contributors is published.                                                                                                         |
| Photos (the soil photos the person takes or chooses)            | Yes                            | Yes                                 | App functionality; publication in the open dataset   | Published under CC BY-SA 4.0 at the person's explicit request (the contribution grant). **[DECISION]** whether the stores count this as sharing or as user-initiated publication. |
| User ID (the anonymous account identifier)                      | Yes                            | Yes                                 | App functionality (sync, withdrawal and deletion)    | No                                                                                                                                                                                |
| Other data: coarse device model, land cover and surface answers | Yes                            | Yes                                 | App functionality (quality checks)                   | The answers are published with the observation; the device model never is.                                                                                                        |
| E-mail address                                                  | Not in this version of the app |                                     |                                                      |                                                                                                                                                                                   |
| Diagnostics, analytics, advertising identifiers, tracking       | No                             |                                     |                                                      |                                                                                                                                                                                   |

- All traffic is encrypted in transit (HTTPS to Supabase).
- On Android the position comes from the phone's own location services through its web view,
  which on many phones include Google Play services, as the phone's settings decide. GSIP's app
  contains no Google location code and receives only the position.
- Photos the app has taken for an observation not yet queued, and queued observations with
  their precise points, wait in the app's own storage until they sync (or until the person
  discards them). The camera plugin's own copy of each photo is deleted as soon as the app has
  read it. Justin's policy is to exclude the private queue, photo drafts and session from cloud
  backups. Android rules and the outstanding iOS gate are described below; the decision is
  resolved, but iOS protection is **blocked/unverified**.

## Versions and repeat-build evidence (WP-APP-2A)

The marketing version is `apps/capture-pwa/package.json` (`0.1.0`), used for Android
`versionName` and iOS `CFBundleShortVersionString`. CI uses the canonical positive
`GITHUB_RUN_NUMBER` from this same `app-build.yml` workflow for Android `versionCode`.
For input `n`, iOS `CFBundleVersion` is
`1 + floor((n - 1) / 10000).floor((n - 1) / 100) % 100.(n - 1) % 100`.
For example, `1` → `1.0.0`, `101` → `1.1.0`, `10000` → `1.99.99`, and `10001` → `2.0.0`.
Inputs stop at `99,990,000` (`9999.99.99`); aliases such as `01` are rejected. Reruns use
identical numbers. The mapping is injective and increasing within this workflow.

**Assumption:** the workflow identity/counter is retained. GitHub scopes run numbers to a
workflow. Before replacing that workflow or uploading a signed build, Justin must compare
both stores' last build numbers; do not reuse a counter or upload a rerun as a new build.

CI includes `gsip-android-build-receipt.json` and `gsip-ios-build-receipt.json` in the existing
Android and iOS artifact archives, respectively. Receipts record source commit, lockfile/configuration hashes, actual
runner/toolchain versions, build-number input, both artifact hashes and a comparison.
`byte_equal` means exact archive equality. `entry_content_equal` compares every non-directory
ZIP entry's bytes. This view omits directory entries, ZIP metadata and container bytes,
including APK signing blocks outside ZIP entries; changed/missing payload entries remain
reported. Full hashes and `byte_equal` include all artifact bytes. Entry equality alone is not
artifact reproducibility. Neither a successful build nor equal version numbers proves it. This compares repeated builds in one job; it does not prove
cross-runner reproducibility. Toolchain pins and resolved versions make inputs traceable;
floating runner images/Xcode and regenerated debug keys can change bytes between jobs.
Only the exact artifact, reference artifact and output receipt paths are excluded from the
source-clean check; other untracked source files or tracked modifications make it false.
Local precommit receipts with `source_tree_clean=false` are preparation evidence, not builds
identified by the HEAD commit alone.

## Phone backups: resolved policy and remaining device gates

Android uses `allowBackup=true` only to activate explicit transport rules. On Android 12+
(API 31+), `dataExtractionRules` excludes all nine app-storage domains from cloud backup and
explicitly includes them for direct device-to-device transfer. This covers WebView storage,
queued points, photo drafts and session files. On Android 11 and older, `fullBackupContent`
excludes the same nine domains from both cloud backup and transfer. CI resolves the compiled
application's resource references, verifies the packaged XML, and rejects custom backup agents
or extra resource configurations. No permission or closed-SDK check is relaxed.

**Android device gate:** before claiming device protection, use synthetic drafts, queue and
session records to test cloud backup/restore on a physical device, plus direct transfer on
Android 12+ and exclusion on a supported legacy device. Compiled rules prove configuration,
not the behavior of every phone manufacturer's transfer tooling. Existing backups already
held by a provider cannot be retroactively erased by an app update.

**iOS gate — blocked/unverified:** the queue/drafts live in WebKit IndexedDB and the session
in localStorage. No reliable exclusion is implemented here. An Info.plist key or simulator
build cannot prove exclusion. Apple's file resource exclusion flag can reset after writes,
and Apple describes it as guidance rather than a guarantee. The existing filesystem plugin's
`LibraryNoCloud` directory does not move WebKit's current stores.

The next separately specified options are to migrate private storage into the existing
no-cloud filesystem directory while preserving offline durability (recommended for study),
or add a native exclusion bridge after Justin approves an exception to the TypeScript/Python
rule. An ephemeral WebKit store would lose offline work and is unsuitable. Either viable
option needs synthetic real-device backup/restore tests before iOS store readiness; no option
has been selected or implemented by this package.

Once a platform's cloud exclusion is implemented and verified, a fresh install or cloud restore
starts a new anonymous account and loses unsynced work. Current iOS cloud-restore behavior is
**unverified**; older backups may still restore private data. A verified direct transfer on
Android 12+ may preserve the queue and account. Until in-app
e-mail linking ships in WP-APP-2, withdraw old-device contributions through the privacy contact
when the old account is inaccessible. Retain the old phone until its queued work has synced.

Platform references: [Android backup transport rules](https://developer.android.com/identity/data/autobackup),
[Apple bundle versions](https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/Articles/CoreFoundationKeys.html),
and [Apple backup exclusion](https://developer.apple.com/documentation/foundation/optimizing-your-app-s-data-for-icloud-backup).

## Account and data deletion

Both stores require in-app deletion for apps with accounts. The app has it: **Your data →
Delete my account…** (WP-6d) files the request, signs out every device and deletes the data
within 30 days; **Withdraw my contributions…** keeps the account and removes the observations.
Both also discard what is still queued, and any photos taken, on the device. Google Play also
asks for a web page where people can request deletion without the app. An anonymous app account
cannot be identified from the web, so that page is the privacy contact in
`docs/legal/PRIVACY.md` **[DECISION: contact address]**.

## Payments

The app sells nothing and has no in-app purchase. If printed cards or kits are ever offered from
the app, they are physical goods, which both stores require to be paid for outside their own
billing (Apple guideline 3.1.5(a); Google Play's payments policy). Digital goods or
subscriptions would need store billing.

## Review notes

- Submit only a build with capture open. A build with capture closed shows a holding message,
  which a reviewer would reject as incomplete.
- No sign-in is needed: the first synced observation creates the device's anonymous account.
  E-mail sign-in, to use one account on several devices, needs deep links (universal links and
  app links on `globalsoilintelligence.com`) and comes in a later version; the app says so.
- Reviewers can photograph any patch of soil with the printed reference card (the PDF is linked
  in the app) and use the manual latitude and longitude fields.
- The CAPTCHA planned for anonymous sign-ins before launch (SPEC section 11) must accept the
  app's origins (`capacitor://localhost` on iOS, `https://localhost` on Android).
  **[DECISION]** when the provider is chosen.

## Provenance of app photos

The server derives a photo's provenance tier from the original upload's own EXIF capture time
(WP-6e); client claims never raise it. With `@capacitor/camera` 8.2, Android returns the camera
app's original file, so its EXIF time survives and fresh captures can reach tier 1. iOS
re-encodes the photo and drops EXIF, exactly as Safari's file input does, so iPhone captures stay
at tier 0. A capture path that keeps iOS metadata is WP-APP-2 work if tier 1 on iPhones matters.

## Before the first store submission

Check on one Android phone and one iPhone, and record the results in the pull request:

1. "Take photo" for shots A and B, the previews, and "Use a saved photo" (on an iPhone whose
   library holds HEIC photos, confirm the picker hands over a JPEG).
2. Location allowed, denied, and with location services off; then the manual fields.
3. With Android's developer option "Don't keep activities" on, take shot A, then shot B: shot A
   must still be there after the camera returns (photos are kept as soon as they are taken).
4. Queue an observation in airplane mode, close the app, reopen it online, and see it sync.
5. After QA, confirm a fresh Android capture reaches provenance tier 1 and an iPhone capture tier
   0, as described above.
6. My Soil lists the observation with its status, shots and, once published, its likely public
   area.
7. Your data: withdraw, then delete the account.
8. Links to the map, the reference card and the legal pages open in the browser.
9. Android synthetic cloud backup/restore, legacy exclusion and Android 12+ direct-transfer
   checks described above; no private bytes in cloud backup.
10. The separately implemented iOS exclusion method passes synthetic real-device backup/restore
    checks. This remains **blocked/unverified** and prevents an iOS store-readiness claim.
11. Local sync reminders: Android 12/13+ and iPhone permission/denial/revocation, foreground/
    background/killed/offline, reboot/unlock, opt-out, empty/closed/foreign queue cancellation,
    late replies, fresh tap access and pending/delivered absence. Exact-alarm settings stay
    closed; synthetic private sentinels never enter native logs. This device evidence remains
    pending; unit tests and unsigned native artifacts do not prove it.

Each CI build is signed with a fresh debug key, so a newer APK will not install over an older
one: uninstall first. Uninstalling deletes the device's anonymous account and queue, so withdraw
or delete test contributions before uninstalling.

## Owner-controlled signing inputs (placeholders only)

The app will publish under Viridis LLC organization accounts controlled by Justin. Accounts,
certificates, keystores and upload credentials are not created by this work package.

| Platform | Required owner input                                                    | Status                             |
| -------- | ----------------------------------------------------------------------- | ---------------------------------- |
| Apple    | Viridis LLC Apple Developer organization / Team ID                      | Pending Justin                     |
| Apple    | App Store Connect app record and bundle-ID registration                 | Pending Justin                     |
| Apple    | Distribution certificate, provisioning profile and upload authorization | Pending Justin; secret stores only |
| Google   | Viridis LLC Play Console organization and app record                    | Pending Justin                     |
| Google   | Play App Signing enrollment, upload key and upload authorization        | Pending Justin; secret stores only |

Still to do before submission (WP-APP-2): the device backup gates, app icons and launch screens
(the generated projects use Capacitor's defaults), signing, store listings and screenshots.
Deep links and e-mail account linking wait for the owner-controlled accounts.

## Private library intake preparation (WP-LIB-4C)

App and Pages builds explicitly keep `VITE_CAPTURE_LIVE=false` and
`VITE_LIBRARY_INTAKE_LIVE=false`. The capture build emits `gsip-activation.json`
from the same values compiled into its code. Pages packaging and native APK/iOS
artifact checks refuse an open flag or a missing receipt; synthetic open builds
stay local. The independent hosted capability gate also defaults closed.

Library draft context, strict declaration JSON bytes, namespace/account bindings
and the queue generation fence use the existing `gsip-capture-v1` WebKit/browser
IndexedDB database (version 4 after APP-2B's additive reminder-intent store). They share the compiled Android all-domain cloud
backup exclusions and approved direct-device-transfer policy above. The existing
iOS cloud backup gate remains blocked/unverified; a local test does not establish
iOS backup exclusion or store readiness. Imported JSON files elsewhere on the
device remain outside GSIP deletion control; the web picker supplies no temporary
native path to erase.
