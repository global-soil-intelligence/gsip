"""Synthetic photographs of a node card, for tests. No real photograph or person is involved."""

from __future__ import annotations

import cv2
import numpy as np

from card.node_design import (
    ALL_PATCHES,
    CARD_HEIGHT_MM,
    CARD_WIDTH_MM,
    MARKER_ID,
    MARKER_SIZE_MM,
    MARKER_X_MM,
    MARKER_Y_MM,
)

SCALE = 12


def canonical_node_card(marker_id: int = MARKER_ID, *, ring: bool = False) -> np.ndarray:
    """The card at 12 pixels a millimetre. ``ring`` paints a 1 mm band of a clashing colour just
    inside every patch edge, so a sampling window that strays shows up in the reading."""

    image = np.full((round(CARD_HEIGHT_MM * SCALE), round(CARD_WIDTH_MM * SCALE), 3), 255, np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, marker_id, round(MARKER_SIZE_MM * SCALE))
    x, y = round(MARKER_X_MM * SCALE), round(MARKER_Y_MM * SCALE)
    image[y : y + marker.shape[0], x : x + marker.shape[1]] = cv2.cvtColor(
        marker, cv2.COLOR_GRAY2BGR
    )
    for patch in ALL_PATCHES:
        x1, y1 = round(patch.x_mm * SCALE), round(patch.y_mm * SCALE)
        x2 = round((patch.x_mm + patch.width_mm) * SCALE)
        y2 = round((patch.y_mm + patch.height_mm) * SCALE)
        cv2.rectangle(image, (x1, y1), (x2, y2), patch.rgb[::-1], -1)
        if ring:
            half = SCALE // 2
            cv2.rectangle(
                image, (x1 + half, y1 + half), (x2 - half, y2 - half), (255, 0, 255), SCALE
            )
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 0), 1)
    return image


def photograph(
    index: int,
    *,
    card_width_px: float = 1100.0,
    canvas: tuple[int, int] = (2000, 1500),
    shift: bool = True,
    flat: bool = False,
    source: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """One synthetic photo and the true image position of the card's four corners.

    ``index`` varies the angle, perspective, colour cast, tone curve, vignette and noise.
    ``card_width_px`` sets how large the card is in the frame. ``flat`` removes the perspective
    and corner jitter, leaving a rotated card seen square-on."""

    card = canonical_node_card() if source is None else source
    height, width = card.shape[:2]
    corners = np.asarray([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32)
    rng = np.random.default_rng(15112026 + index)
    canvas_width, canvas_height = canvas
    card_height_px = card_width_px * CARD_HEIGHT_MM / CARD_WIDTH_MM
    angle = np.deg2rad(-25 + index * 6)
    base = np.asarray(
        [
            [-card_width_px / 2, -card_height_px / 2],
            [card_width_px / 2, -card_height_px / 2],
            [card_width_px / 2, card_height_px / 2],
            [-card_width_px / 2, card_height_px / 2],
        ],
        dtype=np.float32,
    )
    rotation = np.asarray(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]], dtype=np.float32
    )
    destination = base @ rotation.T
    perspective = 0.0 if flat else 0.05 + index * 0.008
    lift = 0.0 if flat else card_height_px * 0.03
    destination[0] += (card_width_px * perspective, lift)
    destination[1] += (-card_width_px * perspective, -lift)
    destination += np.asarray([canvas_width / 2, canvas_height / 2], dtype=np.float32)
    if not flat:
        destination += rng.normal(0, card_width_px * 0.006, size=(4, 2)).astype(np.float32)
    transform = cv2.getPerspectiveTransform(corners, destination)
    warped = cv2.warpPerspective(
        card, transform, (canvas_width, canvas_height), borderValue=(96, 122, 148)
    )
    if not shift:
        return warped, destination
    normalized = warped.astype(np.float32) / 255.0
    nonlinear = np.power(normalized, 0.82 + index * 0.045)
    cast = np.asarray(
        [
            [0.88 + index * 0.006, 0.05, 0.02],
            [0.03, 0.96 - index * 0.003, 0.04],
            [0.04, 0.03, 0.90 + index * 0.004],
        ],
        dtype=np.float32,
    )
    adjusted = nonlinear @ cast.T
    x_axis = np.linspace(-1, 1, canvas_width, dtype=np.float32)
    y_axis = np.linspace(-1, 1, canvas_height, dtype=np.float32)
    x, y = np.meshgrid(x_axis, y_axis)
    adjusted *= np.clip(1.0 - (0.05 + index * 0.004) * (x * x + y * y), 0.78, 1.0)[..., None]
    adjusted += rng.normal(0, 0.008 + index * 0.0007, adjusted.shape).astype(np.float32)
    return np.clip(adjusted * 255.0, 0, 255).astype(np.uint8), destination
