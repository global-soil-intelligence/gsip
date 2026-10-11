# GSIP v3 — Citizen-Science Architecture Specification

**Project:** Global Soil Intelligence Project (globalsoilintelligence.com)
**Version:** 3.0 — 2026-10-10
**Status:** PROPOSED — becomes ACTIVE when the product owner merges it. Supersedes v2.2 and every earlier architecture document. The 2024 `GSIP core algorithms` spectroscopy document remains a Phase 4+ reference for hardware-partner integrations.
**Owner:** Justin Hart, Viridis LLC (steward; see `GOVERNANCE.md`)
**Hosting:** GitHub (org monorepo) · Supabase (canonical instance) · Hugging Face (open dataset and models)

---

## 1. Mission

Build the world's best-resolved, living global soil map by turning every phone into a soil sensor and letting people and AI agents build on the result. Contributors photograph soil with a printable reference card; GSIP fuses those observations with public soil maps to produce soil estimates with explicit uncertainty. Every verified observation, label and estimate request improves the dataset, the models and the map.

**What GSIP is:** an open-source citizen-science data flywheel (the iNaturalist playbook applied to soil), open to human contributors and to agents acting for accountable people.
**What GSIP is not:** a farm-management SaaS, a laboratory replacement, a carbon-credit marketplace, a data broker or an advertising platform.

The phone app is the main contribution funnel (§4, WP-APP-1). Agents start as readers and assistants and earn wider roles in stages (§9). Viridis LLC stewards the hosted service under the business guardrails B1–B8 in `GOVERNANCE.md`; the commons stays free and forkable.

## 2. Invariants

These are the non-negotiable properties of the system. Any implementation decision that violates one of them is wrong. Each invariant names the check that proves it; a check that does not exist yet is listed in the build order as acceptance criteria.

### Core (I1–I8, amended in v3.0)

- **I1 — Open by default.** Code is MIT. Published databases and structured data are ODbL 1.0; contributed photos are CC BY-SA 4.0. Model weights are released openly with model cards. Anyone can self-host the full stack on free tiers. _Check:_ license files, dataset-card license blocks, and a default deployment with no paid dependency.
- **I2 — The contribution unit is a finalized, geotagged photo set** captured per the standard protocol (§5): shots A and B are required, shot C is optional. It can be submitted from the GSIP phone app or, with no install, from the web capture app. A submission enters QA status aggregation only after its owner finalizes it with both required shots. _Check:_ the finalize function refuses a submission without shots A and B.
- **I3 — Existing soil maps are priors, never truth.** SoilGrids, SSURGO and WoSIS values are weak labels with stated uncertainty. A location without a prior (SoilGrids masks built-up land, for example) records "no prior"; GSIP never fabricates a prior and never retries a definitive empty answer. _Check:_ parser tests for null responses; prior jobs reach a terminal state.
- **I4 — Confirmed lab results are gold labels.** Lab-paired results anchor calibration and are tracked separately from weak labels at every pipeline stage, including the sealed holdout of I15.
- **I5 — Every output is a probabilistic estimate with uncertainty.** GSIP never claims to be a "soil test". UI copy, API responses and docs carry intervals and the basis of each estimate (image, prior, nearby gold labels). _Check:_ the language guard in `scripts/check-language.mjs`, and mandatory interval fields in every estimate schema.
- **I6 — Consented requests feed the flywheel.** A photo submitted for an estimate enters the dataset, subject to QA and the contributor's grant. An agent's request enters only under its human of record's grant (I9). _Check:_ export refuses photos without an immutable grant.
- **I7 — Contributor location privacy is protected.**
  - Precise coordinates are private operational data and never enter a public artifact.
  - Public artifacts locate an observation by an H3 cell generalized for k-anonymity: it is published at the finest of resolutions 8 (about 0.74 km²), 6 (about 36 km²) and 4 (about 1,770 km²) whose published cell aggregates observations from at least **k = 3 distinct contributors**. An observation that qualifies at none of them is withheld until it does.
  - No public field may locate an observation more precisely than its published cell, by value as well as by name. Point-level values sampled from public rasters (SoilGrids priors, elevation) and scores derived from GPS accuracy are therefore never released per observation: matched against the public rasters, eight prior properties pinpoint a 250 m pixel.
  - External processors (ISRIC, USDA, Open-Meteo) receive only the centre of the observation's resolution-9 cell (about 0.1 km²), never the precise point.
  - Original uploads exist only in a short-lived private quarantine with an independent cleanup schedule. Ingest strips EXIF/XMP/ICC before promotion, keeping only allowlisted non-location fields in private metadata; export strips again and asserts that no metadata remains.
  - A contributor can withdraw contributions and delete their account; withdrawn observations leave the private store and every later release.
  - _Check:_ pgTAP privacy tests, export assertions on rows and image bytes, and k-anonymity tests on the published cells.
