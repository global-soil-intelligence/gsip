# GSIP Build Order — Work Plan

**Project:** Global Soil Intelligence Project (citizen-science soil mapping flywheel for people and agents)
**Version:** 3.0 — 2026-10-10
**Pending amendment:** v4.0 draft — 2026-10-12. The additional packages below are proposed under SPEC §15; the reviewed v3.0 plan remains the baseline until Justin approves and merges the specification PR.
**Builder:** Claude (build sessions), acting for the product owner as human of record.
**Independent review:** every PR is reviewed by fresh-context adversarial review agents (no memory of authoring the code) against the §5 review gates; findings and resolutions are posted to the PR. Justin Hart provides the final product-owner go/no-go. On 2026-10-12 he approved an owner exception: the extra non-author GitHub approval is no longer required for this owner-operated repository. Independent adversarial review and green CI remain required; an agent never submits an approving review or certifies the human DCO.
**Product owner:** Justin Hart
**Governing document:** `docs/SPEC.md` (v3.0). If this document and the spec conflict, the spec wins; flag the conflict instead of guessing. The v2.2 work plan, with the full WP-0 to WP-6 acceptance criteria, is archived in `docs/archive/v2.2/`.

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

### Pending v4.0 follow-ups — separate implementation PRs

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

**WP-6f: Every-photo publication privacy screen — BLOCKED pending specification approval**

Branch: `wp-6f-photo-privacy-screening`. Justin's chosen policy is server-side open-detector screening of every photo, with individual flagged photos withheld for private human CLI review and no automatic blur. Start with face and scene-text screening. Until WP-6f is deployed and Justin approves calibration evidence, releases contain structured data only under the SPEC §11 photo-publication gate; passing existing QA or individual review cannot bypass it. After that gate, eligible observation data and other cleared photos proceed normally. **Do not implement, install detectors, add migrations or deploy this WP until Justin approves and merges this specification PR.** Even after that, unresolved weight licenses, uncalibrated category coverage and production authorization remain gates. See SPEC §15.4 and [the detector comparison](PHOTO_PRIVACY_SCREENING.md).

Acceptance criteria for the later implementation PR:

- [ ] Migration/pgTAP tests give every existing/new photo a pending private publication state, reject client clearance, bind clearance to content/version evidence and preserve RLS strength. QA settlement remains independent of privacy withholding.
- [ ] Worker tests cover every sanitized/oriented A/B/C photo. Face screening covers the entire frame. Scene-text may exclude only the detected GSIP reference-card quadrilateral plus a bounded margin from the existing marker homography; screen the entire remainder of the frame. With no reliably localized card, screen the entire frame. Tests cover text immediately outside the margin, rotation/partial cards and failed localization; no soil-region mask or other context exclusion is used. Retries are bounded/idempotent; detector errors, unsupported input and ambiguous detections withhold only that photo.
- [ ] Export/release/training tests reject pending/review/error/withheld photo bytes, shards, thumbnails and URLs; eligible structured data and other cleared photos survive a privacy flag, including an empty-photo observation. Existing QA, finalized A/B, grant, withdrawal, provenance, holdout and k-anonymity checks still apply.
- [ ] Private CLI tests reject unauthorized review, preserve audit decisions, suppress private payloads from logs and prevent withdrawn content from reappearing. Only explicit human clearance can overturn a flagged result; no automatic blur exists.
- [ ] Every code/runtime dependency and exact model artifact has verified separate licenses, source/payload digest, maintenance signal and size. An MIT wrapper cannot imply an MIT weight license; unresolved artifacts cannot be deployed.
- [ ] Before photo publication, WP-6f is deployed and Justin approves calibration evidence from private synthetic/staged evaluation: per-category sample counts, misses/false positives and uncertainty, high-recall thresholds and unsupported cases. Start with face and scene-text screening; add a dedicated plate detector only if staged evaluation exposes a material gap and its exact artifact has verified code and weight licenses. No claimed GSIP recall is borrowed from an upstream benchmark; an ineligible unselected plate candidate does not become a mandatory dependency.
- [ ] Contributor-facing/legal copy explains individual photo withholding, private review and residual privacy limits, subject to counsel review. Any immutable older release is identified honestly; no retroactive erasure claim.
- [ ] No raw images, precise points, OCR strings or private screening metadata enter public fixtures/reports, CI logs or agent surfaces; I7/I11/I12 tests cover the new path.

Remaining **WP-APP-2 store-release scope** stays gated: Apple/Google accounts, signing, store listings and deep links require Justin's accounts and decisions. No account, certificate or keystore is created by WP-APP-2A/2B.

### Phase 1.5a — Follow-ups independent of production deployment

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

Pending v4.0 review/merge sequence: WP-APP-1 → `docs/spec-v4` (Justin approval/merge) → WP-APP-2A → WP-APP-2B. Owner-authorized account-free WP-APP-2A preparation can start after the specification commit exists, while its PR remains stacked and awaits the merge sequence. WP-6f may be a separate branch after the approved specification, with no dependency on notifications, but stays blocked until that specification approval and its model/license/calibration gates. Retarget successors after Justin merges; merge main forward to resolve conflicts, never rebase or force-push the reviewed stack. §11 launch and production-command gates remain independent of this sequence.

## 8. Changelog

- **v4.0 draft (2026-10-12; awaiting product-owner approval):** schedules account-free WP-APP-2A, sync reminders only in version 1 for WP-APP-2B, and gated every-photo screening WP-6f. Nearby suggestions wait for Most Wanted and land-access eligibility. Records the separate data-only publication gate, bounded card exception for scene-text, and evaluation/license conditions for a dedicated plate detector without claiming iOS protection, model recall, store readiness or implementation approval.
- **v3.0 (2026-10-10):** follows SPEC v3.0. Completed WP-0 to WP-6 summarized and archived. Added Phase 1.1 launch hardening (WP-6b ingest, QA and release integrity; WP-6c priors and tiles; WP-6d contributor rights; WP-6e provenance), Phase 1.5 (WP-SITE-1D, WP-AGENT-1, WP-APP-1) and the Phase 2+ outline. Added stacked-PR workflow, human-of-record DCO rule, guardrails 9 (I12) and 10 (B1–B8), updated environment variables, and review gates for I12.
- **v2.2 (2026-07-22):** anonymous sign-ins; immutable per-submission grants; canonical units and depth constraints; owner-prefixed quarantine paths.
- **v2.1 (2026-07-22):** builder changed to Claude; non-author approval plus product-owner go/no-go; WP-4b ingest QA; z8 native tiles; export metadata assertions.
- **v2.0 (2026-07-22):** initial build order, WP-0 to WP-6.

---

_Builder: read `docs/SPEC.md` in full before starting a WP. When in doubt, open an issue: a question costs minutes; an assumption costs a rebuild._
