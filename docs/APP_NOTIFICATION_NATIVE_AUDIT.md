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
and a JSON view of selected resolved modules and actual JAR/AAR inputs. The existing
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
its original setup exception. Settings or initialization/compilation failures before
that callback legitimately have no receipt and remain `UNKNOWN`. This uses public
Gradle lifecycle and Java file APIs only within Python-emitted temporary build
configuration, with its exact task hash retained by the audit. It adds no shipped
native source or dependency. Offline Gradle 8.14.3/Java 21 synthetic controls verified
byte-identical successful graphs, preserved tool/CLI failure statuses for oversized
task/setup output, and explicitly unknown early settings failures. They do not identify
the hosted Android failure's underlying cause or establish a native product build.

Both actual debug and release inputs remain required; there is no debug substitution
or check skip. If the next CI run confirms absent release project outputs, their
actual variant producers must run before inspection in a separate forward fix.

## Runtime artifact producer order

The inspection task declares `dependsOn` for the public `buildDependencies` of both
`debugRuntimeClasspath` and `releaseRuntimeClasspath`. Gradle schedules the selected
project artifact producers before the task reads resolved artifact files. The
[Gradle 8.14.3 configuration API](<https://docs.gradle.org/8.14.3/javadoc/org/gradle/api/artifacts/Configuration.html#getBuildDependencies()>)
provides this dependency information. The
[legacy resolved-configuration API](https://docs.gradle.org/8.14.3/javadoc/org/gradle/api/artifacts/ResolvedConfiguration.html)
does not track task dependencies in its returned file sets. Resolving those sets
inside `doLast` alone therefore does not schedule their producers.

An offline Gradle 8.14.3/Java 21 regression uses built-in Java projects and a registered
artifact transform that opens each actual jar as a ZIP. The previous task fails during
debug artifact inspection before either selected project jar exists. The declared
producers build both selected jars first and the unchanged inspection then succeeds.
Removing either variant's dependency, disabling a producer, failing a producer or
omitting a runtime configuration still fails; selecting another project never licenses
it or bypasses the source audit. This proves a task-input defect and its correction.
The hosted Android run reported `DEBUG_ARTIFACTS|UNKNOWN`, so its specific cause remains
unverified until a fresh CI run. The local fixture does not establish that cause.

The declaration adds no artifact substitution, configuration skip, application release
signing, key or account. Both selected graphs, artifact files and all existing source,
license, permission, backup, repeat and closed-activation proofs remain required. Task-
graph/setup failures may occur before the inspection callback emits a fault receipt;
those failures remain failed and explicitly unknown.

The real regression is opt-in because ordinary Python validation may lack the verified
Gradle/Java tools. A skip is reported as unavailable, never as a passing native control:

```sh
GSIP_TEST_GRADLE_HOME="<verified-Gradle-8.14.3-home>" \
  python -m pytest tests/test_app_notification_audit.py \
  -k real_gradle_runtime_producers_precede_content_transforms
```

It uses a fresh `GRADLE_USER_HOME`, offline resolution and local synthetic Maven/jar
fixtures only. Actual CI still supplies the Android product build and artifact evidence.

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
