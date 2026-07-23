from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image

from card.fixtures import canonical_card
from pipeline.qa import (
    aggregate_submission_status,
    evaluate_photo,
    has_embedded_metadata,
    sanitize_jpeg,
)


def jpeg(image: np.ndarray, *, exif: bool = False) -> bytes:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    output = io.BytesIO()
    kwargs: dict[str, object] = {"format": "JPEG", "quality": 94}
    if exif:
        metadata = Image.Exif()
        metadata[271] = "GSIP camera"
        metadata[272] = "fixture"
        metadata[34665] = {36867: "2026:07:23 00:00:00"}
        metadata[34853] = {1: "GPS"}
        kwargs["exif"] = metadata
    Image.fromarray(rgb).save(output, **kwargs)
    return output.getvalue()


def sharp_fixture() -> bytes:
    image = np.full((900, 900, 3), (105, 90, 70), dtype=np.uint8)
    for offset in range(0, 900, 35):
        cv2.line(image, (offset, 0), (offset, 899), (190, 170, 135), 4)
        cv2.line(image, (0, offset), (899, offset), (35, 45, 55), 3)
    return jpeg(image, exif=True)


def card_fixture() -> bytes:
    return jpeg(canonical_card())


def jpeg_segment(marker: int, payload: bytes) -> bytes:
    return b"\xff" + bytes([marker]) + (len(payload) + 2).to_bytes(2, "big") + payload


def inject_segments(raw: bytes, *segments: bytes) -> bytes:
    return raw[:2] + b"".join(segments) + raw[2:]


def test_sharp_photo_passes_and_strips_location_metadata() -> None:
    result = evaluate_photo(sharp_fixture(), accuracy_m=12, land_cover="cropland")
    assert result.status == "qa_pass"
    assert result.calibration_status == "uncalibrated"
    assert result.camera_metadata == {"make": "GSIP camera", "model": "fixture"}
    assert not has_embedded_metadata(result.sanitized_jpeg)


def test_all_jpeg_metadata_channels_are_stripped_and_detected_independently() -> None:
    comment = jpeg_segment(0xFE, b"GPS 40.446 -79.982 serial=ABC")
    xmp = jpeg_segment(
        0xE1,
        b"http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta>owner</x:xmpmeta>",
    )
    icc = jpeg_segment(0xE2, b"ICC_PROFILE\x00\x01\x01private-profile")
    exif_with_subifd_and_gps = sharp_fixture()
    combined = inject_segments(exif_with_subifd_and_gps, comment, xmp, icc)

    sanitized, metadata = sanitize_jpeg(combined)

    assert metadata == {"make": "GSIP camera", "model": "fixture"}
    assert b"\xff\xfe" not in sanitized
    assert b"http://ns.adobe.com/xap/1.0/" not in sanitized
    assert b"<x:xmpmeta" not in sanitized
    assert b"ICC_PROFILE" not in sanitized
    assert b"Exif\x00\x00" not in sanitized
    assert not has_embedded_metadata(sanitized)

    clean = card_fixture()
    assert has_embedded_metadata(inject_segments(clean, comment))
    assert has_embedded_metadata(inject_segments(clean, xmp))
    assert has_embedded_metadata(inject_segments(clean, icc))
    assert has_embedded_metadata(exif_with_subifd_and_gps)


def test_blurry_photo_fails() -> None:
    image = cv2.GaussianBlur(cv2.imdecode(np.frombuffer(sharp_fixture(), np.uint8), 1), (71, 71), 0)
    assert evaluate_photo(jpeg(image), accuracy_m=12).status == "qa_fail"


def test_card_is_detected_and_color_patches_recorded() -> None:
    result = evaluate_photo(card_fixture(), accuracy_m=12)
    assert result.calibration_status == "calibrated"
    assert result.card_color_correction is not None
    assert "neutral_gray" in result.card_color_correction


def test_implausible_gps_and_near_duplicate_are_flagged() -> None:
    first = evaluate_photo(sharp_fixture(), accuracy_m=12)
    gps = evaluate_photo(sharp_fixture(), accuracy_m=900)
    duplicate = evaluate_photo(
        sharp_fixture(), accuracy_m=12, existing_hashes=(first.perceptual_hash,)
    )
    assert gps.status == "flagged"
    assert duplicate.status == "flagged"


def test_identical_input_is_deterministic() -> None:
    raw = card_fixture()
    first = evaluate_photo(raw, accuracy_m=10)
    second = evaluate_photo(raw, accuracy_m=10)
    assert first == second


def test_submission_status_keeps_the_strictest_photo_result() -> None:
    assert aggregate_submission_status([("duplicate_A", False), ("sharpness_B", True)]) == "flagged"
    assert (
        aggregate_submission_status([("duplicate_A", False), ("sharpness_B", False)]) == "qa_fail"
    )
