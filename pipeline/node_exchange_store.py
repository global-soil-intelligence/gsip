"""Bounded private filesystem transactions for one explicitly designated synthetic root.

The simulator owns the non-payload metadata schema and all authority decisions. This
module supplies no network, credentials, scientific validation or real erasure claim.
An unsafe or ambiguous artifact is held, never repaired or swept by a glob.
"""

from __future__ import annotations

import ctypes
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import sys
import threading
from collections.abc import Callable, Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Literal, TypeVar, cast
from uuid import UUID, uuid4

MAX_METADATA_BYTES = 32_000_000
MAX_BLOB_BYTES = 2_000_000
MAX_RETAINED_BYTES = 200_000_000
_ERROR = "private store unavailable"
_VERSION = "gsip-node-exchange-store-v1"
_CATEGORIES = {"source", "recipient", "draft", "preparation"}
_DIGEST = re.compile(r"[0-9a-f]{64}")
_SURROGATE = re.compile(r"[\ud800-\udfff]")
_MAX_GENERATION = (1 << 63) - 1
_CHUNK = 1_048_576
# An ancestor exception only; payloads still require an explicit private allowed root.
_SYSTEM_TMP = {Path("/private/tmp"), Path("/tmp")}  # noqa: S108
T = TypeVar("T")
BlobCategory = Literal["source", "recipient", "draft", "preparation"]


class PrivateExchangeStoreError(ValueError):
    """A fixed, non-input-bearing refusal for ordinary callers."""


