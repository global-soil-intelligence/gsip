The current iOS queue/session use WebKit persistence; APP-2C1 in #69 found no complete supported exclusion/transaction mechanism. This specification proposes a concrete candidate: an excluded system-SQLite store, separate non-backed-up Keychain anchor, bounded typed bridge and owned nonpersistent host. It splits future prototype, integration and legacy recovery into APP-2C2A/B/C. **This PR prepares design review only: no backend is admitted, no native-language exception or implementation is authorized, and iOS protection remains blocked/unverified.**

### Explicit invariants and acceptance

- [x] Preserve I1–I15, L1–L7, B1–B8, SPEC sections1–13, every existing section15 requirement and the whole section16 contract byte-for-byte. Preserve all132 existing acceptance lines/states; six new future criteria remain unchecked. All370 other existing files/modes unchanged.
- [x] Cover all six queue stores and current exported operations, combined clears, original owner/generation/revision/auth/reminder fences, async SDK storage, camera/temp, WebKit/native residuals and generic notification cleanup.
- [x] Define exclusion before SQLite open/recovery, DELETE/EXTRA settings, scratch/journal containment, bounded staging/receipts and acknowledgment boundaries. Do not equate fulfilled promises, readbacks, source/CI, process-kill or simulator results with power-loss/backup proof.
- [x] Separate Keychain and SQLite commits; quarantine pending-old/mismatch/unknown lifecycle states and preserve bytes. No silent reset, account replacement, web fallback or local-flags rollback proof. Clean same-install offline restart remains a requirement; hosted use still checks current rights.
- [x] Keep legacy export isolated from the ordinary app/SDK; verified copy before deletion, known-schema no-create export, supported scoped purge, user-driven relaunch and honest physical residual limits.
- [x] Independent final review:93 related tests,25 baseline failures,13 unsafe document mutations rejected;374-file/mode binding and prior normative/acceptance preservation verified. Source fact reviews closed without blockers.
- [x] Exact-head hosted CI and final secret scan verified (run evidence below).

### Verification actually run

Local full lint (ESLint, language, Prettier), Ruff, strict mypy over79 source files and diff whitespace passed. Related specification/storage suite:93 passed, no failures/errors/skips. The25 new document-contract tests failed on unchanged main as expected, with zero errors/skips. They protect written design/admission boundaries; they do not execute or prove a native backend, backup transport or device lifecycle. Pinned Gitleaks8.21.2 scanned159 reported commits over non-shallow full history/all refs with redaction:zero findings; approved ignore/config hashes unchanged. No new dependency, native build/API, device experiment or real-data read ran.

### Changes after review

- The stock Capacitor controller/router cannot filter the hard-coded special-file branch. Proposed an owned controller using public delegate/bridge/asset-handler seams, with exact first-navigation and compatibility proof held; no upstream fork or working sandbox is claimed.
- Existing camera output is a temporary URI, not an opaque-handle broker. The exact supported provenance/interface seam remains a prototype stop gate.
- Legacy exporter must not create/upgrade an absent/unknown IndexedDB or boot the old app. Bound snapshot batches follow frozen writers; migration requires a user-driven full relaunch, not programmatic exit.
- Strengthened the restore-table regression after an unsafe-row mutation survived the initial global phrase checks. Pending-old and mismatch outcomes must now explicitly quarantine; clean/committed/absent rows retain their distinct conditions.
- Corrected Keychain default-access-group terminology and made counter exhaustion hold. SQLite/anchor crash durability, file exclusion, purge residuals and device behavior remain unproved.

### Owner decisions, options and recommendation

All are pending; approval/merge of this design alone grants none of them.

1. Review this candidate for a bounded synthetic prototype (recommended), or retain the iOS hold and research another mechanism.
2. Consider a narrow Swift/native-test exception for the listed coordinator/owned-host/store/bridge scope, with exact file/patch scope approved before code; otherwise keep TypeScript/Python-only and iOS held. No global guardrail changes.
3. Accept a passcode-required anchor with loss/reinstall/unknown-state holds, or require another reviewed policy/mechanism. The no-cloud policy does not already approve this availability trade-off.
4. Preserve quarantined bytes with no automatic destructive reset (recommended). Any later user-confirmed fresh-start/recovery protocol needs separate review; it may lose unsynced work/account access and require the privacy-contact route for old contributions.

### Assumptions and limitations

