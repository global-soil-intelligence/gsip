"""Staged-only phone optical summaries; no instrument spectra or publication clearance."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from uuid import UUID

import cv2
import numpy as np
from PIL import Image

from card.validate import card_transform
from pipeline.library import CameraRgb, LibraryRecord, PrivateLibrary, read_record
from pipeline.qa import SOIL_FRACTION_MIN, sanitize_jpeg, soil_region

MAX_IMAGE_BYTES = 25_000_000


def summarize_rgb(raw: bytes, device: UUID) -> CameraRgb:
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("image too large")
    clean, _ = sanitize_jpeg(raw)
    image = cv2.imdecode(np.frombuffer(clean, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("invalid image")
    transform = card_transform(image)
    region = soil_region(image, transform)
    if region.fraction < SOIL_FRACTION_MIN:
        raise ValueError("insufficient candidate soil pixels")
    # Homography excludes the card plus margin; no claim of learned soil segmentation.
    pixels = image[region.mask.astype(bool)][:, ::-1].astype(np.float64) / 255.0
    if len(pixels) < 100:
        raise ValueError("insufficient candidate soil pixels")
    means = np.mean(pixels, axis=0)
    dispersion = np.std(pixels, axis=0)
    return CameraRgb(
        kind="camera_rgb",
        source_sha256=hashlib.sha256(clean).hexdigest(),
        device_id=device,
        extractor_version="rgb-summary-v1",
        mean_rgb=(float(means[0]), float(means[1]), float(means[2])),
        std_rgb=(float(dispersion[0]), float(dispersion[1]), float(dispersion[2])),
        pixel_count=len(pixels),
        card_present=region.card_found,
        calibration_status="uncalibrated",
    )


def extract_phone_record(raw: bytes, template: LibraryRecord) -> LibraryRecord:
    if not template.synthetic:
        raise ValueError("field-photo extraction awaits privacy-screening integration")
    if not isinstance(template.measurement, CameraRgb):
        raise ValueError("camera template required")
    measurement = summarize_rgb(raw, template.measurement.device_id)
    return LibraryRecord.model_validate(template.model_dump() | {"measurement": measurement})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Staged-only private phone RGB extraction")
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        template = read_record(args.template)
        with args.image.open("rb") as source:
            raw = source.read(MAX_IMAGE_BYTES + 1)
        result = extract_phone_record(raw, template)
        added = PrivateLibrary(args.store).add(result)
        print(f"Imported staged camera records: {int(added)}")
    except (ValueError, OSError, cv2.error, Image.DecompressionBombError):
        print(
            "Invalid staged image, template or private store; operation stopped.", file=sys.stderr
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
