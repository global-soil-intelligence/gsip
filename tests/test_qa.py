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


def boundary_jpeg(*, progressive: bool = False, restart_blocks: int = 0) -> bytes:
    pixels = np.random.default_rng(81).integers(0, 256, (48, 64, 3), dtype=np.uint8)
    output = io.BytesIO()
    Image.fromarray(pixels).save(
        output,
        format="JPEG",
        quality=88,
        progressive=progressive,
        restart_marker_blocks=restart_blocks,
    )
    return output.getvalue()


def replace_jfif(raw: bytes, payload: bytes) -> bytes:
    assert raw[2:4] == b"\xff\xe0"
    end = 4 + int.from_bytes(raw[4:6], "big")
    return raw[:2] + jpeg_segment(0xE0, payload) + raw[end:]


@pytest.mark.parametrize("progressive", [False, True])
@pytest.mark.parametrize("restart_blocks", [0, 1])
def test_canonical_boundary_accepts_baseline_progressive_multiscans_and_restarts(
    progressive: bool,
    restart_blocks: int,
) -> None:
    raw = boundary_jpeg(progressive=progressive, restart_blocks=restart_blocks)
    if progressive:
        assert raw.count(b"\xff\xda") > 1
    if restart_blocks:
        assert any(b"\xff" + bytes([marker]) in raw for marker in range(0xD0, 0xD8))
    assert b"\xff\x00" in raw
    assert not has_embedded_metadata(raw)
    with Image.open(io.BytesIO(raw)) as source:
        source.load()


@pytest.mark.parametrize(
    "suffix",
    [b"synthetic-private-trailer", b"synthetic-private-trailer\xff\xd9", b"\x00", b"\xff\xd9"],
)
def test_canonical_boundary_rejects_every_byte_after_the_first_eoi(suffix: bytes) -> None:
    assert has_embedded_metadata(boundary_jpeg() + suffix)


@pytest.mark.parametrize("progressive", [False, True])
def test_canonical_boundary_accepts_standard_marker_fill_bytes(progressive: bool) -> None:
    raw = boundary_jpeg(progressive=progressive)
    first_scan = raw.index(b"\xff\xda")
    filled = raw[:first_scan] + b"\xff\xff" + raw[first_scan:-2] + b"\xff\xff" + raw[-2:]
    assert not has_embedded_metadata(filled)
    with Image.open(io.BytesIO(filled)) as source:
        source.load()


@pytest.mark.parametrize("marker", [0xC8, 0xF0, 0xFD])
def test_canonical_boundary_rejects_private_or_reserved_extension_segments(marker: int) -> None:
    raw = boundary_jpeg()
    app0_end = 4 + int.from_bytes(raw[4:6], "big")
    assert has_embedded_metadata(
        raw[:app0_end] + jpeg_segment(marker, b"synthetic-private-channel") + raw[app0_end:]
    )


def test_canonical_boundary_rejects_concatenated_jpegs() -> None:
    assert has_embedded_metadata(boundary_jpeg() + boundary_jpeg(progressive=True))


@pytest.mark.parametrize("marker", [0xFE, *range(0xE1, 0xF0)])
@pytest.mark.parametrize("progressive", [False, True])
def test_canonical_boundary_rejects_metadata_after_scan_data(
    marker: int, progressive: bool
) -> None:
    raw = boundary_jpeg(progressive=progressive)
    assert has_embedded_metadata(
        raw[:-2] + jpeg_segment(marker, b"synthetic-private-channel") + raw[-2:]
    )


@pytest.mark.parametrize("marker", [0xFE, 0xE1, 0xE2, 0xED])
def test_canonical_boundary_rejects_metadata_between_progressive_scans(marker: int) -> None:
    raw = boundary_jpeg(progressive=True)
    second_scan = raw.index(b"\xff\xda", raw.index(b"\xff\xda") + 2)
    assert has_embedded_metadata(
        raw[:second_scan] + jpeg_segment(marker, b"synthetic-private-channel") + raw[second_scan:]
    )


