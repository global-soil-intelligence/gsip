from __future__ import annotations

import io
import itertools
import struct

import cv2
import numpy as np
import pytest
from PIL import ExifTags, Image, TiffImagePlugin

from card.fixtures import canonical_card
from pipeline.qa import (
    NEAR_DUPLICATE_DISTANCE,
    SHARPNESS_MIN,
    evaluate_photo,
    gps_plausible,
    hamming_distance,
    has_embedded_metadata,
    perceptual_hash,
    photo_status,
    sanitize_jpeg,
    sharpness,
)

FIXTURE_METADATA = {
    "make": "GSIP camera",
    "model": "fixture",
    "focal_length_mm": 5.4,
    "exposure_time_s": pytest.approx(0.008),
    "f_number": 2.8,
    "iso": 400,
    "color_space": "none",
}


def jpeg(image: np.ndarray, *, exif: bool = False) -> bytes:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    output = io.BytesIO()
    if exif:
        metadata = Image.Exif()
        metadata[271] = "GSIP camera"
        metadata[272] = "fixture"
        exif_subifd = metadata.get_ifd(ExifTags.IFD.Exif)
        exif_subifd[37386] = TiffImagePlugin.IFDRational(54, 10)
        exif_subifd[33434] = TiffImagePlugin.IFDRational(1, 125)
        exif_subifd[33437] = TiffImagePlugin.IFDRational(28, 10)
        exif_subifd[34855] = 400
        metadata[ExifTags.IFD.Exif] = exif_subifd
        metadata[34853] = {1: "GPS"}
        Image.fromarray(rgb).save(output, format="JPEG", quality=94, exif=metadata)
    else:
        Image.fromarray(rgb).save(output, format="JPEG", quality=94)
    return output.getvalue()


def sharp_fixture() -> bytes:
    image = np.full((900, 900, 3), (105, 90, 70), dtype=np.uint8)
    for offset in range(0, 900, 35):
        cv2.line(image, (offset, 0), (offset, 899), (190, 170, 135), 4)
        cv2.line(image, (0, offset), (899, offset), (35, 45, 55), 3)
    return jpeg(image, exif=True)


def card_fixture() -> bytes:
    return jpeg(canonical_card())


def soil_texture(seed: int, *, blur: int = 0, height: int = 900, width: int = 1200) -> np.ndarray:
    """Deterministic synthetic soil: low-frequency patches, clods and fine grain (BGR)."""

    rng = np.random.default_rng(seed)
    low = cv2.resize(
        rng.normal(0, 1, (6, 8)).astype(np.float32), (width, height), interpolation=cv2.INTER_CUBIC
    )
    clods = cv2.GaussianBlur(rng.normal(0, 1, (height, width)).astype(np.float32), (0, 0), 3)
    grain = rng.normal(0, 1, (height, width)).astype(np.float32)
    value = (
        0.42
        + 0.10 * low / (np.abs(low).max() + 1e-6)
        + 0.12 * clods / (np.abs(clods).max() + 1e-6)
        + 0.05 * grain
    )
    tint = np.array([0.55, 0.75, 1.0], dtype=np.float32)
    image: np.ndarray = (np.clip(value[..., None] * tint[None, None, :], 0, 1) * 255).astype(
        np.uint8
    )
    if blur:
        image = np.asarray(cv2.GaussianBlur(image, (blur, blur), 0), dtype=np.uint8)
    return image


def place_card(scene: np.ndarray, *, x: int = 40, y: int = 220, width: int = 320) -> np.ndarray:
    card = canonical_card()
    height = round(card.shape[0] * width / card.shape[1])
    resized = cv2.resize(card, (width, height), interpolation=cv2.INTER_AREA)
    composed = scene.copy()
    composed[y : y + height, x : x + width] = resized
    return composed


def jpeg_segment(marker: int, payload: bytes) -> bytes:
    return b"\xff" + bytes([marker]) + (len(payload) + 2).to_bytes(2, "big") + payload


def inject_segments(raw: bytes, *segments: bytes) -> bytes:
    return raw[:2] + b"".join(segments) + raw[2:]