- **I8 — Junk cannot pollute the dataset.** Every submission passes an automated QA gate before it is labeled, published or trained on. The gate judges the soil region; the reference card is masked out so it cannot dominate the scores. Rejected submissions are retained, flagged, for QA-model training only. _Check:_ fixture tests in which a sharp card beside blurred soil fails.

### Humans and agents (I9–I15, new in v3.0)

- **I9 — Human of record.** Every agent acts for an accountable person or organization that accepted the terms. Agents never accept terms or licenses themselves. Agent credentials are scoped, revocable and rate-limited per human of record. _Check:_ a credential without an operator cannot write, and revoking the operator revokes its agents.
- **I10 — Provenance rises only with evidence.** Every observation, photo and label records its actor kind (human, agent, device, lab), ingest path, capture method, software or model version, and a provenance tier. The server assigns tiers; they rise through corroboration, attestation, verification or lab pairing, never by a client's assertion. _Check:_ client roles cannot write tier columns; export and training filter on tier.
- **I11 — Synthetic never passes as field data.** Generated, simulated or seeded media live in labelled partitions. They never enter field-truth training, the public field dataset or the map's observation layers. _Check:_ export asserts tier and synthetic status on every row.
- **I12 — Agents see no more than the public.** Agent read and verification interfaces expose only what anonymous users or released datasets already expose. No agent role reads precise geometry, raw uploads or private metadata. _Check:_ agent interfaces run as the anonymous database role, and the anonymous pgTAP tests cover them.
- **I13 — Labels are claims.** Every human or agent judgment is stored with its author, method or model version and confidence, then combined by a documented consensus model. That model learns each rater's reliability from hidden gold questions and counts raters from one model family as one. Deterministic QA checks are versioned code, recorded with their version, and exempt from consensus. _Check:_ consensus tests with planted correlated raters (Phase 2).
- **I14 — Bounded throughput.** Every actor and every human of record has quotas. Agent volume can never starve human contributors, exceed upstream fair-use limits or dominate a cell's evidence. _Check:_ database-enforced quotas and the upstream token bucket (§5).
- **I15 — Held-out truth stays held out.** A sealed gold holdout is reachable only through an evaluation service. Its labels never appear in releases, prompts or agent-visible APIs; its photos may. _Check:_ export asserts that no holdout label is present.

## 3. System overview

```
 GSIP phone app (Capacitor)      Web capture (PWA)      Agents and tools
        │  photos + GPS + protocol metadata                 │ public reads (anon role)
        ▼                                                    ▼
 Supabase: Postgres + PostGIS + RLS · private Storage · Auth · Edge Functions
        │                │                               gsip-public: REST + MCP
        │                └─ prior-attach → ISRIC · USDA · Open-Meteo (r9 cell centre)
        ▼
 Ingest QA (sanitize → soil-region checks → promote) → finalize → settle status
        ▼
 Export (k-anonymous cells, set-aside report) → Hugging Face dataset → h3_cells
        ▼
 Training (PyTorch, uncertainty-aware) → model cards on HF Hub → inference
        ▼
 Map (MapLibre + PMTiles): prior layers · contribution cells · correction · Most Wanted
```