@pytest.mark.parametrize(
    "payload",
    [
        b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00synthetic-private-channel",
        b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x01\x01\x10\x20\x30",
        b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x01\x00",
        b"JFIF\x00\x02\x00\x00\x00\x01\x00\x01\x00\x00",
        b"JFIF\x00\x01\x03\x00\x00\x01\x00\x01\x00\x00",
        b"JFIF\x00\x01\x01\x03\x00\x01\x00\x01\x00\x00",
        b"JFIF\x00\x01\x01\x00\x00\x00\x00\x01\x00\x00",
        b"JFIF\x00\x01\x01\x00\x00\x01\x00\x00\x00\x00",
        b"JFXX\x00\x10" + b"synthetic-thumbnail",
    ],
)
def test_canonical_boundary_rejects_noncanonical_app0(payload: bytes) -> None:
    assert has_embedded_metadata(replace_jfif(boundary_jpeg(), payload))


def test_canonical_boundary_preserves_unreadable_short_jfif_refusal() -> None:
    # Some pixel decoders ignore a truncated JFIF header. Pillow refuses it; preserve
    # the shared API's unreadable-image error rather than treating it as clean.
    with pytest.raises((OSError, ValueError)):
        has_embedded_metadata(replace_jfif(boundary_jpeg(), b"JFIF\x00"))


@pytest.mark.parametrize("version", [0, 1, 2])
@pytest.mark.parametrize("units", [0, 1, 2])
def test_canonical_boundary_rejects_even_standard_noncanonical_jfif_fields(
    version: int, units: int
) -> None:
    payload = b"JFIF\x00" + bytes([1, version, units]) + b"\x00\x48\x00\x48\x00\x00"
    assert has_embedded_metadata(replace_jfif(boundary_jpeg(), payload))


def test_canonical_boundary_accepts_the_exact_sanitizer_jfif_and_no_app0() -> None:
    for progressive in (False, True):
        raw = boundary_jpeg(progressive=progressive)
        assert raw[6:20] == b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        assert not has_embedded_metadata(raw)
        end = 4 + int.from_bytes(raw[4:6], "big")
        without_app0 = raw[:2] + raw[end:]
        assert not has_embedded_metadata(without_app0)
        with (
            Image.open(io.BytesIO(raw)) as expected,
            Image.open(io.BytesIO(without_app0)) as actual,
        ):
            assert np.array_equal(np.asarray(actual), np.asarray(expected))


@pytest.mark.parametrize("marker", [0xDD, 0xDB, 0xC4])
@pytest.mark.parametrize("extra", [b"", b"\x00", bytes(17), b"synthetic-private-channel"])
def test_canonical_boundary_rejects_all_table_or_control_payload_after_final_scan(
    marker: int,
    extra: bytes,
) -> None:
    payload = {
        0xDD: b"\x00\x00",
        0xDB: b"\x03" + bytes([1]) * 64,
        0xC4: b"\x13" + bytes([0, 2] + [0] * 14) + b"\x01\x02",
    }[marker]
    raw = boundary_jpeg()
    assert has_embedded_metadata(raw[:-2] + jpeg_segment(marker, payload + extra) + raw[-2:])


@pytest.mark.parametrize("marker", [0xDD, 0xDB, 0xC4])
@pytest.mark.parametrize("extra", [b"\x00", bytes(17), b"synthetic-private-channel"])
def test_canonical_boundary_rejects_surplus_inside_pre_scan_table_or_control(
    marker: int,
    extra: bytes,
) -> None:
    payload = {
        0xDD: b"\x00\x00",
        0xDB: b"\x03" + bytes([1]) * 64,
        0xC4: b"\x13" + bytes([0, 2] + [0] * 14) + b"\x01\x02",
    }[marker]
    raw = boundary_jpeg()
    end = 4 + int.from_bytes(raw[4:6], "big")
    dirty = raw[:end] + jpeg_segment(marker, payload + extra) + raw[end:]
    try:
        rejected = has_embedded_metadata(dirty)
    except (OSError, ValueError):
        rejected = True  # Preserve undecodable-source refusal, never clean acceptance.
    assert rejected