# --- Display P3 test profile ----------------------------------------------------------------

P3_GAMMA = 563 / 256  # u8Fixed8 encoding of 2.2 used by the test profile's TRC tags
BRADFORD = np.array(
    [[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]]
)
D65 = np.array([0.95047, 1.0, 1.08883])
D50 = np.array([0.96422, 1.0, 0.82521])


def _rgb_to_xyz(primaries: list[tuple[float, float]], white: np.ndarray) -> np.ndarray:
    columns = np.array([[x / y, 1.0, (1 - x - y) / y] for x, y in primaries]).T
    scale = np.linalg.solve(columns, white)
    return np.asarray(columns * scale, dtype=np.float64)


def _adapt_d65_to_d50() -> np.ndarray:
    source = BRADFORD @ D65
    target = BRADFORD @ D50
    return np.asarray(np.linalg.inv(BRADFORD) @ np.diag(target / source) @ BRADFORD)


P3_D50 = _adapt_d65_to_d50() @ _rgb_to_xyz([(0.680, 0.320), (0.265, 0.690), (0.150, 0.060)], D65)
SRGB_D50 = _adapt_d65_to_d50() @ _rgb_to_xyz([(0.64, 0.33), (0.30, 0.60), (0.15, 0.06)], D65)


def _s15(value: float) -> bytes:
    return struct.pack(">i", round(value * 65536))


def display_p3_icc() -> bytes:
    """Build a minimal ICC v2.1 display profile: Display P3 primaries, gamma 2.2 curves."""

    def xyz(values: np.ndarray) -> bytes:
        return b"XYZ " + b"\0" * 4 + b"".join(_s15(float(v)) for v in values)

    description = b"Display P3 (GSIP test)\0"
    desc = (
        b"desc"
        + b"\0" * 4
        + struct.pack(">I", len(description))
        + description
        + struct.pack(">II", 0, 0)
        + struct.pack(">HB", 0, 0)
        + b"\0" * 67
    )
    curve = b"curv" + b"\0" * 4 + struct.pack(">IH", 1, 563) + b"\0\0"
    tags = [
        (b"desc", desc),
        (b"wtpt", xyz(D50)),
        (b"rXYZ", xyz(P3_D50[:, 0])),
        (b"gXYZ", xyz(P3_D50[:, 1])),
        (b"bXYZ", xyz(P3_D50[:, 2])),
        (b"rTRC", curve),
        (b"gTRC", curve),
        (b"bTRC", curve),
    ]
    offset = 128 + 4 + 12 * len(tags)
    table = struct.pack(">I", len(tags))
    data = b""
    for signature, payload in tags:
        padded = payload + b"\0" * (-len(payload) % 4)
        table += signature + struct.pack(">II", offset + len(data), len(payload))
        data += padded
    size = offset + len(data)
    header = (
        struct.pack(">I", size)
        + b"lcms"
        + struct.pack(">I", 0x02100000)
        + b"mntrRGB XYZ "
        + struct.pack(">6H", 2026, 10, 10, 0, 0, 0)
        + b"acsp"
        + b"\0" * 24
        + struct.pack(">I", 0)
        + b"".join(_s15(float(v)) for v in D50)
        + b"\0" * 48
    )
    assert len(header) == 128
    return header + table + data


def p3_to_srgb_reference(rgb: tuple[int, int, int]) -> np.ndarray:
    linear = (np.asarray(rgb, dtype=np.float64) / 255.0) ** P3_GAMMA
    srgb_linear = np.clip(np.linalg.solve(SRGB_D50, P3_D50 @ linear), 0, 1)
    encoded = np.where(
        srgb_linear <= 0.0031308,
        12.92 * srgb_linear,
        1.055 * np.power(srgb_linear, 1 / 2.4) - 0.055,
    )
    return np.asarray(np.round(encoded * 255), dtype=np.float64)


# --- Tests ----------------------------------------------------------------------------------


