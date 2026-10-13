"""Bounded service-only RPC and private Storage transport; never an agent API."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from urllib.parse import urlsplit

import httpx

from pipeline.privacy_contract import MAX_PHOTO_BYTES, MAX_WIRE_BYTES, PrivacyError, decode_json

RPC_NAMES = frozenset(
    {
        "photo_privacy_capabilities",
        "record_photo_privacy_content",
        "claim_photo_privacy_job",
        "complete_photo_privacy_job",
        "fail_photo_privacy_job",
        "photo_privacy_receipt",
        "photo_privacy_review_context",
        "review_photo_privacy",
        "authorize_photo_privacy_export",
    }
)
_UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
_PATH = re.compile(rf"({_UUID})/({_UUID})/([ABC])/({_UUID})\.jpg")


def private_path(value: str, submission_id: str | None = None, shot: str | None = None) -> str:
    match = _PATH.fullmatch(value)
    if (
        match is None
        or (submission_id is not None and match[2] != submission_id)
        or (shot is not None and match[3] != shot)
    ):
        raise PrivacyError("authorization")
    # SQL independently derives and binds the first (owner) UUID; it is not a client claim.
    return value


class PrivacyTransport:
    def __init__(self, url: str, service_key: str, client: httpx.Client | None = None) -> None:
        parsed = urlsplit(url)
        if (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or (
                parsed.scheme != "https"
                and not (
                    parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
                )
            )
            or not parsed.hostname
            or not service_key
        ):
            raise PrivacyError("authorization")
        self.url = url.rstrip("/")
        self.client = client or httpx.Client(timeout=30, follow_redirects=False, trust_env=False)
        self.headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}
        # HTTP debug/info request logs otherwise contain private object paths.
        for name in ("httpx", "httpcore"):
            logging.getLogger(name).setLevel(logging.WARNING)

    def _read(self, method: str, path: str, maximum: int, body: bytes | None = None) -> bytes:
        try:
            started = time.monotonic()
            with self.client.stream(
                method,
                self.url + path,
                headers={**self.headers, "Content-Type": "application/json"},
                content=body,
                follow_redirects=False,
            ) as response:
                data = bytearray()
                for chunk in response.iter_bytes():
                    if len(data) + len(chunk) > maximum or time.monotonic() - started > 30:
                        raise PrivacyError("transport")
                    data.extend(chunk)
                if not 200 <= response.status_code < 300:
                    code = "authorization" if response.status_code in {401, 403} else "transport"
                    try:
                        error = decode_json(bytes(data))
                        server_code = error.get("code") if isinstance(error, dict) else None
                        if isinstance(server_code, str):
                            code = {
                                "42501": "authorization",
                                "WD001": "withdrawn",
                                "PP002": "stale",
                                "PP003": "conflict",
                                "22023": "invalid",
                            }.get(server_code, code)
                    except PrivacyError:
                        pass
                    raise PrivacyError(code)
                return bytes(data)
        except PrivacyError:
            raise
        except Exception:
            raise PrivacyError("transport") from None

    def rpc(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        if name not in RPC_NAMES:
            raise PrivacyError("authorization")
        try:
            body = json.dumps(
                arguments or {}, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
            maximum = 8_000_000 if name == "authorize_photo_privacy_export" else MAX_WIRE_BYTES
            if len(body) > maximum + 1024:
                raise PrivacyError()
        except Exception:
            raise PrivacyError() from None
        return decode_json(self._read("POST", "/rest/v1/rpc/" + name, maximum, body), maximum)

    def download(self, path: str) -> bytes:
        return self._read(
            "GET",
            "/storage/v1/object/authenticated/submission-photos/" + private_path(path),
            MAX_PHOTO_BYTES,
        )
