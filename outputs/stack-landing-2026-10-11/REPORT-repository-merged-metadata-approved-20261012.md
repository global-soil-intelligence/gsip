# GSIP repository closeout — 2026-10-12

All 13 reviewed PRs are merged. Final main: `665506fd7a2e4d972bb9fe03c4faf0f174c4675b`. [Final main CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38325785018) completed successfully. Every merge was gated on current-head green validation and secret scans, plus native builds where applicable. DCO was skipped under the existing agent policy; no Justin Signed-off-by was added.

| PR | State | CI before merge | Merge commit |
| --- | --- | --- | --- |
| [#28](https://github.com/global-soil-intelligence/gsip/pull/28) | Merged | Green | `517bc1d13118` |
| [#29](https://github.com/global-soil-intelligence/gsip/pull/29) | Merged | Green | `55d89764375b` |
| [#30](https://github.com/global-soil-intelligence/gsip/pull/30) | Merged | Green | `f84f8464c5de` |
| [#31](https://github.com/global-soil-intelligence/gsip/pull/31) | Merged | Green | `acf10eb41d22` |
| [#32](https://github.com/global-soil-intelligence/gsip/pull/32) | Merged | Green | `7449070d2511` |
| [#33](https://github.com/global-soil-intelligence/gsip/pull/33) | Merged | Green | `02c2ccb91ad8` |
| [#34](https://github.com/global-soil-intelligence/gsip/pull/34) | Merged | Green | `766423725819` |
| [#35](https://github.com/global-soil-intelligence/gsip/pull/35) | Merged | Green | `e72ecd1901c6` |
| [#36](https://github.com/global-soil-intelligence/gsip/pull/36) | Merged | Green | `0bde5e752958` |
| [#37](https://github.com/global-soil-intelligence/gsip/pull/37) | Merged | Green | `7f017dc68c58` |
| [#38](https://github.com/global-soil-intelligence/gsip/pull/38) | Merged | Green | `3cdd8c238399` |
| [#39](https://github.com/global-soil-intelligence/gsip/pull/39) | Merged | Green | `b42cb6796589` |
| [#40](https://github.com/global-soil-intelligence/gsip/pull/40) | Merged | Green | `665506fd7a2e` |

## Changes after review in this turn

- Documented Justin’s narrow owner exception and changed ruleset 19564478 approving-review count from 1 to 0. Exact readback confirmed every other setting unchanged. No approving GitHub reviews or protection bypasses occurred.
- Added job-level opt-in guards for prior enrichment, QA, export and quarantine cleanup on WP-6b; added the contributor-rights guard on WP-6d. Missing opt-in variables hold schedules before secret-bearing steps. Manual runs retain separate approval gates. Tests failed before each relevant change and passed afterward.
- Propagated fixes forward without rewriting or forcing reviewed histories; preserved PR bodies and appended Changes after review. Retargeted successors to main and resolved additive build-order/runbook conflicts while retaining both work packages. The remaining follow-ups were sequenced so combined changes received fresh CI.
- Aligned root coding guidance and v4 build-order copy with the owner exception. Combined local verification: 98 tests passed; affected Ruff and formatting passed. Full final-main CI also passed. No dependency, licence, secret-scan rule, permission or closed-SDK check changes were made.
- Gitleaks 8.21.2 scanned all 99 commits with redaction: zero leaks. The four-line ignore file exactly matches Justin’s approval; no further suppression exists.
- PR #34’s refreshed [app-build run](https://github.com/global-soil-intelligence/gsip/actions/runs/38324411648) passed with both unexpired artifacts: [Android APK](https://github.com/global-soil-intelligence/gsip/actions/runs/38324411648/artifacts/11779992352) and [iOS simulator](https://github.com/global-soil-intelligence/gsip/actions/runs/38324411648/artifacts/11779874381). App-build acceptance is recorded in the preserved PR body. Local Android SDK, Xcode and GDAL checks were not claimed; those results come from CI.

## Metadata mistake — narrow owner exception approved

The 13 GitHub-generated merges used GitHub’s standard titles and lack the required Codex co-author trailer. My authored fix and local forward-merge commits contain it. Correcting those merged commits would rewrite history, which is prohibited. No rewrite was attempted. The concrete audit and narrow exception proposal is `MERGE-METADATA-EXCEPTION-PROPOSAL-20261012.md`; future merge tooling now supplies an explicit Conventional Commit subject and trailer body file. Justin explicitly accepted the narrow exception on 2026-10-12: “Accept this narrow metadata exception (Recommended).” Approval is bound to the exact 13 merge SHAs in `merge-metadata-exception-approved-20261012.json`. History remains unchanged; future merges must supply both required metadata fields. No additional authority is granted.

## Deployment checklist and evidence

Earlier authorised Gate A/B reconciliation, Gate C/D migrations, Gate E function deploys and Gate F repository-variable changes retain their original receipts. This turn performed no production writes, deployments, worker dispatches or Pages approvals.

Fresh read-only production evidence: {"rights_requests_total": 0, "rights_requests_open": 0, "storage_objects": 0, "contributors": 5, "submissions": 25, "photos": 25, "auth_users": 0, "ledger": 28, "capture_open_rows": 0}. Supabase security findings: 0. This refresh covers these counts; full catalog/ACL and Auth-setting baselines must be refreshed before the next production run.

- Database: ledger 28; capture closed; seed counts unchanged.
- Edge Functions: earlier Gate E deployed prior-attach v4 JWT on and gsip-public v1 JWT off; no further deployment in this turn.
- Variables: two new URLs set under Gate F; existing publishable key and old URL retained. Schedule opt-ins and capture-build opt-in absent. No secret values inspected.
- Contributor-rights worker: registered, zero runs; bounded Gate G plan prepared against merged main, not authorised or executed. Secret name previously verified; credential validity remains unverified.
- QA/prior/export workers remain disabled; quarantine cleanup is registered with its opt-in hold and zero runs. No nonterminal worker run exists.
- Tiles: not built/published under this gate. Approved conditional Pages hosting still requires palette-versioned release assets, size limits, SoilGrids-only provenance and actual HTTP 206 range evidence. WMS remains fallback.
- Pages: protected by sole required reviewer jdhart81, administrator bypass false. No deployment approval given.
- Owner launch actions remain pending: make validate required, DNS, counsel/legal URLs, CAPTCHA, paid tier before capture, accounts/signing and capture opening.

## Open work, decisions and assumptions

Four dependency alerts remain open: fsspec/high (fixed 2026.6.0), source-map-js/high (fixed 1.2.2), multidict/moderate (fixed 6.9.1), uuid/moderate (fixed 11.1.1). Recommend a separate tested remediation package before further worker execution. Green CI and zero Supabase findings do not mean these alerts are resolved.

The merged-main one-run worker plan is `GATE-G-merged-main-plan-20261012.md`. It requires a separate explicit go after refreshed evidence and includes the workflow’s generic failure-alert action. No retry, recurring schedule or other worker is included.

Existing owner decisions are retained: capture/signup/anonymous remain closed; Hugging Face organisation/dataset and credentials are Justin’s setup; CAPTCHA and paid services remain deferred; app signing awaits Viridis owner accounts; Android private cloud backup exclusion is implemented, while iOS physical-device proof remains pending; flagged context photos are withheld for private review, with WP-6f implementation and calibration still required before photo publication. Licences remain MIT/ODbL/CC BY-SA.

Assumptions: the empty rights queue remains empty when refreshed; no other writer advances the bound main source before a future dispatch; adding a credential or merging workflows is not production-run authority. Older full production receipts remain historical evidence rather than freshly reverified catalogs.
