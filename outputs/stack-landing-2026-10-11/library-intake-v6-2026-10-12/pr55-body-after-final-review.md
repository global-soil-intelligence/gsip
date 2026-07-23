Keep structured-data releases useful while requiring current private privacy authority for every photo. Old/missing/closed/unapproved policy loads no media and emits empty photo lists. Exact sanitized bytes are staged, hashed and freshly authorized before artifact promotion and any separately authorized upload.

## Work package and invariants

WP-6fC, stacked on WP-6fB. Preserve I1–I15 and B1–B8, private metadata/coordinates, consent/withdrawal, k-anonymity, provenance/holdout and all launch gates. Withheld/changed photos are excluded individually; eligible structured observations survive. Neither a prior QA pass, cached output nor detector outcome opens photo publication or supplies scientific training eligibility.

Strict bounded service RPCs validate capabilities, immutable receipts and ordered exact binding authorizations. Keep already-sanitized canonical JPEG bytes unchanged. Private bindings never enter public manifests/reports. Refresh withdrawal eligibility and recompute aggregation after authorization. Reject linked/special/noncanonical cached artifacts before reads/writes/cleanup and before upload; closed policy removes stale/orphan media.

## Acceptance and verification

- [x] Legacy/missing/unsupported/closed policy causes zero image-loader calls and empty public photo arrays.
- [x] Current exact content/policy/digest authority, exact staged-byte preservation, final fresh per-photo authorization and conservative stale/changed refusal.
- [x] Withdrawal recheck/rebuild/k-anonymity; unaffected photos and structured rows survive a single photo refusal.
- [x] Private mode0700 pre-promotion stage, same-filesystem guard, no symlink/hardlink/special traversal and exact upload inventory.
- [x] Final independent frozen-file review: no remaining code blocker;125 scoped tests and41 fail-before cases with real HTTP/upload forcibly blocked. All49 existing export tests retained with explicit synthetic authority.
- [ ] Exact-head combined CI appended when available.
- [ ] Full-history secrets check held on the inherited synthetic browser-harness fingerprint pending separate explicit owner exception; no new suppression.

Full local Python on the final implementation passed539 tests/four GDAL skips and strict mypy55 files/Ruff; that run preceded two test-only refinements. The final independent four-file review passed125 tests with a safe transport barrier and pinned final-authored-file gitleaks8.21.2 is clean. Combined A/B/C root verification passed595 Python tests/four GDAL skips,181 focused tests, full Ruff/mypy66files and JavaScript/Markdown lint. A first focused run hit the unwritable default dataset cache; the prescribed temporary-cache rerun passed. A newly reproduced shared JPEG parser defect remains held on predecessor WP-6fB; its forward fix and explicit export regression closure are required before ready/merge. No real Storage, Hub, contributor image/data or production request was used.

## Changes after review

Independent review reproduced and regression tests now cover late withdrawal during photo authorization, changed bytes during authorization, empty cached orphan uploads, overly nested RPC JSON, symlink/hardlink traversal or writes, and unknown thumbnails/private files entering an upload. Refuse unsafe inventory before touching files, normalize decoder failure to photo-only fallback, recheck actual bytes/rights after RPC and require the exact canonical final upload inventory. Existing privacy, licence, processor and full-history scanner checks remain unchanged.

## Assumptions and remaining gates

- SQL transactions cannot atomically commit later filesystem/Hub operations. No immediate distributed withdrawal/retraction promise is made; takedown/purge duties remain.
- Private temporary staging and output must share a filesystem for atomic promotion. Cross-filesystem staging refuses before replacing an existing artifact; there is no unsafe copy fallback.
- Sanitized JPEGs are already canonical and metadata-free. Re-encoding would change the reviewed digest, so this export validates and preserves exact bytes.
- Current clearances require owner-approved policy/calibration and all deployed WP-6f components. This PR does not approve model quality, field science, release eligibility, dispatch or upload.
- Bounded rights retries refuse continuously changing source eligibility. Closed/failed per-photo authority does not bypass other structured-data rights/k-anonymity checks.
- No new dependency/service or licence change. Host GDAL is absent; required CI supplies golden-tile evidence. All fixtures are synthetic; recursive public-field refusal includes private policy/operator/card/content bindings.

Codex authored implementation/fixes for Justin Hart, human of record. No agent approves a GitHub review, certifies the DCO, bypasses protections, deploys or publishes.

## Changes after review — shared guard propagation and export regressions (2026-10-13)

Merged the owning worker fix forward with merge `d495d7fed932cc25dcc92fa4fa0b7628b730b26f`, then added 17 synthetic export regressions in `fd5c44bd9e33ca741fc4ed59b4a362e960f3e30a`. Each supplies an exact photo clearance digest yet requires systemic refusal of hidden JPEG payloads with no output artifact. The four original cases failed against the original helper; 13 expanded cases failed against the intermediate helper. All 17 pass with the independently reviewed final shared guard. Fix-forward history and prior descriptions are retained.

The exporter and RPC helper are unchanged, as are all 49 original export tests. Fresh exact-byte authorization, current withdrawal/holdout checks, canonical cached/staged inventory, no-follow private files, structured-only compatibility and generic errors remain enforced. No new dependency, licence change or check weakening was introduced.

Actual verification:

- Root combined Python: 775 passed, four host-GDAL skips; Ruff, formatting, mypy (66 source files), diff whitespace and four-authored-file pinned gitleaks checks passed.
- Independent final narrow integration: 142/142 tests, including all 49 legacy export tests and the 17 new refusals, with real HTTP/upload blocked. Final commit binding matches all four C files and inherited QA bytes. Receipt SHA256 `ef54ee792cea5508c0d9385b67ec84343283bb36241a6a1ad700813d00d652d8`. The broader shared-guard review is bound separately in PR #54.
- Exact-head [CI validate](https://github.com/global-soil-intelligence/gsip/actions/runs/38354450304) passed: 779 Python with GDAL, 424 TypeScript, 593 database assertions, 45 populated migration assertions, six library and 31 photo two-connection cases, 12 browser tests and configured static/Deno/build checks.
- Full-history gitleaks 8.21.2 remains red on the one separately reported historical noncredential fixture fingerprint; no additional ignore or scanner/workflow change has been applied.

Assumptions/limits: exact-byte structural validation is not complete photo privacy assurance, entropy-bit consumption proof or distributed atomic erasure. Model calibration, private actor/policy provisioning, source merges and production/publication approval remain separate gates. No real contributor data, Hub upload, deployment, production migration, capture opening or worker dispatch was used for this work.
