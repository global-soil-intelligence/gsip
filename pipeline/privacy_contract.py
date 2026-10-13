"""Strict private photo-privacy wire contracts; validation supplies no authority."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Annotated, Any, Literal, Self, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

VERSION = "gsip-photo-privacy-v1"
MAX_WIRE_BYTES = 16_384
MAX_PHOTO_BYTES = 10_485_760
MAX_PIXELS = 40_000_000


class PrivacyError(ValueError):
    """A fixed error class, never an input value, exception cause or server message."""

    def __init__(self, code: str = "invalid") -> None:
        allowed = {
            "invalid",
            "authorization",
            "withdrawn",
            "stale",
            "conflict",
            "transport",
            "storage",
            "decode",
            "sanitize",
            "unsupported",
            "detector",
            "timeout",
        }
        self.code = code if code in allowed else "invalid"
        super().__init__(f"Photo privacy refusal: {self.code}")


def _uuid(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value
    ):
        raise PrivacyError()
    return value.lower()


Id = Annotated[str, BeforeValidator(_uuid)]
Digest = Annotated[str, Field(strict=True, min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")]
Version = Annotated[
    str, Field(strict=True, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
]
Revision = Annotated[int, Field(strict=True, ge=0, le=2**63 - 1)]
Count = Annotated[int, Field(strict=True, ge=0, le=10_000)]
PhotoStatus = Literal["pending", "processing", "clear", "review", "withheld", "error"]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, allow_inf_nan=False, revalidate_instances="always"
    )


class PrivacyCapabilities(StrictModel):
    version: Literal["gsip-photo-privacy-v1"]
    publication_open: bool
    policy_id: Id | None
    policy_revision: Revision
    screening_version: Version | None
    calibration_version: Version | None

    @model_validator(mode="after")
    def complete_policy(self) -> Self:
        values = (self.policy_id, self.screening_version, self.calibration_version)
        if any(x is None for x in values) and any(x is not None for x in values):
            raise PrivacyError()
        if self.publication_open and self.policy_id is None:
            raise PrivacyError()
        return self


class ContentRequest(StrictModel):
    schema_version: Literal["gsip-photo-privacy-v1"]
    photo_id: Id
    expected_content_revision: Revision
    sanitized_sha256: Digest
    byte_count: Annotated[int, Field(strict=True, ge=1, le=MAX_PHOTO_BYTES)]
    sanitizer_version: Version


class ContentResponse(StrictModel):
    photo_id: Id
    content_revision: Revision
    status: Literal["registered", "already_current"]


class Lease(StrictModel):
    lease_id: Id
    photo_id: Id
    submission_id: Id
    shot_type: Literal["A", "B", "C"]
    storage_path: Annotated[str, Field(strict=True, max_length=160)]
    content_revision: Revision
    sanitized_sha256: Digest | None
    byte_count: Annotated[int, Field(strict=True, ge=1, le=MAX_PHOTO_BYTES)] | None
    sanitizer_version: Version | None
    policy_id: Id
    policy_revision: Revision
    screening_version: Version
    calibration_version: Version
    detector_manifest_sha256: Digest
    calibration_manifest_sha256: Digest
    lease_expires_at: Annotated[str, Field(strict=True, max_length=64)]
    attempt: Annotated[int, Field(strict=True, ge=1, le=5)]

    @model_validator(mode="after")
    def known_content(self) -> Self:
        fields = (self.sanitized_sha256, self.byte_count, self.sanitizer_version)
        if any(x is None for x in fields) and any(x is not None for x in fields):
            raise PrivacyError()
        parsed = datetime.fromisoformat(self.lease_expires_at.replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            raise PrivacyError()
        return self


class Outcome(StrictModel):
    result: Literal["pass", "flag", "unsupported", "error"]
    candidates: Count

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.result == "pass" and self.candidates != 0) or (
            self.result == "flag" and self.candidates == 0
        ):
            raise PrivacyError()
        return self


class CardExclusion(StrictModel):
    image_width: Annotated[int, Field(strict=True, ge=1, le=MAX_PIXELS)]
    image_height: Annotated[int, Field(strict=True, ge=1, le=MAX_PIXELS)]
    mask_sha256: Digest
    excluded_pixels: Annotated[int, Field(strict=True, ge=1, lt=MAX_PIXELS)]
    margin_version: Version

    @model_validator(mode="after")
    def bounded(self) -> Self:
        pixels = self.image_width * self.image_height
        if pixels > MAX_PIXELS or self.excluded_pixels >= pixels:
            raise PrivacyError()
        return self


class ScreenReceipt(StrictModel):
    schema_version: Literal["gsip-photo-privacy-v1"]
    request_id: Id
    photo_id: Id
    content_revision: Revision
    policy_id: Id
    policy_revision: Revision
    sanitized_sha256: Digest
    screening_version: Version
    calibration_version: Version
    detector_manifest_sha256: Digest
    calibration_manifest_sha256: Digest
    face: Outcome
    scene_text: Outcome
    card_exception_used: bool
    card_exclusion: CardExclusion | None

    @model_validator(mode="after")
    def mask_evidence(self) -> Self:
        if self.card_exception_used != (self.card_exclusion is not None):
            raise PrivacyError()
        return self


class CompleteResponse(StrictModel):
    photo_id: Id
    content_revision: Revision
    status: Literal["clear", "review", "error"]


class FailResponse(StrictModel):
    photo_id: Id
    status: Literal["pending", "error"]


class PrivacyReceipt(StrictModel):
    photo_id: Id
    content_revision: Revision
    sanitized_sha256: Digest | None
    policy_id: Id | None
    policy_revision: Revision
    screening_version: Version | None
    calibration_version: Version | None
    status: PhotoStatus


class ReviewContext(StrictModel):
    photo_id: Id
    storage_path: Annotated[str, Field(strict=True, max_length=160)]
    content_revision: Revision
    sanitized_sha256: Digest | None
    policy_id: Id | None
    policy_revision: Revision
    screening_version: Version | None
    calibration_version: Version | None
    status: PhotoStatus


class ReviewRequest(StrictModel):
    schema_version: Literal["gsip-photo-privacy-v1"]
    review_id: Id
    photo_id: Id
    content_revision: Revision
    sanitized_sha256: Digest
    policy_id: Id
    policy_revision: Revision
    screening_version: Version
    calibration_version: Version
    decision: Literal["clear", "withhold"]
    reason: Literal["false_positive", "privacy_risk"]

    @model_validator(mode="after")
    def paired_reason(self) -> Self:
        if (self.decision == "clear") != (self.reason == "false_positive"):
            raise PrivacyError()
        return self


class ReviewResponse(StrictModel):
    photo_id: Id
    content_revision: Revision
    status: Literal["clear", "withheld"]
    review_id: Id


Model = TypeVar("Model", bound=StrictModel)


def validate(model: type[Model], value: object) -> Model:
    try:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json", warnings="error")
        return model.model_validate(value)
    except Exception:
        raise PrivacyError() from None


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PrivacyError()
        result[key] = value
    return result


def decode_json(raw: bytes, maximum: int = MAX_WIRE_BYTES) -> Any:
    try:
        if len(raw) > maximum:
            raise PrivacyError()
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(PrivacyError()),
        )
    except Exception:
        raise PrivacyError() from None


def encode(model: StrictModel, maximum: int = MAX_WIRE_BYTES) -> bytes:
    try:
        clean = validate(type(model), model)
        raw = json.dumps(
            clean.model_dump(mode="json", warnings="error"),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        if len(raw) > maximum:
            raise PrivacyError()
        return raw
    except Exception:
        raise PrivacyError() from None
