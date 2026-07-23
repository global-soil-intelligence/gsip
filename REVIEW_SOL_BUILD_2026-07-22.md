# GSIP v2 — Adversarial Review of Sol's Full Build (WP-0 → WP-6)

**Reviewer:** Claude (Cowork), four fresh-context adversarial review agents + independent verification of top findings
**Date:** 2026-07-22 · **Baseline:** docs/SPEC.md v2.2 + docs/BUILD_ORDER.md v2.2 · **Tree reviewed:** `origin/wp-6-public-export` (bbc2459) and each stacked WP diff
**Suites re-run locally:** 13 pytest ✅ · 16 vitest ✅ (pgTap + Playwright not re-run here; analyzed statically)

## Verdict summary

| WP | Scope | Verdict |
|---|---|---|
| WP-0 | Repo bootstrap, CI, licenses | ✅ MERGE_WITH_NITS |
| WP-1 | Schema + RLS + grants | 🚫 BLOCKED (1 HIGH) |
| WP-2 | Reference card | ✅ MERGE_WITH_NITS (1 HIGH nit) |
| WP-3 | Capture PWA | 🚫 BLOCKED (1 BLOCKER + 2 HIGH) |
| WP-4 | Prior-attach worker | 🚫 BLOCKED (1 HIGH, small fix) |
| WP-4b | Photo QA / sanitization | 🚫 BLOCKED (1 BLOCKER + 2 HIGH) |
| WP-5 | Public map | ✅ MERGE_WITH_NITS (pre-launch fixes) |
| WP-6 | Nightly export | ✅ MERGE_WITH_NITS (1 HIGH pre-launch) |

**Headline:** the architecture is sound — RLS, grant immutability, fail-closed export ordering, and unit conversions all survived adversarial probing. But as shipped, **the product cannot accept a single real submission** (B1), and **one metadata channel pierces both sanitization and the public-export scan end-to-end** (B2). Both are small fixes; both were masked by test suites that are green but never exercise the failing path.

---

## BLOCKERS (independently verified by me, not just the review agents)

### B1 — Every hosted submission fails with `permission denied` (WP-3 × WP-1)
`apps/capture-pwa/src/supabase.ts:116` inserts an explicit `id: record.submissionId`, but the column-level INSERT grant on `public.submissions` (`20260722181500_wp1_v22_privacy_and_grants.sql:198-201`, extended only by `gps_accuracy_m` in `20260722193000`) does **not** include `id`. Postgres rejects any INSERT whose column list contains an ungranted column → 42501 on every submission from the hosted PWA.
**Consequence:** the grant row inserts first (orphan immutable grant per attempt), the submission insert throws, the queue record is retained and retried forever — precise GPS + raw photos sit in IndexedDB indefinitely, user sees "Sync paused" forever.
**Why tests are green:** pgTap inserts submissions as superuser before switching role; no Vitest/Playwright test ever calls `submitQueued` (the e2e "airplane-mode" test exercises the null-client preview branch because `VITE_SUPABASE_URL` is unset in CI).
**Fix:** migration adding `id` to the submissions INSERT grant (safe — existing WITH CHECK policy still pins `contributor_id` and `status='pending'`), plus an authenticated-role pgTap test mirroring the real client payload, plus a Vitest suite that drives `submitQueued` against a mocked PostgREST.

### B2 — JPEG COM comment survives sanitization and the export scan into the public dataset (WP-4b × WP-6)
`pipeline/qa.py:76` re-encodes with `clean.save(..., format="JPEG", quality=92, optimize=True)` — Pillow ≥9.4 **preserves `info["comment"]` by default**, and `has_embedded_metadata` checks only `exif|xmp|xml` info keys + XMP byte signatures.
**Reproduced on this container (Pillow 12.2.0):** JPEG with COM `GPS 40.446 -79.982 serial=ABC` → sanitize → comment intact, scan returns clean. `pipeline/export.py:162-164` reuses the same two functions, so free-text metadata (camera apps and watermark tools write GPS, owner names, serials into COM) flows through ingest *and* the "fails loudly" export gate into the public HF dataset. Direct I7 violation.
**Fix:** pass `comment=b""` on save (or `del clean.info["comment"]`), add `comment` to the scan key set + raw COM-marker byte scan, and add an adversarial fixture (COM + XMP + ICC + SubIFD) to `tests/test_qa.py`.

---

## HIGH findings

