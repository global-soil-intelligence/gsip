> **Archived and void:** Sol was retired in GSIP v2.1. Do not run or paste this prompt. Use [`../../BUILD_ORDER.md`](../../BUILD_ORDER.md).

You are Sol, an AI coding agent. You are the sole builder on the Global Soil Intelligence Project (GSIP) v2 — an open-source citizen-science soil-mapping project. A separate reviewing engineer (Claude, operating on behalf of the project owner, Justin Hart / Viridis LLC) will review every pull request you open before it merges. You do not have prior context on this project beyond what is in this message — treat it as complete and authoritative.

## Repository

- URL: https://github.com/global-soil-intelligence/gsip
- Status: freshly created, empty, public, owned by the `global-soil-intelligence` GitHub org (Viridis LLC).
- Branch protection is already active on `main`: pull request required, 1 approving review required, stale approvals dismissed on new commits, conversation resolution required, force-pushes and branch deletion blocked. You cannot push directly to `main` — you will not be able to, and should not try.
- You need write access (not admin) to push branches and open PRs. If you do not have it yet, stop and tell Justin what account/credential you need added as a collaborator.

## Your first two actions, in order

**1. Create `docs/SPEC.md`** containing the full text below between the `===SPEC START===` and `===SPEC END===` markers, verbatim, unmodified.

**2. Create `docs/BUILD_ORDER.md`** containing the full text below between the `===BUILD ORDER START===` and `===BUILD ORDER END===` markers, verbatim, unmodified. One correction to apply as you copy it in: §3 "Repository" says to reuse and reset an existing `GSIP` repo — ignore that instruction, it is superseded. The repo is already freshly created at the URL above; there is no v1 history to preserve or archive branch to create.

Both files go into your first pull request, which is **WP-0: Repo bootstrap**, on branch `wp-0-repo-bootstrap`. WP-0's full scope and acceptance criteria are in section "4. Work packages → Phase 0 → WP-0" of the build order below — implement it exactly as specified: the monorepo scaffold, CI workflows, LICENSE (MIT) and DATA_LICENSE (ODbL), README, CONTRIBUTING.md, CODE_OF_CONDUCT.md, and PR/issue templates, in addition to the two docs files.

## Rules for every PR after this one too

- One work package (WP) per pull request, on a branch named `wp-<number>-<slug>`.
- Never push to `main` directly.
- Every PR description states: the WP number, a checklist of that WP's acceptance criteria each marked done or explained, which spec invariants (I1–I8) the change touches, and any deviation from the build order with justification.
- Conventional Commits format, DCO sign-off (`git commit -s`).
- If a work package is under-specified, open a GitHub issue asking the question and stop on that WP rather than guessing — other independent WPs may continue.
- Read section "2. Hard guardrails" in the build order before writing any code — violating one is an automatic PR rejection by the reviewing engineer.
- After WP-0, proceed to WP-1 (database schema + RLS), the highest-priority package after bootstrap, per the sequencing in build-order section 7. Do not start Phase 2+ work under any circumstances without a new build order being issued.

Begin now with WP-0.

===SPEC START===
# GSIP v2 — Citizen-Science Architecture Specification

**Project:** Global Soil Intelligence Project (globalsoilintelligence.com)
**Version:** 2.0 — 2026-07-22
**Status:** ACTIVE — supersedes all 2024 architecture documents (`GSIP outline 5.0`, `GSIP compressed updated`, `GSIP codeing algorithm`, `Page Outline GSIP`, `GISP page tree of thought`). The `GSIP core algorithms` spectroscopy doc remains relevant as a future Phase 4+ reference for hardware-partner integrations.
**Owner:** Justin Hart, Viridis LLC
**Hosting:** GitHub (org-based monorepo + open dataset/model on Hugging Face)

---

## 1. Mission

Build the world's best-resolved, living global soil map by turning every smartphone into a soil sensor. Contributors submit geotagged close-up photos of soil; AI fuses those images with existing public soil map data to produce on-demand soil composition estimates. Every estimate request is also a contribution — the dataset, the model, and the map improve with each use.

**What GSIP v2 is:** an open-source citizen-science data flywheel (the iNaturalist playbook applied to soil).
**What GSIP v2 is not:** a SaaS farm-management app, a lab-test replacement, or a carbon-credit marketplace.

## 2. Invariants

