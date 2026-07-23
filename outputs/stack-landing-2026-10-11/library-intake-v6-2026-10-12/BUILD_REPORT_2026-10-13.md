# GSIP build progress — 2026-10-13

The open soil spectral library is now the organizing mission on main. Smartphones collect optical observations and context, and link sample declarations to instrument spectra and laboratory measurements. AI and the map use that evidence downstream. An ordinary RGB camera is not a measured wavelength spectrum or a biological assay. Software build completion does not establish real paired field data, a useful trained model, or permission to publish observations.

## Source and pull-request register

Nine independently reviewed PRs (#42–#50) are merged. Current main is `66b78ef8a42ddddba4e28601b3905d55d189dc3a`. Six follow-ups are open in order. No further main merge occurred in this continuation. All six remain held by the full-history secret scan; three photo packages and the new architectural proposal are drafts. Exact heads and ordered bases were read back from GitHub.

| PR | Scope | Current checks / review | Merge commit or current head |
| --- | --- | --- | --- |
| [#42](https://github.com/global-soil-intelligence/gsip/pull/42) | Spec v5: library mission and work order | Merged after exact-head CI and independent review | `ad65c9696953431e74895d7efb43dee9739c5a46` |
| [#43](https://github.com/global-soil-intelligence/gsip/pull/43) | LIB-1: private node store | Merged after exact-head CI and independent review | `3ca5b69608ff0a4cb64355c305d5f3426bbd132f` |
| [#44](https://github.com/global-soil-intelligence/gsip/pull/44) | LIB-2: phone optical extraction | Merged after exact-head CI and independent review | `93dc1866968d2dba6bc23334bd8d4a448335529e` |
| [#45](https://github.com/global-soil-intelligence/gsip/pull/45) | LIB-3: synthetic paired baseline | Merged after exact-head CI and independent review | `88de34fbe37a9c7f96d70b42e1be3c2dfc5b19b6` |
| [#46](https://github.com/global-soil-intelligence/gsip/pull/46) | Spec v6: private hosted intake | Merged after exact-head CI and independent review | `4d19553e783326cd8d040ab2e07b4a6ca0b65e6c` |
| [#47](https://github.com/global-soil-intelligence/gsip/pull/47) | SEC-1: dependency fixes | Merged after exact-head CI and independent review | `b37cc13c3ca186b14c76416cd3b4ae84746be2d6` |
| [#48](https://github.com/global-soil-intelligence/gsip/pull/48) | LIB-4A: intake contract | Merged after exact-head CI and independent review | `28aabaad85de78f04e716315b9a0b8ea36d5e4bd` |
| [#49](https://github.com/global-soil-intelligence/gsip/pull/49) | Spec v7: rights/deletion hooks | Merged after exact-head CI and independent review | `0387405429ac8849829a45ccf45250fa08734dc3` |
| [#50](https://github.com/global-soil-intelligence/gsip/pull/50) | LIB-4B: hosted private intake/RLS | Merged after exact-head CI and independent review | `66b78ef8a42ddddba4e28601b3905d55d189dc3a` |
| [#51](https://github.com/global-soil-intelligence/gsip/pull/51) | LIB-4C: phone offline intake | Validate + Android/iOS green; independent review closed; gitleaks red | `14c4188280025c274ac7c58d1fc40138ee3922bb` |
| [#52](https://github.com/global-soil-intelligence/gsip/pull/52) | Spec v8: photo privacy authority | Validate green; independent review closed; gitleaks red | `f1a644af2a78b1b9865385d603cb77ad156843eb` |
| [#53](https://github.com/global-soil-intelligence/gsip/pull/53) | WP-6fA: private database authority | Draft; validate + Android/iOS green; independent review closed; gitleaks red | `af810bf1caa4a38408843897d2c281adc32145d7` |
| [#54](https://github.com/global-soil-intelligence/gsip/pull/54) | WP-6fB: screening / private review / shared JPEG guard | Draft; new exact-head validate green; final independent review closed; gitleaks red | `b0f8e0f808629754bc6f4213f9c94e3149adfe55` |
| [#55](https://github.com/global-soil-intelligence/gsip/pull/55) | WP-6fC: fresh photo export authority | Draft; new exact-head validate green; final independent integration closed; gitleaks red | `fd5c44bd9e33ca741fc4ed59b4a362e960f3e30a` |
| [#56](https://github.com/global-soil-intelligence/gsip/pull/56) | Spec v9: bounded private node exchange | Draft proposal; eight independent static checks and commit/body binding passed; exact-head validate green; gitleaks red | `db3a37062008c291b6e8aa491b99eab3e752fe16` |

[Phone validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38342977588), [phone native builds](https://github.com/global-soil-intelligence/gsip/actions/runs/38342977592), [spec v8 validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38342978366), [database/privacy validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38349093548), [database/privacy native](https://github.com/global-soil-intelligence/gsip/actions/runs/38349093505), [final worker validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38354233257), [final export validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38354450304), [spec v9 validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38355333489).

Phone native artifacts are tied to exact head14c: APK7,220,048B and simulator3,383,660B. Privacy/database native artifacts are tied to exact headaf810: APK7,220,043B and simulator3,383,551B. Readbacks found them nonempty/unexpired. Simulator builds do not establish real-device backup exclusion. B/C change Python/shared QA, not app sources, and no new native-build claim is made for those heads.

DCO is skipped under the unchanged same-repository policy. No agent approved a GitHub review or certified Justin's DCO. Authored fixes and forward merge commits use Conventional Commit subjects and the Codex co-author trailer. Existing PR bodies were preserved and final fixes/evidence appended under Changes after review.

## Exact remaining scan gate

The latest whole-stack pinned gitleaks 8.21.2 `git . --log-opts=--all --redact` scan, including the new B/C/spec9 commits, exited1 with exactly one finding:

`bb9bd8a583231ff63ec14a7622532ddb869d7cde:scripts/e2e_server.py:generic-api-key:32`

This is the historical noncredential browser placeholder at a reserved `.test` endpoint, introduced in the first unmerged harness commit. Its current source was cleaned forward; the avoidable earlier scan failure is acknowledged. The original four-line ignore file still has only the three owner-approved fingerprints. No further suppression, detection-rule/workflow/redaction change or history rewrite was applied. Passing authored-file scans is not a passing whole-history scan.

Justin's explicit rule is: “Any further suppression needs my explicit approval.” The single exact-fingerprint permission question is still unanswered. General authority to keep building and merge does not override that narrower requirement. All further merges are held. Recommendation: permit only the exact historical noncredential fingerprint in the [proposal](HARNESS-SYNTHETIC-FINGERPRINT-PROPOSAL.md), preserve every other scan protection, propagate forward, then rerun the full-history scan and exact-head CI before ordered merges. [Fresh redacted scan report](stack-gitleaks-final-20261013.json). Latest PR54/55/56 CI scanner summary logs independently report one finding and exit1 ([readback](final-ci-secret-scan-readback.json)); their summary logs do not expose the fingerprint. The exact identity above is established by the local whole-stack report.

After that gate clears, merge order remains #51 → #52 → #53 → #54 → #55 → #56, with successor retargeting to main and merge-forward conflict resolution. Draft/spec approval and exact-head required checks must also be complete; no bypass, force-push, rebase or GitHub approving review is permitted.

## Changes after review and why

- LIB-1: interrupted-write remnants and nonregular lock files were tightened; ambiguous/duplicate JSON and concurrent imports are covered. Fixes propagated without rewriting history.
- SEC-1: dependency fixes preserved frozen locks, release-age, open-SDK and secret policies. Dependency alert readback was zero after merge. An initially hidden local permission failure was corrected and the unchanged suite rerun before merge.
- LIB-4B: anonymous grants are restricted to three exact existing OIDs; closed-fixture seeding closes capture inside rollback; synthetic geometries are empty. Ownership, quotas, immutable content and withdrawal/deletion races have coverage. Its actual CI passed450 database assertions,26 migration assertions,six real two-connection cases and456 Python tests.
- LIB-4C: separated synthetic browser fixtures from closed deployable Pages/native assets, cleaned the placeholder, corrected the closed home-page browser expectation and relocated the test server without changing the processor-host audit. Exact-head validate/native builds pass. Independent final relocation review passed67 targeted tests/static and a negative processor-host witness; no mock-live browser ran locally. The historical false positive remains explicitly held above.
- Spec v8: fixed malformed Markdown RPC pipes; clarified owner-only calibration/policy/operator settings, immutable human withholding, all-frame screening with an optional verified-card text exception, and fresh exact-byte export authority. Independent review closed.
- WP-6fA: fixed an independently reproduced parent/photo deletion deadlock and late optional-photo insertion after withdrawal. Contributor-first admission, conservative contention refusal and fresh rights checks close the findings. READ COMMITTED admission/RPC guards reject stale isolation. No existing RLS or check was weakened.
- WP-6fB: disabled the unsafe marker-only card exclusion; every pixel enters face/text views. A human viewing copy is rechecked after decision and before intent/RPC. The shared JPEG guard now traverses every scan through exact terminal EOI and validates canonical JFIF, control/table fields, table-definition generations and structural scan history. Independent decoder counterexamples required tighter refusal of trailers, concatenated streams, late metadata, ignored padding, unused/overwritten definitions and invalid/empty duplicate scans. Tests fail on earlier guards and final review closes all blocking findings in this bounded scope. Sanitizer-produced bytes and unreadable-image behavior are preserved.
- WP-6fC: retains the reviewed fresh rights/exact-byte authorization, orphan/cached-image pruning, bounded RPC JSON and no-follow private artifact handling. The owning B fix was merged forward;17 new exact-clearance hidden-payload regressions refuse without an artifact. Four original cases fail against the original helper;13 expanded cases fail against the intermediate helper. All49 original export tests remain byte-identical. Final independent review binds the narrow integration to commitfd5.
- Spec v9: independent review found ambiguous retirement/sequence-gap handling and unbounded aggregate storage despite per-human quotas. The corrected two-document proposal defines stream identity/immutable slots, contiguous heads, immediate refusal independent of head advancement, aggregate bounds and pre-reserved scope fences on saturation. Real digest retention, private consent/peer authority and cross-contributor policy remain held. No LIB-5 runtime implementation was added. Its exact-head CI passes the inherited runtime: 779 Python with GDAL, 424 TS, 593 database, 45 populated, 6+31 races and 12 browser checks. PR-body clarification distinguishes ordinary sample refusal from whole-scope saturation fencing and calls hosted intake code rather than deployed intake.

## Photo package evidence and limits

| Package | Actual final evidence | Remaining gates |
| --- | --- | --- |
| WP-6fA |143 new /593 isolated database assertions; root/peer45 populated assertions +6library/31photo races; independent closure. Exact-head CI467Python withGDAL,593platform,12browser/static/Deno and native green | Scan exception, ordered source merges, separately approved migration/runtime/operator/policy gates |
| WP-6fB | Root682Python+4hostGDALskips; peer234scoped,6,880marker assertions,47decoder probes (46refusals+1control). Root seven-frame synthetic CPU smoke, timeout cleanup0children. Exact-head CI686Python withGDAL,424TS,593platform,45populated,6+31races,12browser/static/Deno green | Scan/merge; exact deployment-runtime model/artifact/licence audit, permissioned calibration, policy/operators; no publication |
| WP-6fC | Root775Python+4hostGDALskips; peer142/142including49legacy+17new refusal cases. Ruff/mypy66files and authored-file scan0. Exact-head CI779Python withGDAL,424TS,593platform,45populated,6+31races,12browser/static/Deno green | Scan/merge and all separate policy/calibration/deployment/publication gates |

Immutable final review SHA256s: [B](wp6fb-final-independent-review.json) `9dafbdb2d0bab14972447c0fafa339429a8b852026c19109773a98a17c5bafd0`; [C](wp6fc-final-independent-review.json) `ef54ee792cea5508c0d9385b67ec84343283bb36241a6a1ad700813d00d652d8`; [spec9](lib5-spec-v9-final-independent-review.json) `66efbe14646a689c62badc6f44970fe68268799bf89dc91e4debde4afc2219dc`. [B closure](wp6fb-final-closure.json), [C root validation](wp6fc-final-root-validation.json), [B actual CI counts](pr54-actual-final-ci-counts.json), [C actual CI counts](pr55-actual-final-ci-counts.json), and source manifests/logs preserve exact bytes and outcomes.

The JPEG guard validates structural markers/fields/table references/scan history. It does not prove every Huffman entropy bit is consumed, detect all codec or pixel steganography, or attest a trusted producer. Trusted QA reencoding remains required. Synthetic compatibility is not face-positive testing, detector recall, real-data calibration or an approved publication policy. The frame-wide detector policy is more conservative than the optional card exception.

Actual local platform results are separate: root applied the additive A migration to the local Docker development database after the populated rehearsal, and later only the source-only v2 repair. Ledger30 and counts/gates were preserved. Capture and photo publication/deployment/policy stay false/unset. The actual local platform suite ran593 assertions and failed three legacy RLS assertions25/29/33; all143 new privacy assertions passed. This run is not green. The previously true synthetic seed was closed before application; direct diagnostics show closed-capture submission42501 followed by missing-source photo/H3 assertions. The isolated normal-fixture suite and complete actual CI passed593/593. No production migration, local history write or reset was used for this local repair. [Local migration output](wp6fa-actual-local-migration-20261013.log), [local platform output](wp6fa-actual-local-platform-db-tests-20261013.log), [populated rehearsal](wp6fa-root-migration-test-20261013.log).

## Next node-exchange proposal

Draft #56 proposes LIB-5A pure typed exchange contracts/conformance, then LIB-5B synthetic private ledger/outbox/rights simulation. Owner architectural approval precedes either implementation. [Exact-head spec9 CI evidence](pr56-actual-final-ci-counts.json) passes the inherited runtime and does not test a LIB-5 implementation. [Final commit/body binding](lib5-spec-v9-pr56-final-binding-review.json) SHA256 `48a9e2fa807f92b187eaea26a6a9154bfdbe3b650851b61221f25e63add3c07e` closes the description finding. Source-sharing purpose/consent/retention, peer admission, revocable credential/cleanup mechanism, real digest/lineage retention and cross-contributor policy remain explicit LIB-5C holds. Its finite quotas are engineering proposals, not measured operational capacity. Scientific arrays and digests remain private and potentially identifying; aliases do not establish physical same-material pairing or anonymity. No real sender, listener, peer enrollment, data export or automatic training was built.

## Deployment checklist

| Step | Status / evidence |
| --- | --- |
| Target | `toxldjgwkxtneoqsazym`,gsip,us-east-1 selected historically; production not queried or changed in this build continuation |
| Database | Earlier GateD receipt recorded ledger28,zero findings,closed capture. Historical evidence only; no library/photo migration applied to production |
| Edge Functions | No deployment,deletion,JWT or production setting change in this continuation |
| Variables/secrets | No secret value read/printed/pasted/committed; no new configuration action |
| Rights/QA/export workers | No dispatch,enablement,Hub upload or photo publication; separate worker gates remain |
| Tiles/HF | No upload/publish. Owner must create dataset/token; tile approval conditions remain release assets/no git,≤700MBtarget,206range,SoilGrids-only and notice update |
| Pages | API readback earlier this continuation: sole reviewerjdhart81,administrator bypassfalse. No deployment approval or publication |
| Capture/auth | No opening of capture,sign-up or anonymous auth; separate launch decision reserved |

## Open decisions, options and assumptions

- Scan: approve only the exact historical noncredential fingerprint (recommended), or keep the stack held. Explicit suppression approval is pending; no duplicate request was sent.
- Spec9: approve the bounded synthetic LIB-5A/5B proposal after review (recommended), or revise it. Real LIB-5C needs separate owner privacy/legal/purpose/consent/retention and authority choices before an architectural amendment or implementation; no default sharing assumed.
- Capture launch: SPEC §11 separately requires a 50-photo field pilot to calibrate soil/photo QA thresholds, prior PMTiles publication, production paid tier and green workers, counsel approval, and a canonical domain serving the crawlable site. No new field-pilot or DNS/canonical/sitemap verification is claimed. Recommendation: complete and document those gates before any request to open capture.
- Photo calibration: this separate privacy-detector gate requires staged permissioned, independently labelled face/script/plate evaluation before publication. Model and exact deployment-runtime artifact/licence audit and operator provisioning are not completed by the software tests. Add a dedicated plate model only if evidence shows a material gap and a properly licensed model exists. No automatic blur in v1.
- Field library/science: same-sample original instrument/lab data, source verification, device/spatial validation and spectral privacy review remain LIB-6/7 requirements. Keep phone RGB and measured spectra separate; synthetic AI tests establish plumbing, not field usefulness or soil-biome understanding.
- Accounts/signing and real-device iOS backup exclusion, counsel/legal URLs, CAPTCHA, paid launch tier, owner-created HF dataset and conditional tile publication remain gates. Recommendation: retain the closed launch posture and owner-controlled accounts; no new paid/closed service or licence change.
- Existing project licences remain MIT/ODbL1.0/CCBY-SA4.0. No new dependency in C/spec9; B's pinned detector/runtime licences and sizes remain recorded with that package, including OpenCV bundled licence obligations rather than calling the whole bundle MIT.
- Host GDAL,Deno,AndroidSDK and Xcode are absent; four host-GDAL skips are disclosed. CI supplies actual GDAL/Deno/native evidence. Local Docker PostgreSQL/PostGIS/pgTAP is available; local and isolated fixture outcomes are explicitly distinguished.

Automatic approval review previously rejected local mock-live browser execution because of its capture-enabled test build. It was not run locally or bypassed. Actual isolated CI browser tests passed; this local limitation remains disclosed.
