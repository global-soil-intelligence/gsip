"""Private staged evaluation harness. Measurements never approve publication."""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from pipeline.library import PrivateArgumentParser
from pipeline.photo_privacy import (
    BoundedScreenEngine,
    ScreenEngine,
    ScreeningEngine,
    benchmark_configuration,
    configuration_bytes,
    decode_sanitized,
    load_configuration,
    sha256,
)
from pipeline.privacy_contract import (
    Digest,
    PrivacyError,
    StrictModel,
    Version,
    decode_json,
    validate,
)
from pipeline.privacy_io import PrivateDirectory, read_file

CATEGORIES = ("face", "scene_text", "plate", "house_number", "numeral_script")


class StagedCase(StrictModel):
    file: Annotated[str, Field(strict=True, min_length=1, max_length=256)]
    category: Literal["face", "scene_text", "plate", "house_number", "numeral_script"]
    sensitive_present: bool
    stratum: Literal[
        "tiny", "occluded", "oblique", "varied_appearance", "multiscript", "card_edge", "other"
    ]


class StagedManifest(StrictModel):
    schema_version: Literal["gsip-photo-staged-evaluation-v1"]
    material_declared: Literal["synthetic", "permissioned_staged"]
    cases: Annotated[list[StagedCase], Field(max_length=10_000)]


class CategorySummary(StrictModel):
    category: Literal["face", "scene_text", "plate", "house_number", "numeral_script"]
    positive_frames: Annotated[int, Field(strict=True, ge=0)]
    negative_frames: Annotated[int, Field(strict=True, ge=0)]
    misses: Annotated[int, Field(strict=True, ge=0)]
    false_positives: Annotated[int, Field(strict=True, ge=0)]
    unsupported_or_error: Annotated[int, Field(strict=True, ge=0)]
    supported_negative_frames: Annotated[int, Field(strict=True, ge=0)]
    positive_success_interval_95: list[float] | None
    negative_false_positive_interval_95: list[float] | None

    @model_validator(mode="after")
    def numerical_bounds(self) -> Self:
        if (
            self.misses > self.positive_frames
            or self.supported_negative_frames > self.negative_frames
            or self.false_positives > self.supported_negative_frames
        ):
            raise PrivacyError()
        for interval in (
            self.positive_success_interval_95,
            self.negative_false_positive_interval_95,
        ):
            if interval is not None and (
                len(interval) != 2
                or not all(math.isfinite(x) and 0 <= x <= 1 for x in interval)
                or interval[0] > interval[1]
            ):
                raise PrivacyError()
        return self


class CalibrationManifest(StrictModel):
    schema_version: Literal["gsip-photo-calibration-v1"]
    calibration_version: Version
    detector_manifest_sha256: Digest
    publication_approved: bool
    evidence_status: Literal["unknown", "staged_unapproved"]
    material_declared: Literal["synthetic", "permissioned_staged"]
    input_manifest_sha256: Digest
    category_summaries: list[CategorySummary]
    runtime_samples: Annotated[int, Field(strict=True, ge=0)]
    runtime_total_seconds: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
    strata_counts: dict[str, Annotated[int, Field(strict=True, ge=0)]]
    metric: Literal["component_candidate_frame_rate_not_instance_recall"]

    @model_validator(mode="after")
    def no_approval(self) -> Self:
        if self.publication_approved is not False or [
            x.category for x in self.category_summaries
        ] != list(CATEGORIES):
            raise PrivacyError()
        return self


def wilson(successes: int, count: int) -> list[float] | None:
    if type(count) is not int or type(successes) is not int or not 0 <= successes <= count:
        raise PrivacyError()
    if count == 0:
        return None
    z = 1.959963984540054
    fraction = successes / count
    denominator = 1 + z * z / count
    center = (fraction + z * z / (2 * count)) / denominator
    half = (
        z * math.sqrt(fraction * (1 - fraction) / count + z * z / (4 * count * count)) / denominator
    )
    return [max(0.0, center - half), min(1.0, center + half)]


