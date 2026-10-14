"""APP-2C1 verifies source evidence; no test certifies a native storage backend."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
SUBJECT = ROOT / "scripts/ios_storage_feasibility.py"


def loaded() -> ModuleType:
    assert SUBJECT.is_file(), "The offline source-audit contract must exist before migration"
    spec = importlib.util.spec_from_file_location("ios_storage_audit_subject", SUBJECT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def seeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, Path, Path]:
    module = loaded()
    public = tmp_path / "public"
    repository = tmp_path / "repository"
    public.mkdir()
    repository.mkdir()
    for binding in module.REPOSITORY_SOURCES:
        target = repository / binding.path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / binding.path, target)
    data = b"// synthetic public source fixture\n"
    (public / "synthetic.source").write_bytes(data)
    binding = module.SourceBinding("synthetic.source", len(data), hashlib.sha256(data).hexdigest())
    monkeypatch.setattr(module, "PUBLIC_SOURCES", (binding,))
    return module, public, repository


def checked(module: ModuleType, public: Path, repository: Path) -> dict[str, object]:
    return cast(dict[str, object], module.audit(public, repository))


def assert_blocked(report: dict[str, object]) -> None:
    assert report["status"] == "blocked"
    assert report["source_review_valid"] is True
    for key in ("storage_feasible", "backend_selected", "device_verified", "migration_implemented"):
        assert report[key] is False
    assert report["resolution_scope"] == "observed-generated-not-a-lock"
    assert report["next_gate"] == "app2c2-held"


def test_known_source_review_can_never_be_storage_or_device_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    first = checked(module, public, repository)
    assert_blocked(first)
    assert checked(module, public, repository) == first


@pytest.mark.parametrize("case", ["missing", "changed", "truncated", "appended", "comment_api"])
def test_actual_bytes_are_recomputed_and_source_comments_cannot_add_capabilities(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    file = public / "synthetic.source"
    data = file.read_bytes()
    if case == "missing":
        file.unlink()
    elif case == "changed":
        file.write_bytes(b"X" + data[1:])
    elif case == "truncated":
        file.write_bytes(data[:-1])
    elif case == "appended":
        file.write_bytes(data + b"x")
    else:
        file.write_bytes(b"// atomic=true; readback=true; excluded=true\n")
    with pytest.raises(module.AuditError):
        checked(module, public, repository)


@pytest.mark.parametrize("extra", ["claims.json", "backend_selected=true", "private-sentinel"])
def test_no_caller_manifest_or_unknown_file_is_accepted(
    extra: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    (public / extra).write_text('{"device_verified":true,"storage_feasible":true}')
    with pytest.raises(module.AuditError):
        checked(module, public, repository)


@pytest.mark.parametrize(
    "surface", ["public_root", "public_leaf", "repo_intermediate", "repo_leaf"]
)
def test_symlinks_are_refused_at_input_and_nested_source_boundaries(
    surface: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    if surface == "public_root":
        alias = tmp_path / "alias"
        alias.symlink_to(public, target_is_directory=True)
        public = alias
    elif surface == "public_leaf":
        file = public / "synthetic.source"
        target = tmp_path / "other"
        file.rename(target)
        file.symlink_to(target)
    elif surface == "repo_intermediate":
        target = tmp_path / "other-apps"
        (repository / "apps").rename(target)
        (repository / "apps").symlink_to(target, target_is_directory=True)
    else:
        file = repository / module.REPOSITORY_SOURCES[0].path
        target = tmp_path / "other-repo-file"
        file.rename(target)
        file.symlink_to(target)
    with pytest.raises(module.AuditError):
        checked(module, public, repository)


@pytest.mark.parametrize("kind", ["directory", "fifo", "hardlink"])
def test_only_bounded_regular_single_link_sources_are_read(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    file = public / "synthetic.source"
    if kind == "hardlink":
        os.link(file, tmp_path / "alias")
    else:
        file.unlink()
        if kind == "directory":
            file.mkdir()
        else:
            os.mkfifo(file)
    with pytest.raises(module.AuditError):
        checked(module, public, repository)


def test_same_length_repository_drift_requires_a_new_source_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    file = repository / "apps/capture-pwa/src/supabase.ts"
    data = file.read_bytes()
    file.write_bytes(b"X" + data[1:])
    with pytest.raises(module.AuditError):
        checked(module, public, repository)


def test_a_new_queue_store_cannot_silently_reuse_the_old_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    name = "apps/capture-pwa/src/queue.ts"
    file = repository / name
    data = file.read_bytes() + b"\ndb.createObjectStore('syntheticNewStore')\n"
    file.write_bytes(data)
    # Simulate a reviewed source-profile refresh that forgot the inventory. Hash agreement alone
    # must not make an incomplete persistence inventory valid.
    bindings = tuple(
        module.SourceBinding(name, len(data), hashlib.sha256(data).hexdigest())
        if item.path == name
        else item
        for item in module.REPOSITORY_SOURCES
    )
    monkeypatch.setattr(module, "REPOSITORY_SOURCES", bindings)
    with pytest.raises(module.AuditError):
        checked(module, public, repository)


@pytest.mark.parametrize("change", ["missing", "duplicate", "invented"])
def test_missing_or_invented_residual_inventory_is_refused(
    change: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    original = module.INVENTORY_SURFACES
    if change == "missing":
        modified = original[:-1]
    elif change == "duplicate":
        modified = (*original, original[0])
    else:
        modified = (*original, "invented_supabase_disk_mutex")
    monkeypatch.setattr(module, "INVENTORY_SURFACES", modified)
    with pytest.raises(module.AuditError):
        checked(module, public, repository)


def test_source_changed_during_read_is_not_validated_from_its_old_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    file = public / "synthetic.source"
    before = file.stat()
    read = os.read
    changed = False

    def racing_read(fd: int, size: int) -> bytes:
        nonlocal changed
        result = read(fd, size)
        if not changed and os.fstat(fd).st_ino == before.st_ino and result:
            changed = True
            data = file.read_bytes()
            file.write_bytes(b"X" + data[1:])
            os.utime(file, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
        return result

    monkeypatch.setattr(module.os, "read", racing_read)
    with pytest.raises(module.AuditError):
        checked(module, public, repository)
    assert changed


def test_verification_performs_no_network_process_or_filesystem_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    real_open = os.open

    def read_only_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        assert not flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND | os.O_WRONLY | os.O_RDWR)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("The source audit must not perform external actions or writes")

    with monkeypatch.context() as patch:
        patch.setattr(module.os, "open", read_only_open)
        patch.setattr(module.os, "supports_dir_fd", {*os.supports_dir_fd, read_only_open})
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        for name in ("mkdir", "unlink", "rename", "replace"):
            patch.setattr(module.os, name, forbidden)
        assert_blocked(checked(module, public, repository))


@pytest.mark.parametrize(
    "args", [[], ["private-sentinel", "--device-verified"], ["private-sentinel"]]
)
def test_cli_failure_never_echoes_paths_claims_or_exception_details(
    args: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    module = loaded()
    assert module.main(args) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert len(captured.out) < 1500
    assert "private-sentinel" not in captured.out
    assert "Traceback" not in captured.out
    report = json.loads(captured.out)
    assert report["status"] == "evidence_unverified"
    assert report["source_review_valid"] is False
    assert report["storage_feasible"] is False
    assert report["backend_selected"] is False


def test_verified_source_cli_exits_blocked_instead_of_readiness_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module, public, _ = seeded(tmp_path, monkeypatch)
    assert module.main([str(public)]) == 3
    captured = capsys.readouterr()
    assert captured.err == ""
    assert str(public) not in captured.out
    assert_blocked(json.loads(captured.out))


@pytest.mark.parametrize(
    "case", ["empty", "duplicate", "oversize", "boolean_size", "digest", "escape", "aggregate"]
)
def test_even_a_future_profile_edit_cannot_bypass_source_bounds(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    binding = module.PUBLIC_SOURCES[0]
    bindings: tuple[object, ...]
    if case == "empty":
        bindings = ()
    elif case == "duplicate":
        bindings = (binding, binding)
    elif case == "oversize":
        bindings = (
            module.SourceBinding(binding.path, module.MAX_SOURCE_BYTES + 1, binding.sha256),
        )
    elif case == "boolean_size":
        bindings = (module.SourceBinding(binding.path, True, binding.sha256),)
    elif case == "digest":
        bindings = (module.SourceBinding(binding.path, binding.size, "unknown-private-sentinel"),)
    elif case == "escape":
        bindings = (module.SourceBinding("../private-sentinel", binding.size, binding.sha256),)
    else:
        monkeypatch.setattr(module, "MAX_TOTAL_BYTES", 1)
        bindings = (binding,)
    monkeypatch.setattr(module, "PUBLIC_SOURCES", bindings)
    with pytest.raises(module.AuditError):
        checked(module, public, repository)


def test_unsupported_no_follow_platform_is_held_without_a_weaker_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, public, repository = seeded(tmp_path, monkeypatch)
    monkeypatch.setattr(module.os, "supports_dir_fd", set())
    with pytest.raises(module.AuditError):
        checked(module, public, repository)


def test_portable_catalog_and_observed_snapshot_match_the_reviewed_profile() -> None:
    module = loaded()
    catalog = json.loads((ROOT / "docs/ios-storage-feasibility-sources.json").read_text())
    expected = {item.path: (item.size, item.sha256) for item in module.PUBLIC_SOURCES}
    actual = {item["file"]: (item["bytes"], item["sha256"]) for item in catalog["sources"]}
    assert len(catalog["sources"]) == len(expected) == 19
    assert actual == expected
    assert catalog["backend_selected"] is False and catalog["device_verified"] is False
    assert catalog["resolution_scope"] == "observed-generated-not-a-lock"
    observed = (ROOT / "docs/ios-storage-observed-resolution.json").read_bytes()
    assert (len(observed), hashlib.sha256(observed).hexdigest()) == expected[
        "observed-native-resolution.source"
    ]
    record = next(
        item for item in catalog["sources"] if item["file"] == "observed-native-resolution.source"
    )
    assert record["origin"]["repository_native_lock"] is False


def test_displayed_source_table_agrees_with_the_actual_copy_input_profile() -> None:
    module = loaded()
    document = (ROOT / "docs/IOS_STORAGE_FEASIBILITY.md").read_text()
    rows = {
        parts[0].strip("`"): (int(parts[1]), parts[2].strip("`"))
        for line in document.splitlines()
        if line.startswith("|")
        and len(parts := [field.strip() for field in line.strip("|").split("|")]) == 3
        and parts[0].endswith(".source`")
    }
    assert rows == {item.path: (item.size, item.sha256) for item in module.PUBLIC_SOURCES}


def test_documented_repository_evidence_ranges_point_to_real_lines() -> None:
    import re

    document = ROOT / "docs/IOS_STORAGE_FEASIBILITY.md"
    assert document.is_file()
    references = re.findall(r"source:([^`:\s]+):(\d+)-(\d+)", document.read_text())
    assert len(references) >= 3
    for relative, first, last in references:
        target = ROOT / relative
        assert target.is_file()
        assert 1 <= int(first) <= int(last) <= len(target.read_text().splitlines())
