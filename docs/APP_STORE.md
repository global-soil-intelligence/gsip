# GSIP phone app: store readiness

The GSIP phone app (WP-APP-1) is the capture app in `apps/capture-pwa` wrapped with Capacitor
(`com.globalsoilintelligence.app`, "GSIP Capture"). It is the main contribution funnel (SPEC
section 4). This page records what the stores will ask and what GSIP answers. Signing, store
listings and upload are not built yet; items marked **[DECISION]** need the product owner or
counsel.

## How the app is built

- `.github/workflows/app-build.yml` builds the web assets with
  `pnpm --filter @gsip/capture-pwa build:app`: the capture app without its service worker, which
  would serve a stale version after an app update. It then generates the iOS and Android projects
  with `cap add`, applies the permissions with `scripts/app_permissions.py`, and builds an
  unsigned Android debug APK and an iOS simulator build. Both are kept as workflow artifacts for
  14 days.
- The native projects are generated, never committed (`apps/capture-pwa/android/` and `ios/` are
  ignored). To work on them locally: `pnpm --filter @gsip/capture-pwa build:app`, then
  `pnpm exec cap add android` (or `ios`) in `apps/capture-pwa`, then
  `python scripts/app_permissions.py apply-android apps/capture-pwa/android/app/src/main/AndroidManifest.xml`
  (or `apply-ios apps/capture-pwa/ios/App/App/Info.plist`).
- Builds use the same public configuration as the website (`SUPABASE_URL`,
  `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_CAPTURE_LIVE` and the legal links). Like the website,
  the app accepts observations only in builds made with `VITE_CAPTURE_LIVE=true`, and the
  database's capture switch decides the rest.

## Permissions

The app asks for two things, each only when the person uses the feature:

| Platform | Permission                                                               | When it is asked                | Purpose string                                                                                                                  |
| -------- | ------------------------------------------------------------------------ | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| iOS      | Camera (`NSCameraUsageDescription`)                                      | First "Take photo"              | GSIP uses the camera to photograph soil beside the printed reference card.                                                      |
| iOS      | Location when in use (`NSLocationWhenInUseUsageDescription`)             | First "Use my current location" | GSIP records where each soil photo was taken, privately. Only a broad area shared by at least 3 contributors is ever published. |
| Android  | Location while in use (`ACCESS_COARSE_LOCATION`, `ACCESS_FINE_LOCATION`) | First "Use my current location" | Android shows its own prompt; the form explains the use beside the button.                                                      |

- **Android camera.** The app declares no camera permission. "Take photo" opens the system
  camera app, which needs none, so Android never asks.
- **Saved photos.** "Use a saved photo" opens the system photo picker, which needs no permission
  on either platform. iOS still requires two photo-library purpose strings, because the camera
  plugin links the library APIs; the app never triggers either prompt:
  `NSPhotoLibraryUsageDescription` ("Choose a soil photo you already took to add it to an
  observation.") and `NSPhotoLibraryAddUsageDescription` ("GSIP keeps your soil photos inside
  the app and does not add them to your library.").
- **Never requested.** Background location, the microphone, contacts, storage and media
  permissions. `scripts/app_permissions.py` removes any of these that a library brings into the
  Android manifest, and CI fails if the built APK or the built iOS app holds any of them
  (`check-apk`, `check-ios`).
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
- On Android, a location fix may come from Google Play services' location provider, according
  to the phone's own location settings. GSIP receives only the fix.
- Queued observations, including their precise points, wait in the app's own storage until they
  sync. Android and iOS include app storage in the phone's own backups by default, which also
  keeps the device's account across a phone change. **[DECISION]** keep (account continuity)
  or exclude (no copy of unsynced points in backups).

## Account and data deletion

Both stores require in-app deletion for apps with accounts. The app has it: **Your data →
Delete my account…** (WP-6d) files the request, signs out every device and deletes the data
within 30 days; **Withdraw my contributions…** keeps the account and removes the observations.
Google Play also asks for a web page where people can request deletion without the app. An
anonymous app account cannot be identified from the web, so that page is the privacy contact in
`docs/legal/PRIVACY.md` **[DECISION: contact address]**.

## Payments

The app sells nothing and has no in-app purchase. If printed cards or kits are ever offered from
the app, they are physical goods, which both stores allow to be paid for outside their billing
(Apple guideline 3.1.5(a); Google Play's payments policy). Digital goods or subscriptions would
need store billing.

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

## Before the first store submission

Check on one Android phone and one iPhone, and record the results in the pull request:

1. "Take photo" for shots A and B, the previews, and "Use a saved photo" (on an iPhone whose
   library holds HEIC photos: the app accepts only JPEG, so record whether the picker returns
   one).
2. Location allowed, denied, and with location services off; then the manual fields.
3. Queue an observation in airplane mode, close the app, reopen it online, and see it sync.
4. After QA, confirm a fresh in-app capture reaches provenance tier 1 (its original keeps an
   EXIF capture time). If a platform's camera plugin strips EXIF, app captures stay at tier 0;
   record it and decide whether to keep the native camera there.
5. My Soil lists the observation with its status, shots and, once published, its public area.
6. Your data: withdraw, then delete the account.
7. Links to the map, the reference card and the legal pages open in the browser.

Still to do before submission: app icons and launch screens (the generated projects use
Capacitor's defaults), version numbers set by CI, signing, store listings and screenshots.
