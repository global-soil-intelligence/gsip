# GSIP library-first build — 2026-10-12

The specification and build order now organize GSIP around an open soil spectral reference library. Smartphones capture optical evidence/context and connect physical samples to instruments and laboratories; AI and the map are downstream uses. RGB camera summaries remain distinct from measured wavelength spectra.

Four separate stacked PRs are open, with successful full CI and secret scans on every final head:

| Order | PR | Delivered | CI |
| --- | --- | --- | --- |
| 1 | [#42](https://github.com/global-soil-intelligence/gsip/pull/42) | v5 mission, L1–L7, LIB-1–7 sequence, corrected merged-v4 policy status | [passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38332567235) |
| 2 | [#43](https://github.com/global-soil-intelligence/gsip/pull/43) | Strict sample/RGB/spectral/lab contract; private immutable local node; imports, schema, inspection and withdrawal | [passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38332920944) |
| 3 | [#44](https://github.com/global-soil-intelligence/gsip/pull/44) | Staged phone-photo optical extraction, existing sanitation and card masking, explicit uncalibrated RGB | [passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38332919362) |
| 4 | [#45](https://github.com/global-soil-intelligence/gsip/pull/45) | Sample-wide eligible pairing, deterministic private reconstruction demo and reproducibility receipt | [passed](https://github.com/global-soil-intelligence/gsip/actions/runs/38332921724) |

DCO is skipped by the unchanged same-repository workflow policy. Agents did not certify Justin's DCO or approve PRs. Independent adversarial review remains outstanding; no PR has been merged. Verified main remains `665506fd7a2e4d972bb9fe03c4faf0f174c4675b`.

## Evidence

Tip CI: 386 Python tests including required GDAL; 307 web unit tests; 12 desktop-Chrome browser tests; 299 pgTAP assertions in 8 files; Deno and populated-database migration rehearsal passed. Local frozen pnpm/uv installs, lint/language/Prettier, TypeScript, Ruff and strict mypy passed. Local Python: 382 pass, 4 GDAL skips. Native SDK/Xcode checks were not run for these Python/docs changes. No SQL migration or native change is introduced.

Map initial bundle: 1,654,727 / 5,242,880 bytes. Homepage assets: 313,574 / 716,800 bytes. Web and capture app web-asset builds passed. Full-history gitleaks 8.21.2, `--all --redact`: 110 commits scanned, no leaks; only the three previously approved fingerprints remain ignored.

Runnable private demo: 24 synthetic records, 12 fictional paired samples, 7 train and 5 development, zero sample overlap. Camera images go through the actual extractor. Fictional reference values verify software plumbing; scientific validation is false. Nothing is uploaded or published. Input digests and source hashes are in `local-build-receipt.json`; PR heads/check run IDs are in `final-pr-checks.json`.

Automatic approval review rejected local Playwright execution because its existing test configuration builds capture-enabled Pages. It was not run locally or bypassed. The unchanged CI browser job passed. This is a local verification limitation, not evidence of a production capture change.

## Changes after review

Local implementation review found an interrupted-write edge case: private `.pending-*` remnants could survive withdrawal. A test failed before the fix, which removes them under the exclusive store lock before operations. Lock files must be regular private files. Fixed on LIB-1, merged forward without force/rewrite, and recorded in #43–45 descriptions. Initial ambiguous duplicate JSON and concurrent-import behaviors also have regression coverage. A first CI dependency install hit a transient PyPI broken pipe; it was retried without changing dependencies or checks.

## Deployment checklist

No production commands, migrations, function deployments, worker dispatches, schedule changes, repository configuration changes, Pages approvals, merges or capture opening were performed. This request authorizes specification/build preparation. Existing exact-command production gates, capture/anonymous-sign-in holds and photo-publication calibration gate remain binding. Production was not queried this turn; no fresh production health assertion is made.

## Remaining product work and inputs

- LIB-4: phone offline sample identity/context plus authenticated hosted intake, verified grants, server-derived provenance, immutable pairing, private RLS and deletion/holdout enforcement. The current CLI does not synchronize with the hosted service.
- LIB-5: node exchange/deduplication and revocation protocol. A private record directory is not federation or canonical membership.
- LIB-6: acquire actual same-sample camera/instrument/lab evidence, documented calibration and biological assay methods; expert review, independent spatial/device evaluation and calibrated uncertainty. The demo is not a useful trained field model. Recommend a small paired pilot with an existing partner instrument before selecting or purchasing new hardware.
- LIB-7: spectral fingerprinting/linkage privacy review, consent/licensing checks, approved releases and map/model integration. No individual spectral release is allowed by these tools.
- Existing launch dependencies remain: photo-screening implementation/calibration, legal approval, tiles, accounts/signing/iOS backup evidence and separately authorized production worker/publication gates. Four default-branch dependency alerts remain outside this library work.

## Assumptions

Smartphones provide camera observations, context and sample linkage; ordinary RGB does not provide a measured wavelength spectrum. Fractional reflectance/nanometres and canonical label units are the first exchange scope; other units need reviewed adapters. The local node is macOS/Linux, private single-host storage; file permissions do not encrypt it. Operators manage encrypted storage and destroy derived artifacts after withdrawal. Local QA/consent/pairing flags are declarations, not proof, so real field training remains blocked pending hosted/screening verification. No new dependency, paid service, closed SDK, licence change or scientific accuracy claim was introduced.
