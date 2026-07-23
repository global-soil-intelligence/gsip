## Problem and behavior

The approved map bundle computed a MapLibre worker URL that was not emitted by Vite. The URL returned 404 HTML while the map shell could still appear. WP-SITE-1G explicitly bundles the pinned worker and its shared imports, configures its URL before map construction, and ships complete upstream dependency notices. It implements the existing SPEC section 8 architecture.

Fixes #76.

## Invariants and acceptance

- [x] Preserve I1/I3/I5/I7/I11/I12 and B1/B5/B8: existing open software, prior semantics, language, private-data boundaries and public-only access are unchanged. Other invariants/guardrails are unaffected.
- [x] Real worker regression fails on the old artifact with HTTP 404, then passes at both `/map/` and `/gsip/map/`: JavaScript HTTP 200, exact processed synthetic public-cell tags and aggregate fields, no loading/page errors or unexpected origins.
- [x] Configure the worker before map creation; bundle its dependencies and complete installed upstream licence text; retain the unchanged whole-map 5 MiB budget.
- [x] Extend only the loopback test server's map alias, preserving its temporary capture mount, root-capture refusal, decoded traversal and symlink isolation. No real contributor records are used.
- [x] Local lint, types, 603 TypeScript tests, full build and 14 desktop browser tests pass. Ruff, mypy and pytest pass (2,071 passed, 35 skipped locally).
- [x] The prescribed exact-head CI job is green and final independent review has no unresolved findings at `d53eda2e835e57b4ee01dc922fb63d5ebdeceae0`. Making `validate` server-required remains the reserved owner action recorded below.
- [x] Closed Pages artifact and exact next-run handoff are prepared. Creating the valid main-branch run waits for Justin's separate merge go; deployment still requires a later Pages go.

## Changes after review

- Independent review found that retained worker headers linked to the upstream BSD licence but did not reproduce its required full notice. Enable Vite's existing licence-output feature and assert the complete pinned MapLibre licence text in the built artifact. This preserves upstream terms; it changes no project licence or dependency.

## Assumptions and limits

- MapLibre 6.11.2 and Vite 8.3.1 remain pinned. The read-only browser observer inspects the pinned worker's internal parsed index; review that observer during dependency upgrades. It compares distinct H3 tags and every aggregate field because tiling can duplicate features across world copies; it never replaces worker processing or mutates app state.
- The documented test invocation is from the repository root. All contribution/raster replies in this regression are synthetic local fixtures; it verifies packaging and processing, not live tile availability or scientific validity.
- No new dependency or service. Existing MapLibre is BSD-3-Clause; existing Vite is MIT. Full notices and worker bytes count toward the unchanged budget.
- Docker's daemon, GDAL and PostgreSQL/PostGIS/pgTAP are unavailable locally; CI is authoritative for those required checks. No database reset or migration runs against production. Native Android/iOS source is untouched; no device/store acceptance is claimed.
- Fresh independent public checks passed all eight canonical/legacy HTTPS routes, both trusted certificates and exactly `capture_live=false` / `library_intake_live=false`; the prior cached-redirect hold is resolved.
- No merge or deployment is authorized by this PR. The Pages environment allows only `main`/`gh-pages`, requires Justin as reviewer and disallows administrator bypass. A valid fixed Pages run follows a separate owner merge go and still waits for explicit deployment approval. No capture or library activation, protection change, API/database/worker deployment or new production action is included.

Codex authored the implementation/tests for Justin Hart as human of record. No agent approval or human DCO sign-off was added.

## Final verification and release preparation

- [CI validate run 38894216993](https://github.com/global-soil-intelligence/gsip/actions/runs/38894216993) passed at the exact repair head, including GDAL-enforced Python tests, Deno, migration-over-existing-data and local Supabase/pgTAP checks. Both full-history gitleaks scans pass; DCO is skipped under the unchanged in-repository branch policy. No suppression or check was weakened.
- Fresh-context independent review verified the exact commit/tree and all seven changed file hashes, resolved the BSD-notice finding, and found no unresolved issue.
- Independently audited local closed artifact: 40 files, 6,623,128 unpacked bytes; SHA256 `d748a201546fff7b8e71a555ee5abb492cdcb2bffb62d8265dd42c9a160e3d01`. Map bytes: 2,422,310 / 5,242,880. The artifact uses existing public repository configuration, includes the worker and complete licence notices, and has exactly both activation booleans false.
- Local visual readback confirms map rendering/layer switching without first-party worker errors and a closed capture page with zero forms/file inputs. All eight old/canonical routes now retain HTTPS.
- This local artifact is prepared, not deployed, and is not a pending GitHub Pages run. The protected environment accepts only main/gh-pages. Owner merge go starts the existing main workflow; inspect that actual run's source and artifact, then request a separate deployment go. No merge, workflow dispatch, protection change, activation or deployment was executed.

## Existing repository protection setting

The final read-only rules audit found `validate` is **not currently configured as a required merge check**: effective main rules contain PR/deletion/non-fast-forward protections, but no required-status-check rule. `gh pr checks --required` therefore reports no required checks. The complete validate job nevertheless ran and passed on this exact repair head (including CI Python: 2,075 passed/31 skipped; desktop browser: 14 passed; pgTAP: 593 assertions in 11 files, PASS). Both gitleaks jobs passed.

No protection was changed. Making CI `validate` required remains Justin's originally reserved repository action/launch gate; a passing run does not certify that setting. The existing owner review-count exception and protected Pages approval/branch restrictions are preserved.
