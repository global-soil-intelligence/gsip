"""APP-2C1: bind reviewed source evidence; never certify iOS storage protection.

The CLI reads only one designated directory of exact public-source snapshots and fixed
repository source files. It accepts no caller profile, performs no network/process/native
operation and writes no files. Exact bytes identify the reviewed evidence; they do not prove
upstream provenance, real native resolution, runtime capabilities, physical erasure, backup
exclusion or device behavior. Generated resolution is observed-only, not a repository lock.
Checks cover a bounded read snapshot; they cannot prevent a later filesystem modification.
A successful source review remains blocked for APP-2C2 and returns exit status 3.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAX_SOURCE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024
MAX_BINDINGS = 128
PROFILE_ID = "gsip-app2c1-2026-10-14"
_ERROR = "Source evidence is unavailable or invalid"


class AuditError(Exception):
    """A bounded generic evidence refusal, never containing incoming values."""


@dataclass(frozen=True)
class SourceBinding:
    path: str
    size: int
    sha256: str


PUBLIC_SOURCES: tuple[SourceBinding, ...] = (
    SourceBinding(
        "filesystem-mapping.source",
        2112,
        "b4dd96f40a57dff5b43f9b93e208b5f64ae716bcda57378ca4f44a83b713c7c0",
    ),
    SourceBinding(
        "filesystem-location-resolver.source",
        1625,
        "4c46c0a5cf88e8257ea7fd61b33ba098ec26227918c48b53e89ceff8d10fb20e",
    ),
    SourceBinding(
        "filesystem-operation-executor.source",
        6329,
        "ea8252a6d1195ffb3442c8a8ad9149acde5332d3644fcd43739b45227bc13bed",
    ),
    SourceBinding(
        "filesystem-api-types.source",
        17469,
        "2a573b6cbd506aca157950d852470114e4171da2ffc53adb52399be1fa002f7c",
    ),
    SourceBinding(
        "filesystem-plugin-registration.source",
        327,
        "5389deeff8a5762e28285d5051fac2c01c3275f4f2719a9ae22280143bb5095d",
    ),
    SourceBinding(
        "filesystem-web-fallback.source",
        23426,
        "038cfd655a54eafcc7efd6566c4ade942558d69135b4e5f01a58e5da87446685",
    ),
    SourceBinding(
        "filesystem-swift-dependency-range.source",
        1048,
        "1e2799f6a21acc5707709e81de7682eff9fd3df294a80b0f1cb115f7093505f4",
    ),
    SourceBinding(
        "ion-filesystem-manager.source",
        15865,
        "0d59a711c547b26f9d16b9743142c32087b94b40ee4f530665b1b76434c1a084",
    ),
    SourceBinding(
        "capacitor-ios-webview.source",
        16487,
        "0485aee1f25b0ed028ce944fb98306e6a92330038ce7fd923aa87b4ada4bbfec",
    ),
    SourceBinding(
        "capacitor-ios-cookie-manager.source",
        4758,
        "57f0163dcf2e446a5d17fb96919b369479b1202f41bd77fa0f5f357e261f3def",
    ),
    SourceBinding(
        "capacitor-ios-keyvalue-store.source",
        11015,
        "b500084f5bb35df5a74ead375c57cf48186d8adf91091760c4d07276d4fdbbd4",
    ),
    SourceBinding(
        "supabase-client-storage.source",
        26052,
        "eb923579957052a1160cda34a65ff67496d46abf37ae022cdd331f8d6d8bd800",
    ),
    SourceBinding(
        "auth-client-storage.source",
        257301,
        "7552500e375665e28acf23fb552ccbf1ef11379afab15859b2f670f1ae9aee9f",
    ),
    SourceBinding(
        "auth-pkce-helpers.source",
        23030,
        "82025113a07125f319380ec5a510e58544a04f6e3bcf82c6eb8ce3a2cc6b07c5",
    ),
    SourceBinding(
        "camera-plugin.source",
        30250,
        "995102b7abf1138e5ca9e13d3ffb93a85d244994d734c1d5443f0fb428faeba8",
    ),
    SourceBinding(
        "ion-camera-temporary-paths.source",
        2770,
        "4026b77b0196e9843c22648f5d0f12defc07c43826a2ad5b8e7725bff7f84dee",
    ),
    SourceBinding(
        "ion-camera-flow.source",
        18686,
        "5444e8519b40b9798f643ad5043322ec77ec6ce05a9f9f2c6ad9edfcee95d729",
    ),
    SourceBinding(
        "notifications-native.source",
        36659,
        "d923157a6e8522dab046c43b773b4a2b149d19ff98902e9caf40778e83a7d2d4",
    ),
    SourceBinding(
        "observed-native-resolution.source",
        1233,
        "03c73f532a75e0228889472ed648d4ed36a68f05566922ecfb05abef16b18b3f",
    ),
)

REPOSITORY_SOURCES: tuple[SourceBinding, ...] = (
    SourceBinding(
        "apps/capture-pwa/src/queue.ts",
        15180,
        "ce389c528acdfce3cb75acab1bfd55d615f3cf5ba8104130a8813ec6cd889f31",
    ),
    SourceBinding(
        "apps/capture-pwa/src/supabase.ts",
        17613,
        "ab953f710703d675d9d3138227dcf840f3c6c51eec0c65d360932630340d3197",
    ),
    SourceBinding(
        "apps/capture-pwa/src/sync.ts",
        5847,
        "8e7bb7a073060c882cda08a04214e1ed69be4b85d0623d00c74d81bf67018c9c",
    ),
    SourceBinding(
        "apps/capture-pwa/src/syncReminder.ts",
        15754,
        "f118a3ff7cfdcb2489b4cda1df0e33a029d63bab778b45a68926c883972259d3",
    ),
    SourceBinding(
        "apps/capture-pwa/src/library.ts",
        2938,
        "d9ab1c2c46656e1325ee44b645fb9160d95b9b10773870cf73180fe19f184f16",
    ),
    SourceBinding(
        "apps/capture-pwa/src/types.ts",
        1915,
        "15ab78d37d2d7edb8703553b825344cc2a2f6cbf193bbbd1af671a0fd2db7ebb",
    ),
    SourceBinding(
        "apps/capture-pwa/src/platform/camera.ts",
        4859,
        "33b5e2a6bbf61c2bd537a4ff7b0973adb959a37a50ed5e51d4cc51234836f4df",
    ),
    SourceBinding(
        "apps/capture-pwa/src/platform/notifications.ts",
        5850,
        "696c89be417cc8dfac6466f6f163b7aaff7eb84143c43200c1a793e8ed05787f",
    ),
    SourceBinding(
        "apps/capture-pwa/src/platform/types.ts",
        2639,
        "44289e71e53301054297ad594645bf18cddb1e0626328eec12867b46d0fffb86",
    ),
    SourceBinding(
        "apps/capture-pwa/src/platform/index.ts",
        3584,
        "f5d1903df16286dc3d9a6d565ffcd62b2af89388e84f1a4e9305c4c53aa10f83",
    ),
    SourceBinding(
        "apps/capture-pwa/package.json",
        1081,
        "b7f0439a1342222b4c05689047f81c6a7b577891b40836c0e7431b304717a115",
    ),
    SourceBinding(
        "apps/capture-pwa/capacitor.config.ts",
        1112,
        "90c2d96cd148b7b34c4c4bc2b94a6feec74410de4f00c5862ff5da5f1cad4a69",
    ),
    SourceBinding(
        "pnpm-lock.yaml", 225620, "da0d4b977e27b31e419e234cb5e4b2f2935d33874b6db828eed4231d257aad19"
    ),
)

REQUIRED_STORES: frozenset[str] = frozenset(
    {
        "submissions",
        "draftPhotos",
        "libraryDraft",
        "libraryNamespace",
        "queueState",
        "syncReminder",
    }
)
REQUIRED_SURFACES: frozenset[str] = frozenset(
    {
        "indexeddb-submissions",
        "indexeddb-draft-photos",
        "indexeddb-library-draft",
        "indexeddb-library-namespace",
        "indexeddb-queue-state",
        "indexeddb-sync-reminder",
        "last-account-uid",
        "auth-session",
        "auth-legacy-user",
        "auth-pkce-verifiers",
        "webkit-database-journals",
        "webkit-local-storage",
        "webkit-cookies",
        "native-shared-cookies",
        "response-http-cache",
        "native-sdk-preferences",
        "camera-picker-temporary-files",
        "staging-recovery-files",
        "os-notifications",
    }
)
INVENTORY_SURFACES: tuple[str, ...] = (
    "indexeddb-submissions",
    "indexeddb-draft-photos",
    "indexeddb-library-draft",
    "indexeddb-library-namespace",
    "indexeddb-queue-state",
    "indexeddb-sync-reminder",
    "last-account-uid",
    "auth-session",
    "auth-legacy-user",
    "auth-pkce-verifiers",
    "webkit-database-journals",
    "webkit-local-storage",
    "webkit-cookies",
    "native-shared-cookies",
    "response-http-cache",
    "native-sdk-preferences",
    "camera-picker-temporary-files",
    "staging-recovery-files",
    "os-notifications",
)
_QUEUE_PATH = "apps/capture-pwa/src/queue.ts"


def _refuse() -> AuditError:
    return AuditError(_ERROR)


def _snapshot(value: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _identity(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino


def _directory_flags() -> int:
    # Refuse rather than silently following links on an unsupported platform.
    if not all(hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")):
        raise _refuse()
    if os.open not in os.supports_dir_fd or os.stat not in os.supports_dir_fd:
        raise _refuse()
    if os.stat not in os.supports_follow_symlinks:
        raise _refuse()
    return os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)


def _parts(path: str) -> tuple[str, ...]:
    if not isinstance(path, str) or not path or len(path) > 512:
        raise _refuse()
    pieces = tuple(path.split("/"))
    if any(
        item in {"", ".", ".."} or re.fullmatch(r"[A-Za-z0-9_.-]+", item) is None for item in pieces
    ):
        raise _refuse()
    return pieces


def _bindings(values: tuple[SourceBinding, ...], public: bool) -> tuple[SourceBinding, ...]:
    if type(values) is not tuple or not 1 <= len(values) <= MAX_BINDINGS:
        raise _refuse()
    seen: set[str] = set()
    for binding in values:
        if not isinstance(binding, SourceBinding):
            raise _refuse()
        parts = _parts(binding.path)
        if public and (
            len(parts) != 1
            or re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,95}\.source", binding.path) is None
        ):
            raise _refuse()
        if (
            type(binding.size) is not int
            or not 1 <= binding.size <= MAX_SOURCE_BYTES
            or not isinstance(binding.sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", binding.sha256) is None
            or binding.path in seen
        ):
            raise _refuse()
        seen.add(binding.path)
    return values


def _open_directory(path: Path) -> int:
    if not isinstance(path, Path):
        raise _refuse()
    absolute = path if path.is_absolute() else Path.cwd() / path
    if ".." in absolute.parts or absolute == Path("/"):
        raise _refuse()
    flags = _directory_flags()
    current = os.open("/", flags)
    try:
        for piece in absolute.parts[1:]:
            child = os.open(piece, flags, dir_fd=current)
            try:
                if _identity(os.fstat(child)) != _identity(
                    os.stat(piece, dir_fd=current, follow_symlinks=False)
                ):
                    raise _refuse()
            except BaseException:
                os.close(child)
                raise
            os.close(current)
            current = child
        if not stat.S_ISDIR(os.fstat(current).st_mode):
            raise _refuse()
        return current
    except BaseException:
        os.close(current)
        raise


def _relative_directory(root_fd: int, parts: tuple[str, ...]) -> int:
    current = os.dup(root_fd)
    try:
        for piece in parts:
            child = os.open(piece, _directory_flags(), dir_fd=current)
            try:
                if _identity(os.fstat(child)) != _identity(
                    os.stat(piece, dir_fd=current, follow_symlinks=False)
                ):
                    raise _refuse()
            except BaseException:
                os.close(child)
                raise
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _read_regular(root_fd: int, binding: SourceBinding) -> bytes:
    parts = _parts(binding.path)
    parent = _relative_directory(root_fd, parts[:-1])
    try:
        parent_identity = _identity(os.fstat(parent))
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0),
            dir_fd=parent,
        )
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size != binding.size
                or not 1 <= before.st_size <= MAX_SOURCE_BYTES
            ):
                raise _refuse()
            chunks: list[bytes] = []
            count = 0
            while True:
                chunk = os.read(descriptor, min(64 * 1024, binding.size + 1 - count))
                if not chunk:
                    break
                chunks.append(chunk)
                count += len(chunk)
                if count > binding.size:
                    raise _refuse()
            after = os.fstat(descriptor)
            entry = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            if (
                _snapshot(before) != _snapshot(after)
                or _snapshot(before) != _snapshot(entry)
                or count != binding.size
            ):
                raise _refuse()
            reopened = _relative_directory(root_fd, parts[:-1])
            try:
                if _identity(os.fstat(reopened)) != parent_identity:
                    raise _refuse()
            finally:
                os.close(reopened)
            data = b"".join(chunks)
            if hashlib.sha256(data).hexdigest() != binding.sha256:
                raise _refuse()
            return data
        finally:
            os.close(descriptor)
    finally:
        os.close(parent)


def _check_public_entries(descriptor: int, expected: set[str]) -> None:
    # Stop at the first unknown or extra entry instead of materializing an arbitrary directory.
    seen: set[str] = set()
    with os.scandir(descriptor) as entries:
        for entry in entries:
            if entry.name not in expected or entry.name in seen or len(seen) >= len(expected):
                raise _refuse()
            seen.add(entry.name)
    if seen != expected:
        raise _refuse()


def _same_root(path: Path, descriptor: int) -> None:
    reopened = _open_directory(path)
    try:
        if _identity(os.fstat(reopened)) != _identity(os.fstat(descriptor)):
            raise _refuse()
    finally:
        os.close(reopened)


def _check_inventory(queue: bytes) -> None:
    if (
        type(INVENTORY_SURFACES) is not tuple
        or any(not isinstance(item, str) for item in INVENTORY_SURFACES)
        or len(INVENTORY_SURFACES) != len(REQUIRED_SURFACES)
        or frozenset(INVENTORY_SURFACES) != REQUIRED_SURFACES
    ):
        raise _refuse()
    # This checks a fixed source inventory, not TypeScript semantics or capability detection.
    stores = re.findall(
        r"\bdb\.createObjectStore\(\s*(['\"])([A-Za-z][A-Za-z0-9]*)\1",
        queue.decode("utf-8"),
    )
    names = [name for _, name in stores]
    if len(names) != len(REQUIRED_STORES) or frozenset(names) != REQUIRED_STORES:
        raise _refuse()


def _report(valid: bool) -> dict[str, object]:
    return {
        "profile_id": PROFILE_ID,
        "source_review_valid": valid,
        "status": "blocked" if valid else "evidence_unverified",
        "storage_feasible": False,
        "backend_selected": False,
        "device_verified": False,
        "migration_implemented": False,
        "source_count": len(PUBLIC_SOURCES) if valid else 0,
        "repo_count": len(REPOSITORY_SOURCES) if valid else 0,
        "resolution_scope": "observed-generated-not-a-lock",
        "next_gate": "app2c2-held",
    }


def audit(public_root: Path, repository_root: Path = ROOT) -> dict[str, object]:
    """Verify only compiled bindings and inventory; a valid result still holds migration."""
    try:
        sources = _bindings(PUBLIC_SOURCES, public=True)
        repository = _bindings(REPOSITORY_SOURCES, public=False)
        if sum(item.size for item in sources + repository) > MAX_TOTAL_BYTES:
            raise _refuse()
        expected = {item.path for item in sources}
        public_fd = _open_directory(public_root)
        try:
            _check_public_entries(public_fd, expected)
            for binding in sources:
                _read_regular(public_fd, binding)
            _check_public_entries(public_fd, expected)
            _same_root(public_root, public_fd)
            repository_fd = _open_directory(repository_root)
            try:
                queue: bytes | None = None
                for binding in repository:
                    data = _read_regular(repository_fd, binding)
                    if binding.path == _QUEUE_PATH:
                        queue = data
                if queue is None:
                    raise _refuse()
                _check_inventory(queue)
                _same_root(repository_root, repository_fd)
            finally:
                os.close(repository_fd)
            _check_public_entries(public_fd, expected)
            _same_root(public_root, public_fd)
        finally:
            os.close(public_fd)
    except (AuditError, OSError, ValueError, TypeError, UnicodeError):
        raise _refuse() from None
    return _report(True)


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    report = _report(False)
    code = 2
    if (
        isinstance(arguments, list)
        and len(arguments) == 1
        and isinstance(arguments[0], str)
        and 0 < len(arguments[0]) <= 4096
    ):
        try:
            report = audit(Path(arguments[0]))
            code = 3
        except (AuditError, OSError, ValueError, TypeError):
            pass
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
