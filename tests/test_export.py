from __future__ import annotations

import io
import json
import random
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, cast

import h3  # type: ignore[import-untyped]
import httpx
import numpy as np
import pytest
from datasets import load_dataset  # type: ignore[import-untyped]
from PIL import Image

from pipeline.export import (
    ExportPhoto,
    ExportPrivacyError,
    ExportResult,
    ExportSubmission,
    Grant,
    QaCheck,
    SupabaseExportSource,
    assert_public_record,
    build_export,
    publish_export,
)
from pipeline.k_anonymity import Observation, PublishedCell, assign_cells
from pipeline.qa import has_embedded_metadata, sanitize_jpeg

BURLINGTON = h3.latlng_to_cell(44.4759, -73.2121, 8)
R6_PARENT = h3.cell_to_parent(BURLINGTON, 6)
R4_PARENT = h3.cell_to_parent(BURLINGTON, 4)
SIBLINGS_R8 = sorted(h3.cell_to_children(R6_PARENT, 8))
OTHER_R6_CELLS = sorted(set(h3.cell_to_children(R4_PARENT, 6)) - {R6_PARENT})
EXPORT_DATE = date(2026, 7, 22)


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


def photo(shot: str, submission_id: str, qa_status: str = "pass") -> ExportPhoto:
    return ExportPhoto(
        shot_type=shot,
        storage_path=f"private/{submission_id}/{shot}.jpg",
        qa_status=qa_status,
        calibration_status="calibrated",
        qa_checks=(QaCheck("sharpness", True, 120.5), QaCheck("gps_plausibility", True, None)),
        qa_model_version="deterministic-v2",
    )