@pytest.mark.parametrize("marker,payload", [(0xDC, b"\x00\x30"), (0xCC, b"\x00\x10")])
@pytest.mark.parametrize("position", ["before_frame", "after_scan"])
@pytest.mark.parametrize("extra", [b"", b"synthetic-private-channel"])
def test_canonical_boundary_refuses_unsupported_dnl_and_dac(
    marker: int,
    payload: bytes,
    position: str,
    extra: bytes,
) -> None:
    raw = boundary_jpeg()
    offset = 4 + int.from_bytes(raw[4:6], "big") if position == "before_frame" else len(raw) - 2
    dirty = raw[:offset] + jpeg_segment(marker, payload + extra) + raw[offset:]
    try:
        rejected = has_embedded_metadata(dirty)
    except (OSError, ValueError):
        rejected = True
    assert rejected


@pytest.mark.parametrize(
    "marker,payload",
    [
        (0xDB, b"\x23" + bytes([1]) * 64),  # Unsupported precision.
        (0xDB, b"\x04" + bytes([1]) * 64),  # Unsupported table destination.
        (0xDB, b"\x13" + bytes([1]) * 64),  # Truncated 16-bit table.
        (0xDB, b"\x03" + bytes([1]) * 63),
        (0xC4, b"\x23" + bytes([0, 2] + [0] * 14) + b"\x01\x02"),
        (0xC4, b"\x14" + bytes([0, 2] + [0] * 14) + b"\x01\x02"),
        (0xC4, b"\x13" + bytes([0, 2] + [0] * 14) + b"\x01"),
        (0xC4, b"\x13" + bytes(16)),
        (0xDD, b"\x00"),
        (0xDB, b"\x03" + bytes(64)),  # Zero is not a quantization value.
        (0xDB, b"\x13" + bytes([0, 1]) * 63 + b"\x00\x00"),
        (0xC4, b"\x13" + bytes([3] + [0] * 15) + b"\x01\x02\x03"),  # Oversubscribed.
        (0xC4, b"\x13" + bytes([2] + [0] * 15) + b"\x01\x02"),  # All-ones code.
        (0xDB, b"\x03" + bytes([1]) * 64 + b"\x02\x01"),  # Incomplete second table.
        (0xC4, b"\x13" + bytes([0, 2] + [0] * 14) + b"\x01\x02\x12\x01"),
    ],
)
def test_canonical_boundary_rejects_incomplete_or_unsupported_table_entries(
    marker: int, payload: bytes
) -> None:
    raw = boundary_jpeg()
    end = 4 + int.from_bytes(raw[4:6], "big")
    dirty = raw[:end] + jpeg_segment(marker, payload) + raw[end:]
    try:
        rejected = has_embedded_metadata(dirty)
    except (OSError, ValueError):
        rejected = True
    assert rejected


def test_canonical_boundary_accepts_restart_control_before_another_progressive_scan() -> None:
    raw = boundary_jpeg(progressive=True)
    second_scan = raw.index(b"\xff\xda", raw.index(b"\xff\xda") + 2)
    with_table = raw[:second_scan] + jpeg_segment(0xDD, b"\x00\x00") + raw[second_scan:]
    assert not has_embedded_metadata(with_table)
    with Image.open(io.BytesIO(raw)) as expected, Image.open(io.BytesIO(with_table)) as actual:
        assert np.array_equal(np.asarray(actual), np.asarray(expected))


@pytest.mark.parametrize(
    "marker,payload",
    [
        (0xDB, b"\x03synthetic-private-channel" + bytes([1]) * 39),
        (0xC4, b"\x13" + bytes([0, 0, 4] + [0] * 13) + b"site"),
        (0xDB, b"\x00synthetic-private-channel" + bytes([1]) * 39),
        (0xC4, b"\x10" + bytes([0, 0, 4] + [0] * 13) + b"site"),
    ],
)
def test_canonical_boundary_rejects_unused_or_overwritten_pre_scan_definitions(
    marker: int, payload: bytes
) -> None:
    raw = boundary_jpeg()
    app0_end = 4 + int.from_bytes(raw[4:6], "big")
    dirty = raw[:app0_end] + jpeg_segment(marker, payload) + raw[app0_end:]
    assert has_embedded_metadata(dirty)
    with Image.open(io.BytesIO(raw)) as expected, Image.open(io.BytesIO(dirty)) as actual:
        assert np.array_equal(np.asarray(actual), np.asarray(expected))


