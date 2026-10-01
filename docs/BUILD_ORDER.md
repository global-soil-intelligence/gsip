# GSIP Build Order — Work Plan

**Project:** Global Soil Intelligence Project v2 (citizen-science soil mapping flywheel)
**Version:** 2.2 — 2026-07-22
**Builder:** Claude (Cowork build sessions). _Sol is retired as of v2.1; the Sol kickoff prompt is void._
**Independent review:** every PR is reviewed by fresh-context adversarial review agents (no memory of authoring the code) run against the §5 review gates; findings and their resolutions are posted to the PR. The GitHub approval required by branch protection must come from a non-author maintainer account. Justin Hart provides the final product-owner go/no-go; when his account authors a PR, that go/no-go cannot also satisfy GitHub's non-author approval.
**Product owner:** Justin Hart
**Governing document:** `docs/SPEC.md` (GSIP v2 Spec, v2.2). This build order operationalizes that spec. If this document and the spec conflict, the spec wins; flag the conflict instead of guessing.

---

## 1. Roles and workflow

- The builder implements **one work package (WP) per pull request**, on a feature branch named `wp-<number>-<slug>` (e.g. `wp-3-capture-pwa`).
- **No direct commits to `main` after the authorized repository seed.** Main is protected; merges happen only after (a) CI green, (b) adversarial review findings resolved, (c) one approving GitHub review from a non-author maintainer, and (d) the product owner's go/no-go.
- Every PR description must contain: the WP number, a checklist of that WP's acceptance criteria with each item checked or explained, which spec invariants (I1–I8) the change touches, and any deviation from this build order with justification.
- Commits: Conventional Commits format, DCO sign-off (`git commit -s`).
- If a WP turns out to be under-specified, the builder opens a GitHub issue stating the question and stops on that WP — spec gaps are not filled with assumptions. Other WPs may proceed if independent.

## 2. Hard guardrails (violations = automatic PR rejection)

1. **Languages: TypeScript and Python only.** No Dart/Flutter, no Go, no Rust. TS strict mode on. Python 3.11+, fully type-hinted.
2. **No license changes.** Code is MIT; databases and structured data are ODbL 1.0; contributed photos are CC BY-SA 4.0. No dependency with a license incompatible with MIT distribution (GPL-linked libs need reviewer sign-off). The contribution terms and attribution flow require legal review before public launch.
3. **No schema changes outside a migration file**, and no migration that contradicts `docs/SPEC.md` §6 without a spec-update PR first.
4. **Never store or export precise contributor coordinates in any public path** (spec I7) — including image EXIF/XMP metadata. Original uploads may exist only in a short-lived private ingest bucket; canonical photos are metadata-sanitized and remain private. Public artifacts get H3-r8 fuzzing and metadata-free images only. Database and Storage RLS enforce this, and export assertions fail closed.
5. **UI and API copy never says "soil test."** Always "estimate" with uncertainty (spec I5).
6. **No paid/closed services** in the default deployment path. Supabase free tier, GitHub Actions, GitHub Pages, Hugging Face free tier, Open-Meteo, SoilGrids REST. Anything with a bill or a proprietary SDK needs product-owner sign-off first. _Known upcoming decision:_ Supabase free tier (500 MB database / 1 GB storage / 7-day inactivity pause) suffices for Phase 0 development; a Pro-tier upgrade decision is expected before the Phase 1 public launch — product owner signs off.
7. **No secrets in the repo.** All config via environment variables; `.env.example` documents every variable.
8. **Every WP ships with tests.** A PR with production code and no tests is incomplete regardless of how well it works.

## 3. Repository

The repository exists at `https://github.com/global-soil-intelligence/gsip`, public, with branch protection active on `main` (PR + 1 approval required, stale approvals dismissed, conversation resolution required, force-push/deletion blocked). Because a pull request cannot target a branch that does not yet exist, the product owner authorizes exactly one signed, empty seed commit to create `main`. The v2.1 governing documents then land through the repository's first pull request; all later changes also use pull requests. After WP-0 lands CI workflows, "require status checks to pass" is added to the ruleset.

