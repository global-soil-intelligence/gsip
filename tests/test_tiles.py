"""WP-6c: prior tiles are coloured from the versioned palette, with transparent nodata."""

from __future__ import annotations

import io
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from pipeline.build_prior_tiles import (
    PALETTE_PATH,
    color_table,
    colorize,
    expected_rgb,
    load_palette,
    raw_value,
    to_mbtiles,
)

PALETTE = load_palette()
NODATA = -32768
GDAL_TOOLS = ("gdaldem", "gdal_translate")
HAVE_GDAL = all(shutil.which(tool) for tool in GDAL_TOOLS)
requires_gdal = pytest.mark.skipif(
    not HAVE_GDAL and os.environ.get("GSIP_REQUIRE_GDAL") != "1",
    reason="GDAL command-line tools are not installed (CI sets GSIP_REQUIRE_GDAL=1)",
)
TILE_SIZE_M = 156543.03392804097  # one z8 web-mercator tile spans this many metres


def test_palette_file_is_the_shared_schema_palette() -> None:
    assert PALETTE_PATH.parts[-4:] == ("schema", "src", "palettes", "soilgrids.json")
    assert sorted(PALETTE) == ["clay", "ph", "soc"]


def test_color_tables_convert_canonical_stops_to_raw_soilgrids_units_exactly() -> None:
    assert color_table(PALETTE["soc"]).splitlines() == [
        "nv 0 0 0 0",
        "0 244 236 214 255",
        "50 226 200 143 255",
        "150 196 154 90 255",
        "300 148 100 55 255",
        "600 95 59 32 255",
        "1200 46 27 15 255",
    ]
    assert [line.split()[0] for line in color_table(PALETTE["ph"]).splitlines()] == [
        "nv",
        "40",
        "50",
        "60",
        "70",
        "80",
        "90",
    ]
    assert raw_value(PALETTE["clay"], 350) == 350


def test_expected_colours_interpolate_and_clamp() -> None:
    soc = PALETTE["soc"]
    assert expected_rgb(soc, -5) == soc.stops[0].rgb
    assert expected_rgb(soc, 500) == soc.stops[-1].rgb
    assert expected_rgb(soc, 2.5) == (235, 218, 178)


def _ascii_grid(path: Path, rows: list[list[int]]) -> Path:
    header = (
        f"ncols {len(rows[0])}\nnrows {len(rows)}\nxllcorner 0\nyllcorner 0\n"
        f"cellsize 1000\nNODATA_value {NODATA}\n"
    )
    path.write_text(header + "\n".join(" ".join(map(str, row)) for row in rows) + "\n")
    return path


def _georeferenced_int16(source: Path, destination: Path, extent: tuple[float, ...]) -> Path:
    subprocess.run(  # noqa: S603
        [
            shutil.which("gdal_translate") or "gdal_translate",
            "-q",
            "-ot",
            "Int16",
            "-a_srs",
            "EPSG:3857",
            "-a_nodata",
            str(NODATA),
            "-a_ullr",
            *(str(value) for value in extent),
            str(source),
            str(destination),
        ],
        check=True,
    )
    return destination


def _png_pixels(colored: Path, png: Path) -> np.ndarray:
    subprocess.run(  # noqa: S603
        [
            shutil.which("gdal_translate") or "gdal_translate",
            "-q",
            "-of",
            "PNG",
            str(colored),
            str(png),
        ],
        check=True,
    )
    with Image.open(png) as image:
        assert image.mode == "RGBA"
        return np.asarray(image)


@requires_gdal
@pytest.mark.parametrize("name", ["soc", "ph", "clay"])
def test_golden_colours_for_every_layer(tmp_path: Path, name: str) -> None:
    layer = PALETTE[name]
    first, last = layer.stops[0].value, layer.stops[-1].value
    canonical = [stop.value for stop in layer.stops]
    canonical += [
        (low.value + high.value) / 2
        for low, high in zip(layer.stops, layer.stops[1:], strict=False)
    ]
    canonical += [last * 2]  # beyond the top stop clamps to it
    raw = [round(raw_value(layer, value)) for value in canonical]
    assert max(raw) > 255 or name == "ph"  # Int16 values the v1 builder clamped to 0-255
    grid = _ascii_grid(tmp_path / f"{name}.asc", [[*raw, NODATA]])
    source = _georeferenced_int16(
        grid, tmp_path / f"{name}.tif", (0, 1000, 1000 * (len(raw) + 1), 0)
    )

    pixels = _png_pixels(
        colorize(str(source), layer, tmp_path / f"{name}.vrt"), tmp_path / "out.png"
    )

    for index, value in enumerate(canonical):
        observed = pixels[0, index]
        expected = expected_rgb(layer, min(max(value, first), last))
        assert np.max(np.abs(observed[:3].astype(int) - np.asarray(expected))) <= 2, (
            value,
            observed,
        )
        assert observed[3] == 255
    assert pixels[0, -1][3] == 0, "nodata must be transparent, never opaque black"


@requires_gdal
def test_mbtiles_tiles_are_rgba_with_transparent_nodata(tmp_path: Path) -> None:
    layer = PALETTE["soc"]
    rows = [[300] * 128 + [NODATA] * 128 for _ in range(256)]
    grid = _ascii_grid(tmp_path / "tile.asc", rows)
    source = _georeferenced_int16(grid, tmp_path / "tile.tif", (0, TILE_SIZE_M, TILE_SIZE_M, 0))
    mbtiles = to_mbtiles(
        colorize(str(source), layer, tmp_path / "tile.vrt"), tmp_path / "t.mbtiles"
    )

    with sqlite3.connect(mbtiles) as connection:
        blobs = [row[0] for row in connection.execute("select tile_data from tiles")]
    assert blobs
    tile = np.asarray(Image.open(io.BytesIO(blobs[0])).convert("RGBA"))
    opaque = tile[tile[..., 3] == 255]
    transparent = tile[tile[..., 3] == 0]
    assert len(opaque) and len(transparent)
    assert np.max(np.abs(opaque[:, :3].astype(int) - np.asarray(expected_rgb(layer, 30)))) <= 2


def test_required_tools_fail_with_an_actionable_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="gdaldem is required"):
        colorize("missing.tif", PALETTE["soc"], Path("unused.vrt"))
