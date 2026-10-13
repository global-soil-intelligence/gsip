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
before canonical containment checks. Runtime binaries remain inside their exact
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

The current workflow selects Swift Package Manager. Audit records the actual single
`Package.resolved` pin, exact Capacitor SwiftPM 8.5.2 revision, selected package manifest,
and both official checksummed Capacitor/Cordova XCFramework archives. Read-only local
Git checks bind the resolved revision to the actual checkout HEAD and its 8.5.2 release
tag; a correctly shaped but unmatched revision is refused. It compares the
actual extracted framework tree with the verified archive entries. Changed checksums,
unknown pins/binary targets, unexpected Pod resolution or mismatched extracted bytes
refuse the audit. A new native version or Pod path needs an explicit adapter/review;
there is no permissive fallback.

The [official SwiftPM manifest](https://github.com/ionic-team/capacitor-swift-pm/blob/8.5.2/Package.swift)
and [host description](https://github.com/ionic-team/capacitor-swift-pm/blob/8.5.2/README.md)
identify the binary distribution. The audit verifies the npm iOS license matches the
[versioned Capacitor MIT source license](https://github.com/ionic-team/capacitor/blob/8.5.2/LICENSE).
Cordova additionally retains Apache-2.0 headers in its source; audit records the exact
installed `CDV.h` header hash separately. A package-level MIT label never licenses
unrelated binary contents. Apple SDK/system frameworks remain platform/toolchain
inputs and are not represented as open plugin dependencies. This evidence does not
prove reproducible reconstruction of upstream XCFrameworks or device behavior.

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
