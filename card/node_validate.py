"""Detect a photographed GSIP Node Card and read its patches. Detection only: nothing here
corrects soil colour, and the capture pipeline does not call this module yet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

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
    RAMP,
    REPEATED,
    SCALE_LENGTH_MM,
)

PIXELS_PER_MM = 12
INSET = 0.24
# Below this the far patches cannot be placed reliably from one marker. On synthetic photographs
# the far corners were off by up to 2.8 percent of the card's width with a 100 to 118 pixel
# marker, more than the narrowest patch inset allows. 125 pixels is a card about 446 pixels wide
# seen square-on.
MIN_MARKER_SIDE_PX = 125.0
# A patch is one flat colour. A window that is not flat is covered, lit unevenly or blurred.
MAX_PATCH_SPREAD = 12.0
MAX_REPEAT_DIFFERENCE = 30

Rgb = tuple[int, int, int]


def _point(x_mm: float, y_mm: float) -> tuple[float, float]:
    return (x_mm * PIXELS_PER_MM, y_mm * PIXELS_PER_MM)


def _colour_image(image: np.ndarray) -> np.ndarray:
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError("a node card is read from an 8-bit, three-channel BGR image")
    return image


def _node_markers(image: np.ndarray) -> list[np.ndarray]:
    """Corner quadrilaterals of every node-card marker in the photograph."""

    gray = cv2.cvtColor(_colour_image(image), cv2.COLOR_BGR2GRAY)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()
    # The marker is small and the far patches are three marker-widths away, so its corners are
    # located to a fraction of a pixel before the card is projected from them.
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    detector = cv2.aruco.ArucoDetector(dictionary, parameters)
    corners, ids, _ = detector.detectMarkers(gray)
    if ids is None:
        return []
    return [
        corners[int(index)].reshape(4, 2).astype(np.float32)
        for index in np.where(ids.flatten() == MARKER_ID)[0]
    ]


def _transform_from(marker: np.ndarray) -> np.ndarray:
    destination = np.array(
        [
            _point(MARKER_X_MM, MARKER_Y_MM),
            _point(MARKER_X_MM + MARKER_SIZE_MM, MARKER_Y_MM),
            _point(MARKER_X_MM + MARKER_SIZE_MM, MARKER_Y_MM + MARKER_SIZE_MM),
            _point(MARKER_X_MM, MARKER_Y_MM + MARKER_SIZE_MM),
        ],
        dtype=np.float32,
    )
    return cast(np.ndarray, cv2.getPerspectiveTransform(marker, destination))


def node_card_outlines(image: np.ndarray) -> list[np.ndarray]:
    """Where each node card lies in the photograph, as four corners, whether or not it is usable.

    For masking a card out of the soil: a card that is too small, cut off by the frame or one of
    two is still not soil. The corners may lie outside the photograph."""

    outlines = []
    for marker in _node_markers(image):
        try:
            corners = node_card_corners(_transform_from(marker))
        except (np.linalg.LinAlgError, cv2.error):
            continue
        if bool(np.isfinite(corners).all()):
            outlines.append(corners)
    return outlines


def node_card_transform(image: np.ndarray) -> np.ndarray | None:
    """Return the homography from image pixels to canonical node-card pixels, or None.

    None when the node card's marker is not found exactly once, when it is too small to place
    the far patches, or when the card does not lie wholly inside the photograph. An A6 card or a
    mirrored photograph is not a node card."""

    markers = _node_markers(image)
    # Two node cards in one frame are ambiguous; refuse to guess which one is the control.
    if len(markers) != 1:
        return None
    source = markers[0]
    sides = np.linalg.norm(source - np.roll(source, -1, axis=0), axis=1)
    if float(sides.min()) < MIN_MARKER_SIDE_PX:
        return None
    transform = _transform_from(source)
    height, width = image.shape[:2]
    projected = node_card_corners(transform)
    inside = (
        (projected[:, 0] >= 0)
        & (projected[:, 0] <= width - 1)
        & (projected[:, 1] >= 0)
        & (projected[:, 1] <= height - 1)
    )
    return transform if bool(inside.all()) else None


def node_card_corners(transform: np.ndarray) -> np.ndarray:
    """Project the four card corners into image pixels, clockwise from top-left."""

    width = CARD_WIDTH_MM * PIXELS_PER_MM
    height = CARD_HEIGHT_MM * PIXELS_PER_MM
    canonical = np.array(
        [[[0.0, 0.0]], [[width, 0.0]], [[width, height]], [[0.0, height]]], dtype=np.float32
    )
    projected = cv2.perspectiveTransform(canonical, np.linalg.inv(transform).astype(np.float32))
    return cast(np.ndarray, projected.reshape(4, 2))


def card_scale(transform: np.ndarray) -> tuple[float, float]:
    """Millimetres per image pixel at the middle of the card: along its width, then its height.

    From the card's homography, evaluated over the scale line's length in each direction. The two
    differ when the card is tilted or the image is stretched, so both are returned and neither
    is averaged away. Valid on the card's plane only: soil nearer or farther than the card has
    another scale."""

    half = SCALE_LENGTH_MM * PIXELS_PER_MM / 2
    cx, cy = CARD_WIDTH_MM * PIXELS_PER_MM / 2, CARD_HEIGHT_MM * PIXELS_PER_MM / 2
    ends = np.array(
        [[[cx - half, cy]], [[cx + half, cy]], [[cx, cy - half]], [[cx, cy + half]]],
        dtype=np.float32,
    )
    projected = cv2.perspectiveTransform(ends, np.linalg.inv(transform).astype(np.float32))
    across = float(np.linalg.norm(projected[1, 0] - projected[0, 0]))
    down = float(np.linalg.norm(projected[3, 0] - projected[2, 0]))
    if not (np.isfinite(across) and np.isfinite(down)) or min(across, down) <= 0:
        raise ValueError("card scale could not be measured")
    return SCALE_LENGTH_MM / across, SCALE_LENGTH_MM / down


def read_patches(image: np.ndarray, transform: np.ndarray | None = None) -> dict[str, Rgb]:
    """Median RGB of each patch as photographed, or a refusal.

    No correction is applied: these are the raw measurements a later colour correction would be
    fitted to. The reading is refused when a patch window is not wholly inside the photograph,
    when a patch is not one flat colour, when the neutral ramp is out of order, when a patch and
    the ramp step printed with nearly the same value differ by much more or less than they should,
    or when any channel of any patch is at 0 or 255. An even cover of one colour goes undetected
    on the eight patches nothing repeats (six colours and ramp steps 1 and 3), and on a repeated
    patch when the cover is within the tolerance of the patch's own colour."""

    image = _colour_image(image)
    if transform is None:
        transform = node_card_transform(image)
    if transform is None:
        raise ValueError("no single, whole, large-enough node card was found in the photograph")
    size = (round(CARD_WIDTH_MM * PIXELS_PER_MM), round(CARD_HEIGHT_MM * PIXELS_PER_MM))
    warped = cv2.warpPerspective(image, transform, size)
    # The same warp of an all-ones image marks which canonical pixels came from the photograph.
    covered = cv2.warpPerspective(
        np.full(image.shape[:2], 255, np.uint8), transform, size, flags=cv2.INTER_NEAREST
    )
    measured: dict[str, Rgb] = {}
    for patch in ALL_PATCHES:
        x1, y1 = _point(patch.x_mm + patch.width_mm * INSET, patch.y_mm + patch.height_mm * INSET)
        x2, y2 = _point(
            patch.x_mm + patch.width_mm * (1 - INSET),
            patch.y_mm + patch.height_mm * (1 - INSET),
        )
        window = (slice(round(y1), round(y2)), slice(round(x1), round(x2)))
        region = warped[window].reshape(-1, 3).astype(np.float64)
        if region.size == 0 or not bool((covered[window] == 255).all()):
            raise ValueError(f"patch {patch.name} is not wholly inside the photograph")
        bgr = np.median(region, axis=0)
        # The ninetieth percentile, not the median: a tenth of the window off-colour is enough.
        spread = float(np.percentile(np.abs(region - bgr), 90, axis=0).max())
        if spread > MAX_PATCH_SPREAD:
            raise ValueError(f"patch {patch.name} is not one flat colour")
        measured[patch.name] = cast(Rgb, tuple(int(round(value)) for value in bgr[::-1]))
    brightness = [sum(measured[step.name]) for step in RAMP]
    if any(later <= earlier for earlier, later in zip(brightness, brightness[1:], strict=False)):
        raise ValueError("the neutral ramp is out of order")
    targets = {patch.name: patch.rgb for patch in ALL_PATCHES}
    for first, second in REPEATED:
        gap = max(
            abs((a - b) - (wanted_a - wanted_b))
            for a, b, wanted_a, wanted_b in zip(
                measured[first], measured[second], targets[first], targets[second], strict=True
            )
        )
        if gap > MAX_REPEAT_DIFFERENCE:
            raise ValueError(
                f"{first} and {second} are printed nearly alike but were read differently"
            )
    for name, rgb in measured.items():
        if min(rgb) <= 0 or max(rgb) >= 255:
            raise ValueError(f"patch {name} is clipped: the photograph is too dark or too bright")
    return measured


def validate(path: Path) -> dict[str, Rgb]:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return read_patches(image)


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect and sample a photographed GSIP node card")
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.image), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
