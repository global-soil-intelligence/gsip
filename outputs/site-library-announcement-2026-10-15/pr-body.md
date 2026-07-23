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