def evaluate_staged(
    raw_manifest: bytes,
    source: PrivateDirectory,
    engine: ScreeningEngine,
    detector_digest: str,
    calibration_version: str,
) -> CalibrationManifest:
    manifest = validate(StagedManifest, decode_json(raw_manifest, 2_000_000))
    counts = {
        category: {
            "positive": 0,
            "negative": 0,
            "misses": 0,
            "false_positives": 0,
            "unsupported": 0,
            "unsupported_negative": 0,
        }
        for category in CATEGORIES
    }
    seen: set[str] = set()
    strata: dict[str, int] = {}
    total_time = 0.0
    for case in manifest.cases:
        relative = Path(case.file)
        if relative.is_absolute() or ".." in relative.parts or relative.name != case.file:
            raise PrivacyError()
        raw = source.read(source.path / relative, 10_485_760)
        decode_sanitized(raw)
        digest = sha256(raw)
        if digest in seen:
            # Repeated encodings/retries are not independent calibration frames.
            raise PrivacyError()
        seen.add(digest)
        started = time.monotonic()
        result = engine.screen(raw)
        total_time += time.monotonic() - started
        outcome = result.face if case.category == "face" else result.scene_text
        group = counts[case.category]
        group["positive" if case.sensitive_present else "negative"] += 1
        if outcome.result in {"unsupported", "error"}:
            group["unsupported"] += 1
            if not case.sensitive_present:
                group["unsupported_negative"] += 1
            if case.sensitive_present:
                group["misses"] += 1  # No supported success; unknown coverage is not a hit.
        elif case.sensitive_present and outcome.result != "flag":
            group["misses"] += 1
        elif not case.sensitive_present and outcome.result == "flag":
            group["false_positives"] += 1
        key = case.category + ":" + case.stratum
        strata[key] = strata.get(key, 0) + 1
    summaries = []
    for category, group in counts.items():
        summaries.append(
            {
                "category": category,
                "positive_frames": group["positive"],
                "negative_frames": group["negative"],
                "misses": group["misses"],
                "false_positives": group["false_positives"],
                "unsupported_or_error": group["unsupported"],
                "supported_negative_frames": group["negative"] - group["unsupported_negative"],
                "positive_success_interval_95": wilson(
                    group["positive"] - group["misses"], group["positive"]
                ),
                "negative_false_positive_interval_95": wilson(
                    group["false_positives"], group["negative"] - group["unsupported_negative"]
                ),
            }
        )
    return validate(
        CalibrationManifest,
        {
            "schema_version": "gsip-photo-calibration-v1",
            "calibration_version": calibration_version,
            "detector_manifest_sha256": detector_digest,
            "publication_approved": False,
            "evidence_status": "staged_unapproved" if seen else "unknown",
            "material_declared": manifest.material_declared,
            "input_manifest_sha256": sha256(raw_manifest),
            "category_summaries": summaries,
            "runtime_samples": len(seen),
            "runtime_total_seconds": total_time,
            "strata_counts": strata,
            "metric": "component_candidate_frame_rate_not_instance_recall",
        },
    )


def main() -> None:
    parser = PrivateArgumentParser(
        description="Private staged photo evaluation; no calibration approval"
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--models", type=Path)
    parser.add_argument("--configuration", type=Path)
    parser.add_argument("--calibration-version", default="benchmark-unknown-v1")
    args = parser.parse_args()
    try:
        source = PrivateDirectory(args.source)
        output = PrivateDirectory(args.output)
        if any(output.path.iterdir()):
            raise PrivacyError("conflict")
        config_bytes = (
            read_file(args.configuration, 16_384)
            if args.configuration
            else configuration_bytes(benchmark_configuration())
        )
        config_path = output.write("detector-manifest.json", config_bytes)
        config = load_configuration(config_path, sha256(config_bytes))
        raw_manifest = (
            read_file(args.manifest, 2_000_000)
            if args.manifest
            else json.dumps(
                {
                    "schema_version": "gsip-photo-staged-evaluation-v1",
                    "material_declared": "synthetic",
                    "cases": [],
                }
            ).encode()
        )
        if (
            args.models is None
            and validate(StagedManifest, decode_json(raw_manifest, 2_000_000)).cases
        ):
            raise PrivacyError("detector")
        # Empty coverage creates explicit unknown evidence without loading detector weights.
        engine: ScreeningEngine | None = (
            BoundedScreenEngine(config, args.models) if args.models else None
        )
        if engine is None:

            class EmptyBackend:
                def faces(self, value: object) -> list[object]:
                    raise PrivacyError("unsupported")

                def texts(self, value: object) -> list[object]:
                    raise PrivacyError("unsupported")

            engine = ScreenEngine(config, EmptyBackend())  # type: ignore[arg-type]
        report = evaluate_staged(
            raw_manifest, source, engine, sha256(config_bytes), args.calibration_version
        )
        output.write(
            "calibration-manifest.json",
            json.dumps(
                report.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode(),
        )
        print(
            json.dumps(
                {
                    "frames": report.runtime_samples,
                    "publication_approved": False,
                    "evidence_status": report.evidence_status,
                }
            )
        )
    except Exception:
        print("Photo privacy evaluation unavailable", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
