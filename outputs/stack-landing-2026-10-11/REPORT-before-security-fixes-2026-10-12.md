# GSIP current landing and deployment report — 2026-10-12

**Gates A and B completed and verified. Gate C’s nine migrations applied successfully, but its zero-security-findings postcheck failed; further deployment is stopped.** New-user sign-up was independently disabled under its narrow approval and verified after reload; anonymous sign-in stays off. Exactly nine October application migrations ran under Justin’s explicit go. No GSIP Edge deployment, worker, export, tile publication or Pages deployment ran. The live service_state singleton now exists and capture_open=false is independently verified.

All thirteen PRs are open with current effective checks green. Justin reviews and merges; no agent merged or approved a PR. The original dirty checkout, reviewed commits, private backup and check policies remain preserved. This edition supersedes the prior pending-C state, retained as REPORT-before-gate-c-2026-10-12.md; earlier reports and receipts remain preserved.


## Gate C current stop evidence

Owner-authorized exact nine migrations applied once at 2026-10-12T13:39:19–13:39:21UTC. CLIexit0; no automatic retry/reset/rollback. **16/17 postchecks PASS; security_advisor_zero_findings FAIL.** All61 table identities/counts match the reviewed result; the original52 counts are unchanged apart from migration ledger17→26. New rows: actors5, service_state1, terms_versions2, upstream_buckets3; all other five new tables empty. Exact target26 catalog passes, preserving only five known SELECT policy aliases and six known hosted additions. Capture_open=false; signup/anonymousoff; all16 independent backfill anomaly counts0. All25 observations carry the actual synthetic flag and tier `-1`; no higher tier invented.

The seven findings concern six distinct objects:

| Advisor category | Level | Objects |
| --- | --- | --- |
| [RLS enabled/no policy](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy) | INFO | attribution_reviews; grant_withdrawals |
| [Anonymous executable SECURITY DEFINER](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable) | WARN | capture_is_open() |
| [Authenticated executable SECURITY DEFINER](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable) | WARN | capture_is_open(); current_auth_user_exists(); finalize_submission(uuid); my_submission_accepts_uploads(text) |

These match the reviewed schema, so no unexpected catalog drift was found. Service-only tables already deny clients by default; the flagged functions are intended guarded APIs/helpers. The advisor findings do not alone establish a data leak, but the owner’s zero-findings gate remains unsatisfied. No finding is suppressed or dismissed as passing. No more SQL, function deployment or dispatch is authorized by the nine-file go. Local-only remediation proposal and synthetic role experiments are being prepared; source and production are not modified by that preparation.

Execution/stop receipt: gate-c-execution-stop-receipt-2026-10-12.json SHA6070c7fac31931203f85625b80e81b37d4d703c518eac0822741dfcaf708966d. Full hosted postcheck receipt SHA85b1f1b89960582446550883ea3556a34d2a3efba9b7a414d9023d7cc246c73e. Backfill receipt SHA7d119247aedcf74a71ca5f799fdebe10390e18b37810ef0fd5ab386800b4d3f1. Root exact ledger/capture receipt SHA1d55444df57084153cc54159b41eafa7c81686570e4187a1dd67daec8b2a1d5e.

Pages protection now complete: pages-admin-bypass-ui-verified-2026-10-12.json SHA3b5df1ba9ce8918d53fe35f09df147a4d046c8efbe0b2619b5821018303aca9e. Fresh target Auth readback off/off, Confirmemail on: SHA9109e7ded4350751409f4ba07f9574f86723a917e3eac0dcc707a693b50ddadc. Current all13 PRs remain open/green at unchanged heads/bases (gate-c-all-pr-readback-2026-10-12.json SHA5c91ac6578099af56c67f173264124b438bb0053106d43a6148af6a501864314).

## PR status

