# Soil prior map tiles

The map supports native PMTiles archives through `VITE_PRIOR_TILES_BASE` and caps native source zoom
at 8. Deeper browser zooms overzoom those tiles. Until release archives are attached, it falls back to
ISRIC's official WMS visualisation service; the browser never uses the beta point-query REST API.

Build all three release archives from the official SoilGrids global VRTs with one command:

```sh
uv run python -m pipeline.build_prior_tiles --max-zoom 8 --output output/tiles
```

The build requires GDAL with `/vsicurl` and the official `pmtiles` CLI. Publish `soc.pmtiles`,
`ph.pmtiles`, and `clay.pmtiles` together, then set `VITE_PRIOR_TILES_BASE` to their public directory.
Initial browser payload is checked independently from archive size; MapLibre range-requests only the
header, directory, and visible tiles.