The QA and export workers are the only bridge from private to public data. Agent interfaces read public surfaces only (I12).

## 4. Engineering decisions (with rationale)

| Decision                | Choice                                                                                                                                         | Rationale                                                                                                                                                                                                       |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Capture clients         | **GSIP phone app**: the capture PWA wrapped with **Capacitor** for iOS and Android; the same build ships as the web PWA                        | One TypeScript codebase for the web and both stores. Native plugins add camera control, background upload, notifications and platform attestation. The no-install web path stays for reach (I2).                |
| Languages               | **TypeScript + Python, exclusively**                                                                                                           | TS for user-facing code, Edge Functions and agent interfaces; Python for pipeline and ML. Flutter/Dart must never reappear.                                                                                     |
| Backend                 | **Supabase** (hosted for the canonical instance)                                                                                               | Postgres + PostGIS + private Storage + Auth + RLS with no custom server. Anonymous contribution uses Supabase Anonymous Sign-Ins (the `authenticated` role). Supabase is open source, so I1 self-hosting holds. |
| Geospatial indexing     | **H3**                                                                                                                                         | Uniform-area aggregation, k-anonymous publication (I7), prior caching at resolution 9, active-learning scores and cheap tiling share one index.                                                                 |
| Priors                  | **SoilGrids v2** (global 250 m), **SSURGO** via Soil Data Access (US), **WoSIS**, **OSSL**                                                     | Public, free and citable. Lookups are cached per resolution-9 cell and paced by a database token bucket to honour ISRIC's fair-use limit (5 calls a minute).                                                    |
| Agent interfaces        | **`gsip-public` Edge Function**: REST with OpenAPI and an MCP server (Streamable HTTP), plus `llms.txt` and a prerendered site                 | Agents get typed, cited, public-only data (I12) with no new language and no paid service. The function uses the publishable key, so the database's anonymous grants bound what it can read.                     |
| Provenance              | **Server-assigned provenance tiers** on submissions and photos                                                                                 | I10 and I11: evidence raises tiers; clients cannot. Synthetic rows sit below field data.                                                                                                                        |
| ML stack                | **PyTorch + timm** (ConvNeXt-Tiny to start), multi-task heads, ONNX export                                                                     | Small enough to retrain nightly on one GPU and eventually run on-device.                                                                                                                                        |
| Model & dataset hosting | **Hugging Face Hub / Datasets** under a GSIP org                                                                                               | Free hosting, versioning and model cards. Releases ship as Parquet; photo shards before 10,000 submissions (one folder per submission does not scale on the Hub).                                               |
| Map                     | **MapLibre GL + PMTiles**; prior tiles coloured from a versioned palette that also draws the legends                                           | Serverless and open. One palette file prevents the legend and the tiles from disagreeing.                                                                                                                       |
| CI/CD and workers       | **GitHub Actions** (tests, Pages deploy, scheduled workers)                                                                                    | Free for public repositories. Scheduled workers move to an event-driven queue when volume requires it (GitHub delays cron runs under load and disables them after 60 days without repository activity).         |
| Repo structure          | **Monorepo** `gsip`: `apps/capture-pwa`, `apps/map-web`, `apps/site-web`, `packages/schema`, `supabase/`, `pipeline/`, `ml/`, `card/`, `docs/` | One clone is the whole project.                                                                                                                                                                                 |

## 5. Capture protocol (v1.1)

The protocol is the biggest determinant of dataset quality. It must stay cheap enough for anyone, worldwide.

**The GSIP Reference Card** — a free, printable A6 card (colour and black-and-white editions) with 8 colour patches plus neutral grey, an ArUco marker (`DICT_4X4_50`, ID 7) for detection, scale and perspective, a 20 mm scale line, and printed protocol reminders.

**Shot sequence per submission:**

1. **Shot A — context (required):** undisturbed ground from about 30 cm, card in frame.
2. **Shot B — fresh face (required):** scrape 2–3 cm to expose fresh soil; close-up from about 15 cm, card in frame. _(Primary analysis image.)_
3. **Shot C — texture (optional):** moistened soil ball or ribbon in hand. Judged on its own: a failed shot C is left out of the release and never fails the submission.

