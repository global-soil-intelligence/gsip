"""Prospective COLLECT-4 scope guards; these tests never access a camera."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


def design() -> dict[str, Any]:
    value: dict[str, Any] = json.loads((ROOT / "docs/browser-camera-design.json").read_text())
    return value


def validate(value: dict[str, Any]) -> None:
    assert set(value) == {
        "schema",
        "document_grants_implementation",
        "audience",
        "storage",
        "mixed_photos",
        "snapshot",
        "limits",
        "commit",
        "new_dependencies",
        "new_native_files",
        "new_backend_schema",
        "indexeddb_version_change",
        "activation_changes",
    }
    assert value["schema"] == "gsip-browser-camera-design-v1"
    assert value["document_grants_implementation"] is False
    assert value["audience"] == "invited_private_browser"
    assert value["storage"] == "ram_until_atomic_owner_queue"
    assert value["mixed_photos"] is False
    assert value["snapshot"] == {
        "pipeline": "video_frame_jpeg",
        "audio": False,
        "overlay_in_evidence": False,
        "calibration_claim": False,
        "automatic_sample": False,
    }
    for key in ("audio", "overlay_in_evidence", "calibration_claim", "automatic_sample"):
        assert value["snapshot"][key] is False
    for key, number in value["limits"].items():
        assert type(number) is (float if key == "jpeg_quality" else int)
    for key, flag in value["commit"].items():
        if key != "stores":
            assert type(flag) is bool
    assert value["limits"] == {
        "streams": 1,
        "pending_requests": 1,
        "pending_encoders": 1,
        "selected_shots": 3,
        "candidates": 1,
        "max_frame_edge": 2048,
        "max_frame_pixels": 4194304,
        "min_short_edge": 720,
        "min_long_edge": 1280,
        "max_photo_bytes": 12582912,
        "max_retained_encoded_bytes": 50331648,
        "jpeg_quality": 0.92,
        "permission_wait_ms": 20000,
        "playback_wait_ms": 10000,
        "preview_ms": 60000,
        "encode_wait_ms": 10000,
        "access_wait_ms": 5000,
        "access_refresh_ms": 5000,
        "access_lease_ms": 15000,
        "revision_poll_ms": 1000,
    }
    assert value["commit"] == {
        "stores": ["submissions", "queueState", "draftPhotos", "libraryDraft"],
        "requires_empty_photo_store": True,
        "requires_current_owner": True,
        "requires_revision_and_session": True,
        "exact_library_context": True,
        "advance_revision_on_new_commit": True,
        "reconcile_existing_identity_first": True,
        "original_writer_revision_required": True,
        "stale_writer_refusal_observable": True,
        "blanket_draft_cleanup": False,
        "overwrites_existing_record": False,
    }
    for key in ("new_dependencies", "new_native_files"):
        assert value[key] == []
    for key in ("new_backend_schema", "indexeddb_version_change", "activation_changes"):
        assert value[key] is False


def test_design_is_prospective_private_and_bounded() -> None:
    validate(design())


@pytest.mark.parametrize(
    ("section", "key", "replacement"),
    [
        (None, "document_grants_implementation", True),
        (None, "audience", "public_anonymous"),
        (None, "storage", "unowned_draft_store"),
        (None, "mixed_photos", True),
        (None, "new_dependencies", ["camera-sdk"]),
        (None, "new_native_files", ["Camera.swift"]),
        (None, "new_backend_schema", True),
        (None, "indexeddb_version_change", True),
        (None, "activation_changes", True),
        ("snapshot", "pipeline", "image_capture_still"),
        ("snapshot", "audio", True),
        ("snapshot", "overlay_in_evidence", True),
        ("snapshot", "calibration_claim", True),
        ("snapshot", "automatic_sample", True),
        ("limits", "streams", 2),
        ("limits", "streams", True),
        ("snapshot", "audio", 0),
        ("limits", "max_frame_edge", 4096),
        ("limits", "max_retained_encoded_bytes", 200000000),
        ("limits", "pending_requests", 2),
        ("limits", "pending_encoders", 2),
        ("limits", "max_frame_pixels", 40000000),
        ("limits", "max_photo_bytes", 25000000),
        ("limits", "access_lease_ms", 600000),
        ("commit", "requires_empty_photo_store", False),
        ("commit", "requires_current_owner", False),
        ("commit", "requires_revision_and_session", False),
        ("commit", "exact_library_context", False),
        ("commit", "advance_revision_on_new_commit", False),
        ("commit", "reconcile_existing_identity_first", False),
        ("commit", "original_writer_revision_required", False),
        ("commit", "stale_writer_refusal_observable", False),
        ("commit", "blanket_draft_cleanup", True),
        ("commit", "overwrites_existing_record", True),
    ],
)
def test_design_cannot_silently_expand_scope(
    section: str | None, key: str, replacement: Any
) -> None:
    value = copy.deepcopy(design())
    target = value if section is None else value[section]
    target[key] = replacement
    with pytest.raises(AssertionError):
        validate(value)


def test_unknown_design_field_is_not_implicit_authority() -> None:
    value = design() | {"production_go": True}
    with pytest.raises(AssertionError):
        validate(value)
