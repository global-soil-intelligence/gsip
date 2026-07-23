GSIP’s website still leads with a soil map and omits the open soil spectral reference library now defined in SPEC §16. This update makes the library the central mission, presents smartphones as the image/context/sample-link capture tool, and connects builders to the existing private local tools and synthetic demo.

## Work package

- WP-SITE-1F; closes #74.
- Branch: `wp-site-1f-spectral-library`, based on `main` at `ccbe716caf8406dda7ffd58ecb9cab62ea0702bf`.
- This implements the existing approved architecture through copy and metadata; it introduces no architecture change.

## Acceptance criteria

- [x] All five pages, search/social descriptions, JSON-LD and `llms.txt` describe the library and its development stage consistently.
- [x] Ordinary phone RGB remains uncalibrated and distinct from measured spectra. Same-sample instrument/lab evidence, verified calibration and independent evaluation precede scientific model claims. Biological relationships require actual assays.
- [x] Capture and hosted library intake remain closed. New releases are structured-only pending deployed/calibrated photo screening. Individual spectra remain private pending fingerprinting/privacy review.
- [x] Source, private local node tools and the synthetic local demo are discoverable; no automatic node registration or measured global coverage is claimed.
- [x] New tests fail on the old content (6 failures before implementation); 601 unit tests pass, including 32 site tests. Typecheck, lint, build and both asset budgets pass.
- [x] Independent review finding resolved; desktop and phone-size visual review shows no horizontal overflow.
- [x] GitHub repository description updated and read back. A 6.1 MB closed Pages review artifact is prepared locally; deployment remains owner-gated.
- [ ] Hosted CI and complete browser verification recorded below when finished.

## Invariants and business guardrails

I1–I15 and B1–B8 remain in force. The visible boundaries reinforce I3/I4/I5 (priors, labels and honest estimates), I7 (private coordinates and metadata), I8 (publication QA), I9/I10 (human authority and evidence), I11 (synthetic is not field evidence), I12 (public-only agents) and I15 (sealed holdouts). Capture unit, consent, throughput, RLS and provenance behavior are unchanged. MIT code, ODbL 1.0 data and CC BY-SA 4.0 photos remain explicit.

No workflow, activation, production database, function, worker, auth, signing, DNS, account, dependency or licence change. The Pages environment remains restricted to approved branches with Justin (`jdhart81`) as the required reviewer and administrator bypass disabled. This PR is not deployment or capture authorization.

## Verification and limits

- Frozen pnpm and uv installs; `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build:pages`, map/site budgets, prior-tile check and closed `build:app` passed locally. Initial homepage assets: 319,432 / 716,800 bytes. Map: 1,879,934 / 5,242,880 bytes.
- Python Ruff and mypy passed. The requested GDAL-required run produced 2,065 passed, 31 skipped and 4 failures because `gdal_translate` is absent. These tile tests need CI; this is not reported as a full local Python pass.
- Local database suites were not run: Docker socket access is unavailable and PostgreSQL/PostGIS/pgTAP are not configured here. Deno is not installed. CI must verify those checks. No native source changed; no native device-build claim is made.
- The first browser attempt could not launch because its pinned browser was absent. The official Chromium download completed; the full suite is being rerun.
- Local combined Pages artifact readback: `capture_live=false`, `library_intake_live=false`; 38 files, 6,079,975 bytes. It uses repository public configuration and is preserved separately from the loopback-only synthetic browser fixture. No artifact was deployed.

## Changes after review

- Changed the optional configured-dataset label in `llms.txt` from “the latest release” to “configured destination; check published status and contents.” A configured URL alone is not evidence of publication. Independent review verified the correction with no open findings.

## Assumptions

- This announces an open-source project in active development, not public collection, app-store availability, a populated worldwide spectral dataset or a scientifically validated model.
- The existing SPEC §16 library mission is authoritative; this package communicates it without proposing new scientific capabilities.
- The planned canonical domain and DNS cutover remain a separate owner action. Social-image URLs use the repository’s approved Pages origin; the announcement links the public GitHub repository.
- A repository variable supplies a destination, not proof of a current release. The copy therefore distinguishes configured destinations from publication evidence.
- Justin must approve the merge and then the Pages environment release. No approval of the current native prototype PR is inferred.

## Agent contribution

Codex authored the changes and regression tests, with independent agent review and an imagegen-generated social preview. Justin Hart is the human of record; no agent certifies DCO, signs off for Justin or approves the PR. No new dependency or licence change.