**GitHub Pages note:** Pages serves one site per repo. Both apps deploy under subpaths (`/capture`, `/map`) from a single combined Pages artifact built in CI; the custom domain (globalsoilintelligence.com) can front the Pages site later.

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
Scope: monorepo scaffold per §3; CI workflows (lint + typecheck + tests on PR; deploy PWA and map site to GitHub Pages on main, combined-artifact subpath layout); `LICENSE` (MIT), `DATA_LICENSE` (ODbL 1.0), photo-license notice (CC BY-SA 4.0), `README.md` (project pitch + quickstart), `CONTRIBUTING.md` (DCO, WP workflow), `CODE_OF_CONDUCT.md`; PR and issue templates embedding the acceptance-criteria checklist format; preserve `docs/SPEC.md` (v2.2) and `docs/BUILD_ORDER.md` (this file) as the governing documents.
Acceptance criteria:

- [ ] Fresh clone + documented setup commands → all linters, typecheckers, and (empty) test suites pass locally and in CI.
- [ ] CI blocks a PR that fails lint or typecheck (demonstrate with a deliberately failing draft PR, then close it).
- [ ] README explains the project accurately in ≤ 300 words, consistent with spec §1 and I5 language rules.

**WP-1: Database schema + RLS**
Scope: Supabase migrations implementing spec §6 (v2.2) exactly — contributors, immutable contribution_grants, submissions, photos, priors, gold_labels, predictions, qa_events, h3_cells; canonical unit/depth constraints; PostGIS + pgcrypto extensions; a short-lived private `incoming-photos` bucket and a canonical private `submission-photos` bucket; Database and Storage RLS policies — contributors read/write own rows and objects; `submissions.geom_precise` and `photos.camera_metadata_private` readable only by owner and service role; public-key users can read only safe H3-fuzzed columns and aggregates; a `public_submissions` view exposing safe columns only; seed script with 25 synthetic submissions spanning 3 continents; generated TS types into `packages/schema`.
Acceptance criteria:

- [ ] `supabase db reset` builds the schema from migrations with zero errors.
- [ ] Automated RLS tests prove: anon cannot read `geom_precise`, private camera metadata, or either photo bucket; contributor A cannot read contributor B's precise geometry or objects; the public view contains no coordinate more precise than H3-r8 centroid. **(spec I7 — this is the most important test in Phase 0)**
- [ ] Seed script is idempotent.

**WP-2: Reference card**
Scope: Python generator (`card/generate.py`) producing print-ready A6 PDFs — color edition (8 calibrated patches + neutral gray + ArUco 4x4 marker + protocol text) and B&W-printer edition (grayscale patches + marker); patch color values documented in `card/CARD_SPEC.md` with sRGB targets; a validation script that, given a photo of a printed card, detects the marker and extracts patch values via OpenCV.
Acceptance criteria:

- [ ] PDFs generate deterministically from the script (no binary blobs committed except the released PDFs).
- [ ] Validation script detects the marker and recovers all patches from ≥ 9 of 10 test photos (fixtures included: varied angle/lighting, ≤ 30° skew).
- [ ] Card fits A6, prints legibly at 300 dpi on a consumer printer.

### Phase 1 — Capture + Map (public launch, zero ML)

**WP-3: Capture PWA**
Scope: `apps/capture-pwa` — Supabase auth (email magic link + Supabase Anonymous Sign-Ins); guided capture flow per spec §5 (Shot A → B → optional C, on-screen card-placement overlay, one-tap metadata prompts); geolocation with accuracy display + manual pin fallback; offline queue in IndexedDB with background retry and local cleanup after confirmed sync; immutable `contribution_grants` creation; upload to the private owner-prefixed `incoming-photos` path + pending submission insert; contribution-terms screen explaining the ODbL 1.0 structured-data license, CC BY-SA 4.0 photo license, and public attribution choice; post-submit confirmation showing the fuzzed H3 cell on a minimap.
Acceptance criteria:

- [ ] Lighthouse PWA installable score passes; capture flow works on iOS Safari and Android Chrome (Playwright mobile emulation + documented manual test protocol).
- [ ] Airplane-mode submission queues locally and syncs on reconnect (automated test with network mocking).
- [ ] A first-time user completes a submission in ≤ 3 minutes (scripted walkthrough, timed in the PR description).
- [ ] No precise coordinate ever appears in client-side logs, URLs, or analytics.
- [ ] A confirmed sync removes the local queued photo and precise location; automated tests cover success and retry behavior.
- [ ] All copy passes the I5 language rule (estimate, not test) — grep-able lint rule included.

