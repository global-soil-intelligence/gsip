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


## Changes after review

- Justin approved exactly three historical synthetic-fixture fingerprints as a documented exception on 2026-10-11. CI scans every branch, so every branch needs the same file. The four-line `.gitleaksignore` starts in commit `afadda9` on `docs/spec-v3` and is merged forward unchanged.
- `.gitleaks.toml`, all detection rules, redaction, full-history scanning and the secret-scan workflow remain unchanged. No further suppression is authorized. No dependency added.
- This PR only receives the common exception through a forward merge; its reviewed implementation is unchanged. Gitleaks 8.21.2 over the complete stack reported **69 commits scanned, no leaks found, exit code 0**. Current-head GitHub checks are pending.
- Assumptions: the ignored historical matches are audited synthetic WP-AGENT-1 fixtures; no new-match exclusion is introduced. Capture stays closed; no production action or merge was performed.


### Current-head CI completed

At `273e768`, [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38189450978/job/114618848447) and [Gitleaks](https://github.com/global-soil-intelligence/gsip/actions/runs/38189450968/job/114618848472) completed successfully. DCO was intentionally skipped for this same-repository PR; no agent supplied a human sign-off. This completed result supersedes the pending-CI notes above.


### Security-boundary correction and exact-head CI (2026-10-12)

Current head: `6b0bd81508f6f475f4a0d87cb3e4df394e0761c8`. Existing description and earlier verification records are preserved above.

Owning change: [6b0bd81](https://github.com/global-soil-intelligence/gsip/commit/6b0bd81508f6f475f4a0d87cb3e4df394e0761c8) adds `20261012141828_wp6b_invoker_boundary.sql` and its regression suite. Capture reads only its already-granted capture-state column as invoker. Finalization retains its unchanged guarded body in private, with a definition-time bound public invoker adapter and authenticated-only dispatch. The 16 new assertions passed after the fix (five failed before); all 99 existing branch assertions passed before and after. The spec-first clarification is inherited from #28.

The hosted Gate C zero-findings check stopped on seven findings across the service-only rights tables and client-executable public definer functions. The correction preserves authorization rather than suppressing any advisor rule. All 26 executed migration blobs remain unchanged. No new client schema, table or column grant is added; narrow EXECUTE grants on new private helpers match the existing public callers. Public signatures and caller ACLs, owner checks, withdrawal refusal and capture-closed behavior remain intact.

Exact-head CI, verified 2026-10-12 14:56:50 UTC: [validate — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265398509/job/114866169296), [gitleaks — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265398957/job/114866171091). All 13 updated PR heads are green for their required checks. DCO is SKIPPED; an agent has not certified Justin’s DCO.

Assumptions: the reviewed migration owner and exposed-schema settings remain unchanged and there is no overlapping production writer; production execution must refresh these checks. Private is absent from the observed Data API exposed-schema list, but schema placement alone is not authorization. Local tests use synthetic data and do not establish the hosted advisor’s final state. Capture, sign-up and anonymous sign-in stay closed; no production mutation, deployment, new dependency, service or licence change is included in this update.


### Changes after review — owner merge exception and worker holds (2026-10-12)

Justin explicitly authorised removing the extra approving-review requirement for this owner-operated repository. Independent review, green CI, resolved conversations and protection against force pushes remain required. Agents do not submit approving reviews or certify the DCO.
Scheduled production workers now require their own explicit repository-variable opt-in; absent variables hold jobs before any secret-bearing step. Manual dispatch still requires a separate production gate. Contributor-rights schedules receive the same hold from WP-6d onward. This prevents merging workflows or adding a credential from starting unapproved production work. Regression tests failed before the relevant change and passed after it.

Assumptions: schedule opt-in variables remain unset; this merge authority does not authorise deployments, worker dispatches or capture opening. No dependencies or secret-scan exceptions were added.
