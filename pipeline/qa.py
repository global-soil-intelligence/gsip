from __future__ import annotations

import hashlib
import io
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np
from PIL import ExifTags, Image, ImageCms

from card.validate import card_corners, card_transform, extract_patches

Image.MAX_IMAGE_PIXELS = 40_000_000

QA_MODEL_VERSION = "deterministic-v2"

ALLOWED_EXIF = {
    "Make": "make",
    "Model": "model",
    "FocalLength": "focal_length_mm",
    "ExposureTime": "exposure_time_s",
    "FNumber": "f_number",
    "ISOSpeedRatings": "iso",
    "PhotographicSensitivity": "iso",
}
SHARPNESS_MIN = 55.0
MAX_CLIPPED_FRACTION = 0.28
MAX_GPS_ACCURACY_M = 250.0
NEAR_DUPLICATE_DISTANCE = 5
# SPEC section 5: at least 20 % of the frame must remain as soil once the card is masked.
SOIL_FRACTION_MIN = 0.20
# The card polygon is projected from the marker alone, so mask it with a generous margin.
CARD_MASK_SCALE = 1.12
# Keep sharpness away from the mask boundary, where the card edge would add false detail.
SHARPNESS_EROSION_PX = 7

FAILING_CHECKS = ("soil_region", "sharpness", "exposure", "is_soil")
EXIF_ORIENTATION_TAG = 0x0112
# EXIF orientation -> the transpose that makes the pixels upright (as Pillow's exif_transpose).
ORIENTATION_TRANSPOSE = {
    2: Image.Transpose.FLIP_LEFT_RIGHT,
    3: Image.Transpose.ROTATE_180,
    4: Image.Transpose.FLIP_TOP_BOTTOM,
    5: Image.Transpose.TRANSPOSE,
    6: Image.Transpose.ROTATE_270,
    7: Image.Transpose.TRANSVERSE,
    8: Image.Transpose.ROTATE_90,
}
REVIEW_CHECKS = ("gps_plausibility", "duplicate")


class MetadataSurvived(ValueError):
    """Metadata survived sanitization: a privacy failure that must stop any release."""


class SoilClassifier(Protocol):
    """Phase 2 seam; the deterministic gate deliberately supplies no classifier."""

    def score(self, image: np.ndarray) -> float: ...


@dataclass(frozen=True)
class QaEvent:
    check_name: str
    passed: bool
    score: float | None


@dataclass(frozen=True, eq=False)
class SoilRegion:
    """Pixels that count as soil once the reference card (plus a margin) is masked out."""

    card_found: bool
    crop: tuple[int, int, int, int]
    fraction: float
    mask: np.ndarray


@dataclass(frozen=True)
class QaResult:
    calibration_status: str
    camera_metadata: dict[str, float | int | str]
    card_color_correction: dict[str, tuple[int, int, int]] | None
    events: tuple[QaEvent, ...]
    perceptual_hash: str
    sanitized_jpeg: bytes
    status: str
    model_version: str = QA_MODEL_VERSION


def _number(value: object) -> float | int | str | None:
    if isinstance(value, (int, float, str)):
        return value
    numerator = getattr(value, "numerator", None)
    denominator = getattr(value, "denominator", None)
    if isinstance(numerator, int) and isinstance(denominator, int) and denominator:
        return numerator / denominator
    return None


def _upright(image: Image.Image) -> Image.Image:
    """Apply the EXIF orientation to the pixels without re-serializing the EXIF block.

    Pillow's exif_transpose rewrites the EXIF data and raises on type-mismatched tags, which
    would dead-letter a valid photo; reading one integer tag cannot.
    """

    try:
        orientation = image.getexif().get(EXIF_ORIENTATION_TAG)
    except Exception:  # hostile EXIF must never block sanitization; orientation is optional
        orientation = None
    method = ORIENTATION_TRANSPOSE.get(orientation) if isinstance(orientation, int) else None
    return image.transpose(method) if method is not None else image


def _color_space_class(description: str) -> str:
    lowered = description.lower()
    if "p3" in lowered:
        return "display_p3"
    if "srgb" in lowered:
        return "srgb"
    return "other"


