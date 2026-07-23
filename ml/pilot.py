"""Strict local pilot records. Lab values are never inferred from map values."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal, Self

import h3  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Prior(StrictRecord):
    source: str = Field(min_length=1)
    version: str = Field(min_length=1)
    property: Literal["soc"] = "soc"
    unit: Literal["g/kg"] = "g/kg"
    depth_top_cm: Literal[0] = 0
    depth_bottom_cm: Literal[5] = 5
    mean: float = Field(ge=0, le=1000)
    lower: float = Field(ge=0, le=1000)
    upper: float = Field(ge=0, le=1000)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.lower > self.upper:
            raise ValueError("prior lower bound exceeds upper bound")
        return self


class LabResult(StrictRecord):
    sample_id: str = Field(min_length=1)
    lab_name: str = Field(min_length=1)
    method: str = Field(min_length=1)
    document_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    document_path: str = Field(min_length=1)
    verified_by: str = Field(min_length=1)
    verified: Literal[True]
    property: Literal["soc"] = "soc"
    unit: Literal["g/kg"] = "g/kg"
    depth_top_cm: Literal[0] = 0
    depth_bottom_cm: Literal[5] = 5
    value: float = Field(ge=0, le=1000)


class Observation(StrictRecord):
    submission_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    site_id: str = Field(min_length=1)
    region: str = Field(min_length=1)
    h3_r8: str
    depth_top_cm: Literal[0] = 0
    depth_bottom_cm: Literal[5] = 5
    image_path: str = Field(min_length=1)
    # A reviewer selects exposed soil in Shot B; automatic segmentation is future work.
    soil_roi: tuple[int, int, int, int]
    roi_verified: Literal[True]
    phone_group: str = Field(min_length=1)
    lighting: Literal["diffuse_daylight", "direct_sun", "artificial"]
    surface_condition: Literal["dry", "moist", "wet"]
    is_synthetic: bool
    prior: Prior

    @model_validator(mode="after")
    def valid_location_and_roi(self) -> Self:
        if not h3.is_valid_cell(self.h3_r8) or h3.get_resolution(self.h3_r8) != 8:
            raise ValueError("a valid H3 resolution-8 cell is required")
        x0, y0, x1, y1 = self.soil_roi
        if min(x0, y0) < 0 or x1 - x0 < 32 or y1 - y0 < 32:
            raise ValueError("soil ROI must be at least 32 by 32 pixels")
        return self


class Sample(Observation):
    lab: LabResult

    @model_validator(mode="after")
    def matched_sample(self) -> Self:
        if self.lab.sample_id != self.sample_id:
            raise ValueError("photo and laboratory sample IDs must match")
        return self


def local_image(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("image path must remain inside the dataset directory")
    return path


def read_samples(path: Path) -> list[Sample]:
    samples = [
        Sample.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()
    ]
    if not samples:
        raise ValueError("no verified photo/lab pairs supplied")
    for field in ("sample_id", "submission_id"):
        ids = [getattr(s, field) for s in samples]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate {field}; keep repeated photographs in one sample")
    if len({s.region for s in samples}) != 1:
        raise ValueError("a pilot run must target one declared region")
    if len({(s.prior.source, s.prior.version) for s in samples}) != 1:
        raise ValueError("pin one prior source/version per experiment")
    for sample in samples:
        document = local_image(path.parent, sample.lab.document_path)
        if hashlib.sha256(document.read_bytes()).hexdigest() != sample.lab.document_sha256:
            raise ValueError("lab document checksum does not match the reviewed record")
    return samples


def fingerprint(samples: list[Sample], image_hashes: list[str]) -> str:
    records: list[dict[str, Any]] = sorted(
        [
            dict(sample=s.model_dump(), image_sha256=digest)
            for s, digest in zip(samples, image_hashes, strict=True)
        ],
        key=lambda row: str(row["sample"]["sample_id"]),
    )
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
