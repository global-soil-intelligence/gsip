from __future__ import annotations

from pathlib import Path

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

SCALE = 10


def canonical_card() -> np.ndarray:
    image = np.full((round(CARD_HEIGHT_MM * SCALE), round(CARD_WIDTH_MM * SCALE), 3), 255, np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, MARKER_ID, round(MARKER_SIZE_MM * SCALE))
    x, y = round(MARKER_X_MM * SCALE), round(MARKER_Y_MM * SCALE)
    image[y : y + marker.shape[0], x : x + marker.shape[1]] = cv2.cvtColor(
        marker, cv2.COLOR_GRAY2BGR
    )
    for patch in PATCHES:
        x1, y1 = round(patch.x_mm * SCALE), round(patch.y_mm * SCALE)
        x2, y2 = round((patch.x_mm + patch.size_mm) * SCALE), round(
            (patch.y_mm + patch.size_mm) * SCALE
        )
        cv2.rectangle(image, (x1, y1), (x2, y2), patch.rgb[::-1], -1)
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 0), 2)
    return image


def generate_fixtures(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    source = canonical_card()
    height, width = source.shape[:2]
    source_corners = np.asarray(
        [[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32
    )
    rng = np.random.default_rng(22072026)
    paths: list[Path] = []
    for index in range(10):
        canvas_width, canvas_height = 1400, 1750
        margin_x, margin_y = 130, 100
        jitter = rng.integers(-70, 71, size=(4, 2)).astype(np.float32)
        destination = np.asarray(
            [
                [margin_x, margin_y],
                [canvas_width - margin_x, margin_y],
                [canvas_width - margin_x, canvas_height - margin_y],
                [margin_x, canvas_height - margin_y],
            ],
            dtype=np.float32,
        ) + jitter
        transform = cv2.getPerspectiveTransform(source_corners, destination)
        warped = cv2.warpPerspective(
            source,
            transform,
            (canvas_width, canvas_height),
            borderValue=(225, 225, 225),
        )
        cast = np.array(
            [0.86 + index * 0.018, 1.04 - index * 0.006, 0.94 + index * 0.012]
        )
        brightness = 0.82 + index * 0.04
        adjusted = np.clip(warped.astype(np.float32) * cast * brightness, 0, 255).astype(np.uint8)
        path = output_dir / f"card-angle-light-{index + 1:02d}.jpg"
        cv2.imwrite(str(path), adjusted, [cv2.IMWRITE_JPEG_QUALITY, 94])
        paths.append(path)
    return paths