def _to_srgb(image: Image.Image, icc_profile: bytes | None) -> tuple[Image.Image, str]:
    """Convert to 8-bit sRGB using the embedded profile when there is one.

    Returns the converted image and a colour-space class. Phones increasingly embed Display P3
    profiles; dropping the profile without converting would misread every colour.
    """

    if not icc_profile:
        return image.convert("RGB"), "none"
    try:
        source_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
        description = str(ImageCms.getProfileDescription(source_profile) or "")  # type: ignore[no-untyped-call]
    except (OSError, ImageCms.PyCMSError):
        return image.convert("RGB"), "other"
    working = image if image.mode in {"RGB", "CMYK", "L"} else image.convert("RGB")
    try:
        converted = ImageCms.profileToProfile(
            working,
            source_profile,
            ImageCms.createProfile("sRGB"),
            renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
            outputMode="RGB",
        )
    except (OSError, ValueError, ImageCms.PyCMSError):
        return image.convert("RGB"), "other"
    if converted is None:  # pragma: no cover - profileToProfile returns None only in-place
        return image.convert("RGB"), "other"
    return converted, _color_space_class(description)


def sanitize_jpeg(raw: bytes) -> tuple[bytes, dict[str, float | int | str]]:
    """Re-encode a JPEG with no metadata, upright and in sRGB.

    Orientation and colour profile are applied to the pixels before every metadata channel is
    dropped, and only the allowlisted camera fields plus a colour-space class are returned.
    """

    with Image.open(io.BytesIO(raw)) as source:
        source.verify()
    with Image.open(io.BytesIO(raw)) as source:
        metadata: dict[str, float | int | str] = {}
        exif = source.getexif()
        for fields in (exif.items(), exif.get_ifd(ExifTags.IFD.Exif).items()):
            for tag_id, value in fields:
                destination = ALLOWED_EXIF.get(ExifTags.TAGS.get(tag_id, ""))
                normalized = _number(value)
                if destination and normalized is not None:
                    metadata[destination] = normalized
        icc_profile = source.info.get("icc_profile")
        upright = _upright(source)
        clean, color_space = _to_srgb(
            upright, icc_profile if isinstance(icc_profile, bytes) else None
        )
        metadata["color_space"] = color_space
        clean.info.clear()
        output = io.BytesIO()
        clean.save(output, format="JPEG", quality=92, optimize=True, comment=b"")
    sanitized = output.getvalue()
    if has_embedded_metadata(sanitized):
        raise MetadataSurvived("sanitized photo still contains metadata")
    return sanitized, metadata


def has_embedded_metadata(image_bytes: bytes) -> bool:
    """Fail closed unless one complete JPEG has only canonical metadata-free channels.

    Input sanitization still accepts/re-encodes supported source formats. This check is for
    the exact publish-ready representation; it does not prove the producer or prevent image
    steganography. Marker/table/scan-header checks are structural, not a complete Huffman
    entropy-bit validator. Pixel/codec decoding remains the caller's separate check.
    """

    # Preserve unreadable-image errors for callers that set an unreadable photo aside.
    # Readable non-JPEGs and unsafe JPEG streams are dirty postcanonical representations.
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.format != "JPEG" or image.getexif():
            return True
        if any(
            key.lower() in {"comment", "exif", "icc_profile", "xmp", "xml"} for key in image.info
        ):
            return True
    if _has_forbidden_jpeg_segment(image_bytes):
        return True
    lowered = image_bytes.lower()
    return b"http://ns.adobe.com/xap/1.0/" in lowered or b"<x:xmpmeta" in lowered


