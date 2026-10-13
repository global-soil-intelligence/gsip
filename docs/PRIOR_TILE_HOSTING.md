# Prior tiles on repository GitHub Pages

Justin approved this destination on 2026-10-11, with the conditions below. This is the
WP-SITE-1E hosting policy and deployment plan; asset assembly is follow-up implementation.
It does not authorize publishing a release, changing repository variables or deploying Pages.
The [privacy notice](legal/PRIVACY.md) remains a draft requiring counsel approval.

## Invariants and destination

- Tiles hold only SoilGrids-derived prior values. They never contain contributor observations,
  private sampled priors, precise positions, photos or private metadata (SPEC I3 and I7).
- The [versioned palette](../packages/schema/src/palettes/soilgrids.json) drives both colours
  and legends. Preserve its version stamp, source attribution and licence metadata; no GSIP
  licence changes are part of this package.
- The host is this repository's GitHub Pages, from the same origin as the map. Do not add a
  tile CDN or a different origin. The canonical domain is used only after Justin's DNS cutover.
- Never commit tiles to git history. Store the built archives as repository release assets
  named by palette version; add them to the Pages artifact at deploy time.
- Target **700 MB or less for all tiles** (700,000,000 bytes). Keep the complete site well
  below the approved 1 GB Pages limit, counting tiles and every other deployed file. If tiles
  exceed the target, propose maximum zoom 7 or fewer properties to Justin first.
- Verify actual Pages byte-range responses return **206 Partial Content** with the expected
  `Content-Range` and bytes before enabling PMTiles. An ordinary 200 response is insufficient.
- ISRIC WMS and its own legend remain the fallback until every check passes. Keep
  `VITE_PRIOR_TILES_BASE` unset until then. Capture stays closed throughout.

## Preparation and evidence

1. Read [SPEC section 8](SPEC.md#8-map-system),
   [the deployment runbook](PHASE1_DEPLOYMENT.md) and
   [the build-order guardrails](BUILD_ORDER.md#2-hard-guardrails-violations--automatic-pr-rejection).
2. Build once with `uv run python -m pipeline.build_prior_tiles --max-zoom 8`. The current
   [builder](../pipeline/build_prior_tiles.py) reads SoilGrids VRTs from ISRIC and writes
   `output/tiles/<palette-version>/`. Record the palette version, selected layers, source
   metadata and actual command outcome. A successful build alone does not prove publication.
3. Measure each archive and their total byte size, and the complete staged site's byte size.
   Retain checksums and a manifest identifying the SoilGrids sources and palette version.
   Check metadata and confirm no contributor database or photo input entered the build.
4. Prepare one release asset named `gsip-prior-tiles-<palette-version>.tar.gz`, containing the
   whole `<palette-version>/` directory, its archives and the manifest. Record its checksum.
   Do not reuse a version name for changed bytes; changed palettes get a new version.

## Gated publication and activation

Every production publication or deployment needs its own exact commands and destination
posted for Justin's explicit **go**. The repository target is
`global-soil-intelligence/gsip`; show the specific release and Pages site for each step.
Approval of the host is not deployment authorization.

1. After the release-publication go, upload the prepared palette-version release asset.
   Retain the release URL and verify its bytes against the prepared checksum. Tiles stay out
   of git. Do not claim release upload proves Pages hosting or range support.
2. Future Pages assembly must fetch that exact release asset, verify its checksum and unpack
   it under `_site/tiles/<palette-version>/`. Reject unexpected files or a palette mismatch.
   Include the total site-size measurement in the deployment evidence. This asset-fetch and
   assembly step is not implemented by this documentation package.
3. After a separate Pages go, deploy the artifact with `VITE_CAPTURE_LIVE=false` and
   `VITE_PRIOR_TILES_BASE` still unset. This first publication exposes the archives while
   retaining the current WMS map, so range support can be measured before activation.
4. Request byte ranges from **each actual Pages archive URL**. Record status 206, a correct
   `Content-Range`, body length and agreement with the corresponding local archive bytes.
   Verify requests are same origin as the map, and verify the palette metadata and all
   archive paths. An absent `Accept-Ranges` header is not proof of failure or success; the
   observed range response and bytes are the evidence.
5. Only after all conditions pass, post the commands for setting `VITE_PRIOR_TILES_BASE` to
   the same-origin `.../tiles` base and for the closed-capture Pages deployment. Wait for
   Justin's go for the corresponding production steps, then run the existing
   `pnpm check:prior-tiles` palette check and verify the deployed map and legends.

If size, range support, provenance or palette checks fail, leave the base unset and keep WMS.
Report the failed condition and propose the smallest corrective work package. Do not silently
change the host, reduce the properties or publish a different artifact.

## Current state

This package records the approved host and its conditions only. No archive build, release
upload, Pages asset assembly, range-response verification, variable update or deployment is
claimed here. The unmodified Pages workflow does not yet retrieve palette-version release
assets; that implementation needs its own work package and tests before this plan can run.
