from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np
import pytest

from pipeline.photo_privacy import SANITIZER_VERSION, ScreenEngine, benchmark_configuration
from pipeline.privacy_contract import PrivacyError
from pipeline.privacy_io import PrivateDirectory
from pipeline.privacy_review import operator_token, review_photo
from pipeline.privacy_transport import PrivacyTransport
from pipeline.privacy_worker import PrivacyWorker


def identity(number: int) -> str:
    return f"00000000-0000-0000-0000-{number:012d}"


def raw_photo() -> bytes:
    _, data = cv2.imencode(".jpg", np.full((480, 640, 3), 210, np.uint8))
    return data.tobytes()


def lease(known: bool = True, shot: str = "B") -> dict[str, Any]:
    raw = raw_photo()
    return {
        "lease_id": identity(1),
        "photo_id": identity(2),
        "submission_id": identity(3),
        "shot_type": shot,
        "storage_path": f"{identity(4)}/{identity(3)}/{shot}/{identity(5)}.jpg",
        "content_revision": 1 if known else 0,
        "sanitized_sha256": hashlib.sha256(raw).hexdigest() if known else None,
        "byte_count": len(raw) if known else None,
        "sanitizer_version": SANITIZER_VERSION if known else None,
        "policy_id": identity(6),
        "policy_revision": 1,
        "screening_version": "benchmark-v1",
        "calibration_version": "unknown-v1",
        "detector_manifest_sha256": hashlib.sha256(b"fictional configuration").hexdigest(),
        "calibration_manifest_sha256": hashlib.sha256(b"fictional calibration").hexdigest(),
        "lease_expires_at": (datetime.now(UTC) + timedelta(seconds=295)).isoformat(),
        "attempt": 1,
    }


class NoCandidates:
    def faces(self, image: np.ndarray) -> list[Any]:
        return []

    def texts(self, image: np.ndarray) -> list[Any]:
        return []