**Where and how to sample:** only where you have permission to dig; never in protected areas, on graves or archaeological sites, or near buried utilities; replace the scraped soil. Classroom contributions run under a teacher of record. The legal pack (WP-6d) sets the age policy.

**Recorded metadata:** GPS position with accuracy radius and its source (device GPS or manual pin), capture time of shot B as recorded by the device, device model, and allowlisted non-location camera fields extracted at ingest. Raw EXIF/XMP/ICC is never retained. **One-tap prompts:** land cover (7 icons), surface condition (dry/moist/wet), disturbed (yes/no). **Public attribution:** defaults to the pseudonym "Anonymous soil contributor". Capture warns that a typed name is published with the observation's area and date. **Auto-enriched at ingest:** precipitation in the 3 days before capture (Open-Meteo forecast API, or its archive API for older captures) and elevation (Copernicus GLO-90 via the Open-Meteo Elevation API), both queried at the resolution-9 cell centre.

**Card-less submissions are accepted** but marked "uncalibrated" and down-weighted in training. Never reject a willing contributor; grade the data instead.

**Finalize:** after uploading, the client calls `finalize_submission`, which records `finalized_at` once shots A and B exist. QA processes each photo as soon as it arrives (so raw uploads leave quarantine quickly) and settles the submission's status only after finalize.

**QA gate (I8), per photo, in order:**

1. is-soil classifier _(ML; joins in Phase 2)_.
2. Soil region: the card is located from the marker homography and masked with a margin; at least 20 % of the frame must remain as soil.
3. Sharpness and exposure on the soil region only.
4. Card detection and colour-patch extraction ("calibrated" or "uncalibrated").
5. GPS plausibility: an accuracy radius above 250 m, or a gross mismatch with the priors, routes to human review; a missing radius scores as unknown and passes.
6. Near-duplicate perceptual hash on the soil region; a match routes to human review, never to rejection.

Before stripping, ingest applies the EXIF orientation and converts embedded colour profiles (Display P3, for example) to sRGB, recording only the source colour-space class privately. Thresholds are provisional until the 50-photo field pilot calibrates them.

**Status settlement** (`settle_submission`, the single source of truth):

| Shots A and B (both required)                             | Submission status |
| --------------------------------------------------------- | ----------------- |
| Either missing, or either still in QA                     | `pending`         |
| Either failed soil region, sharpness, exposure or is-soil | `qa_fail`         |
| Either flagged for review, or QA errored                  | `flagged`         |
| Both passed                                               | `qa_pass`         |

**Upstream fair use (I14):** prior lookups are cached per resolution-9 cell; each upstream source has a database token bucket (SoilGrids: one call at a time, at most 5 a minute). Claiming a job and paying for its calls is one atomic step, so a request that cannot be claimed or must wait spends nothing and consumes no attempt. Owners can start only their own unstarted job; only the service worker retries.

## 6. Data schema (Postgres/PostGIS, canonical)

