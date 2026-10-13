"""Create fictional paired records and run the local pipeline, never scientific evidence."""

from __future__ import annotations

import hashlib
import io
import json
import sys
from pathlib import Path
from uuid import UUID

from PIL import Image

from ml.library_baseline import run_baseline
from pipeline.library import (
    CameraRgb,
    Context,
    InstrumentReflectance,
    LibraryRecord,
    PrivateArgumentParser,
    PrivateLibrary,
)
from pipeline.phone_optics import summarize_rgb


def demo(output: Path) -> dict[str, int | float | bool | str]:
    if output.exists():
        raise ValueError("output already exists")
    # PrivateLibrary enforces permissions and refuses symlinks before creating the directory.
    PrivateLibrary(output)
    store = PrivateLibrary(output / "records")
    for index in range(12):
        image = Image.new("RGB", (100, 100), (50 + index * 8, 70 + index * 3, 90))
        stream = io.BytesIO()
        image.save(stream, format="JPEG")
        camera = summarize_rgb(stream.getvalue(), UUID(int=5))
        # Deliberately fictional linear response; not a simulated sensor accuracy benchmark.
        values = tuple(0.1 + 0.5 * channel for channel in camera.mean_rgb)
        spectrum = InstrumentReflectance(
            kind="instrument_reflectance",
            source_sha256=hashlib.sha256(json.dumps(values).encode()).hexdigest(),
            instrument_id=UUID(int=6),
            calibration_id=UUID(int=7),
            wavelength_nm=(450.0, 550.0, 650.0),
            reflectance=values,
            uncertainty=(0.01,) * 3,
        )
        measurements: tuple[CameraRgb | InstrumentReflectance, ...] = (camera, spectrum)
        for offset, measurement in enumerate(measurements):
            store.add(
                LibraryRecord(
                    schema_version="gsip-library-v1",
                    measurement_id=UUID(int=100 + index * 2 + offset),
                    node_id=UUID(int=2),
                    sample_id=UUID(int=1000 + index),
                    grant_id=UUID(int=4),
                    protocol_version="gsip-capture-v1",
                    context=Context(depth_top_cm=0.0, depth_bottom_cm=5.0, condition="dry"),
                    consent_verified=True,
                    pairing_verified=True,
                    withdrawn=False,
                    synthetic=True,
                    holdout=False,
                    qa_status="pass",
                    measurement=measurement,
                    labels=(),
                )
            )
    receipt = run_baseline(store.records(), output / "baseline", demo=True)
    return {
        "mode": receipt["mode"],
        "scientific_validation": False,
        "paired_samples": receipt["train_samples"] + receipt["development_samples"],
        "train_samples": receipt["train_samples"],
        "development_samples": receipt["development_samples"],
        "sample_overlap": receipt["sample_overlap"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = PrivateArgumentParser(
        description="Fictional GSIP library demo; no scientific claims"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(demo(args.output), sort_keys=True))
    except (ValueError, OSError):
        print("Invalid private demo output; operation stopped.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
