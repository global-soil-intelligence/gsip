"""How a phone photograph of soil was taken (WP-COLLECT-6, docs/capture-protocol.md).

The Python mirror of ``packages/schema/src/captureAcquisition.ts``; one fictional corpus
exercises both. A phone photograph is an RGB observation, never a spectrum, and this block holds
no soil-property value (SPEC L1, section 17 K1). Every field is a statement about the capture,
not verified here.

The block is private: it names a device and a time (SPEC I7). No network, no upload, and no
public export; ``write_partitions`` writes local private files only (SPEC L6)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

ACQUISITION_VERSION = "gsip-capture-acquisition-v1"
STANDARD_VERSION = "gsip-capture-standard-v1"
MAX_ACQUISITION_BYTES = 8_000

CalibrationStatus = Literal["uncalibrated", "calibrated"]
CardDetection = Literal["not_run", "none", "one", "multiple"]

_LABEL = r"^[0-9A-Za-z][0-9A-Za-z .,()+_/-]*$"
_VERSION = r"^[0-9A-Za-z][0-9A-Za-z.+_-]*$"
_CARD_ID = r"^[a-z0-9][a-z0-9-]*$"
_CARD_VERSION = r"^[0-9A-Za-z][0-9A-Za-z.-]*$"
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$")

Label = Annotated[str, Field(min_length=1, max_length=64, pattern=_LABEL)]
Version = Annotated[str, Field(min_length=1, max_length=64, pattern=_VERSION)]
CardId = Annotated[str, Field(min_length=1, max_length=48, pattern=_CARD_ID)]
CardVersion = Annotated[str, Field(min_length=1, max_length=24, pattern=_CARD_VERSION)]
Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Record = TypeVar("Record")


class _Strict(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, allow_inf_nan=False, revalidate_instances="always"
    )


class Device(_Strict):
    make: Label | None
    model: Label | None
    os_name: Label | None
    os_version: Version | None
    app_version: Version


class Camera(_Strict):
    exposure_time_s: Annotated[Number, Field(gt=0, le=30)] | None
    iso: Annotated[int, Field(strict=True, ge=1, le=1_000_000)] | None
    exposure: Literal["locked", "auto", "unknown"]
    white_balance: Literal["locked", "auto", "unknown"]
    hdr: Literal["off", "on", "unknown"]
    filters: Literal["off", "on", "unknown"]
    flash: Literal["off", "on", "unknown"]
    angle: Literal["nadir", "oblique", "unknown"]
    distance_cm: Annotated[Number, Field(ge=1, le=500)] | None
    field_of_view_cm: Annotated[Number, Field(ge=1, le=1_000)] | None


class ReferenceCard(_Strict):
    detection: CardDetection
    card_id: CardId | None
    card_version: CardVersion | None


class Location(_Strict):
    consent: Annotated[bool, Field(strict=True)]
    # A resolution-9 H3 cell: the grain GSIP already sends to outside processors (SPEC I7).
    h3_r9: Annotated[str, Field(pattern=r"^89[0-9a-f]{13}$")] | None


class CaptureAcquisition(_Strict):
    schema_version: Literal["gsip-capture-acquisition-v1"]
    standard_version: Literal["gsip-capture-standard-v1"]
    # I1: the only kind there is. A phone photograph is never recorded as a spectrum.
    observation_kind: Literal["rgb_photo"]
    procedure: Literal["prepared_sample", "field_profile", "unspecified"]
    device: Device
    camera: Camera
    lighting: Literal["shade", "overcast", "diffuser", "direct_sun", "artificial", "unknown"]
    reference_card: ReferenceCard
    calibration_status: CalibrationStatus
    replicate_count: Annotated[int, Field(strict=True, ge=1, le=20)] | None
    captured_at: str
    location: Location

    @model_validator(mode="after")
    def consistent(self) -> Self:
        card = self.reference_card
        identified = (
            card.detection == "one" and card.card_id is not None and card.card_version is not None
        )
        # I3: only exactly one detected, identified card can make a capture calibrated.
        if self.calibration_status == "calibrated" and not identified:
            raise ValueError("invalid capture acquisition")
        if card.detection != "one" and (card.card_id is not None or card.card_version is not None):
            raise ValueError("invalid capture acquisition")
        # I2: a place is recorded only with consent.
        if self.location.h3_r9 is not None and not self.location.consent:
            raise ValueError("invalid capture acquisition")
        if not _UTC.match(self.captured_at):
            raise ValueError("invalid capture acquisition")
        try:
            datetime.fromisoformat(self.captured_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("invalid capture acquisition") from error
        return self


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def parse_acquisition(raw: bytes | str) -> CaptureAcquisition:
    """Validate one block. Errors are generic: a rejected block's values stay private."""

    data = raw.encode() if isinstance(raw, str) else raw
    try:
        if len(data) > MAX_ACQUISITION_BYTES:
            raise ValueError("too large")
        return CaptureAcquisition.model_validate(json.loads(data, object_pairs_hook=_unique))
    except Exception:  # noqa: BLE001 - validator errors can carry private values
        raise ValueError("invalid capture acquisition") from None