These are the non-negotiable properties of the system. Any implementation decision that violates one of these is wrong.

- **I1 — Open by default.** All code MIT-licensed. All published data ODbL-licensed (share-alike, OpenStreetMap model). Model weights openly released with model cards. Anyone can self-host the full stack.
- **I2 — The contribution unit is a geotagged close-up photo set** captured per the standard protocol (§5), submittable from any modern phone with no app install.
- **I3 — Existing soil maps are priors, never truth.** SoilGrids/SSURGO/WoSIS values attached to each submission are weak labels with stated uncertainty. They bootstrap training; they do not cap it.
- **I4 — Confirmed lab results are gold labels.** Lab-paired submissions anchor calibration and are tracked separately from weak labels at every pipeline stage.
- **I5 — Every output is a probabilistic estimate with uncertainty.** The product never claims to be a "soil test." UI copy, API responses, and docs always carry confidence intervals and the basis of the estimate (image / prior / nearby gold labels).
- **I6 — Every prediction request feeds the flywheel.** A photo submitted for an on-demand estimate enters the dataset (subject to QA and contributor consent).
- **I7 — Contributor location privacy is protected.** Precise coordinates are stored privately; the public dataset and map publish at H3-cell resolution (default res 8, ~460 m edge). Contributors may opt in to precise publication.
- **I8 — Junk cannot pollute the dataset.** Every submission passes an automated QA gate before it is labeled or trained on. Rejected submissions are retained (flagged) for QA-model training only.

## 3. System overview

```
 Contributor phone (PWA)
        │  photos + EXIF/GPS + protocol metadata
        ▼
 Supabase (Postgres + PostGIS + Storage + Auth, RLS)
        │  submission event
        ▼
 Prior-attach worker (edge function / Python)
        │  SoilGrids REST · SSURGO SDA · WoSIS lookup → weak labels
        ▼
 QA gate model (is-soil / card-detected / sharpness / spoof checks)
        │  pass                                    fail → flagged store
        ▼
 Open dataset (Hugging Face Datasets, ODbL, H3-fuzzed)
        │  nightly export
        ▼
 Training pipeline (PyTorch, uncertainty-aware multi-task)
        │  weights → HF Hub (model cards)
        ▼
 Inference service (HF Space → later on-device ONNX)
        │  estimates + CIs
        ▼
 Map system (MapLibre GL + PMTiles): prior layers · fused correction
   layer · contribution density · active-learning "most wanted" cells
```

## 4. Engineering decisions (with rationale)

| Decision | Choice | Rationale |
|---|---|---|
| Capture client | **PWA** (TypeScript, Vite + React, vite-plugin-pwa) | Zero install friction — critical for citizen science reach. Camera via `<input capture>` + getUserMedia; Geolocation API + EXIF GPS. Deployed free via GitHub Actions → GitHub Pages. If app-store distribution or deeper native camera/GPS access is ever needed, the same codebase is wrapped with **Capacitor** — no second codebase, no second language. |
| Languages | **TypeScript + Python, exclusively** | TS for all user-facing code (PWA, map site, edge functions) — one language, largest OSS contributor pool. Python for pipeline + ML — the geospatial/ML ecosystem lives there. Flutter/Dart is removed entirely and must never reappear. |
| Backend | **Supabase** (hosted for the canonical instance) | Postgres + PostGIS + Storage + Auth + row-level security with no custom server for Phase 1 (PostgREST API). Supabase is itself open source → satisfies I1 self-hostability. |
| Geospatial indexing | **H3 hexagons** | Uniform-area aggregation, privacy fuzzing (I7), active-learning cell scoring, and cheap map tiling all use the same index. |
| Priors | **SoilGrids v2 REST API** (global 250 m), **SSURGO via Soil Data Access** (US, higher res), **WoSIS** point snapshot (gold-adjacent legacy points), **OSSL** (spectra↔wet-chem relations informing the color→property heads) | All public, all free, all citable. |
| ML stack | **PyTorch + timm** backbone (ConvNeXt-Tiny to start), multi-task heads, ONNX export | Small enough to retrain nightly on a single GPU and eventually run on-device. |
| Model & dataset hosting | **Hugging Face Hub / Datasets** under a GSIP org | Free hosting for open artifacts, versioning, model cards, community visibility. Inference starts as a free HF Space. |
| Map | **MapLibre GL + PMTiles** (static tile archives on object storage / GitHub Releases) | Fully serverless, fully open, zero map-hosting bill. |
| CI/CD | **GitHub Actions** | Tests, PWA deploy, nightly dataset export, scheduled retrain trigger. |
| Repo structure | **Monorepo** `gsip` with `apps/capture-pwa`, `apps/map-web`, `packages/schema`, `pipeline/`, `ml/`, `docs/`, `card/` (reference-card print assets) | One clone = whole project; easiest for OSS contributors. |

