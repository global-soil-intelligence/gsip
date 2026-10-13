"""Pinned benchmark detector adapters. A private pass never authorizes publication."""

from __future__ import annotations

import hashlib
import io
import multiprocessing
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol, Self, cast

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image
from pydantic import Field, model_validator

import card.design as design_source
import card.validate as geometry_source
import pipeline.privacy_contract as contract_source
import pipeline.qa as jpeg_source
from pipeline.privacy_contract import (
    MAX_PHOTO_BYTES,
    MAX_PIXELS,
    CardExclusion,
    Digest,
    Outcome,
    PrivacyError,
    StrictModel,
    Version,
    decode_json,
    encode,
    validate,
)
from pipeline.privacy_io import read_file
from pipeline.qa import has_embedded_metadata

FACE_MODEL_NAME = "face_detection_yunet_2023mar.onnx"
TEXT_MODEL_NAME = "text_detection_en_ppocrv3_2023may.onnx"
FACE_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
TEXT_SHA256 = "03f550c6b406fda8bf54bd8327815f6c7e2edd98cea02348c93d879254366587"
SOURCE_COMMIT = "47534e27c9851bb1128ccc0102f1145e27f23f98"
SANITIZER_VERSION = "qa-jpeg-srgb-v1"
ImageArray = NDArray[np.uint8]
Fraction = Annotated[float, Field(strict=True, gt=0, le=1, allow_inf_nan=False)]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class DetectorConfiguration(StrictModel):
    schema_version: Literal["gsip-photo-detectors-v1"]
    screening_version: Version
    adapter_source_sha256: Digest
    card_geometry_source_sha256: Digest
    card_design_source_sha256: Digest
    jpeg_validation_source_sha256: Digest
    contract_source_sha256: Digest
    opencv_version: Version
    numpy_version: Version
    pillow_version: Version
    face_model_sha256: Digest
    scene_text_model_sha256: Digest
    face_threshold: Fraction
    face_nms_threshold: Fraction
    face_top_k: Annotated[int, Field(strict=True, ge=1, le=10_000)]
    text_binary_threshold: Fraction
    text_polygon_threshold: Fraction
    text_max_candidates: Annotated[int, Field(strict=True, ge=1, le=10_000)]
    text_unclip_ratio: Annotated[float, Field(strict=True, ge=1, le=3)]
    tile_size: Literal[640]
    tile_overlap: Literal[128]
    scales: list[Annotated[float, Field(strict=True, allow_inf_nan=False)]]
    max_views: Annotated[int, Field(strict=True, ge=1, le=512)]
    timeout_seconds: Annotated[int, Field(strict=True, ge=1, le=240)]
    margin_scale: Annotated[float, Field(strict=True, ge=1.12, le=1.12)]
    margin_version: Version

    @model_validator(mode="after")
    def fixed_coverage(self) -> Self:
        if (
            self.scales != [1.0, 0.5]
            or self.face_model_sha256 != FACE_SHA256
            or self.scene_text_model_sha256 != TEXT_SHA256
        ):
            raise PrivacyError()
        return self


def benchmark_configuration() -> DetectorConfiguration:
    """Unapproved demo parameters for reproducible local compatibility tests only."""
    import PIL

    return validate(
        DetectorConfiguration,
        {
            "schema_version": "gsip-photo-detectors-v1",
            "screening_version": "benchmark-v1",
            **source_digests(),
            "opencv_version": cv2.__version__,
            "numpy_version": np.__version__,
            "pillow_version": PIL.__version__,
            "face_model_sha256": FACE_SHA256,
            "scene_text_model_sha256": TEXT_SHA256,
            "face_threshold": 0.3,
            "face_nms_threshold": 0.3,
            "face_top_k": 5000,
            "text_binary_threshold": 0.3,
            "text_polygon_threshold": 0.5,
            "text_max_candidates": 200,
            "text_unclip_ratio": 2.0,
            "tile_size": 640,
            "tile_overlap": 128,
            "scales": [1.0, 0.5],
            "max_views": 512,
            "timeout_seconds": 240,
            "margin_scale": 1.12,
            "margin_version": "full-frame-no-exclusion-v1",
        },
    )


