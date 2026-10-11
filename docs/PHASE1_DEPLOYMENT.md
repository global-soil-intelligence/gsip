# Phase 1 deployment handoff

Updated 2026-10-10. The governing scope is `SPEC.md` v3.0 and the ordered implementation is
`BUILD_ORDER.md` v3.0. Phase 1 work packages WP0 to WP6 merged on 2026-10-01; the Phase 1.1 launch
hardening packages and their operator steps are listed at the end of this document. The original
Phase 1 stack was published as:

| Package | Outcome                                    | Pull request | Runtime state                                                             |
| ------- | ------------------------------------------ | ------------ | ------------------------------------------------------------------------- |
| WP0     | Monorepo, CI, Pages, governance            | #2           | Published branch                                                          |
| WP1     | PostGIS schema, RLS, private buckets, seed | #3           | Hosted actor grants, H3 containment, and role dependency documented       |
| WP2     | Deterministic A6 reference cards           | #4           | Nonlinear correction passes 10/10 hardened fixtures                       |
| WP3     | Offline capture PWA                        | #5           | Single-flight bounded retries and recovery UI ready for Pages             |
| WP4     | SoilGrids/SSURGO/Open-Meteo priors         | #6           | JWT Edge Function v3 and atomic service-role attempt claims active        |
| WP4b    | Deterministic private photo QA             | #7           | Six-field EXIF capture and coordinate guards ready; worker awaits secret  |
| WP5     | MapLibre public map and PMTiles path       | #8           | Hosted aggregate-only surface active; per-submission residue removed      |
| WP6     | Fail-closed Hugging Face export            | #9           | Hosted atomic refresh active; retries added; Hub awaits destination/token |

## Automated proof

- Python: Ruff, strict mypy over production and tests, 29 tests including hostile images, queue
  continuation, coordinate bounds, EXIF SubIFD capture, refresh recovery, and Datasets round-trip.
- Web: ESLint, language guard, Prettier, TypeScript, 27 unit tests, and production builds.
- Browser: two CI-aligned desktop Chromium journeys covering the map and offline hosted-path sync.
- Database: 48 pgTAP privacy, grant, RLS, queue, actor, worker, and export assertions.
- Hosted Supabase security adviser: zero findings after all Phase 1 migrations.
- Hosted prior worker: version 3 active with JWT verification; unauthenticated smoke returns 401.
- Map initial bundle: 1,642,860 bytes against the 5,242,880-byte limit.

## Remaining launch gates

These are intentionally not bypassed by code:

1. A non-author maintainer approves the stacked pull requests before protected `main` can merge;
   Justin then gives the product-owner go/no-go. No work package has been self-merged.
2. Complete legal review of the ODbL 1.0 / CC BY-SA 4.0 contribution terms, then confirm enabling
   anonymous sign-in in production Supabase.
3. Add `SUPABASE_SERVICE_ROLE_KEY` as a GitHub secret for the scheduled prior, photo-QA, and export
   workers.
4. Confirm the Hugging Face dataset owner/name, set `HF_DATASET_REPO`, and add `HF_TOKEN`. A privacy
   takedown also requires squashing or deleting the affected Hub history.
5. Publish native-z8 SOC/pH/clay PMTiles and set `VITE_PRIOR_TILES_BASE`; official ISRIC WMS is the
   launch-safe visual fallback.
6. Decide whether to upgrade Supabase before public Phase 1 traffic.

Once those gates are satisfied, merge the stack in order, run the Pages workflow, dispatch the photo
QA workflow, dispatch the nightly export, and complete the stranger-with-a-phone launch test.

## Phase 1.1 launch hardening: operator steps

### WP-6b — ingest, QA and release integrity

1. Create the repository variable `SUPABASE_URL`. Every worker workflow and the Pages build now read
   only this variable; delete `VITE_SUPABASE_URL` afterwards.
2. Apply the migrations (`supabase db push`). Capture is **closed** by default:
   `service_state.capture_open` starts `false`, and every grant, submission, photo and quarantine
   upload insert is refused until it is opened. Existing complete submissions are marked finalized
   and their per-photo QA verdicts are backfilled; public cells are cleared until the next export.
3. The `Quarantine cleanup` workflow runs hourly once merged. It needs the same
   `SUPABASE_SERVICE_ROLE_KEY` secret as the QA worker.
4. Add the CI `validate` job as a required status check in the `main` branch ruleset.
5. Open capture only after the SPEC section 11 launch gates pass, in two steps: build Pages with the
   repository variable `VITE_CAPTURE_LIVE=true`, then run, as the service role:

   ```sql
   update public.service_state set capture_open = true, updated_at = now() where singleton;
   ```

   Setting it back to `false` pauses capture immediately; queued observations wait on devices.

### WP-6c — priors and tiles

1. Apply the migrations, then redeploy the function so it picks up the import map and the pinned
   `verify_jwt = true` from `supabase/config.toml`: `supabase functions deploy prior-attach`. The
   function needs no new secret; the optional `OPEN_METEO_ARCHIVE_BASE` and `SOILGRIDS_BASE`
   variables override the public endpoints. Confirm in the dashboard that JWT verification is on.
2. Upstream buckets start full: SoilGrids holds one token refilled five times a minute (calls at
   least 12 s apart), SSURGO 30 a minute, Open-Meteo 60. To pause all prior lookups, set
   `refill_per_minute` very low in `upstream_buckets`; jobs simply defer and the drain waits within
   its budget.
3. Build the prior archives (`uv run python -m pipeline.build_prior_tiles --max-zoom 8`), publish the
   whole `output/tiles/<palette version>/` directory under one public base, and set the repository
   variable `VITE_PRIOR_TILES_BASE` to that base. The Pages deploy then checks that every archive
   exists and carries the palette version the legends use. Until the variable is set the map uses
   ISRIC's WMS with ISRIC's own legend.
