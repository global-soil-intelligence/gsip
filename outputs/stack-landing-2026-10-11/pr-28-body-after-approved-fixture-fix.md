## Work package

- WP: Specification v3.0. It governs WP-6b to WP-APP-1, so it merges first.
- Branch: `docs/spec-v3`
- Stacked on (if any): none. Base `main` at `7a2c082`.

## Summary

Adopts GSIP SPEC v3.0 and BUILD_ORDER v3.0 for a community of people and AI agents. It lands
before any implementation, as GOVERNANCE requires for architecture changes.

- **New invariants I9–I15:** human of record, provenance rises only with evidence, synthetic never
  passes as field data, agents see no more than the public, labels are claims, bounded throughput,
  and held-out truth stays held out.
- **Amended invariants:**
  - I2: finalize requires shots A and B.
  - I3: "no prior" is a terminal state.
  - I6: withdrawal and deletion.
  - I7: k = 3 distinct contributors per published cell at H3 resolution 8, 6 or 4; external
    processors see resolution-9 cell centres only.
  - I8: soil-region QA with the card masked.
- **Phone app:** the Capacitor app moves from Phase 4 to Phase 1.5 as the main contribution funnel.
- **Agents:** a new section stages agent roles and interfaces.
- **BUILD_ORDER v3.0:**
  - Phase 1.1 launch hardening (WP-6b to WP-6e) and Phase 1.5 (WP-SITE-1D, WP-AGENT-1, WP-APP-1),
    with testable acceptance criteria.
  - Stacked pull requests and the human-of-record DCO rule.
  - Guardrails 9 (I12) and 10 (B1–B8).
- **GOVERNANCE.md:** the steward model, business guardrails B1–B8 with their checks, a 10%
  commons share, and conflict rules.
- **Other documents:**
  - TRADEMARKS.md is added; CONTRIBUTING already cited it.
  - SECURITY.md is rewritten around GSIP's privacy promise.
  - The v2.2 documents are archived.

Five later commits amend the specification with what each work package's independent review found,
before the fix was built. One more is tooling:

| Commit    | Change                                                                                                                      | Source of the change |
| --------- | --------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| `d262275` | No point-level priors or GPS-derived scores in releases; an outage aborts the export instead of publishing a hollow release | WP-6b review         |
| `d169716` | Claim a prior job and pay for its upstream calls in one transaction; palette-versioned tiles                                | WP-6c review         |
| `5fe230e` | Agent scratch worktrees are ignored by git, lint and formatting                                                             | Tooling              |
| `fe5111c` | Withdrawal takes effect at once; the attribution name is the only grant change, on account deletion                         | WP-6d build          |
| `a35ec24` | Nothing a rights request covers can come back, from any device or export                                                    | WP-6d review         |
| `e258b41` | Tiers derived from stored evidence and anchored to the terms acceptance; safe terms reconfirmation; migration test          | WP-6e review         |

## Acceptance criteria

- [x] Each implementing PR in this stack cites the sections it satisfies.
- [x] Documentation and ignore rules only. `pnpm lint` (eslint, language guard, prettier) passes.
- [x] No code behaviour changes, so no new tests.

## Invariant impact

Defines I9–I15 and amends I2, I3, I6, I7 and I8 (see Summary). This PR changes no code.

## Business guardrails

- [x] Adds B1–B8 to `GOVERNANCE.md`.
- **Product-owner decisions:**
  - Confirm the 10% commons share.
  - Confirm the 14-day minimum open period for governance changes.

## Agent contribution

- [x] Written by Claude (Claude Opus 5.5), named in each commit's `Co-Authored-By` trailer. Each
      amendment followed an independent agent review of the matching work package.

Human of record: Justin Hart. **Sign-off pending:** an agent never certifies the DCO. Adopt with
`git rebase --signoff` before merging.

## Dependencies and deviations

None.

## Verification evidence

Run locally on `e258b41`, 2026-10-11:

- `pnpm lint` (eslint, language guard, prettier) and `pnpm typecheck` pass.
- vitest: schema 11, site 8, map 3, capture 13 (`main`'s suites, unchanged).
- ruff, mypy (18 files) and pytest (29) pass.
- pgTAP: prior_attempts 6/6, rls 42/42.
- `deno check` is not in CI before WP-6c. `prior-attach` on `main` has one type error (TS2345), which WP-6c fixes when it adds the check.

Merge order: this PR, then WP-6b, WP-6c, WP-6d, WP-6e, WP-AGENT-1 and WP-APP-1. Retarget each to
`main` as its predecessor merges.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_017nrzCzGuaW3XpYuuvMm7U1


## Changes after review

- `afadda988cb8619d4f3a98515629909ca761763f` adds exactly the three historical synthetic-fixture fingerprints approved by Justin on 2026-10-11. CI scans every branch, so every branch needs the same file; this common exception starts on `docs/spec-v3` and is merged forward through the stack.
- No changes to `.gitleaks.toml`, detection rules, redaction, the full-history scan or its workflow. No further suppression is authorized.
- Verification: Gitleaks 8.21.2 over every local and remote ref reported three findings without the file and zero with the approved four lines. Final stack CI results will be recorded after propagation and fixture cleanup.
- Assumptions: these exact historical values are synthetic mocked test fixtures; the exception applies only to the approved immutable commit/file/rule/line fingerprints. No production deployment, capture opening or merge is authorized by this exception. No dependency added.


### Completed stack verification

- The exception was propagated through all seven branches; fixture cleanup `5e50028` was committed on WP-AGENT-1 and merged into WP-APP-1.
- Gitleaks 8.21.2 with the unchanged CI command and an explicit `--log-opts=--all` run each reported: **69 commits scanned, no leaks found, exit code 0**. Exactly the approved three fingerprints were present. Current-head GitHub checks are pending.


### Current-head CI completed

At `afadda9`, [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38189449874/job/114618845556) and [Gitleaks](https://github.com/global-soil-intelligence/gsip/actions/runs/38189449872/job/114618845718) completed successfully. DCO was intentionally skipped for this same-repository PR; no agent supplied a human sign-off. This completed result supersedes the pending-CI notes above.
