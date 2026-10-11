"""Build native-z8 SoilGrids PMTiles archives coloured from the versioned GSIP palette (WP-6c).

The v1 builder converted Int16 SoilGrids rasters straight to 8-bit PNG tiles, which clamps every
value to 0-255 with no scaling: SOC above 25.5 g/kg turned white, pH (stored x10) rendered dark
grey, and nodata became opaque black, while the map drew unrelated CSS legends. Now:

1. stops in canonical units are converted to raw SoilGrids units with the palette's scale;
2. ``gdaldem color-relief -alpha`` colours the warped raster through a VRT (no huge intermediate
   files), with nodata fully transparent;
3. tiles are RGBA PNG; the map draws its legends from the same palette file.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

PALETTE_PATH = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "schema"
    / "src"
    / "palettes"
    / "soilgrids.json"
)
SOURCE = (
    "/vsicurl?max_retry=3&retry_delay=2&list_dir=no"
    "&url=https://files.isric.org/soilgrids/latest/data"
)


@dataclass(frozen=True)
class PaletteStop:
    value: float
    rgb: tuple[int, int, int]


@dataclass(frozen=True)
class PaletteLayer:
    id: str
    label: str
    scale: float
    stops: tuple[PaletteStop, ...]
    unit: str
    vrt: str


def _rgb(color: str) -> tuple[int, int, int]:
    if len(color) != 7 or not color.startswith("#"):
        raise ValueError(f"palette colour must be #rrggbb, got {color!r}")
    return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))


def load_palette(path: Path = PALETTE_PATH) -> dict[str, PaletteLayer]:
    document = json.loads(path.read_text(encoding="utf-8"))
    layers: dict[str, PaletteLayer] = {}
    for layer in document["layers"]:
        stops = tuple(
            PaletteStop(float(stop["value"]), _rgb(str(stop["color"]))) for stop in layer["stops"]
        )
        if len(stops) < 2 or any(
            b.value <= a.value for a, b in zip(stops, stops[1:], strict=False)
        ):
            raise ValueError(f"palette {layer['id']} needs at least two increasing stops")
        layers[str(layer["id"])] = PaletteLayer(
            id=str(layer["id"]),
            label=str(layer["label"]),
            scale=float(layer["soilgrids"]["scale"]),
            stops=stops,
            unit=str(layer["unit"]),
            vrt=str(layer["soilgrids"]["vrt"]),
        )
    return layers


def raw_value(layer: PaletteLayer, canonical: float) -> float:
    """Canonical GSIP units -> raw SoilGrids units (for example g/kg -> dg/kg for SOC)."""

    return round(canonical / layer.scale, 6)


def color_table(layer: PaletteLayer) -> str:
    """A gdaldem colour file in raw units; nodata is fully transparent."""

    lines = ["nv 0 0 0 0"]
    for stop in layer.stops:
        red, green, blue = stop.rgb
        lines.append(f"{raw_value(layer, stop.value):g} {red} {green} {blue} 255")
    return "\n".join(lines) + "\n"


def expected_rgb(layer: PaletteLayer, canonical: float) -> tuple[int, int, int]:
    """The colour gdaldem produces for a value: linear between stops, clamped at both ends."""

    stops = layer.stops
    if canonical <= stops[0].value:
        return stops[0].rgb
    if canonical >= stops[-1].value:
        return stops[-1].rgb
    for low, high in zip(stops, stops[1:], strict=False):
        if low.value <= canonical <= high.value:
            share = (canonical - low.value) / (high.value - low.value)
            red, green, blue = (
                round(a + (b - a) * share) for a, b in zip(low.rgb, high.rgb, strict=True)
            )
            return (red, green, blue)
    raise AssertionError("unreachable: stops are increasing")  # pragma: no cover


def require(command: str) -> str:
    path = shutil.which(command)
    if not path:
        raise RuntimeError(
            f"{command} is required. Use the documented OSGeo (GDAL) + go-pmtiles toolchain."
        )
    return path


def colorize(source: str, layer: PaletteLayer, destination: Path) -> Path:
    """Colour ``source`` through a VRT so a global raster never needs an intermediate file."""

    gdaldem = require("gdaldem")
    colors = destination.with_suffix(".colors.txt")
    colors.write_text(color_table(layer), encoding="utf-8")
    subprocess.run(  # noqa: S603
        [
            gdaldem,
            "color-relief",
            "-q",
            "-of",
            "VRT",
            "-alpha",
            source,
            str(colors),
            str(destination),
        ],
        check=True,
    )
    return destination


def to_mbtiles(colored: Path, destination: Path) -> Path:
    gdal_translate = require("gdal_translate")
    subprocess.run(  # noqa: S603
        [
            gdal_translate,
            "-q",
            "-of",
            "MBTILES",
            "-co",
            "TILE_FORMAT=PNG",
            str(colored),
            str(destination),
        ],
        check=True,
    )
    return destination


def build_layer(name: str, output: Path, max_zoom: int, palette: dict[str, PaletteLayer]) -> Path:
    layer = palette[name]
    gdaladdo = require("gdaladdo")
    gdalwarp = require("gdalwarp")
    pmtiles = require("pmtiles")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"gsip-{name}-") as temporary:
        warped = Path(temporary) / f"{name}.vrt"
        colored = Path(temporary) / f"{name}-colored.vrt"
        mbtiles = Path(temporary) / f"{name}.mbtiles"
        resolution = f"{156543.03392804097 / 2**max_zoom:.8f}"
        subprocess.run(  # noqa: S603
            [
                gdalwarp,
                "-q",
                "-of",
                "VRT",
                "-r",
                "bilinear",
                "-t_srs",
                "EPSG:3857",
                "-tr",
                resolution,
                resolution,
                "-tap",
                f"{SOURCE}/{layer.vrt}",
                str(warped),
            ],
            check=True,
        )
        colorize(str(warped), layer, colored)
        to_mbtiles(colored, mbtiles)
        factors = [str(2**level) for level in range(1, max_zoom + 1)]
        subprocess.run([gdaladdo, "-q", "-r", "average", str(mbtiles), *factors], check=True)  # noqa: S603
        destination = output / f"{name}.pmtiles"
        subprocess.run([pmtiles, "convert", str(mbtiles), str(destination)], check=True)  # noqa: S603
    return destination


def main() -> None:
    palette = load_palette()
    parser = argparse.ArgumentParser(description="Build native-z8 SoilGrids PMTiles archives")
    parser.add_argument("--output", type=Path, default=Path("output/tiles"))
    parser.add_argument("--max-zoom", type=int, default=8, choices=range(0, 9))
    parser.add_argument("--property", action="append", choices=sorted(palette), dest="properties")
    args = parser.parse_args()
    for name in args.properties or list(palette):
        built = build_layer(name, args.output, args.max_zoom, palette)
        print(f"built {built}")


if __name__ == "__main__":
    main()
