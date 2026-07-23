People should be able to start a soil observation with a phone without printing a reference card. The existing protocol already accepts cardless photos; this change makes that clear in the app, website, protocol/MCP/OpenAPI descriptions and builder guidance. Advanced optional instrument declarations now start collapsed, while an attached declaration remains visible and removable.

WP-COLLECT-3; closes #85. Stacked on the specification-first #86 (`docs/spec-v16`).

## Invariants and acceptance

- [x] Preserve I1–I15, L1–L7 and B1–B8. Required photos A+B and optional C, other QA checks, personally accepted rights, private invited admission, real sample depth, immutable ownership and publication holds stay effective.
- [x] “No printed card needed” appears before capture; optional physical-card PDF/help remains reachable. Static guides describe framing and never modify image pixels.
- [x] Library registration stays explicit. Skipping it queues an ordinary observation with no invented sample, depth, spectrum or instrument. Advanced JSON starts collapsed and retains strict validation/import/clear/restart behavior.
- [x] Default/closed/native and explicit authenticated rights-recovery paths stay intact. No new camera API, permission, schema, worker, dependency, licence or service.
- [x] Regressions fail against prior wording/disclosure, then pass after the source change. Existing cardless/uncalibrated QA and native permission/SDK policy checks remain effective.
- [x] Independent adversarial review found no unresolved implementation issues; exact final source confirmation and CI evidence will be appended below.
- [x] Required CI and Android/iOS artifact runs green.

## Verification so far

Frozen dependency installation, whole-workspace lint and typecheck passed. All 705 JavaScript tests passed. Ruff passed; mypy found no issues in 83 source files. The focused permission/optics/QA suite passed; full builds/Python/browser checks and required CI are in progress and will be recorded below.

The fresh reviewer separately ran 27 changed capture tests, eight site regressions, 45 protocol/REST/MCP tests and 29 permission tests successfully, checked the tracked diff and new test hashes, and found no actionable issue. No GitHub approving review was submitted.

## Assumptions and limits

- This implements bounded package A from the researched next-build brief. A live browser camera guide is a separately held design follow-up, not an implemented feature here.
- Protocol shape/version 1.1 stays unchanged because cardless acceptance and `card.optional=true` already exist. Only guidance is aligned.
- Source RGB photographs are distinct from separately extracted `camera_rgb` summaries, explicitly registered samples and instrument-measured spectra. The staged extractor already supports cardless input; real-field extraction remains held. No automatic summary, sample, spectrum, physical-pair or biome claim is added.
- PDF artwork and optional physical-card printing instructions remain valid. Legal-pack wording remains draft, without adopting notices or asserting compliance.
- No physical-phone or scientific-accuracy experiment ran. Local browser emulation and CI are software evidence, not universal-device qualification.
- GDAL, Deno, PostGIS/pgTAP and native SDK checks rely on CI where the corresponding local tooling is absent/unverified. Local results will identify any skips.
- This source push grants no merge, Pages, migration, account/invitation, worker, capture/library opening or other production authority.

Agent contribution: Codex authored the changes with task agents for Justin Hart as human of record. Commits include Codex attribution; no human DCO sign-off was added.

## Changes after review

- Commit 731a30f refreshes exactly two source hashes in `docs/ios-native-scope.json` for the separately reviewed camera-purpose text and added regression. The full Python run correctly caught stale integrity bindings. A maintenance note records the reason; the historical baseline, every other binding, native file/effect scope, permission policy, validator and all scope-expansion rejection tests remain intact. No suppression or weakened check. Fresh independent review verified the two-file follow-up and exact final head `731a30ff6f8f3a90e0df31eb1d977edf1fcaf912`; its independent 67 scope/permission tests passed with no actionable finding.

## Completed local verification

These results supersede the provisional in-progress local status above: all 705 JavaScript tests, lint, typecheck, web and closed native-web builds, map/site budgets, Ruff and mypy passed. Full Python rerun: 2,163 passed, 35 skipped (local GDAL/opt-in native-tool tests). Both desktop browser suite (16/16) and invited phone-browser matrix (4/4 across Chromium/WebKit) passed with synthetic loopback fixtures. Existing cardless/uncalibrated QA, scope/permission and default-closed artifact checks passed. Native artifacts, GDAL, Deno, PostGIS/pgTAP and populated migration results are tracked through the exact-head CI runs; this source package adds no database change.

Independent review covered the full source diff and exact final head. No physical phone, scientific experiment, account operation, migration, worker, production deployment, merge or activation occurred. Required CI is still pending and will be appended once verified.

## Verified final CI and artifacts

Exact head `731a30ff6f8f3a90e0df31eb1d977edf1fcaf912`: [validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38986477510) is green: 705 JavaScript tests, 2,167 Python tests passed (31 opt-in native-tool skips), 16 desktop + four phone-browser cases, 632 pgTAP assertions in 12 files, populated migration regression and Deno checks. GDAL was required in CI. Both secret scans passed; DCO is skipped under the repository's agent policy.

- [x] [App build](https://github.com/global-soil-intelligence/gsip/actions/runs/38986477052): Android and iOS jobs passed, including permission/closed-SDK, repeat-build, licence/runtime and reference-build audits. Non-expired `gsip-capture-android-debug` and `gsip-capture-ios-simulator` artifacts exist for this head.

Independent review is resolved. No merge or deployment occurred; main remains `33260db1ce49c50600942694e43269759e554e66`, Pages still requires jdhart81 approval with admin bypass disabled, and the public/default activation manifests retain capture=false and library intake=false. Review/merge order remains #86 then #87. Live camera-guide implementation and actual-phone/scientific qualification remain separate follow-ups.
