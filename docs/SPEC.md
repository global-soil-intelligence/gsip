# GSIP v7 — Open Soil Spectral Library Specification

**Project:** Global Soil Intelligence Project (globalsoilintelligence.com)
**Version:** 7.0 proposed — 2026-10-12
**Status:** v5 library foundation and v6 private-intake specification are merged under Justin's 2026-10-12 owner authorization. v7 clarifies additive rights-worker integration and durable refusal identities in §16.7; it becomes active after review and merge. Library intake implementation remains separate. Earlier authorized production gates are tracked separately in deployment receipts; no library intake deployment is established by these code or specification merges. No production migration, deployment, publication, worker dispatch or capture opening is authorized.
**Scope:** the open soil spectral library is primary; smartphones are the accessible capture and sample-linking tool. Maps and models are downstream products. Earlier spectroscopy documents are references, not implemented protocols or evidence of measurement accuracy.
**Owner:** Justin Hart, Viridis LLC (steward; see `GOVERNANCE.md`)
**Hosting:** GitHub (org monorepo) · Supabase (canonical instance) · Hugging Face (open dataset and models)

---

## 1. Mission

Build an open, geographically connected soil spectral reference library using smartphones as the widely accessible capture tool. Connect soil observations and their metadata to measured spectra and independently verified laboratory results. Use that growing evidence base to train and evaluate open AI models, build the soil map, and investigate relationships relevant to the soil biome.

The library is the primary research asset. The map is its geographic view, and AI models are reproducible interpretations of evidence. A smartphone captures guided images, context and sample identity; it can also connect a physical sample to an external instrument or laboratory record. A normal RGB camera records three broad channels, not a wavelength-resolved reflectance spectrum. Neither photographs nor spectra alone establish soil chemistry or biological composition. Spectral reconstruction and biological predictions require paired reference measurements and independent evaluation, and must remain labeled estimates.

**Library chain:** smartphone observation → private sample identity and metadata → camera optical record and/or instrument spectrum → paired laboratory evidence → rights-eligible training data → evaluated open models → privacy-preserving map.

People, schools, labs and developers can contribute to and build on the open code under a human of record. Viridis LLC stewards the canonical service under B1–B8. Independent local library nodes can organize private sample records; synchronization with the canonical service requires the separately scheduled authorization and rights protocol. A local import never confers canonical acceptance, QA clearance, consent verification or publication eligibility.

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
  - A contributor can withdraw contributions and delete their account; withdrawn observations leave the private store and every release built after the request, and nothing a request covers can be submitted again from any device.
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
                    actor_id, ingest_path, capture_method, client_version,
                    provenance_tier
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

**Client-callable database functions:** GSIP functions in an exposed Data API schema that `anon` or `authenticated` can call use `SECURITY INVOKER`. `capture_is_open()` reads only the already-readable `service_state.capture_open` column. The singleton primary key and `CHECK (singleton)` enforce at most one row; an absent row returns false. Clients gain no access to the singleton column and cannot change the gate.

The privileged bodies of `finalize_submission(uuid)`, `current_auth_user_exists()` and `my_submission_accepts_uploads(text)` live in the non-exposed `private` schema as `SECURITY DEFINER` functions with an empty pinned `search_path`. Their ownership, required-photo, existing-auth-user and grant-withdrawal guards remain unchanged. The same public signatures dispatch through SQL-standard, definition-time bound `RETURN` bodies with caller privileges. These wrappers resolve their private callees when defined and record the dependency, so callers need no `USAGE` or `CREATE` on `private`. Each private callee grants only the execution needed by its existing public callers: authenticated finalization; authenticated and service-role auth-existence and upload checks; no anonymous execution of these three helpers. Public function caller grants, table and column privileges remain unchanged, including the existing service-role upload-helper grant. `private` must remain excluded from the Data API's exposed schemas.

`grant_withdrawals` and `attribution_reviews` retain RLS and their service-only table privileges, with explicit restrictive policies denying all client operations even if a permissive policy and client grant are accidentally added. Existing service operations, append-only protections and ownership guards remain effective. Additive migrations must prove these boundaries through role tests and a fresh security-advisor result with zero findings; they never suppress a finding or open capture.

**Property naming and units:** canonical names `soc|ph|clay|sand|silt|bd|cec|n`; `g/kg` for SOC, clay, sand, silt and N; `pH` for pH; `kg/dm3` for bulk density; `cmol(+)/kg` for CEC. Depth is `0 <= depth_top_cm < depth_bottom_cm <= 200`. Source codes and units are converted at ingest by one typed mapping in `packages/schema`. The SoilGrids 0–30 cm interval is a thickness-weighted average of layer quantiles: a conservative (wider than exact) bound, documented as such.

**Photo storage paths** are bound by the database to `{auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg`, where `auth_uid` belongs to the submission's contributor. Workers re-derive the expected prefix from database facts and refuse any mismatch.