def configuration_bytes(config: DetectorConfiguration) -> bytes:
    return encode(config)


def source_digests() -> dict[str, str]:
    result = {"adapter_source_sha256": sha256(Path(__file__).read_bytes())}
    for key, module in (
        ("card_geometry_source_sha256", geometry_source),
        ("card_design_source_sha256", design_source),
        ("jpeg_validation_source_sha256", jpeg_source),
        ("contract_source_sha256", contract_source),
    ):
        if module.__file__ is None:
            raise PrivacyError("detector")
        result[key] = sha256(Path(module.__file__).read_bytes())
    return result


def load_configuration(path: Path, expected_digest: str) -> DetectorConfiguration:
    import PIL

    raw = read_file(path, 16_384)
    if sha256(raw) != expected_digest:
        raise PrivacyError("detector")
    config = validate(DetectorConfiguration, decode_json(raw))
    if (
        any(getattr(config, key) != digest for key, digest in source_digests().items())
        or config.opencv_version != cv2.__version__
        or config.numpy_version != np.__version__
        or config.pillow_version != PIL.__version__
    ):
        raise PrivacyError("detector")
    return config


def verified_model(directory: Path, name: str) -> bytes:
    expected = {FACE_MODEL_NAME: (232_589, FACE_SHA256), TEXT_MODEL_NAME: (2_423_490, TEXT_SHA256)}
    if name not in expected:
        raise PrivacyError("detector")
    size, digest = expected[name]
    try:
        raw = read_file(directory / name, size)
        if len(raw) != size or sha256(raw) != digest:
            raise PrivacyError()
        return raw
    except Exception:
        raise PrivacyError("detector") from None


def decode_sanitized(raw: bytes) -> ImageArray:
    try:
        if (
            not 0 < len(raw) <= MAX_PHOTO_BYTES
            or not raw.startswith(b"\xff\xd8")
            or not raw.endswith(b"\xff\xd9")
        ):
            raise PrivacyError()
        if has_embedded_metadata(raw):
            raise PrivacyError()
        with Image.open(io.BytesIO(raw)) as source:
            if (
                source.format != "JPEG"
                or source.mode != "RGB"
                or source.width * source.height > MAX_PIXELS
            ):
                raise PrivacyError()
            source.verify()
        image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.ndim != 3 or image.shape[2] != 3:
            raise PrivacyError()
        return cast(ImageArray, image)
    except Exception:
        raise PrivacyError("decode") from None


@dataclass(frozen=True)
class Detection:
    points: tuple[tuple[float, float], ...]
    score: float


class Backend(Protocol):
    def faces(self, image: ImageArray) -> list[Detection]: ...
    def texts(self, image: ImageArray) -> list[Detection]: ...


