# Phase 1 deployment handoff

Updated 2026-07-23. The governing scope is `SPEC.md` v2.2 and the ordered implementation is
`BUILD_ORDER.md`. Work packages are published as a protected, reviewable stack:

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
