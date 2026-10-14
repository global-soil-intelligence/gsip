# APP-2C1: iOS storage feasibility result

**Result: blocked; no backend selected.** The v11 specification was approved and merged in
[#68](https://github.com/global-soil-intelligence/gsip/pull/68). This source-only work package
adds an offline evidence checker and records a negative capability review. It supplies no
storage adapter, migration, custom native code, dependency installation or device/backup proof.

Baseline: merge `883c7ee51dcb6c58cb7f309b78a590ea684ba8c7`, whose runtime and lockfile match
reviewed head `476bbdab190c99a3bb6d5d8143f21bebde6baf9f`. A verified source review is distinct
from storage feasibility. APP-2C2, APP-2C3 and all production/capture/store gates remain held.

## Complete persistence and rights scope

[The complete inventory and migration/device contract](IOS_PRIVATE_STORAGE.md) remains binding:
all six IndexedDB stores (`submissions`, `draftPhotos`, `libraryDraft`, `libraryNamespace`,
`queueState`, `syncReminder`); session/last UID/compatible legacy user and conditional PKCE
slots; WebKit database/WAL/localStorage/cookies/caches; native shared cookies and SDK preferences;
camera/picker temporary copies; staging/journal/recovery remnants; generic OS notifications.
The code binds actual application source bytes and independently checks the six-store set.
Queue generation and disabled cleanup-pending reminder fences survive combined rights clearing;
there is no invented phone tombstone table or persisted Supabase mutex.

This inventory is source evidence. No private cookie/cache contents, device container or real
contributor records were inspected. Logical deletion is not physical erasure. Current photo
output uses temporary files with best-effort cleanup, not a claimed backed-up Documents flow.

## Existing npm packages, all archive bytes checked against current lock integrity

Sizes below are compressed source archive / sum of unpacked regular-file payload bytes. They are not runtime size, installed transitive closure, or APK/iOS binary growth. Exact npm release dates are observed maintenance signals, not a security/support guarantee. Each named package licence was confirmed in its exact archive LICENSE file; archive integrity was checked against pnpm-lock.yaml.

| Existing package                       | Licence | Exact release date (UTC) | Compressed / unpacked bytes |
| -------------------------------------- | ------- | ------------------------ | --------------------------- |
| `@capacitor/filesystem@8.1.3`          | MIT     | 2026-08-19               | 72,912 / 435,689            |
| `@capacitor/core@8.5.2`                | MIT     | 2026-09-11               | 71,281 / 375,957            |
| `@capacitor/ios@8.5.2`                 | MIT     | 2026-09-11               | 87,631 / 410,508            |
| `@capacitor/camera@8.2.4`              | MIT     | 2026-09-01               | 89,747 / 539,175            |
| `@capacitor/geolocation@8.2.2`         | MIT     | 2026-08-13               | 27,435 / 138,192            |
| `@capacitor/local-notifications@8.3.1` | MIT     | 2026-08-19               | 82,938 / 506,577            |
| `@supabase/supabase-js@2.117.2`        | MIT     | 2026-09-25               | 171,213 / 649,532           |
| `@supabase/auth-js@2.117.2`            | MIT     | 2026-09-25               | 501,821 / 2,923,478         |
| `idb@8.0.3`                            | ISC     | 2025-05-07               | 16,368 / 82,779             |

## Observed native source resolution, not a repository-native lock

The observed generated Package.resolved is one of the exact-byte inputs listed below. npm files specify native version ranges; these observed exact native tags/revisions are not claims about every build. Each tag resolves to the reviewed commit and source archive hashes match the existing audit allowlist. All three exact archive licences are MIT. Public repositories were not archived when read; push timestamps include other branches and are only activity signals.

| Native source               | Observed exact commit                      | Exact commit date | Compressed / unpacked bytes |
| --------------------------- | ------------------------------------------ | ----------------- | --------------------------- |
| `ion-ios-filesystem@1.1.4`  | `56bd6f9e77cb4f2269c03f2d92a9fe58fe168a1c` | 2026-09-08        | 31,020 / 150,959            |
| `ion-ios-camera@2.0.0`      | `00c3dfdd6267f80db299d9c5a0bad522156b6cbc` | 2026-08-28        | 273,170 / 522,080           |
| `ion-ios-geolocation@2.1.1` | `db363927d3a954e3ea24d2e72b6e9814769a84be` | 2026-03-10        | 23,644 / 95,915             |

## Current filesystem capability table

The following source facts describe @capacitor/filesystem 8.1.3 + the observed ION filesystem 1.1.4. Every acceptance result stays unproven or blocked; this is not a storage implementation. Evidence IDs identify the exact-byte input files listed below. The offline checker recomputes their hashes; it does not infer behavior from method names or comments.

| Requirement                            | Exact source observation                                                                                                                | Acceptance | Evidence                                                                                             |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------- |
| declared no cloud mapping              | Enum maps to Library/NoCloud; name is not protection proof.                                                                             | unproven   | `filesystem_mapping:15-23`; `ion_filesystem_manager:337-368`                                         |
| exclude before first private write     | Exclusion attempt precedes creation and ignores failures; root creation occurs later during write.                                      | blocked    | `ion_filesystem_manager:361-367`; `ion_filesystem_manager:114-133`                                   |
| propagate exclusion errors             | try? discards marker-setting error.                                                                                                     | blocked    | `ion_filesystem_manager:365`                                                                         |
| read exclusion marker                  | API/stat result has no exclusion marker; private ION code has no readback.                                                              | blocked    | `filesystem_api_types:390-438`; `filesystem_mapping:38-49`                                           |
| verify post save replace restart       | Path resolution reattempts root marker; no post-operation readback or restart gate.                                                     | blocked    | `ion_filesystem_manager:114-157`; `ion_filesystem_manager:170-195`; `ion_filesystem_manager:361-367` |
| atomic file overwrite                  | Data.write default/no atomic option; String.write atomically:false.                                                                     | blocked    | `ion_filesystem_manager:114-133`                                                                     |
| atomic replace via rename              | Existing destination file is deleted before moveItem, exposing loss window.                                                             | blocked    | `ion_filesystem_manager:170-180`; `ion_filesystem_manager:297-309`                                   |
| durable crash commit                   | No exposed fsync, durable commit, exclusive-create, compare-and-swap or multi-record transaction primitive.                             | blocked    | `filesystem_api_types`; `ion_filesystem_manager:114-157`                                             |
| six store atomicity and fences         | Per-file methods do not preserve combined clear/generation/reminder transaction or conditional update.                                  | blocked    | `filesystem_api_types`; `source:apps/capture-pwa/src/queue.ts:79-117,254-270`                        |
| cross context writer ownership         | No provided transaction/ownership contract for JS read-modify-write across contexts; JS mutex alone insufficient.                       | blocked    | `filesystem_api_types`; `source:apps/capture-pwa/src/sync.ts:59-106`                                 |
| reject implicit web fallback           | Plugin registers IndexedDB web backend; a future iOS adapter must reject unsupported native mode explicitly.                            | blocked    | `filesystem_plugin_registration:1-5`; `filesystem_web_fallback:88-109`                               |
| relative path containment              | Directory mode resolves canonical containment; raw URL mode lacks that directory boundary; still needs bounded app-owned path contract. | unproven   | `ion_filesystem_manager:252-295`                                                                     |
| legacy webkit native residual coverage | Filesystem directory does not relocate or erase current WebKit/session/cookie/cache/journal state.                                      | blocked    | `source:docs/IOS_PRIVATE_STORAGE.md:46-76,86-110`                                                    |
| physical backup restore                | No physical device, backup, store/account/signing, production or live app-data action.                                                  | blocked    | `source:docs/IOS_PRIVATE_STORAGE.md:129-157`                                                         |

## Unadopted open components

All candidates remain **blocked/unselected**. Source archive licence, publication date and
package size are bounded observations, not support, binary provenance or runtime-size proof.
Declared npm SHA-512 integrity was verified; selected crucial source files also matched exact
immutable upstream commits. No candidate was installed or resolved as a native graph.

| Candidate                                                                                                                             | Licence / maintenance observation               | Compressed / unpacked source bytes | Result                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| [Community SQLite 8.1.1](https://github.com/capacitor-community/sqlite/tree/3f3f71606c8f292a3d6d841937bcfc5b5c45aeb5)                 | MIT; published 2026-08-06, Capacitor 8 peer     | 271,508 / 2,034,996                | Real SQL transactions are useful, but exclusion/readback/restart, safe diagnostics and host residuals remain unresolved.    |
| [Preferences 8.0.1](https://registry.npmjs.org/@capacitor%2fpreferences/8.0.1)                                                        | MIT; published 2026-02-12                       | 13,960 / 71,048                    | UserDefaults key/value, without the required transaction or exclusion contract.                                             |
| [Aparajita Secure Storage 8.0.1](https://github.com/aparajita/capacitor-secure-storage/tree/3b0d3144f344ec67ffa51b96a3ca986ad3c608f7) | MIT; published 2026-09-23, Capacitor 8          | 21,145 / 96,368                    | Session/key component only. Default accessibility is not no-backup; replacement/error/readback guarantees are incomplete.   |
| [Capgo InAppBrowser 8.24.0](https://github.com/Cap-go/capacitor-inappbrowser/tree/3ad4979e77317fcd106ad4e06e945dca46deb4a2)           | MPL-2.0; published 2026-10-13, Capacitor 8 peer | 352,784 / 1,973,127                | Offers managed stores: iOS 17+ persistent isolation; older/shared modes use the default store. Clear-all excludes the host. |

SQLite's `UtilsFile.swift:40–72` sets exclusion after creating a missing root; an existing root
skips that branch. Its private exclusion getter exists at 629–634 but has no inspected callsite
or exposed JS readback. `UtilsSQLCipher.swift:380–435` issues BEGIN/COMMIT/ROLLBACK, yet no GSIP
all-store, crash/power-loss, journal/temp or rights/restore tests ran. `Database.swift:83` prints
a database path and error paths include raw SQLite text; safe I7 diagnostics remain unproved.
Its Package.swift adds SQLCipher.swift >=4.14.0 and ZIPFoundation >=0.9.0. The inspected minimum
SQLCipher.swift manifest declares a binary XCFramework. Actual resolved source/binary
correspondence, full transitive licences/notices and binary/app size remain unverified; the MIT
plugin wrapper neither proves closure nor means the binary is proprietary.

Secure Storage defaults to synchronization disabled and `whenUnlocked`; neither implies no
backup. Its declared minimum KeychainSwift 21.0.0 deletes before adding an item; that inspected
minimum is not a claim about future native resolution. Apple's generic ThisDeviceOnly classes
can restore on the original device. The passcode-set-only class is distinct and changes
availability/loss semantics. It still supplies no six-store/photo transaction or host residual
cleanup, and no persisted accessibility-class readback was proven. See
[Apple's Keychain data protection](https://support.apple.com/guide/security/secb0694df1a/web).
InAppBrowser's nonpersistent managed windows do not replace GSIP's host lifecycle or durable
queue. None of the four components implements GSIP account/rights/generation fences by itself.

Archive integrity, licences, release dates, sizes and the candidate semantics above are **manual archive review** facts. The checker binds the selected source snapshots and application files; it does not download or validate registry metadata, re-audit licences or prove those semantic findings.

## Running the offline source checker

Use an existing Python 3.11+ environment. Prepare a **dedicated directory containing only public source evidence**, with exactly the
logical `.source` filenames listed below. Copy the specified package members from their
integrity-verified archives, plus the observed generated dependency-resolution snapshot.
The checker performs no download, package installation, native build or application-data read.
Do not point it at an app container, home directory, secret store or real backup.

```sh
python -B -m scripts.ios_storage_feasibility /absolute/path/to/public-evidence
```

Exit `3` means exact known source evidence was validated **and storage feasibility stays
blocked**; it is intentionally not readiness success. Exit `2` means evidence is unverified
or invocation is unsupported. Both emit one bounded JSON object, without incoming paths,
unknown input hashes/content, arbitrary exception details or a traceback. There is no accepted
backend/device/migration result, caller capability manifest or automatic web fallback.

The checker reads exact expected bytes through directory descriptors, rejects symlinked
roots/intermediates/leaves, non-regular or multiply linked files, extra files, length/hash drift
and observed read-time mutation. Per-file and aggregate bounds are engineering safeguards,
not measured device capacity. It does not execute source or re-prove its semantics. A future
version, source/profile change or newly discovered persistence surface needs a new review;
changing a hash or adding a fake API comment never upgrades capabilities. This is a POSIX
source-review tool, with no claim of race detection after it returns or of universal filesystem
snapshot atomicity. Unknown platform capabilities fail closed.

Unit tests use explicit synthetic source bindings; they do not replace or certify the actual
public profile. The actual public profile must also be exercised separately. Its successful
validation remains a blocked source result, never a backup/storage claim.

## Exact source inputs

Public-source bytes are not vendored into GSIP. The checker binds the fixed profile below and
application files in `REPOSITORY_SOURCES`. Npm members come from the exact package tarballs;
ION members come from the exact revisions above. A registry metadata snapshot is not treated
as a new native lock. The observed-resolution snapshot contains only public dependency pins
and is not a repository-tracked lock or proof of every CI run.

[Portable source catalog](ios-storage-feasibility-sources.json) records exact package archives, members, SHA-512 integrity/SHA-256 source hashes and raw commit URLs. It contains no local absolute paths. Copy the supplied [observed snapshot](ios-storage-observed-resolution.json) as `observed-native-resolution.source`; it records one prior generated resolution, not a dependency lock. Repository formatting normalized JSON whitespace only; parsed values match the original, whose byte length/hash remain in the catalog.

| Logical input file                         | Bytes  | SHA-256                                                            |
| ------------------------------------------ | ------ | ------------------------------------------------------------------ |
| `filesystem-mapping.source`                | 2112   | `b4dd96f40a57dff5b43f9b93e208b5f64ae716bcda57378ca4f44a83b713c7c0` |
| `filesystem-location-resolver.source`      | 1625   | `4c46c0a5cf88e8257ea7fd61b33ba098ec26227918c48b53e89ceff8d10fb20e` |
| `filesystem-operation-executor.source`     | 6329   | `ea8252a6d1195ffb3442c8a8ad9149acde5332d3644fcd43739b45227bc13bed` |
| `filesystem-api-types.source`              | 17469  | `2a573b6cbd506aca157950d852470114e4171da2ffc53adb52399be1fa002f7c` |
| `filesystem-plugin-registration.source`    | 327    | `5389deeff8a5762e28285d5051fac2c01c3275f4f2719a9ae22280143bb5095d` |
| `filesystem-web-fallback.source`           | 23426  | `038cfd655a54eafcc7efd6566c4ade942558d69135b4e5f01a58e5da87446685` |
| `filesystem-swift-dependency-range.source` | 1048   | `1e2799f6a21acc5707709e81de7682eff9fd3df294a80b0f1cb115f7093505f4` |
| `ion-filesystem-manager.source`            | 15865  | `0d59a711c547b26f9d16b9743142c32087b94b40ee4f530665b1b76434c1a084` |
| `capacitor-ios-webview.source`             | 16487  | `0485aee1f25b0ed028ce944fb98306e6a92330038ce7fd923aa87b4ada4bbfec` |
| `capacitor-ios-cookie-manager.source`      | 4758   | `57f0163dcf2e446a5d17fb96919b369479b1202f41bd77fa0f5f357e261f3def` |
| `capacitor-ios-keyvalue-store.source`      | 11015  | `b500084f5bb35df5a74ead375c57cf48186d8adf91091760c4d07276d4fdbbd4` |
| `supabase-client-storage.source`           | 26052  | `eb923579957052a1160cda34a65ff67496d46abf37ae022cdd331f8d6d8bd800` |
| `auth-client-storage.source`               | 257301 | `7552500e375665e28acf23fb552ccbf1ef11379afab15859b2f670f1ae9aee9f` |
| `auth-pkce-helpers.source`                 | 23030  | `82025113a07125f319380ec5a510e58544a04f6e3bcf82c6eb8ce3a2cc6b07c5` |
| `camera-plugin.source`                     | 30250  | `995102b7abf1138e5ca9e13d3ffb93a85d244994d734c1d5443f0fb428faeba8` |
| `ion-camera-temporary-paths.source`        | 2770   | `4026b77b0196e9843c22648f5d0f12defc07c43826a2ad5b8e7725bff7f84dee` |
| `ion-camera-flow.source`                   | 18686  | `5444e8519b40b9798f643ad5043322ec77ec6ce05a9f9f2c6ad9edfcee95d729` |
| `notifications-native.source`              | 36659  | `d923157a6e8522dab046c43b773b4a2b149d19ff98902e9caf40778e83a7d2d4` |
| `observed-native-resolution.source`        | 1233   | `03c73f532a75e0228889472ed648d4ed36a68f05566922ecfb05abef16b18b3f` |

## Next concrete capability study

Keep APP-2C2 and iOS release readiness held. A useful next study is an exact upstream interface
for an app-host lifecycle plus excluded transactional backend: root exclusion/readback before
private bytes; lifecycle/replacement checks; safe atomic transactions/journals; generic errors;
and supported legacy WebKit/native-cookie cleanup while preserving ownership/rights/restored
generation holds. SQLite is a component to investigate, not a selected solution. No candidate
currently merits a backend decision or a native-language exception request.

Custom native code would require a separate concrete specification and Justin's explicit
language exception before implementation. Device/accounts/signing, physical backup/restore,
notifications, legal/store, photo calibration/publication, production and capture gates remain
separate. Old provider-held backups cannot be retroactively retracted by this work.

**Assumptions:** approved no-cloud policy and TypeScript/Python-only guard remain binding;
current source describes capability limits rather than observed leakage or physical erasure;
publication dates/available public repositories are maintenance signals only; package archive
sizes are not measured native/app growth. No new dependency, service or licence is selected.
