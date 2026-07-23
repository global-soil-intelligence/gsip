## Problem and resulting behavior

WP-COLLECT-4A, following owner-approved design #89. Closes #90.

A late picker/declaration callback could restore discarded draft state or report a refused save as ready. A future RAM-only guide also needs a queue transaction that cannot overwrite another tab's draft or mint a new observation after uncertain completion. This package adds the pure guide-session contract and atomic handoff, then corrects the declared shared-writer fences. It adds no preview or camera access; COLLECT-4B waits for reviewed, green and merged 4A.

The guide contract keeps photo selection private in RAM, supports photos first and optional sample details afterward, and freezes one detached retry identity. Queueing reconciles an existing immutable identity first while preserving sync progress; a new insertion requires empty persisted photo slots and exact owned optional library context, then atomically consumes that context and advances the existing revision. Older draft writes refuse visibly, while fresh successor-revision writes survive. No blanket draft cleanup follows this helper.

Existing photo/library UI writers retain their original intent/revision, await successful persistence before claiming ready, and hold ambiguous legacy context for explicit discard/restart. Late initial restores, declaration reads, account changes, pending namespace creation and ordinary/native submits are fenced. Removing sample context preserves persisted photo bytes but clears their old RAM selection and explicitly asks the person to choose again.

## Invariants and acceptance

- [x] Preserve I1–I15, L1–L7 and B1–B8. I5 language, I7 private bytes/metadata, I9 personal acceptance, I10/I11 unchanged provenance and I12 public-agent boundaries remain binding. No scientific/calibration claim.
- [x] Required A+B/optional C, explicit optional sample opt-in, real depth and strict declaration bytes retained. Camera observation intent and canonical library submission ID are distinct; the first pending snapshot fixes IDs/context/bytes.
- [x] Pure session owner/auth/revision/shot/request fences, lease holds, explicit fresh resume, pending resource reservations and defensive copies. No camera, timer, auth, network or storage side effect in this module.
- [x] Four existing stores only; no IndexedDB version/store/backend/QueueRecord/grant-format change. Same-identity reconciliation precedes consumed-draft/original-revision checks; no mutable sync progress overwrite or repeat consume/revision advance.
- [x] Empty-photo transaction, exact library consume, raw byte type/size/strict parsing, both write orders, rights-clear ordering and abort rollback tested. Lost callback authority also aborts namespace creation without replacing another namespace.
- [x] Observable refusal reaches existing UI; no missing-revision rebinding, ghost-ready selection or obsolete declaration/restore resurrection. No permission, dependency, licence, native SDK/config or activation change.
- [x] Failure-before evidence, local regressions and independent cross-review completed. Fresh exact committed-head review/CI will be recorded below after completion.
- [ ] Justin's merge go for this concrete source package. Live preview, page-wide media ownership/pixel proof, physical-phone qualification and every production/activation gate remain separate.

## Assumptions and limits

1. Justin's “go” following #89 approves its recommended first-version design and the source-build sequence. #89 was merged; this PR remains for owner review. It does not authorize another merge, Pages, production, camera/device use, capture or library opening.
2. App supplies verified current same-owner/auth/rights/admission facts. Pure access and transaction predicates never authenticate a person or confer server permission; the server still owns invitation, rights, quota, provenance and publication gates.
3. The pure object's retained-byte limit covers its owned references. Callers own defensive copies; 4B must budget/release those and enforce one page-wide unresolved request/encoder across session replacement. These tests prove no whole-process memory bound, pixel exclusion or phone quality.
4. Legacy missing/stale draft revisions hold for explicit restart. Removing library context advances the existing global revision, so old RAM photos require fresh selection; persisted photo bytes remain untouched. No ownership of an unowned draft is inferred.
5. The iOS design's existing complete-operation catalog now records the new browser-only queue export. It explicitly grants no native opcode or native implementation scope. No native source changed.

## Verification

- Frozen installs unchanged: `pnpm install --frozen-lockfile`, `uv sync --frozen --all-groups`.
- Local: `pnpm lint`, `pnpm typecheck`, `pnpm test` **811 passed** (capture 444, schema 310, site 41, map 16).
- Local: default `pnpm build` and capture `build:app` passed with both activation flags false; map/site budgets passed. Generated default Pages and capture manifests read back false/false.
- Local: `pnpm exec playwright test --project=desktop-chrome` **16 passed**, using the existing temporary synthetic loopback fixture; no actual media device.
- Local: Ruff, mypy and **129 focused Python tests passed**, including unchanged prospective camera/native-scope/backup/spec guards.
- Failure-before receipts cover missing session behavior; transaction/writer failures; malformed/oversized declaration bytes; namespace cancellation; background retry/privacy cleanup; photos-first context binding; late UI reads/refused saves; and the restart-control readiness race. No timeout, detection rule or check was weakened.
- Full GDAL/PostGIS/pgTAP/migration/Deno checks and Android/iOS artifacts rely on this PR's CI. Native web-asset build success is not an APK, simulator, backup or device qualification claim.

