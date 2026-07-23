# Map worker regression invariants

## Before adding browser and handler regression tests

- Deployable Pages and library intake stay closed; the temporary capture fixture remains loopback-only and isolated from `_site`.
- No live API, external map service, account, credential, real contributor record, dependency, licence, workflow or production setting changes.
- Browser tests use the existing synthetic public H3 aggregate fixture and a synthetic transparent raster only.
- Every observed map worker must be an actual browser Worker served by the built site, with HTTP 200, JavaScript content type and non-HTML content. The real locked MapLibre worker must finish constructing the two-feature contributions index; UI copy alone is insufficient proof.
- Both canonical `/gsip/map/` and `/map/` layouts must work. Root `/capture/`, traversal outside the map subtree and symlink escapes remain refused.
- New tests run against the unchanged App before its worker packaging fix. The expected failure is preserved before implementation.

## Before adding the root map route

- Regression run against the unchanged handler: 13 passed, one failed because `/map/index.html` mapped to `.not-found`.
- Add only `/map/` as an alias of `_site/map`; its containment root is the map subtree itself.
- `/gsip/capture/` alone retains the isolated temporary fixture. No root capture alias, directory listing, escape or deployment behavior is added.

## Before refining worker-state diagnostics

- With the App packaging fix applied, both worker URLs now satisfy the HTTP/MIME/non-HTML assertions. The worker-processing predicate still reports false and needs a count-only diagnosis before readiness can be claimed.
- Preserve the two-cell completion requirement and all network/error assertions. Replace the boolean-only predicate with source/index/pending booleans and a feature count.
- Read the already-built root tile directly: MapLibre's `getTile` may transform cached tile state, so a stored-index read better preserves the no-mutation observer invariant.

## Before correcting the parsed-feature assertion

- Count-only diagnosis proves both real workers have a contributions source, a completed request and an existing processed index; their cached world tiles each report four internal features.
- Raw tile count is not a distinct-observation count: the locked tiler can create rendering copies. Preserve exact two-cell semantics by inspecting processed cached source tags, requiring exactly the two distinct synthetic H3 cells and matching every allowlisted aggregate field to the fixture.
- No source/worker behavior, error check, HTTP/content/path assertion or fixture boundary changes. The observer remains read-only and returns only booleans and a distinct-cell count.

## Before completing cached-source and licence regression coverage

- The library can clear a parent tile's source after drilling into child tiles (verified in the locked `@maplibre/geojson-vt` implementation). Inspect cached source tags across all tiles, still requiring exactly two distinct fixture cells and matching every field; do not invoke tiling or alter worker state.
- Include the separately reviewed upstream-notice requirement: the built notice must return HTTP 200 at each canonical map layout and contain the complete installed MapLibre licence text verbatim.
- No dependency or licence is changed. All earlier error, worker, containment and closed-capture assertions remain.

## Before fixing the test runner's licence-file lookup

- The new notice assertion must read the same installed licence bytes without changing the runner or module configuration.
- Playwright compiles this repository's root test files as CommonJS, so `import.meta.url` is not available. Resolve the fixed installed licence path from the documented repository-root invocation instead.
- No browser behavior, fixture, worker or acceptance assertion is relaxed. Preserve the failed runner log as diagnostic evidence.
