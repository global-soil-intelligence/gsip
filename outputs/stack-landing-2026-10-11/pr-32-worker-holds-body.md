## Work package

- WP: WP-6e, provenance foundation (`docs/BUILD_ORDER.md` §4, Phase 1.1)
- Branch: `wp-6e-provenance`
- Stacked on (if any): `wp-6d-contributor-rights`

## Summary

Lands SPEC I9–I11 and the I15 holdout flag while production holds little or no real data, so no
backfill of real rows is needed later.

- **I9 actors.**
  - Every contributor has exactly one human actor.
  - Agents, devices and labs need an active human operator, and an agent cannot operate another.
  - Revocation is final and reaches everything the operator runs.
  - Clients read only their own actor and write none.
- **I9 terms.** Grants cite a published, unretired `terms_versions` row, accepted within the last
  30 days and not in the future. The server records `received_at`. A device holds an observation
  whose acceptance has expired, once the server has shown it was not withdrawn, and asks its
  person to accept the current terms again.
- **I10 provenance.**
  - `provenance_tier` is derived by the database from private, allowlisted, coordinate-free capture
    evidence that QA extracts before stripping. A direct write cannot set a tier.
  - A photo reaches tier 1 when its absolute EXIF time agrees with the claimed capture time, the
    photo was taken within the hour before its person accepted the terms, and any EXIF position is
    within 250 m.
  - A submission's tier is the lower of shots A and B.
  - Client claims (`ingest_path`, `capture_method`, `location_source`, `client_version`) are
    recorded but never read when tiering. Tiers 2 and 3 stay reserved.
- **I11.** Synthetic rows are exactly tier -1 and can never become field data again.
- **I15.** `gold_labels.holdout` is invisible to clients. Export drops holdout labels and aborts if
  one remains.
- **Export** requires tier ≥ 0 and publishes `provenance_tier`, `location_source` and
  `capture_method`. The dataset card explains every tier.

## Acceptance criteria

- [x] Every criterion in BUILD_ORDER WP-6e has a test:
  - pgTAP `wp6e_provenance` (57): actors, client privileges, evidence-derived tiers, synthetic
    rows, terms windows, and `WD001` ahead of the window check.
  - `scripts/db-migration-test.sh` (13): migration onto pre-WP-6e rows, the backfill, and account
    deletion on them. CI runs it.
  - pytest: allowlisted, coordinate-free evidence; hostile metadata; claims not read; export tier
    and holdout aborts; the dataset card.
  - vitest: claims sent, and expired acceptances held only after the server has not refused them.
- [x] Tests cover the changed behaviour, including every review finding below.
- [x] Local lint, typecheck, test, build and database tests pass (see Verification evidence).

## Invariant impact

- [x] I9, I10 and I11: implemented as above.
- [x] I15: holdout flag, with export filtering and assertions.

## Business guardrails

- [x] B4: money never touches scientific judgment. Tiers depend only on evidence, never on who
      pays or what a client claims.

## Agent contribution

- [x] Written by Claude (Claude Opus 5.5), named in `Co-Authored-By` trailers. An independent agent
      review followed, with probes, a two-session race script and a 200,000-case EXIF fuzz. Its
      findings were fixed in `af336ae`, after the specification was amended first (`e258b41` on
      `docs/spec-v3`).

Human of record: Justin Hart. **Sign-off pending:** an agent never certifies the DCO.

## Dependencies and deviations

None.

## Verification evidence

Run locally on `af336ae`, 2026-10-11:

- `pnpm lint` and `pnpm typecheck` pass.
- vitest: schema 58, site 8, map 15, capture 96.
- ruff, mypy (31 files) and pytest (200) pass.
- pgTAP: prior_attempts 30/30, rls 42/42, wp6b_integrity 51/51, wp6d_rights 70/70, wp6e_provenance 57/57.
- Migration test on pre-WP-6e data (`scripts/db-migration-test.sh`): 13/13.
- `deno check` passes.
- Playwright runs in CI on this pull request; at the stack's tip it passes 24/24 (desktop and mobile Chrome).

## Independent review and resolutions

The reviewer found client-facing privileges and RLS solid: no client path writes any provenance
field or reads the holdout flag. The findings concerned the migration on existing data, how much
tier 1 actually corroborates, and reconfirmation after a withdrawal.

