from __future__ import annotations

import hashlib
import io
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np
from PIL import ExifTags, Image

from card.validate import extract_patches

Image.MAX_IMAGE_PIXELS = 40_000_000

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


class SoilClassifier(Protocol):
    """Phase 2 seam; WP-4b deliberately supplies no classifier implementation."""

    def score(self, image: np.ndarray) -> float: ...


@dataclass(frozen=True)
class QaEvent:
    check_name: str
    passed: bool
    score: float | None


@dataclass(frozen=True)
class QaResult:
    calibration_status: str
    camera_metadata: dict[str, float | int | str]
    card_color_correction: dict[str, tuple[int, int, int]] | None
    events: tuple[QaEvent, ...]
    perceptual_hash: str
    sanitized_jpeg: bytes
    status: str


def _number(value: object) -> float | int | str | None:
    if isinstance(value, (int, float, str)):
        return value
    numerator = getattr(value, "numerator", None)
    denominator = getattr(value, "denominator", None)
    if isinstance(numerator, int) and isinstance(denominator, int) and denominator:
        return numerator / denominator
    return None


def sanitize_jpeg(raw: bytes) -> tuple[bytes, dict[str, float | int | str]]:
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
        clean = source.convert("RGB")
        clean.info.pop("comment", None)
        clean.info.clear()
        output = io.BytesIO()
        clean.save(output, format="JPEG", quality=92, optimize=True, comment=b"")
    sanitized = output.getvalue()
    if has_embedded_metadata(sanitized):
        raise ValueError("sanitized photo still contains metadata")
    return sanitized, metadata


def has_embedded_metadata(image_bytes: bytes) -> bool:
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.getexif():
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
    if not image_bytes.startswith(b"\xff\xd8"):
        return False
    cursor = 2
    while cursor < len(image_bytes):
        if image_bytes[cursor] != 0xFF:
            cursor += 1
            continue
        while cursor < len(image_bytes) and image_bytes[cursor] == 0xFF:
            cursor += 1
        if cursor >= len(image_bytes):
            break
        marker = image_bytes[cursor]
        cursor += 1
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if marker == 0xDA:
            break
        if cursor + 2 > len(image_bytes):
            return True
        length = int.from_bytes(image_bytes[cursor : cursor + 2], "big")
        if length < 2 or cursor + length > len(image_bytes):
            return True
        payload = image_bytes[cursor + 2 : cursor + length]
        if marker == 0xFE:
            return True
        if 0xE1 <= marker <= 0xEF:
            return True
        if marker == 0xE0 and not payload.startswith((b"JFIF\x00", b"JFXX\x00")):
            return True
        cursor += length
    return False


def _decode(image_bytes: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("photo is not a decodable image")
    return image


def sharpness(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def exposure_score(image: np.ndarray) -> tuple[float, bool]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clipped = float(np.mean((gray <= 5) | (gray >= 250)))
    midtone = float(np.mean(gray)) / 255.0
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
) -> tuple[float, bool]:
    accuracy_score = 1.0 if accuracy_m is None else max(0.0, 1.0 - accuracy_m / 1000.0)
    accuracy_ok = accuracy_m is None or 0 <= accuracy_m <= MAX_GPS_ACCURACY_M
    gross_mismatch = (land_cover == "bare" and priors.get("soc", 0) >= 120) or (
        land_cover == "wetland" and priors.get("sand", 0) >= 900
    )
    return accuracy_score, accuracy_ok and not gross_mismatch


def aggregate_submission_status(events: Iterable[tuple[str, bool]]) -> str:
    failures = {name for name, passed in events if not passed}
    if any(name.startswith(("sharpness", "exposure", "is_soil")) for name in failures):
        return "qa_fail"
    if any(name.startswith(("gps_plausibility", "duplicate")) for name in failures):
        return "flagged"
    return "qa_pass"


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
    sharpness_value = sharpness(image)
    exposure_value, exposure_ok = exposure_score(image)
    image_hash = perceptual_hash(image)
    unique = all(
        hamming_distance(image_hash, candidate) > NEAR_DUPLICATE_DISTANCE
        for candidate in existing_hashes
    )
    try:
        patches = extract_patches(image)
    except ValueError:
        patches = None
    gps_score, gps_ok = gps_plausible(accuracy_m, land_cover, priors or {})
    events = [
        QaEvent("sharpness", sharpness_value >= SHARPNESS_MIN, sharpness_value),
        QaEvent("exposure", exposure_ok, exposure_value),
        QaEvent("card_detection", True, 1.0 if patches else 0.0),
        QaEvent("gps_plausibility", gps_ok, gps_score),
        QaEvent("duplicate", unique, 1.0 if unique else 0.0),
    ]
    if classifier is not None:
        soil_score = classifier.score(image)
        events.append(QaEvent("is_soil", soil_score >= 0.5, soil_score))
    status = aggregate_submission_status((event.check_name, event.passed) for event in events)
    return QaResult(
        calibration_status="calibrated" if patches else "uncalibrated",
        camera_metadata=camera_metadata,
        card_color_correction=patches,
        events=tuple(events),
        perceptual_hash=image_hash,
        sanitized_jpeg=sanitized,
        status=status,
    )


def stable_result_digest(result: QaResult) -> str:
    """Small reproducibility aid used by worker logs without exposing a photo."""

    return hashlib.sha256(result.sanitized_jpeg).hexdigest()