def _guard(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except Exception:
        failed = True
    # Raising outside the handler removes input-bearing cause AND context.
    if failed:
        raise PrivateExchangeStoreError(_ERROR)
    raise AssertionError


def _fault(point: str) -> None:
    """Private test seam; production performs no callback, output or environment lookup."""
    del point


def _require(condition: bool) -> None:
    if not condition:
        raise PrivateExchangeStoreError(_ERROR)


def _uuid(value: object) -> str:
    _require(type(value) is str)
    text = cast(str, value)
    _require(str(UUID(text)) == text)
    return text


def _clone(value: Any, depth: int = 0) -> Any:
    """Own strict JSON without custom serializers, non-finite values or cycles."""
    _require(depth <= 64)
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float:
        _require(math.isfinite(value))
        return value
    if type(value) is str:
        _require(_SURROGATE.search(value) is None)
        return value
    if type(value) is list:
        return [_clone(item, depth + 1) for item in value]
    _require(type(value) is dict)
    result: dict[str, Any] = {}
    for key, item in value.items():
        _require(type(key) is str)
        result[_clone(key, depth + 1)] = _clone(item, depth + 1)
    return result


def _data(value: Any) -> dict[str, Any]:
    _require(type(value) is dict)
    return cast(dict[str, Any], _clone(value))


def _encode(state: dict[str, Any]) -> bytes:
    encoded = json.dumps(
        _clone(state), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")
    _require(len(encoded) <= MAX_METADATA_BYTES)
    return encoded


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


@dataclass(frozen=True)
class BlobWrite:
    blob_id: str
    category: BlobCategory
    original_bytes: bytes


@dataclass(frozen=True)
class BlobRef:
    blob_id: str
    category: BlobCategory
    byte_count: int
    sha256: str


@dataclass(frozen=True)
class StoreSnapshot:
    generation: int
    data: dict[str, Any]
    blobs: dict[str, BlobRef]


def _ref(value: Any) -> BlobRef:
    _require(type(value) is dict)
    _require(set(value) == {"blob_id", "category", "byte_count", "sha256"})
    identity = _uuid(value["blob_id"])
    _require(type(value["category"]) is str and value["category"] in _CATEGORIES)
    _require(type(value["byte_count"]) is int and 0 <= value["byte_count"] <= MAX_BLOB_BYTES)
    _require(type(value["sha256"]) is str and _DIGEST.fullmatch(value["sha256"]) is not None)
    return BlobRef(identity, value["category"], value["byte_count"], value["sha256"])


def _ref_json(ref: BlobRef) -> dict[str, Any]:
    return {
        "blob_id": ref.blob_id,
        "category": ref.category,
        "byte_count": ref.byte_count,
        "sha256": ref.sha256,
    }


def _state(value: Any) -> dict[str, Any]:
    result = _data(value)
    _require(set(result) == {"version", "generation", "data", "blobs", "pending"})
    _require(result["version"] == _VERSION)
    _require(type(result["generation"]) is int and 0 <= result["generation"] < _MAX_GENERATION)
    _data(result["data"])
    _require(type(result["blobs"]) is dict)
    for key, value in result["blobs"].items():
        _require(_uuid(key) == _ref(value).blob_id)
    pending = result["pending"]
    if pending is not None:
        _require(result["generation"] < _MAX_GENERATION - 1)
        _require(type(pending) is dict)
        if pending.get("kind") == "put":
            _require(set(pending) == {"kind", "blob", "next_data", "stage", "stage_identity"})
            ref = _ref(pending["blob"])
            _require(ref.blob_id not in result["blobs"])
            _data(pending["next_data"])
            _uuid(pending["stage"])
            identity = pending["stage_identity"]
            _require(
                identity is None
                or (
                    type(identity) is list
                    and len(identity) == 2
                    and all(type(part) is int and part >= 0 for part in identity)
                )
            )
        else:
            _require(set(pending) == {"kind", "blob_ids"} and pending["kind"] == "erase")
            _require(type(pending["blob_ids"]) is list)
            ids = [_uuid(item) for item in pending["blob_ids"]]
            _require(len(set(ids)) == len(ids) and all(item in result["blobs"] for item in ids))
    _require(len(_encode(result)) <= MAX_METADATA_BYTES)
    return result


def _same(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _unchanged(left: os.stat_result, right: os.stat_result) -> bool:
    return _same(left, right) and (
        left.st_mode,
        left.st_uid,
        left.st_nlink,
        left.st_size,
        left.st_mtime_ns,
        left.st_ctime_ns,
    ) == (
        right.st_mode,
        right.st_uid,
        right.st_nlink,
        right.st_size,
        right.st_mtime_ns,
        right.st_ctime_ns,
    )


def _private_directory(info: os.stat_result) -> None:
    _require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700)
    _require(info.st_uid == os.getuid())


def _private_file(info: os.stat_result, bound: int) -> None:
    _require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600)
    _require(info.st_nlink == 1 and info.st_uid == os.getuid() and 0 <= info.st_size <= bound)


def _path(value: Path | str) -> Path:
    raw = os.fspath(value)
    _require(isinstance(raw, str) and raw.startswith("/"))
    _require(not any(part in (".", "..") for part in raw.split("/")))
    return Path(raw)


@dataclass(frozen=True)
class _Directory:
    fd: int
    name: str
    info: os.stat_result
    private: bool


def _guard_chain(directories: list[_Directory]) -> None:
    for index, directory in enumerate(directories):
        current = os.fstat(directory.fd)
        _require(_same(current, directory.info) and stat.S_ISDIR(current.st_mode))
        if directory.private:
            _private_directory(current)
        else:
            path = Path("/", *(item.name for item in directories[1 : index + 1]))
            sticky_tmp = path in _SYSTEM_TMP
            _require(
                current.st_uid in (0, os.getuid())
                and (
                    not current.st_mode & 0o022
                    or (sticky_tmp and bool(current.st_mode & stat.S_ISVTX))
                )
            )
        if index:
            named = os.stat(directory.name, dir_fd=directories[index - 1].fd, follow_symlinks=False)
            _require(_same(current, named) and stat.S_ISDIR(named.st_mode))


def _chain(path: Path, allowed: Path) -> list[_Directory]:
    directories: list[_Directory] = []
    try:
        current = Path("/")
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        directories.append(_Directory(fd, "", os.fstat(fd), False))
        for part in path.parts[1:]:
            current /= part
            before = os.stat(part, dir_fd=directories[-1].fd, follow_symlinks=False)
            _require(stat.S_ISDIR(before.st_mode))
            private = current == allowed or allowed in current.parents
            if private:
                _private_directory(before)
            else:
                # The OS temporary directory is the sole trusted sticky exception.
                sticky_tmp = current in _SYSTEM_TMP
                _require(
                    before.st_uid in (0, os.getuid())
                    and (
                        not before.st_mode & 0o022
                        or (sticky_tmp and bool(before.st_mode & stat.S_ISVTX))
                    )
                )
            fd = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directories[-1].fd
            )
            after = os.fstat(fd)
            if not _same(before, after):
                os.close(fd)
                raise PrivateExchangeStoreError(_ERROR)
            directories.append(_Directory(fd, part, after, private))
        return directories
    except BaseException:
        for directory in reversed(directories):
            os.close(directory.fd)
        raise


