# Independent map worker failure diagnostic

Date: 2026-10-15 America/New_York. Reviewer: Codex independent review agent (`site_library_review`).

**Finding: the deployed map is missing MapLibre's worker module.** This is a first-party build/packaging defect in the already approved artifact. DNS routing and byte-identical HTTPS delivery do not correct it; final rendered-map verification remains incomplete. Browser-extension warnings are unrelated and are not counted as this finding.

## Concrete evidence

Reviewed source: main `73088050d6fc68baedf893990ab3fbe76d5e749c` and its identical reviewed tree `43c74ca13b889a561e0e23463b9706c064cf48a8`. Worktree used: `/Users/justinhart/.codex/worktrees/gsip-spec-followups/GSIP 2.0`; no original dirty checkout was changed.

- `apps/map-web/package.json` pins MapLibre GL **6.11.2**. Its public module entry is `dist/maplibre-gl.mjs`, with separate worker/shared modules in the installed package.
- Installed MapLibre source `apps/map-web/node_modules/maplibre-gl/src/util/web_worker.ts:27–33` derives `maplibre-gl-worker.mjs` beside `import.meta.url`. `workerFactory` uses that default unless `setWorkerUrl` has supplied an explicit URL.
- `apps/map-web/src/App.tsx:70` constructs the map without configuring a worker URL. `apps/map-web/vite.config.ts` has only the relative base and React plugin; it supplies no worker packaging entry.
- The exact approved `map/assets/index-BvpiT6QS.js` retains the dynamic `import.meta.url` sibling-worker construction. The approved archive has **no MapLibre worker file** (and no shared worker module). Bundling the main module did not cause Vite to emit that dynamically named sibling.
- Therefore the deployed module computes `https://globalsoilintelligence.com/map/assets/maplibre-gl-worker.mjs`.

Read-only trusted HTTPS GET evidence:

| URL path | HTTP | Content type |
| --- | --- | --- |
| `/map/` | 200 | `text/html; charset=utf-8` |
| `/map/assets/index-BvpiT6QS.js` | 200 | `application/javascript; charset=utf-8` |
| `/map/assets/maplibre-gl-worker.mjs` | **404** | `text/html; charset=utf-8` |
| `/map/assets/maplibre-gl-shared.mjs` | **404** | `text/html; charset=utf-8` |

The live main map module SHA-256 is `8f3c777c959b2a700d299dcd14c30b7d71c93edcff4d3339c5bb40010f44d7ca`, exactly matching the approved artifact and the earlier local artifact. The HTML/main-module responses have no Content-Security-Policy header; the generic 404 response does. There is no evidence of a newly restrictive application CSP: the necessary JavaScript resource is absent and returns HTML. No CSP weakening is warranted.

The root browser observed the specific `Worker failed to load. Check that the worker URL is correct.` error. That text originates from MapLibre's `src/util/dispatcher.ts:39` worker-error handler and is present in the approved main bundle. The inferred worker URL's confirmed 404 explains this error without attributing unrelated extension messages to GSIP.

## Impact and bounded fix/test proposal

The map shell and independent public-cell fetch can finish, so “No QA-passed public contributions yet” is not proof that the worker started. Worker-backed map source processing is not verified while this required module is absent. The same artifact had this packaging defect before the domain change; it is not caused by incorrect DNS or changed source bytes during cutover.

A separate map-build correction should explicitly bundle/package the MapLibre worker and its dependencies through Vite's supported worker mechanism, then configure `setWorkerUrl` before constructing any map. Merely copying an unbundled worker file can leave its relative shared-module imports missing. Preserve same-origin relative/subpath behavior and current map budgets; add no service, dependency, licence or activation change.

Regression evidence should use the **built** map, rather than only a mocked MapLibre constructor: require the worker response and its imports to be valid JavaScript/HTTP 200, reject worker-loading/page errors, and observe completion of worker-backed source processing. Cover both the repository `/gsip/` path and canonical-root layout. The old artifact must fail this check. Re-run appropriate source tests, build/budgets and independent review; prepare a replacement Pages artifact for its own explicit approval.

This diagnostic made no source, Git/GitHub, DNS, deployment, production, authentication or capture change. It performed source/archive reads and public GET requests only. No extra reproduction probes were needed after the missing URL and exact source/archive path were confirmed. Trusted TLS and matching artifact delivery do not establish that the map is functionally ready.
