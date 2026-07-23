"""Auditable RGB features, not reconstructed or measured spectroscopy."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from ml.pilot import Observation, local_image

FEATURE_VERSION = "rgb-roi-v1-uncalibrated"
IMAGE_FEATURES = [
    "red_mean",
    "green_mean",
    "blue_mean",
    "red_std",
    "green_std",
    "blue_std",
    "brightness_q10",
    "brightness_q50",
    "brightness_q90",
    "surface_gradient",
    "clipped_fraction",
]
CONTEXT_FEATURES = ["moist", "wet", "direct_sun", "artificial_light"]


def image_features(observation: Observation, root: Path) -> tuple[list[float], str]:
    path = local_image(root, observation.image_path)
    if path.stat().st_size > 12 * 1024 * 1024:
        raise ValueError("image exceeds the 12 MB pilot limit")
    raw = path.read_bytes()
    with Image.open(path) as source:
        if source.format != "JPEG":
            raise ValueError("pilot images must be JPEG")
        if source.width * source.height > 40_000_000:
            raise ValueError("image exceeds the pixel limit")
        oriented = ImageOps.exif_transpose(source)
        x0, y0, x1, y1 = observation.soil_roi
        if x1 > oriented.width or y1 > oriented.height:
            raise ValueError("soil ROI extends outside the oriented photograph")
        crop = oriented.convert("RGB").crop((x0, y0, x1, y1))
        # Fixed analysis size makes texture statistics comparable across image dimensions.
        pixels = np.asarray(crop.resize((128, 128)), dtype=np.float64) / 255.0
    flat = pixels.reshape(-1, 3)
    gray = pixels @ np.array([0.2126, 0.7152, 0.0722])
    clipped = float(np.mean((gray <= 5 / 255) | (gray >= 250 / 255)))
    if clipped > 0.28 or not 0.08 <= float(gray.mean()) <= 0.92:
        raise ValueError("ROI exposure is unsuitable for prediction")
    values = [
        *flat.mean(axis=0),
        *flat.std(axis=0),
        *np.quantile(gray, [0.1, 0.5, 0.9]),
        (np.abs(np.diff(gray, axis=0)).mean() + np.abs(np.diff(gray, axis=1)).mean()) / 2,
        clipped,
    ]
    return [float(v) for v in values], hashlib.sha256(raw).hexdigest()


def fused_features(observation: Observation, image: list[float]) -> list[float]:
    return [
        observation.prior.mean,
        *image,
        float(observation.surface_condition == "moist"),
        float(observation.surface_condition == "wet"),
        float(observation.lighting == "direct_sun"),
        float(observation.lighting == "artificial"),
    ]