**H1 (WP-1) — H3 indices are entirely client-asserted.** CHECKs are regex-only (`^88[0-9a-f]{13}$`); nothing server-side re-derives `h3_r8/r6` from `geom_precise` (only derivation in the tree is client-side, `apps/capture-pwa/src/geo.ts`). A malicious contributor can georeference their submission to any cell on Earth — undetectable public-dataset poisoning (I8), priors attached to the wrong place (I3). Fix: h3-pg trigger deriving cells server-side, or a QA-gate geom↔cell containment check. *(This is the same class of hole as my v2.1 review's H3-resolution finding — Sol's regex pins resolution but not validity/consistency.)*

**H2 (WP-4) — SSURGO nulls averaged as zeros.** `packages/schema/src/prior.ts:175`: `Number(null) === 0` passes `Number.isFinite` and enters the weighted mean with full weight — bulk density priors dragged toward 0 wherever horizons have missing values (common). Silently poisons the highest-resolution US prior layer. Fix: skip null/empty before coercion + null-bearing fixture row.

**H3 (WP-4b) — Quarantine cleanup can never delete anything.** `qa_worker.py:158-176` lists `incoming-photos` non-recursively with `prefix:""` — gets only top-level uid folder placeholders (`created_at: null`) → `fromisoformat("None")` ValueError; real 4-level-deep objects never enumerated. GPS-bearing raw uploads persist indefinitely; every 5-min run exits nonzero once any folder exists. Fix: recursive walk or query `storage.objects` via PostgREST.

**H4 (WP-4b) — Crafted image wedges the QA queue.** `qa_worker.py:144` catch tuple misses `UnidentifiedImageError` (OSError subclass), `DecompressionBombError`, `cv2.error`. Non-JPEG bytes or a 65k×65k bomb (<12 MiB) → job stuck in `processing` forever, remaining queue skipped that cycle, quarantine object retained. Promotion stays correctly closed, but queue + quarantine guarantees break. Fix: broaden catch + stale-`processing` requeue.

**H5 (WP-3) — No sync on app startup.** `App.tsx:115-121` syncs only on the `online` event or a new submission. Capture offline in the field → reopen at home already online → never syncs. Fix: `void sync()` on mount + background retry.

**H6 (WP-3) — Acceptance-critical paths have zero test coverage.** `submitQueued` (grants, insert, upload, ordering, retry idempotency) untested; the airplane-mode e2e passes via the preview-mode branch. This is what masked B1.

**H7 (WP-6 + WP-5) — Silent 1000-row truncation.** `export.py:223-227` and `mapData.ts:106-109` issue single unpaginated requests; PostgREST caps at `db-max-rows` (1000) **without error**, service role included. Submission #1001 → nightly export silently incomplete; map undercounts. Fix: paginate via Range headers or assert Content-Range total.

**H8 (WP-2) — Card validation acceptance test is circular.** Fixtures re-render from the same design constants with a linear lighting model the validator inverts by construction, ~7° max skew vs required ≤30°, tolerance tuned so exactly 9/10 pass. Real-print robustness untested. Fix: real photographed fixtures or nonlinear tone curves + true 20-30° homographies.

## MEDIUM (fix before or at merge)

- **WP-1:** `grant select, insert on public.photos to authenticated` is table-level — clients can self-grade QA columns (`card_detected`, `sharpness_score`) and will auto-cover future columns (`perceptual_hash` spoofing defeats dup detection). Narrow to `(submission_id, shot_type, storage_path)`.
- **WP-1:** `public_submissions` is invisible to `authenticated` role (anon-only qa_pass policy) — every anonymously signed-in contributor gets 0 public rows from the view. Latent (map queries as anon today); document or scope via definer-owned view.
- **WP-5:** anon REST surface exposes per-submission `captured_at` timestamps + precise-point-derived `elevation` — a terrain side-channel that partially defeats H3-r8 fuzzing in steep terrain, and count-1 cells have no k-anonymity floor. The export already treats both as private; make the live surface match (aggregate `h3_cells` or date-truncate + drop elevation).
- **WP-6:** HF `upload_folder` without `delete_patterns` — a taken-down photo stays downloadable at repo HEAD forever while vanishing from the parquet index. Takedown path required pre-launch (I6/legal).
- **WP-3:** `accept="image/jpeg,image/*"` vs jpeg-only bucket allowlist → gallery-picked WebP/HEIC = permanently failing queue record, no dead-letter (compounds with no attempt cap). Transcode to JPEG client-side (bonus: strips EXIF at source).
- **WP-3:** `device_model` never collected — NULL forever, not backfillable, degrades Phase 2 conditioning.
- **WP-4:** `prior_jobs` has no durable consumer (client best-effort invoke, result unchecked; dead_letter never retried) — acceptance "priors within 60s" holds only on the happy path. Add a scheduled drain like photo-qa.yml.
- **WP-4:** `Promise.all` couples the three sources — one SoilGrids null dead-letters elevation+SSURGO too. Decouple per-source.
- **WP-4b:** dup-hash check fetches all hashes unpaginated (silently degrades past ~1000 photos) and compares against sibling shots of the same submission (self-flagging risk).