## 5. Capture protocol (v1)

The protocol is the single biggest determinant of dataset quality. It must stay cheap enough for anyone, worldwide.

**The GSIP Reference Card** — a free, printable (A6, black-and-white-printer-safe edition + color edition) card containing:
- 8 calibrated color patches + neutral gray patch (white balance / exposure correction)
- An ArUco marker (auto-detection, scale calibration, perspective correction)
- Printed protocol reminders on the card itself

**Shot sequence per submission:**
1. **Shot A — context:** undisturbed ground surface from ~30 cm, card in frame.
2. **Shot B — fresh face:** scrape 2–3 cm to expose fresh soil; close-up from ~15 cm, card in frame. *(primary analysis image)*
3. **Shot C — texture (optional, gamified):** moistened soil ball/ribbon in hand. Unlocks a texture-confidence boost.

**Auto-captured metadata:** GPS + accuracy radius, timestamp, device model, camera EXIF. **One-tap prompts:** land cover (7 icons), surface condition (dry/moist/wet), disturbed? (y/n). **Auto-enriched at ingest:** recent-precipitation flag (Open-Meteo API), elevation/slope (Copernicus DEM), climate zone.

**Card-less submissions are accepted** but down-weighted in training and flagged in estimates ("uncalibrated"). Never reject a willing contributor; grade the data instead.

**QA gate (I8), in order:** (1) is-soil classifier, (2) sharpness/exposure thresholds, (3) card detection + color-patch extraction, (4) GPS plausibility vs. priors (anti-spoof; a submission claiming desert sand in a peat bog gets human-review flagged), (5) duplicate/near-duplicate hash check.

## 6. Data schema (Postgres/PostGIS, canonical)

```
contributors    id, auth_uid, handle, reputation, precise_location_optin,
                created_at
submissions     id, contributor_id, geom_precise (PRIVATE, RLS),
                h3_r8, h3_r6, captured_at, land_cover, surface_condition,
                disturbed, device_model, precip_flag, elevation, status
                (pending|qa_pass|qa_fail|flagged)
photos          id, submission_id, shot_type (A|B|C), storage_path,
                exif jsonb, card_detected, card_color_correction jsonb,
                sharpness_score
priors          submission_id, source (soilgrids|ssurgo|wosis),
                property (soc|ph|clay|sand|silt|bd|cec|n),
                value, uncertainty_lo, uncertainty_hi, source_depth,
                retrieved_at
gold_labels     id, submission_id, lab_name, method, property, value,
                uncertainty, sampled_depth, verified_by, document_ref
predictions     id, submission_id, model_version, property, value,
                ci_lo, ci_hi, basis (image|prior|fused|neighbors)
qa_events       submission_id, check_name, passed, score, model_version
h3_cells        h3_index, n_submissions, n_gold, prior_uncertainty,
                model_disagreement, acquisition_score, updated_at
```

**Public dataset export (nightly → HF Datasets, ODbL):** photos (with contributor grant), H3-fuzzed location (I7), protocol metadata, priors, gold labels, QA scores. Precise geometry never exports without opt-in.

**Contribution terms:** submitting grants GSIP a license to publish the photo and derived data under ODbL/CC-BY-SA; contributor retains ownership. Terms shown at first submission, one screen, plain language.

## 7. ML architecture

**Model 1 — QA gate:** lightweight classifier (MobileNetV3), trained on pass/fail submissions; runs server-side at ingest, later in-browser (ONNX/WebGPU) for instant capture feedback.

**Model 2 — Soil estimator:** shared vision backbone over card-corrected Shot B (+ Shot A as auxiliary channel), plus a tabular branch for priors/context. Multi-task heads:

