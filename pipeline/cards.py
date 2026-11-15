"""Find the reference card in a photograph: the A6 card or the node card (SPEC section 17.2).

``card/design.py`` and ``card/validate.py`` are bound by the photo-privacy calibration and are
used here unchanged."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

import cv2
import numpy as np

from card import design as a6
from card import node_design as node
from card.node_validate import node_card_outlines, node_card_transform, read_patches
from card.validate import PIXELS_PER_MM, canonical_point, card_corners, card_transform

Rgb = tuple[int, int, int]
Edition = Literal["a6", "node"]
A6_INSET = 0.22


@dataclass(frozen=True, eq=False)
class CardReading:
    edition: Edition
    patches: dict[str, Rgb]
    targets: dict[str, Rgb]
    ramp: tuple[str, ...]


@dataclass(frozen=True, eq=False)
class Cards:
    """Every card outline in the frame, and the one reading when exactly one card is usable."""

    outlines: tuple[np.ndarray, ...]
    reading: CardReading | None
    # The outline of the card that was read, when one was.
    read_outline: np.ndarray | None = None


def _a6_markers(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(gray)
    if ids is None:
        return []
    return [
        corners[int(index)].reshape(4, 2).astype(np.float32)
        for index in np.where(ids.flatten() == a6.MARKER_ID)[0]
    ]


def _a6_transform(marker: np.ndarray) -> np.ndarray:
    destination = np.array(
        [
            canonical_point(a6.MARKER_X_MM, a6.MARKER_Y_MM),
            canonical_point(a6.MARKER_X_MM + a6.MARKER_SIZE_MM, a6.MARKER_Y_MM),
            canonical_point(a6.MARKER_X_MM + a6.MARKER_SIZE_MM, a6.MARKER_Y_MM + a6.MARKER_SIZE_MM),
            canonical_point(a6.MARKER_X_MM, a6.MARKER_Y_MM + a6.MARKER_SIZE_MM),
        ],
        dtype=np.float32,
    )
    return cast(np.ndarray, cv2.getPerspectiveTransform(marker, destination))


def _a6_patches(image: np.ndarray, transform: np.ndarray) -> dict[str, Rgb] | None:
    """Median RGB of each A6 patch as photographed, or None when one lies outside the photo."""

    size = (round(a6.CARD_WIDTH_MM * PIXELS_PER_MM), round(a6.CARD_HEIGHT_MM * PIXELS_PER_MM))
    warped = cv2.warpPerspective(image, transform, size)
    covered = cv2.warpPerspective(
        np.full(image.shape[:2], 255, np.uint8), transform, size, flags=cv2.INTER_NEAREST
    )
    measured: dict[str, Rgb] = {}
    for patch in a6.PATCHES:
        inset = patch.size_mm * A6_INSET
        x1, y1 = canonical_point(patch.x_mm + inset, patch.y_mm + inset)
        x2, y2 = canonical_point(
            patch.x_mm + patch.size_mm - inset, patch.y_mm + patch.size_mm - inset
        )
        window = (slice(round(y1), round(y2)), slice(round(x1), round(x2)))
        region = warped[window].reshape(-1, 3)
        if region.size == 0 or not bool((covered[window] == 255).all()):
            return None
        bgr = np.median(region, axis=0)
        measured[patch.name] = cast(Rgb, tuple(int(round(value)) for value in bgr[::-1]))
    return measured


def find_cards(image: np.ndarray) -> Cards:
    """Locate every reference card, and read the patches when exactly one card is in the frame.

    ``image`` is an 8-bit, three-channel BGR array, as ``cv2.imdecode(..., IMREAD_COLOR)`` gives.

    Two cards, of either edition, give no reading: there is no way to tell which one shares the
    soil's light. Every card found is still reported so that it can be masked out of the soil."""

    a6_markers = _a6_markers(image)
    outlines = [
        corners
        for corners in (card_corners(_a6_transform(marker)) for marker in a6_markers)
        if bool(np.isfinite(corners).all())
    ]
    node_outlines = node_card_outlines(image)
    outlines.extend(node_outlines)
    reading: CardReading | None = None
    if len(a6_markers) == 1 and not node_outlines:
        transform = card_transform(image)
        patches = _a6_patches(image, transform) if transform is not None else None
        if patches is not None:
            reading = CardReading(
                "a6",
                patches,
                {patch.name: patch.rgb for patch in a6.PATCHES},
                # The A6 card has no ramp; its black, grey and white patches stand in for one.
                ("black", "neutral_gray", "white"),
            )
    elif len(node_outlines) == 1 and not a6_markers:
        transform = node_card_transform(image)
        if transform is not None:
            try:
                patches = read_patches(image, transform)
            except ValueError:
                patches = None
            if patches is not None:
                reading = CardReading(
                    "node",
                    patches,
                    {patch.name: patch.rgb for patch in node.ALL_PATCHES},
                    tuple(step.name for step in node.RAMP),
                )
    return Cards(tuple(outlines), reading, outlines[0] if reading is not None else None)
