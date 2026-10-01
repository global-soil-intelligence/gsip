from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

LAYERS = {
    "soc": "soc/soc_0-5cm_mean.vrt",
    "ph": "phh2o/phh2o_0-5cm_mean.vrt",
    "clay": "clay/clay_0-5cm_mean.vrt",
}
SOURCE = "/vsicurl?max_retry=3&retry_delay=2&list_dir=no&url=https://files.isric.org/soilgrids/latest/data"


def require(command: str) -> str:
    path = shutil.which(command)
    if not path:
        raise RuntimeError(
            f"{command} is required. Use the documented OSGeo + go-pmtiles toolchain."
        )
    return path


def build_layer(name: str, output: Path, max_zoom: int) -> Path:
    gdal_translate = require("gdal_translate")
    gdaladdo = require("gdaladdo")
    gdalwarp = require("gdalwarp")
    pmtiles = require("pmtiles")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"gsip-{name}-") as temporary:
        mbtiles = Path(temporary) / f"{name}.mbtiles"
        warped = Path(temporary) / f"{name}.vrt"
        source = f"{SOURCE}/{LAYERS[name]}"
        resolution = f"{156543.03392804097 / 2**max_zoom:.8f}"
        subprocess.run(  # noqa: S603
            [
                gdalwarp,
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
                source,
                str(warped),
            ],
            check=True,
        )
        subprocess.run(  # noqa: S603
            [
                gdal_translate,
                "-of",
                "MBTILES",
                "-co",
                "TILE_FORMAT=PNG8",
                str(warped),
                str(mbtiles),
            ],
            check=True,
        )
        factors = [str(2**level) for level in range(1, max_zoom + 1)]
        subprocess.run(  # noqa: S603
            [gdaladdo, "-r", "average", str(mbtiles), *factors], check=True
        )
        destination = output / f"{name}.pmtiles"
        subprocess.run(  # noqa: S603
            [pmtiles, "convert", str(mbtiles), str(destination)], check=True
        )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Build native-z8 SoilGrids PMTiles archives")
    parser.add_argument("--output", type=Path, default=Path("output/tiles"))
    parser.add_argument("--max-zoom", type=int, default=8, choices=range(0, 9))
    parser.add_argument("--property", action="append", choices=LAYERS, dest="properties")
    args = parser.parse_args()
    for name in args.properties or list(LAYERS):
        built = build_layer(name, args.output, args.max_zoom)
        print(f"built {built}")


if __name__ == "__main__":
    main()
