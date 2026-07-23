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

