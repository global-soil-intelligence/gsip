## Work package

- WP: WP-APP-1, GSIP phone app (`docs/BUILD_ORDER.md` §4, Phase 1.5)
- Branch: `wp-app-1-phone-app`
- Stacked on (if any): `wp-agent-1-read-api`

## Summary

The capture app becomes the GSIP phone app (`com.globalsoilintelligence.app`, Capacitor 8), the
main contribution funnel (SPEC section 4). It shares one TypeScript codebase with the website's
capture app.

- **Platform layer** (`apps/capture-pwa/src/platform/`). Native camera and location inside the app,
  file inputs and the Geolocation API in browsers, chosen at runtime. Native plugins load only
  inside the app.
  - **Native photos.** Each becomes the queue's JPEG photo. JPEG format and the 12 MiB limit are
    checked. Photos are never saved to the library, edited, resized or rotated.
  - **Camera copy.** The plugin's own copy is deleted as soon as the app has read it.
  - **Attestation provider** `none` until a server verifier exists (I10).
  - **Claims.** `ingest_path` is `app`.
- **Saved photos.** "Use a saved photo" uses the web view's file input on both platforms. It needs
  no permission, shares only the chosen photo, and iOS hands over HEIC photos as JPEG.
- **Location.**
  - iOS uses the geolocation plugin (CoreLocation).
  - Android uses the web view's location API, because the plugin would compile Google's closed Play
    services SDK into the app (guardrail 6).
  - CI fails the Android build if any closed SDK reaches the runtime classpath.
- **Photos survive the camera.** They are kept in IndexedDB as soon as they are taken (queue
  database v2), so Android ending the app while the camera is open loses nothing. A stale camera
  result never locks the form.
- **My Soil.** The signed-in contributor's observations, read through RLS with an explicit
  contributor filter.
  - Each shows date, status and shots.
  - "Withdrawn" shows while a deletion request is pending.
  - Once published, it shows the likely public area: the finest published cell the observation
    falls in.
  - It never reads coordinates or shows a private cell, and it reloads when the phone comes back
    online.
- **Permissions** (`scripts/app_permissions.py`).
  - **iOS:** camera and when-in-use location with purpose strings, plus the photo-library strings
    that the plugin's linkage requires but the app never triggers.
  - **Android:** coarse and fine location only. CAMERA, AD_ID, storage, media, microphone and
    background location are removed.
  - CI checks the permissions the built APK and the built iOS app actually hold.
- **Builds** (`.github/workflows/app-build.yml`): an unsigned Android debug APK and an iOS
  simulator build, kept as artifacts. Signing and store upload are WP-APP-2.
- **Store readiness** (`docs/APP_STORE.md`): permissions, privacy labels, the in-app deletion path,
  payments, review notes and the device checks before submission. The privacy notice gains a
  phone-app section, and the legal pack's README tells counsel which contribution surfaces exist.
- **Sync fix.** A coalesced follow-up drain still ran after its screen closed and could send a
  record queued for the next screen, which then sent it too. This showed up as a flaky test under
  load. A closed screen now starts no drain, and an in-flight drain stops before its next record.

## Acceptance criteria

- [x] vitest: the platform layer selects native implementations in the app and web ones elsewhere;
      native output becomes a JPEG queue photo; location maps accuracy and source (`platform`,
      `native-app`).
- [x] vitest: My Soil lists only the signed-in contributor's submissions and renders no
      coordinates (`my-soil`).