class OpenCVBackend:
    def __init__(
        self,
        config: DetectorConfiguration,
        models: Path | None = None,
        face_bytes: bytes | None = None,
        text_bytes: bytes | None = None,
    ) -> None:
        try:
            # Hash and consume the same bytes; a pathname swap cannot replace verified weights.
            if face_bytes is None or text_bytes is None:
                if models is None:
                    raise PrivacyError("detector")
                face_bytes = verified_model(models, FACE_MODEL_NAME)
                text_bytes = verified_model(models, TEXT_MODEL_NAME)
            if (
                len(face_bytes) != 232_589
                or sha256(face_bytes) != FACE_SHA256
                or len(text_bytes) != 2_423_490
                or sha256(text_bytes) != TEXT_SHA256
            ):
                raise PrivacyError("detector")
            face = np.frombuffer(face_bytes, dtype=np.uint8)
            text = np.frombuffer(text_bytes, dtype=np.uint8)
            self.face: Any = cv2.FaceDetectorYN.create(
                "onnx",
                face,
                np.empty(0, np.uint8),
                (640, 640),
                config.face_threshold,
                config.face_nms_threshold,
                config.face_top_k,
                cv2.dnn.DNN_BACKEND_OPENCV,
                cv2.dnn.DNN_TARGET_CPU,
            )
            model_type: Any = cv2.dnn.TextDetectionModel_DB
            self.text: Any = model_type(cv2.dnn.readNetFromONNX(text))
            self.text.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.text.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            self.text.setBinaryThreshold(config.text_binary_threshold)
            self.text.setPolygonThreshold(config.text_polygon_threshold)
            self.text.setMaxCandidates(config.text_max_candidates)
            self.text.setUnclipRatio(config.text_unclip_ratio)
            self.text.setInputSize((736, 736))
            self.text.setInputMean((123.675, 116.28, 103.53))
            self.text.setInputScale(1.0 / 255.0 / np.asarray([0.229, 0.224, 0.225]))
        except Exception:
            raise PrivacyError("detector") from None

    def faces(self, image: ImageArray) -> list[Detection]:
        self.face.setInputSize((image.shape[1], image.shape[0]))
        _, rows = self.face.detect(image)
        if rows is None:
            return []
        result: list[Detection] = []
        for row in np.asarray(rows):
            if row.shape != (15,) or not np.isfinite(row).all():
                raise PrivacyError("detector")
            x, y, w, h = map(float, row[:4])
            if w <= 0 or h <= 0:
                raise PrivacyError("detector")
            result.append(
                Detection(((x, y), (x + w, y), (x + w, y + h), (x, y + h)), float(row[-1]))
            )
        return result

    def texts(self, image: ImageArray) -> list[Detection]:
        resized = cv2.resize(image, (736, 736), interpolation=cv2.INTER_LINEAR)
        polygons, scores = self.text.detect(resized)
        if len(polygons) != len(scores):
            raise PrivacyError("detector")
        result: list[Detection] = []
        for polygon, score in zip(polygons, scores, strict=True):
            points = np.asarray(polygon, dtype=np.float64)
            if points.shape != (4, 2):
                raise PrivacyError("detector")
            points *= np.asarray([image.shape[1] / 736, image.shape[0] / 736])
            result.append(Detection(tuple((float(x), float(y)) for x, y in points), float(score)))
        return result


def views(image: ImageArray, config: DetectorConfiguration) -> Iterator[ImageArray]:
    """Both scales are tiled with overlap; edge tiles include the final row and column."""
    for scale in config.scales:
        resized = image if scale == 1 else cv2.resize(image, None, fx=scale, fy=scale)
        height, width = resized.shape[:2]
        step = config.tile_size - config.tile_overlap
        for y in range(0, height, step):
            for x in range(0, width, step):
                yield cast(
                    ImageArray,
                    resized[
                        y : min(y + config.tile_size, height), x : min(x + config.tile_size, width)
                    ],
                )


def card_mask(
    image: ImageArray, config: DetectorConfiguration
) -> tuple[ImageArray, CardExclusion | None]:
    """Screen all text until complete-card verification exists.

    The existing marker homography locates a projected quad, but cannot prove
    the card is present, complete or unobscured. A bare marker or occluded card
    can otherwise hide unrelated addresses/numerals inside that guessed quad.
    SPEC permits the exception; it does not require an unsafe approximation.
    """
    return np.zeros(image.shape[:2], np.uint8), None


@dataclass(frozen=True)
class ScreenResult:
    face: Outcome
    scene_text: Outcome
    card_exclusion: CardExclusion | None


