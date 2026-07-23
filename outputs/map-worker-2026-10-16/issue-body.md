The approved map build omits MapLibre 6.11.2’s worker module. Its computed worker URL returns 404 HTML, so the map shell can appear while worker-backed processing fails.

WP-SITE-1G repairs the existing SPEC section 8 architecture by bundling the worker and its shared imports through Vite and configuring the emitted URL before map construction. It adds a built-browser regression for canonical-root and repository-subpath layouts with synthetic public-cell fixtures and no live service.

Invariants: preserve I1/I3/I5/I7/I11/I12 and B1/B5/B8, all current map behavior and the whole-map 5 MiB budget. No new dependency, licence, CSP relaxation, public records, activation or production change. Capture and library intake remain closed. Justin retains merge and Pages deployment approval.

Acceptance: regression fails on the old build; real worker loads and processes synthetic GeoJSON in both layouts; loopback fixture/traversal boundaries stay intact; required CI and independent review pass; a closed Pages artifact and next-run plan are prepared.
