# iOS storage design review handoff — 2026-10-14

Owner instruction: merge #69 and prepare the next iOS storage design for review. No production changes or capture opening.

## Source outcome

- [#69](https://github.com/global-soil-intelligence/gsip/pull/69) merged at `de9d1221b7c73e9be5c7e25ccaa24dcfa7903934`, 2026-10-14 22:41:11 UTC, using exact approved head `258b57732a94968e576eb15e848566a487cb4878`. No protection bypass, history rewrite, agent approval or DCO certification. Conventional merge metadata and Codex trailer verified.
- Main [CI passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38649327998) and [secret scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38649328085).
- [#70: proposed native iOS private-storage design](https://github.com/global-soil-intelligence/gsip/pull/70), branch `docs/spec-v12`, head `06902edf36810c55e51b169dcb813e81b22206b0`, is open/unmerged. Its CI status is recorded below after the exact-head readback. No auto-merge was enabled.

## What the proposal adds

The source audit found no complete existing storage mechanism. The next design proposes an excluded app-owned system-SQLite store, separate non-backed-up Keychain anchor, bounded TypeScript/native bridge and owned nonpersistent host. It defines the six-store transaction/API mapping, exclusion-before-open, DELETE/EXTRA settings, receipt/acknowledgment and staging limits, account/rights/reminder fences, restore quarantine and isolated legacy migration. SQLite and Keychain remain separate stores; cross-store durability, host seams, camera handles and physical backup exclusion are unproved.

SPEC §15.11 and BUILD_ORDER register future APP-2C2A native primitives/host, APP-2C2B TypeScript integration and APP-2C2C legacy recovery. All six new criteria remain unchecked. All132 prior acceptance lines/states and prior normative sections are unchanged. Exactly four paths changed; all370 other existing files/modes remain identical. No runtime, dependency/lockfile, workflow, permission/SDK rule, licence or deployment configuration changed.

## Changes after independent review and reasons

1. Replaced an insufficient stock-controller/router proposal with an app-owned public host/asset-handler candidate: the stock special-file branch runs before custom routing. Public seams require compatibility/bypass proof; no core fork is authorized.
2. Made camera URI/provenance handling an explicit held interface gate: current plugins provide no opaque native output-handle broker.
3. Required known-schema legacy export without database creation/upgrade, frozen bounded snapshot consistency and a user-driven full relaunch rather than process exit. Supported purge completion remains distinct from physical erasure.
4. Corrected Keychain default access-group terminology and bounded counter exhaustion. Passcode loss, reinstall, pending-before-commit availability and backup limitations remain explicit.
5. An unsafe table-row mutation initially survived global phrase checks. Strengthened the existing document regression to enforce each actual restore outcome. Final review rejected that mutation and all12 other tested unsafe edits. The initial survivor/mutable-freeze mismatches are retained in review evidence; none is called a passing final review.
6. Initial Ruff found one overlong test line; wrapped it, then reran lint/types and the related suite successfully. No check was weakened.

## Verification actually performed

- Local full lint: ESLint, language and Prettier passed. Ruff passed. Strict mypy passed over79 source files. Diff whitespace passed.
- Related specification/storage tests:93 passed, no failures/errors/skips. All25 new tests failed on unchanged main as expected, with zero errors/skips. Independent reviewer repeated both outcomes in private copies.
- Independent final review:13 unsafe document mutations rejected; all374 final file hashes/modes, normative bytes and acceptance preservation verified. Exact committed tree/parent, four paths, clean checkout, Conventional Commit and Codex trailer verified.
- Gitleaks8.21.2 over non-shallow full history/all refs, with redaction:159 reported commits, zero findings. Ignore SHA `bb3e40f995ae51b8e1b9300bd2d079aa5a1b482f259642f52074366b908310e5`; config SHA `e846bacbb1ce5c41f571a10cdaf0e1fde7bfa399fc5c876480b57124059cc760`; unchanged, no new suppression.
- Final374-file manifest `d87d1f26f18a2be15e28b4f82e4a9dde553fcd117866c912a94aa1d733659e10`; independent review SHA `549894ad59ece97651ea65958084eba7925eebb32af61c4cff34d6a6a2c8534f`; exact-commit closure SHA `289219a0bb6b947f40a37c34bf4cca614f407b92eb6c5c0f2b38b308f62f0709`.
- Fact reviews: SQLite/anchor SHA `cf6d815d3196146c3dfd45620f1a3bc096153d7d04bef9f120bd27151f9f507e`; host/migration SHA `9d4524b02fce245102be91cc49ba4927853f9f19e9dc869cdab8a1ffd5719ce1`. Document bytes unchanged between factual V3 and final test-only V4.

Document-contract tests protect proposed written boundaries. They do not prove storage implementation, native compilation, physical erasure, cloud transport or device behavior. No native/device/backup experiment ran. Full hosted CI, when successful, supplies its disposable environment; no local GDAL/PostGIS/pgTAP/Deno/native acceptance is asserted for this docs-only package. These paths do not trigger app-build artifacts.

## Deployment/activation checklist for this turn

| Item | State and evidence |
| --- | --- |
| Production migrations, functions, Auth, data and worker dispatch | Held; no production project API/CLI operation or worker dispatch performed. Production state/counts/advisor/capture were not freshly queried. Prior deployment evidence is not re-certified here. |
| Capture and library activation source | Unchanged; source/CI build flags stay closed. No capture/sign-in opening performed. |
| Pages | [#69 main run](https://github.com/global-soil-intelligence/gsip/actions/runs/38649328063) remains waiting. Required reviewer is solely jdhart81; `can_admins_bypass=false`. No approval/deployment action performed. `PAGES_PROTECTION.json` readback saved. |
| Worker schedules | All five `GSIP_{PRIOR,EXPORT,QA,RIGHTS,CLEANUP}_SCHEDULE_ENABLED` names remain absent in repository-variable readback; no value or secret content read. No dispatch. |
| Native prototype/migration/device | Held for exact architecture, narrow language/file exception, passcode/recovery choices and separately scoped device/account/signing inputs. No generated native or private data changes. |
| #70 merge | Justin's next review/go; left open. #69 is the only merge executed under this request. |

## Pending owner decisions, options and recommendation

- Design: review this bounded native candidate (recommended), or keep iOS held and research another mechanism.
- Language: consider only the listed Swift coordinator/owned-host/store/bridge and direct native-test exception, with exact file/patch scope before code; otherwise retain TypeScript/Python-only. No exception has been granted.
- Passcode: candidate requires a device passcode and holds access on anchor loss/uncertainty. Accept that product trade-off explicitly, or require a new anchor/policy design. Approved no-cloud policy alone does not resolve it.
- Recovery: preserve quarantined bytes without automatic destructive reset (recommended). A later explicit fresh-start UX loses unsynced work and old account access; privacy contact covers old contributions until e-mail linking exists. No reset or new account is currently authorized.
- Existing production/store/legal/photo-calibration/capture/account/signing decisions remain separately gated. No new paid/closed service or licence change is proposed.

Assumptions: current source inventory; app-owned/non-shared root and legacy store; public native seams can enforce the proposed boundary; supported OS/toolchain graph can meet it; capacity figures are provisional. These are admission tests, not confirmed capabilities. A design merge alone authorizes no implementation, native-language exception, dependency, recovery reset, device or production operation.

## Final hosted CI closure

Exact head `06902edf36810c55e51b169dcb813e81b22206b0`: [validate passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38651079315), [PR scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38651079464), [branch scan passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38651043670). Required checks are green, merge state CLEAN; DCO is skipped under the unchanged workflow, not agent-certified.2,031 Python passed/31 skipped/37 warnings;12 browser passed;mypy79 files;593 pgTAP assertions/11 files;Deno passed;data-preserving migration suites13/13,19/19,13/13 passed. Lint/typecheck/JavaScript/build/map-budget and disposable database lifecycle passed.

Readback confirms main still `de9d1221b7c73e9be5c7e25ccaa24dcfa7903934`, #70 OPEN/unmerged with no auto-merge, #69 Pages waiting. Saved `PR70_FINAL_CHECKS.json`, `CI_FINAL.json`, `CI_SAFE_TEST_SUMMARY.txt`, `PAGES_FINAL_STATUS.json` and `MAIN_FINAL_REF.json`. Existing PR descriptions preserved; #69 received appended merge evidence, #70 received final CI evidence and its CI acceptance checkbox was completed. No production/capture operation or further merge occurred. The next action is Justin's review of #70 and its separately pending implementation/language/passcode/recovery decisions.