```
contributors        id, auth_uid, handle, reputation, created_at
contribution_grants id, contributor_id, terms_version, accepted_at,
                    data_license, photo_license, attribution_name     (immutable)
submissions         id, contributor_id, grant_id, geom_precise (PRIVATE),
                    h3_r8, h3_r6 (server-derived), captured_at, land_cover,
                    surface_condition, disturbed, device_model, gps_accuracy_m,
                    location_source, precip_flag, elevation, finalized_at,
                    status (pending|qa_pass|qa_fail|flagged), is_synthetic,
                    actor_id, ingest_path, capture_method, provenance_tier
photos              id, submission_id, shot_type (A|B|C), storage_path (path-bound),
                    camera_metadata_private jsonb, capture_evidence_private jsonb,
                    card_detected, card_color_correction jsonb, calibration_status,
                    sharpness_score, perceptual_hash, qa_status, provenance_tier
priors              submission_id, source (soilgrids|ssurgo|wosis), property,
                    value, unit, uncertainty_lo, uncertainty_hi,
                    depth_top_cm, depth_bottom_cm, retrieved_at
gold_labels         id, submission_id, lab_name, method, property, value, unit,
                    uncertainty, depth_top_cm, depth_bottom_cm, verified_by,
                    document_ref, holdout
predictions         id, submission_id, model_version, property, value, unit,
                    ci_lo, ci_hi, basis (image|prior|fused|neighbors)
qa_events           submission_id, check_name, passed, score, model_version
h3_cells            h3_index, resolution (4|6|8), n_submissions, n_contributors (>= 3),
                    n_gold, latest_submission_date, prior_uncertainty,
                    model_disagreement, acquisition_score, updated_at
actors              id, kind (human|agent|device|lab), operator_id, contributor_id,
                    model_family, model_version, status
service_state       capture_open (single row; default closed)
prior_jobs, qa_jobs durable work queues (server only)
prior_cell_cache    h3_r9, source, payload, retrieved_at (server only)
upstream_buckets    source, tokens, capacity, refill_per_minute (server only)
deletion_requests   contributor_id, kind, requested_at, status (owner-visible)
grant_withdrawals   grant_id, request_id, withdrawn_at, reason (append-only)
attribution_reviews contributor_id, attribution_name, decision, reviewer (server only)
dataset_releases    version, released_at, rows, photos, hf_revision (public)
```

**Property naming and units:** canonical names `soc|ph|clay|sand|silt|bd|cec|n`; `g/kg` for SOC, clay, sand, silt and N; `pH` for pH; `kg/dm3` for bulk density; `cmol(+)/kg` for CEC. Depth is `0 <= depth_top_cm < depth_bottom_cm <= 200`. Source codes and units are converted at ingest by one typed mapping in `packages/schema`. The SoilGrids 0–30 cm interval is a thickness-weighted average of layer quantiles: a conservative (wider than exact) bound, documented as such.

**Photo storage paths** are bound by the database to `{auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg`, where `auth_uid` belongs to the submission's contributor. Workers re-derive the expected prefix from database facts and refuse any mismatch.

**Public dataset export (nightly → Hugging Face):** database and structured data under ODbL 1.0; photos under CC BY-SA 4.0. A release includes only non-synthetic, `qa_pass` submissions at provenance tier 0 or above with a recorded, unwithdrawn grant, and of those only photos whose own QA passed. Each row carries its k-anonymous `h3_cell` and `h3_resolution`, the capture date (never the time), protocol metadata, location source, provenance tier, non-holdout gold labels and per-photo QA checks. Point-level priors stay private (I7): anyone can sample SoilGrids for a published cell, and cell-level priors join releases with the Phase 2 file sampler. QA checks derived from location (GPS plausibility) are released as pass or fail without their score. A row that fails a per-row data check (a missing photo object, for example) is set aside in a private export report and the release continues. The release aborts instead on any privacy assertion failure (metadata found, a forbidden field present, a photo path that does not match its owner), on infrastructure errors (Storage or database outages), and when more than 10 % of rows would be set aside, so that an outage can never publish a hollowed-out release. Each successful push records a `dataset_releases` row.

**Contribution terms:** submitting grants GSIP permission to include structured data in the ODbL 1.0 database and to publish photos under CC BY-SA 4.0; the contributor keeps ownership. Acceptance is snapshotted immutably in `contribution_grants`; every submission references exactly one grant. A later terms version creates a new grant. Withdrawal never rewrites a grant: it appends a `grant_withdrawals` row the moment the contributor asks, every later release excludes the withdrawn grant's observations, and a withdrawn grant accepts no new submission. The one change a grant ever undergoes is on account deletion, when the attribution name on the deleted account's withdrawn grants is replaced with the default pseudonym; its identifier, terms version, date and licenses remain as the record of what was granted. Relicensing is permitted only to more open licenses. The terms, privacy notice, processor list, age policy and withdrawal procedure require legal review before public launch.

