from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import cv2
import numpy as np
import pytest
from PIL import Image
from test_library import record

from card.fixtures import canonical_card
from pipeline.library import CameraRgb, LibraryRecord
from pipeline.phone_optics import extract_phone_record, summarize_rgb


def image_bytes(rgb: tuple[int, int, int] = (100, 80, 60)) -> bytes:
    image = Image.new("RGB", (100, 100), rgb)
    output = io.BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


def test_rgb_is_deterministic_uncalibrated_and_has_no_wavelengths() -> None:
    first = summarize_rgb(image_bytes(), UUID(int=5))
    second = summarize_rgb(image_bytes(), first.device_id)
    assert first == second
    assert first.calibration_status == "uncalibrated"
    assert not first.card_present
    assert first.pixel_count == 10_000
    assert first.mean_rgb == pytest.approx([100 / 255, 80 / 255, 60 / 255], abs=0.01)
    assert "wavelength_nm" not in first.model_dump()


def test_detected_card_is_excluded_from_rgb_summary() -> None:
    card = canonical_card()
    h, w = card.shape[:2]
    frame = np.full((h, w * 2, 3), [40, 80, 120], dtype=np.uint8)
    frame[:, :w] = card
    ok, encoded = cv2.imencode(".jpg", frame)
    assert ok
    summary = summarize_rgb(encoded.tobytes(), UUID(int=5))
    assert summary.card_present
    assert summary.mean_rgb == pytest.approx([120 / 255, 80 / 255, 40 / 255], abs=0.025)
    assert summary.pixel_count < h * w * 2
    assert summary.calibration_status == "uncalibrated"


def test_no_soil_pixels_fails_instead_of_summarizing_card() -> None:
    with patch("pipeline.phone_optics.card_transform", return_value=np.eye(3)):
        with pytest.raises(ValueError):
            summarize_rgb(image_bytes(), UUID(int=5))


def test_extraction_does_not_promote_qa_consent_or_pairing() -> None:
    template = LibraryRecord.model_validate(record())
    result = extract_phone_record(image_bytes(), template)
    assert isinstance(result.measurement, CameraRgb)
    assert result.qa_status == "pending"
    assert not result.pairing_verified
    assert not result.consent_verified
    assert result.measurement.source_sha256 != "a" * 64
    assert result.sample_key == template.sample_key


def test_field_photo_extraction_is_held_until_screening_integration() -> None:
    template = LibraryRecord.model_validate(record() | {"synthetic": False})
    with pytest.raises(ValueError):
        extract_phone_record(image_bytes(), template)


def test_invalid_image_does_not_echo_private_bytes(tmp_path: Path) -> None:
    from pipeline.phone_optics import main

    incoming = tmp_path / "private-photo"
    incoming.write_bytes(b"PRIVATE-BYTES")
    template = tmp_path / "template.json"
    template.write_text(LibraryRecord.model_validate(record()).model_dump_json())
    assert (
        main(
            [
                "--store",
                str(tmp_path / "store"),
                "--template",
                str(template),
                "--image",
                str(incoming),
            ]
        )
        == 1
    )
