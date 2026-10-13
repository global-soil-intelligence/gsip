from __future__ import annotations

import hashlib
import importlib
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest


def api() -> Any:
    return importlib.import_module("pipeline.photo_privacy")


def image() -> np.ndarray:
    return np.full((480, 640, 3), 210, np.uint8)


def jpeg(value: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".jpg", value)
    assert ok
    return encoded.tobytes()


class RecordingBackend:
    def __init__(self) -> None:
        self.face_inputs: list[np.ndarray] = []
        self.text_inputs: list[np.ndarray] = []
        self.candidate = False
        self.invalid_face = False

    def faces(self, value: np.ndarray) -> list[Any]:
        self.face_inputs.append(value.copy())
        if self.invalid_face:
            return [
                api().Detection(((0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)), float("nan"))
            ]
        return []

    def texts(self, value: np.ndarray) -> list[Any]:
        self.text_inputs.append(value.copy())
        if self.candidate:
            return [api().Detection(((2.0, 2.0), (20.0, 2.0), (20.0, 20.0), (2.0, 20.0)), 0.8)]
        return []


def test_whole_face_frame_and_private_card_mask() -> None:
    module = api()
    backend = RecordingBackend()
    engine = module.ScreenEngine(module.benchmark_configuration(), backend)
    source = image()
    source[70:180, 70:180] = (1, 2, 3)
    result = engine.screen(jpeg(source))
    assert result.face.result == "pass" and result.scene_text.result == "pass"
    assert result.card_exclusion is None
    assert backend.face_inputs and backend.text_inputs
    # Full-resolution overlapping views include every pixel, not only candidate soil.
    assert backend.face_inputs[0].shape == source.shape


def test_sensitive_text_candidate_is_not_ocr_clearance() -> None:
    module = api()
    backend = RecordingBackend()
    backend.candidate = True
    result = module.ScreenEngine(module.benchmark_configuration(), backend).screen(jpeg(image()))
    assert result.scene_text.result == "flag" and result.scene_text.candidates > 0


def test_nonfinite_candidate_error_never_clears() -> None:
    module = api()
    backend = RecordingBackend()
    backend.invalid_face = True
    result = module.ScreenEngine(module.benchmark_configuration(), backend).screen(jpeg(image()))
    assert result.face.result == "error"


def test_metadata_and_trailing_bytes_are_refused() -> None:
    module = api()
    with pytest.raises(module.PrivacyError):
        module.decode_sanitized(jpeg(image()) + b"private-tail")


def test_pinned_model_size_and_hash_before_load(tmp_path: Any) -> None:
    module = api()
    p = tmp_path / module.FACE_MODEL_NAME
    p.write_bytes(b"not-the-pinned-model")
    with pytest.raises(module.PrivacyError):
        module.verified_model(tmp_path, module.FACE_MODEL_NAME)


def test_configuration_digest_and_runtime_source_binding(tmp_path: Any) -> None:
    module = api()
    raw = module.configuration_bytes(module.benchmark_configuration())
    p = tmp_path / "config.json"
    p.write_bytes(raw)
    parsed = module.load_configuration(p, hashlib.sha256(raw).hexdigest())
    assert parsed.margin_scale == 1.12
    with pytest.raises(module.PrivacyError):
        module.load_configuration(p, hashlib.sha256(b"other").hexdigest())


def test_hard_timeout_kills_and_joins_an_unresponsive_child(monkeypatch: Any) -> None:
    module = api()

    class Pipe:
        def close(self) -> None:
            pass

        def poll(self, timeout: float) -> bool:
            return False

    class Process:
        pid = 1

        def __init__(self) -> None:
            self.killed = False
            self.terminated = False
            self.closed = False
            self.joins = 0

        def start(self) -> None:
            pass

        def is_alive(self) -> bool:
            return not self.killed

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

        def join(self, timeout: float) -> None:
            self.joins += 1

        def close(self) -> None:
            self.closed = True

    process = Process()

    class Context:
        def Pipe(self, duplex: bool) -> tuple[Pipe, Pipe]:
            return Pipe(), Pipe()

        def Process(self, **kwargs: Any) -> Process:
            return process

    monkeypatch.setattr(module.multiprocessing, "get_context", lambda _: Context())
    monkeypatch.setattr(module, "verified_model", lambda *args: b"synthetic")
    engine = module.BoundedScreenEngine(module.benchmark_configuration(), Path("/private/model"))
    with pytest.raises(module.PrivacyError, match="timeout"):
        engine.screen(jpeg(image()), 1)
    assert process.terminated and process.killed and process.closed and process.joins == 2
