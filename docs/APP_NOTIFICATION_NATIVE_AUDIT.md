# APP-2B native dependency and size evidence

The app reminder behavior is described in [APP_SYNC_REMINDERS.md](APP_SYNC_REMINDERS.md).
This document describes evidence produced by `app-build.yml`; it is not a claim that
CI or a device test has run. The existing permission, closed-SDK, backup, closed
activation, version and repeated-build checks remain required.

## Scope and inputs

The native workflow builds the current checkout and the exact pre-reminder source
`d7ed716ed0921381da04f542e90902ede36cb462` in a separate checkout under the runner's
temporary directory. Candidate and parent frozen installs explicitly copy package files,
so audit inputs are single-link files rather than pnpm store hardlinks. The parent is fetched by its full commit, read back and built
with its own frozen lockfile, generated projects and policy scripts. It never modifies
the candidate working tree. Both builds use the same job, Node/pnpm/Python/Java/Gradle/
Android SDK or Xcode, workflow run number, public configuration and false capture and
library-intake flags. Android uses the same disposable debug key; only its digest is
recorded. No owner-controlled signing input is read or created.

Both parent and candidate are actually built twice. Their existing build receipts
retain artifact hashes, input lock hashes, exact toolchain outputs, source identity,
source-clean results and repeat comparisons. The audit runs after those receipts;
new output remains outside the source checkout. The comparison receives both actual
first-build reference artifacts, validates their hashes, and recomputes each repeat
comparison against the corresponding current artifact. Both references are included
in the uploaded evidence. A failed or unavailable build,
unclean source, changed signing key/toolchain/build number, wrong source identity,
changed artifact or open activation receipt refuses the feature comparison.

**Assumption:** this fixed parent is the baseline for APP-2B as a whole. Later workflow
runs still measure changes from that same source and must describe their broader scope
if additional app changes have landed. The fixed source is not an unrelated earlier
artifact: CI rebuilds it under the candidate's current job inputs.

## Android runtime evidence

`python -m scripts.app_notification_audit android` retains separate exact
`debugRuntimeClasspath` and `releaseRuntimeClasspath` dependency trees, their digests
and a JSON view of selected resolved modules, original external JAR/AAR inputs and
compiled project runtime-classpath JARs. Project classpath JARs are not described as
all intermediate resource, manifest or native-library inputs: full installed npm-source
manifests and the complete APK/permission/native-entry/repeat proofs remain separate
and required. The existing
`check-dependencies` checks continue on both configurations. Closed SDK coordinates,
missing graphs, unknown projects, malformed or ambiguous metadata, unsafe files and
unknown licenses fail the additional audit as well. Traversal components are rejected
before canonical containment checks. File opens use `O_NOFOLLOW | O_NONBLOCK`, then
validate the opened descriptor as a bounded single-link regular file. A FIFO with no
writer is promptly refused, including an input replaced between containment and open;
regular-file reads retain their existing behavior. A path-only preflight cannot replace
these descriptor checks. Runtime binaries remain inside their exact
module/version cache directory or known generated project output; the temporary task
emits canonical paths for pnpm package links.

A small temporary Gradle inspection task, emitted by the Python helper, reads resolved
configurations and artifact paths. Its exact digest is recorded. It has no shell,
network, environment, credential or service logic. This is generated build-tool
configuration, consistent with the existing Python-applied Gradle versions, not new
maintained or shipped Java/Kotlin/Groovy app code.

Each resolved public module records its coordinate, actual binary digest/size and
coordinate-matched POM digest/size, declared license and license URL. A missing child
license requires explicit bounded parent-POM inheritance; duplicate identity, parent,
license-container, name or URL fields are refused rather than taking the first match; unknown/absent/ambiguous
licenses refuse the audit. POM metadata comes from the exact resolved Gradle cache or
only the public Google Maven/Maven Central paths for that coordinate. A repository
host does not approve a closed Google SDK. Embedded license/notice files are recorded
when present; their absence is reported by an empty list, never invented content.
These are declared licensing/provenance facts about exact resolved inputs, not an
attestation that a checksum proves the upstream compiler's source-to-binary build.