## Changes after review

- Separated camera/request invalidation from per-queue-attempt authority, so a fresh same-context resume can retry the same frozen identity while pre-background callbacks stay stale. Expired pending reads hold; obsolete library payloads are released.
- Added explicit completed-context binding before freeze. People can take photos before opting in or filling depth, without changing camera intent or any already-pending canonical identity.
- Guarded all legacy/native queue writes after awaited owner lookup, plus namespace creation after every await, to prevent discarded work from returning through the old paths.
- Keyed declaration UI by draft identity so an unresolved obsolete file read cannot lock a fresh draft or release its pending indicator.
- Made successful sample removal's fresh-selection requirement explicit; retained persisted bytes. Failed removal remains held and visible for another discard attempt.
- The complete-operation iOS catalog guard caught the new export; documented its browser-only transaction and retained the native hold without editing the guard.
- A full-suite restart test clicked before a deferred clear enabled the controls. Reproduced it, then awaited real user readiness; no timeout increase or behavior assertion removed.

Agent-authored code/tests/docs: Codex. Justin Hart is the human of record. No human DCO certification or approving review is supplied by the agent. No production changes; Pages run 38992492384 from #89 is cancelled, and collection remains closed.

### Changes after review — exact head 9b53315

- CI run [38993810652](https://github.com/global-soil-intelligence/gsip/actions/runs/38993810652) hit the existing five-second timeout in the oversized synthetic declaration test (443/444 capture tests passed). Isolated measurement located the cost in the generic deep-equality matcher: approximately 1.8 seconds locally, versus about 1 ms for the runtime refusal.
- Commit `9b5331569602db7f2a54b0748e03325f591ffa9d` compares every saved context field, intrinsic typed-array kind, exact length and every byte directly. The complete 2,000,001-byte fixture and tail remain checked. No runtime guard, size cap, timeout, assertion, workflow or suppression changed.
- Full local lint, type checking and all **811 tests passed** again. Independent review confirmed this exact committed head, clean worktree and **no outstanding findings**; its focused queue rerun passed **42/42**. Fresh CI/native builds are pending at this head; no green claim is made yet.

### Final verification — head 9b53315 (2026-10-17 UTC)

The earlier pending record is now superseded by terminal results for `9b5331569602db7f2a54b0748e03325f591ffa9d`. PR remains **open**, mergeable and CLEAN. Owner merge approval remains unchecked above.

- [x] [CI 38994200164](https://github.com/global-soil-intelligence/gsip/actions/runs/38994200164) **success**: lint, types, **811 unit tests**, **16 desktop browser tests**, **4 invited phone-browser engine tests**, Ruff, mypy, **2203 Python tests passed / 31 skipped / 37 warnings**, Deno, migration-on-existing-synthetic-data regression (**61/61 across 4 files** plus the existing concurrency scripts), and disposable local pgTAP (**632 assertions in 12 files; PASS**). No production database was targeted.
- [x] [App build 38994200223](https://github.com/global-soil-intelligence/gsip/actions/runs/38994200223) **success** for Android and iOS, including unchanged permission/closed-SDK/backup/version checks, repeated builds and pinned-parent comparisons.
- [x] Artifacts exist: [Android debug APK and evidence](https://github.com/global-soil-intelligence/gsip/actions/runs/38994200223/artifacts/12086990876), [iOS simulator app and evidence](https://github.com/global-soil-intelligence/gsip/actions/runs/38994200223/artifacts/12086123011). Downloaded both; actual payload SHA-256 matches each build receipt. Both embedded activation manifests read `capture_live=false`, `library_intake_live=false`. Artifact retention expires 2026-10-31.
- [x] GitHub tested merge `8088673afb4719290385d96c29850629294ad690` has the same tree (`ebad8683407010e1a7d24e2d07415061fbd67ce6`) as the independently reviewed PR head. Both repeat builds have equal entry contents; Android's complete APK is byte equal, while the complete iOS ZIP containers differ. No universal reproducibility or physical-device qualification is claimed.
- [x] Both full-history secret scans passed: [PR scan](https://github.com/global-soil-intelligence/gsip/actions/runs/38994200421), [branch scan](https://github.com/global-soil-intelligence/gsip/actions/runs/38994197053). No suppression was added. DCO is **skipped** by the existing internal policy; no agent supplied human certification or approving review.
- [x] Exact-head independent technical review: **no outstanding findings**. The test-only CI correction above retained every-byte preservation and the original timeout.
- [x] Pages approval protection retained (`jdhart81` sole reviewer, administrator bypass disabled); #89's automatic Pages run stays cancelled. Live public capture manifest remains false/false. No Pages, production, real camera/device or collection-opening action occurred.

Next: Justin's review/merge go for this concrete 4A package. The approved design requires reviewed, green and merged 4A before COLLECT-4B's preview/controller/UI work. No additional dependency, licence or production decision is needed for this PR.

