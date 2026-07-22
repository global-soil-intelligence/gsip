from __future__ import annotations

import io
import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from datasets import load_dataset
from PIL import Image

from pipeline.export import (
    ExportPhoto,
    ExportSubmission,
    Grant,
    assert_public_record,
    build_export,
)
from pipeline.qa import has_embedded_metadata


def raw_photo() -> bytes:
    image = Image.fromarray(np.full((120, 160, 3), (110, 80, 45), dtype=np.uint8))
    exif = Image.Exif()
    exif[271] = "Fixture camera"
    exif[34853] = {1: "GPS must disappear"}
    output = io.BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return output.getvalue()


def submission(*, grant: bool = True, synthetic: bool = False) -> ExportSubmission:
    return ExportSubmission(
        captured_at="2026-07-22T12:00:00Z",
        disturbed=False,
        grant=Grant("soil-friend", "ODbL-1.0", "CC-BY-SA-4.0", "2026-07-22-v1") if grant else None,
        gold_labels=(),
        h3_r6="86262b287ffffff",
        h3_r8="88262b2a37fffff",
        id="73f0400e-5c64-5a6e-90d1-6a7686935317",
        is_synthetic=synthetic,
        land_cover="cropland",
        photos=(ExportPhoto("B", "private/raw.jpg"),),
        precip_flag=False,
        priors=(
            {
                "depth_bottom_cm": 30,
                "depth_top_cm": 0,
                "property": "soc",
                "source": "soilgrids",
                "uncertainty_hi": 29.0,
                "uncertainty_lo": 8.0,
                "unit": "g/kg",
                "value": 17.0,
            },
        ),
        status="qa_pass",
        surface_condition="moist",
    )


def test_export_is_private_field_free_and_loads_with_datasets(tmp_path: Path) -> None:
    target = build_export([submission()], tmp_path, date(2026, 7, 22), lambda _: raw_photo())
    loaded = load_dataset(
        "parquet", data_files=str(target / "data" / "train.parquet"), split="train"
    )
    assert len(loaded) == 1
    assert set(loaded.column_names).isdisjoint(
        {"geom_precise", "latitude", "longitude", "contributor_id"}
    )
    exported_photo = target / loaded[0]["photos"][0]["path"]
    assert not has_embedded_metadata(exported_photo.read_bytes())
    card = (target / "README.md").read_text()
    assert "ODbL-1.0" in card
    assert "CC BY-SA 4.0" in card
    assert "soil-friend" in card


def test_export_is_idempotent_per_day(tmp_path: Path) -> None:
    first = build_export([submission()], tmp_path, date(2026, 7, 22), lambda _: raw_photo())
    first_manifest = json.loads((first / "manifest.json").read_text())
    second = build_export([submission()], tmp_path, date(2026, 7, 22), lambda _: raw_photo())
    assert json.loads((second / "manifest.json").read_text()) == first_manifest
    assert len(list((second / "photos").rglob("*.jpg"))) == 1


def test_export_rejects_missing_grant_and_private_columns(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no immutable grant"):
        build_export([submission(grant=False)], tmp_path, date(2026, 7, 22), lambda _: raw_photo())
    with pytest.raises(ValueError, match="forbidden private fields"):
        assert_public_record({"h3_r8": "safe", "geom_precise": "POINT(0 0)"})


def test_synthetic_rows_never_export(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No non-synthetic"):
        build_export(
            [submission(synthetic=True)], tmp_path, date(2026, 7, 22), lambda _: raw_photo()
        )
