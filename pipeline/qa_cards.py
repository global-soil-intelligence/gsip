"""Photo QA that knows both reference-card editions (SPEC section 17).

``pipeline/qa.py`` is bound by the photo-privacy configuration and is not edited. This module
repeats its ``evaluate_photo`` step for step, with two differences: every card of either edition
is masked from the soil region, and one readable card yields a private colour record. A photo
with no card, or with one whole A6 card, receives the same events and status as before; only
the recorded version differs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np

from pipeline.cards import CardReading, find_cards
from pipeline.colour_correction import (
    CORRECTION_VERSION,
    MAX_RESIDUAL_DELTA_E,
    Correction,
    fit,
    soil_colour,
)
from pipeline.qa import (
    CARD_MASK_SCALE,
    NEAR_DUPLICATE_DISTANCE,
    SHARPNESS_MIN,
    SOIL_FRACTION_MIN,
    QaEvent,
    SoilClassifier,
    SoilRegion,
    exposure_score,
    gps_plausible,
    hamming_distance,
    perceptual_hash,
    photo_status,
    sanitize_jpeg,
    sharpness,
)

# Node-card photos, two A6 cards and an A6 card cut by the frame are judged differently from
# ``pipeline.qa`` (SPEC section 17.2), so results from this gate carry their own version (I13).
CARD_QA_MODEL_VERSION = "deterministic-v3"


@dataclass(frozen=True)
class CardQaResult:
    """As ``pipeline.qa.QaResult``, with the card finding and the versioned colour record."""

    calibration_status: str
    camera_metadata: dict[str, float | int | str]
    card_color_correction: dict[str, object] | None
    card_detected: bool
    events: tuple[QaEvent, ...]
    perceptual_hash: str
    sanitized_jpeg: bytes
    status: str
    model_version: str = CARD_QA_MODEL_VERSION


def soil_region_without(image: np.ndarray, outlines: Sequence[np.ndarray]) -> SoilRegion:
    """Mask every reference card so that none can dominate soil QA (SPEC I8, section 17.2).

    Without a card the whole frame is soil. Each card outline, projected from its own marker, is
    enlarged about its centroid and removed, whether or not the card is usable. ``crop`` is the
    largest axis-aligned band of the frame beside the cards, used for the perceptual hash."""

    height, width = image.shape[:2]
    mask = np.ones((height, width), dtype=np.uint8)
    if not outlines:
        return SoilRegion(card_found=False, crop=(0, 0, width, height), fraction=1.0, mask=mask)
    reach = 4.0 * max(width, height)
    enlarged_all = []
    for corners in outlines:
        centroid = corners.mean(axis=0)
        enlarged = centroid + (corners - centroid) * CARD_MASK_SCALE
        if not bool(np.isfinite(enlarged).all()):
            continue
        if cv2.contourArea(enlarged.astype(np.float32)) > MAX_OUTLINE_FRAME_AREAS * width * height:
            continue
        # A marker seen at a steep angle can project corners far away; keep the polygon drawable.
        enlarged = np.clip(
            np.nan_to_num(enlarged, nan=0.0, posinf=reach, neginf=-reach), -reach, reach
        )
        cv2.fillPoly(mask, [np.round(enlarged).astype(np.int32)], 0)
        enlarged_all.append(enlarged)
    if not enlarged_all:
        return SoilRegion(card_found=False, crop=(0, 0, width, height), fraction=1.0, mask=mask)
    every = np.concatenate(enlarged_all)
    x0 = int(np.clip(np.floor(every[:, 0].min()), 0, width))
    x1 = int(np.clip(np.ceil(every[:, 0].max()), 0, width))
    y0 = int(np.clip(np.floor(every[:, 1].min()), 0, height))
    y1 = int(np.clip(np.ceil(every[:, 1].max()), 0, height))
    candidates = [
        (0, 0, width, y0),
        (0, y1, width, height),
        (0, 0, x0, height),
        (x1, 0, width, height),
    ]
    crop = max(candidates, key=lambda box: (box[2] - box[0]) * (box[3] - box[1]))
    if (crop[2] - crop[0]) * (crop[3] - crop[1]) == 0:
        crop = (0, 0, width, height)
    return SoilRegion(card_found=True, crop=crop, fraction=float(mask.mean()), mask=mask)


# Soil colour is taken from the soil inside the card's outline enlarged this many times about its
# centre: a band about half a card wide around the card, where the light is most likely the
# light the card is in.
NEAR_CARD_SCALE = 2.0
# An outline this many times the frame's area comes from a marker seen almost edge-on, not from
# a card. Masking it would hide the whole photo, so it is ignored.
MAX_OUTLINE_FRAME_AREAS = 4.0


def soil_near_card(mask: np.ndarray, outline: np.ndarray | None) -> np.ndarray:
    """The soil pixels beside the card that was read; the whole soil region if there are none."""

    if outline is None:
        return mask
    centroid = outline.mean(axis=0)
    reach = 4.0 * max(mask.shape)
    wide = np.clip(centroid + (outline - centroid) * NEAR_CARD_SCALE, -reach, reach)
    near = np.zeros_like(mask)
    cv2.fillPoly(near, [np.round(wide).astype(np.int32)], 1)
    near &= mask
    return near if int(near.sum()) >= 2_000 else mask


def colour_record(
    image: np.ndarray, mask: np.ndarray, reading: CardReading | None
) -> dict[str, object] | None:
    """The private colour record for a photo with one readable card.

    ``normalised`` is true only when the fitted correction predicts each patch it was not shown
    within the limit. The photograph itself is never changed (SPEC section 17.1). These values
    are for the soil estimator only: they are not reflectance calibration and never enter a
    ``camera_rgb`` library record (SPEC L1, L3, section 16.3)."""

    if reading is None:
        return None
    correction: Correction | None
    try:
        correction = fit(reading.patches, reading.targets, reading.ramp)
    except ValueError:
        correction = None
    uncorrected = soil_colour(image, mask, None)
    # Without soil beside the card there is nothing to normalise.
    normalised = correction is not None and correction.within_limit and uncorrected is not None
    corrected = soil_colour(image, mask, correction) if normalised else None
    record: dict[str, object] = {
        "version": CORRECTION_VERSION,
        "edition": reading.edition,
        "reference": "digital-targets",
        "patches": {name: list(rgb) for name, rgb in reading.patches.items()},
        "method": correction.method if correction is not None else None,
        "residual_delta_e": correction.residual_delta_e if correction is not None else None,
        "residual_limit_delta_e": MAX_RESIDUAL_DELTA_E,
        "normalised": normalised,
        "soil_rgb_uncorrected": list(uncorrected[0]) if uncorrected else None,
        "soil_rgb": list(corrected[0]) if corrected else None,
        "soil_lab": list(corrected[1]) if corrected else None,
    }
    if normalised and correction is not None:
        record["matrix"] = [list(row) for row in correction.matrix]
        record["tone_seen"] = [list(row) for row in correction.tone_seen or ()] or None
        record["tone_want"] = [list(row) for row in correction.tone_want or ()] or None
    return record


def evaluate_photo_with_cards(
    raw: bytes,
    *,
    accuracy_m: float | None,
    existing_hashes: tuple[str, ...] = (),
    land_cover: str | None = None,
    priors: dict[str, float] | None = None,
    classifier: SoilClassifier | None = None,
) -> CardQaResult:
    sanitized, camera_metadata = sanitize_jpeg(raw)
    image = cv2.imdecode(np.frombuffer(sanitized, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("photo is not a decodable image")
    cards = find_cards(image)
    region = soil_region_without(image, cards.outlines)
    sharpness_value = sharpness(image, region.mask)
    exposure_value, exposure_ok = exposure_score(image, region.mask)
    x0, y0, x1, y1 = region.crop
    image_hash = perceptual_hash(image[y0:y1, x0:x1])
    unique = all(
        hamming_distance(image_hash, candidate) > NEAR_DUPLICATE_DISTANCE
        for candidate in existing_hashes
    )
    record: dict[str, object] | None
    try:
        record = colour_record(
            image, soil_near_card(region.mask, cards.read_outline), cards.reading
        )
    except Exception:  # noqa: BLE001 - an unreadable card must never cost the photo its QA
        record = None
    gps_score, gps_ok = gps_plausible(accuracy_m, land_cover, priors or {})
    events = [
        QaEvent("soil_region", region.fraction >= SOIL_FRACTION_MIN, round(region.fraction, 4)),
        QaEvent("sharpness", sharpness_value >= SHARPNESS_MIN, sharpness_value),
        QaEvent("exposure", exposure_ok, exposure_value),
        QaEvent("card_detection", True, 1.0 if record else 0.0),
        QaEvent("gps_plausibility", gps_ok, gps_score),
        QaEvent("duplicate", unique, 1.0 if unique else 0.0),
    ]
    if classifier is not None:
        soil_score = classifier.score(image[y0:y1, x0:x1])
        events.append(QaEvent("is_soil", soil_score >= 0.5, soil_score))
    return CardQaResult(
        # The published field keeps its meaning: one reference card's patches were read. It is
        # not a claim of reflectance calibration (SPEC L3); see ``normalised`` in the record.
        calibration_status="calibrated" if record else "uncalibrated",
        camera_metadata=camera_metadata,
        card_color_correction=record,
        card_detected=bool(cards.outlines),
        events=tuple(events),
        perceptual_hash=image_hash,
        sanitized_jpeg=sanitized,
        status=photo_status((event.check_name, event.passed) for event in events),
    )
