from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

from card.design import MARKER_ID
from card.fixtures import canonical_card
from pipeline.photo_privacy import (
    ScreenEngine,
    benchmark_configuration,
    card_mask,
    decode_sanitized,
    views,
)
from pipeline.photo_privacy_calibrate import CalibrationManifest, evaluate_staged, wilson
from pipeline.privacy_contract import (
    MAX_WIRE_BYTES,
    CardExclusion,
    Outcome,
    PrivacyCapabilities,
    PrivacyError,
    decode_json,
    validate,
)
from pipeline.privacy_io import PrivateDirectory
from pipeline.privacy_review import human_decision
from pipeline.privacy_review import main as review_main


class NoCandidates:
    def faces(self, image: np.ndarray) -> list[Any]:
        return []

    def texts(self, image: np.ndarray) -> list[Any]:
        return []


def jpeg(value: np.ndarray) -> bytes:
    _, data = cv2.imencode(".jpg", value, [cv2.IMWRITE_JPEG_QUALITY, 94])
    return data.tobytes()


def test_complete_card_pixels_remain_screened_until_verification_exists() -> None:
    value = np.full((768, 768, 3), 210, np.uint8)
    value[70:520, 80:400] = cv2.resize(canonical_card(), (320, 450))
    original = decode_sanitized(jpeg(value))
    config = benchmark_configuration()
    mask, evidence = card_mask(original, config)
    assert evidence is None and mask.dtype == np.uint8 and not mask.any()

    class Capture(NoCandidates):
        def __init__(self) -> None:
            self.face_views: list[np.ndarray] = []
            self.text_views: list[np.ndarray] = []

        def faces(self, image: np.ndarray) -> list[Any]:
            self.face_views.append(image.copy())
            return []

        def texts(self, image: np.ndarray) -> list[Any]:
            self.text_views.append(image.copy())
            return []

    backend = Capture()
    result = ScreenEngine(config, backend).screen(jpeg(value))
    assert result.card_exclusion == evidence
    expected = original.copy()
    expected[mask == 1] = 0
    assert np.array_equal(backend.face_views[0], original[:640, :640])
    assert np.array_equal(backend.text_views[0], expected[:640, :640])
    assert np.array_equal(expected[mask == 0], original[mask == 0])


def test_partial_card_does_not_guess_exclusion() -> None:
    value = np.full((768, 768, 3), 210, np.uint8)
    value[70:520, 80:400] = cv2.resize(canonical_card(), (320, 450))
    _, evidence = card_mask(value[200:, :], benchmark_configuration())
    assert evidence is None
    mask, evidence = card_mask(value, benchmark_configuration())
    assert evidence is None and not mask.any()