def _rename_no_replace(source_fd: int, source: str, destination_fd: int, destination: str) -> None:
    """Rename one single-link inode atomically; never use a transient hardlink."""
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function = getattr(library, "renameatx_np", None)
        flag = 0x00000004  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        function = getattr(library, "renameat2", None)
        flag = 1  # RENAME_NOREPLACE
    else:
        function = None
        flag = 0
    if function is None:
        raise PrivateExchangeStoreError(_ERROR)
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    function.restype = ctypes.c_int
    _require(function(source_fd, source.encode(), destination_fd, destination.encode(), flag) == 0)


class PrivateExchangeStore:
    """Creation and opening are separate; an existing incomplete root never initializes."""

    def __init__(
        self,
        root: Path,
        allowed_root: Path,
        identity: tuple[int, int],
        chain_identity: tuple[tuple[int, int], ...],
        lock_identity: tuple[int, int] | None = None,
    ):
        self.root = root
        self.allowed_root = allowed_root
        self._identity = identity
        self._chain_identity = chain_identity
        self._lock_identity = lock_identity

    @classmethod
    def create_designated(cls, root: Path | str, allowed_root: Path | str) -> PrivateExchangeStore:
        def create() -> PrivateExchangeStore:
            target, allowed = _path(root), _path(allowed_root)
            _require(target != allowed and allowed in target.parents)
            directories = _chain(target.parent, allowed)
            root_fd = -1
            try:
                parent = directories[-1].fd
                _guard_chain(directories)
                os.mkdir(target.name, 0o700, dir_fd=parent)
                root_info = os.stat(target.name, dir_fd=parent, follow_symlinks=False)
                root_fd = os.open(
                    target.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
                )
                _private_directory(os.fstat(root_fd))
                _require(_same(root_info, os.fstat(root_fd)))
                directories.append(_Directory(root_fd, target.name, root_info, True))
                root_fd = -1
                managed_fd = directories[-1].fd
                for name in ("blobs", "staging"):
                    _guard_chain(directories)
                    os.mkdir(name, 0o700, dir_fd=managed_fd)
                lock_identity = None
                for name, content in (
                    (".lock", b""),
                    (
                        "state.json",
                        _encode(
                            {
                                "version": _VERSION,
                                "generation": 0,
                                "data": {},
                                "blobs": {},
                                "pending": None,
                            }
                        ),
                    ),
                ):
                    _guard_chain(directories)
                    fd = os.open(
                        name,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=managed_fd,
                    )
                    try:
                        _private_file(os.fstat(fd), MAX_METADATA_BYTES)
                        if name == ".lock":
                            lock_info = os.fstat(fd)
                            lock_identity = (lock_info.st_dev, lock_info.st_ino)
                        _write_all(fd, content)
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                os.fsync(managed_fd)
                os.fsync(parent)
                _guard_chain(directories)
                info = os.fstat(managed_fd)
                return cls(
                    target,
                    allowed,
                    (info.st_dev, info.st_ino),
                    tuple((item.info.st_dev, item.info.st_ino) for item in directories),
                    lock_identity,
                )
            finally:
                if root_fd >= 0:
                    os.close(root_fd)
                for directory in reversed(directories):
                    os.close(directory.fd)

        return _guard(create)

    @classmethod
    def open_designated(cls, root: Path | str, allowed_root: Path | str) -> PrivateExchangeStore:
        def open_existing() -> PrivateExchangeStore:
            target, allowed = _path(root), _path(allowed_root)
            _require(target != allowed and allowed in target.parents)
            directories = _chain(target, allowed)
            try:
                info = directories[-1].info
                store = cls(
                    target,
                    allowed,
                    (info.st_dev, info.st_ino),
                    tuple((item.info.st_dev, item.info.st_ino) for item in directories),
                )
            finally:
                for directory in reversed(directories):
                    os.close(directory.fd)
            with store.locked():
                pass
            return store

        return _guard(open_existing)

    def locked(self) -> AbstractContextManager[PrivateExchangeSession]:
        return _OwnedLockContext(self._locked())

    @contextmanager
    def _locked(self) -> Iterator[PrivateExchangeSession]:
        session = _guard(lambda: PrivateExchangeSession._acquire(self))
        try:
            yield session
        finally:
            session._close()