def submission(
    index: int = 1,
    *,
    contributor: str | None = None,
    h3_r8: str = BURLINGTON,
    grant: bool = True,
    synthetic: bool = False,
    photos: tuple[ExportPhoto, ...] | None = None,
    captured_at: str = "2026-07-22T12:00:00Z",
) -> ExportSubmission:
    submission_id = f"73f0400e-5c64-5a6e-90d1-{index:012d}"
    return ExportSubmission(
        captured_at=captured_at,
        contributor_id=contributor or f"contributor-{index}",
        disturbed=False,
        grant=Grant("soil-friend", "ODbL-1.0", "CC-BY-SA-4.0", "2026-07-22-v1") if grant else None,
        gold_labels=(),
        h3_r6=h3.cell_to_parent(h3_r8, 6),
        h3_r8=h3_r8,
        id=submission_id,
        is_synthetic=synthetic,
        land_cover="cropland",
        photos=photos
        if photos is not None
        else (photo("A", submission_id), photo("B", submission_id)),
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


def three_contributors_in_one_cell() -> list[ExportSubmission]:
    return [submission(index) for index in (1, 2, 3)]


def build(
    submissions: list[ExportSubmission],
    root: Path,
    loader: Any = None,
) -> ExportResult:
    return build_export(submissions, root, EXPORT_DATE, loader or (lambda _: clean_photo()))


def test_export_is_private_field_free_and_loads_with_datasets(tmp_path: Path) -> None:
    result = build(three_contributors_in_one_cell(), tmp_path)
    loaded = load_dataset(
        "parquet", data_files=str(result.target / "data" / "train.parquet"), split="train"
    )
    assert len(loaded) == 3
    assert set(loaded.column_names).isdisjoint(
        {"geom_precise", "latitude", "longitude", "contributor_id", "h3_r8", "h3_r6"}
    )
    assert loaded[0]["captured_at"] == "2026-07-22"
    assert loaded[0]["h3_cell"] == BURLINGTON
    assert loaded[0]["h3_resolution"] == 8
    first_photo = loaded[0]["photos"][0]
    assert first_photo["qa"]["model_version"] == "deterministic-v2"
    assert {"check": "sharpness", "passed": True, "score": 120.5} in first_photo["qa"]["checks"]
    assert not has_embedded_metadata((result.target / first_photo["path"]).read_bytes())
    card = (result.target / "README.md").read_text()
    assert "ODbL-1.0" in card
    assert "CC BY-SA 4.0" in card
    assert "soil-friend" in card
    assert "untrusted text" in card
    assert result.cells == (PublishedCell(BURLINGTON, 8, 3, 3, date(2026, 7, 22)),)


def test_export_is_idempotent_per_day(tmp_path: Path) -> None:
    first = build(three_contributors_in_one_cell(), tmp_path)
    first_manifest = json.loads((first.target / "manifest.json").read_text())
    second = build(three_contributors_in_one_cell(), tmp_path)
    assert json.loads((second.target / "manifest.json").read_text()) == first_manifest
    assert len(list((second.target / "photos").rglob("*.jpg"))) == 6


def test_sparse_cells_roll_up_to_resolution_6(tmp_path: Path) -> None:
    rows = [
        submission(1, h3_r8=SIBLINGS_R8[0]),
        submission(2, h3_r8=SIBLINGS_R8[0]),
        submission(3, h3_r8=SIBLINGS_R8[5]),
    ]
    result = build(rows, tmp_path)
    loaded = load_dataset(
        "parquet", data_files=str(result.target / "data" / "train.parquet"), split="train"
    )
    assert {row["h3_cell"] for row in loaded} == {R6_PARENT}
    assert {row["h3_resolution"] for row in loaded} == {6}
    assert result.cells == (PublishedCell(R6_PARENT, 6, 3, 3, date(2026, 7, 22)),)


def test_sparser_cells_roll_up_to_resolution_4(tmp_path: Path) -> None:
    rows = [
        submission(1, h3_r8=SIBLINGS_R8[0]),
        submission(2, h3_r8=h3.cell_to_center_child(OTHER_R6_CELLS[0], 8)),
        submission(3, h3_r8=h3.cell_to_center_child(OTHER_R6_CELLS[1], 8)),
    ]
    result = build(rows, tmp_path)
    assert result.rows == 3
    assert result.cells == (PublishedCell(R4_PARENT, 4, 3, 3, date(2026, 7, 22)),)


def test_observations_below_k_everywhere_are_withheld(tmp_path: Path) -> None:
    rows = [submission(1), submission(2)]
    result = build(rows, tmp_path)
    assert result.rows == 0
    assert result.withheld == 2
    assert result.cells == ()
    assert (result.target / "data" / "EMPTY.md").is_file()
    assert not (result.target / "photos").exists() or not any((result.target / "photos").iterdir())
    assert "withheld until they meet k-anonymity: 2" in (result.target / "README.md").read_text()


def test_one_contributor_never_counts_as_several(tmp_path: Path) -> None:
    rows = [submission(index, contributor="same-person") for index in range(1, 6)]
    result = build(rows, tmp_path)
    assert result.rows == 0
    assert result.withheld == 5


def test_a_published_fine_cell_does_not_lend_contributors_to_a_coarse_one(tmp_path: Path) -> None:
    rows = [
        *three_contributors_in_one_cell(),
        submission(4, h3_r8=SIBLINGS_R8[7]),
    ]
    result = build(rows, tmp_path)
    assert result.rows == 3
    assert result.withheld == 1
    assert [cell.resolution for cell in result.cells] == [8]


def test_random_populations_never_publish_a_cell_below_k() -> None:
    generator = random.Random(20261010)  # noqa: S311 - deterministic test data
    candidates = [
        *SIBLINGS_R8[:12],
        *(h3.cell_to_center_child(cell, 8) for cell in OTHER_R6_CELLS[:10]),
    ]
    observations = [
        Observation(
            key=f"obs-{index:04d}",
            contributor=f"person-{generator.randrange(40)}",
            h3_r8=generator.choice(candidates),
            observed_on=date(2026, 7, 1 + generator.randrange(28)),
        )
        for index in range(400)
    ]
    assignment = assign_cells(observations)
    members: dict[tuple[str, int], set[str]] = defaultdict(set)
    by_key = {observation.key: observation for observation in observations}
    for key, placed in assignment.placement.items():
        members[placed].add(by_key[key].contributor)
    assert members
    assert all(len(contributors) >= 3 for contributors in members.values())
    assert {(cell.h3_index, cell.resolution) for cell in assignment.cells} == set(members)
    assert set(assignment.placement) | set(assignment.withheld) == set(by_key)
    assert set(assignment.placement).isdisjoint(assignment.withheld)


def test_an_unavailable_photo_is_set_aside_and_the_release_continues(tmp_path: Path) -> None:
    rows = [*three_contributors_in_one_cell(), submission(4), submission(5)]
    broken = rows[0].id

    def loader(path: str) -> bytes:
        if broken in path:
            request = httpx.Request("GET", "https://supabase.test/storage")
            raise httpx.HTTPStatusError(
                "missing", request=request, response=httpx.Response(404, request=request)
            )
        return clean_photo()

    result = build(rows, tmp_path, loader)
    assert result.set_aside == {"photo_unavailable": 1}
    assert result.rows == 4
    assert not (result.target / "photos" / broken).exists()


def test_a_set_aside_row_cannot_leave_a_published_cell_below_k(tmp_path: Path) -> None:
    rows = three_contributors_in_one_cell()
    corrupt = rows[0].id
    result = build(rows, tmp_path, lambda path: b"not a jpeg" if corrupt in path else clean_photo())
    assert result.set_aside == {"photo_unreadable": 1}
    assert result.rows == 0
    assert result.withheld == 2


def test_only_photos_that_passed_qa_are_released(tmp_path: Path) -> None:
    rows = three_contributors_in_one_cell()
    first = rows[0]
    rows[0] = ExportSubmission(
        **{
            **first.__dict__,
            "photos": (
                photo("A", first.id),
                photo("B", first.id),
                photo("C", first.id, qa_status="fail"),
            ),
        }
    )
    result = build(rows, tmp_path)
    loaded = load_dataset(
        "parquet", data_files=str(result.target / "data" / "train.parquet"), split="train"
    )
    released = next(row for row in loaded if row["id"] == first.id)
    assert [item["shot_type"] for item in released["photos"]] == ["A", "B"]
    assert not (result.target / "photos" / first.id / "C.jpg").exists()


def test_missing_grant_is_set_aside_not_published(tmp_path: Path) -> None:
    rows = [*three_contributors_in_one_cell(), submission(4, grant=False)]
    result = build(rows, tmp_path)
    assert result.set_aside == {"missing_grant": 1}
    assert result.rows == 3


def test_private_columns_are_refused() -> None:
    with pytest.raises(ExportPrivacyError, match="forbidden private fields"):
        assert_public_record({"h3_cell": "safe", "geom_precise": "POINT(0 0)"})
    with pytest.raises(ExportPrivacyError, match="forbidden private fields"):
        assert_public_record({"h3_cell": "safe", "h3_r8": BURLINGTON})


def test_dirty_canonical_photo_aborts_before_any_public_artifact(tmp_path: Path) -> None:
    with pytest.raises(ExportPrivacyError, match="embedded metadata"):
        build(three_contributors_in_one_cell(), tmp_path, lambda _: dirty_photo())
    assert not (tmp_path / "2026-07-22").exists()
    assert not (tmp_path / ".2026-07-22.building").exists()


def test_synthetic_only_export_is_an_explicit_empty_success(tmp_path: Path) -> None:
    result = build([submission(synthetic=True)], tmp_path)
    assert (result.target / "data" / "EMPTY.md").is_file()
    assert not (result.target / "data" / "train.parquet").exists()
    assert "Rows: 0" in (result.target / "README.md").read_text()


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


def test_source_attaches_per_photo_qa_and_keeps_the_contributor_private() -> None:
    submission_id = "73f0400e-5c64-5a6e-90d1-000000000001"
    tables: dict[str, list[dict[str, Any]]] = {
        "submissions": [
            {
                "captured_at": "2026-07-22T12:00:00+00:00",
                "contributor_id": "c-1",
                "disturbed": False,
                "grant_id": "g-1",
                "h3_r6": R6_PARENT,
                "h3_r8": BURLINGTON,
                "id": submission_id,
                "is_synthetic": False,
                "land_cover": "cropland",
                "precip_flag": None,
                "status": "qa_pass",
                "surface_condition": "dry",
            }
        ],
        "contribution_grants": [
            {
                "attribution_name": "Anonymous soil contributor",
                "data_license": "ODbL-1.0",
                "photo_license": "CC-BY-SA-4.0",
                "terms_version": "v1",
            }
        ],
        "qa_events": [
            {
                "check_name": "sharpness_B",
                "passed": True,
                "score": 88.0,
                "model_version": "deterministic-v2",
            },
            {
                "check_name": "soil_region_B",
                "passed": True,
                "score": 0.8,
                "model_version": "deterministic-v2",
            },
            {
                "check_name": "sharpness_A",
                "passed": False,
                "score": 3.0,
                "model_version": "deterministic-v2",
            },
        ],
        "photos": [
            {
                "calibration_status": "calibrated",
                "qa_status": "fail",
                "shot_type": "A",
                "storage_path": "p/A.jpg",
            },
            {
                "calibration_status": "uncalibrated",
                "qa_status": "pass",
                "shot_type": "B",
                "storage_path": "p/B.jpg",
            },
        ],
        "priors": [],
        "gold_labels": [],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        table = request.url.path.rsplit("/", 1)[-1]
        body = tables[table]
        return httpx.Response(
            200, headers={"Content-Range": f"0-{len(body) - 1}/{len(body)}"}, json=body
        )

    source = SupabaseExportSource("https://supabase.test", "service-key")
    source.client.close()
    source.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        [loaded] = source.submissions()
    finally:
        source.client.close()
    assert loaded.contributor_id == "c-1"
    shot_b = next(item for item in loaded.photos if item.shot_type == "B")
    assert shot_b.qa_status == "pass"
    assert shot_b.qa_model_version == "deterministic-v2"
    assert {check.check for check in shot_b.qa_checks} == {"sharpness", "soil_region"}


def test_hub_replacement_precedes_atomic_public_cell_refresh(tmp_path: Path) -> None:
    events: list[str] = []
    upload: dict[str, Any] = {}
    result = build(three_contributors_in_one_cell(), tmp_path)

    class FakeHub:
        def upload_folder(self, **kwargs: Any) -> None:
            events.append("hub")
            upload.update(kwargs)

    class RecordingSource(SupabaseExportSource):
        def refresh_h3_cells(self, cells: tuple[PublishedCell, ...]) -> None:
            events.append("cells")

    source = RecordingSource("https://supabase.test", "service-key")
    try:
        publish_export(source, result, EXPORT_DATE, "token", "org/dataset", cast(Any, FakeHub()))
    finally:
        source.client.close()
    assert events == ["hub", "cells"]
    assert upload["delete_patterns"] == ["photos/**", "data/**"]
    assert upload["folder_path"] == result.target


def test_failed_post_upload_refresh_is_retried_on_the_next_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploads = 0
    refreshed: list[tuple[PublishedCell, ...]] = []
    result = build(three_contributors_in_one_cell(), tmp_path)

    class FakeHub:
        def upload_folder(self, **kwargs: Any) -> None:
            nonlocal uploads
            uploads += 1

    class RecoveringSource(SupabaseExportSource):
        failures_remaining = 3

        def refresh_h3_cells(self, cells: tuple[PublishedCell, ...]) -> None:
            if self.failures_remaining:
                self.failures_remaining -= 1
                request = httpx.Request("POST", f"{self.url}/rest/v1/rpc/refresh_public_h3_cells")
                response = httpx.Response(500, request=request)
                raise httpx.HTTPStatusError(
                    "refresh failed",
                    request=request,
                    response=response,
                )
            refreshed.append(cells)

    monkeypatch.setattr("pipeline.export.time.sleep", lambda _: None)
    source = RecoveringSource("https://supabase.test", "service-key")
    try:
        with pytest.raises(httpx.HTTPStatusError):
            publish_export(
                source, result, EXPORT_DATE, "token", "org/dataset", cast(Any, FakeHub())
            )
        publish_export(
            source, result, date(2026, 7, 23), "token", "org/dataset", cast(Any, FakeHub())
        )
    finally:
        source.client.close()

    assert uploads == 2
    assert refreshed == [result.cells]


def test_public_cell_refresh_sends_k_anonymous_cells_and_clears_an_empty_release() -> None:
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/rpc/refresh_public_h3_cells"
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=1)

    source = SupabaseExportSource("https://supabase.test", "service-key")
    source.client.close()
    source.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        source.refresh_h3_cells(())
        source.refresh_h3_cells((PublishedCell(R6_PARENT, 6, 4, 3, date(2026, 7, 22)),))
    finally:
        source.client.close()
    assert requests[0] == {"payload": []}
    assert requests[1] == {
        "payload": [
            {
                "h3_index": R6_PARENT,
                "latest_submission_date": "2026-07-22",
                "n_contributors": 3,
                "n_submissions": 4,
                "resolution": 6,
            }
        ]
    }