**Public dataset export (nightly → Hugging Face):** database and structured data under ODbL 1.0; photos under CC BY-SA 4.0. A release includes only non-synthetic, `qa_pass` submissions at provenance tier 0 or above with a recorded, unwithdrawn grant, and of those only photos whose own QA passed. Each row carries its k-anonymous `h3_cell` and `h3_resolution`, the capture date (never the time), protocol metadata, location source, capture method, provenance tier, non-holdout gold labels and per-photo QA checks. Point-level priors stay private (I7): anyone can sample SoilGrids for a published cell, and cell-level priors join releases with the Phase 2 file sampler. QA checks derived from location (GPS plausibility) are released as pass or fail without their score. A row that fails a per-row data check (a missing photo object, for example) is set aside in a private export report and the release continues. The release aborts instead on any privacy assertion failure (metadata found, a forbidden field present, a photo path that does not match its owner), on infrastructure errors (Storage or database outages), and when more than 10 % of rows would be set aside, so that an outage can never publish a hollowed-out release. Each successful push records a `dataset_releases` row.

**Contribution terms:** submitting grants GSIP permission to include structured data in the ODbL 1.0 database and to publish photos under CC BY-SA 4.0; the contributor keeps ownership. Acceptance is snapshotted immutably in `contribution_grants`; every submission references exactly one grant. A later terms version creates a new grant. Withdrawal never rewrites a grant: it appends a `grant_withdrawals` row the moment the contributor asks, and every release built after that excludes the withdrawn grant's observations (the export re-reads withdrawals just before publishing). A request covers everything accepted up to it: a grant accepted at or before a request is refused, as is any grant once an account deletion is requested, and a withdrawn grant accepts no submission, photo or upload. Clients send a queued observation only as the account it was made under; a deleted account's tokens cannot recreate a contributor. The one change a grant ever undergoes is on account deletion, when the attribution name on the deleted account's withdrawn grants is replaced with the default pseudonym; its identifier, terms version, date and licenses remain as the record of what was granted. Relicensing is permitted only to more open licenses. The terms, privacy notice, processor list, age policy and withdrawal procedure require legal review before public launch.

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

_Photo-publication gate (merged v4.0; every newly built release):_ no photo publication until WP-6f is deployed and Justin has approved its calibration evidence. Until then, releases contain structured data only, with empty photo lists and no public photo bytes, shards, thumbnails or URLs. Eligible data still passes the existing QA, consent, withdrawal, provenance, holdout and k-anonymity gates. This gate does not open capture or authorize deployment; previously published immutable releases are identified honestly rather than claimed erased.

**Phase 1.5 — App and agent readers.** The GSIP phone app (WP-APP-1) and the read API, MCP server and prerendered site (WP-AGENT-1). Read-only agent pieces can ship before launch because they touch no contributor data. Phase 1.5b, after launch: delegated capture for assistants.

**Phase 2 — Library and paired evidence first (§16), then first models.** QA gate model; estimator v0 (colour, coarse texture, SOM) on weak labels; silver-label protocols; verifier task API with consensus (I13); nightly retrain with model cards; SoilGrids file sampler replacing the REST dependency.
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
| App-store rejection or account-deletion rules | Native camera, offline queue and local sync reminders in version 1; in-app deletion request backed by WP-6d.                                    |
| Steward trust                                 | B1–B8 with checks, open books, trademark limits, and the right to fork.                                                                         |
| Overclaiming accuracy                         | I5 in UI copy, API schemas and model cards. "Estimate", never "test".                                                                           |

## 13. Success metrics

Flywheel health: finalized submissions a week, QA pass rate, contributor 30-day retention, gold and silver labels a month, app installs that become contributors.
Science: coarse-texture accuracy and SOC RMSE on the holdout, interval coverage, share of cells where the fused layer beats the prior at gold points.
Community and agents: external contributors merged, partner labs onboarded, dataset downloads and citations, agent integrations operating under a human of record, share of verified labels from agents.

## 14. Changelog

- **v6.0 proposed (2026-10-12):** specifies owner-private, unverified library intake and splits WP-LIB-4 into shared contract/parser (4A), additive hosted RPC/rights/holdout enforcement (4B) and compatible phone queue/form integration (4C). Local declarations cannot confer hosted authority. Original instrument files, physical-pair verification, scientific adapters, field training, federation and public releases remain outside these packages; all activation gates default closed.

- **v5.0 proposed (2026-10-12):** makes the open soil spectral library primary, smartphones the capture/linking tool, and maps/models downstream. Adds L1–L7 and WP-LIB-1 through WP-LIB-7; preserves capture and photo-publication gates. Local preparation is authorized, production remains separately gated.