**Private upload lifecycle:** the client signs in (permanently or anonymously), creates its grant and a pending submission, uploads to `incoming-photos/{auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg`, inserts the photo rows, and finalizes. Ingest QA sanitizes, promotes to the private `submission-photos` bucket and deletes the quarantine object. A separate hourly job deletes quarantine objects older than 24 hours; failed sanitization never promotes an object. Every insert along this path requires `service_state.capture_open`.

## 7. ML architecture

**Model 1 — QA gate:** lightweight classifier (MobileNetV3) trained on pass/fail submissions; server-side at ingest, later in-browser (ONNX/WebGPU) for instant capture feedback.

**Model 2 — Soil estimator:** shared vision backbone over card-corrected shot B (shot A as an auxiliary input), plus a tabular branch for priors and context. Multi-task heads:

| Head          | Target                                        | Label source                       | Honest expectation                                                                          |
| ------------- | --------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------- |
| Munsell color | hue/value/chroma                              | derived from card-corrected pixels | near-deterministic with card                                                                |
| Texture class | 12-class USDA triangle (coarse 3-class first) | weak: priors; gold: lab PSA        | 70–90 % coarse-class published range                                                        |
| SOM/SOC       | continuous + CI                               | weak: SoilGrids; gold: lab         | moderate; moisture confound handled via surface-condition input                             |
| pH, CEC, N    | continuous + CI                               | weak priors, gold anchors          | **inference via correlation only** — always wide CIs, always labeled as fused estimate (I5) |

**Label tiers:** weak labels (priors) < silver labels (simple tests a photo can verify, such as jar sedimentation, a vinegar fizz test or pH strips read against the card) < gold labels (lab results). Weak labels enter the loss weighted by inverse prior variance; gold labels get full weight. Heteroscedastic heads plus conformal calibration on the sealed gold holdout (I15). Training uses provenance tier ≥ 0 field data only (I11).

**Fusion at inference:** posterior = image evidence × location prior × nearby gold-label kriging. The API returns the decomposition (`basis`) so the map and UI can show why an estimate is what it is.

**Active learning and credit:** the target is information gain, the expected drop in map uncertainty at a cell. It replaces the v2 heuristic `acquisition_score` once models exist, and it drives the Most Wanted layer and contribution credit ("soil bits", non-transferable).

**Retraining cadence:** nightly fine-tune, weekly full retrain, every release versioned on the Hub with a model card reporting gold-holdout metrics. No silent model swaps.

## 8. Map system

Layers, all MapLibre + PMTiles, all reproducible from the pipeline:

1. **Prior layers** — SoilGrids properties coloured with `gdaldem color-relief` from the versioned palette in `packages/schema`, with transparent nodata. Legends are drawn from the same palette. Archives are stamped with the palette version and published under it, and a deploy fails unless they match the palette the legends use. When no tile archive is configured, the map falls back to ISRIC's WMS and shows ISRIC's own legend.
2. **Contribution layer** — k-anonymous H3 cells at resolutions 4, 6 and 8, finer cells drawn above coarser ones. Popups show the observation count, the resolution and the latest date; never a point.
3. **Fused correction layer** (Phase 3) — where GSIP's model diverges from priors, with confidence. _This layer is the product._
4. **Most Wanted layer** (Phase 2–3) — information-gain targets, excluding protected areas and framed as "if you have access" (§9).
5. **Gold anchor layer** — lab-confirmed observations under the same k-anonymous cells as layer 2.

## 9. Agents

Agents join in order of risk. Each role sees no more than it needs, and an assistant acting for a person keeps that person as contributor of record (I9).

| Role              | What the agent does                                                  | What it may touch                                           | Phase |
| ----------------- | -------------------------------------------------------------------- | ----------------------------------------------------------- | ----- |
| Reader            | Answers questions about a place: protocol, coverage, releases        | Public cells and released data, as the anonymous role (I12) | 1.5   |
| Capture assistant | Guides a person through the protocol and submits for them            | That person's submissions through a delegated, scoped token | 1.5b  |
| Coordinator       | Plans Most Wanted outings and classroom campaigns                    | Public data and campaign tools, within land-access rules    | 2     |
| Verifier          | Labels released photos (soil or not, card visible, Munsell, hazards) | Released photos, with hidden gold questions (I13)           | 2     |
| Scientist         | Trains models and scores them against the sealed holdout             | Released data and the evaluation service (I15)              | 3     |
| Autonomous sensor | A robot, drone or field station submits its own observations         | A write path that requires device attestation (I10)         | 4     |

