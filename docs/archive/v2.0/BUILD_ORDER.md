> **Archived:** superseded by [`../../BUILD_ORDER.md`](../../BUILD_ORDER.md). Sol is retired; do not implement from this v2.0 work plan.

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

**Decision: reuse the existing `GSIP` repository, reset for v2.**
- Preserve v1 history on branch `archive/v1`.
- `main` becomes a clean v2 tree (orphan branch or hard reset — Justin's call at execution time).
- Repo must be **public** (spec I1) with branch protection on `main`: require PR, require CI, require 1 approving review.

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
Scope: monorepo scaffold per §3; CI workflows (lint + typecheck + tests on PR; deploy PWA and map site to GitHub Pages on main); `LICENSE` (MIT), `DATA_LICENSE` (ODbL), `README.md` (project pitch + quickstart), `CONTRIBUTING.md` (DCO, WP workflow), `CODE_OF_CONDUCT.md`; PR and issue templates embedding the acceptance-criteria checklist format.
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