| ID    | Severity | Finding                                                                                                                            | Resolution                                                                                                                                                     |
| ----- | -------- | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1    | Major    | A `NOT VALID` check on `received_at` also applied to WP-6d's redaction update, blocking account deletion for every pre-WP-6e grant | `received_at` is set by a BEFORE INSERT trigger, with a pgTAP case for redaction                                                                               |
| F2    | Major    | Tier 1 compared EXIF time with a capture time taken from the same file, so a year-old gallery photo was "corroborated"             | Tier 1 is anchored to the terms acceptance: the photo was taken within the hour before its person accepted. The dataset card says so                           |
| F3    | Major    | The 30-day hold was decided locally, so a withdrawn acceptance could be re-accepted on a second device                             | The original acceptance always goes first. `WD001` (raised before the window check, pinned by pgTAP) drops the record; only `42501` is held for reconfirmation |
| F4–F5 | Minor    | The backfill left deleted accounts' actors active and published arbitrary legacy terms strings as citable                          | Contributors without a sign-in get revoked actors; legacy-only versions are retired with a neutral publication time                                            |
| F6    | Minor    | An overflowing GPS date escaped evidence derivation and failed the photo's QA                                                      | Derivation is total; the hostile-metadata test covers it                                                                                                       |
| F7–F8 | Minor    | A concurrent peer's commit could leave a stale tier; direct server writes could set tiers                                          | Tiers are derived under the submission's row lock with a fresh snapshot; direct writes are ignored; evidence changes refresh the submission                    |
| F9    | Minor    | The holdout assertion could not fire once the flag had been stripped                                                               | Export asks only for non-holdout labels and aborts on any label that is held out or unflagged                                                                  |
| F10   | Minor    | No test ran the migration on existing rows                                                                                         | `scripts/db-migration-test.sh`, run in CI                                                                                                                      |
| N1–N5 | Nit      | Untyped evidence values; actor and terms deletion; revoked operators; doc wording; no `client_version`                             | Typed whole-number evidence; deletion revoked; active operators required; final revocation; docs fixed; a `client_version` claim                               |

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_017nrzCzGuaW3XpYuuvMm7U1


## Changes after review

- Justin approved exactly three historical synthetic-fixture fingerprints as a documented exception on 2026-10-11. CI scans every branch, so every branch needs the same file. The four-line `.gitleaksignore` starts in commit `afadda9` on `docs/spec-v3` and is merged forward unchanged.
- `.gitleaks.toml`, all detection rules, redaction, full-history scanning and the secret-scan workflow remain unchanged. No further suppression is authorized. No dependency added.
- This PR only receives the common exception through a forward merge; its reviewed implementation is unchanged. Gitleaks 8.21.2 over the complete stack reported **69 commits scanned, no leaks found, exit code 0**. Current-head GitHub checks are pending.
- Assumptions: the ignored historical matches are audited synthetic WP-AGENT-1 fixtures; no new-match exclusion is introduced. Capture stays closed; no production action or merge was performed.


### Current-head CI completed

At `4f76145`, [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38189449798/job/114618844971) and [Gitleaks](https://github.com/global-soil-intelligence/gsip/actions/runs/38189449759/job/114618844724) completed successfully. DCO was intentionally skipped for this same-repository PR; no agent supplied a human sign-off. This completed result supersedes the pending-CI notes above.


### Security-boundary correction and exact-head CI (2026-10-12)

Current head: `5bea5b75d82a31dc8bd9bc485cfd133acdbd4940`. Existing description and earlier verification records are preserved above.

Inherited change: merge-forward carries #28’s spec-first boundary clarification and #29/#31’s additive guarded-helper/invoker and restrictive-policy fixes. The owning fixes remain on WP-6b/WP-6d; this branch does not duplicate or rewrite their SQL.

The hosted Gate C zero-findings check stopped on seven findings across the service-only rights tables and client-executable public definer functions. The correction preserves authorization rather than suppressing any advisor rule. All 26 executed migration blobs remain unchanged. No new client schema, table or column grant is added; narrow EXECUTE grants on new private helpers match the existing public callers. Public signatures and caller ACLs, owner checks, withdrawal refusal and capture-closed behavior remain intact.

Local source proof preserved the existing WP-6b 99 assertions and WP-6d 209 assertions; the new owning suites passed 16 and 21 assertions respectively, with 13 new assertions failing before the changes. The candidate complete pgTAP suite passed 299 assertions, migration testing passed 13/13, and isolated synthetic PostgREST dispatch/reload/privilege tests passed 33/33. These are local proofs; hosted advisor remediation remains unexecuted.

Exact-head CI, verified 2026-10-12 14:56:50 UTC: [validate — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265398543/job/114866169089), [gitleaks — SUCCESS](https://github.com/global-soil-intelligence/gsip/actions/runs/38265398594/job/114866168559). All 13 updated PR heads are green for their required checks. DCO is SKIPPED; an agent has not certified Justin’s DCO.

Assumptions: the reviewed migration owner and exposed-schema settings remain unchanged and there is no overlapping production writer; production execution must refresh these checks. Private is absent from the observed Data API exposed-schema list, but schema placement alone is not authorization. Local tests use synthetic data and do not establish the hosted advisor’s final state. Capture, sign-up and anonymous sign-in stay closed; no production mutation, deployment, new dependency, service or licence change is included in this update.


### Changes after review — owner merge exception and worker holds (2026-10-12)

Justin explicitly authorised removing the extra approving-review requirement for this owner-operated repository. Independent review, green CI, resolved conversations and protection against force pushes remain required. Agents do not submit approving reviews or certify the DCO.
Scheduled production workers now require their own explicit repository-variable opt-in; absent variables hold jobs before any secret-bearing step. Manual dispatch still requires a separate production gate. Contributor-rights schedules receive the same hold from WP-6d onward. This prevents merging workflows or adding a credential from starting unapproved production work. Regression tests failed before the relevant change and passed after it.

Assumptions: schedule opt-in variables remain unset; this merge authority does not authorise deployments, worker dispatches or capture opening. No dependencies or secret-scan exceptions were added.
