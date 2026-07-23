from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import h3  # type: ignore[import-untyped]
import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from ml.experiment import conformal_radius, spatial_split, train_experiment
from ml.features import image_features
from ml.inference import predict
from ml.pilot import Observation, Sample, read_samples
from ml.prior_cache import lookup_prior


def make_dataset(root: Path, count: int = 25) -> Path:
    """Synthetic fixtures exercise software; never scientific validation data."""
    rows = []
    document = b"SYNTHETIC LAB REPORT FOR SOFTWARE TESTS ONLY"
    (root / "lab.txt").write_bytes(document)
    rng = np.random.default_rng(41)
    for i in range(count):
        color = 60 + (i * 17) % 100
        pixels = np.clip(rng.normal(color, 12, (64, 64, 3)), 0, 255).astype(np.uint8)
        name = f"photo-{i}.jpg"
        Image.fromarray(pixels).save(root / name, quality=90)
        row = {
            "submission_id": f"submission-{i}",
            "sample_id": f"sample-{i}",
            "site_id": f"site-{i}",
            "region": "SYNTHETIC_TEST_REGION",
            "h3_r8": h3.latlng_to_cell(25 + (i // 10) * 1.4, -125 + (i % 10) * 1.4, 8),
            "image_path": name,
            "soil_roi": [0, 0, 64, 64],
            "roi_verified": True,
            "phone_group": "synthetic_camera",
            "lighting": "diffuse_daylight",
            "surface_condition": "dry",
            "is_synthetic": True,
            "prior": {
                "source": "fixture",
                "version": "test-v1",
                "mean": 30,
                "lower": 0,
                "upper": 60,
            },
            "lab": {
                "sample_id": f"sample-{i}",
                "lab_name": "SYNTHETIC",
                "method": "synthetic",
                "document_path": "lab.txt",
                "document_sha256": hashlib.sha256(document).hexdigest(),
                "verified_by": "TEST_ONLY",
                "verified": True,
                "value": color / 5,
            },
        }
        rows.append(row)
    path = root / "pilot.jsonl"
    write_rows(path, rows)
    return path


def read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def observation(sample: Sample) -> Observation:
    return Observation.model_validate(sample.model_dump(exclude={"lab"}))


@pytest.mark.parametrize(
    "change",
    [
        {"sample_id": "wrong"},
        {"verified": False},
        {"value": float("nan")},
        {"property": "som"},
        {"unit": "%"},
        {"depth_bottom_cm": 30},
    ],
)
def test_rejects_unpaired_unverified_or_incompatible_lab_values(
    tmp_path: Path,
    change: dict[str, Any],
) -> None:
    path = make_dataset(tmp_path, 1)
    rows = read_rows(path)
    rows[0]["lab"].update(change)
    write_rows(path, rows)
    with pytest.raises(ValidationError):
        read_samples(path)


def test_lab_report_checksum_and_duplicate_samples_are_enforced(tmp_path: Path) -> None:
    path = make_dataset(tmp_path, 2)
    rows = read_rows(path)
    write_rows(path, [rows[0], rows[0]])
    with pytest.raises(ValueError, match="duplicate"):
        read_samples(path)
    write_rows(path, rows)
    (tmp_path / "lab.txt").write_text("changed after review")
    with pytest.raises(ValueError, match="checksum"):
        read_samples(path)


def test_spatial_split_keeps_sites_and_cells_together_and_is_order_independent(
    tmp_path: Path,
) -> None:
    path = make_dataset(tmp_path)
    samples = read_samples(path)
    samples[0].site_id = samples[1].site_id
    samples[2].h3_r8 = samples[1].h3_r8
    groups, splits = spatial_split(samples)
    assert groups[0] == groups[1] == groups[2]
    assert splits[0] == splits[1] == splits[2]
    reverse_groups, reverse_splits = spatial_split(list(reversed(samples)))
    assert list(reversed(reverse_groups)) == groups
    assert list(reversed(reverse_splits)) == splits
    assert not (
        {g for g, s in zip(groups, splits, strict=True) if s == "train"}
        & {g for g, s in zip(groups, splits, strict=True) if s == "test"}
    )


def test_images_reject_path_escape_bad_crop_and_exposure(tmp_path: Path) -> None:
    sample = observation(read_samples(make_dataset(tmp_path, 1))[0])
    sample.image_path = "../outside.jpg"
    with pytest.raises(ValueError, match="inside"):
        image_features(sample, tmp_path)
    sample.image_path = "photo-0.jpg"
    sample.soil_roi = (0, 0, 200, 200)
    with pytest.raises(ValueError, match="outside"):
        image_features(sample, tmp_path)
    sample.soil_roi = (0, 0, 64, 64)
    Image.new("RGB", (64, 64), "white").save(tmp_path / sample.image_path)
    with pytest.raises(ValueError, match="exposure"):
        image_features(sample, tmp_path)


def test_conformal_uses_one_maximum_per_block_and_rejects_too_few_blocks() -> None:
    assert conformal_radius(np.array([1, 2, 3]), ["a", "b", "c"]) is None
    assert conformal_radius(np.array([1, 100] * 10), [str(i // 2) for i in range(20)]) == 100


def test_training_compares_baselines_but_holds_synthetic_and_small_data(tmp_path: Path) -> None:
    artifact = train_experiment(make_dataset(tmp_path))
    report = artifact["report"]
    assert report["status"] == "HOLD"
    assert report["public_release_approved"] is False
    assert "synthetic_data_present" in report["reasons"]
    assert "insufficient_train_blocks" in report["reasons"]
    assert set(report["comparison"]) == {"map_only", "image_only", "prior_context", "combined"}
    json.dumps(artifact, allow_nan=False)


def test_test_labels_never_change_model_or_calibration(tmp_path: Path) -> None:
    path = make_dataset(tmp_path, 50)
    before = train_experiment(path)
    held_out = {r["sample_id"] for r in before["report"]["split_manifest"] if r["split"] == "test"}
    rows = read_rows(path)
    for row in rows:
        if row["sample_id"] in held_out:
            row["lab"]["value"] = 999
    write_rows(path, rows)
    after = train_experiment(path)
    assert before["models"] == after["models"]
    assert before["conformal_radius"] == after["conformal_radius"]
    assert before["dataset_sha256"] != after["dataset_sha256"]
    assert before["report"]["comparison"] != after["report"]["comparison"]


def test_duplicate_images_cannot_inflate_experiment(tmp_path: Path) -> None:
    path = make_dataset(tmp_path)
    (tmp_path / "photo-1.jpg").write_bytes((tmp_path / "photo-0.jpg").read_bytes())
    with pytest.raises(ValueError, match="duplicate image"):
        train_experiment(path)


def test_absent_held_and_unfamiliar_models_withhold_corrections(tmp_path: Path) -> None:
    path = make_dataset(tmp_path)
    sample = observation(read_samples(path)[0])
    assert predict(sample, tmp_path, None)["prediction"] is None
    model = train_experiment(path)
    assert predict(sample, tmp_path, model)["reason"] == "model_on_hold"
    # Isolated unit fixture exercises inference routing; never written as a released model.
    model["report"]["status"] = "RESEARCH_CANDIDATE"
    assert predict(sample, tmp_path, model)["reason"] == "synthetic_observation"
    sample.is_synthetic = False
    sample.region = "unfamiliar"
    assert predict(sample, tmp_path, model)["reason"] == "outside_validated_scope"


def test_local_research_inference_keeps_prior_and_interval_separate(tmp_path: Path) -> None:
    path = make_dataset(tmp_path, 50)
    model = train_experiment(path)
    chosen = next(
        r["sample_id"] for r in model["report"]["split_manifest"] if r["split"] == "train"
    )
    sample = observation(next(s for s in read_samples(path) if s.sample_id == chosen))
    # An in-memory test fixture only; all real synthetic experiment artifacts remain HOLD.
    model["report"]["status"] = "RESEARCH_CANDIDATE"
    sample.is_synthetic = False
    result = predict(sample, tmp_path, model)
    assert result["status"] == "RESEARCH_ESTIMATE"
    assert result["public_release_approved"] is False
    assert result["prior"]["mean"] == 30
    assert result["prediction"]["lower"] <= result["prediction"]["value"]
    assert result["prediction"]["value"] <= result["prediction"]["upper"]


def test_offline_prior_cache_never_substitutes_another_version(tmp_path: Path) -> None:
    row = read_rows(make_dataset(tmp_path, 1))[0]
    cache = tmp_path / "priors.jsonl"
    entry = (
        json.dumps({"h3_r8": row["h3_r8"], "sampling": "h3_r8_centroid", "prior": row["prior"]})
        + "\n"
    )
    cache.write_text(entry)
    assert lookup_prior(cache, row["h3_r8"], "fixture", "test-v1").mean == 30
    with pytest.raises(ValueError, match="exactly one"):
        lookup_prior(cache, row["h3_r8"], "fixture", "stale-version")
    cache.write_text(entry * 2)
    with pytest.raises(ValueError, match="exactly one"):
        lookup_prior(cache, row["h3_r8"], "fixture", "test-v1")


def test_cli_outputs_hold_and_refuses_overwriting_experiment(tmp_path: Path) -> None:
    dataset = make_dataset(tmp_path)
    output = tmp_path / "experiment.json"
    command = [
        sys.executable,
        "-m",
        "ml",
        "train",
        "--dataset",
        str(dataset),
        "--output",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=True)  # noqa: S603
    assert json.loads(completed.stdout)["status"] == "HOLD"
    original = output.read_bytes()
    repeated = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603
    assert repeated.returncode == 2
    assert output.read_bytes() == original
