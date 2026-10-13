"""Protected local state and bounded file reads for private operator tools."""

from __future__ import annotations

import fcntl
import os
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pipeline.privacy_contract import PrivacyError


def read_file(path: Path, maximum: int) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
                raise PrivacyError()
            data = stream.read(maximum + 1)
        if len(data) > maximum:
            raise PrivacyError()
        return data
    except Exception:
        raise PrivacyError() from None


class PrivateDirectory:
    def __init__(self, path: Path) -> None:
        try:
            if any((parent / ".git").exists() for parent in (path, *path.parents)):
                raise PrivacyError()
            if (
                not path.is_absolute()
                or path.resolve() != path
                or any(
                    part.lower()
                    in {
                        "cloudstorage",
                        "mobile documents",
                        "icloud drive",
                        "dropbox",
                        "onedrive",
                        "public",
                        "shared",
                    }
                    for part in path.parts
                )
            ):
                raise PrivacyError()
            path.mkdir(mode=0o700, exist_ok=True)
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
                raise PrivacyError()
            self.path = path
        except Exception:
            raise PrivacyError() from None

    @contextmanager
    def lock(self) -> Iterator[None]:
        descriptor = os.open(self.path / ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise PrivacyError()
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(descriptor)

    def write(self, name: str, data: bytes) -> Path:
        if Path(name).name != name or name in {"", ".", ".."}:
            raise PrivacyError()
        descriptor, temporary = tempfile.mkstemp(prefix=".writing-", dir=self.path)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path / name)
            directory = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return self.path / name

    def read(self, path: Path, maximum: int) -> bytes:
        info = path.lstat()
        if path.parent != self.path or info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise PrivacyError()
        return read_file(path, maximum)