def test_full_resolution_tile_coverage_reaches_every_frame_pixel() -> None:
    h, w = 960, 1280
    ids = np.arange(h * w, dtype=np.uint32).reshape(h, w)
    image = np.stack((ids & 255, (ids >> 8) & 255, (ids >> 16) & 255), axis=2).astype(np.uint8)
    coverage = np.zeros(h * w, dtype=bool)
    full_scale_view_count = ((w + 511) // 512) * ((h + 511) // 512)
    for view in list(views(image, benchmark_configuration()))[:full_scale_view_count]:
        decoded = (
            view[:, :, 0].astype(np.uint32)
            + (view[:, :, 1].astype(np.uint32) << 8)
            + (view[:, :, 2].astype(np.uint32) << 16)
        )
        coverage[decoded.ravel()] = True
    assert coverage.all()


@pytest.mark.parametrize(
    "changed",
    [
        {"candidates": True},
        {"candidates": 1, "result": "pass"},
        {"candidates": 0, "result": "flag"},
        {"candidates": 10_001},
    ],
)
def test_outcome_strict_and_bounded(changed: dict[str, Any]) -> None:
    with pytest.raises(PrivacyError):
        validate(Outcome, {"result": "pass", "candidates": 0, **changed})


@pytest.mark.parametrize(
    "changed",
    [
        {"publication_open": "true"},
        {"publication_open": True},
        {"policy_revision": False},
        {"private_value": "fictional-only"},
    ],
)
def test_capabilities_missing_policy_is_closed_and_strict(changed: dict[str, Any]) -> None:
    base = {
        "version": "gsip-photo-privacy-v1",
        "publication_open": False,
        "policy_id": None,
        "policy_revision": 0,
        "screening_version": None,
        "calibration_version": None,
    }
    with pytest.raises(PrivacyError):
        validate(PrivacyCapabilities, {**base, **changed})


def test_duplicate_raw_json_and_oversize_rejected_without_private_echo(monkeypatch: Any) -> None:
    for raw in [b'{"private_name":1,"private_name":1}', b'{"a":NaN}', b"{bad-private-name"]:
        with pytest.raises(PrivacyError) as error:
            decode_json(raw)
        assert "private_name" not in str(error.value)
    calls = []
    monkeypatch.setattr(json, "loads", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(PrivacyError):
        decode_json(b" " * (MAX_WIRE_BYTES + 1))
    assert not calls


def test_calibration_is_private_unknown_without_cases_and_never_approval(tmp_path: Path) -> None:
    raw = json.dumps(
        {
            "schema_version": "gsip-photo-staged-evaluation-v1",
            "material_declared": "synthetic",
            "cases": [],
        }
    ).encode()
    report = evaluate_staged(
        raw,
        PrivateDirectory(tmp_path),
        ScreenEngine(benchmark_configuration(), NoCandidates()),
        hashlib.sha256(b"config").hexdigest(),
        "unknown-v1",
    )
    assert report.publication_approved is False and report.evidence_status == "unknown"
    assert all(
        x.positive_success_interval_95 is None and x.negative_false_positive_interval_95 is None
        for x in report.category_summaries
    )
    assert report.runtime_samples == 0
    with pytest.raises(PrivacyError):
        validate(CalibrationManifest, {**report.model_dump(), "publication_approved": True})


def test_calibration_misses_and_intervals_do_not_count_duplicates(tmp_path: Path) -> None:
    source = PrivateDirectory(tmp_path)
    source.write("case.jpg", jpeg(np.full((480, 640, 3), 210, np.uint8)))
    case = {
        "file": "case.jpg",
        "category": "plate",
        "sensitive_present": True,
        "stratum": "oblique",
    }
    data = {
        "schema_version": "gsip-photo-staged-evaluation-v1",
        "material_declared": "synthetic",
        "cases": [case],
    }
    engine = ScreenEngine(benchmark_configuration(), NoCandidates())
    report = evaluate_staged(
        json.dumps(data).encode(),
        source,
        engine,
        hashlib.sha256(b"config").hexdigest(),
        "unknown-v1",
    )
    plate = next(x for x in report.category_summaries if x.category == "plate")
    assert plate.positive_frames == 1 and plate.misses == 1 and plate.positive_success_interval_95
    assert plate.positive_success_interval_95[0] == 0 and report.publication_approved is False
    data["cases"] = [case, case]
    with pytest.raises(PrivacyError):
        evaluate_staged(
            json.dumps(data).encode(),
            source,
            engine,
            hashlib.sha256(b"config").hexdigest(),
            "unknown-v1",
        )


def test_calibration_interval_numerics_and_unknown_denominator() -> None:
    assert wilson(0, 0) is None
    interval = wilson(2, 2)
    assert (
        interval and interval[0] == pytest.approx(0.3423802275) and interval[1] == pytest.approx(1)
    )
    with pytest.raises(PrivacyError):
        wilson(3, 2)


def test_cli_unknown_token_argument_and_input_errors_are_generic(
    monkeypatch: Any, capsys: Any, tmp_path: Path
) -> None:
    sentinel = "fictional-private-argument"
    monkeypatch.setattr(
        sys,
        "argv",
        ["privacy-review", sentinel, "--state", str(tmp_path), "--operator-token", sentinel],
    )
    with pytest.raises(SystemExit):
        review_main()
    output = capsys.readouterr()
    assert sentinel not in output.err and str(tmp_path) not in output.err


def test_invalid_private_mask_cannot_cover_entire_frame() -> None:
    with pytest.raises(PrivacyError):
        validate(
            CardExclusion,
            {
                "image_width": 10,
                "image_height": 10,
                "mask_sha256": hashlib.sha256(b"mask").hexdigest(),
                "excluded_pixels": 100,
                "margin_version": "v1",
            },
        )


def test_private_viewer_never_inherits_authority_credentials(
    monkeypatch: Any, tmp_path: Path
) -> None:
    private = PrivateDirectory(tmp_path)
    image = private.write("image.jpg", jpeg(np.full((480, 640, 3), 210, np.uint8)))
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fictional-service")
    monkeypatch.setenv("GSIP_PHOTO_REVIEW_TOKEN", hashlib.sha256(b"fictional-token").hexdigest())
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "abort")
    received: dict[str, Any] = {}

    def open_image(*args: Any, **kwargs: Any) -> None:
        received.update(kwargs)

    monkeypatch.setattr("pipeline.privacy_review.subprocess.run", open_image)
    assert human_decision(image) == "abort"
    assert "env" in received
    assert "SUPABASE_SERVICE_ROLE_KEY" not in received["env"]
    assert "GSIP_PHOTO_REVIEW_TOKEN" not in received["env"]


@pytest.mark.parametrize("scene", ["bare_marker", "occluded_card", "complete_card"])
def test_card_localization_without_complete_verification_screens_every_pixel(scene: str) -> None:
    value = np.full((800, 800, 3), 210, np.uint8)
    if scene == "bare_marker":
        marker = cv2.aruco.generateImageMarker(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), MARKER_ID, 100
        )
        value[220:320, 230:330] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
        cv2.putText(value, "123", (235, 400), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    else:
        value[70:520, 80:400] = cv2.resize(canonical_card(), (320, 450))
        if scene == "occluded_card":
            value[330:520, 80:400] = 210
            cv2.putText(value, "123", (100, 420), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    raw = jpeg(value)
    original = decode_sanitized(raw)
    mask, evidence = card_mask(original, benchmark_configuration())
    assert evidence is None and not mask.any()

    class Capture(NoCandidates):
        def __init__(self) -> None:
            self.face_views: list[np.ndarray] = []
            self.text_views: list[np.ndarray] = []

        def faces(self, image: np.ndarray) -> list[Any]:
            self.face_views.append(image.copy())
            return []

        def texts(self, image: np.ndarray) -> list[Any]:
            self.text_views.append(image.copy())
            return []

    backend = Capture()
    result = ScreenEngine(benchmark_configuration(), backend).screen(raw)
    assert result.card_exclusion is None
    expected = list(views(original, benchmark_configuration()))
    assert len(backend.face_views) == len(backend.text_views) == len(expected)
    assert all(
        np.array_equal(got, want) for got, want in zip(backend.face_views, expected, strict=True)
    )
    assert all(
        np.array_equal(got, want) for got, want in zip(backend.text_views, expected, strict=True)
    )