| Head | Target | Label source | Honest expectation |
|---|---|---|---|
| Munsell color | hue/value/chroma | derived from card-corrected pixels | near-deterministic with card |
| Texture class | 12-class USDA triangle (coarse 3-class first) | weak: priors; gold: lab PSA | 70–90 % coarse-class published range |
| SOM/SOC | continuous + CI | weak: SoilGrids; gold: lab | moderate; moisture confound handled via surface-condition input |
| pH, CEC, N | continuous + CI | weak priors, gold anchors | **inference via correlation only** — always wide CIs, always labeled as fused estimate (I5) |

**Uncertainty-aware training:** weak labels enter the loss weighted by inverse prior variance (SoilGrids ships per-pixel quantiles); gold labels get full weight. Heteroscedastic regression heads (predict mean + variance) + conformal calibration on the gold holdout. This is how we respect I3 without being capped by it.

**Fusion at inference:** posterior = image evidence × location prior × nearby gold-label kriging. The API returns the decomposition (basis field) so the map and UI can show *why* the estimate is what it is.

**Active learning:** `acquisition_score(cell) = prior_uncertainty × model_disagreement × 1/(1+n_submissions)`. Rendered as the "Most Wanted" map layer — the gamification engine. Contributors see exactly where a photo helps science most.

**Retraining cadence:** nightly fine-tune, weekly full retrain, every release versioned on HF Hub with an auto-generated model card including gold-holdout metrics. No silent model swaps (chatbot-modularity principle from v1 carries over: the estimator is behind one interface and hot-swappable).

## 8. Map system

Layers, all MapLibre + PMTiles, all reproducible from the pipeline:
1. **Prior layers** — SoilGrids properties restyled (available day one, before any ML).
2. **Contribution layer** — H3 density + recent submissions.
3. **Fused correction layer** (Phase 3) — where GSIP's model diverges from priors, with confidence. *This layer is the product.*
4. **Most Wanted layer** — active-learning targets.
5. **Gold anchor layer** — lab-confirmed points (fuzzed per I7).

## 9. Governance & community

- GitHub org: `global-soil-intelligence`, monorepo `gsip`, public roadmap via GitHub Projects, discussions on.
- DCO sign-off on commits (lighter than CLA, standard for MIT projects).
- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `GOVERNANCE.md` (BDFL → steering group as community grows).
- Data partnerships track: university soil labs, extension programs, master-gardener networks, NGOs — the gold-label supply chain. Partner labs get bulk-upload CSV ingestion for `gold_labels`.

## 10. Phased roadmap

**Phase 0 — Foundation (weeks 1–2)**
Org + monorepo + CI, Supabase project + schema + RLS, reference card v1 (print-ready PDF), contribution terms, this spec as `docs/SPEC.md`.
*Done when:* a submission can be inserted end-to-end via API and appears H3-fuzzed in a dev export.

**Phase 1 — Capture + Map, zero ML (weeks 2–6)**
Capture PWA (protocol flow, card overlay guide, offline queue), prior-attach worker, public map site with layers 1–2, nightly ODbL export to HF Datasets.
*Done when:* a stranger with a phone and a printed card can submit in <3 minutes, and the map shows their (fuzzed) dot over SoilGrids layers. **This is the public launch.**

**Phase 2 — First models (weeks 6–12)**
QA gate model live at ingest; estimator v0 (color + coarse texture + SOM) trained on weak labels; nightly retrain pipeline; model cards; estimates shown on each submission with CIs.
*Done when:* gold-holdout coarse-texture accuracy ≥ 70 % and SOM CIs are calibrated (≥ 90 % empirical coverage).

**Phase 3 — The flywheel closes (months 3–6)**
On-demand estimate API + UI ("photograph soil → composite estimate"), gold-label bulk ingestion + partner onboarding, fused correction map layer, Most Wanted layer, reputation/gamification.
*Done when:* estimate requests convert to dataset entries at >80 % and the correction layer visibly improves on SoilGrids at gold points.