| PR | Branch / head | Base | Current checks |
| --- | --- | --- | --- |
| [#28](https://github.com/global-soil-intelligence/gsip/pull/28) | docs/spec-v3 / `afadda9` | main | validate + gitleaks green |
| [#29](https://github.com/global-soil-intelligence/gsip/pull/29) | wp-6b-launch-hardening / `273e768` | docs/spec-v3 | validate + gitleaks green |
| [#30](https://github.com/global-soil-intelligence/gsip/pull/30) | wp-6c-priors-and-tiles / `a66c4f2` | wp-6b-launch-hardening | validate + gitleaks green |
| [#31](https://github.com/global-soil-intelligence/gsip/pull/31) | wp-6d-contributor-rights / `f3c7043` | wp-6c-priors-and-tiles | validate + gitleaks green |
| [#32](https://github.com/global-soil-intelligence/gsip/pull/32) | wp-6e-provenance / `4f76145` | wp-6d-contributor-rights | validate + gitleaks green |
| [#33](https://github.com/global-soil-intelligence/gsip/pull/33) | wp-agent-1-read-api / `5e50028` | wp-6e-provenance | validate + gitleaks green |
| [#34](https://github.com/global-soil-intelligence/gsip/pull/34) | wp-app-1-phone-app / `f9e1ac2` | wp-agent-1-read-api | validate + gitleaks green; Android/iOS green |
| [#35](https://github.com/global-soil-intelligence/gsip/pull/35) | wp-3b-sync-lock / `afbd744` | wp-app-1-phone-app | validate + gitleaks green |
| [#36](https://github.com/global-soil-intelligence/gsip/pull/36) | wp-agent-0-coding-guidance / `ca275c4` | wp-app-1-phone-app | validate + gitleaks green |
| [#37](https://github.com/global-soil-intelligence/gsip/pull/37) | wp-site-1e-tile-host-policy / `1bf4323` | wp-app-1-phone-app | validate + gitleaks green |
| [#38](https://github.com/global-soil-intelligence/gsip/pull/38) | docs/spec-v4 / `bc1a293` | wp-app-1-phone-app | validate + gitleaks green |
| [#39](https://github.com/global-soil-intelligence/gsip/pull/39) | wp-app-2a-build-readiness / `82880d5` | docs/spec-v4 | validate + gitleaks green; Android/iOS green |
| [#40](https://github.com/global-soil-intelligence/gsip/pull/40) | wp-ops-2-production-reconciliation / `cf063aa` | wp-app-1-phone-app | validate + gitleaks green |

Source: current-all-pr-readback-2026-10-12.json; complete coverage of #28–#40. DCO is SKIPPED under existing same-repository policy, not an agent certification. #34’s older cancelled native run remains recorded; the later successful current-head run is authoritative. All original reviewed commits remain ancestors. #20–#22 were already closed, superseded by merged #24. No merge observed; next PR retargeting remains contingent on an owner merge.

## Changes after review

- **#28 / #33:** afadda988cb8619d4f3a98515629909ca761763f adds exactly Justin’s four-line .gitleaksignore with only three historical synthetic-fixture fingerprints, merged through all seven branches. Reason: CI scans every branch, so every branch needs the same file. No rules, .gitleaks.toml, redaction, full-history scan or workflow changed.
- **#33:** 5e500287b2caa8990d2d658c8c8e100cccae0e21 cleans three synthetic test values so new history does not match the scanner; secret-format refusal and privileged-role rejection remain tested. Sixteen targeted tests and type/lint/format checks passed; merged forward to #34.
- **#34:** owner-approved 94e19ff7fa06a8b284165d57e612c1bda86ce4c8 renames the unchanged MySoil component and updates two imports to fix the macOS case-insensitive module collision. Its regression test failed before and passed after. No permission/dependency check weakened.
- **#36:** coding-guide language was corrected to satisfy I5; the reason and check are appended in that PR. Product wording stays within the language rule.
- **#38:** bc1a2938cbb17feaca44a611fe04fd406713f3d3 implements all four owner-requested documentation revisions: SPEC §11 blocks photos until WP-6f deployment and approved calibration; text screening may exclude only the reliably detected GSIP card quad and bounded margin; start with face plus scene-text detection, with a dedicated plate model conditional on a material staged gap and verified licence; APP-2B v1 ships opt-in sync reminders only, with nearby suggestions deferred until Most Wanted and land-access eligibility. Coordinated BUILD_ORDER and screening-plan text plus 15 regression tests; 13 failed before the edit. Full local Python235 passed/4 GDAL skipped, Ruff/mypy/format/language/link checks passed. No model or dependency added and no screening implementation. Optional APP-2A reproducibility comparison was retained.
- **#39:** 82880d5863cb44d3ff9b3bc9ee5d61b9d122b341 merges the revised spec forward without rewriting the existing app work; the same four documentation/test files are the only merge changes. Fifteen targeted tests pass; current full CI and both native builds green.
- **#40:** source cf063aa5865a86eb86250e3a1f8287545e51f037 is unchanged. Appended the exact authorized A/B and signup action evidence, remaining C gate and assumptions. Original PR body prefixes are preserved. #38/#39 descriptions now contain exact-head CI closeout evidence, with original prefixes byte-for-byte preserved (pr38-pr39-ci-closeout-body-update-2026-10-12.json).

## Required scanner and native artifacts

Fresh verified **Gitleaks8.21.2** command: `gitleaks git . --no-banner --redact --log-opts=--all`. Official archive checksum and the previously audited binary SHA match. Whole clone/all refs: **80 commits reported scanned, zero findings, exit0**, with exactly the three approved exceptions and unchanged rule/workflow hashes. Git has125 reachable commits; scanner-reported count is80 and is not substituted with an expected number. Receipt gitleaks-8212-restored-full-stack-receipt.json SHA cb60ca1ca2f35cfde252b6a7f21731fe8829cb19826edbb19633e5fbf0d8da65. No further suppression.

#34 [native run38189449982](https://github.com/global-soil-intelligence/gsip/actions/runs/38189449982): Android artifact11720633194, 7,144,211bytes; simulator11720817326, 3,323,675bytes, verified unexpired. Its app-build acceptance box is ticked with the run link.

#39 [native run38248853443](https://github.com/global-soil-intelligence/gsip/actions/runs/38248853443), exact head82880d5: Android artifact11746791476, 7,147,349bytes, archive SHA f165f5a74bf61d0d13743c8a5a4513fae469361e556860d45bf088ce6432b6c1; simulator11747696114, 3,324,927bytes, SHA503740d9a052b2229a0b1b636827ed9d9aa2a6e269c29ed17fe277e42e0e61a3. Both are unexpired and jobs successful. Current artifact metadata was verified; these new archives were not redownloaded. Two optional full-run API metadata calls returned HTTP502; current-head check-runs/artifact readbacks establish success independently. Prior #39 downloaded payload proof remains historical: same-job Android bytes reproduced, iOS entry payloads matched though archive bytes differed; it does not prove cross-run or signed-store reproducibility.

## Deployment checklist and execution evidence

| Step | State | Evidence / next action |
| --- | --- | --- |
| Governing documents / immutable handoff | DONE | v3 sources read before landing; heads/checksum verified; reviewed commits retained. Production target gsip, toxldjgwkxtneoqsazym, us-east-1. |
| Restore / CLI login | OWNER DONE | ACTIVE_HEALTHY and owner-authenticated CLI2.118.0; no agent restore/login or credentials handled. Free tier retained by owner choice. |
| Counts / effective baseline / recovery | DONE | All52 tables counted. 5 contributors,25 submissions,25 photos,0authusers,0publiccells; owner classifies seed data. Effective17-July catalog verified with exact six ownership-alias allowances and preserved hosted extensions/grants. Foreign tables absent. Private0700/0600 backup intact and isolated18/18 full-ledger restoration proven. |
| Required pre-migration checks | DONE | Fresh Oct12 network-none PostgreSQL/PostGIS/pgTAP Docker migration test13/13 and rehearsal64/64 at cleanf9. Docker initially stopped; first attempts failed before assertions, then passed after starting the installed engine. |
| Gate A history reconciliation | EXECUTED / VERIFIED | Owner accepted Realtime89 after initial81→89 drift caused a stop. Resume preflight passed. Three exact CLI repairs executed separately, exits0, full-name/version/hash readbacks18→31→18→17. All application counts, catalogs/RLS and backup unchanged; advisor0. |
| Gate A final inventory / dry run | VERIFIED | migration list exit0. CLI dry-run exit0; authoritative bullet plan contains only9October files, hashes bound. Initial local extractor double-counted repeated filename renderings; its diagnostic receipt is retained, then exact9-entry plan independently verified before B. |
| Gate B foreign function | EXECUTED / VERIFIED | Sole wavefunction-api deletion exit0. Inventory only prior-attach ACTIVEv3/JWTon; selected full metadata exactly matches pre-delete. gsip-public absent. |
| New sign-up closure | EXECUTED / VERIFIED | Separate ownergo: only Allow new users to sign up switched off, saved once and reloaded. signup0, anonymous0, Emailenabled, Confirmemail1, manual linking0 and Save disabled. No signup/write smoke exercised. |
| Gate C nine October migrations | EXECUTED; SECURITY STOP | Exact nine files applied, exit0. Exact26ledger/original17hashes preserved; all61 counts match; target26catalog/RLS passes; capturefalse/Authoff and all16backfill anomaly counts0. Security advisor7instances on6objects across3categories fails zero-findings gate. No further deployment. |
| Edge deployment / smoke | GO REQUIRED | Redeploy prior-attach JWTon and gsip-public JWToff after database readiness. Stale prior function must not drain after old claim RPC is removed. Then protocol200, resolution9cell400, MCP4tools. No new deployments or smoke checks. |
| Repository variables | BLOCKED / GO REQUIRED | Names-only fresh readback: publishable-key variable and legacy VITE_SUPABASE_URL present; SUPABASE_URL and VITE_GSIP_PUBLIC_API absent, worker secret absent. Configure shared/public API URLs and remove legacy URL after readiness/go; owner adds service-role secret through GitHub store. Values/keys not inspected or printed. |
| Contributor-rights worker | BLOCKED | Run once after DB/function/config readiness and explicit production gate. |
| Photo QA / release publication | BLOCKED | #38’s data-only/photo policy is a specification proposal, not implemented enforcement. No photo-capable QA/export/publishing dispatch until reviewed data-only enforcement or deployed/calibrated WP-6f satisfies the gate. |
| HF export | OWNER ACTION / BLOCKED | Owner creates global-soil-intelligence/gsip and adds HF_DATASET_REPO/HF_TOKEN. Fallback viridis-research/gsip. No export dispatch. |
| Tiles | CONDITIONAL HOST APPROVAL; BLOCKED | Same-origin repo GitHubPages approved only with SoilGrids-only content, palette-version release assets, no git tiles, target<=700MB and whole site<1GB, deploy-time assembly and actual206Range proof. Policy PR37 ready; build/publish/assembly/proof pending. ISRIC WMS remains fallback. |
| Pages | APPROVAL PROTECTION COMPLETE; DEPLOY GO REQUIRED | API set sole required reviewer Justin/jdhart81/user179389866. Under the subsequent explicit instruction to drive the task, the settings UI disabled administrator bypass, saved once and persisted after reload; fresh API can_admins_bypass=false, other protection rules and main/gh-pages policy IDs unchanged. No Pages deployment. Later build captureclosed and verify prerendered pages/llms.txt after separately approved deploy. |
| Launch/operator actions | OWNER | Require CIvalidate; DNSWP-SITE-1D; counsellegalapproval then URLvars; CAPTCHAchoice/closed-serviceexception; paidtierbeforecapture; ownerViridisApple/Googleaccounts/signing; everySPEC§11gate before capture/anonymous opening. |

Primary execution receipt: production-gates-a-b-execution-receipt-2026-10-12.json, SHA **c4934bed71dc8427648e89668f2899eedfc033ab9a0d9371d760a5440333f0a4**. Post-A full count/catalog/security receipt SHA77a91551ad9e04f11ade62478a23149c9dec74bbb8d7fb5f424655c7fc86f4bb. Signup receipt SHAbfec01a0ac075bffaf33f9d143a36f9481638a24ace17d59d9a4e5a0c1fc2554. All command receipts include only target/metadata, safe output, exitcode and full-output hash; no secret, coordinate or contributor content. Current52table counts are in production-table-counts-after-gate-a-2026-10-12.md. Private backup contents remain outside git and public receipts.

## Gate C exact command — executed under owner go; security postcheck stopped

Nine ordered files:

1. 20261010120000_wp6b_capture_gate.sql
2. 20261010120100_wp6b_path_binding.sql
3. 20261010120200_wp6b_finalize_and_settle.sql
4. 20261010120300_wp6b_k_anonymous_cells.sql
5. 20261010120400_wp6b_attribution_and_metadata.sql
6. 20261010130000_wp6c_priors.sql
7. 20261010140000_wp6d_contributor_rights.sql
8. 20261010150000_wp6e_provenance.sql
9. 20261011090000_wp_agent1_releases.sql

```sh
GSIP_REPO="/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo"
GSIP_CLI="$GSIP_REPO/node_modules/.bin/supabase"
"$GSIP_CLI" db push --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_REPO" --skip-vault
```

Full file hashes/effects/preconditions/readbacks: gate-c-migration-plan-2026-10-12.md (SHA7f561293f53ba6359aa4ecf1ddf8ff0228d899d8665079f0f0d006f462f1a479) and .json (SHA3cd28d14a2ef09b853999158675d2b275acfc9d7a9b807df2dd59db02ee91e35). Before executing, verify fresh state and no overlapping operator/worker writer or stale prior invocation. No auth config push, seeds, roles, July DDL replay, reset, generic rollback or automatic retry. On partial push/failure, stop with exact per-file ledger evidence and prepare a reviewed fix forward. After execution: exact26ledger, advisor0, singletoncapturefalse, signup/anonoff, stable original counts, actors5 and exact relationship/tier backfills, correct terms/holdout, reviewed20-table RLS/privacy/privileges and k-anonymity. Existing status/finalization/photo-verdict values may intentionally change; no byte-equality promise is made.

## Follow-ups and open owner actions

#35 sync WebLock guard and unsupported-browser fallback tested/green. #36 root coding-agent guide links API-consumer docs, commands and guardrails. #37 tile-host policy prepared. #38 photo screening/notification specification revised and green; implementation waits for Justin’s specification approval/merge and calibration/model gates. #39 CI versions and Android private cloud-backup exclusions tested and built; modern device-to-device transfer allowed, legacy backup excluded. iOS WebKit reliable exclusion and physical-device proof remain unresolved: do not claim privacy protection on that platform. Store accounts, certificates, keystores, listings and deep links remain owner-dependent; signing inputs documented as placeholders. Licences remain MIT/ODbL1.0/CCBY-SA4.0, no new paid or closed default service/model installed.

Immediate blocker is **zero-security-findings remediation**, which needs a documented specification update before any privilege-architecture implementation and a new exact migration go before production changes. Pages administrator bypass is now disabled. #38 specification approval and all merges remain owner-controlled. HFcreation/secretstore readiness, signing accounts, counsel/legalURLs, DNS and launch prerequisites stay pending; CAPTCHA and paid upgrades remain deferred while captureclosed. Opening capture/anonymoussign-in and any licence or new paid/closed-service exception remain solely Justin’s decisions.

## Assumptions and verification limits

- The original workspace remains wp-site-public-hub at a581d20defdd376d913af583cd6b2095a9eda86d with61dirtyentries excluding task outputs; freshly verified digest9f267c791a56dbfe1cbdb8f104cec8dcaa9bc912d2b8c7cfde757ce5dab63419 matches the preserved state. Work occurred in isolated clones/worktrees.
- Owner’s target, foreign-app attribution, seed classification and platform89 acceptance are authority; the underlying Realtime drift cause is unknown. Independent evidence establishes counts/effective catalog, not past-row provenance. Exact current metadata equality does not reconstruct historical DML or prove a hosted system identical to stand-ins.
- No overlapping production writer is assumed. GateC must recheck freshness/operational activity before execution. Prior Edge transition and photo-publication enforcement are explicit limits; applying SQL does not deploy worker code or implement the new spec gate.
- LocalGDAL/Deno/PostgreSQL executables are absent from PATH; Docker supplies PostgreSQL/PostGIS/pgTAP and CI supplies full GDAL/Deno/browser checks. Local pinned Chromium is missing; browser passes are CI evidence. Native SDK/Xcode evidence was established previously; simulator builds do not replace physical-device backup verification. Local full-suite235pass includes4GDALskips, stated explicitly.
- Recovery backup is ledger-only, not an application-data rollback. Canonical repair was actually executed through CLI only now; rehearsal64/64 is separate modeled proof using synthetic stand-ins.
- Newer #39 archives have metadata/job success evidence but were not redownloaded; previous downloaded native payload comparison remains scoped to that older run. DCOskip is neither an agent approval nor certification. No hidden full-run API failure is called a build failure or success proof.