def _has_forbidden_jpeg_segment(image_bytes: bytes) -> bool:
    """Walk marker lengths and every entropy-coded scan, including the true final EOI.

    ITU T.81 Annex B defines length-delimited segments, FF fill, FF00 stuffing and
    standalone restart/EOI markers. Length payloads can contain FFD9: searching raw bytes
    for EOI would truncate a valid table. JFIF 1.02 specifies APP0 fields; our sole allowed
    APP0 is the exact thumbnail-free 14-byte JFIF header emitted by sanitize_jpeg.
    """

    if not image_bytes.startswith(b"\xff\xd8"):
        return True
    # Keep this fixed: variable versions, densities and thumbnails are metadata channels.
    canonical_jfif = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    # Huffman DCT baseline, sequential and progressive frames only. DNL, DAC,
    # arithmetic/lossless frames and extension payloads have no canonical producer here.
    frame_markers = {0xC0, 0xC1, 0xC2}
    table_markers = {0xC4, 0xDB, 0xDD}
    cursor = 2
    in_scan = False
    saw_frame = False
    saw_scan = False
    progressive = False
    components: dict[int, int] = {}
    scanned_components: set[int] = set()
    coefficient_bits: dict[int, list[int | None]] = {}
    defined_tables: set[tuple[int, int]] = set()
    pending_tables: set[tuple[int, int]] = set()
    active_tables: set[tuple[int, int]] = set()
    active_components: set[int] = set()
    scan_has_entropy = False
    first_marker = True
    while cursor < len(image_bytes):
        if in_scan:
            next_marker = image_bytes.find(b"\xff", cursor)
            if next_marker < 0:
                return True
            if next_marker > cursor:
                scan_has_entropy = True
            cursor = next_marker
        elif image_bytes[cursor] != 0xFF:
            return True  # Unframed bytes between length-delimited segments.
        marker_start = cursor
        while cursor < len(image_bytes) and image_bytes[cursor] == 0xFF:
            cursor += 1
        if cursor >= len(image_bytes):
            return True
        marker = image_bytes[cursor]
        cursor += 1
        if in_scan and marker == 0x00:
            # A stuffed FF is exactly FF00; extra FF bytes only precede real markers.
            if cursor != marker_start + 2:
                return True
            scan_has_entropy = True
            continue
        if in_scan and 0xD0 <= marker <= 0xD7:
            continue
        if in_scan:
            if not scan_has_entropy:
                return True  # A bare SOS header cannot consume a pending definition.
            pending_tables.difference_update(active_tables)
            scanned_components.update(active_components)
            in_scan = False
        if marker == 0xD9:
            return not (
                saw_frame
                and saw_scan
                and not pending_tables
                and scanned_components == set(components)
                and cursor == len(image_bytes)
            )
        # Nested SOI, bare restart/TEM and reserved/private extension markers are not
        # supported canonical image syntax. Every other accepted marker has a length.
        if marker not in frame_markers | table_markers | {0xDA, 0xE0}:
            return True
        if cursor + 2 > len(image_bytes):
            return True
        length = int.from_bytes(image_bytes[cursor : cursor + 2], "big")
        if length < 2 or cursor + length > len(image_bytes):
            return True
        payload = image_bytes[cursor + 2 : cursor + length]
        cursor += length
        if marker == 0xE0:
            if not first_marker or payload != canonical_jfif:
                return True
        elif marker in table_markers:
            destinations = _jpeg_table_destinations(marker, payload)
            if destinations is None or (marker == 0xDB and saw_scan):
                return True
            for destination in destinations:
                table = (marker, destination)
                if table in pending_tables:
                    return True  # Replaced before any scan actually consumed this definition.
                defined_tables.add(table)
                pending_tables.add(table)
        elif marker in frame_markers:
            if saw_frame or len(payload) < 6 or not 1 <= payload[5] <= 4:
                return True
            if len(payload) != 6 + 3 * payload[5]:
                return True
            if payload[0] not in ({8} if marker == 0xC0 else {8, 12}):
                return True
            if not int.from_bytes(payload[1:3], "big") or not int.from_bytes(payload[3:5], "big"):
                return True  # DNL-delayed dimensions are outside this canonical profile.
            for offset in range(6, len(payload), 3):
                component, sampling, quantization = payload[offset : offset + 3]
                if component in components or quantization > 3:
                    return True
                if not 1 <= sampling >> 4 <= 4 or not 1 <= sampling & 0x0F <= 4:
                    return True
                components[component] = quantization
                coefficient_bits[component] = [None] * 64
            progressive = marker == 0xC2
            saw_frame = True
        elif marker == 0xDA:
            if not saw_frame or not payload or not 1 <= payload[0] <= 4:
                return True
            if len(payload) != 4 + 2 * payload[0]:
                return True
            start, end, approximation = payload[-3:]
            high, low = approximation >> 4, approximation & 0x0F
            if progressive:
                if not 0 <= start <= end <= 63 or high > 13 or low > 13:
                    return True
                if (start == 0 and end != 0) or (start > 0 and payload[0] != 1):
                    return True
                if high and high != low + 1:
                    return True
            elif (start, end, approximation) != (0, 63, 0):
                return True
            scan_components: set[int] = set()
            required_tables: set[tuple[int, int]] = set()
            for offset in range(1, 1 + 2 * payload[0], 2):
                component, selectors = payload[offset : offset + 2]
                if component not in components or component in scan_components:
                    return True
                dc, ac = selectors >> 4, selectors & 0x0F
                if dc > 3 or ac > 3:
                    return True
                scan_components.add(component)
                required_tables.add((0xDB, components[component]))
                if not progressive:
                    required_tables.update({(0xC4, dc), (0xC4, 0x10 | ac)})
                elif start == 0:
                    if ac or (high and dc):
                        return True  # Unused selector fields must be zero.
                    if not high:
                        required_tables.add((0xC4, dc))
                else:
                    if dc:
                        return True
                    required_tables.add((0xC4, 0x10 | ac))
            if not required_tables <= defined_tables:
                return True
            if not progressive:
                if scan_components & scanned_components:
                    return True  # Sequential components are encoded once, never ignored repeats.
            else:
                for component in scan_components:
                    bits = coefficient_bits[component]
                    if start > 0 and bits[0] is None:
                        return True  # A component's initial DC scan must precede its AC scans.
                    for coefficient in range(start, end + 1):
                        previous = bits[coefficient]
                        if (not high and previous is not None) or (high and previous != high):
                            return True  # No repeated initialization or impossible refinement.
                        bits[coefficient] = low
            # Commit actual definition consumption only after this valid scan has entropy.
            # DC refinement has no Huffman table; AC scans use only their AC tables.
            active_tables = required_tables | {(0xDD, 0)}
            active_components = scan_components
            scan_has_entropy = False
            saw_scan = True
            in_scan = True
        first_marker = False
    return True  # Missing final EOI, even if a permissive decoder can show pixels.