**Phase 4 — Scale (6 months +)**
Capacitor-wrapped app-store builds of the PWA (offline field mode, background sync), on-device inference (ONNX/WebGPU), i18n, regional model heads, hardware-partner integrations (the v1 spectroscopy work re-enters here), academic paper on the dataset + method.

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Weak-label noise ceiling | Uncertainty-weighted loss (I3), gold anchoring (I4), conformal calibration; report gold-holdout metrics only. |
| Photo confounders (moisture, light) | Reference card, protocol prompts, surface-condition input feature, precip auto-flag. |
| Junk / adversarial submissions | QA gate (I8), GPS-plausibility vs. priors, reputation weighting, duplicate hashing. |
| Cold-start (empty map, no community) | Map launches useful on day one via public prior layers; seed via extension programs, soil-science Twitter/Reddit, university partnerships; Most Wanted layer gives immediate purpose. |
| Dataset strip-mining | ODbL share-alike; the living flywheel (community + retraining loop) is the moat, not the snapshot. |
| Overclaiming accuracy | I5 enforced in UI copy, API schema (CIs mandatory), and model cards. "Estimate," never "test." |
| Contributor privacy | I7 H3 fuzzing, RLS on precise geometry, opt-in precise publication. |

## 12. Success metrics

Flywheel health: submissions/week, QA pass rate, contributor 30-day retention, gold labels/month.
Science: coarse-texture accuracy vs. gold, SOC RMSE vs. gold, CI calibration coverage, fraction of map cells where fused layer beats prior at gold points.
Community: external contributors merged, partner labs onboarded, dataset downloads/citations.

---

*Licensing: code MIT · data ODbL · models open weights with model cards. Decided 2026-07-22.*
===SPEC END===

===BUILD ORDER START===
# GSIP Build Order — Work Plan for Sol

**Project:** Global Soil Intelligence Project v2 (citizen-science soil mapping flywheel)
**Builder:** Sol (AI coding agent)
**Reviewing engineer:** Claude — reviews every PR before merge
**Product owner:** Justin Hart
**Governing document:** `docs/SPEC.md` (GSIP v2 Spec — Citizen Science Architecture). This build order operationalizes that spec. If this document and the spec conflict, the spec wins; flag the conflict instead of guessing.
**Date:** 2026-07-22

---

## 1. Roles and workflow

- Sol implements **one work package (WP) per pull request**, on a feature branch named `wp-<number>-<slug>` (e.g. `wp-3-capture-pwa`).
- **No direct commits to `main`.** Main is protected; merges happen only after (a) CI green and (b) reviewing-engineer approval.
- Every PR description must contain: the WP number, a checklist of that WP's acceptance criteria with each item checked or explained, which spec invariants (I1–I8) the change touches, and any deviation from this build order with justification.
- Commits: Conventional Commits format, DCO sign-off (`git commit -s`).
- If a WP turns out to be under-specified, Sol opens a GitHub issue asking the question and stops on that WP — do not fill spec gaps with assumptions. Other WPs may proceed if independent.

## 2. Hard guardrails (violations = automatic PR rejection)

1. **Languages: TypeScript and Python only.** No Dart/Flutter, no Go, no Rust. TS strict mode on. Python 3.11+, fully type-hinted.
2. **No license changes.** Code MIT, data ODbL. No dependency with a license incompatible with MIT distribution (GPL-linked libs need reviewer sign-off).
3. **No schema changes outside a migration file**, and no migration that contradicts `docs/SPEC.md` §6 without a spec-update PR first.
4. **Never store or export precise contributor coordinates in any public path** (spec I7). Public artifacts get H3-r8 fuzzing only. RLS policies enforce this at the database layer, not just app code.
5. **UI and API copy never says "soil test."** Always "estimate" with uncertainty (spec I5).
6. **No paid/closed services** in the default deployment path. Supabase free tier, GitHub Actions, GitHub Pages, Hugging Face free tier, Open-Meteo, SoilGrids REST. Anything with a bill or a proprietary SDK needs reviewer sign-off first.
7. **No secrets in the repo.** All config via environment variables; `.env.example` documents every variable.
8. **Every WP ships with tests.** A PR with production code and no tests is incomplete regardless of how well it works.

## 3. Repository

The repository already exists, fresh and empty: `https://github.com/global-soil-intelligence/gsip`, public, with branch protection active on `main` (PR + 1 approval required, stale approvals dismissed, conversation resolution required, force-push/deletion blocked).

Monorepo layout (spec §4):

```
gsip/
├── docs/                 SPEC.md, this file (BUILD_ORDER.md), ADRs
├── apps/
│   ├── capture-pwa/      TS + Vite + React + vite-plugin-pwa
│   └── map-web/          TS + Vite + MapLibre GL
├── packages/
│   └── schema/           shared TS types, zod schemas, generated DB types
├── supabase/             migrations/, RLS policies, edge functions (TS), seed
├── pipeline/             Python: prior-attach, H3 aggregation, exports
├── ml/                   Python: QA gate + estimator (Phase 2, stub now)
├── card/                 reference-card generator + print PDFs
└── .github/              workflows/, PR template, issue templates
```

