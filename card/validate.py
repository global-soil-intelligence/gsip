from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

import cv2
import numpy as np

from card.design import (
    CARD_HEIGHT_MM,
    CARD_WIDTH_MM,
    MARKER_ID,
    MARKER_SIZE_MM,
    MARKER_X_MM,
    MARKER_Y_MM,
    PATCHES,
)

PIXELS_PER_MM = 10


def canonical_point(x_mm: float, y_mm: float) -> tuple[float, float]:
    return (x_mm * PIXELS_PER_MM, y_mm * PIXELS_PER_MM)


def extract_patches(image: np.ndarray) -> dict[str, tuple[int, int, int]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(gray)
    if ids is None or MARKER_ID not in ids.flatten():
        raise ValueError(f"ArUco marker {MARKER_ID} was not detected")

    marker_index = int(np.where(ids.flatten() == MARKER_ID)[0][0])
    source = corners[marker_index].reshape(4, 2).astype(np.float32)
    destination = np.array(
        [
            canonical_point(MARKER_X_MM, MARKER_Y_MM),
            canonical_point(MARKER_X_MM + MARKER_SIZE_MM, MARKER_Y_MM),
            canonical_point(MARKER_X_MM + MARKER_SIZE_MM, MARKER_Y_MM + MARKER_SIZE_MM),
            canonical_point(MARKER_X_MM, MARKER_Y_MM + MARKER_SIZE_MM),
        ],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(source, destination)
    warped = cv2.warpPerspective(
        image,
        transform,
        (round(CARD_WIDTH_MM * PIXELS_PER_MM), round(CARD_HEIGHT_MM * PIXELS_PER_MM)),
    )

    measured: dict[str, tuple[int, int, int]] = {}
    for patch in PATCHES:
        inset = patch.size_mm * 0.22
        x1, y1 = canonical_point(patch.x_mm + inset, patch.y_mm + inset)
        x2, y2 = canonical_point(
            patch.x_mm + patch.size_mm - inset,
            patch.y_mm + patch.size_mm - inset,
        )
        region = warped[round(y1) : round(y2), round(x1) : round(x2)]
        if region.size == 0:
            raise ValueError(f"Patch {patch.name} fell outside the normalized card")
        bgr = np.median(region.reshape(-1, 3), axis=0)
        measured[patch.name] = cast(
            tuple[int, int, int], tuple(int(round(value)) for value in bgr[::-1])
        )

    neutral_measured = np.array(measured["neutral_gray"], dtype=np.float64)
    gains = 128.0 / np.maximum(neutral_measured, 1.0)
    return {
        name: cast(
            tuple[int, int, int],
            tuple(int(value) for value in np.clip(np.array(rgb) * gains, 0, 255).round()),
        )
        for name, rgb in measured.items()
    }


def validate(path: Path) -> dict[str, tuple[int, int, int]]:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return extract_patches(image)


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect and sample a photographed GSIP card")
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.image), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
