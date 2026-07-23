## Work package

- WP: WP-6b, ingest, QA and release integrity (`docs/BUILD_ORDER.md` §4, Phase 1.1)
- Branch: `wp-6b-launch-hardening`
- Stacked on (if any): `docs/spec-v3`

## Summary

Fixes launch blockers 1, 4, 5, 6 and 8 from the 2026-10-10 review.

- **Path binding.** A trigger binds `photos.storage_path` to
  `{auth_uid}/{submission_id}/{shot}/{uuid}.jpg` for every role, and the quarantine upload policy
  requires the same pattern. The QA worker re-derives the path from database facts and
  dead-letters a mismatch before any Storage request.
- **Finalize and settle.**
  - Owners finalize once shots A and B exist.
  - The worker records a verdict per photo.
  - `settle_submission()` decides the status from shots A and B only. An optional shot C can no
    longer fail a submission, and a missing shot B can no longer pass one.
- **Soil-region QA (`deterministic-v2`).**
  - The card is located from its marker homography and masked. Sharpness, exposure and the
    perceptual hash run on the soil alone, with a 20% soil-region check.
  - EXIF orientation and ICC profiles (Display P3) are applied before stripping.
  - Missing GPS accuracy counts as unknown, not perfect.
- **Release integrity.**
  - Export releases only photos that passed QA and sets aside unreadable rows.
  - A Storage outage, or more than 10% of rows set aside, aborts the release rather than publishing
    a hollow one.
  - Any privacy assertion still aborts.
- **k-anonymous publication.**
  - Each row carries the finest cell (resolution 8, then 6, then 4) that aggregates at least 3
    distinct contributors, or it is withheld.
  - `h3_cells` and its refresh function refuse anything below k = 3.
  - The map draws all three resolutions.
- **Capture gate.** `service_state.capture_open`, closed by default, gates every contribution
  insert. The capture app honours `VITE_CAPTURE_LIVE` and pauses sync while the database reports
  capture closed.
- **Quarantine cleanup** runs hourly on its own schedule.
- **Attribution names** reject markup, control and Unicode format characters, e-mail addresses and
  URLs. Capture warns that a typed name is published with the area and date.
- **Workflows** read one `SUPABASE_URL` variable and pin uv and Python.

## Acceptance criteria

- [x] Every criterion in BUILD_ORDER WP-6b has a test:
  - pgTAP `wp6b_integrity` covers path binding, finalize and settle, the capture gate and the
    k = 3 refresh.
  - pytest covers soil-region QA, the path refusal before Storage, the export's k = 3 roll-up and
    abort rules, and the workflow hygiene check.
  - vitest covers the capture app's closed state, finalize after the last photo, the attribution
    warning and multi-resolution cells.
- [x] Tests cover the changed behaviour, including every review finding below.
- [x] Local lint, typecheck, test, build and database tests pass (see Verification evidence).

## Invariant impact

- [x] I2: a submission is final only with shots A and B.
- [x] I7: path binding, no point-level priors or GPS-derived scores in releases, and k = 3 cells.
- [x] I8: soil-region QA, and junk can no longer reach a release.

## Business guardrails

- [x] B1–B8 unaffected. B5 is strengthened: precise locations cannot be inferred from released
      values.

## Agent contribution

- [x] Written by Claude (Claude Opus 5.5), named in `Co-Authored-By` trailers. An independent agent
      review followed. Its findings were fixed in `4b98765` and `1c4aa51`, with the specification
      amended first (`d262275` on `docs/spec-v3`).

Human of record: Justin Hart. **Sign-off pending:** an agent never certifies the DCO.

## Dependencies and deviations

None added. The QA worker uses the OpenCV ArUco detector already in the pipeline's dependencies.

## Verification evidence

Run locally on `1c4aa51`, 2026-10-11:

- `pnpm lint` and `pnpm typecheck` pass.
- vitest: schema 32, site 8, map 5, capture 28.
- ruff, mypy (21 files) and pytest (82) pass.
- pgTAP: prior_attempts 6/6, rls 42/42, wp6b_integrity 51/51.
- `deno check` is not in CI before WP-6c. `prior-attach` on `main` has one type error (TS2345), which WP-6c fixes when it adds the check.
- Playwright runs in CI on this pull request; at the stack's tip it passes 24/24 (desktop and mobile Chrome).

## Independent review and resolutions

The review found two release-privacy leaks and several robustness gaps. All are fixed and tested.

| Area              | Finding                                                                                          | Resolution                                                                                                                            |
| ----------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| Privacy           | Releases carried point-level priors; matched against public rasters, they pinpoint a 250 m pixel | Priors and elevation are forbidden public keys (SPEC I7 amended). The dataset card explains how to sample priors for a published cell |
| Privacy           | The GPS plausibility score encoded the private GPS accuracy                                      | Released as pass or fail only                                                                                                         |
| Privacy           | Export trusted the stored photo path                                                             | Export re-derives each owner path and aborts on a mismatch                                                                            |
| Privacy           | Attribution names allowed bidirectional and zero-width characters                                | Rejected in the database and the app                                                                                                  |
| Release integrity | A Storage outage could publish an empty release, wiping the dataset and the map                  | 5xx, 429 and timeouts abort. Over 3 rows or 10% set aside aborts. Missing objects are set aside and named in a private report         |
| Release integrity | Rows did not require passing shots A and B; pre-v3 statuses were not re-derived                  | Rows require passing A and B. Statuses are repaired by a tested function, and settlement waits for the H3 cells                       |
| Workers           | The QA worker could crash on spent jobs, and one failed settlement stopped the sweep             | A terminal verdict is recorded and settled first; spent jobs are dead-lettered; the sweep continues                                   |
| Workers           | Applying EXIF orientation re-serialized EXIF, so mistyped tags dead-lettered valid photos        | Orientation is applied without re-serializing EXIF                                                                                    |
| App               | The gate was read once; the grant recorded the photo time; the copy promised a resolution-8 cell | The gate is re-read before every sync; the grant records the acceptance time; the copy is corrected                                   |
| App (`1c4aa51`)   | An `online` event during the first drain was coalesced away, so a reopened gate waited 30 s      | One drain at a time, with exactly one follow-up for triggers that arrive mid-drain. The new test fails without the fix                |

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_017nrzCzGuaW3XpYuuvMm7U1