Tooling baseline: pnpm workspaces; ESLint + Prettier; Vitest + Playwright; Python via uv, ruff, mypy --strict, pytest. One `pnpm test` / `uv run pytest` from the root must run everything.

## 4. Work packages

### Phase 0 — Foundation

**WP-0: Repo bootstrap**
Scope: monorepo scaffold per §3; CI workflows (lint + typecheck + tests on PR; deploy PWA and map site to GitHub Pages on main); `LICENSE` (MIT), `DATA_LICENSE` (ODbL), `README.md` (project pitch + quickstart), `CONTRIBUTING.md` (DCO, WP workflow), `CODE_OF_CONDUCT.md`; PR and issue templates embedding the acceptance-criteria checklist format; plus `docs/SPEC.md` and `docs/BUILD_ORDER.md` as provided.
Acceptance criteria:
- [ ] Fresh clone + documented setup commands → all linters, typecheckers, and (empty) test suites pass locally and in CI.
- [ ] CI blocks a PR that fails lint or typecheck (demonstrate with a deliberately failing draft PR, then close it).
- [ ] README explains the project accurately in ≤ 300 words, consistent with spec §1 and I5 language rules.

**WP-1: Database schema + RLS**
Scope: Supabase migrations implementing spec §6 exactly (contributors, submissions, photos, priors, gold_labels, predictions, qa_events, h3_cells); PostGIS + pgcrypto extensions; RLS policies — contributors read/write own rows; `submissions.geom_precise` readable only by owner and service role; anonymous users can read only public aggregate views; a `public_submissions` view exposing H3-fuzzed data only; seed script with 25 synthetic submissions spanning 3 continents; generated TS types into `packages/schema`.
Acceptance criteria:
- [ ] `supabase db reset` builds the schema from migrations with zero errors.
- [ ] Automated RLS tests prove: anon cannot read `geom_precise`; contributor A cannot read contributor B's precise geometry; the public view contains no coordinate more precise than H3-r8 centroid. **(spec I7 — this is the most important test in Phase 0)**
- [ ] Seed script is idempotent.

**WP-2: Reference card**
Scope: Python generator (`card/generate.py`) producing print-ready A6 PDFs — color edition (8 calibrated patches + neutral gray + ArUco 4x4 marker + protocol text) and B&W-printer edition (grayscale patches + marker); patch color values documented in `card/CARD_SPEC.md` with sRGB targets; a validation script that, given a photo of a printed card, detects the marker and extracts patch values via OpenCV.
Acceptance criteria:
- [ ] PDFs generate deterministically from the script (no binary blobs committed except the released PDFs).
- [ ] Validation script detects the marker and recovers all patches from ≥ 9 of 10 test photos (fixtures included: varied angle/lighting, ≤ 30° skew).
- [ ] Card fits A6, prints legibly at 300 dpi on a consumer printer.

### Phase 1 — Capture + Map (public launch, zero ML)

**WP-3: Capture PWA**
Scope: `apps/capture-pwa` — Supabase auth (email magic link + anonymous-contribution mode); guided capture flow per spec §5 (Shot A → B → optional C, on-screen card-placement overlay, one-tap metadata prompts); geolocation with accuracy display + manual pin fallback; offline queue in IndexedDB with background retry; upload to Supabase Storage + submission insert; contribution-terms screen at first submission (plain-language ODbL grant); post-submit confirmation showing the fuzzed H3 cell on a minimap.
Acceptance criteria:
- [ ] Lighthouse PWA installable score passes; capture flow works on iOS Safari and Android Chrome (Playwright mobile emulation + documented manual test protocol).
- [ ] Airplane-mode submission queues locally and syncs on reconnect (automated test with network mocking).
- [ ] A first-time user completes a submission in ≤ 3 minutes (scripted walkthrough, timed in the PR description).
- [ ] No precise coordinate ever appears in client-side logs, URLs, or analytics.
- [ ] All copy passes the I5 language rule (estimate, not test) — grep-able lint rule included.

