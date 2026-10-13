# GSIP Build Order — Work Plan

**Project:** Global Soil Intelligence Project (open soil spectral library, captured through smartphones, for people and agents)
**Version:** 10.0 — 2026-10-13 (merged local clarification; SPEC §16.12)
**v10 amendment status:** the four LIB-5B local accounting/fence/admission/root clarifications are merged in [#60](https://github.com/global-soil-intelligence/gsip/pull/60). The approved v9 LIB-5A contract source is merged in [#58](https://github.com/global-soil-intelligence/gsip/pull/58); the synthetic LIB-5B ledger/rights simulator is merged in [#64](https://github.com/global-soil-intelligence/gsip/pull/64).
**Owner approval:** Justin approved ordered #51–#56 source merges after green CI on 2026-10-13; those source/specification merges are complete. LIB-5A and LIB-5B source are merged after their specification prerequisites. Real-sharing source/retention/peer/credential choices remain unresolved; no federation rollout or production authority is granted.

**Baseline:** v3 plus the v4 amendment merged in #38 and the v5 library foundation merged under Justin's 2026-10-12 owner authorization, with separately gated v6/v7 private intake. v8 defines exact WP-6f database/worker/review/export authority under the approved photo policy. Implementation preparation and code merges follow their own prerequisite review/CI; all production gates remain required.
**Builder:** Codex, acting for Justin Hart as human of record.
**Independent review:** every PR is reviewed by fresh-context adversarial review agents (no memory of authoring the code) against the §5 review gates; findings and resolutions are posted to the PR. Justin Hart provides the final product-owner go/no-go. On 2026-10-12 he approved an owner exception: the extra non-author GitHub approval is no longer required for this owner-operated repository. Independent adversarial review and green CI remain required; an agent never submits an approving review or certifies the human DCO.
**Product owner:** Justin Hart
**Governing document:** reviewed `docs/SPEC.md` on `main` (v5 foundation, v6/v7 private intake, v8 photo privacy, v9 bounded local exchange architecture and merged v10 local simulator clarification in §16.12). Existing launch gates are preserved; merged source is not deployment or external-readiness evidence. If this document and the spec conflict, the spec wins; flag the conflict instead of guessing. The v2.2 work plan, with the full WP-0 to WP-6 acceptance criteria, is archived in `docs/archive/v2.2/`.

---

## 1. Roles and workflow

- The builder implements **one work package (WP) per pull request**, on a branch named `wp-<id>-<slug>` (e.g. `wp-6b-launch-hardening`). Specification updates use `docs/spec-v<version>`.
- **No direct commits to `main`.** Merges happen only after (a) CI green, (b) adversarial review findings resolved, (c) the product owner's explicit go/no-go. An authorised agent may execute an ordered merge after these gates, but never bypass a protection or approve its own work.
- Work packages that depend on each other are opened as **stacked pull requests**: each PR targets its predecessor's branch and is retargeted to `main` when the predecessor merges. Merge in the order of §7.
- Every PR description contains: the WP id, the WP's acceptance criteria checked or explained, the spec invariants (I1–I15) and business guardrails (B1–B8) it touches, and any deviation from this build order with justification.
- Commits use Conventional Commits. Human commits carry a DCO sign-off (`git commit -s`). Agent-authored commits carry a `Co-Authored-By` trailer for the agent and are signed off by the human of record who adopts them; an agent never certifies the DCO itself.
- If a WP is under-specified, the builder opens an issue stating the question and stops on that WP. Spec gaps are not filled with assumptions; assumptions that must be made to proceed are listed in the PR.

## 2. Hard guardrails (violations = automatic PR rejection)

1. **Languages: TypeScript and Python only.** TS strict mode; Python 3.11+, fully type-hinted.
2. **No license changes.** Code MIT; databases and structured data ODbL 1.0; photos CC BY-SA 4.0. No dependency with a license incompatible with MIT distribution without reviewer sign-off.
3. **No schema change outside a migration**, and no migration that contradicts `docs/SPEC.md` §6 without a spec update first.
4. **Never store or export precise contributor coordinates in any public path** (I7), including image metadata, logs, URLs, analytics and calls to external services. Public artifacts use k-anonymous H3 cells only.
5. **UI and API copy never says "soil test."** Always "estimate" with uncertainty (I5).
6. **No paid or closed services in the default deployment path.** Anything with a bill or a proprietary SDK needs product-owner sign-off. Known decisions: Supabase Pro before public launch; Apple ($99 a year) and Google Play ($25 once) developer accounts for WP-APP-1; CAPTCHA provider for anonymous sign-in (Turnstile and hCaptcha are both closed services).
7. **No secrets in the repo.** All configuration via environment variables; `.env.example` documents every variable.
8. **Every WP ships with tests.** A PR with production code and no tests is incomplete.
9. **Agents see no more than the public (I12).** No agent-facing interface may use the service role key or a contributor's session.
10. **Business guardrails B1–B8** in `GOVERNANCE.md` hold: no paywall on contribution or released data, no embargo fields, no trackers or advertising SDKs, no payment input to QA, consensus or evaluation code.

## 3. Repository

`https://github.com/global-soil-intelligence/gsip`, public, with branch protection on `main` (PR required, zero extra approving reviews under the owner exception, stale approvals dismissed, conversation resolution, no force-push or deletion). The product owner adds the CI `validate` job as a required status check.

GitHub Pages serves one site per repository: the site at `/`, capture at `/capture/`, the map at `/map/`, and the reference card PDFs at `/reference-card/`, from one combined artifact. The canonical domain fronts it after WP-SITE-1D.

```
gsip/
├── docs/                 SPEC.md, BUILD_ORDER.md, AGENTS.md, legal/ drafts, archive/
├── apps/
│   ├── capture-pwa/      capture app (web PWA; Capacitor phone app from WP-APP-1)
│   ├── map-web/          MapLibre map
│   └── site-web/         public site (prerendered from WP-AGENT-1)
├── packages/schema/      shared TS types, zod schemas, prior logic, palettes, agent API logic
├── supabase/             migrations, pgTAP tests, Edge Functions (TS), seed
├── pipeline/             Python workers: QA, priors drain, export, rights, tiles
├── ml/                   Python models (Phase 2)
├── card/                 reference-card generator and validation
└── .github/              workflows, PR and issue templates
```

Tooling: pnpm workspaces; ESLint + Prettier; Vitest + Playwright; uv, ruff, mypy --strict, pytest; pgTAP via `supabase test db`. `pnpm test`, `uv run pytest` and `pnpm db:test` from the root run everything.

## 4. Work packages

### Completed (Phase 0 and Phase 1 code)

WP-0 repository bootstrap · WP-1 schema and RLS · WP-2 reference card · WP-3 capture PWA · WP-4 prior-attach worker · WP-4b deterministic ingest QA · WP-5 map site · WP-6 nightly export · public website. All merged on 2026-10-01; acceptance criteria in `docs/archive/v2.2/BUILD_ORDER.md`.

### Phase 1.1 — Launch hardening (before the first real contribution)

**WP-OPS-2: Production migration-history reconciliation**

Before deploying the reviewed stack, reconcile the owner-confirmed legacy timestamp drift and accidental foreign deployment. Preserve application rows, schema, RLS, grants, capture restrictions and anonymous-auth settings. [PRODUCTION_RECONCILIATION.md](PRODUCTION_RECONCILIATION.md) records the effective-schema comparison, thirteen timestamp pairs, a private ledger backup and exact commands. The read-only catalog comparator must reject any difference beyond the documented aliases and platform metadata; tests must reject missing or changed privacy protections. Rehearse metadata alignment and all nine pending migrations in an isolated database, and run `scripts/db-migration-test.sh` before requesting approval. Justin authorizes history repair and the stray function deletion separately; new migrations and deployments each require their own subsequent go. No foreign application migration is imported into GSIP.

Acceptance:

- [ ] Compare production's effective baseline with all seventeen reviewed July migrations, including private functions, Storage policies and grants.
- [ ] Confirm aggregate counts and the absence of foreign tables; preserve recoverable original history privately before any repair.
- [ ] Test strict drift rejection and rehearse history alignment without application changes, then the nine pending migrations on synthetic existing rows.
- [ ] Show the exact project and commands; execute only after Justin's explicit go, with a stop on any failed step or changed evidence.
- [ ] Read back seventeen canonical baseline identities, exactly nine pending migrations, unchanged application counts/privacy controls and removal of only the approved stray function.

**WP-6b: Ingest, QA and release integrity**
Fixes launch blockers 1, 4, 5, 6 and 8 from the 2026-10-10 review.
Scope:

1. **Path binding.** A trigger binds `photos.storage_path` to `{auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg` for every role, using the submission contributor's `auth_uid`. The `incoming-photos` insert policy requires the same full pattern. The QA worker re-derives the expected prefix from database facts and refuses any mismatch before touching Storage.
2. **Finalize and settle.** `submissions.finalized_at`; `finalize_submission(uuid)` for the owner, requiring photo rows for shots A and B, idempotent. `photos.qa_status` (`pass|fail|flagged|error`) written by the QA worker. `settle_submission(uuid)` (service role) implements the SPEC §5 settlement table; the worker settles every finalized, pending submission each run. The capture client finalizes after its last photo insert.
3. **Soil-region QA.** Locate the card from the marker homography and mask it with a margin; require at least 20 % soil (`soil_region` check); compute sharpness, exposure and the perceptual hash on the soil region. Apply EXIF orientation and convert embedded ICC profiles to sRGB before stripping, recording only a colour-space class (`srgb|display_p3|other|none`) in private metadata. Missing GPS accuracy scores as unknown (null) and passes. QA version `deterministic-v2`.
4. **Release integrity.** Export selects `qa_pass` submissions with passing shots A and B and, within them, photos with `qa_status = 'pass'`, re-deriving each photo's owner path. A per-row data failure (a missing photo object, for example) is set aside in a private `export_report.json` and the release continues. A privacy assertion failure, an infrastructure error (Storage or database 5xx, timeouts) or more than 10 % of rows set aside aborts the release. Rows carry per-photo QA checks; location-derived scores and point-level priors are never released (SPEC I7).
5. **k-anonymous publication.** Export assigns each row the finest published cell (r8, then r6, then r4) aggregating at least 3 distinct contributors, or withholds it. Rows carry `h3_cell` and `h3_resolution` instead of `h3_r8`/`h3_r6`. `h3_cells` gains `resolution` and `n_contributors`; `refresh_public_h3_cells` rejects any item with fewer than 3 contributors or a resolution that does not match its index. The map draws all three resolutions, finer above coarser, with popups showing count, resolution and latest date.
6. **Capture gate.** `service_state` (one row; `capture_open` defaults to false; readable by everyone; writable only by the service role). Insert policies on `contribution_grants`, `submissions`, `photos` and `incoming-photos` require it. The capture app renders an "opening soon" state unless built with `VITE_CAPTURE_LIVE=true`, and pauses sync while the database reports capture closed.
7. **Quarantine cleanup** runs hourly on its own schedule (`quarantine-cleanup.yml`, `python -m pipeline.qa_worker --cleanup-only`).
8. **Attribution.** New grants reject attribution names containing control characters, markup characters or URLs; existing rows are not revalidated. Capture warns that a typed name is published with the observation's area and date.
9. **Workflow hygiene.** Every workflow reads `vars.SUPABASE_URL`; uv and Python versions are pinned in every workflow.
10. **Copy.** "Two required photos, one optional" everywhere; the capture app stops promising a history view until WP-APP-1 ships My Soil.
11. **Client function boundary (SPEC §6).** An additive migration makes `capture_is_open()` an invoker function reading only the already-readable gate column and moves the guarded finalization body to `private`. Its unchanged public signature uses a definition-time bound SQL-standard invoker wrapper; caller ACLs and client table, column and private-schema privileges stay unchanged.

Acceptance criteria:

- [ ] pgTAP: a photo row naming another user, another submission, another shot, a non-UUID object or a `..` segment is rejected for both `authenticated` and `service_role`; incoming uploads outside the pattern are rejected.
- [ ] pgTAP: `finalize_submission` refuses non-owners and submissions missing shot A or B, and is idempotent; `settle_submission` produces every row of the settlement table; a failed shot C leaves a passing submission at `qa_pass`.
- [ ] pgTAP: with capture closed, authenticated inserts into grants, submissions, photos and incoming storage fail; with it open they succeed; clients cannot change `service_state`.
- [ ] pgTAP: anonymous and authenticated gate reads need no singleton-column privilege; an absent singleton row returns false. Finalization retains owner, required-shot and idempotence checks through the invoker wrapper; its private dependency is recorded, direct private name resolution is denied, and only authenticated callers can execute the private finalizer. Existing ACLs and service operations remain unchanged.
- [ ] pgTAP: `refresh_public_h3_cells` rejects fewer than 3 contributors and mismatched resolutions.
- [ ] pytest: blurred soil beside a sharp card fails sharpness; sharp soil beside a card passes; a card-only frame fails `soil_region`; different soils photographed with the card at one pose are not near-duplicates; orientation and Display P3 conversion are applied; missing accuracy is unknown and passes.
- [ ] pytest: the QA worker refuses a mismatched storage path before any Storage request.
- [ ] pytest: no exported cell aggregates fewer than 3 distinct contributors; sparse rows roll up to r6, then r4, else are withheld; one missing photo is set aside and the release completes; a metadata finding, a Storage outage or widespread set-asides abort; only `qa_status = 'pass'` photos are exported; no row carries priors or a GPS-derived score.
- [ ] vitest: capture shows the closed state without `VITE_CAPTURE_LIVE`; sync finalizes after the last photo insert; the attribution warning is visible; the map renders cells of all three resolutions.
- [ ] A test fails if any workflow reads `vars.VITE_SUPABASE_URL` or runs `setup-uv` without a pinned version.

**WP-6c: Priors and tiles**
Fixes launch blockers 2 and 3.
Scope:

1. **No-prior is terminal.** The SoilGrids parser accepts null values; a property with a null mean yields no row. A definitive empty answer completes the job and records the source in `prior_jobs.empty_sources`; it never dead-letters.
2. **Cell-centre lookups and cache.** All upstream lookups use the centre of the submission's resolution-9 cell. Static sources (SoilGrids, SSURGO, elevation) are cached in the server-only `prior_cell_cache` keyed by cell and source for 365 days. Precipitation covers the 3 days ending at `captured_at`: the forecast API for captures within 90 days, the archive API before that.
3. **Upstream token buckets, claimed and paid atomically.** `upstream_buckets` holds one bucket per source: SoilGrids one token refilled five times a minute (calls at least 12 s apart, never more than five in 60 s), SSURGO 30 a minute, Open-Meteo 60. `begin_prior_attempt(submission, owner_request, costs)` (service role) claims a job and spends the tokens for its cache misses in one transaction: a request that cannot be claimed, or must wait, claims and spends nothing, and a deferral returns its wait (202 with `Retry-After`). Each upstream call is made once; the job retry is the retry.
4. **Job claims.** `verify_jwt` is pinned on for `prior-attach`. A contributor's request reads the submission through RLS and can start only their own `pending` job with zero attempts; service mode needs the exact service-role key, never a token claim. Only the service role retries `pending` and `dead_letter` jobs, up to 32 attempts; `requeue_stale_prior_jobs()` returns `processing` claims older than 15 minutes to `pending`, or to `dead_letter` once the attempts are spent; `fail_prior_job()` ends a job that can never succeed. The drain waits out `Retry-After` within a 240-second budget and moves failed, unclaimed jobs behind the queue. Orchestration lives in a tested module in `packages/schema`; the Edge Function is a thin adapter.
5. **Tiles.** A versioned palette file in `packages/schema/src/palettes/` holds stops in canonical units plus each SoilGrids scale factor. The builder converts stops to raw units, colours with `gdaldem color-relief -alpha` (nodata transparent), tiles RGBA PNG, stamps each archive with the palette version and writes it under that version's directory, the path the map requests. Map legends render from the same file, and the Pages deploy fails unless every archive for the current palette version exists and carries its stamp. The WMS fallback shows ISRIC's legend graphic. CI installs GDAL.

Acceptance criteria:

- [ ] vitest: an all-null SoilGrids response (urban fixture) parses to zero rows without throwing; a mixed response keeps the non-null properties; lookups use the r9 cell centre, never the input point; precipitation windows end at `captured_at` and use the archive API for old captures.
- [ ] vitest: a cache hit makes no upstream call; a deferred or unclaimable request makes no upstream call and consumes no attempt; empty answers complete the job.
- [ ] pgTAP: claiming and spending are atomic (unclaimable and deferred requests spend no tokens); the SoilGrids bucket never banks a burst and refills every 12 s; contributors cannot restart completed jobs or claim others' jobs; stale `processing` jobs requeue, or end once their attempts are spent.
- [ ] pytest: the drain waits for `Retry-After` within its budget and never touches a `processing` claim.
- [ ] pytest: palette conversion to `gdaldem` stops is exact; a golden-tile test colours a synthetic Int16 raster with nodata to the palette (±2 per channel), with alpha 0 at nodata and correct colours above 255; archives are stamped with the palette version.
- [ ] vitest: every prior layer's legend is generated from the palette file; the deploy gate rejects archives that are missing or carry another palette version.

**WP-6d: Contributor rights and launch paperwork**
Fixes the mechanisms behind launch blocker 7; counsel still approves the text.
Scope:

1. **Requests.** `deletion_requests` (kinds `withdraw_contributions` and `delete_account`; owner insert and select; one open request per contributor; an empty withdrawal completes when filed) and append-only, untruncatable `grant_withdrawals` (service role). Filing a request withdraws every grant the contributor holds in the same transaction, so publication stops at once. Nothing a request covers comes back: a grant accepted at or before a request, or any grant once an account deletion is requested, is refused with SQLSTATE `WD001`, as are submissions, photo rows and uploads under a withdrawn grant; a contributor can be created only for an auth user that exists.
2. **Rights worker.** `pipeline/rights_worker.py` (service role, hourly workflow, 20-minute budget, requests with data first) deletes every submission under a withdrawn grant (cascading) and every object in either bucket under the contributor's folder that no remaining submission owns (one database snapshot), and for `delete_account` also withdraws any remaining grant, deletes the auth user through the Admin API and only then pseudonymizes the contributor row and replaces the attribution names on its grants with the default pseudonym (the only change a grant ever undergoes). Idempotent; a failed step returns the request to the queue after a one-hour wait; a failed run opens an issue, and a request older than 25 days fails the run. Every run also deletes canonical photo objects that no photo row owns, and the QA worker undoes a promotion whose photo was withdrawn mid-check.
3. **Export filters.** Withdrawn grants never export, and the export re-reads withdrawals just before publishing, rebuilding once without late ones (or refusing to publish if they keep arriving). Photos publish only under the default pseudonym or an approved attribution (`attribution_reviews`, service role, with a small review CLI); otherwise the row is released without photos until review.
4. **Legal pack drafts** in `docs/legal/`, each marked "Draft — requires counsel review": terms, privacy notice with processor list, withdrawal and deletion procedure (including Hugging Face history), classroom and minors policy, sampling and land-access rules.
5. **Capture.** A "Your data" panel to withdraw contributions or delete the account, with typed confirmation and status (account deletion revokes every session); queued observations record their account and are never sent as another or a new account (held for the person to discard or release); `WD001` refusals drop the observation; adding an e-mail upgrades an anonymous account in place; acknowledgement of the sampling rules and the age statement before queueing; terms, privacy and sampling-rules links from `VITE_TERMS_URL`, `VITE_PRIVACY_URL` and `VITE_SAMPLING_RULES_URL` (HTTPS or same-site only), defaulting to the drafts in the repository.
6. **Rights function boundary (SPEC §6).** A later additive migration moves the guarded auth-existence and upload-check bodies to `private` behind unchanged public invoker signatures with definition-time bound SQL-standard bodies. It preserves authenticated and service-role execution, including the upload-helper grant, and adds restrictive false policies to the two service-only rights tables without granting client access.

Acceptance criteria:

- [ ] pgTAP: owners create and read only their own requests, with at most one open; clients cannot write withdrawals or attribution reviews; grants stay immutable and untruncatable; grants accepted before a request, grants during an account deletion, and submissions, photos and uploads under withdrawn grants are refused; a deleted auth user cannot recreate a contributor; the orphan listing never lists a live submission's object.
- [ ] pgTAP: rights wrappers record their private dependencies, refuse missing auth UIDs and preserve deleted-user and withdrawn-grant checks. Anonymous callers cannot execute their private callees, and client private-schema and table privileges remain denied. In a rolled-back synthetic fixture, restrictive false policies defeat temporary permissive policies plus SELECT grants; service-role rights operations still succeed.
- [ ] pytest: the rights worker removes both buckets' objects and the rows, pseudonymizes only after the auth user is gone, is idempotent, and stays within its budget; Storage or Auth failures leave the request retryable.
- [ ] pytest: export excludes withdrawn grants, including withdrawals filed during the export; pending or rejected attributions release rows without photos; default and approved attributions publish photos.
- [ ] vitest: deletion requires confirmation and shows status; an unreadable session is a failure, not "no account"; records are never sent as another account; `WD001` records are dropped; sampling rules must be acknowledged before queueing.
- [ ] A test checks that every external host the code calls appears in the privacy notice's processor list.

**WP-6e: Provenance foundation**
Lands I9–I11 and the I15 holdout flag while production holds little or no real data.
Scope:

1. **Actors.** `actors` (`human|agent|device|lab`); a human actor per contributor (backfilled, then created by trigger; revoked when the contributor has no sign-in); non-human actors require an active human operator; revocation is final and reaches every actor the operator runs. A submission's actor is the contributor's human actor unless a server path names an active actor that human operates. Clients read only their own actor and write none.
2. **Submission provenance.** `actor_id` (server-set), client claims `ingest_path` (`web|app`), `capture_method` (`camera|file|unknown`), `location_source` (`device_gps|manual_pin|unknown`) and `client_version`, and server-only `provenance_tier` (-1 synthetic, 0 unattested, 1 corroborated, 2 attested, 3 lab-verified). Synthetic rows are exactly tier -1 and never become field data again.
3. **Photo evidence.** Before stripping, QA derives private `capture_evidence_private` (EXIF time present and absolute, its difference from the claimed capture time, its age when the terms were accepted, EXIF GPS present, distance to the claimed point — never coordinates or timestamps). The database derives every tier from that evidence; a direct write cannot set one. A photo reaches tier 1 when its absolute EXIF capture time agrees with the claimed capture time and was taken within the hour before the contributor accepted the terms for the observation (five minutes of clock skew allowed), and any EXIF GPS agrees with the claimed point; a submission's tier is the minimum of shots A and B. Tiers 2 and 3 are reserved for attestation and lab pairing.
4. **Grants under I9.** Published `terms_versions` (versions recorded only from existing grants are retired); a grant must cite a published version, its client acceptance time must fall within the last 30 days and not in the future, and the server records `received_at`. A device holds an observation whose acceptance has expired, once the server has shown it was not withdrawn, until its person accepts the current terms again.
5. **Holdout.** `gold_labels.holdout` (server-only); export drops holdout labels and aborts if one remains.
6. **Export.** Rows require tier ≥ 0 and carry `provenance_tier`, `location_source` and `capture_method`; the dataset card documents tiers. The capture client sends its claims.

Acceptance criteria:

- [ ] pgTAP: every contributor has exactly one human actor; a non-human actor without an active human operator is rejected; clients cannot write `provenance_tier`, `actor_id`, `received_at` or `holdout`; tiers follow the evidence whatever is written; synthetic rows are exactly tier -1.
- [ ] pgTAP: grants citing an unpublished terms version or an out-of-window acceptance time are rejected; a withdrawn acceptance is refused as withdrawn (`WD001`) even when it is also out of window.
- [ ] A migration test applies WP-6e to a database holding pre-WP-6e rows and checks the backfill and the account-deletion flow on them.
- [ ] pytest: capture evidence contains only allowlisted fields and no coordinates; hostile metadata yields empty evidence; client claims are never read when tiering.
- [ ] pytest: export refuses rows below tier 0 and aborts on holdout labels; the dataset card lists tiers.
- [ ] vitest: the capture client sends `ingest_path`, `capture_method`, `location_source` and `client_version`; an expired acceptance is held only after the server has not refused it as withdrawn.

### Phase 1.5 — App and agent readers

**WP-SITE-1D: Canonical domain cutover** (product-owner action)
Point `globalsoilintelligence.com` at GitHub Pages, set the Pages custom domain, enforce HTTPS and retire the Squarespace page.
Acceptance: the canonical domain serves the Pages site; `robots.txt` allows crawlers; canonical URLs and the sitemap resolve.

**WP-SITE-1E: Prior-tile host policy**
Scope: record the product owner's conditional approval for same-origin repository GitHub Pages
prior tiles in the privacy notice and a deployment plan. Tiles remain palette-version release
assets outside git and enter the Pages artifact only at deploy time. This package documents the
host; it does not build or publish archives, change workflows or authorize deployment.

Acceptance criteria:

- [ ] The privacy notice identifies GitHub Pages as the map tile host and discloses browser
      requests; its counsel-review status remains unchanged.
- [ ] The plan requires SoilGrids-only values, palette and checksum evidence, a tile target of
      700 MB or less, a whole site well below 1 GB, and verified Pages 206 range responses.
- [ ] WMS remains the fallback until every condition passes; release publication and Pages
      deployment remain gated by Justin's explicit go.
- [ ] The privacy disclosure test fails without the host entry; processor and language checks and
      documentation formatting pass. No dependency or licence changes.

**WP-AGENT-1: Agent-readable GSIP**
Scope:

1. **`gsip-public` Edge Function** (`verify_jwt = false`) using only the publishable key, so the anonymous role's grants bound every read (I12). REST: `GET /v1/protocol`, `GET /v1/cells/{h3}`, `GET /v1/cells?within={h3}&limit=`, `GET /v1/releases/latest`, `GET /v1/openapi.json`. Cells finer than resolution 8 are refused: GSIP publishes nothing finer, so a finer question only reveals more about where the asker is. MCP over Streamable HTTP at `POST /mcp` (stateless JSON responses) with tools `get_protocol`, `get_cell`, `list_cells` and `get_release`. Every response carries license, attribution and citation fields; free text appears only in fields marked untrusted. Best-effort per-client rate limit with a per-instance ceiling, and cache headers. Request logic lives in `packages/schema/src/agent/`.
2. **Releases.** `dataset_releases` (public read, service-role insert), written by export after each successful push.
3. **Site.** Prerender every page at build time and hydrate in the browser; static Dataset and Organization JSON-LD; `llms.txt` at the site root; `docs/AGENTS.md` for agent builders.

Acceptance criteria:

- [ ] vitest: REST handlers validate H3 input, return only public fields with license and citation, and answer unknown cells with "no published observations" without distinguishing withheld from empty.
- [ ] vitest: MCP `initialize` negotiates a supported protocol version; `tools/list` returns four tools with JSON Schemas; `tools/call` returns structured and text content; malformed requests return JSON-RPC errors; notifications return 202.
- [ ] vitest: people-written text appears only inside untrusted fields.
- [ ] pgTAP: the anonymous role can read `dataset_releases` and `h3_cells` and nothing private; a test fails if the function source references the service role.
- [ ] Build check: every built site page contains its headline and JSON-LD without JavaScript, and `llms.txt` is published at the root.

**WP-APP-1: GSIP phone app**
Scope:

1. **Capacitor** in `apps/capture-pwa` (`appId com.globalsoilintelligence.app`, web directory `dist`) with the core, camera and geolocation plugins. The geolocation plugin is included on iOS only: on Android it compiles in Google's closed Play services location SDK (guardrail 6), so the Android app uses the web view's location API, which asks for the same permissions.
2. **Platform layer** (`src/platform/`): native or web camera (normalized to the queue's JPEG photo shape), geolocation (accuracy and source), an attestation-provider interface (`none` until a server verifier exists), and the `app` ingest-path claim.
3. **My Soil**: the signed-in contributor's submissions with date, status, shots and public cell, read through RLS; never coordinates.
4. **Builds.** `app-build.yml` generates the iOS and Android projects from the Capacitor config, applies permission strings with a checked-in script, and builds an unsigned Android debug APK and an iOS simulator build as artifacts. Signing and store upload are out of scope.
5. **`docs/APP_STORE.md`**: permissions text, privacy labels, the in-app deletion path (WP-6d), no in-app purchase for physical goods, review notes.

Acceptance criteria:

- [ ] vitest: the platform layer selects native implementations on native platforms and web ones otherwise; native camera output becomes a JPEG queue photo; geolocation maps accuracy and source.
- [ ] vitest: My Soil lists only the signed-in contributor's submissions and renders no coordinates.
- [ ] `app-build.yml` produces the Android debug APK and the iOS simulator build.
- [ ] The app requests only camera and when-in-use location permissions, each with a purpose string.

### Merged v4.0 specification follow-ups — separate implementation PRs

The following packages schedule SPEC §15 without claiming it has been approved or implemented. Owner-approved policy decisions are recorded there. Capture and production anonymous sign-in remain closed. The specification PR carries no code, dependencies or migrations. Follow-up branches stack after WP-APP-1 until the existing stack merges, with this specification amendment as the first change for the new architecture. Already-authorized WP-APP-2A CI/Android backup preparation may be built and reviewed against this proposal after its specification commit; its merge follows specification approval. Notification architecture remains a proposal, and screening implementation has the stronger explicit approval-and-merge gate below. Justin retains final review and merge authority; the documented owner exception permits an explicitly authorized agent to execute ordered merges after green CI, without submitting an approving review.

**WP-APP-2A: Account-free app build readiness and private backup exclusions**

Branch: `wp-app-2a-build-readiness`. Scope: validated CI build numbers and one marketing-version source; source/toolchain/lockfile/artifact receipts and honest reproducibility comparisons; Android exclusion of private queue, photo and session stores from cloud backup, with direct device transfer allowed only under tested cloud/transfer separation; otherwise exclude both. Update the app-store checklist to distinguish Android artifact evidence from iOS readiness. No signing, store accounts, keystores, deep-link account setup or store submission.

Acceptance criteria:

- [ ] Tests reject invalid/out-of-range build numbers and verify that both generated platform configurations use the declared marketing/build versions; CI reads the values back from the built APK and simulator app.
- [ ] CI records input versions/digests and artifact hashes. A repeated build with the same inputs records either byte equality or explicit normalized-content differences; do not call an ordinary successful build reproducible.
- [ ] Tests cover legacy Android backup rules, current cloud-backup/device-transfer rules and effective manifest wiring. The compiled app excludes WebView private storage and draft photos from cloud backup; a synthetic device backup/transfer check is required before claiming device protection.
- [ ] Android 12+ direct device transfer may preserve private queue/session storage only if cloud and transfer rules are cleanly separated and synthetic checks prove the cloud channel excludes all private stores. Legacy Android or unproven separation excludes both. A fresh install/cloud restore starts a new anonymous account; verified direct transfer may preserve it.
- [ ] iOS backup protection is marked **blocked/unverified** until a separately specified reliable method passes synthetic real-device backup/restore checks. A no-cloud filesystem directory does not exclude existing IndexedDB/localStorage. Any storage migration requires its own architecture review and regression tests; any new native-language code requires Justin's exception first.
- [ ] Existing permission and Android `check-dependencies` checks pass unchanged in strength; no new dependency/service or signing secret is needed.

**WP-APP-2B: Local sync reminders in version 1 (proposal)**

Branch: `wp-app-2b-local-notifications`. Depends on approved SPEC §15 and WP-APP-2A. Version 1 schedules opt-in on-device sync reminders only, using `@capacitor/local-notifications`, with no push service or location calculation. Nearby suggestions are deferred until Most Wanted and land-access eligibility inputs exist; their later implementation needs its own reviewed scope under SPEC §9. Notifications contain no private payload and do not invite contribution with capture closed. [The proposed plugin audit](PHOTO_PRIVACY_SCREENING.md#notification-candidate) must be refreshed for the pinned version in the implementation PR.

Acceptance criteria:

- [ ] Behavior tests cover opt-in, denial, unsupported/web fallback, queue-empty/no-repeat behavior, cancellation after sync/deletion/withdrawal/sign-out, capture-closed behavior and notification actions through existing access checks.
- [ ] Tests prove version 1 never computes, schedules or exposes nearby targets and adds no location request, coordinate upload, background geolocation or land-access/minor targeting. The deferred follow-up must establish Most Wanted and land-access eligibility before any nearby suggestion.
- [ ] Generic notification text and opaque identifiers contain no location, photo, contributor name, token or private queue metadata; copy does not equate a withheld public cell with an unobserved cell.
- [ ] Inexact scheduling works without `SCHEDULE_EXACT_ALARM` or `USE_EXACT_ALARM`; compiled-permission tests cover removal of plugin defaults and only needed notification/boot/wake additions.
- [ ] Android `check-dependencies` still rejects proprietary SDKs. List the chosen plugin's code license, release/maintenance signal, compressed/unpacked size and measured APK impact; inspect transitive dependencies rather than assume the plugin name proves compliance.
- [ ] Android/iOS synthetic device evidence covers permission prompts/denial, scheduled reminder delivery and cancellation. Unsupported behavior is documented honestly; no claim of App Store guideline 4.2 acceptance follows from an artifact build.

**WP-6f: Every-photo publication privacy screen — source merged; deployment and calibration gated**

Branch: `wp-6f-photo-privacy-screening`. Justin's chosen policy is server-side open-detector screening of every photo, with individual flagged photos withheld for private human CLI review and no automatic blur. Start with face and scene-text screening. Until WP-6f is deployed and Justin approves calibration evidence, releases contain structured data only under the SPEC §11 photo-publication gate; passing existing QA or individual review cannot bypass it. After that gate, eligible observation data and other cleared photos proceed normally. **The specification approval and merge prerequisite was satisfied in #38.** WP-6fA/B/C source is merged in [#53](https://github.com/global-soil-intelligence/gsip/pull/53), [#54](https://github.com/global-soil-intelligence/gsip/pull/54) and [#55](https://github.com/global-soil-intelligence/gsip/pull/55); unresolved weight licenses, uncalibrated category coverage and separate production authorization remain gates. See SPEC §15.4 and [the detector comparison](PHOTO_PRIVACY_SCREENING.md).

Acceptance requirements for source and separately gated deployment:

- [ ] Migration/pgTAP tests give every existing/new photo a pending private publication state, reject client clearance, bind clearance to content/version evidence and preserve RLS strength. QA settlement remains independent of privacy withholding.
- [ ] Worker tests cover every sanitized/oriented A/B/C photo. Face screening covers the entire frame. Scene-text may exclude only the detected GSIP reference-card quadrilateral plus a bounded margin from the existing marker homography; screen the entire remainder of the frame. With no reliably localized card, screen the entire frame. Tests cover text immediately outside the margin, rotation/partial cards and failed localization; no soil-region mask or other context exclusion is used. Retries are bounded/idempotent; detector errors, unsupported input and ambiguous detections withhold only that photo.
- [ ] Export/release/training tests reject pending/review/error/withheld photo bytes, shards, thumbnails and URLs; eligible structured data and other cleared photos survive a privacy flag, including an empty-photo observation. Existing QA, finalized A/B, grant, withdrawal, provenance, holdout and k-anonymity checks still apply.
- [ ] Private CLI tests reject unauthorized review, preserve audit decisions, suppress private payloads from logs and prevent withdrawn content from reappearing. Only explicit human clearance can overturn a flagged result; no automatic blur exists.
- [ ] Every code/runtime dependency and exact model artifact has verified separate licenses, source/payload digest, maintenance signal and size. An MIT wrapper cannot imply an MIT weight license; unresolved artifacts cannot be deployed.
- [ ] Before photo publication, WP-6f is deployed and Justin approves calibration evidence from private synthetic/staged evaluation: per-category sample counts, misses/false positives and uncertainty, high-recall thresholds and unsupported cases. Start with face and scene-text screening; add a dedicated plate detector only if staged evaluation exposes a material gap and its exact artifact has verified code and weight licenses. No claimed GSIP recall is borrowed from an upstream benchmark; an ineligible unselected plate candidate does not become a mandatory dependency.
- [ ] Contributor-facing/legal copy explains individual photo withholding, private review and residual privacy limits, subject to counsel review. Any immutable older release is identified honestly; no retroactive erasure claim.
- [ ] No raw images, precise points, OCR strings or private screening metadata enter public fixtures/reports, CI logs or agent surfaces; I7/I11/I12 tests cover the new path.

**WP-6f implementation details (merged v8 architecture, SPEC §15.5–15.9):** `docs/spec-v8` → `wp-6fa-private-photo-privacy` → `wp-6fb-photo-privacy-worker` → `wp-6fc-photo-export-enforcement`, separate independently reviewed PRs with green CI. The architecture is merged in [#52](https://github.com/global-soil-intelligence/gsip/pull/52), and the three source packages are merged in #53–#55 after their specification/predecessor prerequisites. Owner-authorized code merges supply no production migration, dispatch, model approval, operator credential or photo-publication permission.

| Package    | Deliverable                                                | Acceptance refinements                                                                                                                                                                                                                                                                                                                                                                                                     |
| ---------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **WP-6fA** | Additive private SQL state, worker/review/export authority | Every existing/new photo starts pending; private restrictive RLS/direct table deny; immutable content/policy/audit bindings; default-closed owner-admin publication gate; SQL-standard service-only invoker wrappers; exact bounded RPC shapes; contributor-first rights cleanup and honest old-worker completion. No detector selection or remote worker dispatch.                                                        |
| **WP-6fB** | Detector adapter, bounded worker and private operator CLI  | Exact configured model/configuration digests; actual sanitized-byte digest registration before current-lease screening; whole-frame face and bounded homography card exception for scene text; five-attempt/300-second lease bound; generic logs; personally authenticated review with server-derived live operator identity. No auto-blur, public review interface or calibration approval.                               |
| **WP-6fC** | Structured-only compatibility and photo export enforcement | Old/missing schema or closed/unapproved gate loads no media and emits empty photo lists. Current clear source/policy required; exact staged bytes hashed and freshly service-authorized immediately before artifact promotion and any separately authorized publication. Changed bytes/versions/manual review/rights remove photos; eligible structured rows survive. No publication dispatch or new training eligibility. |

Additional acceptance for the three implementation PRs:

- [ ] A schema/RPC manifest fixes the exact service-only entry-point grants. `anon`/ordinary `authenticated` cannot call capabilities, worker, receipt, review or export authorization or clear via direct writes; no private schema exposure or public screening field is added. Existing client-RPC allowlists and capture fixtures remain exact.
- [ ] Existing-data migration tests preserve public rows, QA/settlement, source paths, capture gates, rights-worker signatures and existing RLS, while every legacy/new photo begins pending with no fabricated digest. Content/version changes invalidate detector/manual clearance; permanent human withholding remains binding to the photo UUID across content/policy generations and human retries, with no reversal API. Stale lease, lost response, unknown revision, conflicting receipt UUID and policy revision regressions fail closed.
- [ ] Real concurrent tests cover claim/registration/completion/review/authorization versus withdrawal in both orders, consistent contributor-first locking and claim `SKIP LOCKED` order, stale content/policy races, tombstones, and completion refusal for every residual private content/job/screen/review row. No long SQL lock is held across image processing or network publication.
- [ ] Runtime/detector evidence separately records every exact code/weight license, source digest, maintenance and payload/runtime size. Benchmark candidates and upstream performance remain unapproved; owner-admin policy/calibration approval records require the exact immutable manifests and separate owner go.
- [ ] Personal operator token is exactly 64 lowercase hexadecimal characters from 32 cryptographically random bytes, env/secret-store-only, hashes to a live private allowlist mapping and server-derived opaque reviewer. Only Justin's owner-admin provisioning may create/revoke/reassign operators after a separate production go. Service keys cannot provision/reassign operators, approve calibration/policies or open publication through an RPC/private CRUD grant. Revoked token, missing/deleted user, wrong operator, stale content/version and client-call tests refuse review; audit append-only and erasure tests pass.
- [ ] Private synthetic/staged evaluation covers every A/B/C shot, tiny/occluded faces, varied skin tones, full frame including card, text/plate/numerals immediately outside the bounded mask, rotation/partial cards and failed/ambiguous localization. Bound private exclusion-mask dimensions/count/SHA256/margin evidence to the exact screen receipt; no face/text boxes/OCR/crops enter it. Missing coverage or detector/decode errors cannot produce clear. Human false-positive review cannot clear an unsupported/missing screen, permanently withheld photo or open the gate.
- [ ] Export tests prove no download against an old schema or closed gate; no pending/review/error/withheld bytes, shards, thumbnails or URLs; metadata/path failure handling; actual staged-byte SHA256 comparison including changed bytes from a second sanitizing JPEG encoding; late content/policy/review/withdrawal mutations before promotion/publication; same-date/previous artifact reuse after gate closure; and intact eligible structured rows with no photos. Preserve publish-ready canonical bytes exactly. A cached receipt, pixel equivalence, old artifact or manual decision never substitutes for fresh authorization.
- [ ] Logs, fixtures, review transport logs/errors and CI artifacts contain no real images, raw uploads, OCR strings, precise points, arbitrary incoming values or operator tokens. The personal token is allowed only in the private authenticated RPC request body over protected transport, never a URL or transport log. I7/I11/I12 and existing field-training/publication gates remain enforced. Local passes establish code behavior only; calibration, production migration/worker deployment, operator provisioning and gate opening are separately evidenced owner actions.

Remaining **WP-APP-2 store-release scope** stays gated: Apple/Google accounts, signing, store listings and deep links require Justin's accounts and decisions. No account, certificate or keystore is created by WP-APP-2A/2B.

### Phase 1.5a — Follow-ups independent of production deployment

**WP-DOC-1: Merged source status and remaining readiness gates**

Scope: update only `README.md`, `docs/SPEC.md` and this build order with verified merged-source/specification status and PR links. This factual documentation package adds no architecture, runtime behavior, dependency or future implementation promise. Acceptance: every completion claim is bound to a merged PR present on `main`; existing documentation link, language and formatting checks pass; all existing acceptance boxes, invariants and deployment/calibration/operator/model/photo/capture/real-peer/scientific/device gates remain intact. Source and CI verification never supplies external-readiness evidence.

**WP-AGENT-0: Coding-agent guidance**
Scope: add root `AGENTS.md` for repository contributors, linking the public-reader guide at
`docs/AGENTS.md`; collect the invariant, reviewed-stack, privacy, verification and per-step
production-authorization rules. This is documentation of existing authority, not an architecture
change or deployment permission.

Acceptance criteria:

- [ ] The root guide distinguishes coding agents from public API consumers and links every
      read-first governing document.
- [ ] A documentation usability test proves the local links and documented repository check
      commands resolve; it fails without the guide.
- [ ] Formatting and language checks pass; no dependency, licence, workflow or production change.

**WP-3b: Cross-tab queue sync**
Scope:

1. Coordinate the existing queue drain with the origin's exclusive Web Lock `gsip-sync`, requested with `ifAvailable: true`. A context that cannot acquire it returns immediately without reading or changing the queue.
2. Hold the lock until the complete drain settles, including queue writes and failures. Browsers without Web Locks keep the current drain behavior; existing per-screen trigger coalescing and retry scheduling continue.
3. Preserve account binding, withdrawn-record removal, queue-generation checks, terms reconfirmation, backoff and dead-letter handling. No data, credential, capture-gate or dependency changes.

Acceptance criteria:

- [ ] vitest: overlapping tabs sharing a queue send each record only once with Web Locks; an unavailable lock causes no queue reads, writes or sends.
- [ ] vitest: a queue exception releases the lock so a later drain can acquire it; browsers without Web Locks retain the existing behavior.
- [ ] Existing queue, ownership, terms, rights and startup-sync tests pass.

### Phase 1.5b and Phase 2+ (specified after launch review)

WP-AGENT-2 delegated capture for assistants (scoped tokens, consent screen, path-bound upload URLs) · WP-APP-2 store release of the phone app (deep-link e-mail sign-in, icons, signing and store listings; `docs/APP_STORE.md`) · WP-7 QA gate model (slots into the WP-4b/6b interface) · WP-8 estimator v0 · WP-9 nightly retrain and model cards · WP-10 estimate API · WP-11 gold-label bulk ingestion and gold kits · WP-12 fused correction and Most Wanted layers with information-gain credit · WP-13 SoilGrids file sampler replacing the REST dependency · WP-14 silver-label protocols · WP-AGENT-3 verifier task API with I13 consensus · WP-AGENT-4 evaluation service (I15) · WP-DATA-1 Parquet photo shards, Croissant metadata and PROV provenance · WP-OPS-1 event-driven worker queue.

### Library-first implementation sequence (SPEC §16)

The spectral library is the primary asset. The existing capture, QA, rights and provenance infrastructure remains the collection foundation; priors and the map are downstream context. Do not train an estimator on unpaired imagery and imply measured spectra or biological ground truth.

| Package       | Deliverable                                                       | Acceptance and dependencies                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **WP-LIB-1**  | Private sample/measurement contract and runnable local node store | Strict versioned validation; RGB distinct from reflectance; dimensions/units/calibration/source hashes; immutable idempotent imports; conflicting UUID rejection; private filesystem; sample-wide tombstones; generic logs; synthetic tests. No credentials, network or public release.                                                                                                                                       |
| **WP-LIB-2**  | Smartphone-photo optical extraction                               | Sanitization, orientation and sRGB conversion reuse; detected card excluded with margin; mean/dispersion/pixel count/source hash; no card is explicit unknown and all outputs uncalibrated; reject insufficient soil region; synthetic fixtures prove masking and deterministic output. Depends on LIB-1. Offline staged utility only while WP-6f remains gated.                                                              |
| **WP-LIB-3**  | Paired dataset and reconstruction baseline                        | Same-sample RGB↔instrument pairing, aligned wavelength grids; sample-level disjoint partitions; rights/QA/holdout propagation; field vs synthetic separation; deterministic baseline and reproducibility receipts; honest development errors only. No public predictions, publication or hosted retraining. Depends on LIB-1/2; meaningful field evaluation awaits paired data.                                               |
| **WP-LIB-4A** | Shared caller contract and instrument parser                      | `gsip-library-intake-v1` strict envelope and bounded declaration JSON; UUID/context/band/unit validation; reject local rights/QA/holdout fields, unknown/duplicate fields and unsupported files. Shared synthetic TS/Python conformance corpus. No network, app activation or schema change. Depends on LIB-1/2/3 and reviewed v6 specification.                                                                              |
| **WP-LIB-4B** | Additive private hosted intake                                    | Service-owned private tables, caller-bound invoker RPC, independent closed gate, immutable idempotence/digests, owner/grant/actor checks, quota, withdrawal/tombstones and monotonic sample holdout. Existing-data/role/race tests; unchanged rights-worker RPC signatures. Receipts are stored private declarations only; original source and physical pairing stay unverified. Depends on LIB-4A.                           |
| **WP-LIB-4C** | Compatible phone sample form and queue                            | Optional sample depth/condition and strict JSON attachment; restart-safe draft IDs; staged/lost-response retry, legacy queues, original-account binding, discard/withdraw clearing, native backup coverage and false-by-default build flag. Capability absence holds safely without changing the legacy capture read or creating an account. Synthetic end-to-end unverified receipt and deletion test. Depends on LIB-4A/4B. |
| **WP-LIB-5A** | Strict private exchange event contract                            | Approved v9 contract; bounded typed declare/retire envelopes, exact-byte retries/conflicts and synthetic conformance. No authority, network, secret, real export or scientific verification.                                                                                                                                                                                                                                  |
| **WP-LIB-5B** | Local private ledger and rights simulator                         | Recipient-scoped aliases, private filesystem, priority bounded cleanup, durable refusals and honest acknowledgments under fake authority/transport. Synthetic-only; no real peer exchange. Depends on merged 5A and reviewed/green/merged v10 local accounting clarification.                                                                                                                                                 |
| **WP-LIB-5C** | Scoped peer authority and transport (held)                        | Separate owner-approved private-sharing, peer, credential/cleanup and cross-contributor decisions first; fresh original rights, additive role/migration/race tests and synthetic end-to-end evidence. No default private/public rollout or training.                                                                                                                                                                          |
| **WP-LIB-6**  | Scientific reference adapters and evaluation                      | Lab/biological assay vocabulary, licensed instrument adapters, paired field pilot, sealed spatial/device holdout, uncertainty calibration and model card. Device spectral hardware is optional; no closed SDK without approval. Requires real verified reference data and expert review.                                                                                                                                      |
| **WP-LIB-7**  | Eligible library releases and map integration                     | Fingerprinting/linkage privacy evaluation, k-anonymity, consent/withdrawal checks, photo gate, licenses, dataset card and approved release pipeline; map advertises measurement basis and uncertainty. No individual spectral release by default.                                                                                                                                                                             |

New dependencies: none for LIB-1/2/3 or the proposed LIB-4A/4B/4C path; use the existing locked TypeScript validation stack, Pydantic, NumPy/OpenCV and Pillow plus standard libraries/Postgres. Instrument/model/detector dependencies in later packages require license (including weights), maintenance and payload-size audits before adoption. The linear baseline is research plumbing; it does not supersede WP-8's estimator/evaluation gates. WP-11's gold-label ingestion and WP-DATA-1 join the library contract rather than a competing identity system.

The v5 foundation sequence is `docs/spec-v5` → WP-LIB-1 → WP-LIB-2 → WP-LIB-3. The next sequence is `docs/spec-v6` → `wp-lib-4a-intake-contract` → `docs/spec-v7` (additive rights integration and durable refusal identities) → `wp-lib-4b-private-intake` → `wp-lib-4c-phone-intake`, as separate PRs in that order. Implementation can be prepared after the specification commit, with no merge before its prerequisite and independent review/green CI. Execute only owner-authorized merges; this order supplies no deployment, worker dispatch, capture opening or release authority. LIB-5B additionally awaits the reviewed v10 local clarification; LIB-5C/6/7 still need their separate scientific/privacy specifications and prerequisites.

**WP-LIB-4A acceptance (SPEC §16.5):**

- [ ] Strict envelope/declaration parser accepts only the specified IDs, version, context and optional instrument payload; all local verified-state, label, URL, timestamp and arbitrary-file fields are refused.
- [ ] Reject duplicate/unknown keys, invalid UUIDs, non-finite values, malformed/misaligned/non-increasing bands, unsupported units and input above 2,000,000 UTF-8 bytes before full parsing.
- [ ] Shared valid/invalid synthetic corpus proves TS parser and Python instrument-validator agreement; ordinary local `gsip-library-v1` files are not silently promoted into hosted requests.
- [ ] No dependencies, network, private data, app activation or database changes; no weakening of LIB-1/2/3's field-training/photo gates.

**WP-LIB-4B acceptance (SPEC §16.6–16.7):**

- [ ] Fresh additive migration creates RLS-protected, service-owned private tables, durable tombstones and an independent default-closed gate; no exposed private schema or direct client table privilege.
- [ ] `library_intake_capabilities()` returns exactly `{version: 'gsip-library-intake-v1', available: boolean}`; `record_library_intake(p_request jsonb)` and `my_library_intake_receipt(p_intake_id uuid)` return only the specified safe receipt. Public wrappers are invoker with definition-time bound private dispatch and narrowly granted execution.
- [ ] pgTAP covers anon, owner, another contributor and service roles; server structural/bound/quota validation; live auth/actor/grant/submission/photo ownership; forbidden authority fields; absent/closed gates; identical retry and conflicting UUID/context/source requests.
- [ ] Instrument source/calibration and physical-pair verification stay pending; no positive verification API, field RGB extraction, labels/adapters, new generic Storage, public release or training path.
- [ ] Rights tests prove shared-lock serialization against intake/withdrawal, immediate invalidation, tombstones before payload erasure, no revival, monotonic sample holdout and no owner-visible seal/label/evidence leakage.
- [ ] Existing-data migration tests preserve legacy rows, grants and function signatures, keep capture/auth/gates closed, create no acceptance backfill and prove an older rights worker cannot complete a request while library payload remains.
- [ ] Existing worker/export/public-reader suites stay green; library fields never reach agent APIs, export, map aggregates or ordinary model preparation.

**WP-LIB-4C acceptance (SPEC §16.8):**

- [ ] Optional form accepts explicit depth/condition and one strict JSON instrument declaration; private IDs/metadata/bytes survive draft restart and queue upgrade without inventing library records for legacy observations.
- [ ] Tests prove exact retries after partial upload or lost response, capability absence/unsupported service as a non-consuming hold, terminal conflict handling, withdrawal rejection and no premature queue removal.
- [ ] Account-switch tests prove immutable namespace/owner binding, new namespace for new-account captures and no silent reassignment through bulk held-record release.
- [ ] Queue/draft clear and withdrawal/account deletion erase new private bytes, with generation/cross-tab race tests and compiled native backup assertions.
- [ ] `VITE_LIBRARY_INTAKE_LIVE=false` default preserves existing UI and sends no new RPC; capability probing does not change the legacy gate query or trigger anonymous sign-in. Actual intake also requires compatible capabilities, server library gate and existing capture gates.
- [ ] Synthetic end-to-end capture → queued sample → owner-private unverified receipt → exact retry → withdrawal/deletion succeeds; the test artifact stays local, and the actual app/Pages artifact is rebuilt with both build flags false.

**Approved local LIB-5 sequence (v9 and merged v10 §16.12 clarification):** merged `docs/spec-v9` → `wp-lib-5a-exchange-contract` ([#58](https://github.com/global-soil-intelligence/gsip/pull/58)) → `wp-lib-5b-private-exchange-ledger` ([#64](https://github.com/global-soil-intelligence/gsip/pull/64)), with the reviewed/green/merged `docs/spec-v10` ([#60](https://github.com/global-soil-intelligence/gsip/pull/60)) prerequisite satisfied before LIB-5B. Justin approved the local v9 architecture on 2026-10-13. v10 resolves only the four local simulator ambiguities; it changes neither LIB-5A's approved contract nor the unresolved real-sharing policies and transport in LIB-5C. Each package is a separate PR with independent adversarial review and green CI. `wp-lib-5c-scoped-peer-transport` remains blocked until the new source-sharing/privacy, peer-admission, credential/cleanup and same-material policy decisions are resolved. Preparing synthetic local code never permits real exchange, peer enrollment, production migration, deployment, public release or field training. Existing public readers remain anonymous/read-only and no service-role key or contributor session reaches an agent interface.

**WP-LIB-5A: Strict private exchange event contract**

Branch: `wp-lib-5a-exchange-contract`. Depends on the approved v9 amendment and existing LIB-1/4 contracts. Implement only the exact `gsip-node-exchange-v1` parser, exact-byte integrity/idempotency convention and synthetic TS/Python conformance corpus. No network, secret, listener, schema migration, real record export or scientific verification. Keep phone/library namespace distinct from an enrolled federation peer.

- [ ] Strict byte-only UTF-8 parsing proves 2,000,000-byte and 12-container limits before unsafe allocation; rejects BOM, malformed UTF-8, unpaired surrogates and fractional/exponent/negative-zero integer spellings; unknown/duplicate fields, non-finite values, wrong types/UUIDs, unsafe sequence numbers and unsupported versions are refused generically.
- [ ] Both event variants accept only SPEC §16.10 fields; context and camera/instrument payloads retain LIB-1's units/bounds and RGB-versus-spectrum distinction. Raw files, images, precise/time/device-serial/person/path/URL/credential fields and caller authority/labels are rejected.
- [ ] Exact retries retain identical transmitted bytes and digest. Same event identity with different bytes conflicts; no unproved cross-language canonical-number/signature claim.
- [ ] Stream tuple and immutable event/sequence-slot ownership are explicit; the committed digest head advances only through verified contiguous predecessors. Out-of-order retirement restricts immediately without inventing chain progress; unrecoverable gaps remain held.
- [ ] Synthetic tests fail without rejection, including malformed/deep/oversized input, fake rights/provenance, conflicting event/measurement identity, stable identical retries, immutable sample/scientific binding, monotonic synthetic restriction and incorrect previous digest. Parser success remains an unverified declaration, never a credential, permission or physical-pair receipt.
- [ ] No dependency or license change; no change to capture, photo publication, public APIs, local field baseline or production configuration.

**WP-LIB-5B: Local private exchange ledger and rights simulator**

Branch: `wp-lib-5b-private-exchange-ledger`. Depends on merged LIB-5A and independently reviewed/green/merged v10 §16.12. Implement one deterministic synthetic-only draft/outbox/receiver simulator per operator-designated private root with fake authority and transport; do not add a real sender, downloader, peer listener, automatic contributor-directory scan or field-data export. A locally stored record's verified-state declarations and LIB-5A supplied-fact helpers cannot be treated as source authority. The synthetic-only source is merged in [#64](https://github.com/global-soil-intelligence/gsip/pull/64); source/CI verification supplies no real-sharing, scientific or production readiness.

- [ ] Operator-designated private storage enforces the configured allowed root, directory/file permissions, regular single-link payloads, no-follow reads, atomic writes and locks. Tests reject symlink/traversal/special/multi-link paths and conflicting IDs. Shared/cloud folders are prohibited by operator policy; no claim of exhaustive provider detection.
- [ ] Recipient/scope-specific handles are allocated once and remain tied to the same original simulated lineage. Repeated copies never increase independent sample/contributor counts; only within-owner known aliases group, and unverified physical pairing remains held.
- [ ] Tests prove synthetic/restricted/withdrawn inheritance across every known alias, no unsealing or identity revival, gap/disconnection holds, exact retries, conflict stop and late declaration refusal after a retirement received first.
- [ ] Minimal immutable tombstones precede erasure of draft/context/measurement/preparation payload. Acknowledgment requires absence of covered simulated payload. Unknown/lost acknowledgment stays pending; receipts do not claim immediate distributed deletion.
- [ ] Daily admission proves independent source/outbox and recipient 100-per-original-fake-human/UTC-day views across scopes, persisted first durable charge including recipient quarantine, free exact retries across restart/midnight, charged distinct repeated-measurement events, no charge on refused admission and no refund after accepted-event erasure. Twenty-event batches, five-attempt backoff and priority cleanup remain bounded; cleanup ignores spent contribution allowances. No network/upstream calls; logs contain only counts and generic classes.
- [ ] SPEC §16.12 aggregate scope/declaration/gap/slot/refusal/cleanup capacities and the existing 200,000,000 queued-byte cap apply across all managed state in the single root before writes. A separate 200,000,000 retained-managed-payload-byte cap counts every source/recipient event copy, scientific/context payload, draft and synthetic preparation until verified absence; claim/dequeue/receipt never frees remaining file bytes. Separate roots confer no shared authority/global-quota claim.
- [ ] One complete authoritative metadata image is at most 32,000,000 encoded bytes; at most current plus one replacement image coexist, with one staged payload blob at most 2,000,000 bytes per transaction. Recover/refuse unfinished work before more staging, keep all files under private/no-follow/single-link/atomic/locking rules, and refuse generically without eviction at metadata saturation. Boundaries, simultaneous reservations and interrupted writes/erasure are tested; no unbounded metadata history/staging accumulates.
- [ ] Before declaration admission, every enrolled scope reserves permanent fence state and a generic pending-erasure marker plus their metadata budget in its existing at-most-100 scope record, separate from alias-refusal/cleanup capacities. Tests exhaust alias, slot and cleanup storage: fence activation allocates no new such record, no partial payload or tombstone eviction occurs, all scope declarations/use remain held, and completion stays pending until exact covered absence is verified. No normal retry/dequeue reopens the fence.
- [ ] Retired declaration bytes and derived scientific/context files are erased; private integrity digests are separate from minimal refusal identities and supply no anonymity or remote-erasure claim. Real digest/lineage retention remains a LIB-5C owner/legal/privacy hold.
- [ ] Existing LIB-1/2/3 and hosted/phone tests remain intact; no real-source authorization, dependency, public release, physical verification, training, worker dispatch or production change.

**WP-LIB-5C: Scoped peer authority and transport — owner-policy hold**

Branch: `wp-lib-5c-scoped-peer-transport`. Depends on LIB-5A/5B, original-source/physical-reference verification in LIB-6 where claimed, approved legal/private-sharing purpose, peer admission, exact credential/cleanup lifecycle and the SPEC §16.13 choices. Its architecture detail and real-source implementation require a subsequent reviewed amendment after those choices; do not fill the gaps with an invented token or trust scheme.

- [ ] Record Justin/counsel's recipient-specific consent/purpose/retention/privacy decision, peer registry authority, exact credential/cleanup mechanism and policy for different contributors claiming the same material. No existing public-photo grant is silently repurposed.
- [ ] Fresh authority derives original grant/terms/licenses/contributor/source relationships and restrictions; scoped live human-of-record credentials can neither reach another owner/recipient nor assign QA, provenance, labels, holdout or publication permission. Generic unavailable receipts reveal no hidden evaluation membership.
- [ ] Source and receiver recheck current rights before admission/use; expired/missing/disconnected authority holds data. Deleting or revoking a contributor never restores their old session/token to deliver cleanup; separately scoped steward cleanup is authenticated and bounded.
- [ ] Additive SQL role/existing-data tests and real two-connection races prove contributor-first rights serialization, both operation orders, partial source locks, tombstones, unknown late records, recipient isolation and honest unchanged older-worker completion. No RLS weakening or captured acceptance backfill.
- [ ] Synthetic end-to-end enrollment/scope/transfer/retry/withdrawal/revocation/acknowledgment passes against fake/local adapters before a separately authorized real pilot. Count declarations, verified physical pairs, pending erasure and measured scientific evidence separately.
- [ ] No automatic training, map/model ingestion or spectral/photo publication. LIB-7's fingerprinting/privacy approval and WP-6f's deployment/calibration remain independent. Every new dependency/service/key location needs its existing audit/owner gate; all production commands wait for a separate exact-target go.

**LIB-5 assumptions and unresolved choices:** this proposal treats private peer sharing as a new unapproved purpose; known lineage identity as weaker than verified physical pairing; recipient handles as weaker than anonymity; and size/quota/retry values as provisional. Recommended rollout is owner-enrolled peers and explicit recipient opt-in, with same-owner aliases only and real sharing held until consent/privacy/credential decisions are approved. Released-data-only tools may remain public anonymous consumers; they are not evidence that private federation exists. Code and data licenses remain unchanged, no new default service/dependency is selected, and no program collects real samples or trains/publishes automatically.

**WP-SEC-1: Existing dependency security remediation**

Branch: `wp-sec-1-dependency-remediation`. Update the four confirmed vulnerable resolutions (source-map-js, xcode's UUID dependency, fsspec and multidict) to the smallest compatible patched versions. Keep frozen installation, package release-age policy, native dependency/permission checks and full-history secret scanning unchanged. Record exact advisory, license, maintenance/release signal and artifact size for each updated package. No new runtime capability, production change or new service.

- [ ] Frozen lockfiles install and resolve only patched versions of the four affected packages; explain any additional solver change.
- [ ] CommonJS Xcode tooling still generates project IDs with the scoped UUID upgrade; UUID boundary regression and the existing Python/web/native suites pass.
- [ ] Read back the repository's dependency-alert status after merge; do not call unavailable evidence zero findings.

## 5. Review gates (checked on every PR)

1. Acceptance criteria demonstrably met (CI evidence or reproducible commands, not claims).
2. Guardrails §2: automatic rejection on violation.
3. Invariant and guardrail impact honestly declared. I5 (language), I7 (privacy in rows, Storage, image bytes, logs and external calls) and I12 (agent surfaces) are checked on every PR regardless of declaration.
4. Tests test behavior (reviewers may run mutation spot-checks).
5. No scope creep: work outside the WP goes to a separate PR.
6. Each new dependency justified in the PR (license, maintenance, size).
7. Licensing boundaries explicit: ODbL 1.0 data, CC BY-SA 4.0 photos, MIT code. Public launch stays blocked until counsel approves the legal pack.

## 6. Environment variables (`.env.example`)

```
SUPABASE_URL=                    # project URL (GitHub variable: vars.SUPABASE_URL)
SUPABASE_PUBLISHABLE_KEY=        # public client key for server-side tools
SUPABASE_SERVICE_ROLE_KEY=       # server-only: workers and export; never in clients or agent interfaces
VITE_SUPABASE_URL=               # browser build of SUPABASE_URL
VITE_SUPABASE_PUBLISHABLE_KEY=   # browser-safe publishable key
VITE_CAPTURE_LIVE=false          # "true" opens capture in the site and the capture app
VITE_TERMS_URL=                  # published contribution terms (WP-6d)
VITE_PRIVACY_URL=                # published privacy notice (WP-6d)
VITE_SAMPLING_RULES_URL=         # published sampling and land-access rules (WP-6d)
VITE_PRIOR_TILES_BASE=           # PMTiles archive base URL; empty uses the ISRIC WMS fallback
VITE_DATASET_URL=                # published Hugging Face dataset URL
HF_TOKEN=                        # dataset push (CI secret)
HF_DATASET_REPO=                 # e.g. global-soil-intelligence/gsip-observations
OPEN_METEO_BASE=https://api.open-meteo.com
OPEN_METEO_ARCHIVE_BASE=https://archive-api.open-meteo.com
SOILGRIDS_BASE=https://rest.isric.org
VITE_GSIP_PUBLIC_API=            # deployed gsip-public URL for the site and llms.txt; empty until it answers
GSIP_PUBLIC_BASE_URL=            # gsip-public function secret: its public URL (default SUPABASE_URL/functions/v1/gsip-public)
GSIP_PUBLIC_RATE_LIMIT_PER_MINUTE=60   # gsip-public best-effort per-client limit
GSIP_PUBLIC_INSTANCE_LIMIT_PER_MINUTE=1200   # gsip-public ceiling per function instance across clients
```

## 7. Sequencing

`docs/spec-v3` → WP-6b → WP-6c → WP-6d → WP-6e → WP-AGENT-1 → WP-APP-1, as stacked pull requests merged in that order. WP-SITE-1D can happen at any time. The launch gates of SPEC §11 are checked after WP-6e merges; the product owner then sets `service_state.capture_open`. The read-only parts of WP-AGENT-1 may deploy before launch because they touch no contributor data. WP-3b is an independent queue follow-up stacked on WP-APP-1 until the reviewed stack merges.

Historical v4.0 review/merge sequence (#38 and WP-APP-2A have merged; remaining implementation and calibration gates still apply): WP-APP-1 → `docs/spec-v4` (Justin approval/merge) → WP-APP-2A → WP-APP-2B. Owner-authorized account-free WP-APP-2A preparation can start after the specification commit exists, while its PR remains stacked and awaits the merge sequence. WP-6f may be a separate branch after the approved specification, with no dependency on notifications, but stays blocked until that specification approval and its model/license/calibration gates. Retarget successors after Justin merges; merge main forward to resolve conflicts, never rebase or force-push the reviewed stack. §11 launch and production-command gates remain independent of this sequence.

## 8. Changelog

- **v10.0 (2026-10-13; clarification merged in [#60](https://github.com/global-soil-intelligence/gsip/pull/60)):** records only the four LIB-5B local accounting, reserved-fence, daily-admission and single-root clarifications in SPEC §16.12. Adds the reviewed/green/merged clarification as a 5B code prerequisite while keeping LIB-5A independent, all existing queued/capacity limits and all real-sharing/scientific/production gates. The specification amendment itself claims no implementation, new dependency or test evidence.

- **v9.0 (2026-10-13):** owner-approved local architecture splits LIB-5 into a strict local event contract, synthetic private ledger/rights simulator and separately held peer authority/transport. Flags unapproved private-sharing purpose, credential/cleanup and same-material policy; preserves anonymous readers and all scientific/privacy/production gates.

- **v8.0 proposed (2026-10-12):** defines separately reviewed WP-6fA private SQL authority, WP-6fB bounded detector/worker/personal-operator CLI and WP-6fC exact-byte export enforcement. Records default-closed owner-admin policy approval, contributor erasure, legacy structured-only compatibility and fresh actual-byte authorization, without detector selection/calibration, operator provisioning or production permission.

- **v6.0 proposed (2026-10-12):** splits private intake into LIB-4A caller contract/parser, LIB-4B additive hosted rights/holdout enforcement and LIB-4C compatible phone queue integration. Registers exact branches/acceptance and keeps original source-file/physical verification, field training, federation, production activation and publication outside these packages.

- **v5.0 proposed (2026-10-12):** library-first mission and seven explicit work packages, executable private foundations before hosted integration, federation and evaluated models. Existing launch/owner gates retained.

- **v4.0 (2026-10-12; specification merged in #38):** schedules account-free WP-APP-2A, sync reminders only in version 1 for WP-APP-2B, and gated every-photo screening WP-6f. Nearby suggestions wait for Most Wanted and land-access eligibility. Records the separate data-only publication gate, bounded card exception for scene-text, and evaluation/license conditions for a dedicated plate detector without claiming iOS protection, model recall or store readiness; WP-6f source subsequently merged in #53–#55, while deployment and calibration remain separately gated.
- **v3.0 (2026-10-10):** follows SPEC v3.0. Completed WP-0 to WP-6 summarized and archived. Added Phase 1.1 launch hardening (WP-6b ingest, QA and release integrity; WP-6c priors and tiles; WP-6d contributor rights; WP-6e provenance), Phase 1.5 (WP-SITE-1D, WP-AGENT-1, WP-APP-1) and the Phase 2+ outline. Added stacked-PR workflow, human-of-record DCO rule, guardrails 9 (I12) and 10 (B1–B8), updated environment variables, and review gates for I12.
- **v2.2 (2026-07-22):** anonymous sign-ins; immutable per-submission grants; canonical units and depth constraints; owner-prefixed quarantine paths.
- **v2.1 (2026-07-22):** builder changed to Claude; non-author approval plus product-owner go/no-go; WP-4b ingest QA; z8 native tiles; export metadata assertions.
- **v2.0 (2026-07-22):** initial build order, WP-0 to WP-6.

---

_Builder: read `docs/SPEC.md` in full before starting a WP. When in doubt, open an issue: a question costs minutes; an assumption costs a rebuild._