def _jpeg_table_destinations(marker: int, payload: bytes) -> tuple[int, ...] | None:
    """Consume complete T.81 DQT/DHT entries or the exact two-byte DRI control.

    A length-valid segment is insufficient: decoders can ignore surplus table/control
    bytes. Do not accept padding, unknown precision/class/destination, or empty entries.
    """

    if marker == 0xDD:
        return (0,) if len(payload) == 2 else None
    cursor = 0
    destinations: list[int] = []
    if not payload:
        return None
    while cursor < len(payload):
        header = payload[cursor]
        cursor += 1
        kind, destination = header >> 4, header & 0x0F
        if kind not in {0, 1} or destination > 3:
            return None
        if marker == 0xDB:
            entry_size = 64 * (kind + 1)
            end = cursor + entry_size
            if end > len(payload):
                return None
            step = kind + 1
            if any(
                int.from_bytes(payload[offset : offset + step], "big") == 0
                for offset in range(cursor, end, step)
            ):
                return None
            destinations.append(destination)
        else:  # DHT: sixteen code-length counts followed by exactly that many symbols.
            counts = payload[cursor : cursor + 16]
            if len(counts) != 16 or not 1 <= sum(counts) <= 256:
                return None
            # Canonical Huffman codes cannot oversubscribe the tree or use all-ones.
            remaining_codes = 1
            for count in counts:
                remaining_codes = remaining_codes * 2 - count
                if remaining_codes <= 0:
                    return None
            end = cursor + 16 + sum(counts)
            if end > len(payload):
                return None
            destinations.append(header)
        cursor = end
    return tuple(destinations)