def test_sharp_photo_passes_and_strips_location_metadata() -> None:
    result = evaluate_photo(sharp_fixture(), accuracy_m=12, land_cover="cropland")
    assert result.status == "pass"
    assert result.model_version == "deterministic-v2"
    assert result.calibration_status == "uncalibrated"
    assert result.camera_metadata == FIXTURE_METADATA
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

    # The injected "profile" is not a parsable ICC profile, so it is dropped as "other".
    assert metadata == {**FIXTURE_METADATA, "color_space": "other"}
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
    decoded = cv2.imdecode(np.frombuffer(sharp_fixture(), np.uint8), 1)
    assert decoded is not None
    image = cv2.GaussianBlur(decoded, (71, 71), 0)
    assert evaluate_photo(jpeg(image), accuracy_m=12).status == "fail"


def test_card_is_detected_and_color_patches_recorded() -> None:
    result = evaluate_photo(jpeg(place_card(soil_texture(1))), accuracy_m=12)
    assert result.calibration_status == "calibrated"
    assert result.card_color_correction is not None
    assert "neutral_gray" in result.card_color_correction
    assert result.status == "pass"


def test_sharp_soil_beside_the_card_passes_on_the_soil_region() -> None:
    result = evaluate_photo(jpeg(place_card(soil_texture(2))), accuracy_m=8)
    events = {event.check_name: event for event in result.events}
    assert events["soil_region"].passed
    assert events["soil_region"].score is not None
    assert 0.6 < events["soil_region"].score < 0.95
    assert events["sharpness"].passed
    assert result.status == "pass"


def test_blurred_soil_beside_a_sharp_card_fails_sharpness() -> None:
    composed = place_card(soil_texture(3, blur=31))
    # The whole frame looks sharp because the card is sharp: the v1 gate passed this photo.
    assert sharpness(composed) >= SHARPNESS_MIN

    result = evaluate_photo(jpeg(composed), accuracy_m=8)
    events = {event.check_name: event for event in result.events}
    assert events["soil_region"].passed
    assert not events["sharpness"].passed
    assert events["sharpness"].score is not None
    assert events["sharpness"].score < SHARPNESS_MIN
    assert result.status == "fail"


def test_a_card_only_frame_fails_the_soil_region_check() -> None:
    result = evaluate_photo(card_fixture(), accuracy_m=12)
    events = {event.check_name: event for event in result.events}
    assert result.calibration_status == "calibrated"
    assert not events["soil_region"].passed
    assert result.status == "fail"


def test_different_soils_with_the_card_at_one_pose_are_not_near_duplicates() -> None:
    photos = [jpeg(place_card(soil_texture(seed))) for seed in range(10, 16)]
    # Hashing the whole frame lets the identical card dominate: the v1 gate saw duplicates here.
    decoded = [cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR) for raw in photos]
    whole_frame = [perceptual_hash(image) for image in decoded if image is not None]
    assert len(whole_frame) == len(photos)
    assert (
        min(hamming_distance(a, b) for a, b in itertools.combinations(whole_frame, 2))
        <= NEAR_DUPLICATE_DISTANCE
    )

    hashes = [evaluate_photo(raw, accuracy_m=8).perceptual_hash for raw in photos]
    distances = [hamming_distance(a, b) for a, b in itertools.combinations(hashes, 2)]
    assert min(distances) > NEAR_DUPLICATE_DISTANCE


def test_implausible_gps_and_near_duplicate_are_flagged() -> None:
    first = evaluate_photo(sharp_fixture(), accuracy_m=12)
    gps = evaluate_photo(sharp_fixture(), accuracy_m=900)
    duplicate = evaluate_photo(
        sharp_fixture(), accuracy_m=12, existing_hashes=(first.perceptual_hash,)
    )
    assert gps.status == "flagged"
    assert duplicate.status == "flagged"


def test_missing_accuracy_is_unknown_and_passes() -> None:
    assert gps_plausible(None, "cropland", {}) == (None, True)
    assert gps_plausible(None, "bare", {"soc": 150}) == (None, False)
    result = evaluate_photo(sharp_fixture(), accuracy_m=None)
    gps = next(event for event in result.events if event.check_name == "gps_plausibility")
    assert gps.score is None
    assert gps.passed
    assert result.status == "pass"