## Final verification — 2026-10-15

- [x] Full hosted [CI validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38730587784) passed, including Python with GDAL, Deno, the migration test and disposable Supabase database/pgTAP checks that were unavailable locally.
- [x] PR [full-history secret scan](https://github.com/global-soil-intelligence/gsip/actions/runs/38730587416) passed; the branch-push scan also passed. No ignore/rule/workflow changes or new suppression. DCO is skipped under the existing workflow, not reported as passed.
- [x] Local desktop Playwright completed **12/12**, including five-page accessibility, non-JavaScript metadata, hydration and the closed public capture path. This supersedes the in-progress browser note above. Final local lint also passed.
- [x] Source commit: `1a22a8cfa44b2b726140a8901be4efb5fbc99d74`. Prepared Pages archive SHA-256: `14937b8a7e8b2480f035d780581ed5e6d6c83c96d7fa1f3947a68bad820adc8b`; 38 unpacked files / 6,079,975 bytes. Activation readback is exactly `{"capture_live":false,"library_intake_live":false}`.
- [x] LinkedIn project announcement drafted for Justin; nothing posted.

**Approval boundary:** PR remains open and unmerged. The review artifact is local; no new Pages workflow was dispatched or approved. After Justin approves merging this PR, the unchanged main workflow will build a new artifact and wait for his separate `github-pages` environment approval (required reviewer `jdhart81`, admin bypass disabled). Do not approve stale Pages run `38657274196`; it lacks this website update. Production services, DNS, signing, public capture and library uploads are unchanged.


## Changes after review — whole-project builder clarification (2026-10-15)

Justin clarified that the entire project must be open source and available for builders. The website now explicitly says **“The whole stack is open source”** and links to a new README builder map covering apps, map/site, backend, workers, library, modelling, contracts, API/MCP, card generator, tests and workflows. The quickstart now includes cloning, frozen installs, site development and separate database/GDAL/native prerequisites. The library guide explains that “private local node” protects records and credentials; it does not mean closed software. Hosted-service approval imposes no extra software-licence restriction. Public visibility and MIT were verified via GitHub; documentation CC BY 4.0, data ODbL 1.0, photos CC BY-SA 4.0 and third-party notices remain unchanged.

- Public audit found no required private GSIP code, private submodule or private Git dependency in the implemented stack. Unfinished federation, field adapters, validated field models and the public #73 native prototype are described honestly as ongoing work.
- One new regression failed before implementation and now passes: **602 total unit tests / 33 site tests**, plus **12/12 desktop browser tests**, local lint/typecheck, build, prior-tile check and budgets. All 41 README and 4 library-guide local targets exist. Independent review has no open findings.
- A README link-formatting failure at `7944a65` was fixed forward at `d13abfb`; no commit was amended or force-pushed. The final text also avoids implying byte-identical build evidence. No scanner, dependency, licence, activation or workflow changes.
- GitHub description now explicitly advertises full app/backend/pipeline/modelling source for builders to run, fork and extend; public visibility and MIT readback match.
- Latest reviewed head: `d13abfb1bace8ba84e6091ce0033f104b53edf78`. Its [new CI run](https://github.com/global-soil-intelligence/gsip/actions/runs/38819661058) is pending; earlier green evidence belongs to its stated prior head and is not a pass claim for this revision. Both latest full-history secret scans are green. DCO remains skipped under the existing workflow.

Updated local Pages archive SHA-256: `0b869a920d39310a331f1e9517d3d4000af12d0faba40a218371e9e8707b80a6`; 38 unpacked files / 6,080,752 bytes. Both activation flags read false. No merge, Pages dispatch/approval, production change, public capture opening or LinkedIn publication. Previous review receipts remain preserved; this package supersedes them for the new source head.


### Builder clarification — final verification

The latest exact-head [CI validate run](https://github.com/global-soil-intelligence/gsip/actions/runs/38819661058) passed on `d13abfb1bace8ba84e6091ce0033f104b53edf78`, including GDAL scientific tests, Deno, migration tests and disposable database/pgTAP checks. Latest PR [Gitleaks](https://github.com/global-soil-intelligence/gsip/actions/runs/38819661096) and branch-push scan both passed; DCO is skipped under the unchanged workflow. This supersedes the pending-CI note above.

The two documented library demo module commands also passed offline with no GSIP account or credentials in the environment: 24 explicitly synthetic records across 12 fictional pairs, 7 training / 5 development samples and zero overlap. Both demo receipt hashes are `b9af09e17e06ec68894b5f80af34a67c7a3b89f53a637674dd02e1691a4154cf`. This proves the local software entry point, not scientific accuracy (`scientific_validation=false`). An initial sandbox-only uv cache permission failure was resolved by selecting a new owned temporary cache; no source or dependency change was needed.

No open independent-review findings remain. Latest local Pages package has both activation flags false and stays undeployed. PR remains open/unmerged, awaiting Justin's merge approval and a later separate exact-run Pages approval. No production, hosted capture, data/publication policy, licence, workflow or account changes were made.


## Approved merge and replacement Pages gate — 2026-10-15

Justin explicitly approved merging #75 and preparing the new Pages run for his separate approval. Merged as `73088050d6fc68baedf893990ab3fbe76d5e749c` with a Conventional Commit title and Codex co-author trailer, without a human DCO certification or agent approving review. Parent/source readback matches; merge and reviewed head resolve to the identical tree `43c74ca13b889a561e0e23463b9706c064cf48a8`.

- [Main CI](https://github.com/global-soil-intelligence/gsip/actions/runs/38821460088) and [main full-history secret scan](https://github.com/global-soil-intelligence/gsip/actions/runs/38821460068) passed.
- Replacement [Pages run 38821460183](https://github.com/global-soil-intelligence/gsip/actions/runs/38821460183): build passed; deployment is waiting for `github-pages` owner approval. Old pending run `38657274196` was cancelled by the unchanged concurrency policy.
- Downloaded artifact `12013740607`: SHA-256 `2bc0829549d98331c7a8dc5e451b6e5457125fd5863f166e63ce1ea90a4cde33` matches GitHub metadata. Safe archive layout, 38 files / 6,080,760 bytes, five prerendered pages/JSON-LD, library/whole-stack copy, publication limits, `llms.txt`, reviewed share image and absent synthetic fixture verified independently.
- `capture/gsip-activation.json` contains exactly `{"capture_live":false,"library_intake_live":false}`. The eight-byte difference from local preview is the expected `+7308805` CI client-version suffix; dependent asset hashes/precache references are explained by it.
- Pages remains protected by required reviewer `jdhart81`; administrator bypass is disabled. The exact-run approval command/payload is prepared but **not executed**. No Pages deployment, capture/library activation, database, function, worker, auth, DNS or signing change was performed.

The prepared next gate publishes this static-site artifact to `https://global-soil-intelligence.github.io/gsip/` only after Justin’s new Pages go. It introduces no paid service. Undo is an owner-approved revert of this PR with green CI and another separately approved closed Pages release.


## Approved Pages release and live verification — 2026-10-15

Justin gave the exact go for run `38821460183`, keeping capture and library uploads closed. Refreshed preflight matched current main, green CI/secret scan, expected reviewer and disabled administrator bypass, and artifact `12013740607`/SHA-256 `2bc0829549d98331c7a8dc5e451b6e5457125fd5863f166e63ce1ea90a4cde33`. Executed only the previously posted exact-run approval command.

- [Pages run](https://github.com/global-soil-intelligence/gsip/actions/runs/38821460183) completed **success** at merge `73088050d6fc68baedf893990ab3fbe76d5e749c`; deployment `7106555973` reports success.
- **Live site:** https://global-soil-intelligence.github.io/gsip/
- All **38 live files returned HTTP 200 and matched the approved artifact byte-for-byte**, including the five prerendered pages, `llms.txt`, social preview, scripts/styles, map/capture shells and reference-card PDFs. Independent live review also passed.
- Live activation receipt is exactly `{"capture_live":false,"library_intake_live":false}`. Browser verification showed the closed contribution panel, zero file inputs/forms/buttons, working Library navigation and no observed console errors. No sign-in or data submission was performed.
- The required Pages reviewer remains `jdhart81`, with administrator bypass disabled. No database/function/worker/auth/DNS/signing operation or capture/library activation occurred.

**Remaining separate domain action:** `https://globalsoilintelligence.com/` still returns its Coming Soon placeholder. Its DNS cutover was not authorized or performed. Canonical metadata and canonical-domain links remain subject to WP-SITE-1D; use the GitHub Pages URL for this deployed site until that separate gate is completed.