**Interfaces.** WP-AGENT-1 ships the reader interfaces: the `gsip-public` Edge Function (REST with OpenAPI, and an MCP server over Streamable HTTP with the tools `get_protocol`, `get_cell`, `list_cells` and `get_release`), `llms.txt`, and a prerendered site with Dataset JSON-LD. Later phases add delegated capture (`start_observation`, `finalize_observation`, `list_my_observations`, never returning coordinates), a task API for verifiers, and the evaluation service.

**Rules for every agent interface.** Public reads run as the anonymous role. Free text that people wrote (attribution names, for example) is returned only inside fields marked untrusted, never as instructions. Responses carry license and citation fields. Most Wanted targets exclude protected areas, private land and hazards, are framed as "if you have access", and are never routed to minors. Photos with no human author may not be copyrightable; counsel selects their license class before Phase 4.

## 10. Governance & community

- GitHub org `global-soil-intelligence`, monorepo `gsip`, public roadmap, discussions on.
- Steward: Viridis LLC, bound by the business guardrails B1–B8 and the conflict rules in `GOVERNANCE.md`. Names and marks are covered by `TRADEMARKS.md`; the licenses cover code and data, not the marks.
- DCO sign-off on human commits. Agent-authored changes carry a co-author trailer and are adopted, reviewed and signed off by a human of record; an agent never certifies the DCO.
- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `GOVERNANCE.md` (product owner during bootstrap → advisory council → steering group as the community grows).
- Data partnerships: university soil labs, extension programs, master-gardener networks, schools and NGOs supply gold labels and campaigns. Partner labs get bulk CSV ingestion for `gold_labels`.

## 11. Phased roadmap

**Phase 0 — Foundation.** Done (WP-0 to WP-2, merged 2026-10-01).

**Phase 1 — Capture + map, zero ML.** Code done (WP-3 to WP-6). **Phase 1.1 — Launch hardening** (WP-6b to WP-6e) fixes the review's launch blockers and lands the agent-era schema (I9–I11) while production holds little or no real data, because adding provenance later costs a backfill of every row.
_Launch gates (all required before `capture_open` is set):_ WP-6b to WP-6e merged; legal pack approved by counsel; the 50-photo field pilot calibrates QA thresholds; prior PMTiles published; production Supabase on a paid tier with workers green; the canonical domain serves the crawlable site. **The legal review, not the code, sets the launch date.**

**Phase 1.5 — App and agent readers.** The GSIP phone app (WP-APP-1) and the read API, MCP server and prerendered site (WP-AGENT-1). Read-only agent pieces can ship before launch because they touch no contributor data. Phase 1.5b, after launch: delegated capture for assistants.

**Phase 2 — First models.** QA gate model; estimator v0 (colour, coarse texture, SOM) on weak labels; silver-label protocols; verifier task API with consensus (I13); nightly retrain with model cards; SoilGrids file sampler replacing the REST dependency.
_Done when:_ gold-holdout coarse-texture accuracy ≥ 70 % and SOM intervals reach ≥ 90 % empirical coverage.

**Phase 3 — The flywheel closes.** Estimate API and UI, evaluation service, gold-kit partner labs, fused correction layer, Most Wanted layer and contribution credit.
_Done when:_ estimate requests convert to dataset entries at > 80 % and the correction layer beats SoilGrids at gold points.

**Phase 4 — Scale.** On-device inference, i18n, regional model heads, attested autonomous sensors, hardware-partner integrations, and an academic paper on the dataset and method.

## 12. Risks & mitigations

