# GSIP v2 — Citizen-Science Architecture Specification

**Project:** Global Soil Intelligence Project (globalsoilintelligence.com)
**Version:** 2.1 — 2026-07-22
**Status:** ACTIVE — supersedes v2.0 (2026-07-22) and all 2024 architecture documents (`GSIP outline 5.0`, `GSIP compressed updated`, `GSIP codeing algorithm`, `Page Outline GSIP`, `GISP page tree of thought`). The `GSIP core algorithms` spectroscopy doc remains relevant as a future Phase 4+ reference for hardware-partner integrations.
**Owner:** Justin Hart, Viridis LLC
**Hosting:** GitHub (org-based monorepo + open dataset/model on Hugging Face)

---

## 1. Mission

Build the world's best-resolved, living global soil map by turning every smartphone into a soil sensor. Contributors submit geotagged close-up photos of soil; AI fuses those images with existing public soil map data to produce on-demand soil composition estimates. Every estimate request is also a contribution — the dataset, the model, and the map improve with each use.

**What GSIP v2 is:** an open-source citizen-science data flywheel (the iNaturalist playbook applied to soil).
**What GSIP v2 is not:** a SaaS farm-management app, a lab-test replacement, or a carbon-credit marketplace.

## 2. Invariants

These are the non-negotiable properties of the system. Any implementation decision that violates one of these is wrong.

- **I1 — Open by default.** All code is MIT-licensed. Published databases and structured data are ODbL-1.0-licensed; contributed photos are separately licensed CC BY-SA 4.0. Model weights are openly released with model cards. Anyone can self-host the full stack.
- **I2 — The contribution unit is a geotagged close-up photo set** captured per the standard protocol (§5), submittable from any modern phone with no app install.
- **I3 — Existing soil maps are priors, never truth.** SoilGrids/SSURGO/WoSIS values attached to each submission are weak labels with stated uncertainty. They bootstrap training; they do not cap it.
- **I4 — Confirmed lab results are gold labels.** Lab-paired submissions anchor calibration and are tracked separately from weak labels at every pipeline stage.
- **I5 — Every output is a probabilistic estimate with uncertainty.** The product never claims to be a "soil test." UI copy, API responses, and docs always carry confidence intervals and the basis of the estimate (image / prior / nearby gold labels).
- **I6 — Every prediction request feeds the flywheel.** A photo submitted for an on-demand estimate enters the dataset (subject to QA and contributor consent).
- **I7 — Contributor location privacy is protected.** Precise coordinates are private operational data and never enter a public artifact; the public dataset and map publish at H3-cell resolution (default res 8, ~460 m edge). Original uploads may exist only in a short-lived private ingest quarantine. Server-side ingest strips EXIF/XMP before promotion to canonical private storage, retaining only allowlisted non-location camera fields in private structured metadata. Public export strips metadata again and asserts that no location metadata remains.
- **I8 — Junk cannot pollute the dataset.** Every submission passes an automated QA gate before it is labeled or trained on. Rejected submissions are retained (flagged) for QA-model training only.

## 3. System overview

```
 Contributor phone (PWA)
        │  photos + GPS + protocol metadata
        ▼
 Supabase (Postgres + PostGIS + private Storage + Auth, RLS)
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
| Backend | **Supabase** (hosted for the canonical instance) | Postgres + PostGIS + private Storage buckets + Auth + row-level security with no custom server for Phase 1 (PostgREST API). Supabase is itself open source → satisfies I1 self-hostability. |
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

**Auto-captured metadata:** GPS + accuracy radius, timestamp, device model, and an allowlist of non-location camera fields extracted during ingest. Raw EXIF/XMP is never retained in canonical storage. **One-tap prompts:** land cover (7 icons), surface condition (dry/moist/wet), disturbed? (y/n). **Auto-enriched at ingest:** recent-precipitation flag (Open-Meteo API), elevation (Copernicus DEM GLO-90 via the Open-Meteo Elevation API — free, no key, with Copernicus and Open-Meteo attribution). Slope and climate zone are deferred to Phase 2+; they have no schema columns until a spec update adds them.

**Card-less submissions are accepted** but down-weighted in training and flagged in estimates ("uncalibrated"). Never reject a willing contributor; grade the data instead.

**QA gate (I8), in order:** (1) is-soil classifier *(ML — joins the gate in Phase 2)*, (2) sharpness/exposure thresholds, (3) card detection + color-patch extraction, (4) GPS plausibility vs. priors (anti-spoof; a submission claiming desert sand in a peat bog gets human-review flagged), (5) duplicate/near-duplicate hash check. Checks 2–5 are deterministic (non-ML) and run from Phase 1 (WP-4b in the build order); the gate is live from the first public submission.

## 6. Data schema (Postgres/PostGIS, canonical)

```
contributors    id, auth_uid, handle, reputation, terms_version,
                terms_accepted_at, created_at
