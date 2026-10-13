"""Personally authenticated private human review. No reversal of permanent withholding."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pipeline.library import PrivateArgumentParser
from pipeline.photo_privacy import decode_sanitized, sha256
from pipeline.privacy_contract import (
    MAX_PHOTO_BYTES,
    VERSION,
    Id,
    PrivacyError,
    ReviewContext,
    ReviewRequest,
    ReviewResponse,
    StrictModel,
    decode_json,
    encode,
    validate,
)
from pipeline.privacy_io import PrivateDirectory
from pipeline.privacy_transport import PrivacyTransport, private_path
from pipeline.privacy_worker import rpc_retry

Decision = Literal["clear", "withhold", "abort"]


class ReviewTarget(StrictModel):
    photo_id: Id


def operator_token(value: str | None) -> str:
    if value is None or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise PrivacyError("authorization")
    return value


def _submit(
    transport: PrivacyTransport, token: str, request: ReviewRequest, path: Path
) -> ReviewResponse:
    response = validate(
        ReviewResponse,
        rpc_retry(
            transport,
            "review_photo_privacy",
            {
                "p_operator_token": token,
                "p_request": decode_json(encode(request)),
            },
        ),
    )
    expected = "clear" if request.decision == "clear" else "withheld"
    if (
        response.photo_id != request.photo_id
        or response.content_revision != request.content_revision
        or response.review_id != request.review_id
        or response.status != expected
    ):
        raise PrivacyError()
    path.unlink()
    return response


def review_photo(
    transport: PrivacyTransport,
    state: PrivateDirectory,
    photo_id: str,
    token: str,
    decide: Callable[[Path], Decision],
) -> ReviewResponse | None:
    token = operator_token(token)
    photo_id = validate(ReviewTarget, {"photo_id": photo_id}).photo_id
    with state.lock():
        for path in sorted(state.path.glob("review-*.json")):
            request = validate(ReviewRequest, decode_json(state.read(path, 16_384)))
            if request.photo_id == photo_id:
                try:
                    return _submit(transport, token, request, path)
                except PrivacyError as error:
                    if error.code in {"withdrawn", "stale"}:
                        path.unlink(missing_ok=True)
                    raise
        value = transport.rpc(
            "photo_privacy_review_context", {"p_photo_id": photo_id, "p_operator_token": token}
        )
        if value is None:
            return None
        context = validate(ReviewContext, value)
        if (
            context.photo_id != photo_id
            or context.sanitized_sha256 is None
            or context.policy_id is None
            or context.screening_version is None
            or context.calibration_version is None
        ):
            raise PrivacyError("stale")
        raw = transport.download(private_path(context.storage_path))
        decode_sanitized(raw)
        if sha256(raw) != context.sanitized_sha256:
            raise PrivacyError("stale")
        # No public image path or unprotected viewer copy; always removed on decision/abort/error.
        with tempfile.TemporaryDirectory(prefix=".review-", dir=state.path) as temporary:
            private = PrivateDirectory(Path(temporary))
            image = private.write("image.jpg", raw)
            try:
                decision = decide(image)
            except Exception:
                raise PrivacyError("authorization") from None
            if decision == "abort":
                return None
            if (
                decision not in {"clear", "withhold"}
                or (decision == "clear" and context.status not in {"review", "clear"})
                or context.status == "withheld"
            ):
                raise PrivacyError("stale")
            # Viewers may edit/autosave or replace their copy. Bind the decision
            # to the same bounded, metadata-free bytes, before durable intent/RPC.
            try:
                reviewed = private.read(image, MAX_PHOTO_BYTES)
                decode_sanitized(reviewed)
                if sha256(reviewed) != context.sanitized_sha256:
                    raise PrivacyError("stale")
            except Exception:
                raise PrivacyError("stale") from None
            request = validate(
                ReviewRequest,
                {
                    "schema_version": VERSION,
                    "review_id": str(uuid4()),
                    "photo_id": photo_id,
                    "content_revision": context.content_revision,
                    "sanitized_sha256": context.sanitized_sha256,
                    "policy_id": context.policy_id,
                    "policy_revision": context.policy_revision,
                    "screening_version": context.screening_version,
                    "calibration_version": context.calibration_version,
                    "decision": decision,
                    "reason": "false_positive" if decision == "clear" else "privacy_risk",
                },
            )
            path = state.write("review-" + request.review_id + ".json", encode(request))
            try:
                return _submit(transport, token, request, path)
            except PrivacyError as error:
                if error.code in {"withdrawn", "stale"}:
                    path.unlink(missing_ok=True)
                raise


def human_decision(image: Path) -> Decision:
    if not sys.stdin.isatty():
        raise PrivacyError("authorization")
    PrivateDirectory(image.parent)
    if image.name != "image.jpg" or not image.is_absolute() or image.is_symlink():
        raise PrivacyError("authorization")
    command = "/usr/bin/open" if sys.platform == "darwin" else "/usr/bin/xdg-open"
    viewer_environment = {
        name: value
        for name, value in os.environ.items()
        if name not in {"SUPABASE_SERVICE_ROLE_KEY", "GSIP_PHOTO_REVIEW_TOKEN"}
    }
    try:
        subprocess.run(  # noqa: S603 -- fixed viewer, absolute protected JPEG, no shell or user flags.
            [command, str(image)],
            check=True,
            timeout=15,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=viewer_environment,
        )
        response = input(
            "Review the private image. Type clear-false-positive, permanently-withhold, or abort: "
        )
    except Exception:
        raise PrivacyError("authorization") from None
    return {
        "clear-false-positive": "clear",
        "permanently-withhold": "withhold",
        "abort": "abort",
    }.get(response, "abort")  # type: ignore[return-value]


def main() -> None:
    parser = PrivateArgumentParser(
        description="Private human photo review; withholding is permanent"
    )
    parser.add_argument("photo", type=str)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    try:
        token = operator_token(os.environ.get("GSIP_PHOTO_REVIEW_TOKEN"))
        response = review_photo(
            PrivacyTransport(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]),
            PrivateDirectory(args.state),
            args.photo,
            token,
            human_decision,
        )
        print(json.dumps({"reviews_completed": int(response is not None)}))
    except Exception:
        print("Photo privacy review unavailable", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