def test_canonical_boundary_rejects_quantization_overwritten_after_sof_before_first_scan() -> None:
    raw = boundary_jpeg()
    first_scan = raw.index(b"\xff\xda")
    replacement = jpeg_segment(0xDB, b"\x00" + bytes([1]) * 64)
    assert has_embedded_metadata(raw[:first_scan] + replacement + raw[first_scan:])


@pytest.mark.parametrize("marker", [0xDB, 0xC4])
def test_canonical_boundary_rejects_unused_definitions_between_progressive_scans(
    marker: int,
) -> None:
    raw = boundary_jpeg(progressive=True)
    second_scan = raw.index(b"\xff\xda", raw.index(b"\xff\xda") + 2)
    payload = (
        b"\x03" + bytes([1]) * 64
        if marker == 0xDB
        else b"\x13" + bytes([0, 2] + [0] * 14) + b"\x01\x02"
    )
    assert has_embedded_metadata(
        raw[:second_scan] + jpeg_segment(marker, payload) + raw[second_scan:]
    )


def test_canonical_boundary_rejects_quantization_redefinition_after_component_use() -> None:
    raw = boundary_jpeg(progressive=True)
    second_scan = raw.index(b"\xff\xda", raw.index(b"\xff\xda") + 2)
    replacement = jpeg_segment(0xDB, b"\x00" + bytes([1]) * 64)
    assert has_embedded_metadata(raw[:second_scan] + replacement + raw[second_scan:])


@pytest.mark.parametrize("scan_kind", ["initial_dc", "dc_refinement", "ac"])
def test_canonical_boundary_does_not_consume_huffman_tables_from_unused_selector_fields(
    scan_kind: str,
) -> None:
    raw = boundary_jpeg(progressive=True)
    # Producer SOS markers are outside length payloads in this fixture. Find the actual
    # scan mode before inserting a complete table the decoder will not use there.
    scans = [offset for offset in range(len(raw)) if raw[offset : offset + 2] == b"\xff\xda"]
    for scan in scans:
        length = int.from_bytes(raw[scan + 2 : scan + 4], "big")
        payload = bytearray(raw[scan + 4 : scan + 2 + length])
        start, _, approximation = payload[-3:]
        high = approximation >> 4
        if (
            (scan_kind == "initial_dc" and start == 0 and not high)
            or (scan_kind == "dc_refinement" and start == 0 and high)
            or (scan_kind == "ac" and start > 0)
        ):
            if scan_kind == "initial_dc":
                table_class = 0x13
                payload[2] |= 3  # AC selector is ignored in a DC-only scan.
            elif scan_kind == "ac":
                table_class = 0x03
                payload[2] |= 0x30  # DC selector is ignored in an AC-only scan.
            else:
                table_class = 0x00  # Refinement uses no DC Huffman table, even selector0.
            table = jpeg_segment(0xC4, bytes([table_class, 0, 2] + [0] * 14) + b"\x01\x02")
            dirty = (
                raw[:scan] + table + jpeg_segment(0xDA, bytes(payload)) + raw[scan + 2 + length :]
            )
            assert has_embedded_metadata(dirty)
            return
    pytest.fail("the producer fixture did not contain the intended progressive scan")


@pytest.mark.parametrize("marker", [0xDB, 0xC4])
@pytest.mark.parametrize("progressive", [False, True])
def test_canonical_boundary_accepts_complete_multi_entry_tables_used_by_scans(
    marker: int, progressive: bool
) -> None:
    raw = boundary_jpeg(progressive=progressive)
    start = raw.index(b"\xff" + bytes([marker]))
    end = start
    payload = b""
    entries = 0
    while raw[end : end + 2] == b"\xff" + bytes([marker]):
        length = int.from_bytes(raw[end + 2 : end + 4], "big")
        payload += raw[end + 4 : end + 2 + length]
        end += 2 + length
        entries += 1
    assert entries >= 2
    merged = raw[:start] + jpeg_segment(marker, payload) + raw[end:]
    assert not has_embedded_metadata(merged)
    with Image.open(io.BytesIO(raw)) as expected, Image.open(io.BytesIO(merged)) as actual:
        assert np.array_equal(np.asarray(actual), np.asarray(expected))


