## Work package

- WP: WP-6c, priors and tiles (`docs/BUILD_ORDER.md` §4, Phase 1.1)
- Branch: `wp-6c-priors-and-tiles`
- Stacked on (if any): `wp-6b-launch-hardening`

## Summary

Fixes launch blockers 2 and 3 from the 2026-10-10 review (SPEC v3.0 I3, I7, I14).

**Priors**

- A null SoilGrids answer, which it gives for built-up land, means "no prior". The parser keeps
  whatever it can, and an empty answer completes the job, recorded in `prior_jobs.empty_sources`.
  Before, it dead-lettered after 32 attempts.
- External services see only the resolution-9 cell centre, never the precise point. Static lookups
  (SoilGrids, SSURGO, elevation) are cached per cell for 365 days in a server-only table.
- Precipitation covers the 72 hours before capture, not before the request: the forecast API within
  90 days, the archive API before that.
- **Fair use with database token buckets** (SoilGrids 5 a minute, SSURGO 30, Open-Meteo 60).
  - `begin_prior_attempt()` claims a job and pays for its upstream calls in one transaction. A
    deferred or unclaimable request spends nothing and consumes no attempt.
  - Contributors can start only their own unstarted job; only the service drain retries.
  - Stale claims are requeued, or dead-lettered once their attempts are spent.
- Orchestration lives in `packages/schema/src/priorJob.ts` with unit tests. The Edge Function is a
  thin adapter, now type-checked by `deno check` in CI.

**Tiles**

- A versioned palette in `packages/schema/src/palettes/` colours the tiles through
  `gdaldem color-relief` (RGBA, transparent nodata) and draws the map legends, so the two can no
  longer disagree. The WMS fallback shows ISRIC's own legend graphic.
- Tile archives are stamped with the palette version and published under it. The Pages deploy
  fails unless every archive matches the palette its legends are drawn from.
- A golden-tile test runs through real GDAL, including values above 255 and nodata. CI installs
  `gdal-bin` and requires it.

## Acceptance criteria

- [x] Every criterion in BUILD_ORDER WP-6c has a test:
  - vitest: the null and mixed SoilGrids parsing, cell-centre lookups, precipitation windows, cache
    hits, deferred requests and empty answers.
  - pgTAP `prior_attempts`: atomic claim and spend, the SoilGrids bucket, the claim rules, and the
    stale requeue.
  - pytest: drain waiting and its budget, palette conversion, the golden tile and archive stamps.
  - vitest: legends drawn from the palette, and the deploy gate.
- [x] Tests cover the changed behaviour, including every review finding below.
- [x] Local lint, typecheck, test, build and database tests pass (see Verification evidence).

## Invariant impact

- [x] I3: no prior is a terminal state.
- [x] I7: external processors see the resolution-9 cell centre only.
- [x] I14: upstream fair use is enforced in the database and cannot be drained by contributors.

## Business guardrails

- [x] B1–B8 unaffected. B1 benefits: priors come from free public services within their fair-use
      limits.

## Agent contribution

- [x] Written by Claude (Claude Opus 5.5), named in `Co-Authored-By` trailers. An independent agent
      review followed. Its findings were fixed in `f3ffa4f`, after the specification was amended
      first (`d169716` on `docs/spec-v3`).

Human of record: Justin Hart. **Sign-off pending:** an agent never certifies the DCO.

## Dependencies and deviations

- `h3-js` 4.5.0 (Apache-2.0) is added to `packages/schema`; the capture app and the map already
  use the same version.
- CI installs `gdal-bin` (MIT/X style licence) from Ubuntu for the tile tests.

## Verification evidence

Run locally on `f3ffa4f`, 2026-10-11:

- `pnpm lint` and `pnpm typecheck` pass.
- vitest: schema 58, site 8, map 15, capture 28.
- ruff, mypy (22 files) and pytest (111, with GDAL required) pass.
- pgTAP: prior_attempts 30/30, rls 42/42, wp6b_integrity 51/51.
- `deno check` passes on both Edge Functions.
- Playwright runs in CI on this pull request; at the stack's tip it passes 24/24 (desktop and mobile Chrome).

## Independent review and resolutions

The review found that `prior-attach` took upstream tokens before claiming a job and never returned
them. Any contributor could therefore starve every bucket with requests that could never run (I14).

| Area       | Finding                                                                                         | Resolution                                                                                                                                                                            |
| ---------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I14        | Tokens were spent before the claim, so unclaimable requests drained the buckets                 | `begin_prior_attempt()` claims and spends in one transaction, returning claimed, deferred (with a wait) or not claimable; only a claimed attempt spends tokens                        |
| I14        | SoilGrids could bank a burst                                                                    | One token, refilled five times a minute, so calls are at least 12 s apart. Buckets are locked before the clock is read, and every upstream call is made once                          |
| Auth       | `verify_jwt` and service mode were loose                                                        | `verify_jwt` is pinned on. Service mode needs the exact service-role key, and contributors read the submission through RLS                                                            |
| Liveness   | Jobs that can never succeed stayed pending; stale claims with no attempts left were stuck       | `fail_prior_job()` ends them, and stale claims become dead letters                                                                                                                    |
| Drain      | No `Retry-After` handling, and failed jobs blocked the head of the queue                        | The drain honours `Retry-After` within a 240 s budget and rotates failed, unclaimed jobs to the back without touching processing claims                                               |
| Robustness | A failed cache write failed a good answer; empty or definitive 4xx answers retried              | Cache writes are best-effort; empty Soil Data Access answers and definitive 4xx rejections complete as no data; capture times outside every weather service are no data, with no call |
| Precision  | The precipitation window boundary was off by an hour, and the forecast cut-over was mismeasured | The window counts the hour labelled at capture time; the cut-over is measured from the window start                                                                                   |
| Tiles      | Archives were not tied to a palette version                                                     | Archives are stamped and written under the palette version; the map requests that version, and the deploy gate checks it                                                              |

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_017nrzCzGuaW3XpYuuvMm7U1


## Changes after review

- Justin approved exactly three historical synthetic-fixture fingerprints as a documented exception on 2026-10-11. CI scans every branch, so every branch needs the same file. The four-line `.gitleaksignore` starts in commit `afadda9` on `docs/spec-v3` and is merged forward unchanged.
- `.gitleaks.toml`, all detection rules, redaction, full-history scanning and the secret-scan workflow remain unchanged. No further suppression is authorized. No dependency added.
- This PR only receives the common exception through a forward merge; its reviewed implementation is unchanged. Gitleaks 8.21.2 over the complete stack reported **69 commits scanned, no leaks found, exit code 0**. Current-head GitHub checks are pending.
- Assumptions: the ignored historical matches are audited synthetic WP-AGENT-1 fixtures; no new-match exclusion is introduced. Capture stays closed; no production action or merge was performed.


### Current-head CI completed

At `a66c4f2`, [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38189451564/job/114618850617) and [Gitleaks](https://github.com/global-soil-intelligence/gsip/actions/runs/38189451583/job/114618850557) completed successfully. DCO was intentionally skipped for this same-repository PR; no agent supplied a human sign-off. This completed result supersedes the pending-CI notes above.