def card_gate(
    detection: CardDetection, card_id: str | None = None, card_version: str | None = None
) -> tuple[CalibrationStatus, ReferenceCard]:
    """The card gate (I3): ``calibrated`` only for exactly one detected, identified card.

    A card the person says they used, a card that was not looked for, no card and two cards are
    all ``uncalibrated``."""

    identified = (
        detection == "one"
        and isinstance(card_id, str)
        and isinstance(card_version, str)
        and re.fullmatch(_CARD_ID, card_id) is not None
        and len(card_id) <= 48
        and re.fullmatch(_CARD_VERSION, card_version) is not None
        and len(card_version) <= 24
    )
    return (
        "calibrated" if identified else "uncalibrated",
        ReferenceCard(
            detection=detection,
            card_id=card_id if identified else None,
            card_version=card_version if identified else None,
        ),
    )


# The editions ``pipeline.cards`` can read, as they are named in an acquisition block.
CARD_EDITIONS: Mapping[str, tuple[str, str]] = {
    "a6": ("gsip-a6", "v1"),
    "node": ("gsip-node", "v1"),
}


def gate_from_qa(
    *, card_outlines: int, edition: str | None
) -> tuple[CalibrationStatus, ReferenceCard]:
    """The gate for what photo QA found: how many cards, and the edition of the one it read."""

    if card_outlines == 0:
        return card_gate("none")
    if card_outlines > 1:
        return card_gate("multiple")
    known = CARD_EDITIONS.get(edition or "")
    # One card that could not be read is found but not identified: uncalibrated.
    return card_gate("one", *(known or (None, None)))


def calibration_status_of(record: object) -> CalibrationStatus:
    """A record's partition. One with no acquisition block predates it and is uncalibrated."""

    acquisition = (
        record.get("acquisition")
        if isinstance(record, Mapping)
        else getattr(record, "acquisition", None)
    )
    if acquisition is None:
        return "uncalibrated"
    return CaptureAcquisition.model_validate(acquisition).calibration_status


def partition_by_calibration(
    records: Iterable[Record],
) -> dict[CalibrationStatus, list[Record]]:
    """Split records so that calibrated and uncalibrated never share a list (I3)."""

    result: dict[CalibrationStatus, list[Record]] = {"calibrated": [], "uncalibrated": []}
    for record in records:
        result[calibration_status_of(record)].append(record)
    return result


def assert_unmixed(records: Sequence[object], status: CalibrationStatus) -> None:
    """Refuse a list that holds any record of the other kind."""

    if any(calibration_status_of(record) != status for record in records):
        raise ValueError("calibrated and uncalibrated capture records must not be mixed")


def _json_value(record: object) -> Any:
    if isinstance(record, BaseModel):
        return record.model_dump(mode="json")
    return record


def write_partitions(records: Iterable[object], directory: Path) -> dict[str, int]:
    """Write ``calibrated.jsonl`` and ``uncalibrated.jsonl`` into a new private directory.

    Local and private: mode 0700 for the directory, 0600 for the files, nothing uploaded. Each
    file is checked again before it is written, so neither can hold a record of the other kind.
    Returns counts only."""

    parts = partition_by_calibration(list(records))
    directory.mkdir(mode=0o700, exist_ok=False)
    counts: dict[str, int] = {}
    for status, items in parts.items():
        assert_unmixed(items, status)
        lines = [
            json.dumps(_json_value(item), sort_keys=True, separators=(",", ":")) for item in items
        ]
        descriptor = os.open(
            directory / f"{status}.jsonl", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write("".join(line + "\n" for line in lines))
        counts[status] = len(items)
    return counts


def _rounded(value: object, places: int) -> object:
    if isinstance(value, bool) or value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        return round(value, places)
    if isinstance(value, Mapping):
        return {str(key): _rounded(item, places) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_rounded(item, places) for item in value]
    raise ValueError("unsupported value in a colour record")


def calibration_digest(colour_record: Mapping[str, object] | None) -> str:
    """SHA-256 of a photo's colour record (I4): the same image and card give the same digest.

    ``colour_record`` is ``CardQaResult.card_color_correction``. Floats are rounded to six places
    before hashing, so the digest pins the corrected values and not the last bits of a platform's
    linear algebra. ``None`` (no readable card) has its own fixed digest."""

    canonical = json.dumps(
        _rounded(colour_record, 6), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def with_pipeline_findings(
    acquisition: CaptureAcquisition,
    *,
    card_outlines: int,
    edition: str | None,
    camera_metadata: Mapping[str, float | int | str] | None = None,
) -> CaptureAcquisition:
    """Replace what the client said about the card with what the pipeline found (I3).

    The gate is always the pipeline's: a client that claimed a card cannot keep ``calibrated``
    when none was detected. Exposure time, ISO, make and model are filled from the photograph's
    own allowlisted metadata only where the block left them unknown."""

    status, card = gate_from_qa(card_outlines=card_outlines, edition=edition)
    data = acquisition.model_dump(mode="json")
    data["calibration_status"] = status
    data["reference_card"] = card.model_dump(mode="json")
    metadata = camera_metadata or {}
    exposure, iso = metadata.get("exposure_time_s"), metadata.get("iso")
    if data["camera"]["exposure_time_s"] is None and isinstance(exposure, (int, float)):
        if 0 < float(exposure) <= 30:
            data["camera"]["exposure_time_s"] = float(exposure)
    if data["camera"]["iso"] is None and isinstance(iso, (int, float)):
        if float(iso).is_integer() and 1 <= int(iso) <= 1_000_000:
            data["camera"]["iso"] = int(iso)
    for key in ("make", "model"):
        value = metadata.get(key)
        if data["device"][key] is None and isinstance(value, str):
            cleaned = value.strip()[:64]
            if re.fullmatch(_LABEL, cleaned):
                data["device"][key] = cleaned
    return CaptureAcquisition.model_validate(data)
