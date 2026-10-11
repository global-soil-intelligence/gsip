# Soil prior map tiles

The map supports native PMTiles archives through `VITE_PRIOR_TILES_BASE` and caps native source zoom
at 8. Deeper browser zooms overzoom those tiles. Until release archives are attached, it falls back to
ISRIC's official WMS visualisation service and shows ISRIC's own legend graphic; the browser never
uses the beta point-query REST API.

## One palette for tiles and legends

`packages/schema/src/palettes/soilgrids.json` is versioned and holds, for each layer, colour stops in
canonical GSIP units and the SoilGrids scale factor (SOC is stored in dg/kg, pH ×10, clay in g/kg).
The tile builder converts the stops to raw SoilGrids units and colours each raster with
`gdaldem color-relief -alpha` through a VRT, so the global build needs no huge intermediate file:

- values between stops are interpolated linearly, values beyond the ends are clamped to the end
  colours;
- nodata is fully transparent, never opaque black;
- tiles are RGBA PNG.

The map's legends are drawn from the same JSON (`legendGradient`, `legendLabels`). Three things keep
a legend from ever disagreeing with its tiles:

1. the builder stamps each archive's metadata with `gsip_palette_version`, `gsip_layer`, a name,
   description and ISRIC attribution (CC BY 4.0), and writes it to `<output>/<palette version>/`;
2. the map requests `${VITE_PRIOR_TILES_BASE}/<palette version>/<layer>.pmtiles`, the version it
   draws its legends from;
3. the Pages deploy runs `pnpm check:prior-tiles`, which reads each archive's metadata and fails if
   any archive is missing, unstamped, holds another layer or carries another palette version.

Changing a palette therefore means changing that file (and its `version`), rebuilding, and publishing
the new version directory before the map that uses it can deploy.

## Build

Build all three release archives from the official SoilGrids global VRTs with one command:

```sh
uv run python -m pipeline.build_prior_tiles --max-zoom 8 --output output/tiles
```

The build requires GDAL (with `/vsicurl`) and the official `pmtiles` CLI. It writes
`output/tiles/<palette version>/{soc,ph,clay}.pmtiles`. Publish that version directory under one public
base, then set `VITE_PRIOR_TILES_BASE` to the base (without the version). Older version directories
can stay published; nothing requests them.
Initial browser payload is checked independently from archive size; MapLibre range-requests only the
header, directory, and visible tiles.

## Tests

`tests/test_tiles.py` checks the palette conversion exactly and runs a golden test through real GDAL:
a synthetic Int16 raster with values above 255 and a nodata cell is coloured, and every pixel must
match the palette within 2 levels per channel with transparent nodata; a second test builds an
MBTiles tile, checks it is RGBA and stamped. CI installs `gdal-bin` and sets `GSIP_REQUIRE_GDAL=1`, so
these tests cannot silently skip there. `apps/map-web/tests/check-prior-tiles.test.ts` covers the
deploy gate, including a run of the command against a local server.