- **v4.0 (2026-10-12; specification merged in #38):** proposed §11 photo-publication gate and §15 schedule WP-APP-2A (CI versions, reproducibility evidence and private-storage backup exclusions), WP-APP-2B (local sync reminders only in version 1) and WP-6f (per-photo privacy screening). Nearby suggestions wait for Most Wanted and land-access eligibility. Scene-text screening may exclude only the detected reference-card quadrilateral plus its bounded margin; face screening covers the entire frame. Start with face and scene-text screening; a dedicated plate model needs an evidenced gap and verified licenses. The publication gate is normative; photo-screening implementation and calibration remain outstanding.
- **v3.0 (2026-10-10):** humans and agents. Added I9–I15. Amended I2 (finalize with required shots A and B; app or web), I3 ("no prior" is terminal), I6 (agents contribute only under a human of record's grant), I7 (k = 3 distinct-contributor publication at resolution 8 → 6 → 4; processors receive resolution-9 cell centres; withdrawal and deletion; independent quarantine cleanup) and I8 (soil-region QA with the card masked). §4 moves the Capacitor phone app from Phase 4 to Phase 1.5 as the main funnel and adds agent interfaces, provenance tiers and palette-driven tiles. §5 adds the finalize step, settlement table, sampling rules, capture-time precipitation, colour handling and upstream fair use. §6 adds path binding, per-photo QA status, provenance, the capture gate, withdrawals, releases and the holdout flag, and makes export set aside bad rows instead of aborting. §8 adds palette legends and multi-resolution contribution cells. New §9 Agents. §10 adds the steward, guardrails, trademarks and human-of-record DCO. §11 adds Phase 1.1 launch hardening, launch gates and Phase 1.5.
- **v2.2 (2026-07-22):** anonymous contribution pinned to Supabase Anonymous Sign-Ins; immutable `contribution_grants` referenced by every submission; canonical units and depth bounds; private Storage path, metadata allowlist, fail-closed promotion and 24-hour quarantine cleanup.
- **v2.1 (2026-07-22):** I7 made fail-closed; ODbL data separated from CC BY-SA photos with a legal-review gate; elevation source pinned; QA gate phased; canonical property mapping; legacy-repo disposition.
- **v2.0 (2026-07-22):** initial citizen-science architecture; superseded all 2024 documents.

## 15. Merged v4.0 amendment: app readiness and photo privacy

**Status: merged in #38.** Justin approved the backup and screening policy specification on 2026-10-12. WP-6f implementation, detector licensing and calibration evidence remain separate requirements; the amendment does not authorize production changes. [BUILD_ORDER.md](BUILD_ORDER.md) schedules the implementation PRs.

### 15.1 Invariants and activation

I1–I15 and B1–B8 continue to hold. In particular: MIT code, ODbL 1.0 structured data and CC BY-SA 4.0 photos keep their licenses; TypeScript and Python remain the authored languages; no new paid service, closed Android SDK or push service enters the default path. Agents continue to read only public data through the anonymous role (I12). Precise locations, raw uploads, sessions and private screening evidence never enter public output, logs, issues, PRs or fixtures (I7). Fixtures use synthetic or staged material with no real contributor data and cannot enter field-truth partitions (I11).

This amendment preserves the existing §11 capture launch gates and adds its separate photo-publication gate. `service_state.capture_open` and `VITE_CAPTURE_LIVE` stay false, production anonymous sign-in stays disabled, and only Justin may open them after the launch gates. Store accounts, signing, keystores, store submission and deep-link account configuration remain Justin's actions. A green artifact build or a local notification does not authorize launch, deployment or store submission.

### 15.2 WP-APP-2A: account-free build readiness and backup policy

CI supplies the Android build number and iOS build number from a validated, bounded integer; the marketing version comes from one checked-in source. The emitted APK and simulator app must contain the declared values. The reproducibility receipt records the source commit, lockfile hashes, resolved toolchain versions, build-number input and artifact hashes without credentials or private data. Comparing two builds of the same inputs must distinguish byte-identical artifacts from a documented comparison that normalizes nondeterministic packaging metadata; a successful build alone is not reproducibility evidence. This work needs no developer account or signing material.

**Approved backup policy:** the private offline queue, photo drafts, unsynced precise points and authentication/session storage must be excluded from cloud backups. Private storage may transfer directly between Android devices only when cloud and direct-transfer rules are cleanly separated and tests establish that private bytes cannot enter cloud backup. Android 12+ may preserve the private queue/session through the explicit device-transfer channel; legacy Android mechanisms or unproven transport separation must exclude both backup and transfer. Generated rules must cover effective WebView stores and photo files and be checked in the compiled artifact. A fresh install or cloud restore starts a new anonymous account; verified direct transfer may preserve it. An old backup already held by a phone provider is outside the app's ability to retract; document this limit without claiming retroactive deletion.

**iOS remains an explicit readiness gate.** The present queue/drafts use WebKit IndexedDB and the session uses localStorage. An existing filesystem plugin's no-cloud directory does not move those stores or exclude them. Apple's [backup exclusion resource key](https://developer.apple.com/documentation/foundation/urlresourcekey/isexcludedfrombackupkey) applies to files and can need reapplication after writes; [WebKit's website data store](https://developer.apple.com/documentation/webkit/wkwebviewconfiguration/websitedatastore) controls web persistence. An ephemeral store would lose the durable offline queue. Do not infer exclusion from a plist, simulator success or an unrelated filesystem directory. Before any iOS store-readiness claim, prove a reliable exclusion method with real-device backup/restore checks using synthetic private records. The alternatives are a separately specified TypeScript storage migration into the existing no-cloud filesystem directory, or a native bridge requiring Justin's explicit exception to the language guardrail. Neither alternative is implemented or selected here. Preserve offline durability and report iOS backup protection as unverified/blocked until the relevant proof exists.

### 15.3 WP-APP-2B: local notifications in app version 1

The §12 notification promise is scheduled as local notifications. Version 1 schedules opt-in sync reminders only, about unsynced work. Nearby suggestions are deferred until Most Wanted and land-access eligibility inputs exist, with a separately reviewed follow-up specifying their use. Use the open `@capacitor/local-notifications` plugin; no push service, push token, advertising SDK or proprietary location SDK. The [candidate audit](PHOTO_PRIVACY_SCREENING.md#notification-candidate) records license, maintenance and package size; implementation must recheck the pinned version and transitive Android dependencies.

Reminder scheduling happens on the device and requires no location calculation or new location permission. Version 1 does not compute, schedule or expose nearby targets; it adds no background location, geofencing service or remote point upload. In the later follow-up, targets must obey §9 land-access/minor restrictions and cannot infer eligibility or an unobserved area from sparse or withheld public coverage. Notification permission is requested only after explicit opt-in; denial leaves the app usable.

Notifications carry generic text and opaque local identifiers, never photos, coordinates, address text, contributor names, account tokens or private queue contents. Selecting one opens the relevant in-app view subject to existing access checks. Reminders are bounded, cancellable, and cleared after sync, withdrawal, deletion, sign-out or opt-out; no repeated alerts for an empty queue. No contribution invitation is scheduled while capture is closed. No exact alarm is required: use inexact scheduling and remove `SCHEDULE_EXACT_ALARM`/`USE_EXACT_ALARM` from effective Android permissions. Add only the notification/runtime and boot/wake permissions demonstrably needed by the selected plugin, preserving the permission and closed-SDK checks. Device tests must verify permission denial, reminder cancellation and behavior with capture closed; local delivery and App Store acceptance are not guaranteed by scheduling success.

### 15.4 WP-6f: every-photo privacy screening, pending implementation approval

**Chosen outcome: withhold the flagged photo for private human review.** Screen every shot A, B and C server-side in the private QA worker, including optional, retried and legacy photos that could reach a future public release. Start with face and scene-text screening on the sanitized, correctly oriented image, evaluating house-number/address text and number plates as sensitive text regions. Do not send images to an external processor. Any detected candidate, ambiguous result, unsupported image or unavailable/erroring screen withholds that individual photo until reviewed. Never automatically blur a photo. Until WP-6f is deployed and Justin approves calibration evidence under §11, newly built releases contain structured data only; neither an individual review nor passing existing QA bypasses that deployment/calibration gate.

**Bounded card exception for scene-text only:** it may exclude the detected GSIP reference-card quadrilateral plus a bounded margin derived from the existing marker homography, then must screen the entire remainder of the frame. Face screening always covers the entire frame, including the card region. If no card is reliably localized, scene-text screening covers the entire frame. Do not reuse the soil-region mask, infer a card from arbitrary text or exclude any other context. Version the margin and test text immediately outside it, rotated/partial cards and localization failures with staged fixtures; record exclusion evidence privately with the screening digest/version.

A separate server-controlled, private publication state is required on each photo, proposed as `privacy_screen_status` (`pending|clear|review|error|withheld`). All existing rows start `pending`, not implicitly clear. Record the screened sanitized-content digest, screening code/model versions, thresholds and category-level outcomes; keep detections, extracted text and reviewer evidence private. Public logs/reports carry only aggregate counts and sanitized error classes. The implementation migration must enforce that clients cannot mark a photo clear and that content/version changes invalidate stale clearance. A reviewer can explicitly clear a false positive or permanently withhold the photo through an authenticated private operator CLI with an auditable decision and no private payload in stdout or CI logs. This operator path is not an agent-facing API (I12).

Privacy status is independent of `photos.qa_status` and submission settlement. A flagged photo alone does not fail, reject or flag the observation. A finalized observation still requires the existing A/B capture and quality checks (I2/I8); once those pass, its eligible structured data and other cleared, QA-passing photos proceed through the existing consent, withdrawal, provenance, holdout and k-anonymity gates. If no photo is cleared, export may publish eligible structured data with an empty photo list. Release bytes, shards, thumbnails, photo URLs and training inputs must never contain a pending, review, error or withheld photo. Screening cannot republish withdrawn media or bypass any existing gate. Previously published immutable releases cannot be silently recalled; report their status honestly and exclude uncleared media from every newly built release.

[The detector comparison](PHOTO_PRIVACY_SCREENING.md) separates code licenses from weight licenses, records payload size and maintenance signals, and explains unmeasured recall. YuNet and open scene-text detection are first-stage benchmark candidates; OCR may aid evaluation but cannot be the clearance gate. Add a dedicated plate detector only if staged evaluation exposes a material gap in face and scene-text coverage, and its exact artifact has verified code and weight licenses. The listed plate candidate remains ineligible while its weight license is unresolved; that candidate is not a required dependency. No model is selected for deployment. Prefer high recall and human review over automatic clearance based on OCR recognition alone: an unreadable plate or house number may still identify a place or person. Confidence thresholds, full-resolution/multiscale handling and unsupported cases must be calibrated and approved before public photo publication; absence of a detection is not a guarantee of anonymity. Report sample counts, per-category misses/false positives and uncertainty, including tiny/occluded faces, varied skin tones, oblique plates and multiple numeral scripts. Use synthetic/staged, consented evaluation material with no real contributor uploads in fixtures or public reports. Unknown recall, unresolved weight licenses for a selected artifact or missing category coverage are explicit blockers; fail closed for photos while eligible data continues.

**Implementation gate:** the specification merge prerequisite is satisfied by #38. The later implementation PR needs migrations/RLS and export tests, private review authorization tests, reproducible detector-license/digest evidence, and calibration evidence before deployment; production commands still require a separate exact-target "go". This proposal neither starts screening nor claims current photos are screened.

## 16. Open soil spectral library (v5 foundation; v6/v7 private intake)

### 16.1 Additional invariants

I1–I15 and B1–B8 remain binding. These library rules add constraints, not exceptions:

- **L1 — Measurement identity:** `camera_rgb` records contain three sRGB channel summaries with no invented wavelengths. `instrument_reflectance` records contain explicit nanometre wavelengths, fractional reflectance, uncertainty per band and an instrument/calibration identity. Derived spectra are a future distinct record type, never instrument truth.
- **L2 — Sample linkage:** a node UUID plus sample UUID identifies one physical sample. Measurement UUIDs identify immutable records. The same paired sample and all its repeated observations must remain in one training partition. Nodes cannot claim the same physical sample under different identities to increase evidence counts.
- **L3 — Traceable context:** record protocol version, capture method, device/instrument identity, material condition, depth bounds, source digest and calibration status. Unknown values are explicit; absence of a reference card is uncalibrated. Card detection alone does not certify reflectance calibration. Exact timestamps, instrument serials, operator identity, locations and document links remain private.
- **L4 — Paired evidence:** spectra and camera records join only through the same physical sample key. Laboratory evidence records method, canonical unit, uncertainty and verifier. Laboratory properties are not inferred from the spectrum. Biological assays require a separately reviewed vocabulary and interpretation protocol; none is fabricated from imagery.
- **L5 — Rights and partitions:** local records declare grant references, withdrawal state, QA state, synthetic provenance and sealed holdout state. These declarations are untrusted until verified by canonical ingest. Withdrawn, unconsented, QA-failing and synthetic records never enter field-model training. Holdout samples and their twins never enter training, tuning or an ordinary evaluation CLI.
- **L6 — Private by default:** the new node store, measurements, spectra, sample linkage and training files remain private, even when they omit coordinates. No node CLI publishes or uploads. No individual spectral public release until a separate privacy review considers fingerprinting, linkage and generalization under I7, including k = 3; a broad cell alone is insufficient clearance. WP-6f continues to gate image bytes and image-derived training inputs. Logs contain counts and generic error classes only.
- **L7 — Reproducibility and honest status:** record input hashes, extractor/model version, grouping rule and label basis. A baseline demonstrates the pipeline, not scientific validity. No useful model or soil-biome inference is claimed without eligible paired field data, independent evaluation and calibrated uncertainty.

### 16.2 Version 1 private exchange contract

`gsip-library-v1` is a bounded JSON record, validated identically at import and use. One record carries a measurement UUID, node/sample UUID pair, protocol version, structured sample context, grant UUID and current eligibility states. A discriminated measurement payload holds either camera RGB summaries (source-image SHA-256, extractor version, pixel count, dispersion, card-present indicator, uncalibrated status) or instrument reflectance (source-file SHA-256, wavelengths in nm, reflectance in [0,1], uncertainty in [0,1], instrument and calibration reference UUIDs). Wavelengths are finite, strictly increasing, aligned with values and uncertainties, between 200 and 25,000 nm; at least three and at most 10,000 bands. Version 1 accepts fractional reflectance only; percent, absorbance, radiance and out-of-range values must be converted by an independently documented adapter, never silently clipped or guessed.

Depths use cm with 0 ≤ top < bottom ≤ 200; material condition is wet, moist, dry or unknown. Opaque UUID references replace arbitrary text/document URLs. Optional paired labels use the existing canonical chemistry/texture property and unit mapping, a method reference UUID, nonnegative uncertainty and a verifier UUID. A label is evidence only when its origin and pairing are verified. Reject unknown fields, non-finite numbers, inconsistent arrays and conflicting measurement identities. Local declarations never bypass hosted grants/RLS.

### 16.3 Node, capture and model implementation boundaries

WP-LIB-1 supplies a local private store and import/inspect/withdraw commands. Creation uses restrictive filesystem permissions; immutable writes are atomic and identical re-imports are idempotent. Reject conflicting identities and symlinked stores. A withdrawal is a durable node/sample tombstone blocking future imports and use. Store operators must use encrypted local storage and delete separately produced training/model files when rights change; the CLI cannot retract external copies. Shared/public folders and phone cloud backups are unsuitable. Federation is explicitly not implemented by a directory of records.

WP-LIB-2 derives deterministic optical summaries from a sanitized phone photograph using the existing card homography and card-exclusion margin. Summarize only the selected soil candidate region; it is a geometric candidate, not a learned segmentation guarantee. Report per-channel mean and dispersion, surviving pixel count and source digest. Keep values as uncalibrated sRGB even with a detected card; do not reuse corrected card patches as a soil correction transform. Require private operator input and synthetic/staged material while WP-6f is not deployed. This offline utility does not change app capture, QA verdicts or hosted workers.

WP-LIB-3 prepares a private dataset of verified paired RGB and instrument records. Reject duplicate/conflicting sample pairing; propagate withdrawal and holdout across every measurement of a sample. Require a common wavelength grid and matching device/protocol/material condition per admitted pair, without implicit interpolation. Partition by sample, never by photo. Grouping across sites/campaigns and an independently sealed spatial/device holdout must precede scientific accuracy claims. The initial runnable linear baseline is synthetic-only; field training stays blocked pending canonical eligibility and photo-screening integration. Its preparation code admits only eligible paired records and propagates exclusions sample-wide. The baseline learns RGB→reflectance from synthetic train samples and reports error on a disjoint development partition; it emits no chemistry/biome predictions or public weights. Prediction intervals and external validation are mandatory before an estimator is exposed. Synthetic data are only a test/demo mode with conspicuous non-scientific output and cannot mix into field runs.

WP-LIB-4A/4B/4C integrate owner-private sample declarations with the phone and hosted service under §16.5–16.8. Their result is a private, immutable intake receipt, not physical-pair verification or training eligibility. WP-LIB-5 specifies node federation (scoped delegated credentials, identity/deduplication, terms/license verification and revocation propagation) before implementing it. WP-LIB-6 adds original instrument-source verification, verified lab/biological assay adapters and independent reconstruction/estimator evaluation; WP-LIB-7 adds approved generalized library releases and map/model consumption. These depend on field data and scientific/privacy review, not merely a green software build. Existing priors remain priors, not training truth.

### 16.4 Library success measures

Report eligible physical samples, paired camera/instrument samples, verified lab links, instrument/calibration coverage, repeat measurements and material/device/site diversity separately. Report synthetic demo counts separately. Track withdrawal completion and withheld/publication counts. Model evidence includes held-out error, uncertainty coverage and domain coverage; a repository, successful CLI run or library record count does not establish useful scientific adoption or biome insight.

### 16.5 Version 1 caller contract and instrument declaration (WP-LIB-4A)

**Boundary:** a local `gsip-library-v1` record is not a hosted authorization document. Its `consent_verified`, `pairing_verified`, `withdrawn`, `synthetic`, `holdout`, `qa_status` and label verifier fields remain local declarations. The hosted service accepts a separate, strict caller envelope; none of those fields can be supplied, copied or promoted into server authority. WP-LIB-4A supplies the shared TypeScript contract, bounded instrument-declaration parser and synthetic conformance fixtures; it makes no network calls and changes no app or database behavior.

`gsip-library-intake-v1` has exactly these fields:

| Field                    | Value and meaning                                                                                                                                                                                |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `schema_version`         | Exactly `gsip-library-intake-v1`.                                                                                                                                                                |
| `intake_id`              | UUID allocated once for the queued request; retries retain it.                                                                                                                                   |
| `node_id`, `sample_id`   | UUID namespace and sample key, allocated once in the private draft. A phone namespace is not a federated credential.                                                                             |
| `submission_id`          | UUID of the contributor's existing finalized submission. The server resolves its shot B photo; no arbitrary photo ID, storage path or URL is accepted.                                           |
| `protocol_version`       | Exactly `gsip-capture-v1`.                                                                                                                                                                       |
| `context`                | Exactly `depth_top_cm`, `depth_bottom_cm` and `condition`, with the finite bounds and condition vocabulary of §16.2. Depths are declarations entered by the person, never inferred or defaulted. |
| `instrument_declaration` | Null, or the strict object below. Absence means no instrument evidence was supplied.                                                                                                             |

An attached declaration JSON file has exactly `measurement_id` (UUID) and `measurement`. `measurement` is the `instrument_reflectance` payload in §16.2: lowercase 64-hex `source_sha256`, instrument and calibration UUIDs, 3–10,000 aligned finite bands, strictly increasing wavelengths from 200 to 25,000 nm, and reflectance/uncertainty in [0,1]. The nested intake field has this same shape; its version is defined by the enclosing intake contract. It contains no labels, references to external URLs, instrument serials, operator names, timestamps or original instrument-file bytes. Percent reflectance, absorbance and radiance remain unsupported; do not convert them implicitly.

The shared raw-JSON parser rejects unknown or duplicate fields, malformed UUIDs, unsupported versions, non-finite values, inconsistent arrays and oversized input. Both declaration files and the whole caller envelope are bounded by 2,000,000 UTF-8 bytes; validate the bound before fully parsing a file and again before sending. Shared synthetic valid/invalid fixtures exercise the TypeScript parser and the existing Python instrument validator. The hosted RPC receives PostgREST-normalized `jsonb` and independently revalidates semantic structure and the normalized representation's size; that boundary cannot detect original duplicate JSON keys or raw transport whitespace and must not claim to do so. Canonical idempotency compares the resulting validated fields, and no caller field supplies authority. Client validation never grants permission. A raw local `gsip-library-v1` record, arbitrary file, PDF, CSV or laboratory report is not a version-one attachment. The UI must explain the accepted declaration format rather than silently discard authority fields from another format.

One submission admits at most one intake and one optional instrument declaration. Its normalized envelope becomes immutable once stored. To keep retries stable, the server compares validated field values, including JSON numeric equality, rather than raw whitespace or object-key order. It stores the normalized representation and computes a SHA-256 digest over its exact persisted UTF-8 bytes; an equivalent retry returns the original representation's digest. The claimed instrument `source_sha256` remains a separate value: a digest of a stored declaration does not prove the digest of an absent original instrument file.

The response contains only `intake_id` and `status`, where status is `stored_private_unverified` or `already_stored`. It carries no grant, actor, QA, holdout, verifier or eligibility fields, source payload or private digest. Errors use generic classes for authentication/ownership refusal, identity/context conflict, withdrawal, activation hold or retryable infrastructure failure; logs contain only counts and generic classes. A receipt is successful private storage, not consent certification, a verified spectrum, physical-pair proof, QA clearance or scientific evidence.

### 16.6 Additive hosted intake and authority (WP-LIB-4B)

**Data model:** an additive migration creates service-owned tables in the non-exposed `private` schema for node ownership, immutable samples, submission/photo links, instrument declarations, sample tombstones and sample restrictions. A node is bound immutably to one contributor at first successful intake. A sample's node/sample key, contributor, original grant, protocol and context never change. A submission and its resolved shot B photo cannot be rebound to another sample. A measurement UUID cannot name different bytes or another sample. Exact retries consume no new quota and create no new rows; conflicts never overwrite or mint replacement UUIDs.

Enable RLS on every new table, revoke client table access and apply explicit restrictive deny-all client policies. `private` remains excluded from exposed Data API schemas, with no client `USAGE` or `CREATE` grant. Immutable identities/payloads and durable tombstones have mutation/truncation guards; the controlled deletion path can erase payloads after preserving tombstones. Service operations receive only the required privileges. The public API, agent readers, export, map aggregates and model preparation receive no new table access or library fields.

Client entry points are `library_intake_capabilities()`, `record_library_intake(p_request jsonb)` and `my_library_intake_receipt(p_intake_id uuid)`. Public wrappers use `SECURITY INVOKER` with SQL-standard, definition-time bound private dispatch, following §6. Privileged bodies have an empty pinned `search_path` and narrowly granted execution. The capability response is exactly `{version: 'gsip-library-intake-v1', available: boolean}`. Receipt lookup is owner-bound and returns the same receipt shape in §16.5 with `already_stored`; it cannot reveal another person's request, sealed status or evidence. No client entry point returns raw private tables or allows a verification decision. The phone uses its own user session and publishable key; no service-role credential reaches the client or an agent-facing interface.

Before each fresh write or idempotent retry, the private ingest transaction verifies the live auth user, current contributor and active human actor; ownership of the finalized submission and resolved shot B photo; its exact grant/contributor relationship; the original grant's immutable license and terms acceptance; absence of grant withdrawal, a covered deletion request or sample tombstone; and both capture and library activation gates. Terms validity is checked at the grant's acceptance time. A previously admitted grant is not re-aged or replaced merely because intake happens later. New grant creation and expired original acceptance continue through the existing contribution lifecycle and withdrawal-first rules. No caller-supplied contributor, actor, grant, provenance, QA, synthetic or holdout field is accepted. Keep reserved provenance tiers 2/3 unassigned.

The transaction independently validates the envelope, binds its normalized digest and source-photo identity, and enforces at most 100 newly admitted intakes per contributor per UTC day. Retries do not spend quota. Library intake cannot create submissions or upload photos to bypass the existing capture limits. Source linkage to an existing photo is an immutable reference, not proof about its bytes: if no trusted sanitized-byte digest is recorded, source digest verification remains pending. This package neither extracts field RGB summaries nor changes photo QA, sanitization, settlement or provenance.

**Unverified instrument claims:** instrument/calibration UUIDs and `source_sha256` are declarations, not verified registry entries or attestations. The stored payload digest and photo link establish consistent claimed linkage only. All instrument-origin, calibration and physical-pair verification remains pending in version one, even for a locally declared verified record. There is no positive pairing/verification mutation or verified-record export in WP-LIB-4B. Original source-file verification and reviewed evidence adapters belong to LIB-6. Arbitrary original-file Storage, scientific lab-label ingestion and changes to `gold_labels` are excluded.

Known duplication of a source-photo identity is rejected across sample keys. Within the owner's private declarations, a repeated claimed instrument-source digest under another sample key is also rejected rather than counted as independent evidence. An untrusted claimed digest cannot change another owner's restrictions or establish a cross-owner physical-sample match. Unknown twins and invented identities cannot be ruled out by this mechanism; cross-node identity and verified deduplication require LIB-5/6. A consistent UUID or hash is never called physical pairing verification.

### 16.7 Withdrawal, deletion and held-out samples (WP-LIB-4B)

Reuse `deletion_requests`, append-only `grant_withdrawals` and SQLSTATE `WD001`. Filing a covered withdrawal invalidates new library use in the same transaction as grant withdrawal. Intake and rights-request mutation serialize on the same contributor row, acquiring that lock before sample/grant/source locks; recheck rights after locking. Concurrent withdrawal and ingest must linearize without a late write escaping invalidation or cleanup. Checks only before a network operation are insufficient.

Before deleting any covered sample payload, preserve a durable opaque node/sample tombstone with the original grant reference and generic withdrawal reason. It holds no context, measurement arrays, photo path, location, operator name or instrument identifiers. Tombstones have no cascading reference to the erased sample and cannot be removed or overridden by a later intake. A later grant cannot revive that same sample key. The canonical grant-withdrawal record continues to reject covered queued submissions even when no hosted sample existed at request time. Other devices may retain offline bytes until they reconnect or the person clears them; do not claim immediate remote erasure of device storage or copies outside GSIP.

Integrate with the existing service-only `apply_deletion_request(uuid)` and `complete_deletion_request(uuid)` without changing their signatures, so the existing rights worker deletes/checks covered library rows even if worker deployment lags the migration. Additive withdrawal/request and completion-guard triggers may provide this integration while preserving those existing function bodies. Retire erased intake and measurement declaration UUIDs in minimal opaque, immutable refusal records so historical identities cannot name another payload or sample. These ledgers contain only the declaration UUID and identity kind, never contributor links, instrument/calibration registry IDs, source hashes, context or measurement bytes. Account deletion also retires opaque node UUIDs after removing ownership, preventing namespace reassignment to a new contributor. Persist tombstones first, erase declarations/context/links under withdrawn grants, and cascade submission deletion through source links. Account deletion also removes the contributor's library namespaces and other private payload after preserving minimal refusal records. Completion must fail while covered library payload remains; an empty-request shortcut must not mark a library-bearing request complete. Requests remain retryable and idempotent within the existing 30-day deletion commitment. There is no new Storage bucket in these packages, so existing photo-object cleanup remains authoritative for photo bytes.

Sealed holdout is a server-only, monotonic sample restriction. Linking a submission with an existing held-out `gold_labels` row seals its sample; subsequently sealing a linked label seals the sample too. All existing and future measurements/links of that sample inherit the restriction. Known twins established by server-owned source-photo linkage inherit the most restrictive state; untrusted instrument digests do not seal another owner's sample. Removing a label, adding a twin or writing a false flag cannot unseal a sample. Do not return the seal, the fact that a holdout label exists, label values or the reason for a scientific restriction through receipts or phone UI. This is enforcement plumbing, not an evaluation service. Ordinary preparation, tuning, baseline and agent APIs gain no holdout access, and field baseline execution stays blocked.

### 16.8 Phone integration and independent activation (WP-LIB-4C)

An optional library section on the existing capture form creates private draft UUIDs, asks the person for depth bounds/condition and optionally accepts one strict instrument declaration JSON file. Sample metadata and attachment bytes are persisted with draft photos before queueing and survive a restart. New submissions allocate their own sample; version one has no cross-account transfer or same-sample recapture UI. Never invent a depth, spectrum, instrument identity or library sample for an older observation. The source reference is the submission's existing required shot B, not an arbitrary upload or external reference.

Add an optional versioned library member to queue records and upgrade IndexedDB additively. Version-two records without it continue through the unchanged photo submission path. A record with it retains the same IDs, context and normalized instrument declaration across every retry. Sync first completes the existing grant/submission/photos/finalize lifecycle, then calls private library intake. Do not remove that queue record until every required stage succeeds; a lost response retries the same intake. Withdrawal drops the covered record and bytes; a permanent identity/context conflict holds it for discard/correction without blind UUID replacement; infrastructure failure uses the existing bounded retry/dead-letter behavior. A temporarily closed, absent or unsupported library service holds the record without spending failure attempts or losing its completed photo stage.

Keep owner binding across retries, expired sessions and account switches. A namespace becomes bound on first successful intake; the phone must remember which account can use it. New captures after an account switch allocate a new namespace. A held library record must not pass through a bulk operation that clears `ownerUid` and silently reassigns its node/sample to the newly signed-in account. Version one permits return to its original account or explicit local discard; transfer/re-identification is future work. Original acceptance is still offered before reconfirmation so a withdrawn grant cannot be resurrected.

Queue/draft clearing, withdrawal and account-deletion UX erase the new sample metadata and attachment bytes as well as photos. Extend the queue generation fence and cross-tab sync lock to prevent a drain writing back a discarded record. Cloud-backup exclusions and compiled native-artifact checks cover every new private store; the approved direct-device-transfer distinctions in §15 still apply. Delete temporary picker copies when the platform provides them; imported declaration files elsewhere on the device remain outside GSIP's deletion control.

**Merge-safe activation:** `VITE_LIBRARY_INTAKE_LIVE` defaults to `false`; a separate server library-intake gate defaults to `false` and is readable only through capability dispatch and writable only by the service operation. Actual intake requires that build flag, compatible capability response, the new server gate and existing `capture_open`/`VITE_CAPTURE_LIVE` gates. A false build flag sends no new library RPC and renders the established capture UI. Probe capabilities separately from the existing `service_state.capture_open` query: do not query new columns in that legacy query. Missing RPC/schema, incompatible contract or capability failure is a library hold, not evidence of an empty service or authorization to sign in anonymously. Check capability/gates before any new library-related sign-in or mutation.

Default app and Pages artifacts keep both build flags false; production auth/capture gates remain untouched. Synthetic local tests may use a mock-open service, but their artifacts stay local and the actual deployment artifact is rebuilt closed. The migration preserves existing rows, function signatures, grants and gate values, creates no acceptance backfill and activates no worker. Every production migration/deployment still needs its separate exact-command/target go under §6 and the deployment runbook. These packages add no public endpoint, release, estimate, model weights, field extraction/training, federation or physical verification.

**Completion evidence:** separate PRs for 4A, 4B and 4C must pass independent review and CI. The contract corpus proves identical bounds and forbidden-authority behavior. Database role/migration tests prove caller binding, strict server validation, immutable idempotence, quota, closed gates, withdrawal races, tombstones, monotonic holdout and compatibility with the existing worker/function signatures. Phone tests prove draft restart, legacy queues, partial/lost-response retries, capability absence, account changes, clear/withdraw races and native backup coverage. A synthetic end-to-end run demonstrates capture → queued sample → owner-private unverified receipt → exact retry → withdrawal/deletion. Report stored declarations separately from verified physical pairs; a completed LIB-4 test supplies no verified field pair, scientific validation or deployment evidence.

---

_Licensing: code MIT · databases/structured data ODbL 1.0 · contributed photos CC BY-SA 4.0 · models open weights with model cards. Contribution terms require legal review before public launch._