Local Capacitor/plugin projects are tied to their installed npm source manifests and
MIT license hashes. Generated build/cache files are excluded from those source
manifests. Unexpected prebundled JAR/AAR/native-framework inputs are refused instead
of inheriting a wrapper's MIT label. The empty generated Cordova compatibility project
must contain no third-party plugin source or binary. The installed geolocation package
can appear in npm inspection; its Android project remains excluded from the runtime.

The generated Cordova tree is scanned rather than excluding its build directory. Its
only permitted JAR roles are the exact debug/release AGP runtime-classes and resource-R
output paths. Runtime-classes JARs must be canonical 22-byte empty ZIPs. Resource JARs
must have exactly one fixed `capacitor/cordova/android/plugins/R.class` entry, with no
extra members, ZIP comments, extra fields or hidden prefix/trailing payload. Its exact
150-byte Java 8 class has no fields, interfaces, additional constants or attributes;
its sole private constructor calls `Object.<init>` and returns. Changed constructors,
classes, namespaces, source/libs archives, any AAR or standalone `.so` library
(case-insensitive, anywhere in the tree), Java/Kotlin source, unknown JAR
producer paths, unsafe links, nonregular files and oversized inputs are refused.
Unreadable root or child directories refuse the audit rather than being skipped;
the scan is bounded to 30,000 entries.

**Assumption:** this empty generated R stub is the deterministic output of the pinned
AGP 8.13.0 `BytecodeRClassWriterKt.generateOuterRClass` implementation for an empty
resource set and the Capacitor CLI 8.5.2 template namespace. The reviewed builder class
digest is `650dd0508723e0eb6be807f756bfc4f1dbe63c9f154b0b3ed4cc25da2b9c8ac6`;
the template archive digest is
`c9fa746751c74e786878e40b073fd3854c772b26716663cabbd8ebb874e39ba9`.
The expected class is constructed from that exact structure, not approved merely by
its filename or supplied hash. These are primary implementation provenance facts,
not a supported AGP generator API dependency. A changed generator, template or output
shape requires review. This exception identifies the project's own empty generated
outputs; it grants no licence approval to any third-party binary and changes none of
the separate component, POM, source-manifest, descriptor, whole-APK or repeat checks.

Build-only `:app:buildEnvironment` is retained separately and hashed. It describes
Gradle/AGP/Kotlin tooling, not shipped runtime code. The resolved runtime audit does not
claim a complete license audit of every test/compiler/SDK artifact.

## iOS selection and license evidence

The current workflow selects Swift Package Manager. Its application graph selects
Capacitor SwiftPM 8.5.2, IONCameraLib 2.0.0, IONFilesystemLib 1.1.4 and
IONGeolocationLib 2.1.1. All four identities, official repositories, exact versions and
checkout HEAD/tag revisions are required. Unknown, missing or changed selections
refuse the audit. Capacitor's complete checkout, manifest and source archive are bound
to the independently retrieved 8.5.2 release, including revision
`0b6882e9a3288342aacf36348e5a94e4f1dd7b13`. Additional source targets, dependencies,
files or changed metadata fail even when the two expected binary declarations remain.
The comparison validates fixed published archive hashes, byte sizes and full extracted
binary trees for both Capacitor/Cordova XCFrameworks. It compares the
actual extracted framework tree with the verified archive entries. Changed checksums,
unknown pins/binary targets, unexpected Pod resolution or mismatched extracted bytes
refuse the audit. Each ION package additionally records its exact reviewed manifest,
MIT licence, compressed source archive hash/size and full unpacked source tree. The
actual checkout tree must match that reviewed tag archive, including the licence and
manifest. Source trees with extra files, symlinks or prebundled native archives fail.
A new native version or Pod path needs an explicit adapter/review;
there is no permissive fallback.

The application lockfile and two upstream ION development-project lockfiles are
inventoried separately and bound to both the build receipt and the reviewed source
archive. The latter declare SwiftLintPlugins 0.57.1 at its exact recorded revision;
it is absent from the application's selected graph. Camera's Quick/Nimble declarations
serve its upstream test target. These declarations remain visible as development/test
inputs; no tool or test binary is represented as shipped or licensed by a wrapper.
An extra resolved file or inconsistent tool pin is rejected.

