from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

import pytest
from test_library import record

from ml.library_baseline import prepare_pairs, run_baseline
from pipeline.library import LibraryRecord


def pairs(count: int = 12) -> list[LibraryRecord]:
    result = []
    for sample in range(count):
        for index, kind in enumerate(("camera_rgb", "instrument_reflectance")):
            raw = record(100 + sample * 2 + index, kind=kind)
            raw.update(
                sample_id=str(UUID(int=1000 + sample)),
                consent_verified=True,
                pairing_verified=True,
                qa_status="pass",
            )
            measurement = raw["measurement"]
            assert isinstance(measurement, dict)
            measurement["source_sha256"] = hashlib.sha256(f"{sample}-{kind}".encode()).hexdigest()
            if kind == "camera_rgb":
                measurement["mean_rgb"] = [0.1 + sample * 0.03, 0.2, 0.3]
            else:
                measurement["reflectance"] = [0.2 + sample * 0.02, 0.3, 0.4]
            result.append(LibraryRecord.model_validate(raw))
    return result


def changed(row: LibraryRecord, **updates: object) -> LibraryRecord:
    return LibraryRecord.model_validate(row.model_dump() | updates)


def test_sample_rights_and_holdout_propagate_to_all_measurements() -> None:
    rows = pairs()
    for i, flag in enumerate(("withdrawn", "holdout")):
        rows[i * 2] = changed(rows[i * 2], **{flag: True})
    rows[4] = changed(rows[4], consent_verified=False)
    rows[6] = changed(rows[6], pairing_verified=False)
    rows[8] = changed(rows[8], qa_status="fail")
    prepared = prepare_pairs(rows, demo=True)
    assert len(prepared) == 7
    assert all(pair.key[1].int >= 1005 for pair in prepared)


def test_synthetic_data_cannot_enter_field_pairs() -> None:
    assert prepare_pairs(pairs(), demo=False) == []


def test_multiple_camera_measurements_need_explicit_aggregation_protocol() -> None:
    rows = pairs()
    rows.append(changed(rows[0], measurement_id=UUID(int=9000)))
    with pytest.raises(ValueError):
        prepare_pairs(rows, demo=True)


def test_cross_sample_duplicate_source_cannot_leak_between_partitions() -> None:
    rows = pairs()
    measurement = rows[2].measurement.model_dump() | {
        "source_sha256": rows[0].measurement.source_sha256
    }
    rows[2] = changed(rows[2], measurement=measurement)
    with pytest.raises(ValueError):
        prepare_pairs(rows, demo=True)


@pytest.mark.parametrize("source_index", [0, 1], ids=["camera", "instrument"])
@pytest.mark.parametrize(
    "excluded_state",
    [
        pytest.param({"holdout": True}, id="holdout"),
        pytest.param({"withdrawn": True}, id="withdrawn"),
        pytest.param({"consent_verified": False}, id="unconsented"),
        pytest.param({"pairing_verified": False}, id="unpaired"),
        pytest.param({"qa_status": "fail"}, id="failed-qa"),
    ],
)
def test_excluded_sample_sources_cannot_enter_training_as_another_sample(
    source_index: int, excluded_state: dict[str, object]
) -> None:
    rows = pairs()
    rows[source_index] = changed(rows[source_index], **excluded_state)
    twin_index = 2 + source_index
    rows[twin_index] = changed(
        rows[twin_index],
        measurement=rows[twin_index].measurement.model_dump()
        | {"source_sha256": rows[source_index].measurement.source_sha256},
    )
    with pytest.raises(ValueError, match="repeated source across physical sample identities"):
        prepare_pairs(rows, demo=True)


@pytest.mark.parametrize("source_index", [0, 1], ids=["camera-only", "instrument-only"])
def test_incomplete_pair_sources_cannot_enter_as_another_sample(source_index: int) -> None:
    rows = pairs()
    twin_index = 2 + source_index
    rows[twin_index] = changed(
        rows[twin_index],
        measurement=rows[twin_index].measurement.model_dump()
        | {"source_sha256": rows[source_index].measurement.source_sha256},
    )
    del rows[1 - source_index]
    with pytest.raises(ValueError, match="repeated source across physical sample identities"):
        prepare_pairs(rows, demo=True)


def test_wavelength_grid_and_context_mismatches_are_refused() -> None:
    for update in ({"wavelength_nm": [460.0, 550.0, 650.0]},):
        rows = pairs()
        rows[1] = changed(rows[1], measurement=rows[1].measurement.model_dump() | update)
        with pytest.raises(ValueError):
            prepare_pairs(rows, demo=True)
    rows = pairs()
    rows[1] = changed(
        rows[1], context={"depth_top_cm": 0.0, "depth_bottom_cm": 10.0, "condition": "dry"}
    )
    with pytest.raises(ValueError):
        prepare_pairs(rows, demo=True)


def test_baseline_is_order_independent_with_disjoint_samples_and_private_output(
    tmp_path: Path,
) -> None:
    first = run_baseline(pairs(), tmp_path / "first", demo=True)
    second = run_baseline(list(reversed(pairs())), tmp_path / "second", demo=True)
    assert first == second
    assert first["scientific_validation"] is False
    assert first["train_samples"] + first["development_samples"] == 12
    assert first["sample_overlap"] == 0
    assert first["development_rmse"] < 0.05
    assert (tmp_path / "first").stat().st_mode & 0o077 == 0
    assert all(p.stat().st_mode & 0o077 == 0 for p in (tmp_path / "first").iterdir())


def test_demo_run_does_not_overwrite_previous_evidence(tmp_path: Path) -> None:
    run_baseline(pairs(), tmp_path / "receipt", demo=True)
    with pytest.raises(ValueError):
        run_baseline(pairs(), tmp_path / "receipt", demo=True)


def test_field_training_is_blocked_pending_server_and_screening_verification(
    tmp_path: Path,
) -> None:
    rows = [changed(r, synthetic=False) for r in pairs()]
    with pytest.raises(ValueError):
        run_baseline(rows, tmp_path / "field", demo=False)
    assert not (tmp_path / "field").exists()


def test_runnable_demo_uses_phone_extractor_and_private_node(tmp_path: Path) -> None:
    from pipeline.library import PrivateLibrary
    from pipeline.library_demo import demo

    result = demo(tmp_path / "demo")
    assert result["paired_samples"] == 12
    assert result["scientific_validation"] is False
    stored = PrivateLibrary(tmp_path / "demo" / "records").records()
    assert len(stored) == 24
    assert all(r.synthetic for r in stored)
