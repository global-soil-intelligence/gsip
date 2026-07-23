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
        x2, y2 = (
            round((patch.x_mm + patch.size_mm) * SCALE),
            round((patch.y_mm + patch.size_mm) * SCALE),
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
        canvas_width, canvas_height = 1900, 2200
        angle = np.deg2rad(20 + index)
        card_width, card_height = 980.0, 1500.0
        base = np.asarray(
            [
                [-card_width / 2, -card_height / 2],
                [card_width / 2, -card_height / 2],
                [card_width / 2, card_height / 2],
                [-card_width / 2, card_height / 2],
            ],
            dtype=np.float32,
        )
        rotation = np.asarray(
            [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]],
            dtype=np.float32,
        )
        destination = base @ rotation.T
        # A real projective warp: the far edge is shorter and offset, rather
        # than the near-affine corner jitter used by the first fixture set.
        perspective = 0.16 + index * 0.008
        destination[0] += (card_width * perspective, card_height * 0.035)
        destination[1] += (-card_width * perspective, -card_height * 0.035)
        destination[2] += (card_width * 0.04, card_height * 0.025)
        destination[3] += (-card_width * 0.04, -card_height * 0.025)
        destination += np.asarray([canvas_width / 2, canvas_height / 2], dtype=np.float32)
        destination += rng.normal(0, 9, size=(4, 2)).astype(np.float32)
        transform = cv2.getPerspectiveTransform(source_corners, destination)
        warped = cv2.warpPerspective(
            source,
            transform,
            (canvas_width, canvas_height),
            borderValue=(225, 225, 225),
        )
        normalized = warped.astype(np.float32) / 255.0
        gamma = 0.82 + index * 0.045
        nonlinear = np.power(normalized, gamma)
        color_matrix = np.asarray(
            [
                [0.88 + index * 0.006, 0.05, 0.02],
                [0.03, 0.96 - index * 0.003, 0.04],
                [0.04, 0.03, 0.90 + index * 0.004],
            ],
            dtype=np.float32,
        )
        adjusted = nonlinear @ color_matrix.T
        x_axis = np.linspace(-1, 1, canvas_width, dtype=np.float32)
        y_axis = np.linspace(-1, 1, canvas_height, dtype=np.float32)
        x, y = np.meshgrid(x_axis, y_axis)
        vignette = np.clip(1.0 - (0.05 + index * 0.004) * (x * x + y * y), 0.78, 1.0)
        adjusted *= vignette[..., None]
        adjusted += rng.normal(0, 0.008 + index * 0.0007, adjusted.shape).astype(np.float32)
        adjusted = np.clip(adjusted * 255.0, 0, 255).astype(np.uint8)
        path = output_dir / f"card-angle-light-{index + 1:02d}.jpg"
        cv2.imwrite(str(path), adjusted, [cv2.IMWRITE_JPEG_QUALITY, 94])
        paths.append(path)
    return paths
