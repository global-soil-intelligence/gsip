"""Private, fail-closed exact-byte photo authorization. No public screening fields."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

VERSION = "gsip-photo-privacy-v1"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
LABEL = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _text(value: Any, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError("Unsupported private photo authorization")
    return value


def _integer(value: Any) -> int:
    if type(value) is not int or value < 0 or value > 2**63 - 1:
        raise ValueError("Unsupported private photo authorization")
    return int(value)


def _object(value: Any, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("Unsupported private photo authorization")
    return value


def _pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values:
        if key in result:
            raise ValueError("Unsupported private photo authorization")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValueError("Unsupported private photo authorization")


@dataclass(frozen=True)
class PhotoPolicy:
    policy_id: str
    policy_revision: int
    screening_version: str
    calibration_version: str

    @classmethod
    def parse(cls, value: dict[str, Any]) -> PhotoPolicy:
        return cls(
            _text(value["policy_id"], UUID),
            _integer(value["policy_revision"]),
            _text(value["screening_version"], LABEL),
            _text(value["calibration_version"], LABEL),
        )


@dataclass(frozen=True)
class PhotoExportBinding:
    photo_id: str
    content_revision: int
    sanitized_sha256: str
    policy: PhotoPolicy

    def payload(self) -> dict[str, Any]:
        return {
            "photo_id": self.photo_id,
            "content_revision": self.content_revision,
            "sanitized_sha256": self.sanitized_sha256,
            "policy_id": self.policy.policy_id,
            "policy_revision": self.policy.policy_revision,
            "screening_version": self.policy.screening_version,
            "calibration_version": self.policy.calibration_version,
        }


class PhotoPrivacyAuthority(Protocol):
    def policy(self) -> PhotoPolicy | None: ...

    def binding(self, photo_id: str) -> PhotoExportBinding | None: ...

    def authorize(self, bindings: list[PhotoExportBinding]) -> set[str]: ...


class RpcPhotoPrivacy:
    """Only the existing private export operator constructs this service RPC adapter."""

    def __init__(self, url: str, client: httpx.Client) -> None:
        self.url = url.rstrip("/")
        self.client = client

    def _rpc(self, name: str, payload: dict[str, Any]) -> Any:
        if name not in {
            "photo_privacy_capabilities",
            "photo_privacy_receipt",
            "authorize_photo_privacy_export",
        }:
            raise ValueError("Unsupported private photo authorization")
        content = bytearray()
        with self.client.stream("POST", f"{self.url}/rest/v1/rpc/{name}", json=payload) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                if len(content) + len(chunk) > 8_000_000:
                    raise ValueError("Unsupported private photo authorization")
                content.extend(chunk)
        try:
            return json.loads(
                content.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite
            )
        except RecursionError:
            raise ValueError("Unsupported private photo authorization") from None

    def policy(self) -> PhotoPolicy | None:
        try:
            value = _object(
                self._rpc("photo_privacy_capabilities", {}),
                {
                    "version",
                    "publication_open",
                    "policy_id",
                    "policy_revision",
                    "screening_version",
                    "calibration_version",
                },
            )
            if value["version"] != VERSION or type(value["publication_open"]) is not bool:
                return None
            _integer(value["policy_revision"])
            if not value["publication_open"]:
                return None
            return PhotoPolicy.parse(value)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            # Old schema, missing approval, outage or an unknown response never opens photos.
            return None

    def binding(self, photo_id: str) -> PhotoExportBinding | None:
        try:
            _text(photo_id, UUID)
            raw = self._rpc("photo_privacy_receipt", {"p_photo_id": photo_id})
            if raw is None:
                return None
            value = _object(
                raw,
                {
                    "photo_id",
                    "content_revision",
                    "sanitized_sha256",
                    "policy_id",
                    "policy_revision",
                    "screening_version",
                    "calibration_version",
                    "status",
                },
            )
            if value["photo_id"] != photo_id or value["status"] != "clear":
                return None
            return PhotoExportBinding(
                _text(value["photo_id"], UUID),
                _integer(value["content_revision"]),
                _text(value["sanitized_sha256"], DIGEST),
                PhotoPolicy.parse(value),
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return None

    def authorize(self, bindings: list[PhotoExportBinding]) -> set[str]:
        if not bindings:
            return set()
        try:
            payload = {"schema_version": VERSION, "photos": [item.payload() for item in bindings]}
            if len(bindings) > 10_000 or len(json.dumps(payload).encode("utf-8")) > 8_000_000:
                return set()
            ids = [item.photo_id for item in bindings]
            if len(set(ids)) != len(ids):
                return set()
            response = _object(
                self._rpc("authorize_photo_privacy_export", {"p_request": payload}),
                {
                    "version",
                    "publication_open",
                    "policy_id",
                    "policy_revision",
                    "screening_version",
                    "calibration_version",
                    "authorizations",
                },
            )
            if response["version"] != VERSION or response["publication_open"] is not True:
                return set()
            policy = PhotoPolicy.parse(response)
            decisions = response["authorizations"]
            if not isinstance(decisions, list) or len(decisions) != len(bindings):
                return set()
            allowed: set[str] = set()
            for binding, raw in zip(bindings, decisions, strict=True):
                decision = _object(raw, {"photo_id", "authorized"})
                if (
                    decision["photo_id"] != binding.photo_id
                    or type(decision["authorized"]) is not bool
                ):
                    return set()
                if decision["authorized"] and binding.policy == policy:
                    allowed.add(binding.photo_id)
            return allowed
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return set()