@pytest.mark.parametrize("progressive", [False, True])
def test_canonical_boundary_accepts_complete_consumed_16_bit_quantization_tables(
    progressive: bool,
) -> None:
    output = io.BytesIO()
    Image.new("RGB", (32, 32), (20, 80, 120)).save(
        output, format="JPEG", qtables=[[500] + [257] * 63], progressive=progressive
    )
    raw = output.getvalue()
    table = raw.index(b"\xff\xdb")
    assert raw[table + 4] >> 4 == 1
    assert not has_embedded_metadata(raw)
    with Image.open(io.BytesIO(raw)) as image:
        image.load()


@pytest.mark.parametrize("entropy", [b"", b"\x00", b"synthetic-private-channel"])
def test_canonical_boundary_rejects_duplicate_sequential_scans_with_ignored_tables(
    entropy: bytes,
) -> None:
    raw = boundary_jpeg()
    scan = raw.index(b"\xff\xda")
    end = scan + 2 + int.from_bytes(raw[scan + 2 : scan + 4], "big")
    table = jpeg_segment(0xC4, b"\x10" + bytes([0, 0, 4] + [0] * 13) + b"site")
    dirty = raw[:-2] + table + raw[scan:end] + entropy + raw[-2:]
    assert has_embedded_metadata(dirty)
    # The pipeline's pixel decoder ignores this extra scan, even though Pillow.load
    # rejects it. The shared boundary must reject before that permissive decoder runs.
    expected = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    actual = cv2.imdecode(np.frombuffer(dirty, np.uint8), cv2.IMREAD_COLOR)
    assert expected is not None and actual is not None
    assert np.array_equal(actual, expected)


@pytest.mark.parametrize("progressive", [False, True])
def test_canonical_boundary_rejects_empty_scan_headers_as_definition_consumption(
    progressive: bool,
) -> None:
    raw = boundary_jpeg(progressive=progressive)
    scan = raw.index(b"\xff\xda")
    end = scan + 2 + int.from_bytes(raw[scan + 2 : scan + 4], "big")
    assert has_embedded_metadata(raw[:end] + raw[-2:])


@pytest.mark.parametrize("scan_kind", ["dc", "ac", "refinement"])
def test_canonical_boundary_rejects_repeated_progressive_initialization_and_refinement(
    scan_kind: str,
) -> None:
    raw = boundary_jpeg(progressive=True)
    scans = [offset for offset in range(len(raw)) if raw[offset : offset + 2] == b"\xff\xda"]
    scan = scans[0] if scan_kind == "dc" else scans[1] if scan_kind == "ac" else scans[-1]
    end = scan + 2 + int.from_bytes(raw[scan + 2 : scan + 4], "big")
    table_class = 0x00 if scan_kind == "dc" else 0x10
    table = jpeg_segment(0xC4, bytes([table_class, 1] + [0] * 15 + [0]))
    assert has_embedded_metadata(raw[:-2] + table + raw[scan:end] + b"\x00" + raw[-2:])


@pytest.mark.parametrize("scan_kind", ["uninitialized_dc", "skipped_refinement_bitplane"])
def test_canonical_boundary_rejects_impossible_progressive_refinement_history(
    scan_kind: str,
) -> None:
    raw = boundary_jpeg(progressive=True)
    scans = [offset for offset in range(len(raw)) if raw[offset : offset + 2] == b"\xff\xda"]
    scan = scans[0] if scan_kind == "uninitialized_dc" else scans[-1]
    end = scan + 2 + int.from_bytes(raw[scan + 2 : scan + 4], "big")
    payload = bytearray(raw[scan + 4 : end])
    payload[-1] = 0x10 if scan_kind == "uninitialized_dc" else 0x21
    dirty = raw[:scan] + jpeg_segment(0xDA, bytes(payload)) + raw[end:]
    assert has_embedded_metadata(dirty)


def test_canonical_boundary_rejects_progressive_ac_before_component_dc() -> None:
    raw = boundary_jpeg(progressive=True)
    first = raw.index(b"\xff\xda")
    second = raw.index(b"\xff\xda", first + 2)
    second_end = second + 2 + int.from_bytes(raw[second + 2 : second + 4], "big")
    table = jpeg_segment(0xC4, bytes([0x10, 1] + [0] * 15 + [0]))
    dirty = raw[:first] + table + raw[second:second_end] + b"\x00" + raw[first:]
    assert has_embedded_metadata(dirty)


