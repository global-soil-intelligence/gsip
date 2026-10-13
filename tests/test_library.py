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


def test_withdrawn_measurement_identity_cannot_be_reassigned(tmp_path: Path) -> None:
    store = PrivateLibrary(tmp_path / "library")
    for number in (10, 11):
        store.add(LibraryRecord.model_validate(record(number)))
    assert store.withdraw(UUID(int=2), UUID(int=3)) == 2
    reopened = PrivateLibrary(store.root)
    for number in (10, 11):
        changed = copy.deepcopy(record(number))
        changed["node_id"] = str(UUID(int=80))
        changed["sample_id"] = str(UUID(int=90))
        changed["synthetic"] = False
        with pytest.raises(ValueError):
            reopened.add(LibraryRecord.model_validate(changed))
    # A different measurement still cannot revive the withdrawn sample key.
    with pytest.raises(ValueError):
        reopened.add(LibraryRecord.model_validate(record(12)))
    assert reopened.records() == []
    assert not list(reopened.root.glob("*.json"))
    unrelated = record(90) | {"node_id": str(UUID(int=80)), "sample_id": str(UUID(int=90))}
    assert reopened.add(LibraryRecord.model_validate(unrelated)) is True
    assert len(reopened.records()) == 1


def test_withdrawal_identity_marker_precedes_record_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = PrivateLibrary(tmp_path / "library")
    original = LibraryRecord.model_validate(record())
    store.add(original)
    original_unlink = Path.unlink

    def fail_record_deletion(path: Path, missing_ok: bool = False) -> None:
        if path == store.root / f"{original.measurement_id}.json":
            raise OSError("simulated interruption")
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_record_deletion)
    with pytest.raises(OSError):
        store.withdraw(original.node_id, original.sample_id)
    marker = store.root / f"withdrawn-measurement-{original.measurement_id}"
    assert marker.read_bytes() == b"withdrawn\n"
    assert marker.stat().st_mode & 0o077 == 0
    assert store.records() == []
    monkeypatch.setattr(Path, "unlink", original_unlink)
    assert store.withdraw(original.node_id, original.sample_id) == 1
    changed = copy.deepcopy(record())
    changed["sample_id"] = str(UUID(int=90))
    with pytest.raises(ValueError):
        PrivateLibrary(store.root).add(LibraryRecord.model_validate(changed))


@pytest.mark.parametrize("invalid_field", ["consent_verified", "measurement_id", "measurement"])
def test_store_revalidates_copied_models_without_logging_values(
    tmp_path: Path, invalid_field: str, capsys: pytest.CaptureFixture[str]
) -> None:
    import warnings

    store = PrivateLibrary(tmp_path / "library")
    original = LibraryRecord.model_validate(record())
    replacement: object = "NEVER-ECHO-THIS"
    if invalid_field == "measurement":
        replacement = original.measurement.model_copy(update={"source_sha256": replacement})
    invalid = original.model_copy(update={invalid_field: replacement})
    with warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter("always")
        with pytest.raises(ValueError):
            store.add(invalid)
    assert emitted == []
    output = capsys.readouterr()
    assert "NEVER-ECHO-THIS" not in output.out + output.err
    assert store.records() == []
    assert not list(store.root.glob("*.json"))


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


@pytest.mark.parametrize("field", ["--node", "--sample"])
def test_cli_malformed_withdrawal_identifier_is_generic(
    tmp_path: Path, field: str, capsys: pytest.CaptureFixture[str]
) -> None:
    identifiers = {"--node": str(UUID(int=2)), "--sample": str(UUID(int=3))}
    identifiers[field] = "NEVER-ECHO-THIS"
    with pytest.raises(SystemExit) as stopped:
        main(
            [
                "--store",
                str(tmp_path / "library"),
                "withdraw",
                "--node",
                identifiers["--node"],
                "--sample",
                identifiers["--sample"],
            ]
        )
    assert stopped.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "NEVER-ECHO-THIS" not in output.err
    assert str(tmp_path) not in output.err
    assert "invalid" in output.err.lower()
    assert not (tmp_path / "library").exists()


def test_concurrent_identical_import_is_single_write(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    store = PrivateLibrary(tmp_path / "library")
    incoming = LibraryRecord.model_validate(record())
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: store.add(incoming), range(12)))
    assert sum(results) == 1
    assert len(store.records()) == 1


def test_invalid_label_units_and_spectral_camera_fields_fail() -> None:
    raw = record()
    raw["labels"] = [
        {
            "property": "ph",
            "unit": "g/kg",
            "value": 7.0,
            "uncertainty": 0.1,
            "method_id": str(UUID(int=6)),
            "verifier_id": str(UUID(int=7)),
        }
    ]
    with pytest.raises(ValueError):
        LibraryRecord.model_validate(raw)


def test_duplicate_json_fields_cannot_change_measurement_meaning(tmp_path: Path) -> None:
    from pipeline.library import read_record

    incoming = tmp_path / "duplicate.json"
    data = json.dumps(record())
    incoming.write_text(data[:-1] + ', "synthetic": false}')
    with pytest.raises(ValueError):
        read_record(incoming)


def test_crash_leftovers_are_removed_before_withdrawal(tmp_path: Path) -> None:
    store = PrivateLibrary(tmp_path / "library")
    store.add(LibraryRecord.model_validate(record()))
    orphan = store.root / ".pending-crashed-write"
    orphan.write_bytes(b"private incomplete record")
    orphan.chmod(0o600)
    store.withdraw(UUID(int=2), UUID(int=3))
    assert not orphan.exists()
    assert store.records() == []