def _write_all(fd: int, content: bytes, *, payload: bool = False) -> None:
    position = 0
    while position < len(content):
        written = os.write(fd, content[position : position + _CHUNK])
        _require(written > 0)
        position += written
        if payload:
            _fault("put_payload_chunk")


class PrivateExchangeSession:
    """A process/thread-bound root session; every access validates durable state.

    The flock protects independently opened sessions, not concurrent users of one
    inherited descriptor. Only its creating process/thread may use this session.
    """

    def __init__(self, store: PrivateExchangeStore, directories: list[_Directory]):
        self._store = store
        self._directories = directories
        self._root_fd = directories[-1].fd
        self._lock_fd = -1
        self._blobs_fd = -1
        self._staging_fd = -1
        self._lock_info: os.stat_result | None = None
        self._blobs_info: os.stat_result | None = None
        self._staging_info: os.stat_result | None = None
        self._active = True
        self._owner_pid = os.getpid()
        self._owner_thread = threading.current_thread()

    @classmethod
    def _acquire(cls, store: PrivateExchangeStore) -> PrivateExchangeSession:
        directories = _chain(store.root, store.allowed_root)
        session = cls(store, directories)
        try:
            _require((directories[-1].info.st_dev, directories[-1].info.st_ino) == store._identity)
            _require(
                tuple((item.info.st_dev, item.info.st_ino) for item in directories)
                == store._chain_identity
            )
            session._lock_fd, session._lock_info = session._open_file(".lock", session._root_fd, 0)
            lock_identity = (session._lock_info.st_dev, session._lock_info.st_ino)
            if store._lock_identity is None:
                store._lock_identity = lock_identity
            _require(lock_identity == store._lock_identity)
            fcntl.flock(session._lock_fd, fcntl.LOCK_EX)
            session._blobs_fd, session._blobs_info = session._open_directory("blobs")
            session._staging_fd, session._staging_info = session._open_directory("staging")
            session._recover()
            return session
        except BaseException:
            session._close()
            raise

    def _close(self) -> None:
        _require(os.getpid() != self._owner_pid or threading.current_thread() is self._owner_thread)
        self._active = False
        for fd in (self._staging_fd, self._blobs_fd, self._lock_fd):
            if fd >= 0:
                os.close(fd)
        for directory in reversed(self._directories):
            os.close(directory.fd)

    def _open_directory(self, name: str) -> tuple[int, os.stat_result]:
        before = os.stat(name, dir_fd=self._root_fd, follow_symlinks=False)
        _private_directory(before)
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self._root_fd)
        try:
            after = os.fstat(fd)
            _require(_same(before, after))
            _private_directory(after)
            return fd, after
        except BaseException:
            os.close(fd)
            raise

    def _open_file(self, name: str, directory_fd: int, bound: int) -> tuple[int, os.stat_result]:
        before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        _private_file(before, bound)
        _fault("file_before_open")
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        try:
            after = os.fstat(fd)
            _require(_unchanged(before, after))
            _private_file(after, bound)
            _fault("file_after_open")
            self._binding(fd, directory_fd, name, after, bound)
            return fd, after
        except BaseException:
            os.close(fd)
            raise

    def _binding(
        self, fd: int, directory_fd: int, name: str, before: os.stat_result, bound: int
    ) -> None:
        after = os.fstat(fd)
        named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        _private_file(after, bound)
        _private_file(named, bound)
        _require(_unchanged(before, after) and _same(after, named))

    def _guard_root(self) -> None:
        _require(self._active)
        _require(
            os.getpid() == self._owner_pid and threading.current_thread() is self._owner_thread
        )
        _guard_chain(self._directories)
        _require(self._lock_info is not None)
        self._binding(
            self._lock_fd, self._root_fd, ".lock", cast(os.stat_result, self._lock_info), 0
        )
        for name, fd, info in (
            ("blobs", self._blobs_fd, self._blobs_info),
            ("staging", self._staging_fd, self._staging_info),
        ):
            _require(info is not None)
            descriptor = os.fstat(fd)
            named = os.stat(name, dir_fd=self._root_fd, follow_symlinks=False)
            _private_directory(descriptor)
            _private_directory(named)
            _require(_same(descriptor, cast(os.stat_result, info)) and _same(descriptor, named))

    def _read(self, directory_fd: int, name: str, bound: int, ref: BlobRef | None = None) -> bytes:
        fd, before = self._open_file(name, directory_fd, bound)
        try:
            chunks: list[bytes] = []
            length = 0
            while True:
                chunk = os.read(fd, min(_CHUNK, bound + 1 - length))
                if not chunk:
                    break
                chunks.append(chunk)
                length += len(chunk)
                _require(length <= bound)
                _fault("file_read_chunk")
            content = b"".join(chunks)
            _fault("file_after_read")
            self._binding(fd, directory_fd, name, before, bound)
            _require(length == before.st_size)
            if ref is not None:
                _require(
                    length == ref.byte_count and hashlib.sha256(content).hexdigest() == ref.sha256
                )
            self._guard_root()
            return content
        finally:
            os.close(fd)

    def _read_state(self, name: str = "state.json") -> dict[str, Any]:
        content = self._read(self._root_fd, name, MAX_METADATA_BYTES)
        _require(not content.startswith(b"\xef\xbb\xbf"))
        return _state(json.loads(content, object_pairs_hook=_unique))

    def _names(self, directory_fd: int, permitted: set[str]) -> set[str]:
        found: set[str] = set()
        with os.scandir(directory_fd) as entries:
            for entry in entries:
                _require(entry.name in permitted and len(found) < len(permitted))
                found.add(entry.name)
        return found

    def _audit(self, state: dict[str, Any]) -> None:
        self._guard_root()
        self._names(self._root_fd, {".lock", "state.json", "state.next", "blobs", "staging"})
        refs = {key: _ref(value) for key, value in state["blobs"].items()}
        pending = state["pending"]
        permitted_blobs, permitted_stages = set(refs), set()
        missing_allowed: set[str] = set()
        pending_ref: BlobRef | None = None
        if pending is not None:
            if pending["kind"] == "erase":
                missing_allowed = set(pending["blob_ids"])
            else:
                pending_ref = _ref(pending["blob"])
                permitted_blobs.add(pending_ref.blob_id)
                permitted_stages.add(pending["stage"])
        blobs = self._names(self._blobs_fd, permitted_blobs)
        stages = self._names(self._staging_fd, permitted_stages)
        _require(set(refs) - blobs <= missing_allowed)
        retained = 0
        for name in blobs:
            ref = refs.get(name, pending_ref)
            _require(ref is not None)
            checked_ref = cast(BlobRef, ref)
            self._read(self._blobs_fd, name, MAX_BLOB_BYTES, checked_ref)
            retained += checked_ref.byte_count
            if name not in refs:
                _require(pending["stage_identity"] is not None)
                info = os.stat(name, dir_fd=self._blobs_fd, follow_symlinks=False)
                _require([info.st_dev, info.st_ino] == pending["stage_identity"])
        for name in stages:
            _require(pending_ref is not None and pending["stage_identity"] is not None)
            info = os.stat(name, dir_fd=self._staging_fd, follow_symlinks=False)
            _private_file(info, cast(BlobRef, pending_ref).byte_count)
            _require([info.st_dev, info.st_ino] == pending["stage_identity"])
            self._read(self._staging_fd, name, cast(BlobRef, pending_ref).byte_count)
            retained += info.st_size
        if pending_ref is not None:
            _require(not (pending_ref.blob_id in blobs and stages))
            # Charge the full reserved blob while any pending state remains.
            retained += (
                pending_ref.byte_count
                - sum(
                    os.stat(name, dir_fd=self._staging_fd, follow_symlinks=False).st_size
                    for name in stages
                )
                - (pending_ref.byte_count if pending_ref.blob_id in blobs else 0)
            )
        _require(retained <= MAX_RETAINED_BYTES)
        self._guard_root()

    def _replace(self, state: dict[str, Any]) -> None:
        content = _encode(state)
        self._guard_root()
        _require(
            "state.next"
            not in self._names(
                self._root_fd,
                {
                    ".lock",
                    "state.json",
                    "state.next",
                    "blobs",
                    "staging",
                },
            )
        )
        old_fd, old_info = self._open_file("state.json", self._root_fd, MAX_METADATA_BYTES)
        next_fd = -1
        try:
            _fault("metadata_before_create")
            self._guard_root()
            next_fd = os.open(
                "state.next",
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self._root_fd,
            )
            next_info = os.fstat(next_fd)
            _private_file(next_info, MAX_METADATA_BYTES)
            _fault("metadata_before_write")
            _write_all(next_fd, content)
            _fault("metadata_after_write")
            os.fsync(next_fd)
            os.fsync(self._root_fd)
            _fault("metadata_after_fsync")
            # Check the written image as well as both names after every injected barrier.
            written_info = os.fstat(next_fd)
            _private_file(written_info, MAX_METADATA_BYTES)
            _require(written_info.st_size == len(content) and _same(written_info, next_info))
            _require(
                _same(
                    written_info, os.stat("state.next", dir_fd=self._root_fd, follow_symlinks=False)
                )
            )
            _fault("metadata_before_promote")
            self._guard_root()
            self._binding(old_fd, self._root_fd, "state.json", old_info, MAX_METADATA_BYTES)
            self._binding(next_fd, self._root_fd, "state.next", written_info, MAX_METADATA_BYTES)
            _require(self._read(self._root_fd, "state.next", MAX_METADATA_BYTES) == content)
            os.replace(
                "state.next", "state.json", src_dir_fd=self._root_fd, dst_dir_fd=self._root_fd
            )
            _fault("metadata_after_promote")
            os.fsync(self._root_fd)
            _fault("metadata_after_directory_fsync")
            self._guard_root()
            # Rename legitimately changes ctime. Rebind the promoted descriptor and
            # re-read the exact owned image instead of treating that change as corruption.
            promoted_info = os.fstat(next_fd)
            _private_file(promoted_info, MAX_METADATA_BYTES)
            _require(_same(written_info, promoted_info) and promoted_info.st_size == len(content))
            self._binding(next_fd, self._root_fd, "state.json", promoted_info, MAX_METADATA_BYTES)
            _require(self._read(self._root_fd, "state.json", MAX_METADATA_BYTES) == content)
        finally:
            if next_fd >= 0:
                os.close(next_fd)
            os.close(old_fd)

    def _unlink(
        self,
        directory_fd: int,
        name: str,
        bound: int,
        ref: BlobRef | None = None,
        identity: list[int] | None = None,
        expected_content: bytes | None = None,
    ) -> None:
        self._guard_root()
        fd, info = self._open_file(name, directory_fd, bound)
        try:
            if identity is not None:
                _require([info.st_dev, info.st_ino] == identity)
            if ref is not None:
                self._read(directory_fd, name, bound, ref)
            if expected_content is not None:
                _require(self._read(directory_fd, name, bound) == expected_content)
            _fault("erase_before_unlink")
            self._guard_root()
            self._binding(fd, directory_fd, name, info, bound)
            os.unlink(name, dir_fd=directory_fd)
            _fault("erase_after_unlink")
            os.fsync(directory_fd)
            _fault("erase_after_directory_fsync")
            try:
                os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise PrivateExchangeStoreError(_ERROR)
        finally:
            os.close(fd)

    def _recover(self) -> dict[str, Any]:
        self._guard_root()
        state = self._read_state()
        self._audit(state)
        names = self._names(
            self._root_fd, {".lock", "state.json", "state.next", "blobs", "staging"}
        )
        if "state.next" in names:
            replacement_bytes = self._read(self._root_fd, "state.next", MAX_METADATA_BYTES)
            _require(not replacement_bytes.startswith(b"\xef\xbb\xbf"))
            replacement = _state(json.loads(replacement_bytes, object_pairs_hook=_unique))
            _require(replacement["generation"] == state["generation"] + 1)
            self._unlink(
                self._root_fd,
                "state.next",
                MAX_METADATA_BYTES,
                expected_content=replacement_bytes,
            )
        pending = state["pending"]
        if pending is None:
            return state
        _fault("recovery_before_cleanup")
        if pending["kind"] == "put":
            ref = _ref(pending["blob"])
            if ref.blob_id in self._names(self._blobs_fd, set(state["blobs"]) | {ref.blob_id}):
                self._unlink(
                    self._blobs_fd, ref.blob_id, MAX_BLOB_BYTES, ref, pending["stage_identity"]
                )
            if pending["stage"] in self._names(self._staging_fd, {pending["stage"]}):
                self._unlink(
                    self._staging_fd,
                    pending["stage"],
                    ref.byte_count,
                    identity=pending["stage_identity"],
                )
        else:
            for identity in pending["blob_ids"]:
                if identity in self._names(self._blobs_fd, set(state["blobs"])):
                    self._unlink(
                        self._blobs_fd, identity, MAX_BLOB_BYTES, _ref(state["blobs"][identity])
                    )
                del state["blobs"][identity]
        state["pending"] = None
        state["generation"] += 1
        self._replace(state)
        self._audit(state)
        return state

    def _start(self, expected_generation: int) -> dict[str, Any]:
        state = self._recover()
        _require(type(expected_generation) is int and state["generation"] == expected_generation)
        _require(state["generation"] < _MAX_GENERATION - 4)
        return state

    def _snapshot(self, state: dict[str, Any]) -> StoreSnapshot:
        snapshot = StoreSnapshot(
            state["generation"],
            _data(state["data"]),
            {identity: _ref(value) for identity, value in state["blobs"].items()},
        )
        self._guard_root()
        return snapshot

    def snapshot(self) -> StoreSnapshot:
        return _guard(lambda: self._snapshot(self._recover()))

    def read_blob(self, blob_id: str) -> bytes:
        def read() -> bytes:
            identity = _uuid(blob_id)
            state = self._recover()
            _require(identity in state["blobs"])
            content = self._read(
                self._blobs_fd, identity, MAX_BLOB_BYTES, _ref(state["blobs"][identity])
            )
            self._guard_root()
            return content

        return _guard(read)

    def commit_metadata(self, data: dict[str, Any], expected_generation: int) -> StoreSnapshot:
        def commit() -> StoreSnapshot:
            owned = _data(data)
            state = self._start(expected_generation)
            state["data"] = owned
            state["generation"] += 1
            self._replace(state)
            self._audit(state)
            return self._snapshot(state)

        return _guard(commit)

    def put_blob(
        self, data: dict[str, Any], write: BlobWrite, expected_generation: int
    ) -> StoreSnapshot:
        def put() -> StoreSnapshot:
            owned = _data(data)
            _require(type(write) is BlobWrite and type(write.original_bytes) is bytes)
            identity = _uuid(write.blob_id)
            _require(type(write.category) is str and write.category in _CATEGORIES)
            _require(len(write.original_bytes) <= MAX_BLOB_BYTES)
            ref = BlobRef(
                identity,
                write.category,
                len(write.original_bytes),
                hashlib.sha256(write.original_bytes).hexdigest(),
            )
            state = self._start(expected_generation)
            if identity in state["blobs"]:
                _require(_ref(state["blobs"][identity]) == ref)
                self._read(self._blobs_fd, identity, MAX_BLOB_BYTES, ref)
                if state["data"] == owned:
                    return self._snapshot(state)
                return self.commit_metadata(owned, expected_generation)
            _require(
                sum(_ref(value).byte_count for value in state["blobs"].values()) + ref.byte_count
                <= MAX_RETAINED_BYTES
            )
            final = _data(state)
            final["data"] = owned
            final["blobs"][identity] = _ref_json(ref)
            final["generation"] += 3
            _encode(final)
            stage = str(uuid4())
            state["pending"] = {
                "kind": "put",
                "blob": _ref_json(ref),
                "next_data": owned,
                "stage": stage,
                "stage_identity": None,
            }
            state["generation"] += 1
            _encode(state)
            _fault("put_before_reservation")
            self._replace(state)
            _fault("put_after_reservation")
            self._guard_root()
            fd = os.open(
                stage,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self._staging_fd,
            )
            try:
                info = os.fstat(fd)
                _private_file(info, 0)
                os.fsync(fd)
                os.fsync(self._staging_fd)
                _fault("put_after_empty_stage")
                state["pending"]["stage_identity"] = [info.st_dev, info.st_ino]
                state["generation"] += 1
                self._replace(state)
                _fault("put_before_payload_write")
                self._guard_root()
                self._binding(fd, self._staging_fd, stage, info, ref.byte_count)
                _write_all(fd, write.original_bytes, payload=True)
                _fault("put_after_payload_write")
                os.fsync(fd)
                _fault("put_after_payload_fsync")
                self._read(self._staging_fd, stage, MAX_BLOB_BYTES, ref)
                _fault("put_before_publish")
                self._guard_root()
                written = os.fstat(fd)
                self._binding(fd, self._staging_fd, stage, written, MAX_BLOB_BYTES)
                self._read(self._staging_fd, stage, MAX_BLOB_BYTES, ref)
                _rename_no_replace(self._staging_fd, stage, self._blobs_fd, identity)
                _fault("put_after_publish")
                os.fsync(self._staging_fd)
                os.fsync(self._blobs_fd)
                _fault("put_after_publish_fsync")
                self._read(self._blobs_fd, identity, MAX_BLOB_BYTES, ref)
                self._audit(state)
                _fault("put_before_commit")
                self._audit(state)
                final["generation"] = state["generation"] + 1
                self._replace(final)
                _fault("put_after_commit")
                self._audit(final)
                return self._snapshot(final)
            finally:
                os.close(fd)

        return _guard(put)

    def erase_blobs(
        self, restricted_data: dict[str, Any], blob_ids: Sequence[str], expected_generation: int
    ) -> StoreSnapshot:
        def erase() -> StoreSnapshot:
            owned = _data(restricted_data)
            _require(not isinstance(blob_ids, (str, bytes)))
            ids = [_uuid(value) for value in blob_ids]
            _require(len(ids) == len(set(ids)))
            state = self._start(expected_generation)
            _require(all(identity in state["blobs"] for identity in ids))
            state["data"] = owned
            state["pending"] = {"kind": "erase", "blob_ids": ids}
            state["generation"] += 1
            _encode(state)
            _fault("erase_before_restrictions")
            self._replace(state)
            _fault("erase_after_restrictions")
            return self._snapshot(self._recover())

        return _guard(erase)

    def verified_absent(self, blob_ids: Sequence[str]) -> bool:
        def absent() -> bool:
            _require(not isinstance(blob_ids, (str, bytes)))
            ids = {_uuid(value) for value in blob_ids}
            state = self._recover()
            self._audit(state)
            absent = not (ids & set(state["blobs"]))
            self._guard_root()
            return absent

        return _guard(absent)


class _OwnedLockContext(AbstractContextManager[PrivateExchangeSession]):
    """Check ownership before advancing the generator, preserving owner teardown.

    An inherited child may close its own copied descriptors without explicitly
    unlocking the parent's shared flock. A foreign same-process thread may not
    terminate the owner's generator or invalidate its live session.
    """

    def __init__(self, manager: AbstractContextManager[PrivateExchangeSession]):
        self._manager = manager
        self._pid = os.getpid()
        self._thread = threading.current_thread()
        self._entered = False
        self._finished = False

    def __enter__(self) -> PrivateExchangeSession:
        _require(os.getpid() == self._pid and threading.current_thread() is self._thread)
        _require(not self._entered and not self._finished)
        session = self._manager.__enter__()
        self._entered = True
        return session

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        _require(os.getpid() != self._pid or threading.current_thread() is self._thread)
        _require(self._entered and not self._finished)
        # Set only after the owner check. Rejected foreign exits leave the owner
        # able to use its session and eventually advance normal cleanup.
        self._finished = True
        return self._manager.__exit__(exception_type, exception, traceback)
