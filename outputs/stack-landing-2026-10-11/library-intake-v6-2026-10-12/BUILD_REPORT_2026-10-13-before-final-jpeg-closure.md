# GSIP build progress — 2026-10-13

The open soil spectral library is now the organizing mission on main. Phones collect optical observations and context and link physical samples to instrument spectra and laboratory measurements. AI and the map use that evidence downstream. An ordinary RGB camera is not a measured wavelength spectrum or a biological assay.

## Current source and PRs

Nine reviewed PRs (#42–#50) are merged. Current main is `66b78ef8a42ddddba4e28601b3905d55d189dc3a`. Five follow-up PRs are open; none is merge-ready while its secret scan is red. The three photo packages are drafts with ordered bases. The merge register was refreshed from GitHub on 2026-10-13.

| PR | Scope | Current status | Merge commit / current head |
| --- | --- | --- | --- |
| [#42](https://github.com/global-soil-intelligence/gsip/pull/42) | Spec v5: library mission and work order | Merged after exact-head CI and independent review | `ad65c9696953431e74895d7efb43dee9739c5a46` |
| [#43](https://github.com/global-soil-intelligence/gsip/pull/43) | LIB-1: private node store and strict records | Merged after exact-head CI and independent review | `3ca5b69608ff0a4cb64355c305d5f3426bbd132f` |
| [#44](https://github.com/global-soil-intelligence/gsip/pull/44) | LIB-2: phone optical extraction | Merged after exact-head CI and independent review | `93dc1866968d2dba6bc23334bd8d4a448335529e` |
| [#45](https://github.com/global-soil-intelligence/gsip/pull/45) | LIB-3: synthetic paired baseline | Merged after exact-head CI and independent review | `88de34fbe37a9c7f96d70b42e1be3c2dfc5b19b6` |
| [#46](https://github.com/global-soil-intelligence/gsip/pull/46) | Spec v6: hosted private intake | Merged after exact-head CI and independent review | `4d19553e783326cd8d040ab2e07b4a6ca0b65e6c` |
| [#47](https://github.com/global-soil-intelligence/gsip/pull/47) | SEC-1: dependency fixes | Merged after exact-head CI and independent review | `b37cc13c3ca186b14c76416cd3b4ae84746be2d6` |
| [#48](https://github.com/global-soil-intelligence/gsip/pull/48) | LIB-4A: strict intake contract | Merged after exact-head CI and independent review | `28aabaad85de78f04e716315b9a0b8ea36d5e4bd` |
| [#49](https://github.com/global-soil-intelligence/gsip/pull/49) | Spec v7: rights/deletion hooks | Merged after exact-head CI and independent review | `0387405429ac8849829a45ccf45250fa08734dc3` |
| [#50](https://github.com/global-soil-intelligence/gsip/pull/50) | LIB-4B: hosted private intake/RLS | Merged after exact-head CI and independent review | `66b78ef8a42ddddba4e28601b3905d55d189dc3a` |
| [#51](https://github.com/global-soil-intelligence/gsip/pull/51) | LIB-4C: phone offline intake | Validate + Android/iOS green; gitleaks held | `14c4188280025c274ac7c58d1fc40138ee3922bb` |
| [#52](https://github.com/global-soil-intelligence/gsip/pull/52) | Spec v8: photo screening/authorization | Validate green; gitleaks held; stacked on #51 | `f1a644af2a78b1b9865385d603cb77ad156843eb` |
| [#53](https://github.com/global-soil-intelligence/gsip/pull/53) | WP-6fA: private database/privacy authority | Draft; independent review closed; validate + native green; gitleaks held | `af810bf1caa4a38408843897d2c281adc32145d7` |
| [#54](https://github.com/global-soil-intelligence/gsip/pull/54) | WP-6fB: private screening and human review | Draft; baseline validate green; shared JPEG byte-boundary fix/re-review underway; gitleaks held | `e8c452e7734a0c20c3f4cc054e6608767d1a674d` |
| [#55](https://github.com/global-soil-intelligence/gsip/pull/55) | WP-6fC: current photo export authority | Draft; baseline validate green; reviewed C4 source, awaiting shared JPEG guard propagation/regressions; gitleaks held | `e03e20457a11456d1cd3842caa224d049b44265f` |


[Phone validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38342977588), [phone native builds](https://github.com/global-soil-intelligence/gsip/actions/runs/38342977592), [spec validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38342978366). Native inventory readback found unexpired, nonempty Android debug archive (7,220,048 bytes) and iOS simulator archive (3,383,660 bytes), both tied to the exact phone head. This evidence was appended to the existing PR descriptions; their prior text was preserved.

DCO is skipped under the unchanged same-repository policy. No agent approved a GitHub review or certified Justin's DCO. Ordered merge commits use Conventional Commit subjects and the Codex co-author trailer.

## One required owner decision

The fresh full-history gitleaks 8.21.2 `--all --redact` run, repeated after opening #53–#55, exited 1 with exactly one finding:

`bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32`

This is the historical noncredential browser placeholder at a reserved `.test` endpoint. The current fixture is shortened and scans clean. The original four-line ignore file remains unchanged, and no further suppression, scanner rule, workflow, redaction or history rewrite has been applied. All further merges are held. The owner's instruction is explicit: “Any further suppression needs my explicit approval.” The one-line proposal is [here](HARNESS-SYNTHETIC-FINGERPRINT-PROPOSAL.md); the fresh redacted report is [here](stack-gitleaks-after-new-prs-20261013.json). Passing new-file scans does not make the historical stack scan pass.

## Changes after review

- LIB-1: interrupted-write remnants and nonregular lock files were tightened; ambiguous/duplicate JSON and concurrent imports are covered. Fixes propagated forward without rewriting history.
- SEC-1: dependency fixes preserved frozen locks, release-age, open-SDK and secret policies; the dependency alert readback was zero after merge. An initially hidden local permission failure was corrected and the unchanged suite rerun before merge.
- LIB-4B: restricted anonymous function grants to three exact existing OIDs; closed-fixture seeding explicitly closes capture inside a rollback; synthetic geometries are empty. Intake ownership, quotas, immutable content, withdrawal and deletion races have coverage. Actual CI passed 450 database assertions, 26 migration assertions, six genuine two-connection cases and 456 Python tests.
- LIB-4C: isolated the synthetic browser fixture from closed deployable Pages/native assets; shortened its placeholder; corrected the closed home-page browser expectation; moved the server into test sources without changing the production processor-host audit. Main CI and both native builds now pass. Final relocation independent review passed 67 targeted tests, static checks and a negative processor-host witness; no mock-live browser ran locally. The historical false positive introduced in the first harness commit is acknowledged above and still needs explicit approval.
- Spec v8: corrected malformed Markdown RPC-table pipes; clarified exact private RPC authority, owner-only policy/calibration/operator configuration, immutable human withholding, all-frame face/text screening with the reference-card text exception, and fresh exact-byte export authorization. Independent specification review found no blocker.
- Draft WP-6fA: independent adversarial probes reproduced a parent/photo deletion deadlock and late optional-photo insertion recreating private screening state after withdrawal. Both are fixed with contributor-first admission, conservative lock-contention refusal and fresh rights checks; independent closure and actual CI are green; no old RLS/check has been weakened.
- Draft WP-6fB: independent review reproduced marker-only masking of unrelated scene text and a viewer changing the photo after its initial digest check. The optional card exclusion is disabled pending reliable complete-card verification, and the viewed copy is rechecked before durable review/RPC. Nine new cases fail before those fixes and all 56 focused cases pass; those two independent findings are closed. A further review found four JPEG stream/APP0 metadata channels accepted by the old shared guard, plus a fifth decoder case reproduced locally; the complete-stream/fixed-APP0 fix is underway on the owning worker branch.
- Draft WP-6fC: independent review found and regression tests now cover late withdrawals during photo authorization, changed image bytes after authorization, zero-row orphan images, excessively nested RPC JSON, unsafe symlink/hardlink cleanup or writes, and noncanonical files entering an upload. These fixes are local only. Final independent review cleared the four frozen files, passed 125 scoped tests and verified 41 fail-before regressions with real HTTP/upload blocked.

## Local photo-privacy implementation

| Package | Current evidence | Remaining work |
| --- | --- | --- |
| WP-6fA database | Corrected freeze: 143 new privacy / 593 isolated assertions; root and independent peer both 45 populated assertions + six library/31photo races. Independent blockers closed. Actual [CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38349093548): 593 platform assertions, 467 Python with GDAL, 12 browser and static/Deno green. [Native](https://github.com/global-soil-intelligence/gsip/actions/runs/38349093505) green, exact-head unexpired APK7,220,043B / simulator3,383,551B | Full-history scanner exception and predecessor merges |
| WP-6fB screening worker + private reviewer CLI | Current candidate: 56 scoped / 519 Python+four skips, nine fail-before cases and pinned authored-file scan clean; first two independent findings closed. Additional five decoder cases fail before the shared JPEG fix | Complete-stream/fixed-APP0 fix, independent review and updated CI; models/calibration/activation remain separate |
| WP-6fC export authorization | Reviewed exact C4 implementation: 125 independent checks, 41 fail-before cases. Initial combined A/B/C integration: 595 Python+four skips, 181 focused, Ruff/mypy66files and lint green | Propagate shared JPEG boundary fix, narrow export regressions/re-review, updated CI; no publication |


Actual local Supabase-platform evidence is separate: after the 45/45 populated rehearsal, root applied only the original additive WP-6fA migration to the local Docker development database. Its local ledger became 30; capture and private photo publication/deployment/policy gates remain false/unset. The actual local-platform suite ran 593 assertions before and after the local v2 source-only repair and failed three legacy RLS assertions (25/29/33); all 143 new privacy assertions passed. This run is **not** reported as green. The local synthetic seed had previously left capture true; root closed it before application. The direct closed-fixture diagnostic shows submission RLS rejection, followed by missing-source photo/H3 assertions. The isolated normal-fixture suite and actual complete CI passed 593/593. The local v2 repair preserved ledger30, all counts and closed/unset gates; no local history write/reset was used. No production target, reset or repair was used. See the [actual local migration output](wp6fa-actual-local-migration-20261013.log), [actual local test output](wp6fa-actual-local-platform-db-tests-20261013.log) and [root populated rehearsal](wp6fa-root-migration-test-20261013.log).


The detector compatibility smoke is not face-positive testing, calibration, global recall or an approved publication policy. Photo publication must remain closed until deployment and owner-approved calibration. Ordinary phone camera evidence remains separate from measured spectra. No real contributor images or data were used.

## Deployment checklist

| Step | Status and evidence |
| --- | --- |
| Production target | Selected `toxldjgwkxtneoqsazym`; not queried or changed in this build continuation |
| Database | Earlier Gate D receipt recorded ledger 28, zero findings and closed capture; that is historical evidence. No library/photo migration has been applied to production |
| Edge functions | No function deployment, deletion or setting change in this build continuation |
| Variables/secrets | No secret value read, printed, pasted or committed; no new configuration action |
| Rights/QA/export workers | No dispatch, enablement or publication; future worker gate still required |
| Tiles/Hugging Face | No upload or publish; owner-created dataset/token and the approved tile-host conditions remain gates |
| Pages | Fresh API readback: sole required reviewer `jdhart81`, administrator bypass false. No deployment approval was given |
| Capture / anonymous auth | No opening or enabling action; separate owner launch decision remains reserved |

## Decisions and assumptions

- Explicit additional historical fingerprint approval is required before further merges. Recommendation: permit only the single exact noncredential fingerprint after reviewing the proposal; keep every other scan protection unchanged.
- Calibration/model activation and production migration/deployment commands need separate owner gates. Recommend a small staged, independently labelled evaluation before enabling photo publication.
- Actual same-sample instrument/lab acquisition, spatial/device validation and spectral privacy assessment are still needed for useful field AI and an approved open spectral release (LIB-5–7). A synthetic baseline demonstrates software plumbing.
- Accounts/signing, physical iOS backup verification, counsel/legal URLs, CAPTCHA, paid launch tier, owner-created HF dataset and conditional tile publication remain pending. Recommend retaining the existing closed launch posture.
- No new package dependency or project licence change is introduced by the export draft. Existing detectors/weights need their pinned licence and size evidence kept with the worker package.
- Host GDAL, Android SDK and Xcode are unavailable. Native builds are actual GitHub CI evidence; the iOS simulator is not real-device backup evidence. Database draft stand-in results are labelled separately from actual Supabase-platform checks.

Automatic approval review previously rejected local mock-live browser execution because of its capture-enabled test build. It was not run locally or bypassed. The isolated CI browser suite passed; this local restriction remains reported.
