"""Bounded private screening worker; it never changes QA or publication gates."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self
from uuid import uuid4

from pydantic import model_validator

from pipeline.library import PrivateArgumentParser
from pipeline.photo_privacy import (
    SANITIZER_VERSION,
    BoundedScreenEngine,
    ScreeningEngine,
    decode_sanitized,
    load_configuration,
    sha256,
)
from pipeline.photo_privacy_calibrate import CalibrationManifest
from pipeline.privacy_contract import (
    VERSION,
    CompleteResponse,
    ContentRequest,
    ContentResponse,
    FailResponse,
    Lease,
    PrivacyCapabilities,
    PrivacyError,
    ScreenReceipt,
    StrictModel,
    decode_json,
    encode,
    validate,
)
from pipeline.privacy_io import PrivateDirectory, read_file
from pipeline.privacy_transport import PrivacyTransport, private_path


class PendingScreen(StrictModel):
    lease: Lease
    receipt: ScreenReceipt

    @model_validator(mode="after")
    def same_binding(self) -> Self:
        for name in (
            "photo_id",
            "content_revision",
            "policy_id",
            "policy_revision",
            "sanitized_sha256",
            "screening_version",
            "calibration_version",
            "detector_manifest_sha256",
            "calibration_manifest_sha256",
        ):
            if getattr(self.lease, name) != getattr(self.receipt, name):
                raise PrivacyError()
        return self


@dataclass
class WorkerSummary:
    registered: int = 0
    completed: int = 0
    held: int = 0
    errors: int = 0
    dispositions: dict[str, int] = field(default_factory=dict)


def rpc_retry(transport: PrivacyTransport, name: str, arguments: dict[str, Any]) -> Any:
    # Exact arguments/UUIDs on uncertain responses; SQL alone owns generation/backoff budgets.
    for attempt in range(3):
        try:
            return transport.rpc(name, arguments)
        except PrivacyError as error:
            if error.code != "transport" or attempt == 2:
                raise
    raise PrivacyError("transport")


class PrivacyWorker:
    def __init__(
        self,
        transport: PrivacyTransport,
        state: PrivateDirectory,
        engine_factory: Callable[[Lease], ScreeningEngine],
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.transport = transport
        self.state = state
        self.engine_factory = engine_factory
        self.now = now

    def _remaining(self, lease: Lease) -> float:
        expires = datetime.fromisoformat(lease.lease_expires_at.replace("Z", "+00:00"))
        seconds = (expires - self.now()).total_seconds()
        if not 0 < seconds <= 300:
            raise PrivacyError("stale")
        return seconds

    def _complete(self, pending: PendingScreen, path: Path, summary: WorkerSummary) -> bool:
        try:
            receipt = validate(ScreenReceipt, pending.receipt)
            response = validate(
                CompleteResponse,
                rpc_retry(
                    self.transport,
                    "complete_photo_privacy_job",
                    {
                        "p_lease_id": pending.lease.lease_id,
                        "p_receipt": decode_json(encode(receipt)),
                    },
                ),
            )
            expected = (
                "error"
                if any(
                    x.result in {"unsupported", "error"} for x in (receipt.face, receipt.scene_text)
                )
                else (
                    "review"
                    if any(x.result == "flag" for x in (receipt.face, receipt.scene_text))
                    else "clear"
                )
            )
            if (
                response.photo_id != receipt.photo_id
                or response.content_revision != receipt.content_revision
                or response.status != expected
            ):
                raise PrivacyError()
            path.unlink()
            summary.completed += 1
            summary.dispositions[response.status] = summary.dispositions.get(response.status, 0) + 1
            return True
        except PrivacyError as error:
            if error.code in {"withdrawn", "stale"}:
                path.unlink(missing_ok=True)
            summary.held += 1
            return False

    def _fail(self, lease: Lease, code: str) -> None:
        reason = (
            code
            if code in {"storage", "decode", "sanitize", "unsupported", "detector", "timeout"}
            else "detector"
        )
        response = validate(
            FailResponse,
            rpc_retry(
                self.transport,
                "fail_photo_privacy_job",
                {
                    "p_lease_id": lease.lease_id,
                    "p_error_code": reason,
                },
            ),
        )
        if response.photo_id != lease.photo_id:
            raise PrivacyError()

    def run(self, limit: int = 25) -> WorkerSummary:
        if isinstance(limit, bool) or not 1 <= limit <= 100:
            raise PrivacyError()
        summary = WorkerSummary()
        with self.state.lock():
            # A lost completion is replayed from durable private state before claiming new work.
            for path in sorted(self.state.path.glob("screen-*.json"))[:limit]:
                pending = validate(
                    PendingScreen, decode_json(self.state.read(path, 32_768), 32_768)
                )
                if not self._complete(pending, path, summary) and path.exists():
                    return summary
            try:
                capabilities = validate(
                    PrivacyCapabilities, self.transport.rpc("photo_privacy_capabilities")
                )
            except PrivacyError:
                summary.held += 1
                return summary
            if capabilities.policy_id is None:
                summary.held += 1
                return summary
            # publication_open=false is expected: benchmark screening may still run privately.
            for _ in range(limit):
                try:
                    claimed = self.transport.rpc("claim_photo_privacy_job")
                    if claimed is None:
                        break
                    lease = validate(Lease, claimed)
                    self._remaining(lease)
                    private_path(lease.storage_path, lease.submission_id, lease.shot_type)
                except PrivacyError:
                    summary.held += 1
                    break
                try:
                    raw = self.transport.download(lease.storage_path)
                    decode_sanitized(raw)
                    digest = sha256(raw)
                    if (
                        lease.sanitized_sha256 != digest
                        or lease.byte_count != len(raw)
                        or lease.sanitizer_version != SANITIZER_VERSION
                    ):
                        request = validate(
                            ContentRequest,
                            {
                                "schema_version": VERSION,
                                "photo_id": lease.photo_id,
                                "expected_content_revision": lease.content_revision,
                                "sanitized_sha256": digest,
                                "byte_count": len(raw),
                                "sanitizer_version": SANITIZER_VERSION,
                            },
                        )
                        response = validate(
                            ContentResponse,
                            rpc_retry(
                                self.transport,
                                "record_photo_privacy_content",
                                {"p_request": decode_json(encode(request))},
                            ),
                        )
                        if (
                            response.photo_id != lease.photo_id
                            or response.content_revision < lease.content_revision
                            or (
                                response.status == "registered"
                                and response.content_revision <= lease.content_revision
                            )
                        ):
                            raise PrivacyError()
                        summary.registered += 1
                        continue  # Registration invalidated this lease; claim a fresh current one.
                    engine = self.engine_factory(lease)
                    if engine.config.screening_version != lease.screening_version:
                        raise PrivacyError("detector")
                    result = engine.screen(raw, self._remaining(lease))
                    self._remaining(lease)
                    receipt = validate(
                        ScreenReceipt,
                        {
                            "schema_version": VERSION,
                            "request_id": str(uuid4()),
                            "photo_id": lease.photo_id,
                            "content_revision": lease.content_revision,
                            "policy_id": lease.policy_id,
                            "policy_revision": lease.policy_revision,
                            "sanitized_sha256": digest,
                            "screening_version": lease.screening_version,
                            "calibration_version": lease.calibration_version,
                            "detector_manifest_sha256": lease.detector_manifest_sha256,
                            "calibration_manifest_sha256": lease.calibration_manifest_sha256,
                            "face": result.face.model_dump(),
                            "scene_text": result.scene_text.model_dump(),
                            "card_exception_used": result.card_exclusion is not None,
                            "card_exclusion": result.card_exclusion.model_dump()
                            if result.card_exclusion
                            else None,
                        },
                    )
                    pending = validate(
                        PendingScreen,
                        {"lease": lease.model_dump(), "receipt": receipt.model_dump()},
                    )
                    path = self.state.write(
                        "screen-" + receipt.request_id + ".json", encode(pending, 32_768)
                    )
                    if not self._complete(pending, path, summary) and path.exists():
                        break
                except PrivacyError as error:
                    summary.errors += 1
                    try:
                        self._fail(lease, error.code)
                    except PrivacyError:
                        summary.held += 1
        return summary


def configured_engine(
    configuration: Path, calibration: Path, models: Path
) -> Callable[[Lease], ScreeningEngine]:
    def make(lease: Lease) -> ScreeningEngine:
        config = load_configuration(configuration, lease.detector_manifest_sha256)
        raw = read_file(calibration, 2_000_000)
        if sha256(raw) != lease.calibration_manifest_sha256:
            raise PrivacyError("detector")
        data = validate(CalibrationManifest, decode_json(raw, 2_000_000))
        if (
            data.calibration_version != lease.calibration_version
            or data.detector_manifest_sha256 != lease.detector_manifest_sha256
        ):
            raise PrivacyError("detector")
        return BoundedScreenEngine(config, models)

    return make


def main() -> None:
    parser = PrivateArgumentParser(description="Bounded private photo screening; no publication")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    try:
        worker = PrivacyWorker(
            PrivacyTransport(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]),
            PrivateDirectory(args.state),
            configured_engine(args.configuration, args.calibration, args.models),
        )
        summary = worker.run(args.limit)
        print(
            json.dumps(
                {
                    "registered": summary.registered,
                    "completed": summary.completed,
                    "held": summary.held,
                    "errors": summary.errors,
                    "dispositions": summary.dispositions,
                }
            )
        )
    except Exception:
        print("Photo privacy operation unavailable", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
