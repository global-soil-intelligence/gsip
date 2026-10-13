"""Private, offline library records. No network, public export or canonical acceptance."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal, NoReturn, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Fraction = Annotated[Finite, Field(ge=0, le=1)]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
MAX_RECORD_BYTES = 2_000_000


class StrictRecord(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, allow_inf_nan=False, revalidate_instances="always"
    )


class Context(StrictRecord):
    depth_top_cm: Annotated[Finite, Field(ge=0, le=200)]
    depth_bottom_cm: Annotated[Finite, Field(ge=0, le=200)]
    condition: Literal["dry", "moist", "wet", "unknown"]

    @model_validator(mode="after")
    def ordered_depths(self) -> Self:
        if self.depth_top_cm >= self.depth_bottom_cm:
            raise ValueError("invalid depth bounds")
        return self


class CameraRgb(StrictRecord):
    kind: Literal["camera_rgb"]
    source_sha256: Digest
    device_id: UUID
    extractor_version: Literal["rgb-summary-v1"]
    mean_rgb: tuple[Fraction, Fraction, Fraction]
    std_rgb: tuple[Fraction, Fraction, Fraction]
    pixel_count: Annotated[int, Field(strict=True, ge=1, le=40_000_000)]
    card_present: Annotated[bool, Field(strict=True)]
    calibration_status: Literal["uncalibrated"]


class InstrumentReflectance(StrictRecord):
    kind: Literal["instrument_reflectance"]
    source_sha256: Digest
    instrument_id: UUID
    calibration_id: UUID
    wavelength_nm: Annotated[tuple[Finite, ...], Field(min_length=3, max_length=10_000)]
    reflectance: Annotated[tuple[Fraction, ...], Field(min_length=3, max_length=10_000)]
    uncertainty: Annotated[tuple[Fraction, ...], Field(min_length=3, max_length=10_000)]

    @model_validator(mode="after")
    def aligned_bands(self) -> Self:
        if len(self.wavelength_nm) != len(self.reflectance) or len(self.reflectance) != len(
            self.uncertainty
        ):
            raise ValueError("unaligned bands")
        if not all(200 <= value <= 25_000 for value in self.wavelength_nm):
            raise ValueError("wavelength out of bounds")
        if any(a >= b for a, b in zip(self.wavelength_nm, self.wavelength_nm[1:], strict=False)):
            raise ValueError("wavelengths must increase strictly")
        return self


PROPERTY_UNITS = {
    "soc": "g/kg",
    "ph": "pH",
    "clay": "g/kg",
    "sand": "g/kg",
    "silt": "g/kg",
    "bd": "kg/dm3",
    "cec": "cmol(+)/kg",
    "n": "g/kg",
}


class LabLabel(StrictRecord):
    property: Literal["soc", "ph", "clay", "sand", "silt", "bd", "cec", "n"]
    unit: Literal["g/kg", "pH", "kg/dm3", "cmol(+)/kg"]
    value: Finite
    uncertainty: Annotated[Finite, Field(ge=0)]
    method_id: UUID
    verifier_id: UUID

    @model_validator(mode="after")
    def canonical_unit(self) -> Self:
        if self.unit != PROPERTY_UNITS[self.property]:
            raise ValueError("noncanonical label unit")
        return self


class LibraryRecord(StrictRecord):
    schema_version: Literal["gsip-library-v1"]
    measurement_id: UUID
    node_id: UUID
    sample_id: UUID
    grant_id: UUID
    protocol_version: Literal["gsip-capture-v1"]
    context: Context
    consent_verified: Annotated[bool, Field(strict=True)]
    pairing_verified: Annotated[bool, Field(strict=True)]
    withdrawn: Annotated[bool, Field(strict=True)]
    synthetic: Annotated[bool, Field(strict=True)]
    holdout: Annotated[bool, Field(strict=True)]
    qa_status: Literal["pending", "pass", "fail", "review"]
    measurement: Annotated[CameraRgb | InstrumentReflectance, Field(discriminator="kind")]
    labels: Annotated[tuple[LabLabel, ...], Field(max_length=32)]

    @property
    def sample_key(self) -> tuple[UUID, UUID]:
        return self.node_id, self.sample_id


def encoded(record: LibraryRecord) -> bytes:
    return json.dumps(
        record.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode()


def private_path(path: Path) -> None:
    # Check ancestors before resolving: resolving first would silently follow symlinks.
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError("symlinked store is not supported")
    if path.exists() and (not path.is_dir() or path.stat().st_mode & 0o077):
        raise ValueError("store must be a private directory")


class PrivateLibrary:
    """Single-host locked, immutable records; private sample tombstones survive deletion."""

    def __init__(self, root: Path):
        self.root = root.absolute()
        private_path(self.root)
        # Require an existing parent: avoid creating intermediate public directories.
        self.root.mkdir(mode=0o700, exist_ok=True)

    @contextmanager
    def locked(self) -> Iterator[None]:
        private_path(self.root)
        fd = os.open(self.root / ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            if os.fstat(fd).st_mode & 0o077 or not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError("store lock is not private")
            fcntl.flock(fd, fcntl.LOCK_EX)
            # Only writers under this lock create .pending-* files. Remove crash remnants
            # before any operation so withdrawal cannot leave incomplete private records.
            leftovers = list(self.root.glob(".pending-*"))
            for leftover in leftovers:
                leftover.unlink()
            if leftovers:
                self._sync()
            yield
        finally:
            os.close(fd)

    def _read(self, path: Path) -> bytes:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if (
                info.st_mode & 0o077
                or info.st_size > MAX_RECORD_BYTES
                or not stat.S_ISREG(info.st_mode)
            ):
                raise ValueError("invalid private record")
            with os.fdopen(fd, "rb", closefd=False) as source:
                return source.read(MAX_RECORD_BYTES + 1)
        finally:
            os.close(fd)

    def _sync(self) -> None:
        fd = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _write(self, path: Path, data: bytes) -> None:
        # A complete temporary file is linked atomically without replacing an existing identity.
        import tempfile

        fd, name = tempfile.mkstemp(dir=self.root, prefix=".pending-")
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.link(temporary, path, follow_symlinks=False)
            self._sync()
        finally:
            temporary.unlink(missing_ok=True)

    def _tombstone(self, node: UUID, sample: UUID) -> Path:
        return self.root / f"withdrawn-{node}-{sample}"

    def _withdrawn(self, node: UUID, sample: UUID) -> bool:
        path = self._tombstone(node, sample)
        return path.exists() or path.is_symlink()

    def _measurement_tombstone(self, measurement: UUID) -> Path:
        return self.root / f"withdrawn-measurement-{measurement}"

    def _measurement_withdrawn(self, measurement: UUID) -> bool:
        path = self._measurement_tombstone(measurement)
        return path.exists() or path.is_symlink()

    def _records(self) -> list[LibraryRecord]:
        result = []
        for path in sorted(self.root.glob("*.json")):
            record = parse_record(self._read(path))
            if path.name != f"{record.measurement_id}.json":
                raise ValueError("record identity mismatch")
            if not self._withdrawn(*record.sample_key) and not self._measurement_withdrawn(
                record.measurement_id
            ):
                result.append(record)
        return result

    def records(self) -> list[LibraryRecord]:
        with self.locked():
            return self._records()

    def add(self, record: LibraryRecord) -> bool:
        # Pydantic copies/construction can bypass validation, including on nested models.
        # Revalidate before serialization, which otherwise warns with private field values.
        record = LibraryRecord.model_validate(record)
        with self.locked():
            if self._withdrawn(*record.sample_key) or record.withdrawn:
                raise ValueError("sample is withdrawn")
            if self._measurement_withdrawn(record.measurement_id):
                raise ValueError("measurement is withdrawn")
            data = encoded(record)
            if len(data) > MAX_RECORD_BYTES:
                raise ValueError("record too large")
            path = self.root / f"{record.measurement_id}.json"
            if path.exists() or path.is_symlink():
                if self._read(path) != data:
                    raise ValueError("measurement identity conflict")
                return False
            for existing in self._records():
                if existing.sample_key == record.sample_key and (
                    existing.context != record.context
                    or existing.grant_id != record.grant_id
                    or existing.protocol_version != record.protocol_version
                ):
                    raise ValueError("sample context conflict")
            self._write(path, data)
            return True

    def withdraw(self, node: UUID, sample: UUID) -> int:
        with self.locked():
            path = self._tombstone(node, sample)
            if not path.exists():
                self._write(path, b"withdrawn\n")
            removed = 0
            # Tombstone first: a crash during deletion cannot readmit the remaining records.
            for item in self.root.glob("*.json"):
                record = parse_record(self._read(item))
                if record.sample_key == (node, sample):
                    # Preserve only the opaque identity before deleting any record bytes.
                    # A crash cannot free a measurement UUID for another sample's data.
                    if not self._measurement_withdrawn(record.measurement_id):
                        self._write(
                            self._measurement_tombstone(record.measurement_id), b"withdrawn\n"
                        )
                    item.unlink()
                    removed += 1
            self._sync()
            return removed


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def parse_record(data: bytes) -> LibraryRecord:
    if len(data) > MAX_RECORD_BYTES:
        raise ValueError("record too large")
    return LibraryRecord.model_validate(json.loads(data, object_pairs_hook=_unique_fields))


def read_record(path: Path) -> LibraryRecord:
    with path.open("rb") as source:
        data = source.read(MAX_RECORD_BYTES + 1)
    if len(data) > MAX_RECORD_BYTES:
        raise ValueError("record too large")
    return parse_record(data)


class PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse's default error includes supplied values, including malformed IDs.
        self.exit(2, "Invalid private command arguments; operation stopped.\n")


def main(argv: list[str] | None = None) -> int:
    parser = PrivateArgumentParser(description="Private offline GSIP library; no upload or export")
    parser.add_argument("--store", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("schema")
    incoming = commands.add_parser("import")
    incoming.add_argument("record", type=Path)
    commands.add_parser("inspect")
    withdraw = commands.add_parser("withdraw")
    withdraw.add_argument("--node", type=UUID, required=True)
    withdraw.add_argument("--sample", type=UUID, required=True)
    args = parser.parse_args(argv)
    if args.command == "schema":
        print(json.dumps(LibraryRecord.model_json_schema(), indent=2, sort_keys=True))
        return 0
    if args.store is None:
        parser.error("--store is required for private operations")
    try:
        library = PrivateLibrary(args.store)
        if args.command == "import":
            print(json.dumps({"imported": int(library.add(read_record(args.record)))}))
        elif args.command == "withdraw":
            print(json.dumps({"removed": library.withdraw(args.node, args.sample)}))
        else:
            records = library.records()
            print(
                json.dumps(
                    {"records": len(records), "synthetic": sum(r.synthetic for r in records)}
                )
            )
    except (ValueError, OSError):
        print("Invalid record or private store; operation stopped.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
