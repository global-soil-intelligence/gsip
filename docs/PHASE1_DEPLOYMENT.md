# Phase 1 deployment handoff

Updated 2026-07-22. The governing scope is `SPEC.md` v2.2 and the ordered implementation is
`BUILD_ORDER.md`. Work packages are published as a protected, reviewable stack:

| Package | Outcome                                    | Pull request | Runtime state                                                                      |
| ------- | ------------------------------------------ | ------------ | ---------------------------------------------------------------------------------- |
| WP0     | Monorepo, CI, Pages, governance            | #2           | Published branch                                                                   |
| WP1     | PostGIS schema, RLS, private buckets, seed | #3           | Hosted Supabase migration applied                                                  |
| WP2     | Deterministic A6 reference cards           | #4           | Pages artifact ready                                                               |
| WP3     | Offline capture PWA                        | #5           | Pages artifact ready; anonymous auth awaits owner confirmation                     |
| WP4     | SoilGrids/SSURGO/Open-Meteo priors         | #6           | Hosted migrations and JWT Edge Function active                                     |
| WP4b    | Deterministic private photo QA             | #7           | Hosted migration applied; worker awaits server-role secret                         |
| WP5     | MapLibre public map and PMTiles path       | #8           | Pages artifact ready; WMS fallback active until PMTiles release URL exists         |
| WP6     | Fail-closed Hugging Face export            | #9           | Hosted guardrail applied; push awaits Hub destination/token and server-role secret |

## Automated proof

- Python: Ruff, strict mypy, 13 tests including image sanitization and Datasets round-trip.
- Web: ESLint, language guard, Prettier, TypeScript, 16 unit tests, production builds.
- Browser: six journeys across mobile Chrome, mobile Safari, and desktop Chrome.
- Database: 32 pgTAP privacy, grant, RLS, queue, and export-marker assertions.
- Hosted Supabase security adviser: zero findings after all Phase 1 migrations.
- Map initial bundle: 1,436,278 bytes against the 5,242,880-byte limit.

## Remaining launch gates

These are intentionally not bypassed by code:

1. A non-author maintainer approves the stacked pull requests before protected `main` can merge.
2. The product owner confirms enabling anonymous sign-in in the production Supabase project.
3. Add `SUPABASE_SERVICE_ROLE_KEY` as a GitHub secret for private QA and export workers.
4. Confirm the Hugging Face dataset owner/name, set `HF_DATASET_REPO`, and add `HF_TOKEN`.
5. Publish native-z8 SOC/pH/clay PMTiles and set `VITE_PRIOR_TILES_BASE`; official ISRIC WMS is the
   launch-safe visual fallback.
6. Complete legal review of the ODbL 1.0 / CC BY-SA 4.0 contribution terms.
7. Decide whether to upgrade Supabase before public Phase 1 traffic.

Once those gates are satisfied, merge the stack in order, run the Pages workflow, dispatch the photo
QA workflow, dispatch the nightly export, and complete the stranger-with-a-phone launch test.
