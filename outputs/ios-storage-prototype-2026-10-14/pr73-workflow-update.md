Implements the exact APP-2C2A synthetic prototype authorized by Justin after #71. The scope is limited to its 21 Swift files, three new Python/CI support files, nine disposable template edits and 21 literal source copies. Closes #72 after owner review/merge.

The prototype preserves uncertain storage and refuses use until its native policy and lease checks pass. It is isolated from the ordinary app: no queue/auth migration, ordinary registration, production, device, signing, capture or account action. The historical scope snapshot and all 377 pre-existing tracked files remain unchanged.

### Explicit invariants and acceptance

- [x] Preserve I1–I15, L1–L7, B1–B8, existing language/dependency/permission/secret checks, and every production/launch/device gate. The direct owner exception covers only #71’s finite native scope.
- [x] Require exact complete file protection and backup exclusion with fresh uncached readback before SQLite opening/recovery and at operation boundaries. Unknown metadata, identity replacement, links, quota and schema uncertainty hold.
- [x] Fixed system-SQLite operations, DELETE journal/EXTRA synchronization readback, bounded staging/receipts, single native writer and atomic six-store-shaped clearing. No arbitrary SQL/path, statement-journal spill configuration, extension, reset or eviction.
- [x] Serial off-main pending-anchor → SQLite commit/receipt → clean-anchor → final fence → acknowledgment protocol; owner/epoch/launch/generation/revision/idempotency/exhaustion/timeout checks preserve uncertainty. No automatic account or anchor recreation.
- [x] Keychain policy requires the exact passcode-bound ThisDeviceOnly class, synchronizable false and a separately verified default group. Unknown group holds before any item query/add/update; no delete/add gap, weaker class or extra group.
- [x] Held startup, nonpersistent WebKit before first navigation, disabled automatic package registration/application-notification routing, exact native message/asset gates, cookie/prompt/alias/Cordova/navigation denial, native-only canary handles and revocation through asynchronous replies. No actual camera, location, notification or network work.
- [x] Simulator suites actually ran: **42 core + 33 host tests passed, zero skips**. Injected root/anchor/availability faults remain labelled; passing the expected Keychain hold is not a platform-Keychain pass.
- [x] Ordinary Debug and Release actual compiler/output-map/link-command/link-map/native-tree/bundle/clean-ZIP isolation passed; no filename-only assertion. Debug 44 bundle files, Release 42, each with 309 emitted source/object inputs.
- [x] 51 synthetic Python harness-policy regressions, related storage/spec suite, full lint/TypeScript/JavaScript checks, Ruff and strict mypy passed locally. Full-history redacted Gitleaks 8.21.2 reports zero findings; original four approved fingerprints/rules/workflow unchanged.
- [ ] Exact-head hosted CI and ordinary Android/iOS artifacts: pending this PR’s first run; evidence will be appended.
- [ ] Actual platform Keychain/default-group, physical passcode/lock/backup/restore/power-loss acceptance, ordinary-app adoption and later APP-2C2B/C/C3 gates remain held.

### Changes after review

- Bound every generated preimage and copy destination; refuse links, special/multiple-link inputs, traversal, source/output overlap, template drift, missing/duplicate anchors and unknown compiled/link/bundle inputs. Added adversarial regressions for each discovered acceptance bypass.
- Corrected observed Xcode scheme/plan layouts and dependency ordering without changing dependency selection or platform floor. Required exact authored test identities and zero skips; all raw native output and artifacts remain private, with only a bounded sanitized receipt uploaded.
- Independent review closed stale callbacks across clear/navigation, final async reply fencing, protected-data preflight, off-main execution, timeout/recovery revocation, exclusive writer ownership, receipt/record ABA and schema/quota holes.
- Actual simulator readback showed FileManager’s protection dictionary key absent. The public NSURL complete-protection setter plus fresh uncached URLFileProtection.complete readback returned the exact required class and exclusion true. Adopted that supported same-class metadata API; no policy relaxation. All actual SQLite and canary tests then passed.
- Fixed statement-journal risk using fixed INSERT/UPDATE OR ROLLBACK operations, preserving transaction rollback and original bounded errors. No global temp override or custom VFS.
- Joined actual Swift driver maps, source/module objects, merged outputs, audited native binaries, both ordinary configurations and exact archive bytes. Tests reject unused/forged maps, renamed unknown code, hidden link inputs, changed binaries/resolution, canary resources and substituted/special ZIP members.
- Made failed native assertions report only boolean predicates, preventing associated payload/opaque-handle echo; predicates unchanged. Trimmed one trailing blank line in a forward commit.

### Assumptions and honest limits

- The owner’s go binds #71 at e9f5bade7a54601ded41ea7eda09e9b96c2c21bc and merge ccbe716caf8406dda7ffd58ecb9cab62ea0702bf. It authorizes this prototype, not merging this PR.
- This is one app-owned synthetic process/root. In-process connection/coordinator exclusion is not a cross-process/distributed compare-and-swap or power-loss certificate. SQLite fullfsync and metadata readback are not physical durability/backup proof.
- The unsigned harness has no independently bound default Keychain access group. Its actual probe reports held-group-unverified before item calls. Injected adapters prove protocol/policy fault behavior; they do not prove platform Keychain behavior.
- Protected-data availability is explicitly injected in conformance fixtures; actual UIKit lifecycle/host gates are tested separately. Simulator metadata does not prove device encryption, passcode removal, cloud exclusion, restored-session isolation or historical backup retraction.
- The six-store canaries are not the actual TypeScript adapter. Legacy export/purge/recovery, real camera provenance, full reminder/plugin parity, physical-device evidence and account/signing inputs remain separate.
- Capacity bounds remain provisional. No streaming/performance, hardware capture, scientific accuracy, node enrollment or publication-readiness claim.
- No new package/version/service or licence: authored code MIT; system SQLite public domain; existing platform frameworks retain Apple terms. Existing npm/SPM source/binary/licence audits remain unchanged. Ordinary prototype size delta is zero because it is excluded. Synthetic harness payload measurements are build evidence, not release-app functionality.
- Local Xcode/simulator checks ran; local GDAL/PostGIS/pgTAP/Deno/Android checks are not claimed. Hosted CI supplies their disposable environments. Production was not queried or changed this turn; Pages approvals, workers and capture stay held.
- Codex authored implementation/integration/tests; independent agents reviewed source and adversarial boundaries. Justin remains human of record; no agent approval or DCO certification.


### Changes after review — workflow execution

- The independent review found that the workflow originally supplied the ordinary source checkout’s generated iOS directory to the harness, which deliberately refuses that input. The workflow now creates a separate, no-hardlink, detached checkout at the exact candidate commit, installs frozen packages by copy, and builds/generates the ordinary comparison there. The refusal remains in force.
- Moved the exact ordinary-input refusal before the directory-existence check, so clean Linux checkouts enforce the same boundary. Added absent/present-directory regressions; no admission policy was relaxed.
- A complete fresh simulator execution passed all 75 native cases and then exposed a direct-file Python entry-point import failure at the ordinary audit. The workflow now uses `python -m scripts.ios_storage_prototype`; its regression failed before the correction and passes after it. Corrected assertion wrapping in forward-only commits.
- Current policy suite: **54 tests passed**, Ruff all-files and strict mypy (82 files) passed. Independent source review found no actionable findings at the prior support head; final-head review and hosted/native execution remain pending. Native source bytes and all 377 pre-existing tracked files remain unchanged throughout these workflow corrections.