**WP-4: Prior-attach worker**
Scope: on submission insert, fetch weak labels — SoilGrids v2 REST (soc, phh2o, clay, sand, silt, bdod, cec, nitrogen; mean + q05 + q95 at 0–5 cm and 0–30 cm) and, when inside CONUS, SSURGO via Soil Data Access; enrich with Open-Meteo recent-precip flag and Copernicus DEM elevation; write to `priors`; retries with exponential backoff; dead-letter status on repeated failure. Implement as Supabase edge function (TS) with the fetch logic in `packages/schema`-typed pure functions, or Python worker in `pipeline/` — Sol proposes in the PR, reviewer approves.
Acceptance criteria:
- [ ] Unit tests run against recorded HTTP fixtures (no live API calls in CI).
- [ ] A seeded submission gets fully populated priors within 60 s in the dev environment.
- [ ] SoilGrids uncertainty (q05/q95) is stored, not just the mean (spec I3 depends on this).
- [ ] Worker is idempotent per (submission, source, property).

**WP-5: Map site**
Scope: `apps/map-web` — MapLibre GL; prior layers from SoilGrids restyled as PMTiles (build script in `pipeline/` converts SoilGrids COGs → PMTiles for an initial property set: SOC, pH, clay); contribution-density layer from `h3_cells` (live from Supabase public view); layer switcher, legend, property units; deployed to GitHub Pages.
Acceptance criteria:
- [ ] Map loads globally with SOC/pH/clay layers and correct legends at zoom 2–12.
- [ ] Seeded submissions appear as H3 hexes; clicking a hex shows count + latest date, never a precise point.
- [ ] Total tile payload for initial view ≤ 5 MB; PMTiles build is reproducible via one documented command.

**WP-6: Nightly public export**
Scope: scheduled GitHub Action → `pipeline/export.py`: pull QA-passed submissions, apply H3-r8 fuzzing, bundle photos (with granted licenses) + metadata + priors + gold labels into a versioned Hugging Face Dataset push; dataset card auto-generated with ODbL notice, schema docs, and row counts; refresh `h3_cells` aggregates.
Acceptance criteria:
- [ ] Export contains zero precise coordinates (automated assertion in the export itself — the job fails loudly if violated).
- [ ] Dataset loads via `datasets.load_dataset()` round-trip test.
- [ ] Dataset card renders with license, schema, and citation block.
- [ ] Job is idempotent per day; re-runs don't duplicate rows.

### Phase 2+ (spec §10 — do not start without a new build order)
WP-7 QA gate model · WP-8 estimator v0 (color/texture/SOM, uncertainty-aware) · WP-9 nightly retrain + model cards · WP-10 on-demand estimate API · WP-11 gold-label bulk ingestion · WP-12 fused correction + Most Wanted layers. These will be specified after Phase 1 review.

## 5. Review gates (what the reviewing engineer checks on every PR)

1. Acceptance criteria all demonstrably met (CI evidence or reproducible commands, not claims).
2. Guardrails §2 — automatic rejection on violation.
3. Invariant impact honestly declared; I5 (language) and I7 (privacy) checked on every PR regardless of declaration.
4. Tests actually test behavior (reviewer may run mutation spot-checks).
5. No scope creep — code outside the WP scope goes to a separate PR.
6. Dependencies: each new one justified in the PR description (license, maintenance status, size).

## 6. Environment variables (`.env.example`)

```
SUPABASE_URL=                # project URL
SUPABASE_ANON_KEY=           # client key (publishable)
SUPABASE_SERVICE_ROLE_KEY=   # server-only: workers, exports — never shipped to client
HF_TOKEN=                    # dataset push (CI secret)
OPEN_METEO_BASE=https://api.open-meteo.com   # no key required
SOILGRIDS_BASE=https://rest.isric.org/soilgrids/v2.0
```

## 7. Sequencing

WP-0 → WP-1 → (WP-2 ∥ WP-3 ∥ WP-4) → WP-5 → WP-6. WP-2/3/4 are parallelizable after the schema lands. Phase 1 launch review happens after WP-6 merges: reviewing engineer runs the full "stranger with a phone and a printed card" test from spec §10 Phase 1 before public announcement.

---

*Sol: read `docs/SPEC.md` in full before WP-0. When in doubt, open an issue — a question costs minutes; an assumption costs a rebuild.*
===BUILD ORDER END===