submissions     id, contributor_id, geom_precise (PRIVATE, RLS),
                h3_r8, h3_r6, captured_at, land_cover, surface_condition,
                disturbed, device_model, precip_flag, elevation, status
                (pending|qa_pass|qa_fail|flagged)
photos          id, submission_id, shot_type (A|B|C), storage_path,
                camera_metadata_private jsonb, card_detected,
                card_color_correction jsonb, sharpness_score
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

**Property naming:** `priors.property` (and `gold_labels`/`predictions`) uses canonical GSIP names (`soc|ph|clay|sand|silt|bd|cec|n`). Source-specific codes (SoilGrids `phh2o`, `bdod`, `nitrogen`, …) are mapped at ingest via a single mapping table maintained in `packages/schema` — no source codes leak into stored rows.

**Public dataset export (nightly → HF Datasets):** the database and structured data are ODbL 1.0; contributed photos are CC BY-SA 4.0. The export includes only photos with a recorded grant, H3-fuzzed location (I7), protocol metadata, priors, gold labels, and QA scores. Precise geometry and private camera metadata never export. Photo binaries are sanitized at ingest, stripped again at export, and scanned for EXIF/XMP before release; the job fails loudly if any metadata remains (I7).

**Contribution terms:** submitting grants GSIP permission to include structured contribution data in the ODbL 1.0 database and to publish the contributed photos under CC BY-SA 4.0; the contributor retains ownership. The terms state the public attribution name or pseudonym used for photos. Terms are shown at first submission in one plain-language screen. Acceptance is recorded (`contributors.terms_version`, `terms_accepted_at`); no photo enters the public export without a recorded grant (I6). This licensing design must receive legal review before the Phase 1 public launch.

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
- Legacy repo `github.com/jhumoz/GSIP`: archive with a pointer README to this org (open operational item).

## 10. Phased roadmap

**Phase 0 — Foundation (weeks 1–2)**
Org + monorepo + CI, Supabase project + schema + RLS, reference card v1 (print-ready PDF), contribution terms, this spec as `docs/SPEC.md`.
*Done when:* a submission can be inserted end-to-end via API and appears H3-fuzzed in a dev export.

**Phase 1 — Capture + Map, zero ML (weeks 2–6)**
Capture PWA (protocol flow, card overlay guide, offline queue), prior-attach worker, ingest QA gate (non-ML checks 2–5 of §5), public map site with layers 1–2, nightly ODbL export to HF Datasets.
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
| Contributor privacy | I7 H3 fuzzing, RLS on precise geometry, private Storage policies, ingest-time metadata sanitization, and fail-closed export scanning. Precise coordinates are never published. |

## 12. Success metrics

Flywheel health: submissions/week, QA pass rate, contributor 30-day retention, gold labels/month.
Science: coarse-texture accuracy vs. gold, SOC RMSE vs. gold, CI calibration coverage, fraction of map cells where fused layer beats prior at gold points.
Community: external contributors merged, partner labs onboarded, dataset downloads/citations.

## 13. Changelog

- **v2.1 (2026-07-22):** I7 made fail-closed: precise coordinates are never public, original uploads are quarantined privately, canonical photos are sanitized at ingest, and export scans every image again; database/data licensing (ODbL 1.0) is separated from photo licensing (CC BY-SA 4.0) with a pre-launch legal-review gate; §5 elevation source specified (Open-Meteo Elevation API / Copernicus GLO-90) with attribution, while slope and climate zone are deferred to Phase 2+; §5 QA gate phased — deterministic checks 2–5 active from Phase 1, is-soil classifier joins in Phase 2; §6 `contributors` gains `terms_version` + `terms_accepted_at`; §6 canonical property-name mapping rule added; §9 legacy-repo disposition noted; §10 Phase 1 scope includes ingest QA; §11 privacy row updated.
- **v2.0 (2026-07-22):** initial citizen-science architecture; supersedes all 2024 documents.

---

*Licensing: code MIT · databases/structured data ODbL 1.0 · contributed photos CC BY-SA 4.0 · models open weights with model cards. Licensing terms require legal review before public launch. Decided 2026-07-22.*