def test_canonical_boundary_accepts_valid_coarse_progressive_dc_only_interchange() -> None:
    raw = boundary_jpeg(progressive=True)
    first = raw.index(b"\xff\xda")
    first_end = first + 2 + int.from_bytes(raw[first + 2 : first + 4], "big")
    # The producer's first complete DC scan ends at its next DHT. End the image there,
    # before that unused AC definition: partial/coarse progressive JPEG remains valid.
    next_definition = raw.index(b"\xff\xc4", first_end)
    assert next_definition > first_end
    coarse = raw[:next_definition] + raw[-2:]
    assert not has_embedded_metadata(coarse)
    with Image.open(io.BytesIO(coarse)) as image:
        image.load()
        assert image.size == (64, 48)


def test_canonical_boundary_rejects_duplicate_or_late_app0() -> None:
    raw = boundary_jpeg()
    app0_end = 4 + int.from_bytes(raw[4:6], "big")
    app0 = raw[2:app0_end]
    assert has_embedded_metadata(raw[:app0_end] + app0 + raw[app0_end:])
    assert has_embedded_metadata(raw[:-2] + app0 + raw[-2:])


def test_canonical_boundary_tracks_segment_lengths_instead_of_raw_eoi_search() -> None:
    raw = boundary_jpeg(progressive=True)
    start = raw.index(b"\xff\xdb")
    end = start + 2 + int.from_bytes(raw[start + 2 : start + 4], "big")
    # Replace an actually consumed 8-bit table0; its first two values happen to be FFD9.
    # No unused/overwritten definition is necessary to prove length-aware EOI handling.
    assert raw[start + 4] == 0
    table = jpeg_segment(0xDB, b"\x00\xff\xd9" + bytes([1]) * 62)
    with_table = raw[:start] + table + raw[end:]
    assert not has_embedded_metadata(with_table)
    with Image.open(io.BytesIO(with_table)) as actual:
        actual.load()
    # A metadata segment after the real final scan remains visible past the payload decoy.
    assert has_embedded_metadata(
        with_table[:-2] + jpeg_segment(0xFE, b"synthetic-private-channel") + with_table[-2:]
    )


@pytest.mark.parametrize(
    "suffix", [b"", b"\xff", b"\xff\x00", b"\xff\xe1\x00", b"\xff\xe1\x00\x01", b"\xff\xe1\xff\xff"]
)
def test_canonical_boundary_rejects_truncated_entropy_and_segment_lengths(suffix: bytes) -> None:
    assert has_embedded_metadata(boundary_jpeg()[:-2] + suffix)


@pytest.mark.parametrize(
    "raw", [b"", b"\xff\xd8", b"\xff\xd8\xff\xd9", b"\xff\xd8synthetic-private-channel\xff\xd9"]
)
def test_canonical_boundary_preserves_unreadable_image_refusal(raw: bytes) -> None:
    with pytest.raises((OSError, ValueError)):
        has_embedded_metadata(raw)


def test_non_jpeg_publish_ready_input_fails_closed_but_private_sanitize_still_reencodes() -> None:
    output = io.BytesIO()
    Image.new("RGB", (16, 16), (50, 80, 120)).save(output, format="PNG")
    raw = output.getvalue()
    assert has_embedded_metadata(raw)
    sanitized, _ = sanitize_jpeg(raw)
    assert not has_embedded_metadata(sanitized)
    assert sanitized.startswith(b"\xff\xd8") and sanitized.endswith(b"\xff\xd9")


def test_stronger_boundary_preserves_the_exact_existing_sanitizer_representation() -> None:
    raw = boundary_jpeg()
    with Image.open(io.BytesIO(raw)) as source:
        source.load()
        clean = source.convert("RGB")
        clean.info.clear()
        expected = io.BytesIO()
        clean.save(expected, format="JPEG", quality=92, optimize=True, comment=b"")
    actual, _ = sanitize_jpeg(raw)
    assert actual == expected.getvalue()


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
