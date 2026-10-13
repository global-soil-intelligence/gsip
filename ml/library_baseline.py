"""Private paired-record preparation and an explicitly synthetic reconstruction demo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict
from uuid import UUID

import numpy as np

from pipeline.library import (
    CameraRgb,
    InstrumentReflectance,
    LibraryRecord,
    PrivateLibrary,
    encoded,
    private_path,
)


class BaselineReceipt(TypedDict):
    mode: str
    scientific_validation: bool
    model_version: str
    input_sha256: str
    train_samples: int
    development_samples: int
    sample_overlap: int
    development_rmse: float
    numpy_version: str


MODEL_VERSION = "rgb-reflectance-ridge-demo-v1"


@dataclass(frozen=True)
class PairedSample:
    key: tuple[UUID, UUID]
    camera: LibraryRecord
    spectrum: LibraryRecord


def prepare_pairs(records: list[LibraryRecord], *, demo: bool) -> list[PairedSample]:
    groups: dict[tuple[UUID, UUID], list[LibraryRecord]] = defaultdict(list)
    identities: dict[UUID, bytes] = {}
    for record in records:
        digest = encoded(record)
        if record.measurement_id in identities:
            if identities[record.measurement_id] != digest:
                raise ValueError("conflicting measurement identity")
            continue
        identities[record.measurement_id] = digest
        groups[record.sample_key].append(record)
    pairs = []
    source_samples: dict[str, tuple[UUID, UUID]] = {}
    grid: tuple[float, ...] | None = None
    device: UUID | None = None
    for key, group in sorted(groups.items()):
        # Never let an eligible twin override a sample's negative rights/holdout state.
        if any(
            r.withdrawn
            or r.holdout
            or not r.consent_verified
            or not r.pairing_verified
            or r.qa_status != "pass"
            for r in group
        ):
            continue
        if any(r.synthetic != demo for r in group):
            continue
        first = group[0]
        if any(
            r.context != first.context
            or r.grant_id != first.grant_id
            or r.protocol_version != first.protocol_version
            for r in group
        ):
            raise ValueError("inconsistent sample pairing")
        cameras = [r for r in group if isinstance(r.measurement, CameraRgb)]
        spectra = [r for r in group if isinstance(r.measurement, InstrumentReflectance)]
        if not cameras or not spectra:
            continue
        if len(cameras) != 1 or len(spectra) != 1:
            raise ValueError("ambiguous repeated measurements; aggregation protocol required")
        camera, spectrum = cameras[0], spectra[0]
        optical = camera.measurement
        measured = spectrum.measurement
        if not isinstance(optical, CameraRgb) or not isinstance(measured, InstrumentReflectance):
            raise ValueError("invalid pairing")
        if grid is None:
            grid, device = measured.wavelength_nm, optical.device_id
        elif grid != measured.wavelength_nm or device != optical.device_id:
            raise ValueError("mixed wavelength grids or camera devices")
        for row in (camera, spectrum):
            source = row.measurement.source_sha256
            if source in source_samples and source_samples[source] != key:
                raise ValueError("repeated source across physical sample identities")
            source_samples[source] = key
        pairs.append(PairedSample(key, camera, spectrum))
    return pairs


def _partition(key: tuple[UUID, UUID]) -> bool:
    """Fixed sample-key hash: true is development, never a sealed holdout."""
    digest = hashlib.sha256(f"gsip-library-split-v1:{key[0]}:{key[1]}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 5 == 0


def _matrix(pairs: list[PairedSample]) -> tuple[np.ndarray, np.ndarray]:
    features, targets = [], []
    for pair in pairs:
        camera, spectrum = pair.camera.measurement, pair.spectrum.measurement
        if not isinstance(camera, CameraRgb) or not isinstance(spectrum, InstrumentReflectance):
            raise ValueError("invalid pair")
        features.append([1.0, *camera.mean_rgb])
        targets.append(spectrum.reflectance)
    return np.asarray(features, dtype=np.float64), np.asarray(targets, dtype=np.float64)


def _write_private(path: Path, value: object) -> None:
    data = json.dumps(value, sort_keys=True, allow_nan=False, indent=2).encode() + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def run_baseline(records: list[LibraryRecord], output: Path, *, demo: bool) -> BaselineReceipt:
    if not demo:
        raise ValueError("field training awaits hosted rights and privacy-screening verification")
    pairs = prepare_pairs(records, demo=True)
    train = [p for p in pairs if not _partition(p.key)]
    development = [p for p in pairs if _partition(p.key)]
    if len(train) < 4 or len(development) < 2:
        raise ValueError("at least four train and two development samples required")
    x, y = _matrix(train)
    dx, dy = _matrix(development)
    # Small fixed ridge regularization; synthetic plumbing, not hyperparameter selection.
    ridge = np.eye(x.shape[1]) * 1e-6
    weights = np.linalg.solve(x.T @ x + ridge, x.T @ y)
    predictions = dx @ weights
    rmse = float(np.sqrt(np.mean((predictions - dy) ** 2)))
    if not np.isfinite(weights).all() or not np.isfinite(rmse):
        raise ValueError("non-finite baseline")
    ordered = [r for p in pairs for r in (p.camera, p.spectrum)]
    input_digest = hashlib.sha256(b"\n".join(encoded(r) for r in ordered)).hexdigest()
    receipt: BaselineReceipt = {
        "mode": "synthetic-demo-only",
        "scientific_validation": False,
        "model_version": MODEL_VERSION,
        "input_sha256": input_digest,
        "train_samples": len(train),
        "development_samples": len(development),
        "sample_overlap": len({p.key for p in train} & {p.key for p in development}),
        "development_rmse": rmse,
        "numpy_version": np.__version__,
    }
    target = output.absolute()
    private_path(target)
    if target.exists():
        raise ValueError("output already exists")
    target.mkdir(mode=0o700)
    _write_private(
        target / "model.json",
        {
            "mode": "synthetic-demo-only",
            "model_version": MODEL_VERSION,
            "wavelength_nm": list(pairs[0].spectrum.measurement.wavelength_nm)
            if isinstance(pairs[0].spectrum.measurement, InstrumentReflectance)
            else [],
            "coefficients": weights.tolist(),
            "features": ["intercept", "srgb_r", "srgb_g", "srgb_b"],
            "intervals": None,
            "deployment_eligible": False,
        },
    )
    _write_private(
        target / "partitions.json",
        {
            "grouping": "node-and-physical-sample-v1",
            "split": "sha256-mod-5-v1",
            "train": [[str(x) for x in p.key] for p in train],
            "development": [[str(x) for x in p.key] for p in development],
            "sealed_holdout_used": False,
        },
    )
    # Written last: a directory without this receipt is an incomplete run.
    _write_private(target / "receipt.json", receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthetic-only private RGB reconstruction demo")
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--demo", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = run_baseline(PrivateLibrary(args.store).records(), args.output, demo=args.demo)
        # No sample identifiers, measurement hashes, paths or model payload in logs.
        print(
            json.dumps(
                {
                    "mode": receipt["mode"],
                    "scientific_validation": receipt["scientific_validation"],
                    "train_samples": receipt["train_samples"],
                    "development_samples": receipt["development_samples"],
                    "sample_overlap": receipt["sample_overlap"],
                    "development_rmse": receipt["development_rmse"],
                },
                sort_keys=True,
            )
        )
    except (ValueError, OSError, np.linalg.LinAlgError):
        print("Invalid private dataset or output; operation stopped.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
