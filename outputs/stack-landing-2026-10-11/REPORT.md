# GSIP reviewed stack — landing status

Observed: 2026-10-11T20:15:54.528403-04:00. **Phase 1 blocked on the pending synthetic-fixture secret-scan decision.**

The original bundle checksum, prerequisite and all seven complete heads were verified before import. A clean full clone preserved the existing workspace. All seven PRs are open in the requested order. No force push, history rewrite, merge, approval or production mutation occurred.

| PR | Work package | Current head | validate | Secret scan |
| --- | --- | --- | --- | --- |
| [#28](https://github.com/global-soil-intelligence/gsip/pull/28) | `docs/spec-v3` | `e258b41` | SUCCESS | FAILURE: same three synthetic fixture matches |
| [#29](https://github.com/global-soil-intelligence/gsip/pull/29) | `wp-6b-launch-hardening` | `1c4aa51` | SUCCESS | FAILURE: same three synthetic fixture matches |
| [#30](https://github.com/global-soil-intelligence/gsip/pull/30) | `wp-6c-priors-and-tiles` | `f3ffa4f` | SUCCESS | FAILURE: same three synthetic fixture matches |
| [#31](https://github.com/global-soil-intelligence/gsip/pull/31) | `wp-6d-contributor-rights` | `18c4aba` | SUCCESS | FAILURE: same three synthetic fixture matches |
| [#32](https://github.com/global-soil-intelligence/gsip/pull/32) | `wp-6e-provenance` | `af336ae` | SUCCESS | FAILURE: same three synthetic fixture matches |
| [#33](https://github.com/global-soil-intelligence/gsip/pull/33) | `wp-agent-1-read-api` | `f20d793` | SUCCESS | FAILURE: same three synthetic fixture matches |
| [#34](https://github.com/global-soil-intelligence/gsip/pull/34) | `wp-app-1-phone-app` | `94e19ff` | SUCCESS | FAILURE: same three synthetic fixture matches |

DCO was skipped as designed for same-repository PRs. No DCO sign-off was fabricated. Superseded dependency PRs #20–#22 were already closed; #24 is merged.

## Changes after review

- PR #34: commit `94e19ff7fa06a8b284165d57e612c1bda86ce4c8` renames the unchanged UI component `MySoil.tsx` to `MySoilPanel.tsx` and updates two imports. On macOS, the original import selected `mySoil.ts` and failed with a missing export.
- A new cross-platform source-module guard fails on the original case-insensitive module collision and passes after the rename. My Soil UI tests, permissions, RLS-bound reads and privacy behavior remain intact. No dependency was added.
- PR #34’s original prose was retained; the Changes after review section was appended, and the app-build acceptance box was ticked with evidence. No other reviewed branch was changed.

## App artifacts

[Successful repaired App build](https://github.com/global-soil-intelligence/gsip/actions/runs/38186898193) at `94e19ff` produced both artifacts; Android dependency and built APK/iOS permission checks passed unchanged.

| Artifact | ID | Bytes |
| --- | --- | --- |
| `gsip-capture-android-debug` | 11720401121 | 7,144,177 |
| `gsip-capture-ios-simulator` | 11720022132 | 3,323,666 |

GitHub archive digests and expiry are in `status.json`; they are not independently calculated APK or app-binary hashes.

## Verification evidence

- All seven initial validate jobs completed successfully. [Current PR #34 validation](https://github.com/global-soil-intelligence/gsip/actions/runs/38186898183) also passed after the fix: 302 Vitest, 224 pytest (one new regression test), 262 pgTAP assertions, and 12 desktop-Chrome browser tests. `first-ci-results.json` records the original and current head’s exact step outcomes and package/test totals.
- CI at the original tip: 302 Vitest, 223 pytest, 262 pgTAP assertions, and 12 desktop-Chrome browser tests. The supplied 24-browser-test baseline was not reproduced by this CI project invocation. Migration-test step succeeded; its numeric total was not established from the captured logs.
- Local after the fix: frozen dependency installs, lint, typecheck, 302 Vitest tests, builds, map/site budgets, macOS build:app, ruff and strict mypy passed. Pytest: 220 passed, 4 GDAL-dependent tests skipped.
- Local browser verification could not launch 11 browser tests because the pinned Chromium headless executable is missing; the API-only llms.txt test passed. The prescribed checked-in harness builds a local mock capture-live site; no test artifact was uploaded or deployed. The final local Pages artifact was rebuilt explicitly with `VITE_CAPTURE_LIVE=false`.

## Remaining CI blocker and concrete proposal

The unchanged gitleaks8.21.2 full-history scan identifies three synthetic credentials in mocked agent-API tests. All three belong to WP-AGENT-1. Checkout fetches all branch histories, so earlier stack PRs also see them. A forward fixture edit cannot remove historical findings, and reviewed history cannot be rewritten.

The proposed `gitleaksignore.proposed` contains only three exact commit/file/rule/line fingerprints. No path, regex, rule-wide, commit-wide or future-match exclusion is proposed. It has not been applied to any reviewed branch.

A local proof using exactly gitleaks8.21.2 found zero remaining history matches with the proposal, then correctly failed on the same fixture/file in a newly created temporary commit. `secret-fixture-proposal-evidence.json` records counts only. Because this is an exception to the no-weaken-check rule, Justin’s approval was requested before changing scan policy. Applying the common policy at the stack base and merging forward also awaits that decision.

## Deployment checklist

| Step | State | Evidence or next requirement |
| --- | --- | --- |
| Governing v3 documents | DONE | Read from verified bundle; original v2.2 main document was not substituted. |
| Production selection | DONE; execution gated | Justin selected toxldjgwkxtneoqsazym, gsip, us-east-1. Live metadata says INACTIVE. Justin alone restores it when authorized. |
| Pre-migration inventory | BLOCKED | Exact table counts only, applied migration history and existing-row state await restored target. Nine successor migrations exist vs main; their production pending status is unverified. |
| Migration | BLOCKED | Complete Phase1; run migration test against selected reviewed/merged head; post exact project and commands; wait for go. Never production db reset. |
| Security/capture/auth readbacks | BLOCKED | No advisor, service_state or auth-setting readback; zero findings/closed state not asserted as live facts. No settings changed. |
| Edge Functions/smoke | BLOCKED | No deployment. Later prior-attach JWT on; gsip-public JWT off; protocol200, r9 rejection400, four MCP tools. Separate go required. |
| Variables/secrets | BLOCKED | Repository has only legacy VITE_SUPABASE_URL and publishable-key variable; repository/Pages secret-name lists empty. No changes. Owner supplies service-role key through secret store. |
| Rights worker / QA | BLOCKED | No dispatch. Existing QA/prior/export workflows remain disabled. |
| HF export | JUSTIN ACTION | Owner creates organization/dataset, sets HF_TOKEN/HF_DATASET_REPO. Approved primary global-soil-intelligence/gsip; fallback viridis-research/gsip. No export until ready. |
| Tiles | PREPARED POLICY; NOT BUILT | Same-origin Pages approved conditionally: palette-versioned release assets, no git tiles, <=700MB target, site below1GB, 206 Range, SoilGrids-only values, privacy-host docs PR. WMS until all pass. |
| Pages | NOT DEPLOYED | Closed local build succeeded; production go, public configuration and production readbacks pending. |
| Required validate / DNS / counsel / CAPTCHA / paid tier / capture opening | JUSTIN ACTION | Existing main rules do not require validate. CAPTCHA and paid tier deferred; capture and anonymous sign-in remain disabled by owner instruction. |

**Merge-time caveat:** Pages automatically deploys on a push to main. The github-pages environment has a branch policy but no required-reviewer gate. This must be reconciled with Justin’s per-deployment go rule before merging; no gate or workflow settings were changed.

## Follow-ups and decisions

Phase3 implementation has not started because Phase1 is not complete. The owner’s policy decisions are preserved in `owner-decisions.json`: private cloud backups excluded (platform reliability/device verification required), open-source server screening of every photo with individual human-review withholding and no blur, spec approval before screening implementation, CI versions/reproducible builds later, signing/accounts deferred, licences unchanged and no new paid/closed services. These choices do not grant deployment authority.

The sole new decision currently requested is the exact three-fingerprint scanner exception. Production restoration/go, Hub creation/secrets, counsel, required CI check, DNS, launch CAPTCHA/tier and store credentials remain owner actions. No previous decision is being asked again.

## Assumptions

- Original reviewed commits remain immutable and are the authoritative bundle contents.
- Synthetic test-credential fingerprint exception requires separate owner approval.
- The prescribed browser test command uses a local mocked capture-live build; no such build was uploaded or deployed and final local Pages build is capture closed.
- Local GDAL/Chromium gaps are environment limitations; CI results are separately attributed.
- Production metadata readback does not prove capture/auth settings, table counts or security-advisor state.

Sanitized receipt: `status.json`. Initial CI receipt: `first-ci-results.json`. Hashes: `SHA256SUMS`.
