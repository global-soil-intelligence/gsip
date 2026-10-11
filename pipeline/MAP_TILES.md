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

The map's legends are drawn from the same JSON (`legendGradient`, `legendLabels`), so a legend cannot
disagree with its tiles. Changing a palette means changing that file, rebuilding the archives and
publishing them together.

## Build

Build all three release archives from the official SoilGrids global VRTs with one command:

```sh
uv run python -m pipeline.build_prior_tiles --max-zoom 8 --output output/tiles
```

The build requires GDAL (with `/vsicurl`) and the official `pmtiles` CLI. Publish `soc.pmtiles`,
`ph.pmtiles`, and `clay.pmtiles` together, then set `VITE_PRIOR_TILES_BASE` to their public directory.
Initial browser payload is checked independently from archive size; MapLibre range-requests only the
header, directory, and visible tiles.

## Tests

`tests/test_tiles.py` checks the palette conversion exactly and runs a golden test through real GDAL:
a synthetic Int16 raster with values above 255 and a nodata cell is coloured, and every pixel must
match the palette within 2 levels per channel with transparent nodata; a second test builds an
MBTiles tile and checks it is RGBA. CI installs `gdal-bin` and sets `GSIP_REQUIRE_GDAL=1`, so these
tests cannot silently skip there.
