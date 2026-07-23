# GSIP: Gate E complete — 2026-10-12

The two approved functions are deployed to gsip (`toxldjgwkxtneoqsazym`) from reviewed commit `19e626c8a95fae32dbd8ad0ff96bc96aba541a0f` with CLI 2.118.0. Prior-attach is ACTIVE v4 with JWT on; gsip-public is ACTIVE v1 with JWT off. Both commands ran once and returned exit code 0. No source, dependency, PR, secret, Auth setting or database change was made in this gate.

All eight anonymous production smoke tests passed: prior denial 401; protocol 200; resolution-9 refusal 400; MCP exactly four read-only tools; coarse cell/list/latest-release reads 200 with expected empty public data; unsupported POST 405. Function metadata independently confirms the JWT settings.

Final readbacks passed all 15 checks: exact 28-entry history, unchanged full catalogs/grants and all 61 counts, security findings zero, capture closed, and exactly the two intended functions. Sign-up and anonymous sign-in remain off, private schema is unexposed, and all three worker schedules remain disabled with no active run. The 13 PRs #28–#40 remain open and green at their exact reviewed heads (refreshed 20:01 UTC). APK and simulator artifacts remain verified.

Evidence: [completion receipt](gate-e-completion-receipt-2026-10-12.json), [final database/function readback](gate-e-final-db-functions-20261012T2007.json), [eight live smoke checks](gate-e-http-all-20261012T200606684396Z.json). Exact commands are retained in the two command receipts and the approved Gate E plan. No secrets, response bodies or contributor coordinates are recorded.

Next gate: repository variables (`SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_GSIP_PUBLIC_API`), retirement of old `VITE_SUPABASE_URL`, and owner-only confirmation of the service-role secret. It must be prepared for separate approval; no variable changes were made here. Workers, export, tiles and Pages remain held. Justin reviews and merges; capture stays closed until launch gates pass.

Assumptions and limits: the latest instruction authorizes the previously presented two-function gate only. These are synthetic-fixture read tests; no successful owner/service prior job was invoked on production. Existing platform keys were neither read nor changed. Local Deno remains unavailable; the current-head successful CI Deno step is the compile evidence. All earlier fixes, PR links and pending owner decisions are retained below as historical Gate D context; Gate E status above supersedes its prepared-only function status.

---

# GSIP landing and Gate D completion — 2026-10-12

All 13 PRs are open and green at their newly pushed heads. The two security fixes were committed on their owning branches and merged forward without rewriting reviewed history. No PR was merged or approved. Gate D applied exactly the two separately authorized migrations once at 15:25 EDT. Production now has 28 migrations and the complete hosted security advisor reports zero findings. All 61 table identities/counts are unchanged except the two new migration records; all 26 historical record hashes are preserved. Capture, new-user sign-up and anonymous sign-in remain closed. No other deployment or PR merge was performed.

## PRs and checks