- [x] `app-build.yml` produces the Android debug APK and the iOS simulator build. [Verified run](https://github.com/global-soil-intelligence/gsip/actions/runs/38186898193). **Shown by this
      PR's first CI run:** the build sandbox has no Android SDK or Xcode. The workflow's ordering
      and safety are unit-tested (`tests/test_workflows.py`).
- [x] The app requests only camera and when-in-use location, each with a purpose string. The
      permissions are tested on Capacitor 8.5.2's generated templates
      (`tests/test_app_permissions.py`), and CI rechecks the built artifacts.

## Invariant impact

- [x] I7: My Soil never reads coordinates or shows unpublished cells; no plugin result reaches the
      device log (`loggingBehavior: 'none'`).
- [x] I10: the app claims `ingest_path = app` and attestation `none`; tiers stay server-derived.
      Android captures keep their EXIF and can reach tier 1. iOS re-encodes and stays at tier 0
      (see `docs/APP_STORE.md`).

## Business guardrails

- [x] B1 and guardrail 6: no closed SDK ships; CI enforces it. B3: contributing stays free, with no
      in-app purchase. B5: no ads, tracking or advertising ID.

## Agent contribution

- [x] Written by Claude (Claude Opus 5.5), named in `Co-Authored-By` trailers. An independent agent
      review followed, fixed in `cd94c19`, plus a legal-pack status update in `a8818aa`.

Human of record: Justin Hart. **Sign-off pending:** an agent never certifies the DCO.

## Dependencies and deviations

| Package                                                                     | Version | Licence | Notes                                                                                       |
| --------------------------------------------------------------------------- | ------- | ------- | ------------------------------------------------------------------------------------------- |
| `@capacitor/core`, `@capacitor/cli`, `@capacitor/android`, `@capacitor/ios` | 8.5.2   | MIT     | The app shell; the CLI and platforms are dev dependencies                                   |
| `@capacitor/camera`                                                         | 8.2.4   | MIT     | Native libraries `ion-android-camera` and `IONCameraLib`, both MIT, with no Play services   |
| `@capacitor/filesystem`                                                     | 8.1.3   | MIT     | Deletes the camera plugin's copy (`ionfilesystem-android` and `IONFilesystemLib`, both MIT) |
| `@capacitor/geolocation`                                                    | 8.2.2   | MIT     | iOS only (`IONGeolocationLib`, MIT). Excluded from Android under guardrail 6                |

The website precaches about 30 kB of plugin code but never runs it.

**Decisions** (see `docs/APP_STORE.md`):

- Apple ($99 a year) and Google Play ($25 once) developer accounts.
- Whether App Store Connect will require an Always-location purpose string (ITMS-90683). GSIP
  never requests it.
- Whether the stores count photo publication as sharing.
- Keep or exclude app storage from phone backups.
- The deletion contact for Google Play's web form.
- A CAPTCHA provider that accepts the app's origins.

## Verification evidence

Run locally on `cd94c19`, 2026-10-11. `a8818aa` changes only `docs/legal/README.md`; prettier, the language guard and the processor scan pass on it.

- `pnpm lint` and `pnpm typecheck` pass.
- vitest: schema 126, site 28, map 15, capture 133.
- ruff, mypy (34 files) and pytest (223) pass, including 18 permission-policy tests on Capacitor 8.5.2's generated templates.
- pgTAP: prior_attempts 30/30, rls 42/42, wp6b_integrity 51/51, wp6d_rights 70/70, wp6e_provenance 57/57, wp_agent1_public 12/12. Migration test: 13/13.
- `deno check` passes.
- Playwright: desktop Chrome 12/12, mobile Chrome 12/12.
- Builds: `pnpm build` (every workspace) and `build:app`. Site budget 329,574 / 716,800 bytes; map budget 1,654,727 / 5,242,880 bytes.
- Load: the capture suite ran 12 times, four at a time on two cores, with no failure. Before the sync fix, 1 run in 9 failed.
- Mutation checks: removing either new sync guard makes its new test fail.
- Not runnable here: Gradle and Xcode builds. This pull request's CI produces the APK and the simulator build.

## Independent review and resolutions

Verdict: "well built… not ready to merge as is", because of M-1 and M-2. All findings are fixed.

| ID  | Severity | Finding                                                                                                                            | Resolution                                                                                                                               |
| --- | -------- | ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| M-1 | Major    | On iOS, "Use a saved photo" went through the plugin's library browser, which asks for photo-library access and mostly rejects HEIC | The web view's file input on both platforms: no permission, only the chosen photo, HEIC converted to JPEG                                |
| M-2 | Major    | `@capacitor/geolocation` compiled Google's closed Play services location SDK into the APK (guardrail 6)                            | Plugin on iOS only; Android uses the web view's location; CI's `check-dependencies` fails on gms, firebase, play, mlkit or ads libraries |
| m-1 | Minor    | My Soil labelled every passed row with a published cell the export might not place it in                                           | "Likely public area" (the finest published ancestor) with honest copy; a withdrawn status; reloads when back online                      |
| m-2 | Minor    | Mutation runs survived (reversed resolutions, status mapping)                                                                      | Fixtures with two published ancestors and every status; native flow, drafts, and Android location tests                                  |
| m-3 | Minor    | Comments and docs treated EXIF retention as unknown                                                                                | Documented per platform: Android keeps the original EXIF; iOS drops it, as Safari does                                                   |
| m-4 | Minor    | Android could kill the app while the camera was open, losing shot A; a camera call could hang the form                             | Photos kept in IndexedDB as soon as they are taken; request tickets ignore stale results; a "Discard these photos" action                |
| m-5 | Minor    | The plugin's full-resolution copy, possibly with GPS EXIF, stayed in the app cache                                                 | Deleted with `@capacitor/filesystem` as soon as it has been read                                                                         |
| n-1 | Nit      | A comment claimed websites never download the plugin code                                                                          | Comment corrected: the code is precached (about 30 kB) but never run                                                                     |
| n-2 | Nit      | Debug builds logged plugin results, positions included                                                                             | `loggingBehavior: 'none'`                                                                                                                |
| n-3 | Nit      | CAMERA was silently allowed and AD_ID was not treated as sensitive                                                                 | Both removed from the merged manifest, and the checks fail on either                                                                     |
| n-4 | Nit      | Each CI APK is signed with a fresh debug key                                                                                       | Documented: uninstall first, and withdraw test contributions before uninstalling                                                         |
| n-5 | Nit      | Declining Android's "turn on location" dialog showed "allow location in settings"                                                  | Mapped to "location is off"                                                                                                              |
| n-6 | Nit      | Payments wording, and the photo-library-add string                                                                                 | Physical goods must be paid outside store billing (Apple 3.1.5(a), Play policy); the string is reworded                                  |

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_017nrzCzGuaW3XpYuuvMm7U1


## Changes after review

- Fixed the first iOS CI failure: macOS resolved `./MySoil` to `mySoil.ts` before `MySoil.tsx`, which has the UI export. Renamed the unchanged UI component to `MySoilPanel.tsx` and updated its two imports.
- Added a cross-platform source-module guard: it fails on the original case-insensitive `.ts`/`.tsx` collision and passes after the rename. No RLS, permissions, dependency checks, capture flags or user-facing behavior changed. No new dependency.
- Verification run after the fix: lint, typecheck, all 302 Vitest tests, production builds, map/site budgets, macOS capture `build:app`, ruff and strict mypy passed. Pytest: 220 passed, 4 GDAL-dependent tests skipped locally; CI supplies GDAL. The new guard failed before the change and passed after it.
- Assumption: supported macOS runners may use case-insensitive filesystems, so source module names must be unambiguous under case folding.
- First app-build run produced only the Android APK and failed the iOS web build. The repaired [App build run](https://github.com/global-soil-intelligence/gsip/actions/runs/38186898193), at `94e19ff`, completed successfully with both artifacts: `gsip-capture-android-debug` (7,144,177 bytes) and `gsip-capture-ios-simulator` (3,323,666 bytes). Its dependency and built-permission checks passed unchanged. This repaired run is the acceptance evidence; the original description anticipated success on the first run.