## LOW (selected)

WP-0: e2e suite never wired into CI; pages.yml workflow-level `pages:write`/`id-token:write` should be deploy-job-scoped; `.env.example` drifts from BUILD_ORDER §6 undeclared. WP-1: `camera_metadata_private` CHECK pins keys not value types; `precise_location_optin` column is spec-undocumented and dangling; RLS tests lack write-path negatives; public `elevation` (see WP-5 medium). WP-2: `pypdf` in runtime deps; neutral-gray patch check vacuous. WP-3: `check-language.mjs` breaks on subdirectories (Dirent basename bug); no dead-letter UI. WP-4: `attempts` hardcoded to 1; unguarded `request.json()`. WP-4b: `model_version` never written to qa_events. WP-6: zero-qualifying-rows raises → red nightly until first real contribution (alarm fatigue); dataset card YAML `license: odbl` covers CC BY-SA photos too; `refresh_h3_cells` never zeroes dropped cells and runs before push; full `captured_at` exported (date-truncate costs nothing). WP-5: budget check measures bundle not tiles; hardcoded `seedCells` render as real data on any fetch error; synthetic seeds will render on the hosted map (export excludes them — pick one story).

## What held up under attack (auditable passes)

- **RLS core (I7):** anon/public-key cannot reach `geom_precise`, `camera_metadata_private`, or either bucket; A cannot read B; no self-approve path (no UPDATE grants on submissions; insert WITH CHECK forces `status='pending'`); view is security_invoker + barrier; column grants verified by pgTap (21 planned assertions).
- **Grant immutability (I6):** BEFORE UPDATE/DELETE trigger raises unconditionally; composite FK `(grant_id, contributor_id)` makes cross-contributor grant spoofing impossible; export verifies per-photo via `grant_id` snapshot (attribution from grant, not live row); photos without grants abort the export.
- **Export fail-closed ordering:** download → re-sanitize → re-scan **before** anything written; single atomic `upload_folder` commit; exceptions nuke the `.building` dir and fail the workflow. No partial-publish window.
- **Unit conversions all correct** (checked factor-by-factor against ISRIC/SSURGO docs): bdod ×0.01, cec ×0.1, nitrogen ×0.01, phh2o ×0.1, soc ×0.1, texture ×1; mapping table typed, single-source, in packages/schema; canonical-unit + depth CHECKs enforced in the DB, not convention.
- **WP-2 determinism:** regenerated PDFs byte-identical to committed artifacts (`invariant=1`); A6 geometry and mm→pt exact; ArUco ID/size consistent across generator/spec/validator.
- **Capture privacy:** precise coords flow only into the submissions insert; upload path matches spec exactly (`{uid}/{submission_id}/{shot_type}/{object_id}.jpg`); Anonymous Sign-Ins per spec; no analytics/log/cache sinks; minimap is static SVG of the r8 cell.
- **Workflows:** no `pull_request_target`; fork PRs see no secrets; photo-qa/nightly-export schedule+dispatch only, minimal permissions, concurrency-guarded.

## Recommended merge sequence

1. **WP-0** merge now (nits as fast-follow).
2. **WP-1** after H1 (server-side H3) + photos-grant narrowing — both are migration-only.
3. **WP-2** merge; replace fixtures in a fast-follow (H8).
4. **WP-3** after B1 + H5 + real `submitQueued` tests (H6); mime fix strongly recommended same PR.
5. **WP-4** after H2 (two-line fix + fixture).
6. **WP-4b** after B2 + H3 + H4.
7. **WP-5/WP-6** after H7 pagination; WP-5's anon-surface narrowing and WP-6's `delete_patterns` are pre-public-launch gates rather than merge blockers.

All four fresh-context agents also logged what they checked that passed, so the passes above are auditable, not silence.