| PR | Current head | Base | Checks |
| --- | --- | --- | --- |
| [#28](https://github.com/global-soil-intelligence/gsip/pull/28) | `a9f89e3` | main | Green |
| [#29](https://github.com/global-soil-intelligence/gsip/pull/29) | `6b0bd81` | docs/spec-v3 | Green |
| [#30](https://github.com/global-soil-intelligence/gsip/pull/30) | `2d5b0f0` | wp-6b-launch-hardening | Green |
| [#31](https://github.com/global-soil-intelligence/gsip/pull/31) | `620c36a` | wp-6c-priors-and-tiles | Green |
| [#32](https://github.com/global-soil-intelligence/gsip/pull/32) | `5bea5b7` | wp-6d-contributor-rights | Green |
| [#33](https://github.com/global-soil-intelligence/gsip/pull/33) | `f156ad9` | wp-6e-provenance | Green |
| [#34](https://github.com/global-soil-intelligence/gsip/pull/34) | `19e626c` | wp-agent-1-read-api | Green — APK and simulator ready |
| [#35](https://github.com/global-soil-intelligence/gsip/pull/35) | `79baf1e` | wp-app-1-phone-app | Green |
| [#36](https://github.com/global-soil-intelligence/gsip/pull/36) | `505a0e8` | wp-app-1-phone-app | Green |
| [#37](https://github.com/global-soil-intelligence/gsip/pull/37) | `a325c61` | wp-app-1-phone-app | Green |
| [#38](https://github.com/global-soil-intelligence/gsip/pull/38) | `322ecd4` | wp-app-1-phone-app | Green |
| [#39](https://github.com/global-soil-intelligence/gsip/pull/39) | `d522c77` | docs/spec-v4 | Green — APK and simulator ready |
| [#40](https://github.com/global-soil-intelligence/gsip/pull/40) | `f5c6967` | wp-app-1-phone-app | Green |

Fresh checks are bound to each current head, with all bounded check connections exhausted. Final CI receipt: `security-fix-all-pr-ci-final-2026-10-12.json`, SHA-256 `e053c78464f62b052e1e8c0c24013947219fad467e8ef03762239a2e180db158`. DCO is skipped under the existing same-repository policy, not certified by an agent. Two earlier #39 native cancellations were superseded by the successful current-head run; neither is counted as passing.

Current native runs with nonempty, unexpired APK and simulator archives; #34/#39 payloads were downloaded and checked using the unchanged permission checker:

- #34: https://github.com/global-soil-intelligence/gsip/actions/runs/38265397710
- #39: https://github.com/global-soil-intelligence/gsip/actions/runs/38265400180
- #35 also builds successfully: https://github.com/global-soil-intelligence/gsip/actions/runs/38265398452

The new #39 build receipts and binaries verify CI version numbers and compiled Android backup rules. Android same-input payload bytes match; iOS entry contents match while complete ZIP bytes differ. Neither this nor the simulator proves iOS cloud-backup exclusion on a device. Native verification receipts: `c75706191ed8662af01289fcbc23de638d2b83716c7d73ff41cbb7f00646f2cd` and `3c8dd42a5ddbb0a5cce80c151fd197ac378ac10eb96bc9fb9e5b341be816be79`.

## Changes after review

- **#28 / #33:** `afadda9` adds exactly Justin's four-line `.gitleaksignore`, with only the three approved historical synthetic-fixture fingerprints. It was merged through the stack because CI scans every branch. Detection rules, redaction, full-history scanning and workflow are unchanged.
- **#33:** `5e50028` cleans the three synthetic test values, preserving secret-format refusal and privileged-role rejection. No new suppression.
- **#34:** owner-approved `94e19ff` fixes the macOS MySoil module-name collision, with a failing-before regression test; permission and dependency checks stay intact.
- **#36:** the coding-guide wording was corrected for I5.
- **#38 / #39:** `bc1a293` adds Justin's requested photo-publication gate, bounded reference-card text exception, face/scene-text-first screening and sync-reminders-only version 1. The specification still awaits his review and merge; these docs do not implement screening. #39 inherited those revisions.
- **#28:** `a9f89e3` documents the database privilege boundary in SPEC §6 and the owning packages' acceptance criteria before SQL implementation.
- **#29:** `6b0bd81` adds the capture/finalization migration and 16 regression assertions. Capture uses its existing readable column; the guarded finalizer moves to a private implementation behind an unchanged public invoker signature. Five new assertions fail before; all 16 and 99 existing assertions pass after.
- **#31:** `620c36a` adds the rights-helper migration and 21 regression assertions. Auth-user and withdrawn-grant guards remain intact behind bound invoker adapters; service-only tables gain restrictive deny-all policies. Eight assertions fail before, including temporary permissive-policy exposures; all 21 and 209 inherited assertions pass after.
- **#30 / #32–#40:** these corrections were merged forward. Follow-up branches each inherit #34 independently; #39 inherits updated #38. No sibling scopes were combined. All 26 already executed migration files remain byte-for-byte unchanged.
- **#40:** `f5c6967` preserves historical preparation, records Gate C's stop, and adds the exact separate two-file Gate D with no implied deployment approval.

All 13 PR descriptions were updated append-only, with every original body prefix verified byte-for-byte and heads unchanged. #34 and #39 include checked current-run acceptance links. Receipt `security-fix-all-13-pr-body-update-receipt-2026-10-12.json`, SHA-256 `76fb8d2d8a83ecbc15202dc223f7bd2d1ab37a382fcc78faeba0234e1fa1ccd7`. No existing acceptance or historical test claim was rewritten.

## Verification

The exact candidate `19e626c8a95fae32dbd8ad0ff96bc96aba541a0f` passes 299/299 pgTAP assertions, the actual migration script's 13/13 assertions, and 33/33 independent local HTTP checks. Thirteen new assertions fail before the fixes. Fresh ordered installation of 28 files and a seeded 26-to-28 upgrade produce identical catalogs, counts, grants, owners and storage policies. New private dispatch permissions are exact; existing public caller and schema/table/column privileges remain unchanged. The three relevant official advisor rules produce 7 findings before and 0 after locally; this is separate from the required hosted result.

Source proof SHA-256: `5f410d445a8b2926cec75dee3395ec539922fcceadac9645e943187715ed6083`. HTTP proof: `1667c648580787a6dd79485a8e57f9973cb2472e42ba426e45429f938da53928`. Complete target-28 primary and supplement metadata are retained outside Git for strict postchecks.

Whole-stack Gitleaks 8.21.2 reports zero leaks: 84 scanner commits, 141 reachable commits, only the three approved historical entries. Receipt SHA-256 `c6311a5fd48a52c37eaa4a298d6913be8e1f4d12f9be16204cac12683159b1ed`. No dependency or license change, proprietary SDK, paid service, detection suppression or RLS weakening was introduced.

## Deployment checklist

| Step | State and evidence |
| --- | --- |
| Gates A/B | Done under separate approvals: ledger 18→31→18→17 and only wavefunction-api deleted. Receipt `c4934bed71dc8427648e89668f2899eedfc033ab9a0d9371d760a5440333f0a4`. |
| Gate C | Nine files applied once; ledger 26 and capture false. 16/17 postchecks pass, zero-security-findings fails with seven instances. Stop receipt `6070c7fac31931203f85625b80e81b37d4d703c518eac0822741dfcaf708966d`. |
| Fresh production state | Post-D: 20/20 metadata checks and 7/7 aggregate checks pass; 61 counts unchanged except ledger +2, 26 historical hashes preserved, exact target-28 catalogs and complete ACLs/owners, contributors 5/submissions 25/photos 25/auth users 0/public cells 0, capture false, full advisor zero, unchanged prior-attach v3/JWT on. Metadata receipt `d7335af97bb60e6af2e8f5647a7e28754562c8df8c174f2480c1af670a8c6acb`. |
| Gate D | Done under Justin's separate go. Fresh migration test 13/13; dry run only the two reviewed files. One push exits zero, applies exactly both; all hosted postchecks pass. Command receipt `8a48e6be8efcae6b5988ccbcc32197cb03672bd7cbb7ff8f70371be985877f00`. |
| Pages protection | Done: Justin is sole required reviewer; administrator bypass is disabled. Receipt `3b5df1ba9ce8918d53fe35f09df147a4d046c8efbe0b2619b5821018303aca9e`. No Pages deployment. |
| Edge Functions | Held until database security passes and separate go: prior-attach JWT on; gsip-public JWT off; protocol 200, resolution-9 cell 400, MCP four tools then verified. |
| Repository configuration | Held: add SUPABASE_URL and VITE_GSIP_PUBLIC_API, remove old VITE_SUPABASE_URL; Justin adds service-role secret. Names-only reads found the publishable-key variable and old URL variable. |
| Rights/QA workers | Held for separate gates. Prior/QA/export schedules remain quiescent. Photo publication stays held for the screening/data-only policy. |
| HF export | Justin creates global-soil-intelligence/gsip and adds HF_TOKEN/HF_DATASET_REPO; fallback viridis-research/gsip. No dispatch. |
| Tiles | Conditional same-origin Pages approval: palette-version release assets, never Git history, target ≤700 MB, site <1 GB, SoilGrids-only content, actual 206 range response. Build/assembly/publication checks pending; WMS fallback remains. |
| Pages and launch | Separate deployment go, capture closed, prerendered pages/llms.txt checks. DNS, required validate, counsel/legal URLs, CAPTCHA, paid tier and capture opening remain Justin's gates. |

At the historical Gate C stop, the seven findings concerned six objects: INFO no-policy findings on attribution_reviews/grant_withdrawals; WARN anonymous executable definer on capture_is_open; WARN authenticated executable definers on capture_is_open, current_auth_user_exists, finalize_submission and my_submission_accepts_uploads. Gate D now resolves all seven in the complete hosted advisor. Nothing was suppressed.

## Gate D's executed plan

Only these files, in this order:

1. `20261012141828_wp6b_invoker_boundary.sql` — SHA-256 `afe4f698989729bd456fe763582f93042f58bf66a271704cdaa1c556eeb124d6`.
2. `20261012142348_wp6d_private_rights_boundary.sql` — SHA-256 `27c0b1ae001351358b6a56490bc1389d1075dd62cbd6ffc4e6250943fa507260`.

Executed once under Justin's separate Gate D go, with CLI 2.118.0 and exact clean source `19e626c8a95fae32dbd8ad0ff96bc96aba541a0f`:

```sh
GSIP_DEPLOY_SOURCE="/Users/justinhart/.codex/worktrees/gsip-coding-guidance/GSIP 2.0"
GSIP_CLI="/Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/repo/node_modules/.bin/supabase"
"$GSIP_CLI" db push --project-ref toxldjgwkxtneoqsazym --workdir "$GSIP_DEPLOY_SOURCE" --skip-vault
```

Fresh preflight passed before execution. Readback confirms exact ledger 28 preserving all 26 prior full-row hashes, the full hosted advisor zero, strict target-28 catalogs/complete ACLs/owners, unchanged counts except ledger +2, closed capture/auth, private still unexposed, and passing backfill/k-anonymity checks. Anonymous hosted capture RPC returned HTTP 200 and false using the existing public key only in memory. No extra cache SQL, history repair, reset, retry, rollback, Edge deployment, worker/publication dispatch or PR merge occurred. Docker was initially stopped; the existing local app was started and the isolated cached-image migration test then passed 13/13. A diagnostic result parser and one UI locator needed correction/waiting; no production preflight or postcheck mismatch occurred.

## Decisions and assumptions

Keep the approved project and free tier while capture is closed; a paid tier remains a launch gate. HF creation, signing accounts and legal/DNS/operator actions remain pending. CAPTCHA remains deferred: Turnstile/hCaptcha each need an explicit closed-service exception, or an open alternative needs a spec change. Capture and anonymous sign-in stay disabled. Photos require server screening and approved calibration; no automatic blur in version 1. Sync reminders only; nearby suggestions await eligibility data.

Android cloud-backup exclusion and CI versions are tested in #39. iOS WebKit backup exclusion and physical-device proof remain unresolved: options are a separately specified TypeScript storage migration or an explicitly approved native-language exception. Simulator success is not device backup proof. No owner accounts, certificates or keystores were created.

Assumptions: the verified postgres migration owner/default grants, private-schema exclusion and no-overlapping-writer state remain unchanged. Hosted PostgreSQL 17 supports bound SQL-standard bodies; CI uses 16. Fresh source/count equality does not establish historical contributor provenance. Read-only CLI preflight may initialize its temporary database login role. Local stand-ins and HTTP proof do not replace hosted security verification. Local GDAL/Deno/PostgreSQL executables are unavailable; Docker supplies PostgreSQL/PostGIS/pgTAP and CI supplies the other required checks. The original dirty workspace is preserved: 61 entries and digest `9f267c791a56dbfe1cbdb8f104cec8dcaa9bc912d2b8c7cfde757ce5dab63419`.

## Gate D immutable execution evidence

- preflight: [gate-d-authorized-preflight-20261012T1925Z.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-d-authorized-preflight-20261012T1925Z.json>), SHA-256 `5bb6b4f126f895192a04786fd3f065f95fdf90fceeb187d1ce41b22801c58472`.
- command: [gate-d-01-db-push-command-2026-10-12.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-d-01-db-push-command-2026-10-12.json>), SHA-256 `8a48e6be8efcae6b5988ccbcc32197cb03672bd7cbb7ff8f70371be985877f00`.
- metadata: [production-gate-d-post-metadata-verification-20261012T192521Z.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/production-gate-d-post-metadata-verification-20261012T192521Z.json>), SHA-256 `d7335af97bb60e6af2e8f5647a7e28754562c8df8c174f2480c1af670a8c6acb`.
- aggregates: [production-gate-d-post-aggregate-verification-20261012T192521Z.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/production-gate-d-post-aggregate-verification-20261012T192521Z.json>), SHA-256 `bc6bfda41ec93a9a73c97ab85b849039de8a46dcec21863567bc54a5e1c871c5`.
- settings: [gate-d-auth-api-pages-postcheck-verified-20261012T1926Z.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-d-auth-api-pages-postcheck-verified-20261012T1926Z.json>), SHA-256 `596dea745bf567269a4184138fca09e201bec52167cdba1d05bed68c59720bcb`.
- http: [gate-d-hosted-capture-rpc-postcheck-2026-10-12.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-d-hosted-capture-rpc-postcheck-2026-10-12.json>), SHA-256 `f2090a75db4ca1da2da69624985f65e13fbbc34d25c7cfa68b73609cc77d1cc0`.
- ci: [security-fix-all-pr-ci-20261012T192003Z.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/security-fix-all-pr-ci-20261012T192003Z.json>), SHA-256 `4888cbb34f6fa159e9db9f0cb629de51c5fb50446c552729245ea70b063bde4b`.
- migration_test: [gate-d-fresh-migration-test-20261012T192201Z.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-d-fresh-migration-test-20261012T192201Z.json>), SHA-256 `70a4c8158eb548da022b3671d22af2561b62759642b51edc87e5b5fff3c0a9b8`.
- workers_native: [gate-d-worker-native-readiness-20261012T192235Z.json](</Users/justinhart/Desktop/Cowork /GSIP 2.0/outputs/stack-landing-2026-10-11/gate-d-worker-native-readiness-20261012T192235Z.json>), SHA-256 `af09b233e063133fdf677a24096dd2ba86a4f828ca2381c7b4c5ac8b8fef6d4b`.

This is a new report version. The prior REPORT-current.md and all preparation/history receipts remain byte-for-byte preserved. Verification completed on 2026-10-12 at about 15:26 EDT. The snapshot assumes no externally initiated writer or setting change after the recorded readbacks; it is not a persistent lock. All further deployment gates remain held.