The existing ION selections are source libraries, not newly added app dependencies.
Their exact public tags were verified independently on 2026-10-13. These are source
archive sizes, not application overhead:

| Selected library      | Licence source                                                              | Compressed / unpacked source bytes | Selected-tag commit date |
| --------------------- | --------------------------------------------------------------------------- | ---------------------------------: | ------------------------ |
| ION camera 2.0.0      | [MIT](https://github.com/ionic-team/ion-ios-camera/blob/2.0.0/LICENSE)      |                  273,170 / 522,080 | 2026-08-28               |
| ION filesystem 1.1.4  | [MIT](https://github.com/ionic-team/ion-ios-filesystem/blob/1.1.4/LICENSE)  |                   31,020 / 150,959 | 2026-09-08               |
| ION geolocation 2.1.1 | [MIT](https://github.com/ionic-team/ion-ios-geolocation/blob/2.1.1/LICENSE) |                    23,644 / 95,915 | 2026-03-10               |

The Capacitor distribution tag was committed and released on 2026-09-11. Its reviewed
source archive is 3,549 compressed bytes / 9,594 unpacked bytes. The published Capacitor
XCFramework archive is 6,611,661 compressed bytes / 23,980,848 unpacked bytes; Cordova is
1,842,451 / 4,838,267 bytes. These are distribution input sizes, not application impact.
The versioned upstream Capacitor MIT licence, README and Cordova Apache source header
have fixed independent hashes. Both binary archives have no separate licence/notice
entries; the evidence records that exact absence. Matching package labels or mutually
consistent but unreviewed sidecar hashes cannot substitute for these reviewed inputs.
This proves identity/provenance of published bytes, not reproducibility of their
upstream compilation.

Exact archive, manifest, licence and source-tree digests are retained by the audit.
`codeload.github.com` supplies only the reviewed public source archives during build
evidence collection; it receives no app-runtime request or contributor data.

The [official SwiftPM manifest](https://github.com/ionic-team/capacitor-swift-pm/blob/8.5.2/Package.swift)
and [host description](https://github.com/ionic-team/capacitor-swift-pm/blob/8.5.2/README.md)
identify the binary distribution. The audit verifies the npm iOS license matches the
[versioned Capacitor MIT source license](https://github.com/ionic-team/capacitor/blob/8.5.2/LICENSE).
Cordova additionally retains Apache-2.0 headers in its source; audit records the exact
installed `CDV.h` header hash separately. A package-level MIT label never licenses
unrelated binary contents. Apple SDK/system frameworks remain platform/toolchain
inputs and are not represented as open plugin dependencies. This evidence does not
prove reproducible reconstruction of upstream XCFrameworks or device behavior.

## Safe failure diagnostics

A failure reports only a fixed audit-stage label, fixed error-class label, source line
number and bounded counts. It never prints paths, coordinates, parser payloads, tool
stderr, environment values, credentials or arbitrary exception text. This diagnoses
the Android audit failure without assuming that release artifacts are its cause.
For the exact inspection command, bounded UTF-8 output is inspected in memory for
unambiguous Gradle failure signatures. Only fixed labels for an unsupported
component/artifact, missing task/configuration/runtime file, known inspection API
property, or dependency network failure can replace `BUILD_TOOL`. Unknown,
malformed, oversized or ambiguous output remains `BUILD_TOOL`; no tool output is
copied into the four-field diagnostic. These labels do not establish a repair or
provide native acceptance evidence.
The temporary inspection task now emits one fixed failure marker before rethrowing
the exact original exception. Its phase identifies debug/release configuration,
resolution, component selection, artifact selection or output. Its cause is selected
only from whitelisted public exception classes; no message, property name, method
argument, path or other payload is printed. Cause traversal is limited to 16 distinct
objects and detects cycles. Unknown, conflicting, cyclic or truncated causes report
`UNKNOWN`. The Python diagnostic accepts only one exact, bounded marker for the
exact inspection command and keeps the same four fields. All original resolution,
selection, artifact and output operations remain mandatory. The marker is diagnostic
build configuration emitted by Python, with its exact hash recorded in the audit;
it adds no shipped native application source or dependency.
If the exact inspection command fails, the CLI also reports one
`GSIP_GRADLE_CONTEXT_V1` line with eight fixed tokens: version, canonical command,
stdout state, stderr state, combined bound, task-marker state, structured framing
and public Gradle framing category. This distinguishes an absent marker from a
marker that could not be inspected because of type, UTF-8, control or size guards.
The cap remains 65,536 bytes. Unknown or ambiguous framing stays explicitly unknown
or ambiguous; no message, path, property, URL or stream fragment is copied. Commands
outside the exact inspection scope emit no supplemental line. The original
four-field diagnostic remains last and unchanged, and the CLI still fails. This
context establishes where diagnostic inspection stopped; it does not establish a
producer/API repair or native acceptance. This context adds no graph acceptance.
An independently bounded private fault channel now survives oversized captured stderr
without inspecting it or changing its 65,536-byte refusal. Python creates a fresh
private directory beside the temporary graph output. The generated task writes only
three fixed fields (`schema`, `phase`, `cause`) into an exclusively created numbered
receipt; it never overwrites an existing file. Python accepts exactly one 256-byte-or-
smaller receipt, with the exact schema and whitelisted phase/cause strings. Duplicate
keys, unknown fields, foreign names, multiple receipts, unsafe links, nonregular files
and oversized or malformed contents remain `UNKNOWN`. No raw stream is persisted.

The CLI emits only `GSIP_FIXED_FAULT_V1|VALID|<phase>|<cause>` or
`GSIP_FIXED_FAULT_V1|UNKNOWN`, tied to the exact original failed inspection command,
exception identity, nonzero exit status and inspection stage. Its lease resets at CLI
and inspection entry. A different exception, command, status or stage cannot reuse
an earlier receipt. Commands outside the exact inspection scope emit no fault line.
The existing context and four-field diagnostic remain unchanged, and the original
Gradle exception is rethrown; a receipt supplies no audit acceptance.

The existing `projectsEvaluated` callback also records `TASK_SETUP` before rethrowing
its original setup exception. Failures that prevent diagnostic registration or leave
no usable output location legitimately have no receipt and remain `UNKNOWN`. This
uses public Gradle lifecycle and Java file APIs only within Python-emitted temporary build
configuration, with its exact task hash retained by the audit. It adds no shipped
native source or dependency. Offline Gradle 8.14.3/Java 21 synthetic controls verified
byte-identical successful graphs, preserved tool/CLI failure statuses for oversized
task/setup output, and explicitly unknown early settings failures. They do not identify
the hosted Android failure's underlying cause or establish a native product build.

Both actual debug and release inputs remain required; there is no debug substitution
or check skip. If the next CI run confirms absent release project outputs, their
actual variant producers must run before inspection in a separate forward fix.

A build-level observer additionally reads the public `BuildResult.failure` after the
build finishes. Only a failed build with no earlier task/setup fault attempt can emit
`BUILD_FAILURE`. It reuses the exclusive bounded file channel and existing cause
classification; it does not rethrow, replace, suppress or alter the original build
failure. Earlier faults are never replaced or duplicated, including a failed attempt
to write a receipt. Malformed/multiple receipts and failures before registration remain
`UNKNOWN`. Successful output/status and every mandatory graph check remain unchanged.

The [public Gradle 8.14.3 callback](<https://docs.gradle.org/8.14.3/javadoc/org/gradle/api/invocation/Gradle.html#buildFinished(groovy.lang.Closure)>)
is deprecated and unsupported with configuration caching. This diagnostic adapter is
bound to the existing pinned operation with configuration caching disabled; it changes
no cache or command flag. Future toolchain/cache changes need fresh evidence. The
[BuildResult API](<https://docs.gradle.org/8.14.3/javadoc/org/gradle/BuildResult.html#getFailure()>)
reports the original failed result. Offline controls prove a producer failure before
task execution retains tool/CLI failure status and now yields fixed labels, with no
raw private strings emitted. They do not establish the hosted failure's cause.

Two additional exact public Java error types map to fixed `STACK_OVERFLOW` and
`OUT_OF_MEMORY` labels. Their installed Java 21 source/class identity and synthetic
thrown controls were verified; no stack or memory exhaustion is induced. No arbitrary
class name, exception message or property is printed. Existing 16-object depth,
identity-cycle and conflicting-label refusals remain intact; unsupported classes remain
`UNKNOWN`. These labels are diagnostic coverage and are not a claim about hosted CI.

## Runtime artifact selection and producer order

The pinned AGP 8.13.0 projects publish several secondary artifacts on each debug and
release runtime variant. An unchanged local inspection reproduced
`ArtifactSelectionException` through the pinned Gradle artifact-ambiguity describer:
asking the original configuration for an unspecified artifact type cannot choose
between those secondary artifacts. The same source operation succeeded after the
adapter below. This establishes the local mechanism; the hosted failure's identical
root cause still requires a fresh CI result.

The adapter activates only for the public `AgpVersionAttr` metadata with the reviewed
value `8.13.0`. An unknown AGP version fails; configurations without that Android
metadata retain the existing unambiguous Java path. Both original component graphs
and their consumer attributes remain intact. Each Android configuration has two
strict public artifact views:

- A module-only view adds no attributes and retains original external AAR/JAR bytes.
- A project-only view requests AGP's `android-classes-jar` artifact type, retaining the
  selected debug/release variant. The exact resolution-root identity is excluded.

There is no variant reselection, lenient resolution, debug substitution or fallback
on failure. Every selected nonroot project must be represented; a typed view can
otherwise return no matching artifact even when leniency is disabled. The existing
sidecar validator continues to require a binary for every selected non-`pom` module.
Its metadata-only exception still requires coordinate-matched, licensed primary POM
proof whose packaging is `pom`; a missing ordinary library never qualifies. Unknown
projects, paths, modules and licences remain refused.

Producer dependencies are lazy and refer to the exact module/project view file
collections for both configurations. Those are the files subsequently inspected.
Using the original configuration's default `buildDependencies` would perform the
same ambiguous selection before the task ran. The plain Java path retains its
original dependency declaration and resolved-artifact collection. The
[ArtifactView API](https://docs.gradle.org/8.14.3/javadoc/org/gradle/api/artifacts/ArtifactView.html)
and [ArtifactCollection API](https://docs.gradle.org/8.14.3/javadoc/org/gradle/api/artifacts/ArtifactCollection.html)
provide the selected artifacts and producer-aware file collections. The adapter
never transforms or substitutes the external module binaries.

The four reviewed plugin projects each declare exactly one compiled-class artifact
of type `android-classes-jar` on both actual runtime variants. AGP's class artifact is
an explicit classpath projection; separate resources, manifest and native-library
coverage remains attributed to the unchanged full-source and complete-APK proofs.
No new resource-directory evidence protocol or broader intermediate-file claim is
introduced.

Offline public Gradle 8.14.3/Java 21 controls reproduce secondary-artifact ambiguity,
retain raw external JAR/AAR identity, build different debug/release class JARs, and
exercise missing typed-project output, missing module/binary, incorrect variant,
unknown AGP metadata and removal of either producer dependency. Existing producer
transform, graph, source, licence and diagnostic controls remain required. The local
Android inspection builds plugin producers, not an application APK, and neither it
nor a diagnostic supplies native product acceptance.

The real controls are opt-in because ordinary Python validation may lack verified
Gradle/Java tools. A skip is unavailable evidence:

```sh
GSIP_TEST_GRADLE_HOME="<verified-Gradle-8.14.3-home>" \
  python -m pytest tests/test_app_notification_audit.py -k real_gradle
```

They preserve `HOME`, use fresh task-specific `GRADLE_USER_HOME` directories and local
synthetic Maven inputs, and require no SDK download, owner signing input or account.
All source, permission, backup, repeated-build and closed-activation checks remain
mandatory. Actual CI still supplies the complete Android product build, parent
comparison and published artifact evidence.

## Reading the artifacts

The existing Android and simulator artifact archives contain their original builds
and repeat receipts plus the parent build, native audit JSON, Android dependency-tree/
build-environment text and `gsip-android-feature-comparison.json` or
`gsip-ios-feature-comparison.json`.

Before comparison, complete platform-specific sidecars are validated: both runtime
views with licensed coordinate/project-bound binaries and npm sources, or the resolved
SPM selection, archive/tree checksums and license-source bindings. Source/lock hashes
and native audit artifact hashes must match the corresponding build receipt. Empty,
partial, contradictory or unknown sidecars cannot become feature evidence. Tree digests
use canonical key ordering so writing/reading JSON cannot change their meaning.

Every build receipt has the exact schema emitted by `app_build.py`, including all
platform-specific tool outputs, runner-image fields, source and lock digests, version
mapping, source-clean status and six repeat-comparison fields. Unknown fields at any
nesting level, duplicate JSON keys, nonfinite or boolean proof numbers, missing or
unbounded tool output, malformed digests and conflicting repeat entries refuse the
audit before any input receipt can be copied to output. Repeat ZIP contents and full
byte equality are recomputed from both actual artifacts. A valid repeat may contain
packaging metadata differences; the evidence reports those differences rather than
claiming byte equality. Tool outputs use bounded adapters for the selected CI tools;
a changed output format needs a reviewed adapter, and actual native CI remains pending.

A feature comparison records archive byte sizes/delta, full hashes, changed/added/
removed ZIP entries and Android DEX/resource/native-library versus other entry sizes.
The result is the **overall APP-2B feature delta**, including Kotlin, resources, UI
and packaging changes. It is not the plugin's isolated overhead. No dependency-only
control is built. Compressed npm package bytes are not an APK size measurement.
ZIP-entry equality excludes archive metadata/signing-block differences; full artifact
hashes and byte equality include them. Neither comparison establishes universal or
cross-runner reproducibility.

Only actual successful CI output supplies native builds, resolved licenses and measured
native size. Local fixture/mutation tests prove the audit's refusals, not a native build.
Android/iPhone permission, delivery, cancellation, reboot, native logging and backup
checks remain synthetic real-device gates. iOS WebKit cloud-backup exclusion, signing,
accounts and store acceptance remain blocked/unverified. No artifact or code merge
opens production, capture, photo publication or notification permission on a real phone.

## Exact existing Android POM classifications

The additional audit exposed five pre-existing runtime metadata declarations that its
name-only licence parser could not classify. The fixed pre-reminder parent already
pins camera 8.2.4 and filesystem 8.1.3; this correction changes no selected dependency,
version, scope, project licence, Gradle task, permission, closed-SDK rule or receipt
schema. The generic name-only table still refuses `License`, `BSD License`,
`New BSD License` and `Eclipse Public License 1.0` outside the reviewed context.

Both collection and offline validation require the exact coordinate, complete primary
POM digest and size, packaging, ordered licence name/URL/classification tuples and
relevant parent chain. The six contexts below cover the five selected modules and
Hamcrest's explicit parent. Changed, partial, duplicated, rebound or unreviewed
metadata refuses; the map is not a permissive licence-name fallback.

| Exact coordinate                            | Primary POM SHA-256                                                | Reviewed classification                |
| ------------------------------------------- | ------------------------------------------------------------------ | -------------------------------------- |
| `androidx.camera:camera-core:1.4.2`         | `ea820b7874afa1047d288c29d6dbb4c9795b70bf12d3e229235af4e7bd08c072` | Apache-2.0 and libyuv BSD-3-Clause     |
| `io.ionic.libs:ioncamera-android:1.0.2`     | `5c1bc27a7c7442ba6ebdb731f88f2a74ed620d7c9847a357c26389800e63a958` | MIT                                    |
| `io.ionic.libs:ionfilesystem-android:1.1.0` | `5fc8a9c96e200e19673596aba8c66e7e1bdaa217146a3c04eae75e154b844ecb` | MIT                                    |
| `junit:junit:4.13.2`                        | `569b6977ee4603c965c1c46c3058fa6e969291b0160eb6964dd092cd89eadd94` | EPL-1.0                                |
| `org.hamcrest:hamcrest-core:1.3`            | `fde386a7905173a1b103de6ab820727584b50d0e32282e2797787c20a64ffa93` | Explicit inheritance from the next row |
| `org.hamcrest:hamcrest-parent:1.3`          | `6d535f94efb663bdb682c9f27a50335394688009642ba7a9677504bc1be4129b` | BSD-3-Clause                           |

All six exact public Google Maven/Maven Central POMs matched the resolved cache
byte-for-byte during the bounded review. The source/licence facts supporting the
ambiguous declarations are separately pinned:

- Camera's declared libyuv link identifies BSD-3-Clause. The reviewed
  [libyuv licence at commit `58d817ed`](https://chromium.googlesource.com/libyuv/libyuv/+/58d817ed81e8fe8b06a58576d639cd56b19526d3/LICENSE)
  hashes to `2b2cc1180c7e6988328ad2033b04b80117419db9c4c584918bbb3cfec7e9364f`.
  The Camera POM does not identify its bundled native source revision; this is
  declared licence classification, not a source-to-binary reconstruction claim.
- ION camera's POM points to a missing `docs/LICENSE`. The actual root
  [MIT licence at immutable commit `f802e3ed`](https://github.com/ionic-team/ion-android-camera/blob/f802e3ed0cb948131e6f962fccea96a9a5c4fb23/LICENSE)
  hashes to `5eee4ddf7b28c22447e4440ab08c9344e68252ee1effc56621764268f7687c14`.
  All 29 Java/Kotlin files in the exact
  [published 1.0.2 source JAR](https://repo.maven.apache.org/maven2/io/ionic/libs/ioncamera-android/1.0.2/ioncamera-android-1.0.2-sources.jar)
  match that source snapshot byte-for-byte. No public release tag was available;
  the commit is a matched source snapshot, not an asserted publication tag.
- ION filesystem's [1.1.0 source licence](https://github.com/ionic-team/ion-android-filesystem/blob/11ef15db0c355faa917750a31758b3edd33a9cf7/LICENSE)
  hashes to `de884404585ed20280150b0768082b6004d3548aaa0d6e596d6bfa0538ab331d`.
  All 20 Java/Kotlin files in its exact
  [published source JAR](https://repo.maven.apache.org/maven2/io/ionic/libs/ionfilesystem-android/1.1.0/ionfilesystem-android-1.1.0-sources.jar)
  match the 1.1.0 tag's source tree.
- The exact JUnit binary and
  [published source JAR](https://repo.maven.apache.org/maven2/junit/junit/4.13.2/junit-4.13.2-sources.jar)
  contain identical `LICENSE-junit.txt` bytes, SHA-256
  `9648bb2891b9813970bddb68d4be8a5e6ec8280d0180a53dfb29236b579c55bb`.
  The exact [Hamcrest binary](https://repo.maven.apache.org/maven2/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar)
  contains its three-clause `LICENSE.txt`, SHA-256
  `1cde867cab5c8e842929da5391cef98b4017314822270e934e8e2eef3767c666`.

JUnit and Hamcrest are actual binary inputs to both resolved runtime configurations,
not metadata-only platforms. ION camera's exact published POM/module metadata and
[matching build source](https://github.com/ionic-team/ion-android-camera/blob/f802e3ed0cb948131e6f962fccea96a9a5c4fb23/build.gradle#L100)
explicitly declare JUnit as a runtime implementation dependency; JUnit declares
Hamcrest. The bounded source and class-file inspection found no direct JUnit/Hamcrest
references in the selected ION camera/filesystem code, but this does not establish
reflective/runtime exclusion safety or final APK removal. No exclusion is made.

EPL-1.0 classification of this exact existing JUnit context does not relicense GSIP's
MIT code or approve distribution. The [official EPL-1.0 text](https://www.eclipse.org/legal/epl/epl-v10.html)
and [Eclipse FAQ questions 16–17](https://www.eclipse.org/legal/epl/faq/)
separate source-availability information and compliance for the EPL portion. Licence
and notice preservation, source availability and the applicable distribution terms
still require review for the actual distributed product. A parser pass supplies no
legal compatibility opinion, counsel approval, store acceptance, deployment or
physical-device evidence. Existing legal, owner, production and launch gates remain
unchanged.