def test_exif_orientation_is_applied_before_stripping() -> None:
    pixels = np.zeros((40, 60, 3), dtype=np.uint8)
    pixels[:, :30] = (220, 30, 30)
    pixels[:, 30:] = (30, 30, 220)
    exif = Image.Exif()
    exif[ExifTags.Base.Orientation] = 6  # display requires a 90 degree clockwise rotation
    output = io.BytesIO()
    Image.fromarray(pixels).save(output, format="JPEG", quality=95, exif=exif)

    sanitized, _ = sanitize_jpeg(output.getvalue())

    with Image.open(io.BytesIO(sanitized)) as upright:
        assert upright.size == (40, 60)
        top = np.asarray(upright.convert("RGB"))[10, 20]
        bottom = np.asarray(upright.convert("RGB"))[50, 20]
    assert top[0] > 180 and top[2] < 80
    assert bottom[2] > 180 and bottom[0] < 80
    assert not has_embedded_metadata(sanitized)


def test_type_mismatched_exif_tags_cannot_block_orientation_or_sanitization() -> None:
    pixels = np.zeros((40, 60, 3), dtype=np.uint8)
    pixels[:, :30] = (220, 30, 30)
    pixels[:, 30:] = (30, 30, 220)
    output = io.BytesIO()
    Image.fromarray(pixels).save(output, format="JPEG", quality=95)
    plain = output.getvalue()
    # Orientation 6 plus ResolutionUnit stored as RATIONAL: Pillow's exif_transpose raises
    # struct.error re-serializing this block, which would dead-letter a valid photo.
    entries = struct.pack(">HHI", 0x0112, 3, 1) + struct.pack(">HH", 6, 0)
    entries += struct.pack(">HHII", 0x0128, 5, 1, 38)
    tiff = (
        b"MM\x00\x2a"
        + struct.pack(">I", 8)
        + struct.pack(">H", 2)
        + entries
        + struct.pack(">I", 0)
        + struct.pack(">II", 2, 1)
    )
    payload = b"Exif\x00\x00" + tiff
    raw = plain[:2] + b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload + plain[2:]

    sanitized, metadata = sanitize_jpeg(raw)

    assert metadata == {"color_space": "none"}
    assert not has_embedded_metadata(sanitized)
    with Image.open(io.BytesIO(sanitized)) as upright:
        assert upright.size == (40, 60)
        assert np.asarray(upright.convert("RGB"))[10, 20][0] > 180


def test_display_p3_photos_are_converted_to_srgb_before_stripping() -> None:
    source_rgb = (200, 120, 60)
    pixels = np.full((64, 64, 3), source_rgb, dtype=np.uint8)
    output = io.BytesIO()
    Image.fromarray(pixels).save(
        output, format="JPEG", quality=100, subsampling=0, icc_profile=display_p3_icc()
    )

    sanitized, metadata = sanitize_jpeg(output.getvalue())

    assert metadata["color_space"] == "display_p3"
    assert not has_embedded_metadata(sanitized)
    with Image.open(io.BytesIO(sanitized)) as converted:
        observed = np.asarray(converted.convert("RGB"), dtype=np.float64)[32, 32]
    expected = p3_to_srgb_reference(source_rgb)
    assert np.max(np.abs(observed - expected)) <= 4
    # Reading the P3 values as if they were sRGB would be visibly wrong.
    assert np.max(np.abs(np.asarray(source_rgb, dtype=np.float64) - expected)) > 6


def test_identical_input_is_deterministic() -> None:
    raw = jpeg(place_card(soil_texture(4)))
    first = evaluate_photo(raw, accuracy_m=10)
    second = evaluate_photo(raw, accuracy_m=10)
    assert first == second


def test_photo_status_keeps_the_strictest_check() -> None:
    assert photo_status([("duplicate", False), ("sharpness", True)]) == "flagged"
    assert photo_status([("duplicate", False), ("sharpness", False)]) == "fail"
    assert photo_status([("soil_region", False)]) == "fail"
    assert photo_status([("gps_plausibility", False)]) == "flagged"
    assert photo_status([("card_detection", True), ("exposure", True)]) == "pass"