def _decode(image_bytes: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("photo is not a decodable image")
    return image


def soil_region(image: np.ndarray, transform: np.ndarray | None) -> SoilRegion:
    """Mask the reference card so that it cannot dominate soil QA (SPEC I8).

    Without a detected card the whole frame is soil. With one, the card polygon projected from
    the marker homography is enlarged about its centroid and removed. ``crop`` is the largest
    axis-aligned band of the frame beside the card, used for the perceptual hash.
    """

    height, width = image.shape[:2]
    mask = np.ones((height, width), dtype=np.uint8)
    if transform is None:
        return SoilRegion(card_found=False, crop=(0, 0, width, height), fraction=1.0, mask=mask)

    corners = card_corners(transform)
    centroid = corners.mean(axis=0)
    enlarged = centroid + (corners - centroid) * CARD_MASK_SCALE
    cv2.fillPoly(mask, [np.round(enlarged).astype(np.int32)], 0)

    x0 = int(np.clip(np.floor(enlarged[:, 0].min()), 0, width))
    x1 = int(np.clip(np.ceil(enlarged[:, 0].max()), 0, width))
    y0 = int(np.clip(np.floor(enlarged[:, 1].min()), 0, height))
    y1 = int(np.clip(np.ceil(enlarged[:, 1].max()), 0, height))
    candidates = [
        (0, 0, width, y0),
        (0, y1, width, height),
        (0, 0, x0, height),
        (x1, 0, width, height),
    ]
    crop = max(candidates, key=lambda box: (box[2] - box[0]) * (box[3] - box[1]))
    if (crop[2] - crop[0]) * (crop[3] - crop[1]) == 0:
        crop = (0, 0, width, height)
    return SoilRegion(
        card_found=True,
        crop=crop,
        fraction=float(mask.mean()),
        mask=mask,
    )


def sharpness(image: np.ndarray, mask: np.ndarray | None = None) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    if mask is None:
        return float(laplacian.var())
    kernel = np.ones((SHARPNESS_EROSION_PX, SHARPNESS_EROSION_PX), dtype=np.uint8)
    inner = cv2.erode(mask, kernel).astype(bool)
    values = laplacian[inner]
    return float(values.var()) if values.size else 0.0


def exposure_score(image: np.ndarray, mask: np.ndarray | None = None) -> tuple[float, bool]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    values = gray[mask.astype(bool)] if mask is not None else gray.ravel()
    if values.size == 0:
        return 0.0, False
    clipped = float(np.mean((values <= 5) | (values >= 250)))
    midtone = float(np.mean(values)) / 255.0
    score = max(0.0, min(1.0, (1.0 - clipped) * (1.0 - abs(midtone - 0.5))))
    return score, clipped <= MAX_CLIPPED_FRACTION and 0.08 <= midtone <= 0.92


def perceptual_hash(image: np.ndarray) -> str:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    low_frequency = cv2.dct(resized)[:8, :8]
    threshold = float(np.median(low_frequency.flatten()[1:]))
    bits = (low_frequency > threshold).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def hamming_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def gps_plausible(
    accuracy_m: float | None,
    land_cover: str | None,
    priors: dict[str, float],
) -> tuple[float | None, bool]:
    """Score location plausibility. A missing accuracy radius is unknown, never perfect."""

    gross_mismatch = (land_cover == "bare" and priors.get("soc", 0) >= 120) or (
        land_cover == "wetland" and priors.get("sand", 0) >= 900
    )
    if accuracy_m is None:
        return None, not gross_mismatch
    accuracy_score = max(0.0, 1.0 - accuracy_m / 1000.0)
    accuracy_ok = 0 <= accuracy_m <= MAX_GPS_ACCURACY_M
    return accuracy_score, accuracy_ok and not gross_mismatch


def photo_status(events: Iterable[tuple[str, bool]]) -> str:
    """Per-photo verdict: fail, flagged for human review, or pass (SPEC section 5)."""

    failures = {name for name, passed in events if not passed}
    if any(name.startswith(FAILING_CHECKS) for name in failures):
        return "fail"
    if any(name.startswith(REVIEW_CHECKS) for name in failures):
        return "flagged"
    return "pass"


def evaluate_photo(
    raw: bytes,
    *,
    accuracy_m: float | None,
    existing_hashes: tuple[str, ...] = (),
    land_cover: str | None = None,
    priors: dict[str, float] | None = None,
    classifier: SoilClassifier | None = None,
) -> QaResult:
    sanitized, camera_metadata = sanitize_jpeg(raw)
    image = _decode(sanitized)
    transform = card_transform(image)
    region = soil_region(image, transform)
    sharpness_value = sharpness(image, region.mask)
    exposure_value, exposure_ok = exposure_score(image, region.mask)
    x0, y0, x1, y1 = region.crop
    image_hash = perceptual_hash(image[y0:y1, x0:x1])
    unique = all(
        hamming_distance(image_hash, candidate) > NEAR_DUPLICATE_DISTANCE
        for candidate in existing_hashes
    )
    patches: dict[str, tuple[int, int, int]] | None = None
    if transform is not None:
        try:
            patches = extract_patches(image, transform)
        except ValueError:
            patches = None
    gps_score, gps_ok = gps_plausible(accuracy_m, land_cover, priors or {})
    events = [
        QaEvent("soil_region", region.fraction >= SOIL_FRACTION_MIN, round(region.fraction, 4)),
        QaEvent("sharpness", sharpness_value >= SHARPNESS_MIN, sharpness_value),
        QaEvent("exposure", exposure_ok, exposure_value),
        QaEvent("card_detection", True, 1.0 if patches else 0.0),
        QaEvent("gps_plausibility", gps_ok, gps_score),
        QaEvent("duplicate", unique, 1.0 if unique else 0.0),
    ]
    if classifier is not None:
        x0, y0, x1, y1 = region.crop
        soil_score = classifier.score(image[y0:y1, x0:x1])
        events.append(QaEvent("is_soil", soil_score >= 0.5, soil_score))
    return QaResult(
        calibration_status="calibrated" if patches else "uncalibrated",
        camera_metadata=camera_metadata,
        card_color_correction=patches,
        events=tuple(events),
        perceptual_hash=image_hash,
        sanitized_jpeg=sanitized,
        status=photo_status((event.check_name, event.passed) for event in events),
    )


def stable_result_digest(result: QaResult) -> str:
    """Small reproducibility aid used by worker logs without exposing a photo."""

    return hashlib.sha256(result.sanitized_jpeg).hexdigest()
