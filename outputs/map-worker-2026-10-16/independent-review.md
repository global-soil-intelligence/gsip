# WP-SITE-1G independent adversarial review

Date: 2026-10-16. Reviewer: separate non-author Codex review agent.

Reviewed worktree: `/Users/justinhart/.codex/worktrees/gsip-spec-followups/GSIP 2.0`, branch `wp-site-1g-map-worker`. Current exact reviewed commit: `d53eda2e835e57b4ee01dc922fb63d5ebdeceae0` ([PR #77](https://github.com/global-soil-intelligence/gsip/pull/77)); tree `d49fa2ef6b31a0042db64d74e78b8a12df5b758b`. Base: `73088050d6fc68baedf893990ab3fbe76d5e749c`. Final binding verified at 2026-10-16 11:34:53 UTC.

Review began against the working diff and completed against the committed seven-file change above. The final worktree is clean; all seven file hashes below exactly match the earlier reviewed source, and a diff against the committed head is empty. The primary checkout was not edited except for the requested evidence reports. No server was started by this reviewer; no commit, push, approval, merge, protection change or deployment was performed by this reviewer.

## Findings

**No unresolved findings at `d53eda2e835e57b4ee01dc922fb63d5ebdeceae0`.** The final source and built artifact were read back after the author repairs. One P2 packaging finding was raised and resolved:

**[P2, resolved] Include the upstream BSD redistribution notice with the new worker.** The initial worker preserved upstream licence-URL headers but the distribution omitted the full copyright, conditions and disclaimer. The author enabled Vite's existing licence emission with `build.license.fileName = 'THIRD_PARTY_LICENSES.md'`. Independent final readback confirms the emitted 32,566-byte notice contains the entire pinned `maplibre-gl@6.11.2/LICENSE.txt` after trimming its outer whitespace, including the MapLibre/Mapbox conditions and disclaimers. The map `dist` and `_site/map` notices are byte-identical, SHA-256 `9aa4807394e33c6a38be8c590001a791203e703d9afefa0e7c2f47b1655a1dce`. The asset also includes notices for the existing bundled dependencies. The browser test requires HTTP 200 and the exact upstream MapLibre text at both layouts. No project licence or dependency changed.

No other actionable correctness, privacy, scope, cross-layout or budget finding was identified. The initially incorrect browser-index assertion was repaired against the pinned library's actual index shape. The final test only observes retained worker tiles; it requires two distinct synthetic H3 cells, exact matching aggregate fields, a real index and no pending data request. Allowing repeated copies of those same cells handles normal world-copy tiling without accepting arbitrary or missing fixture data.

## Review evidence

- Reviewed `AGENTS.md`, `CONTRIBUTING.md`, `GOVERNANCE.md`, the map/invariant/launch portions of the current governing specification, work-package and review guardrails, deployment/activation boundaries, app privacy constraints, legal-pack status and environment example. The fix implements the existing SPEC section 8 map design; no architecture decision, new dependency, service, licence choice or activation change is introduced.
- Reviewed all seven changed source files, including the browser test, final licence-emission config and updated WP acceptance criteria. Worker configuration executes at module evaluation before the sole map construction. Vite's worker query processes the worker entry's sibling module dependencies rather than copying an unresolved entry alone.
- Inspected pinned MapLibre worker factory and Vite output. The emitted worker is a self-contained IIFE. MapLibre selects a module worker for the emitted `.js` URL; the IIFE is compatible. The URL resolves relative to the main script, preserving both `/map/` and `/gsip/map/` layouts, with no cross-origin blob wrapper or CSP change.
- The browser test routes backend responses to fictional public-shaped H3 aggregates, replaces raster replies with an in-memory image, refuses unexpected origins, checks worker HTTP status/MIME/body, captures page/console/resource errors, and inspects the real worker's processed GeoJSON index. It does not replace processing or app state. The root map alias is limited to `site/map`; decoded traversal and symlink escapes fail closed; the temporary synthetic capture mount remains only under `/gsip/capture/`.
- Checked I5 (no changed UI/API claims), I7 (no contributor points/raw records/private metadata), I11 (local labelled synthetic fixtures only), I12 (unchanged public reader), and B1/B5/B8 (no paid dependency/tracking/licence selection). Other invariants and guardrails receive no changed behavior.
- Independently reran `git diff --check`: exit 0. Independently reran `pnpm check:map-budget` after the notice repair: exit 0, `2,421,465 / 5,242,880` bytes. The budget script recursively counts the whole map output, including the worker and notice; its limit is unchanged. The 32,566-byte notice is the entire increase over the initial worker-fix artifact.
- Reinspected `_site/capture/gsip-activation.json`: `{"capture_live":false,"library_intake_live":false}`. The built worker and Pages worker remain byte-identical. Worker SHA-256: `096f3b4deeeaa7ed1372a96978bea3495b78250041df835fada34f12320e11d2`; size: `509,702` bytes. These are observed local artifact bytes, not a deployment receipt.
- Independently exercised the handler's path translation without starting a server. Both notice URLs resolve to `_site/map/THIRD_PARTY_LICENSES.md`; `/capture/index.html`, `/map/../capture/index.html` and its encoded traversal variant resolve to `.not-found`.
- Read the other agents' saved logs rather than representing their runs as this reviewer's runs: old build failed at worker HTTP 404 under both layouts; map unit regression 16/16 passed; handler regression 14/14 passed; final root lint/type checks and all 603 TypeScript tests passed; root Python reported 2,071 passed and 35 skipped (GDAL-dependent coverage unavailable locally). The final focused `browser-final.log` reports 2/2 passed and full `playwright-desktop.log` reports 14/14 passed, including actual worker processing and notice HTTP readback under `/map/` and `/gsip/map/`. Required GitHub exact-head CI remains pending at final review binding.

## Final prepared artifact readback

Independently verified `closed-pages-artifact-receipt.json` and `gsip-site-1g-closed-pages.tar.gz` without extraction or rebuilding. The receipt names the exact reviewed commit. All 40 archive file names, byte counts and SHA-256 hashes match the receipt and the `pages-preview` files; archive members contain no links or path escapes. Total content is 6,623,128 bytes. The archive is 3,878,058 bytes, SHA-256 `d748a201546fff7b8e71a555ee5abb492cdcb2bffb62d8265dd42c9a160e3d01`. The verified preparation-receipt SHA-256 is `ba66bc6786e75421e6d9374e305e3aa4c8f8da56b2d5857129d8c5fef437d0c1`.

Archive activation is exactly `{"capture_live":false,"library_intake_live":false}`. Whole-map content is 2,422,310 / 5,242,880 bytes, including the unchanged 509,702-byte worker and 32,566-byte full notice with the hashes above. This is 845 bytes larger than the synthetic-browser configuration, entirely in the main map script; the preparer records its Pages-variable mapping. This reviewer verified the archive/receipt bytes and bounds, but did not re-fetch repository variables. The preparation log reports the homepage at 320,065 / 716,800 bytes and prior tiles unset with the reviewed ISRIC WMS fallback. No new build or browser run was needed for this final binding.

Machine-readable reviewer receipt: `independent-review-receipt.json`. Status remains prepared locally, not deployed; no GitHub Pages artifact or live destination is inferred from these local bytes.

## Scope and remaining gates

The independent source/artifact review and local prepared-artifact readback are complete with the finding resolved. Required exact-head GitHub CI remains pending at final binding; the owning agent must verify its terminal result. Justin retains merge and Pages approval. A branch build is not a valid bypass of the Pages environment's allowed `main`/`gh-pages` branches. Capture and library intake remain closed. Local checks establish neither current production health nor deployment.

## Snapshot identity

The authoritative final binding is commit `d53eda2e835e57b4ee01dc922fb63d5ebdeceae0` and the seven matching file hashes below. Historical pre-commit tracked diff SHA-256 was `a970ca720563faf2e9bccd0ba9b8339df036d8b3aee42cd617c7e10911719b2d` (`git diff --no-ext-diff --binary`); it excluded the then-untracked browser test, now committed at the hash below. Reviewed file hashes:

| File | SHA-256 |
| --- | --- |
| `apps/map-web/src/App.tsx` | `bab88f58e52a99c7c14d35880cae16ea40dd77d25c8280eb2c35b28116ecb8ae` |
| `apps/map-web/tests/app.test.tsx` | `bde18dba6c15d29cda6b08a115c9f7e7a9f1b195d78aa04db3bfe5fafbb640c2` |
| `apps/map-web/vite.config.ts` | `be6c16f48526588baa2d4c93e6ce45b8ba1cc300afc2dac6de0d490ca6799406` |
| `docs/BUILD_ORDER.md` | `bad2f186a6303e526fb9ef0ed55623c9d86b0563aa409c8eb46cba82f6e048fd` |
| `tests/e2e_server.py` | `328db8ed95d11905ab19aec1a59002504e78850b1e650476c24e77dc5eba066a` |
| `tests/test_e2e_server.py` | `6bd528460634721696922bbd42c1faac3bf4456aced7f6470db42fa58737b799` |
| `tests/e2e/map-worker.spec.ts` | `8decacd28a1f2e5e93f1ac5cc754d95e50d25cd9687545a850fbb940ecde62ee` |