**WP-4: Prior-attach worker**
Scope: on submission insert, fetch weak labels — SoilGrids v2 REST (soc, phh2o, clay, sand, silt, bdod, cec, nitrogen; mean + q05 + q95 at 0–5 cm and 0–30 cm) and, when inside CONUS, SSURGO via Soil Data Access; enrich with Open-Meteo recent-precip flag and elevation via the Open-Meteo Elevation API (Copernicus GLO-90 — free, no key, already an approved service); write to `priors` using canonical GSIP property names per spec §6 (mapping table in `packages/schema`); retries with exponential backoff; dead-letter status on repeated failure. Implement as Supabase edge function (TS) with the fetch logic in `packages/schema`-typed pure functions, or Python worker in `pipeline/` — builder proposes in the PR, reviewer approves.
Acceptance criteria:

- [ ] Unit tests run against recorded HTTP fixtures (no live API calls in CI).
- [ ] A seeded submission gets fully populated priors within 60 s in the dev environment.
- [ ] SoilGrids uncertainty (q05/q95) is stored, not just the mean (spec I3 depends on this).
- [ ] Worker is idempotent per (submission, source, property).
- [ ] Property names stored in canonical GSIP form; the source-code→canonical mapping is unit-tested.

**WP-4b: Ingest QA gate (non-ML)**
Scope: deterministic QA pipeline at ingest implementing spec §5 checks 2–5 — server-side EXIF/XMP stripping before promotion from the short-lived `incoming-photos` bucket to canonical private `submission-photos` storage; allowlisted non-location camera fields written to `photos.camera_metadata_private`; sharpness/exposure thresholds (reusing `card/` validation code where applicable); card detection + color-patch extraction recorded to `photos.card_detected` / `card_color_correction`; GPS plausibility (accuracy-radius sanity + gross prior mismatch → human-review flag); duplicate/near-duplicate perceptual-hash check; writes a `qa_events` row per check; sets `submissions.status` → `qa_pass|qa_fail|flagged`; card-less submissions pass but are marked "uncalibrated" per §5. Exposes a stubbed interface where the Phase 2 is-soil classifier (WP-7) will slot in.
Acceptance criteria:

- [ ] Every seeded submission reaches a terminal QA status with a `qa_events` row per executed check.
- [ ] Fixture set covers: sharp/blurry, card/no-card, GPS-implausible, and near-duplicate pairs — each routed to the correct status.
- [ ] Gate is deterministic: identical input produces identical status and scores across two runs (asserted in tests).
- [ ] Canonical photo fixtures contain no EXIF/XMP; raw quarantine objects are deleted after successful promotion and expire fail-safe if processing stalls.
- [ ] No ML dependency anywhere in this WP.

**WP-5: Map site**
Scope: `apps/map-web` — MapLibre GL; prior layers from SoilGrids restyled as PMTiles (build script in `pipeline/` converts SoilGrids COGs → PMTiles for an initial property set: SOC, pH, clay); contribution-density layer from `h3_cells` (live from Supabase public view); layer switcher, legend, property units; deployed to GitHub Pages. **Native tile zoom is capped at z8; deeper zoom levels render via overzoom.** Global native-z12 raster builds are out of scope (multi-GB archives).
Acceptance criteria:

- [ ] Map loads globally with SOC/pH/clay layers and correct legends at zoom 2–12 (overzoom beyond native z8).
- [ ] Seeded submissions appear as H3 hexes; clicking a hex shows count + latest date, never a precise point.
- [ ] Total tile payload for initial view ≤ 5 MB; PMTiles build is reproducible via one documented command.

**WP-6: Nightly public export**
Scope: scheduled GitHub Action → `pipeline/export.py`: pull QA-passed submissions, apply H3-r8 fuzzing, **strip all EXIF/XMP metadata from photo binaries again**, bundle photos (with recorded contributor grant only) + metadata + priors + gold labels into a versioned Hugging Face Dataset push; dataset card auto-generated with an ODbL 1.0 notice for the database/structured data and a CC BY-SA 4.0 notice plus attribution for photos; refresh `h3_cells` aggregates.
Acceptance criteria:

- [ ] Export contains zero precise coordinates in tabular data **or image metadata** — the automated assertion scans both columns and the EXIF of every exported image binary, and the job fails loudly if violated.
- [ ] Dataset loads via `datasets.load_dataset()` round-trip test.
- [ ] Dataset card renders with separate database/data and photo licenses, photo attribution, schema, and citation blocks.
- [ ] Job is idempotent per day; re-runs don't duplicate rows.
- [ ] No photo whose submission lacks an immutable `contribution_grants` row is exported (spec I6).

### Phase 2+ (spec §10 — do not start without a new build order)

WP-7 QA gate model (is-soil, slots into the WP-4b interface) · WP-8 estimator v0 (color/texture/SOM, uncertainty-aware) · WP-9 nightly retrain + model cards · WP-10 on-demand estimate API · WP-11 gold-label bulk ingestion · WP-12 fused correction + Most Wanted layers. These will be specified after Phase 1 review.

## 5. Review gates (checked on every PR)

Run by fresh-context adversarial review agents; findings are posted to the PR and resolved before the non-author maintainer's GitHub approval and the product owner's go/no-go.

1. Acceptance criteria all demonstrably met (CI evidence or reproducible commands, not claims).
2. Guardrails §2 — automatic rejection on violation.
3. Invariant impact honestly declared; I5 (language) and I7 (privacy, including database rows, Storage policies, image metadata, and offline cleanup) checked on every PR regardless of declaration.
4. Tests actually test behavior (reviewer may run mutation spot-checks).
5. No scope creep — code outside the WP scope goes to a separate PR.
6. Dependencies: each new one justified in the PR description (license, maintenance status, size).
7. Licensing boundaries remain explicit: ODbL 1.0 for the database/structured data, CC BY-SA 4.0 for contributed photos, and MIT for code. Public launch remains blocked until contribution terms receive legal review.

## 6. Environment variables (`.env.example`)

```
SUPABASE_URL=                # project URL
SUPABASE_PUBLISHABLE_KEY=    # server-side tools using the public client key
VITE_SUPABASE_PUBLISHABLE_KEY= # browser-safe publishable key
SUPABASE_SERVICE_ROLE_KEY=   # server-only: workers, exports — never shipped to client
HF_TOKEN=                    # dataset push (CI secret)
OPEN_METEO_BASE=https://api.open-meteo.com   # no key required; also serves the Elevation API
SOILGRIDS_BASE=https://rest.isric.org/soilgrids/v2.0
```

## 7. Sequencing

WP-0 → WP-1 → (WP-2 ∥ WP-3 ∥ WP-4) → (WP-4b ∥ WP-5) → WP-6. WP-2/3/4 are parallelizable after the schema lands; WP-4b needs WP-2's validation code; WP-6 needs WP-4b (it exports QA-passed rows only). Phase 1 launch review happens after WP-6 merges: the full "stranger with a phone and a printed card" test from spec §10 Phase 1 runs before public announcement.

## 8. Changelog

- **v2.2 (2026-07-22):** anonymous contribution pinned to Supabase Anonymous Sign-Ins; WP-1 gains immutable per-submission grants and canonical unit/depth constraints; WP-3 records the grant and uses owner-prefixed quarantine paths; WP-6 checks the referenced immutable grant.
- **v2.1 (2026-07-22):** builder changed from Sol to Claude; review workflow now requires a non-author GitHub approver plus product-owner go/no-go; one signed empty-repository seed commit is authorized; WP-4b (ingest QA, non-ML) added with private quarantine, ingest-time metadata sanitization, and fail-safe cleanup; WP-4 elevation source pinned to Open-Meteo Elevation API and canonical property-name mapping required; WP-5 native zoom capped at z8; WP-6 repeats EXIF stripping, asserts image safety, separates ODbL data from CC BY-SA photos, and checks recorded grants; guardrails cover Database and Storage privacy; guardrail 6 gains the Supabase-tier upgrade note; WP-0 preserves the v2.1 governing docs.
- **v2.0 (2026-07-22):** initial build order for Sol, WP-0–WP-6.

---

_Builder: read `docs/SPEC.md` in full before WP-0. When in doubt, open an issue — a question costs minutes; an assumption costs a rebuild._