class ScreenEngine:
    def __init__(self, config: DetectorConfiguration, backend: Backend) -> None:
        self.config = validate(DetectorConfiguration, config)
        self.backend = backend

    def _outcome(self, image: ImageArray, category: str, deadline: float) -> Outcome:
        count = 0
        maximum = self.config.face_top_k if category == "face" else self.config.text_max_candidates
        try:
            for index, view in enumerate(views(image, self.config)):
                if index >= self.config.max_views or time.monotonic() >= deadline:
                    raise PrivacyError("timeout")
                detections = (
                    self.backend.faces(view) if category == "face" else self.backend.texts(view)
                )
                if len(detections) >= maximum:
                    raise PrivacyError("detector")
                for detection in detections:
                    points = np.asarray(detection.points, dtype=np.float64)
                    if (
                        points.shape != (4, 2)
                        or not np.isfinite(points).all()
                        or not np.isfinite(detection.score)
                        or not 0 <= detection.score <= 1
                    ):
                        raise PrivacyError("detector")
                    if (
                        points[:, 0].max() < 0
                        or points[:, 1].max() < 0
                        or points[:, 0].min() >= view.shape[1]
                        or points[:, 1].min() >= view.shape[0]
                    ):
                        raise PrivacyError("detector")
                count += len(detections)
                if count > 10_000 or time.monotonic() >= deadline:
                    raise PrivacyError("timeout")
            return validate(Outcome, {"result": "flag" if count else "pass", "candidates": count})
        except Exception:
            return validate(Outcome, {"result": "error", "candidates": 0})

    def screen(self, raw: bytes, seconds_remaining: float = 240) -> ScreenResult:
        image = decode_sanitized(raw)
        deadline = time.monotonic() + min(self.config.timeout_seconds, max(0, seconds_remaining))
        mask, exclusion = card_mask(image, self.config)
        remainder = image.copy()
        remainder[mask != 0] = 0
        # Separate frames: face input is never the scene-text/card-masked remainder.
        face = self._outcome(image, "face", deadline)
        text = self._outcome(remainder, "text", deadline)
        return ScreenResult(face, text, exclusion)


class ScreeningEngine(Protocol):
    config: DetectorConfiguration

    def screen(self, raw: bytes, seconds_remaining: float = 240) -> ScreenResult: ...


class _ScreenEnvelope(StrictModel):
    face: Outcome
    scene_text: Outcome
    card_exclusion: CardExclusion | None


def _isolated_screen(
    sender: Any,
    config_value: dict[str, Any],
    face_bytes: bytes,
    text_bytes: bytes,
    raw: bytes,
    seconds: float,
) -> None:
    # Model inference receives image/model bytes, never authority credentials.
    for name in ("SUPABASE_SERVICE_ROLE_KEY", "GSIP_PHOTO_REVIEW_TOKEN"):
        os.environ.pop(name, None)
    with open(os.devnull, "wb") as silent:
        os.dup2(silent.fileno(), 1)
        os.dup2(silent.fileno(), 2)
        try:
            config = validate(DetectorConfiguration, config_value)
            if any(getattr(config, key) != digest for key, digest in source_digests().items()):
                raise PrivacyError("detector")
            cv2.setNumThreads(1)
            engine = ScreenEngine(
                config, OpenCVBackend(config, face_bytes=face_bytes, text_bytes=text_bytes)
            )
            result = engine.screen(raw, seconds)
            sender.send(
                {
                    "face": result.face.model_dump(),
                    "scene_text": result.scene_text.model_dump(),
                    "card_exclusion": result.card_exclusion.model_dump()
                    if result.card_exclusion
                    else None,
                }
            )
        except Exception:
            sender.send(None)
        finally:
            sender.close()


class BoundedScreenEngine:
    """Hard process deadline for pinned C/C++ inference, including native-library hangs."""

    def __init__(self, config: DetectorConfiguration, models: Path) -> None:
        self.config = validate(DetectorConfiguration, config)
        self.face_bytes = verified_model(models, FACE_MODEL_NAME)
        self.text_bytes = verified_model(models, TEXT_MODEL_NAME)

    def screen(self, raw: bytes, seconds_remaining: float = 240) -> ScreenResult:
        seconds = min(self.config.timeout_seconds, seconds_remaining)
        if seconds <= 0:
            raise PrivacyError("timeout")
        context = multiprocessing.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(
            target=_isolated_screen,
            args=(sender, self.config.model_dump(), self.face_bytes, self.text_bytes, raw, seconds),
            daemon=True,
        )
        started = time.monotonic()
        try:
            process.start()
            sender.close()
            remaining = max(0.0, seconds - (time.monotonic() - started))
            if not receiver.poll(remaining):
                raise PrivacyError("timeout")
            value = receiver.recv()
            if value is None or time.monotonic() - started > seconds:
                raise PrivacyError("detector")
            result = validate(_ScreenEnvelope, value)
            return ScreenResult(result.face, result.scene_text, result.card_exclusion)
        except PrivacyError:
            raise
        except Exception:
            raise PrivacyError("detector") from None
        finally:
            sender.close()
            receiver.close()
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1)
                process.close()
