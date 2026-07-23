## Problem and result

The closed capture page simultaneously promises "Ready for your first observation" and says contributions are unavailable. It also singles out legal review as the collection blocker after Justin removed the outside-counsel prerequisite.

WP-SITE-1H gives the closed card factual preparation copy and shows "Collection is closed" in its status panel. The live flow retains its existing dynamic status. The reference-card and map links remain available. Closes #80.

Stacked on #79 (`docs/spec-v14`) so BUILD_ORDER contains the package registration. Merge order is #79, then this PR; neither merge nor deployment is authorized by opening this proposal.

## Invariants and scope

- Preserve every activation, authentication, capability, upload, sync and publication gate. Closed builds still expose no photo inputs or queue action.
- Preserve live-capture status behavior and I1–I15/B1–B8, especially language, private data and agent boundaries (I5/I7/I12).
- Only App.tsx, its behavioral regression and the work-package issue link change. No schema, dependency, licence, workflow or configuration changes.

## Validation

- Added regressions before changing App.tsx: **2 failed / 3 passed** against the existing UI. The failures expose the old closed headings and contradictory ready status.
- After the fix, targeted app tests: **5 passed**. Both unset and false capture flags show closed status, retain map access and lack A/B/C photo inputs or a queue action; the live test retains its ready status.
- `pnpm lint`, `pnpm typecheck`, `pnpm test`: passed; **604 tests** across all four tested packages.
- `pnpm build`, both map/site asset budgets, `node scripts/build-pages.mjs` and `pnpm --filter @gsip/capture-pwa build:app`: passed.
- Packaged browser and native web-bundle manifests retain `capture_live=false` and `library_intake_live=false`. No bundle was deployed.
- Independent read-only review: no material findings; `git diff --check` passed.
- CI supplies GDAL, disposable PostgreSQL/PostGIS/pgTAP, Android and iOS runner checks. Their results are pending until the linked runs complete; local web builds do not establish a device build or storage/backup proof.

## Assumptions

- The service remains closed until its separate collection package and exact production go. Changing copy does not establish upload readiness.
- Default closed builds should describe their actual status even if an old local queue exists. The closed-status label changes no queue data or sending behavior.
- Outside counsel is not the sole technical blocker; the factual preparation message avoids inventing a launch date or claiming completion.
- This is a source-only browser/native UI correction. The protected Pages deployment and production capture/library gates remain separately held.

Codex authored the source/test change. Justin Hart remains human of record and final reviewer; no DCO certification, approving review, merge or deployment is performed.

## Additional verification

The packaged closed Pages artifact at head `3d27077277374fcf2f7bc2411401dd16b6186462` was exercised in an isolated headless browser on loopback, with every external request blocked. Both closed headings and the map link were visible; the ready heading, photo inputs and queue button were absent. Its fetched activation manifest was exactly false/false. Screenshot and machine-readable receipt are retained privately; no preview artifact or synthetic data was published.

## CI evidence

At exact head `3d27077277374fcf2f7bc2411401dd16b6186462`, [validate run 38975572947](https://github.com/global-soil-intelligence/gsip/actions/runs/38975572947) and [app build 38975572671](https://github.com/global-soil-intelligence/gsip/actions/runs/38975572671) completed successfully. Android, iOS and both secret scans passed; the internal-branch DCO job was skipped. The app run retains Android APK artifact `12079227079` and iOS simulator artifact `12079041683`, bound to this source head and not expired. CI simulator/APK artifacts are not physical-device storage/backup proof. No merge or deployment followed.
