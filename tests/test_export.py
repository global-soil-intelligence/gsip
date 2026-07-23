from __future__ import annotations

import io
import json
from datetime import date
from pathlib import Path
from typing import Any, cast

import httpx
import numpy as np
import pytest
from datasets import load_dataset
from PIL import Image

from pipeline.export import (
    ExportPhoto,
    ExportSubmission,
    Grant,
    SupabaseExportSource,
    assert_public_record,
    build_export,
    publish_export,
)
from pipeline.qa import has_embedded_metadata, sanitize_jpeg


def raw_photo() -> bytes:
    image = Image.fromarray(np.full((120, 160, 3), (110, 80, 45), dtype=np.uint8))
    exif = Image.Exif()
    exif[271] = "Fixture camera"
    exif[34853] = {1: "GPS must disappear"}
    output = io.BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return output.getvalue()


def clean_photo() -> bytes:
    return sanitize_jpeg(raw_photo())[0]


def jpeg_segment(marker: int, payload: bytes) -> bytes:
    return b"\xff" + bytes([marker]) + (len(payload) + 2).to_bytes(2, "big") + payload


def dirty_photo() -> bytes:
    segments = (
        jpeg_segment(0xFE, b"GPS 40.446 -79.982 serial=ABC"),
        jpeg_segment(
            0xE1,
            b"http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta>owner</x:xmpmeta>",
        ),
        jpeg_segment(0xE2, b"ICC_PROFILE\x00\x01\x01private-profile"),
    )
    raw = raw_photo()
    return raw[:2] + b"".join(segments) + raw[2:]


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
    target = build_export([submission()], tmp_path, date(2026, 7, 22), lambda _: clean_photo())
    loaded = load_dataset(
        "parquet", data_files=str(target / "data" / "train.parquet"), split="train"
    )
    assert len(loaded) == 1
    assert set(loaded.column_names).isdisjoint(
        {"geom_precise", "latitude", "longitude", "contributor_id"}
    )
    assert loaded[0]["captured_at"] == "2026-07-22"
    exported_photo = target / loaded[0]["photos"][0]["path"]
    assert not has_embedded_metadata(exported_photo.read_bytes())
    card = (target / "README.md").read_text()
    assert "ODbL-1.0" in card
    assert "CC BY-SA 4.0" in card
    assert "soil-friend" in card


def test_export_is_idempotent_per_day(tmp_path: Path) -> None:
    first = build_export([submission()], tmp_path, date(2026, 7, 22), lambda _: clean_photo())
    first_manifest = json.loads((first / "manifest.json").read_text())
    second = build_export([submission()], tmp_path, date(2026, 7, 22), lambda _: clean_photo())
    assert json.loads((second / "manifest.json").read_text()) == first_manifest
    assert len(list((second / "photos").rglob("*.jpg"))) == 1


def test_export_rejects_missing_grant_and_private_columns(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no immutable grant"):
        build_export(
            [submission(grant=False)], tmp_path, date(2026, 7, 22), lambda _: clean_photo()
        )
    with pytest.raises(ValueError, match="forbidden private fields"):
        assert_public_record({"h3_r8": "safe", "geom_precise": "POINT(0 0)"})


def test_dirty_canonical_photo_aborts_before_any_public_artifact(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="embedded metadata"):
        build_export([submission()], tmp_path, date(2026, 7, 22), lambda _: dirty_photo())
    assert not (tmp_path / "2026-07-22").exists()
    assert not (tmp_path / ".2026-07-22.building").exists()


def test_synthetic_only_export_is_an_explicit_empty_success(tmp_path: Path) -> None:
    target = build_export(
        [submission(synthetic=True)], tmp_path, date(2026, 7, 22), lambda _: clean_photo()
    )
    assert (target / "data" / "EMPTY.md").is_file()
    assert not (target / "data" / "train.parquet").exists()
    assert "Rows: 0" in (target / "README.md").read_text()


def test_postgrest_reads_all_1001_rows() -> None:
    rows = [{"id": index} for index in range(1001)]
    ranges: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested = request.headers["range"]
        ranges.append(requested)
        start, end = (int(value) for value in requested.split("-"))
        page = rows[start : end + 1]
        last = start + len(page) - 1
        content_range = f"{start}-{last}/{len(rows)}" if page else f"*/{len(rows)}"
        return httpx.Response(200, headers={"Content-Range": content_range}, json=page)

    source = SupabaseExportSource("https://supabase.test", "service-key")
    source.client.close()
    source.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        assert source._rows("submissions?select=id") == rows
    finally:
        source.client.close()
    assert ranges == ["0-999", "1000-1999"]


def test_hub_replacement_precedes_atomic_public_cell_refresh(tmp_path: Path) -> None:
    events: list[str] = []
    upload: dict[str, Any] = {}

    class FakeHub:
        def upload_folder(self, **kwargs: Any) -> None:
            events.append("hub")
            upload.update(kwargs)

    source = SupabaseExportSource("https://supabase.test", "service-key")
    source.refresh_h3_cells = lambda _: events.append("cells")  # type: ignore[method-assign]
    try:
        publish_export(
            source,
            [submission()],
            tmp_path,
            date(2026, 7, 22),
            "token",
            "org/dataset",
            cast(Any, FakeHub()),
        )
    finally:
        source.client.close()
    assert events == ["hub", "cells"]
    assert upload["delete_patterns"] == ["photos/**", "data/**"]


def test_public_cell_refresh_includes_dates_and_clears_an_empty_release() -> None:
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/rpc/refresh_public_h3_cells"
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=1)

    source = SupabaseExportSource("https://supabase.test", "service-key")
    source.client.close()
    source.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        source.refresh_h3_cells([])
        source.refresh_h3_cells([submission()])
    finally:
        source.client.close()
    assert requests[0] == {"payload": []}
    assert requests[1] == {
        "payload": [
            {
                "h3_index": "88262b2a37fffff",
                "latest_submission_date": "2026-07-22",
                "n_submissions": 1,
            }
        ]
    }
