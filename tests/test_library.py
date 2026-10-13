from __future__ import annotations

import copy
import json
from pathlib import Path
from uuid import UUID

import pytest

from pipeline.library import LibraryRecord, PrivateLibrary, main


def record(number: int = 1, *, kind: str = "camera_rgb") -> dict[str, object]:
    measurement: dict[str, object] = {
        "kind": "camera_rgb",
        "source_sha256": "a" * 64,
        "device_id": str(UUID(int=5)),
        "extractor_version": "rgb-summary-v1",
        "mean_rgb": [0.4, 0.3, 0.2],
        "std_rgb": [0.1, 0.1, 0.1],
        "pixel_count": 100,
        "card_present": False,
        "calibration_status": "uncalibrated",
    }
    if kind == "instrument_reflectance":
        measurement = {
            "kind": kind,
            "source_sha256": "b" * 64,
            "instrument_id": str(UUID(int=6)),
            "calibration_id": str(UUID(int=7)),
            "wavelength_nm": [450.0, 550.0, 650.0],
            "reflectance": [0.3, 0.4, 0.5],
            "uncertainty": [0.01] * 3,
        }
    return {
        "schema_version": "gsip-library-v1",
        "measurement_id": str(UUID(int=number)),
        "node_id": str(UUID(int=2)),
        "sample_id": str(UUID(int=3)),
        "grant_id": str(UUID(int=4)),
        "protocol_version": "gsip-capture-v1",
        "context": {"depth_top_cm": 0.0, "depth_bottom_cm": 5.0, "condition": "dry"},
        "consent_verified": False,
        "pairing_verified": False,
        "withdrawn": False,
        "synthetic": True,
        "holdout": False,
        "qa_status": "pending",
        "measurement": measurement,
        "labels": [],
    }


def test_both_measurements_validate_and_keep_distinct_identity() -> None:
    for kind in ("camera_rgb", "instrument_reflectance"):
        parsed = LibraryRecord.model_validate(record(kind=kind))
        assert parsed.measurement.kind == kind
        assert parsed.sample_id == UUID(int=3)


@pytest.mark.parametrize(
    "mutation",
    [
        {"latitude": 40.0},
        {"schema_version": "unknown"},
        {"synthetic": "false"},
        {"context": {"depth_top_cm": 5.0, "depth_bottom_cm": 5.0, "condition": "dry"}},
        {"context": {"depth_top_cm": 0.0, "depth_bottom_cm": float("nan"), "condition": "dry"}},
    ],
)
def test_rejects_private_field_smuggling_and_invalid_context(mutation: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        LibraryRecord.model_validate(record() | mutation)


@pytest.mark.parametrize(
    "field,value",
    [
        ("wavelength_nm", [450.0, 450.0, 650.0]),
        ("wavelength_nm", [550.0, 450.0, 650.0]),
        ("wavelength_nm", [100.0, 550.0, 650.0]),
        ("reflectance", [30.0, 40.0, 50.0]),
        ("uncertainty", [0.1, 0.1]),
        ("reflectance", [0.1, float("inf"), 0.3]),
        ("reflectance", ["0.1", 0.2, 0.3]),
    ],
)
def test_rejects_ambiguous_or_inconsistent_spectra(field: str, value: object) -> None:
    raw = record(kind="instrument_reflectance")
    measurement = raw["measurement"]
    assert isinstance(measurement, dict)
    measurement[field] = value
    with pytest.raises(ValueError):
        LibraryRecord.model_validate(raw)


def test_camera_cannot_masquerade_as_spectrum_or_calibrated_measurement() -> None:
    for added in ({"wavelength_nm": [450, 550, 650]}, {"calibration_status": "calibrated"}):
        raw = record()
        measurement = raw["measurement"]
        assert isinstance(measurement, dict)
        measurement.update(added)
        with pytest.raises(ValueError):
            LibraryRecord.model_validate(raw)


def test_store_is_private_idempotent_and_refuses_conflicting_ids(tmp_path: Path) -> None:
    root = tmp_path / "library"
    store = PrivateLibrary(root)
    parsed = LibraryRecord.model_validate(record())
    assert store.add(parsed) is True
    assert store.add(parsed) is False
    changed = copy.deepcopy(record())
    changed["synthetic"] = False
    with pytest.raises(ValueError):
        store.add(LibraryRecord.model_validate(changed))
    assert len(store.records()) == 1
    assert root.stat().st_mode & 0o077 == 0
    assert all(p.stat().st_mode & 0o077 == 0 for p in root.iterdir())


def test_sample_wide_withdrawal_removes_records_and_blocks_reimport(tmp_path: Path) -> None:
    store = PrivateLibrary(tmp_path / "library")
    for n in (10, 11):
        store.add(LibraryRecord.model_validate(record(n)))
    assert store.withdraw(UUID(int=2), UUID(int=3)) == 2
    assert store.records() == []
    with pytest.raises(ValueError):
        PrivateLibrary(store.root).add(LibraryRecord.model_validate(record(12)))


def test_symlinks_and_public_store_are_refused(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        PrivateLibrary(link)
    target.chmod(0o755)
    with pytest.raises(ValueError):
        PrivateLibrary(target)


def test_cli_never_echoes_invalid_payload_or_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    incoming = tmp_path / "private-incoming.json"
    incoming.write_text(json.dumps(record() | {"private_note": "NEVER-ECHO-THIS"}))
    assert main(["--store", str(tmp_path / "library"), "import", str(incoming)]) == 1
    output = capsys.readouterr()
    assert "NEVER-ECHO-THIS" not in output.out + output.err
    assert str(incoming) not in output.out + output.err
    assert "invalid" in output.err.lower()