class ScriptedTransport(PrivacyTransport):
    def __init__(self, claims: list[dict[str, Any]]) -> None:
        self.claims = claims
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.downloads = 0
        self.complete_failures = 0
        self.register_failures = 0
        self.complete_code = "transport"
        self.review_failures = 0
        self.context_status = "review"
        self.context_digest = hashlib.sha256(raw_photo()).hexdigest()
        self.no_policy = False
        self.wrong_response = False

    def rpc(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        args = arguments or {}
        self.calls.append((name, copy.deepcopy(args)))
        if name == "photo_privacy_capabilities":
            return {
                "version": "gsip-photo-privacy-v1",
                "publication_open": False,
                "policy_id": None if self.no_policy else identity(6),
                "policy_revision": 1,
                "screening_version": None if self.no_policy else "benchmark-v1",
                "calibration_version": None if self.no_policy else "unknown-v1",
            }
        if name == "claim_photo_privacy_job":
            return self.claims.pop(0) if self.claims else None
        if name == "record_photo_privacy_content":
            if self.register_failures:
                self.register_failures -= 1
                raise PrivacyError("transport")
            return {
                "photo_id": args["p_request"]["photo_id"],
                "content_revision": 1,
                "status": "already_current",
            }
        if name == "complete_photo_privacy_job":
            if self.complete_failures:
                self.complete_failures -= 1
                raise PrivacyError(self.complete_code)
            request = args["p_receipt"]
            return {
                "photo_id": identity(999) if self.wrong_response else request["photo_id"],
                "content_revision": request["content_revision"],
                "status": "clear",
            }
        if name == "fail_photo_privacy_job":
            return {"photo_id": identity(2), "status": "pending"}
        if name == "photo_privacy_review_context":
            return {
                "photo_id": identity(2),
                "storage_path": lease()["storage_path"],
                "content_revision": 1,
                "sanitized_sha256": self.context_digest,
                "policy_id": identity(6),
                "policy_revision": 1,
                "screening_version": "benchmark-v1",
                "calibration_version": "unknown-v1",
                "status": self.context_status,
            }
        if name == "review_photo_privacy":
            if self.review_failures:
                self.review_failures -= 1
                raise PrivacyError("transport")
            request = args["p_request"]
            return {
                "photo_id": request["photo_id"],
                "content_revision": request["content_revision"],
                "review_id": request["review_id"],
                "status": "clear" if request["decision"] == "clear" else "withheld",
            }
        raise AssertionError("unexpected generic RPC")

    def download(self, path: str) -> bytes:
        self.downloads += 1
        return raw_photo()


def worker(transport: ScriptedTransport, state: Path) -> PrivacyWorker:
    return PrivacyWorker(
        transport,
        PrivateDirectory(state),
        lambda _: ScreenEngine(benchmark_configuration(), NoCandidates()),
    )


@pytest.mark.parametrize("shot", ["A", "B", "C"])
def test_every_shot_is_private_screened_without_qa_calls(tmp_path: Path, shot: str) -> None:
    transport = ScriptedTransport([lease(shot=shot)])
    assert worker(transport, tmp_path).run().completed == 1
    assert transport.downloads == 1
    assert not any("qa" in name or "settle" in name for name, _ in transport.calls)


def test_unknown_legacy_digest_registers_then_requires_fresh_lease(tmp_path: Path) -> None:
    transport = ScriptedTransport([lease(False), lease()])
    transport.register_failures = 1
    result = worker(transport, tmp_path).run()
    assert result.registered == 1 and result.completed == 1
    registrations = [
        args for name, args in transport.calls if name == "record_photo_privacy_content"
    ]
    assert registrations[0] == registrations[1]
    names = [name for name, _ in transport.calls]
    assert names.index("record_photo_privacy_content") < names.index("complete_photo_privacy_job")
    assert names.count("claim_photo_privacy_job") >= 2


def test_lost_receipt_restart_keeps_request_id_and_exact_bytes(tmp_path: Path) -> None:
    transport = ScriptedTransport([lease()])
    transport.complete_failures = 3
    assert worker(transport, tmp_path).run().held == 1
    files = list(tmp_path.glob("screen-*.json"))
    assert len(files) == 1 and os.stat(files[0]).st_mode & 0o777 == 0o600
    earlier = [args for name, args in transport.calls if name == "complete_photo_privacy_job"]
    assert worker(transport, tmp_path).run().completed == 1
    later = [args for name, args in transport.calls if name == "complete_photo_privacy_job"]
    assert all(value == earlier[0] for value in later)
    assert not list(tmp_path.glob("screen-*.json"))


@pytest.mark.parametrize("code", ["withdrawn", "stale"])
def test_refused_current_completion_never_resurrects(tmp_path: Path, code: str) -> None:
    transport = ScriptedTransport([lease()])
    transport.complete_failures = 1
    transport.complete_code = code
    result = worker(transport, tmp_path).run()
    assert result.completed == 0 and result.held == 1 and not list(tmp_path.glob("screen-*.json"))


def test_immutable_conflict_retains_same_receipt(tmp_path: Path) -> None:
    transport = ScriptedTransport([lease()])
    transport.complete_failures = 2
    transport.complete_code = "conflict"
    worker(transport, tmp_path).run()
    before = list(tmp_path.glob("screen-*.json"))[0].read_bytes()
    worker(transport, tmp_path).run()
    assert list(tmp_path.glob("screen-*.json"))[0].read_bytes() == before


def test_no_policy_and_oversized_lease_hold_before_download(tmp_path: Path) -> None:
    transport = ScriptedTransport([lease()])
    transport.no_policy = True
    assert worker(transport, tmp_path).run().held == 1 and transport.downloads == 0
    transport.no_policy = False
    transport.claims[0]["attempt"] = 6
    assert worker(transport, tmp_path).run().held == 1 and transport.downloads == 0


def test_bad_matching_response_is_not_success(tmp_path: Path) -> None:
    transport = ScriptedTransport([lease()])
    transport.wrong_response = True
    assert worker(transport, tmp_path).run().completed == 0
    assert list(tmp_path.glob("screen-*.json"))


def token() -> str:
    return hashlib.sha256(b"fictional operator, never provisioned").hexdigest()


def test_review_private_copy_cleanup_and_server_derived_operator(tmp_path: Path) -> None:
    transport = ScriptedTransport([])
    copies = []

    def choose(path: Path) -> str:
        copies.append(path)
        assert path.read_bytes() == raw_photo()
        assert os.stat(path).st_mode & 0o777 == 0o600
        return "clear"

    result = review_photo(transport, PrivateDirectory(tmp_path), identity(2), token(), choose)  # type: ignore[arg-type]
    assert result and result.status == "clear" and all(not p.exists() for p in copies)
    request = [args for name, args in transport.calls if name == "review_photo_privacy"][0]
    assert "reviewer_id" not in request["p_request"] and "p_operator_token" in request
    assert token() not in json.dumps([p.read_text() for p in tmp_path.glob("*.json")])


@pytest.mark.parametrize("status", ["pending", "processing", "error", "withheld"])
def test_no_clear_of_unsupported_or_permanent_withhold(tmp_path: Path, status: str) -> None:
    transport = ScriptedTransport([])
    transport.context_status = status
    with pytest.raises(PrivacyError):
        review_photo(transport, PrivateDirectory(tmp_path), identity(2), token(), lambda _: "clear")
    assert not any(name == "review_photo_privacy" for name, _ in transport.calls)
    assert not list(tmp_path.glob(".review-*"))


def test_lost_review_retry_keeps_id_without_token_on_disk(tmp_path: Path) -> None:
    transport = ScriptedTransport([])
    transport.review_failures = 3
    with pytest.raises(PrivacyError):
        review_photo(
            transport, PrivateDirectory(tmp_path), identity(2), token(), lambda _: "withhold"
        )
    stored = list(tmp_path.glob("review-*.json"))[0].read_bytes()
    assert token().encode() not in stored
    result = review_photo(
        transport, PrivateDirectory(tmp_path), identity(2), token(), lambda _: "abort"
    )
    assert result and result.status == "withheld"
    requests = [
        args["p_request"] for name, args in transport.calls if name == "review_photo_privacy"
    ]
    assert all(request == requests[0] for request in requests)
    assert transport.downloads == 1 and not list(tmp_path.glob(".review-*"))


@pytest.mark.parametrize("value", [None, "short", token().upper(), token() + "\n"])
def test_invalid_operator_token_has_generic_error(value: str | None) -> None:
    with pytest.raises(PrivacyError, match="authorization") as error:
        operator_token(value)
    if value:
        assert value not in str(error.value)


def test_private_transport_does_not_redirect_or_log_error_payload() -> None:
    sentinel = "fictional-private-contents"

    def handle(request: httpx.Request) -> httpx.Response:
        assert sentinel not in str(request.url)
        return httpx.Response(403, json={"code": "42501", "message": sentinel})

    transport = PrivacyTransport(
        "https://example.test", "test-only", httpx.Client(transport=httpx.MockTransport(handle))
    )
    with pytest.raises(PrivacyError) as error:
        transport.rpc("photo_privacy_review_context", {"p_operator_token": token()})
    assert sentinel not in str(error.value)


def test_view_callback_failure_erases_copy_and_hides_details(tmp_path: Path) -> None:
    def broken(path: Path) -> Any:
        raise RuntimeError("fictional-private-callback")

    with pytest.raises(PrivacyError) as error:
        review_photo(
            ScriptedTransport([]), PrivateDirectory(tmp_path), identity(2), token(), broken
        )
    assert "fictional-private-callback" not in str(error.value) and not list(
        tmp_path.glob(".review-*")
    )


@pytest.mark.parametrize("decision", ["clear", "withhold"])
@pytest.mark.parametrize("change", ["bytes", "symlink", "missing"])
def test_review_viewing_copy_must_match_decision_bytes(
    tmp_path: Path, decision: str, change: str
) -> None:
    transport = ScriptedTransport([])
    copies: list[Path] = []

    def choose(path: Path) -> str:
        copies.append(path)
        if change == "bytes":
            _, changed = cv2.imencode(".jpg", np.full((480, 640, 3), 150, np.uint8))
            path.write_bytes(changed.tobytes())
        elif change == "symlink":
            target = tmp_path / "synthetic-bystander.jpg"
            target.write_bytes(raw_photo())
            target.chmod(0o600)
            path.unlink()
            path.symlink_to(target)
        else:
            path.unlink()
        return decision

    with pytest.raises(PrivacyError):
        review_photo(transport, PrivateDirectory(tmp_path), identity(2), token(), choose)  # type: ignore[arg-type]
    assert not any(name == "review_photo_privacy" for name, _ in transport.calls)
    assert not list(tmp_path.glob("review-*.json"))
    assert copies and all(not p.exists() and not p.is_symlink() for p in copies)
    assert not list(tmp_path.glob(".review-*"))