- Justin authorized merging #69 and preparing the next design only. No production migration/deployment, worker dispatch, Pages approval, capture/sign-in opening, signing/accounts or store submission is authorized.
- The app-owned root/default legacy store are non-shared, actual platform/native public seams can meet the full contract, and the supported OS/toolchain matrix can retain compatibility. Each is an admission test, not a proven fact. Current generated resolution is observational, not a universal native lock.
- Keychain is not a hardware monotonic counter or atomically joined to SQLite. Pending-before-commit may preserve acknowledged bytes while making them unavailable. Missing anchor/DB is not fresh-install proof; recovery/reset remains held.
- 128KiB chunks,512KiB frames and256MiB managed space are provisional prototype bounds, not measured capacity. Current list materialization requires a separately tested paged/streaming native path; no end-to-end memory/performance claim.
- No new third-party dependency/service or licence change. System SQLite core is public domain; platform terms, exact native/linked closure, maintenance and app-size delta require actual implementation receipts. No third-party encryption engine is selected. MIT/ODbL1.0/CC BY-SA4.0 boundaries remain.
- Code/source tests cannot prove physical erasure or backup transport. Old provider-held backups cannot be retracted. APP-2C3, notification-device, legal/store, photo-calibration/publication, scientific and production gates remain separate.
- Codex authored the integration/design/tests; independent agents reviewed architecture and primary-source facts. Justin remains human of record; no agent approval or DCO certification is asserted.


### Final exact-head CI and review evidence (2026-10-14)

Head `06902edf36810c55e51b169dcb813e81b22206b0`: [validate passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38651079315), [PR secret scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38651079464), [branch secret scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38651043670). DCO was skipped by the unchanged workflow; no agent certification is asserted.

Hosted CI verified2,031 Python passes/31 skips/37 warnings,12 browser passes,mypy79 source files,593 pgTAP assertions in11 files, Deno and data-preserving migration suites13/13,19/19,13/13. Lint/typecheck/JavaScript/build/map-budget and disposable database lifecycle all passed. No native/device/backup acceptance is implied; these paths do not trigger app-build artifacts.

Final independent review rejected all13 unsafe document mutations, repeated93 related tests/25 expected baseline failures, and verified374 final hashes/modes,370 unchanged files and132 unchanged prior acceptance lines. The initial unsafe restore-row mutation survivor was fixed before this commit. Manifest SHA `d87d1f26f18a2be15e28b4f82e4a9dde553fcd117866c912a94aa1d733659e10`; independent review SHA `549894ad59ece97651ea65958084eba7925eebb32af61c4cff34d6a6a2c8534f`; exact-commit closure SHA `289219a0bb6b947f40a37c34bf4cca614f407b92eb6c5c0f2b38b308f62f0709`. Conventional Commit/Codex trailer, approved parent and exactly four authorized paths verified; no Signed-off-by.

#69 is merged at `de9d1221b7c73e9be5c7e25ccaa24dcfa7903934`, with green main CI. This PR remains open/unmerged with no auto-merge. Pages remains waiting behind Justin-only approval/admin bypass disabled; all five worker schedule enable-variable names remain absent. No production project operation, native implementation/device experiment, deployment approval, worker dispatch or capture/sign-in opening occurred. Design/native-language/file scope, passcode/recovery and physical-device gates remain pending as described above.


### Owner-authorized merge and resolved policy choices (2026-10-14)

Justin explicitly approved merging #70 and preparing the exact native-code scope for review. Merged exact reviewed head `06902edf36810c55e51b169dcb813e81b22206b0` at `6a652f94b220be7eeff49508283883c502baa527`, 2026-10-14 23:13:31 UTC, without protection bypass or history rewrite. Conventional merge title and Codex co-author trailer verified; no Signed-off-by, agent approval or DCO certification.

Justin also accepted the recommended **passcode-required and preserve/quarantine/no-automatic-reset safeguards**. Those policy choices are resolved and supersede the earlier pending labels above. They authorize no current device/private-data/Keychain access. The exact native-language/file/import/API-effect scope and synthetic implementation go remain a separate review; no native code has been written or executed.

Main [CI passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38652748021) and [secret scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38652748032). [Pages remains waiting](https://github.com/global-soil-intelligence/gsip/actions/runs/38652748052), sole reviewer jdhart81/admin bypass disabled. All five worker schedule enable-variable names remain absent; the scheduled cleanup workflow was skipped, not agent-dispatched. No production project operation, deployment approval, worker dispatch, capture/sign-in opening, account/signing or device/backup action occurred. The next exact scope proposal is separate and unmerged.