| Risk                                          | Mitigation                                                                                                                                      |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Weak-label noise ceiling                      | Uncertainty-weighted loss (I3), silver and gold anchoring (I4), conformal calibration; report holdout metrics only (I15).                       |
| Photo confounders (moisture, light, profiles) | Reference card, soil-region QA, sRGB conversion at ingest, surface-condition input, capture-time precipitation flag.                            |
| Junk or adversarial submissions               | QA gate (I8), GPS plausibility, provenance tiers (I10), quotas (I14), near-duplicate review.                                                    |
| Synthetic imagery posing as field data        | I11 partitions, server-assigned tiers, attestation for higher tiers, C2PA verification before metadata stripping (Phase 2+).                    |
| Correlated or colluding raters                | I13 consensus counts one model family as one vote and learns reliability from hidden gold questions.                                            |
| Prompt injection through public text          | Untrusted-text fencing in agent interfaces; attribution names constrained and moderated (WP-6b, WP-6d).                                         |
| Re-identification of named contributors       | Pseudonymous default, a warning before a real name is used, k-anonymous cells (I7). Sybil inflation of k is bounded by quotas and QA; residual. |
| Cold start                                    | Prior layers useful on day one; launch region with partners; Most Wanted gives purpose; the app answers "what soil is under me?" from priors.   |
| Upstream dependency (SoilGrids REST is beta)  | Cell cache, token bucket, "no prior" terminal state; Phase 2 file sampler.                                                                      |
| App-store rejection or account-deletion rules | Native camera, offline queue and notifications in version 1; in-app deletion request backed by WP-6d.                                           |
| Steward trust                                 | B1–B8 with checks, open books, trademark limits, and the right to fork.                                                                         |
| Overclaiming accuracy                         | I5 in UI copy, API schemas and model cards. "Estimate", never "test".                                                                           |

## 13. Success metrics

Flywheel health: finalized submissions a week, QA pass rate, contributor 30-day retention, gold and silver labels a month, app installs that become contributors.
Science: coarse-texture accuracy and SOC RMSE on the holdout, interval coverage, share of cells where the fused layer beats the prior at gold points.
Community and agents: external contributors merged, partner labs onboarded, dataset downloads and citations, agent integrations operating under a human of record, share of verified labels from agents.

## 14. Changelog

- **v3.0 (2026-10-10):** humans and agents. Added I9–I15. Amended I2 (finalize with required shots A and B; app or web), I3 ("no prior" is terminal), I6 (agents contribute only under a human of record's grant), I7 (k = 3 distinct-contributor publication at resolution 8 → 6 → 4; processors receive resolution-9 cell centres; withdrawal and deletion; independent quarantine cleanup) and I8 (soil-region QA with the card masked). §4 moves the Capacitor phone app from Phase 4 to Phase 1.5 as the main funnel and adds agent interfaces, provenance tiers and palette-driven tiles. §5 adds the finalize step, settlement table, sampling rules, capture-time precipitation, colour handling and upstream fair use. §6 adds path binding, per-photo QA status, provenance, the capture gate, withdrawals, releases and the holdout flag, and makes export set aside bad rows instead of aborting. §8 adds palette legends and multi-resolution contribution cells. New §9 Agents. §10 adds the steward, guardrails, trademarks and human-of-record DCO. §11 adds Phase 1.1 launch hardening, launch gates and Phase 1.5.
- **v2.2 (2026-07-22):** anonymous contribution pinned to Supabase Anonymous Sign-Ins; immutable `contribution_grants` referenced by every submission; canonical units and depth bounds; private Storage path, metadata allowlist, fail-closed promotion and 24-hour quarantine cleanup.
- **v2.1 (2026-07-22):** I7 made fail-closed; ODbL data separated from CC BY-SA photos with a legal-review gate; elevation source pinned; QA gate phased; canonical property mapping; legacy-repo disposition.
- **v2.0 (2026-07-22):** initial citizen-science architecture; superseded all 2024 documents.

---

_Licensing: code MIT · databases/structured data ODbL 1.0 · contributed photos CC BY-SA 4.0 · models open weights with model cards. Contribution terms require legal review before public launch._
