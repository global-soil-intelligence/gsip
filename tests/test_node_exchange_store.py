"""Synthetic private-store adversarial tests; no real records or transport."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import socket
import stat
import sys
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

import pipeline.node_exchange_store as module
from pipeline.node_exchange_store import (
    MAX_BLOB_BYTES,
    MAX_METADATA_BYTES,
    MAX_RETAINED_BYTES,
    BlobWrite,
    PrivateExchangeSession,
    PrivateExchangeStore,
    PrivateExchangeStoreError,
)

_SYNTHETIC = b"fictional synthetic scientific bytes"
_FIRST = str(UUID(int=1))
_SECOND = str(UUID(int=2))
_MESSAGE = "private store unavailable"


@pytest.fixture(autouse=True)
def _no_transport() -> Iterator[None]:
    def denied(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("synthetic store tests permit no network")

    with pytest.MonkeyPatch.context() as guard:
        guard.setattr(socket, "socket", denied)
        guard.setattr(socket, "create_connection", denied)
        yield


@pytest.fixture
def designated(tmp_path: Path) -> tuple[PrivateExchangeStore, Path]:
    allowed = tmp_path.resolve() / "private"
    allowed.mkdir(mode=0o700)
    return PrivateExchangeStore.create_designated(allowed / "simulation", allowed), allowed


def _put(store: PrivateExchangeStore, identity: str = _FIRST, content: bytes = _SYNTHETIC) -> int:
    with store.locked() as session:
        current = session.snapshot()
        updated = session.put_blob(
            {"synthetic_only": True}, BlobWrite(identity, "source", content), current.generation
        )
        return updated.generation


def _fixed(error: pytest.ExceptionInfo[PrivateExchangeStoreError]) -> None:
    assert str(error.value) == _MESSAGE
    assert error.value.__cause__ is None
    assert error.value.__context__ is None


def test_create_open_owned_snapshots_and_exact_idempotent_bytes(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    store, allowed = designated
    metadata: dict[str, Any] = {"synthetic_only": True, "counts": [1, {"pending": 2}]}
    with store.locked() as session:
        initial = session.snapshot()
        updated = session.put_blob(metadata, BlobWrite(_FIRST, "source", _SYNTHETIC), 0)
        metadata["counts"][1]["pending"] = 999
        updated.data["counts"][1]["pending"] = 888
        updated.blobs.clear()
        actual = session.snapshot()
        assert actual.data["counts"][1]["pending"] == 2
        assert actual.blobs[_FIRST].sha256 == hashlib.sha256(_SYNTHETIC).hexdigest()
        assert session.read_blob(_FIRST) == _SYNTHETIC
        repeat = session.put_blob(
            actual.data, BlobWrite(_FIRST, "source", _SYNTHETIC), actual.generation
        )
        assert repeat.generation == actual.generation
        assert initial.generation == 0 and actual.generation == 3
    reopened = PrivateExchangeStore.open_designated(store.root, allowed)
    with reopened.locked() as session:
        assert session.read_blob(_FIRST) == _SYNTHETIC
    assert list((store.root / "staging").iterdir()) == []
    assert set(path.name for path in store.root.iterdir()) == {
        ".lock",
        "state.json",
        "blobs",
        "staging",
    }
    for path in (store.root, store.root / "blobs", store.root / "staging"):
        assert stat.S_IMODE(path.stat().st_mode) == 0o700
    for path in (store.root / ".lock", store.root / "state.json", store.root / "blobs" / _FIRST):
        info = path.stat()
        assert stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1


def test_conflicting_identity_and_stale_generation_fail_before_mutation(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    store, _ = designated
    generation = _put(store)
    original = (store.root / "state.json").read_bytes()
    with store.locked() as session:
        with pytest.raises(PrivateExchangeStoreError) as conflict:
            session.put_blob({}, BlobWrite(_FIRST, "source", _SYNTHETIC + b"!"), generation)
        _fixed(conflict)
        with pytest.raises(PrivateExchangeStoreError) as stale:
            session.commit_metadata({"stale": True}, 0)
        _fixed(stale)
    assert (store.root / "state.json").read_bytes() == original
    assert (store.root / "blobs" / _FIRST).read_bytes() == _SYNTHETIC
    assert not (store.root / "state.next").exists()


@pytest.mark.parametrize(
    "data", [{"x": float("nan")}, {"x": b"private"}, {"x": (1,)}, {"x": "\ud800"}]
)
def test_non_json_metadata_refuses_without_writes(
    designated: tuple[PrivateExchangeStore, Path],
    data: dict[str, Any],
) -> None:
    store, _ = designated
    original = (store.root / "state.json").read_bytes()
    with store.locked() as session, pytest.raises(PrivateExchangeStoreError) as error:
        session.commit_metadata(data, 0)
    _fixed(error)
    assert (store.root / "state.json").read_bytes() == original
    assert not (store.root / "state.next").exists()


def test_existing_missing_corrupt_or_private_state_never_initializes(tmp_path: Path) -> None:
    allowed = tmp_path.resolve() / "private"
    allowed.mkdir(mode=0o700)
    root = allowed / "existing"
    root.mkdir(mode=0o700)
    canary = root / "fictional-private-canary"
    canary.write_bytes(b"fictional canary")
    original = set(root.iterdir())
    for operation in (PrivateExchangeStore.create_designated, PrivateExchangeStore.open_designated):
        with pytest.raises(PrivateExchangeStoreError) as error:
            operation(root, allowed)
        _fixed(error)
    assert set(root.iterdir()) == original and canary.read_bytes() == b"fictional canary"


@pytest.mark.parametrize(
    "which", ["allowed", "ancestor", "root", "blobs", "staging", ".lock", "state.json"]
)
def test_unsafe_permissions_refuse_without_repair(
    designated: tuple[PrivateExchangeStore, Path],
    which: str,
) -> None:
    store, allowed = designated
    target = (
        allowed if which == "allowed" else store.root if which == "root" else store.root / which
    )
    if which == "ancestor":
        target = allowed.parent
    old_mode = stat.S_IMODE(target.stat().st_mode)
    unsafe = 0o777 if which == "ancestor" else 0o755 if target.is_dir() else 0o644
    original = (store.root / "state.json").read_bytes()
    target.chmod(unsafe)
    try:
        with pytest.raises(PrivateExchangeStoreError) as error:
            with store.locked():
                pass
        _fixed(error)
        assert stat.S_IMODE(target.stat().st_mode) == unsafe
        assert (store.root / "state.json").read_bytes() == original
    finally:
        target.chmod(old_mode)


def test_designation_rejects_traversal_outside_root_and_symlinked_ancestors(tmp_path: Path) -> None:
    allowed = tmp_path.resolve() / "private"
    allowed.mkdir(mode=0o700)
    outside = tmp_path.resolve() / "outside"
    outside.mkdir(mode=0o700)
    alias = allowed / "alias"
    alias.symlink_to(outside, target_is_directory=True)
    for path in (outside / "simulation", str(allowed / ".." / "simulation"), alias / "simulation"):
        with pytest.raises(PrivateExchangeStoreError) as error:
            PrivateExchangeStore.create_designated(path, allowed)
        _fixed(error)
    assert not (outside / "simulation").exists()


@pytest.mark.parametrize("target", [".lock", "state.json", "blob"])
@pytest.mark.parametrize("replacement", ["symlink", "hardlink", "fifo", "directory"])
def test_managed_files_reject_links_special_files_and_directories(
    designated: tuple[PrivateExchangeStore, Path],
    target: str,
    replacement: str,
) -> None:
    store, allowed = designated
    _put(store)
    path = store.root / "blobs" / _FIRST if target == "blob" else store.root / target
    saved = allowed / "saved"
    path.rename(saved)
    if replacement == "symlink":
        path.symlink_to(saved)
    elif replacement == "hardlink":
        os.link(saved, path)
    elif replacement == "fifo":
        os.mkfifo(path, 0o600)
    else:
        path.mkdir(mode=0o700)
    with pytest.raises(PrivateExchangeStoreError) as error:
        with store.locked():
            pass
    _fixed(error)
    assert saved.exists() and path.lstat()


@pytest.mark.parametrize("where", ["root", "blobs", "staging"])
def test_unknown_artifact_blocks_absence_and_is_never_swept(
    designated: tuple[PrivateExchangeStore, Path],
    where: str,
) -> None:
    store, _ = designated
    directory = store.root if where == "root" else store.root / where
    orphan = directory / "fictional-private-canary"
    orphan.write_bytes(_SYNTHETIC)
    orphan.chmod(0o600)
    with pytest.raises(PrivateExchangeStoreError) as error:
        with store.locked() as session:
            session.verified_absent([_FIRST])
    _fixed(error)
    assert orphan.read_bytes() == _SYNTHETIC


@pytest.mark.parametrize(
    "change", ["same_length", "append", "truncate", "hardlink", "permission", "inode"]
)
def test_descriptor_read_races_never_commit_substituted_content(
    designated: tuple[PrivateExchangeStore, Path],
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    store, allowed = designated
    generation = _put(store)
    original = (store.root / "state.json").read_bytes()
    path = store.root / "blobs" / _FIRST
    attacked = False

    def attack(point: str) -> None:
        nonlocal attacked
        if point != "file_after_read" or attacked:
            return
        # The trigger occurs while this file's owned descriptor has completed its read.
        if not any(
            path.stat().st_ino == os.fstat(fd).st_ino for fd in range(3, 100) if _fd_open(fd)
        ):
            return
        attacked = True
        if change == "same_length":
            path.write_bytes(b"X" * len(_SYNTHETIC))
        elif change == "append":
            with path.open("ab") as output:
                output.write(b"X")
        elif change == "truncate":
            path.write_bytes(b"")
        elif change == "hardlink":
            os.link(path, allowed / "extra-link")
        elif change == "permission":
            path.chmod(0o644)
        else:
            path.rename(allowed / "moved")
            path.write_bytes(_SYNTHETIC)
            path.chmod(0o600)

    with store.locked() as session:
        monkeypatch.setattr(module, "_fault", attack)
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.commit_metadata({"may_not_commit": True}, generation)
        _fixed(error)
    assert attacked and (store.root / "state.json").read_bytes() == original


def _fd_open(fd: int) -> bool:
    try:
        os.fstat(fd)
        return True
    except OSError:
        return False


@pytest.mark.parametrize("target", ["root", "lock", "allowed", "blobs"])
def test_open_session_rechecks_inode_guards_before_mutation(
    designated: tuple[PrivateExchangeStore, Path],
    target: str,
) -> None:
    store, allowed = designated
    original = (store.root / "state.json").read_bytes()
    with store.locked() as session:
        if target == "root":
            moved = allowed / "moved"
            store.root.rename(moved)
            store.root.mkdir(mode=0o700)
        elif target == "allowed":
            moved = allowed.parent / "moved"
            allowed.rename(moved)
            allowed.mkdir(mode=0o700)
        elif target == "blobs":
            moved = store.root / "moved-blobs"
            (store.root / "blobs").rename(moved)
            (store.root / "blobs").mkdir(mode=0o700)
        else:
            moved = allowed / "moved-lock"
            (store.root / ".lock").rename(moved)
            (store.root / ".lock").write_bytes(b"")
            (store.root / ".lock").chmod(0o600)
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.commit_metadata({"cannot_commit": True}, 0)
        _fixed(error)
    if target == "root":
        assert (moved / "state.json").read_bytes() == original
    elif target == "allowed":
        assert (moved / "simulation" / "state.json").read_bytes() == original
    else:
        assert (store.root / "state.json").read_bytes() == original


def test_raced_symlink_is_never_opened_as_a_payload_descriptor(
    designated: tuple[PrivateExchangeStore, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, allowed = designated
    _put(store)
    path = store.root / "blobs" / _FIRST
    opened_link: list[str] = []
    real_open = os.open
    attacked = False

    def observed_open(name: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        result = real_open(name, flags, *args, **kwargs)
        if name == _FIRST and path.is_symlink():
            opened_link.append("followed private link")
        return result

    def attack(point: str) -> None:
        nonlocal attacked
        if (
            point == "file_before_open"
            and not attacked
            and sys._getframe(1).f_locals.get("name") == _FIRST
        ):
            # Interrupt specifically between this payload's lstat and descriptor open.
            attacked = True
            moved = allowed / "owned-synthetic"
            path.rename(moved)
            path.symlink_to(moved)

    with store.locked() as session:
        monkeypatch.setattr(os, "open", observed_open)
        monkeypatch.setattr(module, "_fault", attack)
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.read_blob(_FIRST)
        _fixed(error)
    assert attacked and opened_link == []


def test_same_inode_changes_at_metadata_and_blob_promote_barriers_refuse(
    designated: tuple[PrivateExchangeStore, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _ = designated
    original = (store.root / "state.json").read_bytes()

    def change_image(point: str) -> None:
        if point == "metadata_before_promote":
            next_path = store.root / "state.next"
            image = json.loads(next_path.read_bytes())
            image["data"] = {"fictional_changed": True}
            next_path.write_bytes(module._encode(image))

    with store.locked() as session:
        monkeypatch.setattr(module, "_fault", change_image)
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.commit_metadata({"fictional_expected": True}, 0)
        _fixed(error)
    assert (store.root / "state.json").read_bytes() == original
    monkeypatch.undo()
    with store.locked() as session:
        assert session.snapshot().data == {}

    def change_blob(point: str) -> None:
        if point == "put_before_publish":
            stages = list((store.root / "staging").iterdir())
            assert len(stages) == 1
            stages[0].write_bytes(b"X" * len(_SYNTHETIC))

    with store.locked() as session:
        monkeypatch.setattr(module, "_fault", change_blob)
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.put_blob({}, BlobWrite(_FIRST, "source", _SYNTHETIC), 0)
        _fixed(error)
    assert list((store.root / "blobs").iterdir()) == []


def test_transactions_never_accumulate_third_image_or_second_staged_blob(
    designated: tuple[PrivateExchangeStore, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _ = designated
    counts: list[tuple[int, int]] = []

    def observe(point: str) -> None:
        images = sum(
            path.exists() for path in (store.root / "state.json", store.root / "state.next")
        )
        staged = len(list((store.root / "staging").iterdir()))
        counts.append((images, staged))
        assert images <= 2 and staged <= 1

    monkeypatch.setattr(module, "_fault", observe)
    _put(store)
    _put(store, _SECOND)
    assert max(images for images, _ in counts) == 2
    assert max(staged for _, staged in counts) == 1
    monkeypatch.undo()

    def interrupted(point: str) -> None:
        if point == "put_after_reservation":
            raise OSError("fictional interrupted reservation")

    with store.locked() as session:
        current = session.snapshot()
        monkeypatch.setattr(module, "_fault", interrupted)
        with pytest.raises(PrivateExchangeStoreError):
            session.put_blob({}, BlobWrite(str(UUID(int=3)), "source", b"S"), current.generation)
        monkeypatch.undo()
        with pytest.raises(PrivateExchangeStoreError) as stale:
            session.put_blob({}, BlobWrite(str(UUID(int=4)), "source", b"S"), current.generation)
        _fixed(stale)
        assert set(session.snapshot().blobs) == {_FIRST, _SECOND}
    assert list((store.root / "staging").iterdir()) == []


def test_no_replace_publication_preserves_single_link_and_refuses_collision(
    designated: tuple[PrivateExchangeStore, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _ = designated
    observed: list[int] = []

    def observe(point: str) -> None:
        if point in {"put_before_publish", "put_after_publish", "put_after_commit"}:
            paths = list((store.root / "staging").iterdir()) + list(
                (store.root / "blobs").iterdir()
            )
            assert len(paths) == 1
            observed.append(paths[0].stat().st_nlink)

    monkeypatch.setattr(module, "_fault", observe)
    _put(store)
    assert observed == [1, 1, 1]
    monkeypatch.setattr(module, "_fault", lambda point: None)

    def collision(point: str) -> None:
        if point == "put_before_publish":
            path = store.root / "blobs" / _SECOND
            path.write_bytes(b"fictional conflicting target")
            path.chmod(0o600)

    monkeypatch.setattr(module, "_fault", collision)
    with store.locked() as session:
        current = session.snapshot()
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.put_blob({}, BlobWrite(_SECOND, "recipient", _SYNTHETIC), current.generation)
        _fixed(error)
    assert (store.root / "blobs" / _SECOND).read_bytes() == b"fictional conflicting target"
    assert len(list((store.root / "staging").iterdir())) == 1


def test_unavailable_atomic_primitive_holds_reservation_without_payload_overwrite(
    designated: tuple[PrivateExchangeStore, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _ = designated
    monkeypatch.setattr(sys, "platform", "unsupported-synthetic-platform")
    with store.locked() as session:
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.put_blob({}, BlobWrite(_FIRST, "source", _SYNTHETIC), 0)
        _fixed(error)
    assert list((store.root / "blobs").iterdir()) == []
    assert len(list((store.root / "staging").iterdir())) == 1
    monkeypatch.undo()
    with store.locked() as session:
        assert session.snapshot().blobs == {}
    assert list((store.root / "staging").iterdir()) == []


def test_inclusive_blob_bound_and_cap_plus_one_fail_before_reservation(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    store, _ = designated
    generation = _put(store, content=b"S" * MAX_BLOB_BYTES)
    original = (store.root / "state.json").read_bytes()
    with store.locked() as session:
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.put_blob(
                {}, BlobWrite(_SECOND, "draft", b"S" * (MAX_BLOB_BYTES + 1)), generation
            )
        _fixed(error)
    assert (store.root / "state.json").read_bytes() == original
    assert list((store.root / "staging").iterdir()) == []


def test_actual_retained_byte_cap_is_aggregate_until_verified_absence(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    store, _ = designated
    image = json.loads((store.root / "state.json").read_bytes())
    content = b"S" * MAX_BLOB_BYTES
    count = MAX_RETAINED_BYTES // MAX_BLOB_BYTES
    for number in range(count):
        identity = str(UUID(int=number + 100))
        path = store.root / "blobs" / identity
        path.write_bytes(content)
        path.chmod(0o600)
        image["blobs"][identity] = {
            "blob_id": identity,
            "category": "source" if number % 2 else "recipient",
            "byte_count": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    (store.root / "state.json").write_bytes(module._encode(image))
    before = (store.root / "state.json").read_bytes()
    with store.locked() as session:
        assert (
            sum(ref.byte_count for ref in session.snapshot().blobs.values()) == MAX_RETAINED_BYTES
        )
        # Queue/dequeue metadata has no power to release physically retained capacity.
        current = session.commit_metadata({"queued_bytes": 0}, 0)
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.put_blob(
                current.data, BlobWrite(_FIRST, "preparation", b"S"), current.generation
            )
        _fixed(error)
        assert not session.verified_absent([str(UUID(int=100))])
        erased = session.erase_blobs({"refusal": True}, [str(UUID(int=100))], current.generation)
        assert session.verified_absent([str(UUID(int=100))])
        added = session.put_blob(
            erased.data, BlobWrite(_FIRST, "draft", content), erased.generation
        )
        assert sum(ref.byte_count for ref in added.blobs.values()) == MAX_RETAINED_BYTES
    assert before != (store.root / "state.json").read_bytes()


def test_forged_byte_count_cannot_grant_capacity(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    store, _ = designated
    _put(store)
    image = json.loads((store.root / "state.json").read_bytes())
    image["blobs"][_FIRST]["byte_count"] = 0
    (store.root / "state.json").write_bytes(module._encode(image))
    before = (store.root / "state.json").read_bytes()
    with pytest.raises(PrivateExchangeStoreError) as error:
        with store.locked():
            pass
    _fixed(error)
    assert (store.root / "state.json").read_bytes() == before


def test_real_encoded_metadata_inclusive_bound_and_replacement_bound(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    store, _ = designated
    image = json.loads((store.root / "state.json").read_bytes())
    image["generation"] = 1
    image["data"] = {"synthetic_padding": ""}
    overhead = len(module._encode(image))
    padding = "S" * (MAX_METADATA_BYTES - overhead)
    with store.locked() as session:
        updated = session.commit_metadata({"synthetic_padding": padding}, 0)
        assert (store.root / "state.json").stat().st_size == MAX_METADATA_BYTES
        before = (store.root / "state.json").read_bytes()
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.commit_metadata({"synthetic_padding": padding + "S"}, updated.generation)
        _fixed(error)
        assert (store.root / "state.json").read_bytes() == before
        # The pending rollback+prospective image is bounded too; no second blob stages.
        with pytest.raises(PrivateExchangeStoreError) as reservation:
            session.put_blob(updated.data, BlobWrite(_FIRST, "source", b"S"), updated.generation)
        _fixed(reservation)
    assert list((store.root / "staging").iterdir()) == []
    assert list((store.root / "blobs").iterdir()) == []
    assert not (store.root / "state.next").exists()


def _crash_put(root: str, allowed: str, point: str, occurrence: int = 1) -> None:
    store = PrivateExchangeStore.open_designated(root, allowed)
    seen = 0
    target_point = point

    def fail(point: str) -> None:
        nonlocal seen
        if point == target_point:
            seen += 1
            if seen == occurrence:
                os._exit(84)

    module._fault = fail
    with store.locked() as session:
        session.put_blob({"accepted": True}, BlobWrite(_FIRST, "source", b"S" * MAX_BLOB_BYTES), 0)


@pytest.mark.parametrize(
    ("point", "occurrence", "held", "committed"),
    [
        ("put_before_reservation", 1, False, False),
        ("put_after_reservation", 1, False, False),
        ("put_after_empty_stage", 1, True, False),
        ("put_before_payload_write", 1, False, False),
        ("put_payload_chunk", 1, False, False),
        ("put_after_payload_write", 1, False, False),
        ("put_after_payload_fsync", 1, False, False),
        ("put_before_publish", 1, False, False),
        ("put_after_publish", 1, False, False),
        ("put_after_publish_fsync", 1, False, False),
        ("put_before_commit", 1, False, False),
        ("put_after_commit", 1, False, True),
        ("metadata_before_write", 1, True, False),
        ("metadata_after_write", 1, False, False),
        ("metadata_after_fsync", 1, False, False),
        ("metadata_before_promote", 1, False, False),
        ("metadata_after_promote", 1, False, False),
        ("metadata_after_directory_fsync", 1, False, False),
        ("metadata_after_fsync", 2, True, False),
        ("metadata_before_write", 3, True, False),
        ("metadata_after_write", 3, False, False),
        ("metadata_before_promote", 3, False, False),
        ("metadata_after_promote", 3, False, True),
    ],
)
def test_real_process_crash_put_matrix_reopens_twice_without_invented_admission(
    designated: tuple[PrivateExchangeStore, Path],
    point: str,
    occurrence: int,
    held: bool,
    committed: bool,
) -> None:
    store, allowed = designated
    process = multiprocessing.get_context("fork").Process(
        target=_crash_put, args=(str(store.root), str(allowed), point, occurrence)
    )
    process.start()
    process.join(15)
    if process.is_alive():
        process.terminate()
        process.join(5)
    assert process.exitcode == 84
    before = (store.root / "state.json").read_bytes()
    for _ in range(2):
        if held:
            with pytest.raises(PrivateExchangeStoreError) as error:
                PrivateExchangeStore.open_designated(store.root, allowed)
            _fixed(error)
            assert (store.root / "state.json").read_bytes() == before
        else:
            reopened = PrivateExchangeStore.open_designated(store.root, allowed)
            with reopened.locked() as session:
                current = session.snapshot()
                assert bool(current.blobs) is committed
                assert current.data == ({"accepted": True} if committed else {})
                assert session.verified_absent([_FIRST]) is not committed
                if committed:
                    assert session.read_blob(_FIRST) == b"S" * MAX_BLOB_BYTES
            assert list((store.root / "staging").iterdir()) == []
            assert not (store.root / "state.next").exists()


def _crash_erase(root: str, allowed: str, point: str, occurrence: int) -> None:
    store = PrivateExchangeStore.open_designated(root, allowed)
    seen = 0
    target_point = point

    def fail(point: str) -> None:
        nonlocal seen
        if point == target_point:
            seen += 1
            if seen == occurrence:
                os._exit(85)

    module._fault = fail
    with store.locked() as session:
        current = session.snapshot()
        session.erase_blobs(
            {"permanent_refusal": True, "pending_erasure": True},
            [_FIRST, _SECOND],
            current.generation,
        )


@pytest.mark.parametrize(
    ("point", "occurrence"),
    [
        ("erase_after_restrictions", 1),
        ("erase_before_unlink", 1),
        ("erase_after_unlink", 1),
        ("erase_after_directory_fsync", 1),
        ("erase_before_unlink", 2),
        ("erase_after_unlink", 2),
        ("metadata_after_write", 2),
        ("metadata_after_promote", 2),
    ],
)
def test_real_process_erasure_crash_preserves_refusal_and_completes_exact_absence(
    designated: tuple[PrivateExchangeStore, Path],
    point: str,
    occurrence: int,
) -> None:
    store, allowed = designated
    _put(store)
    _put(store, _SECOND)
    process = multiprocessing.get_context("fork").Process(
        target=_crash_erase, args=(str(store.root), str(allowed), point, occurrence)
    )
    process.start()
    process.join(15)
    if process.is_alive():
        process.terminate()
        process.join(5)
    assert process.exitcode == 85
    last_generation = -1
    for _ in range(2):
        reopened = PrivateExchangeStore.open_designated(store.root, allowed)
        with reopened.locked() as session:
            current = session.snapshot()
            assert current.data == {"permanent_refusal": True, "pending_erasure": True}
            assert current.blobs == {} and session.verified_absent([_FIRST, _SECOND])
            assert last_generation in (-1, current.generation)
            last_generation = current.generation
    assert list((store.root / "blobs").iterdir()) == []


def test_unlink_failure_cannot_release_bytes_or_clear_durable_restrictions(
    designated: tuple[PrivateExchangeStore, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _ = designated
    generation = _put(store)
    real_unlink = os.unlink

    def fail(path: Any, *args: Any, **kwargs: Any) -> None:
        if path == _FIRST:
            raise OSError("fictional private failure canary")
        real_unlink(path, *args, **kwargs)

    with store.locked() as session:
        monkeypatch.setattr(os, "unlink", fail)
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.erase_blobs({"permanent_refusal": True}, [_FIRST], generation)
        _fixed(error)
    image = json.loads((store.root / "state.json").read_bytes())
    assert image["data"] == {"permanent_refusal": True} and image["pending"]["kind"] == "erase"
    assert image["blobs"][_FIRST]["byte_count"] == len(_SYNTHETIC)
    assert (store.root / "blobs" / _FIRST).read_bytes() == _SYNTHETIC
    monkeypatch.undo()
    with store.locked() as session:
        assert session.verified_absent([_FIRST])
        assert session.snapshot().data == {"permanent_refusal": True}


def _conditional_writer(
    root: str, allowed: str, identity: str, expected: int, connection: Any
) -> None:
    try:
        store = PrivateExchangeStore.open_designated(root, allowed)
        with store.locked() as session:
            session.put_blob({"synthetic": True}, BlobWrite(identity, "source", b"S"), expected)
        connection.send("committed")
    except PrivateExchangeStoreError:
        connection.send("refused")
    finally:
        connection.close()


def test_two_processes_serialize_last_reservation_and_fence_stale_writer(
    designated: tuple[PrivateExchangeStore, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, allowed = designated
    # A reduced isolated byte budget tests the same aggregate reservation path.
    monkeypatch.setattr(module, "MAX_RETAINED_BYTES", 1)
    context = multiprocessing.get_context("fork")
    readers: list[Any] = []
    processes: list[Any] = []
    for identity in (_FIRST, _SECOND):
        reader, writer = context.Pipe(duplex=False)
        process = context.Process(
            target=_conditional_writer, args=(str(store.root), str(allowed), identity, 0, writer)
        )
        readers.append(reader)
        processes.append(process)
        process.start()
        writer.close()
    outcomes = []
    for reader, process in zip(readers, processes, strict=True):
        assert reader.poll(15)
        outcomes.append(reader.recv())
        process.join(15)
        assert process.exitcode == 0
        reader.close()
    assert sorted(outcomes) == ["committed", "refused"]
    with store.locked() as session:
        assert len(session.snapshot().blobs) == 1


def _blocked_reader(
    root: str, allowed: str, inherited_session: PrivateExchangeSession, connection: Any
) -> None:
    # A fork inherits the parent's lock descriptor. Close only the child's copy
    # so its new descriptor genuinely competes with the still-held parent lock.
    inherited_session._close()
    try:
        connection.send("started")
        store = PrivateExchangeStore.open_designated(root, allowed)
        with store.locked() as session:
            connection.send(session.snapshot().generation)
    finally:
        connection.close()


def test_second_process_cannot_enter_until_the_root_lock_is_released(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    store, allowed = designated
    context = multiprocessing.get_context("fork")
    reader, writer = context.Pipe(duplex=False)
    process = None
    try:
        with store.locked() as session:
            process = context.Process(
                target=_blocked_reader, args=(str(store.root), str(allowed), session, writer)
            )
            process.start()
            writer.close()
            assert reader.poll(15) and reader.recv() == "started"
            assert not reader.poll(0.25)
            session.commit_metadata({"synthetic_lock_order": True}, 0)
        assert reader.poll(15) and reader.recv() == 1
        process.join(15)
        assert process.exitcode == 0
    finally:
        if process is not None and process.is_alive():
            process.terminate()
            process.join(5)
        reader.close()


def test_errors_and_failed_recovery_emit_no_private_output(
    designated: tuple[PrivateExchangeStore, Path],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _ = designated

    def private_failure(point: str) -> None:
        if point == "metadata_before_create":
            raise RuntimeError("fictional-private-canary-92738")

    with store.locked() as session:
        monkeypatch.setattr(module, "_fault", private_failure)
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.commit_metadata({"opaque": "fictional-private-canary-92738"}, 0)
        _fixed(error)
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_partial_corrupt_replacement_holds_without_removing_or_readmitting(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    store, allowed = designated
    next_path = store.root / "state.next"
    next_path.write_bytes(b'{"fictional_partial":')
    next_path.chmod(0o600)
    original = (store.root / "state.json").read_bytes()
    for _ in range(2):
        with pytest.raises(PrivateExchangeStoreError) as error:
            PrivateExchangeStore.open_designated(store.root, allowed)
        _fixed(error)
    assert next_path.read_bytes() == b'{"fictional_partial":'
    assert (store.root / "state.json").read_bytes() == original


def test_validated_replacement_cannot_be_substituted_before_recovery_deletion(
    designated: tuple[PrivateExchangeStore, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _ = designated
    next_path = store.root / "state.next"
    original = (store.root / "state.json").read_bytes()

    def interrupt(point: str) -> None:
        if point == "metadata_before_promote":
            raise OSError("fictional interruption")

    with store.locked() as session:
        monkeypatch.setattr(module, "_fault", interrupt)
        with pytest.raises(PrivateExchangeStoreError):
            session.commit_metadata({"fictional": True}, 0)
        monkeypatch.undo()
        unlink = session._unlink

        def substituted(
            directory_fd: int, name: str, bound: int, *args: Any, **kwargs: Any
        ) -> None:
            if name == "state.next":
                # Same inode, already validated by recovery, now unrelated bytes.
                next_path.write_bytes(b"fictional-unvalidated-private-canary")
            unlink(directory_fd, name, bound, *args, **kwargs)

        monkeypatch.setattr(session, "_unlink", substituted)
        with pytest.raises(PrivateExchangeStoreError) as error:
            session.snapshot()
        _fixed(error)
    assert next_path.read_bytes() == b"fictional-unvalidated-private-canary"
    assert (store.root / "state.json").read_bytes() == original


def test_session_use_after_release_refuses_generically(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    store, _ = designated
    with store.locked() as session:
        pass
    with pytest.raises(PrivateExchangeStoreError) as error:
        session.snapshot()
    _fixed(error)


def test_designated_store_pins_lock_and_ancestor_inodes_across_sessions(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    store, allowed = designated
    lock = store.root / ".lock"
    lock.rename(allowed / "old-lock")
    lock.write_bytes(b"")
    lock.chmod(0o600)
    with pytest.raises(PrivateExchangeStoreError) as error:
        with store.locked():
            pass
    _fixed(error)
    # A fresh explicit designation binds the existing valid root/lock. It then
    # detects ancestor replacement even if the exact root inode was moved back.
    store = PrivateExchangeStore.open_designated(store.root, allowed)
    moved_allowed = allowed.parent / "old-allowed"
    allowed.rename(moved_allowed)
    allowed.mkdir(mode=0o700)
    (moved_allowed / "simulation").rename(store.root)
    with pytest.raises(PrivateExchangeStoreError) as ancestor:
        with store.locked():
            pass
    _fixed(ancestor)


def test_root_creation_detects_parent_substitution_before_any_metadata_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    allowed = tmp_path.resolve() / "private"
    allowed.mkdir(mode=0o700)
    root = allowed / "simulation"
    moved_allowed = allowed.parent / "moved-private"
    real_mkdir = os.mkdir

    def substitute(path: Any, *args: Any, **kwargs: Any) -> None:
        real_mkdir(path, *args, **kwargs)
        if path == "simulation":
            allowed.rename(moved_allowed)
            real_mkdir(allowed, mode=0o700)

    monkeypatch.setattr(os, "mkdir", substitute)
    with pytest.raises(PrivateExchangeStoreError) as error:
        PrivateExchangeStore.create_designated(root, allowed)
    _fixed(error)
    assert not (moved_allowed / "simulation" / "state.json").exists()
    assert not (root / "state.json").exists()


@pytest.mark.parametrize("method", ["read", "snapshot", "absence"])
@pytest.mark.parametrize(
    "race", ["root_mode", "allowed_mode", "root_name", "lock", "blobs", "staging"]
)
def test_last_audit_read_rechecks_every_pinned_guard_before_return(
    designated: tuple[PrivateExchangeStore, Path],
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    race: str,
) -> None:
    store, allowed = designated
    _put(store)
    changed = False
    calls = 0
    target_call = 3 if method == "absence" else 2
    moved = allowed / "moved-root"
    original = (store.root / "state.json").read_bytes()

    def attack(point: str) -> None:
        nonlocal changed, calls
        if point != "file_after_read":
            return
        calls += 1
        if calls != target_call:
            return
        changed = True
        if race == "root_mode":
            store.root.chmod(0o755)
        elif race == "allowed_mode":
            allowed.chmod(0o755)
        elif race == "root_name":
            store.root.rename(moved)
            store.root.mkdir(mode=0o700)
        elif race == "lock":
            (store.root / ".lock").chmod(0o644)
        else:
            (store.root / race).chmod(0o755)

    with store.locked() as session:
        monkeypatch.setattr(module, "_fault", attack)
        try:
            with pytest.raises(PrivateExchangeStoreError) as error:
                if method == "read":
                    session.read_blob(_FIRST)
                elif method == "snapshot":
                    session.snapshot()
                else:
                    session.verified_absent([_SECOND])
            _fixed(error)
        finally:
            if changed:
                if race == "root_mode":
                    store.root.chmod(0o700)
                elif race == "allowed_mode":
                    allowed.chmod(0o700)
                elif race == "root_name":
                    store.root.rmdir()
                    moved.rename(store.root)
                elif race == "lock":
                    (store.root / ".lock").chmod(0o600)
                else:
                    (store.root / race).chmod(0o700)
    assert changed and (store.root / "state.json").read_bytes() == original


def _foreign_operations(session: PrivateExchangeSession, generation: int) -> list[bool]:
    operations: list[Callable[[], object]] = [
        session.snapshot,
        lambda: session.read_blob(_FIRST),
        lambda: session.verified_absent([str(UUID(int=3))]),
        lambda: session.commit_metadata({"foreign": True}, generation),
        lambda: session.put_blob({}, BlobWrite(str(UUID(int=3)), "draft", b"S"), generation),
        lambda: session.erase_blobs({"foreign": True}, [_FIRST], generation),
    ]
    results = []
    for operation in operations:
        try:
            operation()
        except PrivateExchangeStoreError as error:
            results.append(
                str(error) == _MESSAGE and error.__cause__ is None and error.__context__ is None
            )
        else:
            results.append(False)
    return results


def test_foreign_thread_cannot_recover_or_mutate_owner_threads_active_put(
    designated: tuple[PrivateExchangeStore, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _ = designated
    _put(store)
    reached, released = threading.Event(), threading.Event()
    results: list[bool] = []
    unchanged: list[bool] = []
    with store.locked() as session:
        before = session.snapshot()

        def foreign() -> None:
            if not reached.wait(5):
                released.set()
                return
            image = (store.root / "state.json").read_bytes()
            stages = list((store.root / "staging").iterdir())
            results.extend(_foreign_operations(session, before.generation))
            unchanged.append(
                image == (store.root / "state.json").read_bytes()
                and stages == list((store.root / "staging").iterdir())
            )
            released.set()

        def pause(point: str) -> None:
            if point == "put_before_payload_write":
                reached.set()
                assert released.wait(5)

        worker = threading.Thread(target=foreign)
        worker.start()
        monkeypatch.setattr(module, "_fault", pause)
        try:
            updated = session.put_blob(
                {"synthetic_only": True, "accepted": 2},
                BlobWrite(_SECOND, "source", b"fictional second bytes"),
                before.generation,
            )
        finally:
            released.set()
            worker.join(5)
        assert not worker.is_alive()
        assert results == [True] * 6 and unchanged == [True]
        assert set(updated.blobs) == {_FIRST, _SECOND}
        assert session.read_blob(_SECOND) == b"fictional second bytes"


def _inherited_session_probe(
    session: PrivateExchangeSession, generation: int, connection: Any
) -> None:
    try:
        connection.send(_foreign_operations(session, generation))
    finally:
        # Only this child's inherited descriptor copies close; no store access is authorized.
        session._close()
        connection.close()


def test_fork_inherited_session_cannot_read_recover_or_write_without_its_own_lock(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    store, _ = designated
    _put(store)
    context = multiprocessing.get_context("fork")
    reader, writer = context.Pipe(duplex=False)
    process = None
    try:
        with store.locked() as session:
            before = session.snapshot()
            image = (store.root / "state.json").read_bytes()
            process = context.Process(
                target=_inherited_session_probe, args=(session, before.generation, writer)
            )
            process.start()
            writer.close()
            assert reader.poll(10) and reader.recv() == [True] * 6
            process.join(10)
            assert process.exitcode == 0
            assert (store.root / "state.json").read_bytes() == image
            assert session.snapshot() == before
            updated = session.commit_metadata({"creator_continues": True}, before.generation)
            assert updated.generation == before.generation + 1
    finally:
        if process is not None and process.is_alive():
            process.terminate()
            process.join(5)
        reader.close()


def test_foreign_thread_context_exit_cannot_close_owner_or_release_its_lock(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    import fcntl
    import threading

    store, _ = designated
    _put(store)
    manager = store.locked()
    session = manager.__enter__()
    outcomes: list[str] = []

    def foreign() -> None:
        try:
            manager.__exit__(None, None, None)
            outcomes.append("accepted")
        except PrivateExchangeStoreError as error:
            assert str(error) == _MESSAGE and error.__cause__ is None and error.__context__ is None
            outcomes.append("refused")

    try:
        worker = threading.Thread(target=foreign)
        worker.start()
        worker.join(10)
        assert not worker.is_alive() and outcomes == ["refused"]
        assert session.read_blob(_FIRST) == _SYNTHETIC
        contender = os.open(store.root / ".lock", os.O_RDONLY | os.O_NOFOLLOW)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(contender)
    finally:
        manager.__exit__(None, None, None)
    # The refused exit did not consume the owner's eventual generator cleanup.
    with store.locked() as fresh:
        assert fresh.read_blob(_FIRST) == _SYNTHETIC


def test_foreign_thread_cannot_enter_an_owners_unadvanced_context(
    designated: tuple[PrivateExchangeStore, Path],
) -> None:
    import threading

    store, _ = designated
    manager = store.locked()
    outcomes: list[str] = []

    def foreign() -> None:
        try:
            manager.__enter__()
            outcomes.append("accepted")
        except PrivateExchangeStoreError:
            outcomes.append("refused")

    worker = threading.Thread(target=foreign)
    worker.start()
    worker.join(10)
    assert not worker.is_alive() and outcomes == ["refused"]
    with manager as session:
        assert session.snapshot().generation == 0
