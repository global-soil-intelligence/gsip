"""APP-2B evidence refuses incomplete native graphs, licenses and comparisons."""

from __future__ import annotations

import copy
import gzip
import json
import os
import platform
import tarfile
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest

from scripts import app_build
from scripts import app_notification_audit as audit

COORD = ("org.example", "example-runtime", "1.2.3")
ROOT = Path(__file__).parents[1]


def pom(
    coord: tuple[str, str, str] = COORD,
    license_name: str | None = "Apache License, Version 2.0",
    parent: tuple[str, str, str] | None = None,
) -> bytes:
    licenses = (
        ""
        if license_name is None
        else (
            f"<licenses><license><name>{license_name}</name>"
            "<url>https://www.apache.org/licenses/LICENSE-2.0</url></license></licenses>"
        )
    )
    inherited = (
        ""
        if parent is None
        else (
            f"<parent><groupId>{parent[0]}</groupId><artifactId>{parent[1]}</artifactId>"
            f"<version>{parent[2]}</version></parent>"
        )
    )
    return (
        f"<project>{inherited}<groupId>{coord[0]}</groupId>"
        f"<artifactId>{coord[1]}</artifactId><version>{coord[2]}</version>"
        f"{licenses}</project>"
    ).encode()


def cached(cache: Path, coord: tuple[str, str, str], data: bytes) -> Path:
    path = (
        cache
        / "modules-2/files-2.1"
        / coord[0]
        / coord[1]
        / coord[2]
        / "synthetic-hash"
        / f"{coord[1]}-{coord[2]}.pom"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def zipped(
    path: Path, payload: bytes = b"synthetic class bytes", activation: bool | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("classes.dex", payload)
        archive.writestr("META-INF/LICENSE", b"Synthetic Apache-2.0 notice")
        if activation is not None:
            archive.writestr(
                "assets/public/gsip-activation.json",
                json.dumps({"capture_live": activation, "library_intake_live": False}),
            )


@pytest.fixture
def graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, Any], Path, Path, Path]:
    repo, cache = tmp_path / "repo", tmp_path / "cache"
    repo.mkdir()
    cached(cache, COORD, pom())
    artifact = (
        cache / "modules-2/files-2.1" / COORD[0] / COORD[1] / COORD[2] / "binary-hash/runtime.jar"
    )
    zipped(artifact)
    view = {
        "name": "debugRuntimeClasspath",
        "modules": [list(COORD)],
        "projects": [":app"],
        "artifacts": [{"kind": "module", "coordinate": list(COORD), "file": str(artifact)}],
    }
    release = copy.deepcopy(view)
    release["name"] = "releaseRuntimeClasspath"
    monkeypatch.setattr(audit, "npm_evidence", lambda repo, names: [])
    monkeypatch.setattr(
        audit,
        "public_bytes",
        lambda *args, **kwargs: pytest.fail("fixture audit must never fetch a network resource"),
    )
    return {"views": [view, release]}, repo, cache, artifact


def test_exact_graph_retains_both_selected_license_and_binary_evidence(
    graph: tuple[dict[str, Any], Path, Path, Path],
) -> None:
    data, repo, cache, artifact = graph
    result = audit.runtime_evidence(data, repo, cache, False)
    assert {view["configuration"] for view in result["runtime_views"]} == {
        "debugRuntimeClasspath",
        "releaseRuntimeClasspath",
    }
    runtime = result["runtime_views"][0]
    assert (
        runtime["selected_modules"][0]["pom_license_evidence"][0]["licenses"][0]["spdx"]
        == "Apache-2.0"
    )
    assert runtime["resolved_runtime_inputs"][0]["sha256"] == audit.sha(artifact.read_bytes())
    assert runtime["resolved_runtime_inputs"][0]["bytes"] == artifact.stat().st_size
    assert (
        runtime["resolved_runtime_inputs"][0]["embedded_license_notice_files"][0]["entry"]
        == "META-INF/LICENSE"
    )


@pytest.mark.parametrize(
    "defect",
    [
        "missing_release",
        "duplicate_view",
        "empty_modules",
        "unresolved_module",
        "outside_cache",
        "closed_sdk",
        "unknown_project",
        "unknown_binary",
    ],
)
def test_graph_refuses_missing_or_unreviewed_runtime(
    graph: tuple[dict[str, Any], Path, Path, Path], defect: str, tmp_path: Path
) -> None:
    data, repo, cache, artifact = graph
    if defect == "missing_release":
        data["views"].pop()
    elif defect == "duplicate_view":
        data["views"][1]["name"] = "debugRuntimeClasspath"
    elif defect == "empty_modules":
        data["views"][0]["modules"] = []
    elif defect == "unresolved_module":
        data["views"][0]["artifacts"][0]["coordinate"][2] = "99.0"
    elif defect == "outside_cache":
        outside = tmp_path / "other.jar"
        zipped(outside)
        data["views"][0]["artifacts"][0]["file"] = str(outside)
    elif defect == "closed_sdk":
        closed = ("com.google.android.gms", "play-services-location", "1.0")
        cached(cache, closed, pom(closed))
        closed_file = (
            cache
            / "modules-2/files-2.1"
            / closed[0]
            / closed[1]
            / closed[2]
            / "binary-hash/closed.jar"
        )
        zipped(closed_file)
        data["views"][0]["modules"] = [list(closed)]
        data["views"][0]["artifacts"] = [
            {"kind": "module", "coordinate": list(closed), "file": str(closed_file)}
        ]
    elif defect == "unknown_project":
        data["views"][0]["projects"].append(":unreviewed-proprietary-wrapper")
    elif defect == "unknown_binary":
        renamed = artifact.with_suffix(".so")
        artifact.rename(renamed)
        data["views"][0]["artifacts"][0]["file"] = str(renamed)
    with pytest.raises(audit.AuditError):
        audit.runtime_evidence(data, repo, cache, False)


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "ambiguous",
        "wrong_coordinate",
        "no_license",
        "closed_license",
        "entity",
        "parent_cycle",
    ],
)
def test_pom_license_evidence_refuses_unknown_or_ambiguous(
    graph: tuple[dict[str, Any], Path, Path, Path], defect: str
) -> None:
    _, _, cache, _ = graph
    path = cached(cache, COORD, pom())
    if defect == "missing":
        path.unlink()
    elif defect == "ambiguous":
        alternate = path.parent.parent / "other-hash" / path.name
        alternate.parent.mkdir()
        alternate.write_bytes(path.read_bytes())
    elif defect == "wrong_coordinate":
        path.write_bytes(pom((COORD[0], COORD[1], "9.9.9")))
    elif defect == "no_license":
        path.write_bytes(pom(license_name=None))
    elif defect == "closed_license":
        path.write_bytes(pom(license_name="Proprietary commercial runtime"))
    elif defect == "entity":
        path.write_bytes(
            b'<!DOCTYPE project [<!ENTITY x SYSTEM "file:///private/synthetic-test">]>' + pom()
        )
    elif defect == "parent_cycle":
        path.write_bytes(pom(license_name=None, parent=COORD))
    with pytest.raises(audit.AuditError):
        audit.pom_evidence(COORD, cache, False)


def test_explicit_parent_inheritance_is_retained_not_inferred(tmp_path: Path) -> None:
    parent = ("org.example", "example-parent", "1.2.3")
    cached(tmp_path, COORD, pom(license_name=None, parent=parent))
    cached(tmp_path, parent, pom(parent))
    result = audit.pom_evidence(COORD, tmp_path, False)
    assert result[0]["inherits_license_from"] == list(parent)
    assert result[1]["coordinate"] == list(parent)
    assert result[1]["licenses"][0]["spdx"] == "Apache-2.0"


@pytest.mark.parametrize(
    "defect", ["symlink", "ancestor_symlink", "hardlink", "oversized", "outside", "directory"]
)
def test_file_reads_are_explicit_bounded_regular_single_link(tmp_path: Path, defect: str) -> None:
    root = tmp_path / "allowed"
    root.mkdir()
    file = root / "evidence"
    file.write_bytes(b"synthetic metadata")
    target = file
    if defect == "symlink":
        target = root / "link"
        target.symlink_to(file)
    elif defect == "ancestor_symlink":
        directory = root / "real"
        directory.mkdir()
        (directory / "evidence").write_bytes(b"synthetic metadata")
        (root / "alias").symlink_to(directory, target_is_directory=True)
        target = root / "alias/evidence"
    elif defect == "hardlink":
        os.link(file, root / "copy")
    elif defect == "oversized":
        file.write_bytes(b"x" * 100)
    elif defect == "outside":
        target = tmp_path / "outside"
        target.write_bytes(b"synthetic metadata")
    elif defect == "directory":
        target = root
    with pytest.raises((audit.AuditError, OSError)):
        audit.read(target, (root,), 32)


@pytest.mark.parametrize("defect", ["duplicate", "traversal", "symlink", "huge_entry"])
def test_zip_refuses_ambiguous_paths_and_unbounded_unpacking(
    tmp_path: Path, defect: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    file = tmp_path / "runtime.jar"
    with zipfile.ZipFile(file, "w") as archive:
        if defect == "duplicate":
            with pytest.warns(UserWarning):
                archive.writestr("LICENSE", b"one")
                archive.writestr("LICENSE", b"two")
        elif defect == "traversal":
            archive.writestr("../LICENSE", b"synthetic")
        elif defect == "symlink":
            info = zipfile.ZipInfo("LICENSE")
            info.external_attr = 0o120777 << 16
            archive.writestr(info, b"../private-synthetic")
        else:
            archive.writestr("LICENSE", b"too long")
            monkeypatch.setattr(audit, "MAX_ZIP_BYTES", 3)
    with pytest.raises(audit.AuditError):
        audit.zip_evidence(file, (tmp_path,))


def test_raw_metadata_rejects_duplicate_json_and_oversize() -> None:
    with pytest.raises(audit.AuditError):
        audit.decoded(b'{"views":[],"views":[]}')
    with pytest.raises(audit.AuditError):
        audit.decoded(b" " * (audit.MAX_META + 1))


FIXTURE_LOCK_BYTES = b"synthetic locked build input\n"
FIXTURE_LOCK_SHA = audit.sha(FIXTURE_LOCK_BYTES)


def toolchain_fixture(target: str) -> dict[str, Any]:
    import sys

    tools: dict[str, Any] = {
        "node": "v24.11.0",
        "pnpm": "11.9.0",
        "python": sys.version,
        "runner": "Linux-6.11.0-1018-azure-x86_64-with-glibc2.39"
        if target == "android"
        else "macOS-26.0-arm64-arm-64bit",
        "runner_image": {
            "ImageOS": "ubuntu24" if target == "android" else "macos26",
            "ImageVersion": "20261013.2.0",
            "RUNNER_OS": "Linux" if target == "android" else "macOS",
            "RUNNER_ARCH": "X64" if target == "android" else "ARM64",
        },
    }
    if target == "ios":
        tools.update({"xcode": "Xcode 26.0\nBuild version 17A324", "sdk": "26.0"})
    else:
        tools.update(
            {
                "aapt2": "Android Asset Packaging Tool (aapt) 2.19.2-13409019",
                "java": (
                    'openjdk version "21.0.8" 2025-07-15 LTS\n'
                    "OpenJDK Runtime Environment Temurin-21.0.8+9 (build 21.0.8+9-LTS)\n"
                    "OpenJDK 64-Bit Server VM Temurin-21.0.8+9 "
                    "(build 21.0.8+9-LTS, mixed mode, sharing)"
                ),
                "gradle": "\n".join(
                    [
                        "-" * 60,
                        "Gradle 8.14.3",
                        "-" * 60,
                        "Build time: 2025-07-04 13:23:44 UTC",
                        "Revision: " + "a" * 40,
                        "Kotlin: 2.0.21",
                        "Groovy: 3.0.24",
                        "Ant: Apache Ant(TM) version 1.10.15 compiled on August 25 2024",
                        "Launcher JVM: 21.0.8 (Eclipse Adoptium 21.0.8+9-LTS)",
                        "Daemon JVM: /opt/hostedtoolcache/Java_Temurin_jdk/21.0.8/x64 "
                        "(no JDK specified, using current Java home)",
                        "OS: Linux 6.11.0-1018-azure amd64",
                    ]
                ),
            }
        )
    return tools


def genuine_build_receipt(
    artifact: Path,
    source_commit: str,
    target: str = "android",
    reference: Path | None = None,
    resolved_bytes: bytes = FIXTURE_LOCK_BYTES,
) -> dict[str, Any]:
    """Use the actual producer on synthetic ZIPs, with fixed native/tool/environment inputs."""
    import tempfile
    from unittest.mock import patch

    reference = artifact if reference is None else reference
    tools = toolchain_fixture(target)
    with tempfile.TemporaryDirectory(prefix="gsip-build-receipt-control-") as temporary:
        root = Path(temporary)
        for name in (
            "pnpm-lock.yaml",
            "uv.lock",
            "apps/capture-pwa/android/gradle/wrapper/gradle-wrapper.properties",
            "apps/capture-pwa/android/build.gradle",
            "apps/capture-pwa/android/variables.gradle",
        ):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(FIXTURE_LOCK_BYTES)
        package = root / "apps/capture-pwa/package.json"
        package.write_text(json.dumps({"version": "0.1.0"}))
        if target == "ios":
            resolved = (
                root
                / "apps/capture-pwa/ios/App/App.xcodeproj/project.xcworkspace"
                / "xcshareddata/swiftpm/Package.resolved"
            )
            resolved.parent.mkdir(parents=True)
            resolved.write_bytes(resolved_bytes)
            for identity, relative in audit.UPSTREAM_RESOLVED.items():
                nested = (
                    root
                    / f"apps/capture-pwa/ios/App/build/SourcePackages/checkouts/{identity}"
                    / relative
                )
                nested.parent.mkdir(parents=True)
                nested.write_text(json.dumps({"pins": [audit.SWIFTLINT_PIN], "version": 2}))

        def command(args: list[str]) -> str:
            if args[0] == "git":
                return source_commit
            if args[0] in {"node", "pnpm", "java", "xcodebuild"}:
                return cast(
                    str, tools[{"java": "java", "xcodebuild": "xcode"}.get(args[0], args[0])]
                )
            if args[0] == "xcrun":
                return cast(str, tools["sdk"])
            if args[0] == "synthetic-aapt2":
                return cast(str, tools["aapt2"])
            if args[0].endswith("gradlew"):
                return cast(str, tools["gradle"])
            pytest.fail("unexpected tool invocation in synthetic producer control")

        with (
            patch.object(app_build, "__file__", str(root / "scripts/app_build.py")),
            patch.object(app_build, "command", side_effect=command),
            patch.object(app_build, "source_clean", return_value=True),
            patch.object(platform, "platform", return_value=tools["runner"]),
            patch.dict(os.environ, tools["runner_image"]),
        ):
            return app_build.receipt(
                artifact,
                reference,
                app_build.versions("123", package),
                target,
                "synthetic-aapt2" if target == "android" else None,
            )


def complete_native(
    source_commit: str, artifact_sha256: str, *, project_artifact_outside: bool = False
) -> dict[str, Any]:
    """Positive comparison control uses actual bounded collector output on synthetic inputs."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="gsip-native-sidecar-fixture-") as temporary:
        root = Path(temporary).resolve()
        repo, cache = root / "repo", root / "cache"
        names = tuple(
            name
            for name in audit.NPM_PACKAGES
            if source_commit != audit.BASELINE or name != "@capacitor/local-notifications"
        )
        versions = {
            "@capacitor/core": "8.5.2",
            "@capacitor/android": "8.5.2",
            "@capacitor/ios": "8.5.2",
            "@capacitor/camera": "8.2.4",
            "@capacitor/filesystem": "8.1.3",
            "@capacitor/geolocation": "8.2.2",
            "@capacitor/local-notifications": "8.3.1",
        }
        for name in names:
            package = repo / "node_modules/.pnpm/synthetic/node_modules" / name
            package.mkdir(parents=True)
            (package / "package.json").write_text(
                json.dumps({"name": name, "version": versions[name], "license": "MIT"})
            )
            (package / "LICENSE").write_text("MIT synthetic fixture: Permission is hereby granted.")
            installed = repo / "apps/capture-pwa/node_modules" / name
            installed.parent.mkdir(parents=True, exist_ok=True)
            installed.symlink_to(package, target_is_directory=True)
        cached(cache, COORD, pom())
        module = (
            cache / "modules-2/files-2.1" / COORD[0] / COORD[1] / COORD[2] / "binary/runtime.jar"
        )
        zipped(module)
        projects = []
        artifacts = [{"kind": "module", "coordinate": list(COORD), "file": str(module)}]
        for project, name in audit.PROJECT_PACKAGES.items():
            if name not in names:
                continue
            projects.append(project)
            package = (repo / "apps/capture-pwa/node_modules" / name).resolve()
            directory = (
                package / ("capacitor" if project == ":capacitor-android" else "android") / "build"
            )
            file = directory / (project[1:] + ".aar")
            if project_artifact_outside and project == ":capacitor-android":
                file = repo / "unmatched/renamed-capacitor.aar"
            zipped(file)
            artifacts.append({"kind": "project", "project": project, "file": str(file)})
        view = {
            "name": "debugRuntimeClasspath",
            "modules": [list(COORD)],
            "projects": [":app", *projects],
            "artifacts": artifacts,
        }
        release = {**copy.deepcopy(view), "name": "releaseRuntimeClasspath"}
        result = audit.runtime_evidence({"views": [view, release]}, repo, cache, False)
        inputs = {
            name: FIXTURE_LOCK_SHA
            for name in (
                "pnpm-lock.yaml",
                "apps/capture-pwa/package.json",
                "apps/capture-pwa/capacitor.config.ts",
                "scripts/app_permissions.py",
                "scripts/app_build.py",
                "apps/capture-pwa/android/gradle/wrapper/gradle-wrapper.properties",
                "apps/capture-pwa/android/build.gradle",
                "apps/capture-pwa/android/variables.gradle",
            )
        }
        result.update(
            {
                "schema_version": "gsip-app-notification-native-audit-v1",
                "platform": "android",
                "source_commit": source_commit,
                "source_inputs": inputs,
                "built_artifact_sha256": artifact_sha256,
                "resolved_graph_sha256": "c" * 64,
                "build_only_environment_sha256": "d" * 64,
                "runtime_tree_sha256": {
                    name: "e" * 64 for name in ("debugRuntimeClasspath", "releaseRuntimeClasspath")
                },
                "debug_signing_key_sha256": "b" * 64,
            }
        )
        return result


def receipts(
    parent: Path, candidate: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    value = genuine_build_receipt(parent, audit.BASELINE)
    second = genuine_build_receipt(candidate, "a" * 40)
    native = complete_native(audit.BASELINE, value["artifact_sha256"])
    return value, second, native


def test_feature_delta_uses_actual_parent_and_candidate_bytes(tmp_path: Path) -> None:
    parent, candidate = tmp_path / "parent.apk", tmp_path / "candidate.apk"
    zipped(parent, b"parent", False)
    zipped(candidate, b"larger feature candidate", False)
    left, right, native = receipts(parent, candidate)
    result = audit.feature_comparison(
        parent,
        candidate,
        left,
        right,
        "a" * 40,
        {**native, "source_commit": audit.BASELINE},
        complete_native("a" * 40, right["artifact_sha256"]),
    )
    assert result["archive_byte_delta"] == candidate.stat().st_size - parent.stat().st_size
    assert result["zip_comparison"]["changed_entries"] == ["classes.dex"]
    assert "no dependency-only attribution" in result["scope"]
    assert result["closed_flags"] == {"capture_live": False, "library_intake_live": False}


@pytest.mark.parametrize(
    "defect",
    [
        "wrong_parent",
        "wrong_candidate",
        "toolchain",
        "run_number",
        "unclean",
        "wrong_bytes",
        "debug_key",
        "open_activation",
        "missing_activation",
    ],
)
def test_feature_delta_refuses_unmatched_build_inputs(tmp_path: Path, defect: str) -> None:
    parent, candidate = tmp_path / "parent.apk", tmp_path / "candidate.apk"
    zipped(parent, b"parent", False)
    zipped(candidate, b"candidate", False)
    left, right, native = receipts(parent, candidate)
    native["source_commit"] = audit.BASELINE
    other_native = complete_native("a" * 40, right["artifact_sha256"])
    if defect == "wrong_parent":
        left["source_commit"] = "c" * 40
    elif defect == "wrong_candidate":
        right["source_commit"] = "c" * 40
    elif defect == "toolchain":
        right["toolchain"] = {"node": "v25"}
    elif defect == "run_number":
        right["run_number"] = 124
    elif defect == "unclean":
        left["source_tree_clean"] = False
    elif defect == "wrong_bytes":
        right["artifact_sha256"] = "d" * 64
    elif defect == "debug_key":
        other_native["debug_signing_key_sha256"] = "c" * 64
    elif defect == "open_activation":
        zipped(candidate, b"candidate", True)
        right["artifact_sha256"] = audit.sha(candidate.read_bytes())
        other_native["built_artifact_sha256"] = right["artifact_sha256"]
        right["reference_sha256"] = right["artifact_sha256"]
        right["comparison"] = app_build.comparison(candidate, candidate)
    elif defect == "missing_activation":
        zipped(candidate)
        right["artifact_sha256"] = audit.sha(candidate.read_bytes())
        other_native["built_artifact_sha256"] = right["artifact_sha256"]
        right["reference_sha256"] = right["artifact_sha256"]
        right["comparison"] = app_build.comparison(candidate, candidate)
    with pytest.raises((audit.AuditError, ValueError)):
        audit.feature_comparison(parent, candidate, left, right, "a" * 40, native, other_native)


def test_cli_error_never_copies_private_error_text(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    def failure(*args: Any) -> None:
        raise ValueError("synthetic private-sentinel-not-for-output")

    monkeypatch.setattr(audit, "collect_ios", failure)
    assert (
        audit.main(
            [
                "ios",
                str(tmp_path),
                str(tmp_path / "receipt.json"),
                str(tmp_path / "fixture-ios.zip"),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "private-sentinel" not in captured.err
    assert captured.out == ""


def test_workflow_retains_old_gates_and_uploads_owned_evidence() -> None:
    text = (ROOT / ".github/workflows/app-build.yml").read_text()
    for value in (
        "--configuration debugRuntimeClasspath",
        "--configuration releaseRuntimeClasspath",
        "check-dependencies -",
        "check-apk",
        "check-ios",
        "assembleDebug --rerun-tasks --no-build-cache",
        "CODE_SIGNING_ALLOWED=NO clean build",
        "VITE_CAPTURE_LIVE: 'false'",
        "VITE_LIBRARY_INTAKE_LIVE: 'false'",
        "scripts/app_notification_audit.py",
        "tests/test_app_notification_audit.py",
        "scripts.app_notification_audit android",
        "scripts.app_notification_audit ios",
        "scripts.app_notification_audit compare",
        audit.BASELINE,
        "gsip-android-feature-comparison.json",
        "gsip-ios-feature-comparison.json",
    ):
        assert value in text


@pytest.fixture
def ios_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, dict[str, bytes]]:
    import io

    repo = tmp_path / "ios-repo"
    ios = repo / "apps/capture-pwa/ios"
    package = repo / "node_modules/@capacitor/ios"
    package.mkdir(parents=True)
    installed = repo / "apps/capture-pwa/node_modules/@capacitor"
    installed.mkdir(parents=True)
    (installed / "ios").symlink_to(package, target_is_directory=True)
    license_data = b"MIT License\nPermission is hereby granted, synthetic upstream evidence."
    (package / "LICENSE").write_bytes(license_data)
    versions = {
        "@capacitor/core": "8.5.2",
        "@capacitor/android": "8.5.2",
        "@capacitor/ios": "8.5.2",
        "@capacitor/camera": "8.2.4",
        "@capacitor/filesystem": "8.1.3",
        "@capacitor/geolocation": "8.2.2",
        "@capacitor/local-notifications": "8.3.1",
    }
    for name in audit.NPM_PACKAGES:
        directory = repo / "node_modules" / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "package.json").write_text(
            json.dumps({"name": name, "version": versions[name], "license": "MIT"})
        )
        (directory / "LICENSE").write_bytes(license_data)
        if name != "@capacitor/ios":
            (repo / "apps/capture-pwa/node_modules" / name).symlink_to(
                directory, target_is_directory=True
            )
    header = package / "CapacitorCordova/CapacitorCordova/Classes/Public/CDV.h"
    header.parent.mkdir(parents=True)
    header.write_bytes(b"Synthetic source header: Apache License, Version 2.0")
    resolved = ios / "App/App.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
    resolved.parent.mkdir(parents=True)
    resolved.write_text(
        json.dumps(
            {
                "pins": [
                    {
                        "identity": "capacitor-swift-pm",
                        "location": "https://github.com/ionic-team/capacitor-swift-pm.git",
                        "state": {"version": "8.5.2", "revision": "1" * 40},
                    }
                ]
            }
        )
    )
    expected = copy.deepcopy(audit.ION_PACKAGES)
    for identity, entry in expected.items():
        checkout = ios / f"App/build/SourcePackages/checkouts/{identity}"
        checkout.mkdir(parents=True)
        manifest_data = f"// synthetic source-only fixture {identity}\n".encode()
        (checkout / "Package.swift").write_bytes(manifest_data)
        (checkout / "LICENSE").write_bytes(license_data)
        if identity in audit.UPSTREAM_RESOLVED:
            nested = checkout / audit.UPSTREAM_RESOLVED[identity]
            nested.parent.mkdir(parents=True)
            nested.write_text(json.dumps({"pins": [audit.SWIFTLINT_PIN], "version": 2}))
        source_files: list[dict[str, Any]] = []
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as source_archive:
            for file in sorted(checkout.rglob("*")):
                if not file.is_file():
                    continue
                payload = file.read_bytes()
                name = str(file.relative_to(checkout))
                member = tarfile.TarInfo(f"{identity}-{entry['version']}/{name}")
                member.size = len(payload)
                source_archive.addfile(member, io.BytesIO(payload))
                source_files.append(
                    {"path": name, "bytes": len(payload), "sha256": audit.sha(payload)}
                )
        raw_archive = stream.getvalue()
        entry.update(
            {
                "manifest_sha256": audit.sha(manifest_data),
                "license_sha256": audit.sha(license_data),
                "archive_sha256": audit.sha(raw_archive),
                "source_tree_sha256": audit.sha(
                    json.dumps(source_files, sort_keys=True, separators=(",", ":")).encode()
                ),
                "source_bytes": sum(row["bytes"] for row in source_files),
                "source_file_count": len(source_files),
                "archive_bytes": len(raw_archive),
            }
        )
        entry["fixture_archive"] = raw_archive
    monkeypatch.setattr(audit, "ION_PACKAGES", expected)
    resolved_value = json.loads(resolved.read_text())
    resolved_value["pins"] += [
        {
            "identity": identity,
            "location": f"https://github.com/ionic-team/{identity}.git",
            "kind": "remoteSourceControl",
            "state": {"version": entry["version"], "revision": entry["revision"]},
        }
        for identity, entry in expected.items()
    ]
    resolved.write_text(json.dumps(resolved_value))
    public = {
        "https://raw.githubusercontent.com/ionic-team/capacitor-swift-pm/8.5.2/README.md": (
            b"Synthetic binary xcframework releases of Capacitor and CapacitorCordova"
        ),
        "https://raw.githubusercontent.com/ionic-team/capacitor/8.5.2/LICENSE": license_data,
    }
    for identity, entry in expected.items():
        public[
            f"https://codeload.github.com/ionic-team/{identity}/tar.gz/refs/tags/{entry['version']}"
        ] = entry.pop("fixture_archive")
    manifest = ""
    for name in ("Capacitor", "Cordova"):
        folder = (
            ios / f"App/build/SourcePackages/artifacts/capacitor-swift-pm/{name}/{name}.xcframework"
        )
        folder.mkdir(parents=True)
        (folder / "Info.plist").write_bytes(f"synthetic-{name}".encode())
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr(f"{name}.xcframework/Info.plist", f"synthetic-{name}".encode())
        raw = stream.getvalue()
        url = f"https://github.com/ionic-team/capacitor-swift-pm/releases/download/8.5.2/{name}.xcframework.zip"
        public[url] = raw
        manifest += f'.binaryTarget(name: "{name}", url: "{url}", checksum: "{audit.sha(raw)}")\n'
    checkout = ios / "App/build/SourcePackages/checkouts/capacitor-swift-pm"
    checkout.mkdir(parents=True)
    (checkout / "Package.swift").write_text(manifest)
    capacitor = copy.deepcopy(audit.CAPACITOR_RELEASE)
    readme_url = "https://raw.githubusercontent.com/ionic-team/capacitor-swift-pm/8.5.2/README.md"
    (checkout / "README.md").write_bytes(public[readme_url])
    source_files = []
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as source_archive:
        for file in sorted(checkout.rglob("*")):
            if not file.is_file():
                continue
            payload = file.read_bytes()
            name = str(file.relative_to(checkout))
            member = tarfile.TarInfo("capacitor-swift-pm-8.5.2/" + name)
            member.size = len(payload)
            source_archive.addfile(member, io.BytesIO(payload))
            source_files.append({"path": name, "sha256": audit.sha(payload), "bytes": len(payload)})
    raw_archive = stream.getvalue()
    public["https://codeload.github.com/ionic-team/capacitor-swift-pm/tar.gz/refs/tags/8.5.2"] = (
        raw_archive
    )
    capacitor.update(
        {
            "revision": "1" * 40,
            "manifest_sha256": audit.sha(manifest.encode()),
            "readme_sha256": audit.sha(public[readme_url]),
            "license_sha256": audit.sha(license_data),
            "cordova_header_sha256": audit.sha(header.read_bytes()),
            "source_archive_sha256": audit.sha(raw_archive),
            "source_archive_bytes": len(raw_archive),
            "source_tree": {
                "bytes": sum(file["bytes"] for file in source_files),
                "file_count": len(source_files),
                "tree_sha256": audit.sha(
                    json.dumps(source_files, sort_keys=True, separators=(",", ":")).encode()
                ),
            },
        }
    )
    for name in ("Capacitor", "Cordova"):
        url = f"https://github.com/ionic-team/capacitor-swift-pm/releases/download/8.5.2/{name}.xcframework.zip"
        payload = f"synthetic-{name}".encode()
        tree_files = [{"path": "Info.plist", "sha256": audit.sha(payload), "bytes": len(payload)}]
        capacitor["binaries"][name] = {
            "sha256": audit.sha(public[url]),
            "archive_bytes": len(public[url]),
            "bytes": len(payload),
            "file_count": 1,
            "tree_sha256": audit.sha(
                json.dumps(tree_files, sort_keys=True, separators=(",", ":")).encode()
            ),
        }
    monkeypatch.setattr(audit, "CAPACITOR_RELEASE", capacitor)
    monkeypatch.setattr(audit, "public_bytes", lambda url, *args, **kwargs: public[url])
    monkeypatch.setattr(
        audit,
        "source_inputs",
        lambda *args: {
            name: FIXTURE_LOCK_SHA
            for name in (
                "pnpm-lock.yaml",
                "apps/capture-pwa/package.json",
                "apps/capture-pwa/capacitor.config.ts",
                "scripts/app_permissions.py",
                "scripts/app_build.py",
            )
        },
    )

    def readback(args: list[str], *unused: Any) -> str:
        for identity, entry in expected.items():
            if identity in " ".join(args):
                return cast(str, entry["revision"])
        return "1" * 40 if "capacitor-swift-pm" in " ".join(args) else "a" * 40

    monkeypatch.setattr(audit, "run", readback)
    artifact = repo / "fixture-ios.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr(
            "App.app/public/gsip-activation.json",
            json.dumps({"capture_live": False, "library_intake_live": False}),
        )
    return repo, resolved, public


def test_ios_records_selected_pins_exact_binary_tree_and_distinct_licenses(
    ios_evidence: tuple[Path, Path, dict[str, bytes]], tmp_path: Path
) -> None:
    repo, _, _ = ios_evidence
    output = tmp_path / "ios-audit.json"
    audit.collect_ios(repo, output, repo / "fixture-ios.zip")
    result = json.loads(output.read_text())
    assert result["spm"]["pins"][0]["state"]["version"] == "8.5.2"
    assert {item["name"] for item in result["spm"]["binary_inputs"]} == {"Capacitor", "Cordova"}
    for item in result["spm"]["binary_inputs"]:
        assert item["swift_manifest_checksum"] == item["archive"]["sha256"]
        assert item["actual_resolved_tree"]["file_count"] == 1
    assert result["spm"]["upstream_capacitor_source_license"]["spdx"] == "MIT"
    assert result["cordova_apache_source_header"]["spdx"] == "Apache-2.0"


@pytest.mark.parametrize(
    "defect",
    [
        "unknown_pin",
        "changed_version",
        "checksum",
        "changed_tree",
        "pod_resolution",
        "upstream_license",
    ],
)
def test_ios_refuses_unexpected_native_selection_or_unbound_binary(
    ios_evidence: tuple[Path, Path, dict[str, bytes]], tmp_path: Path, defect: str
) -> None:
    repo, resolved, public = ios_evidence
    if defect in {"unknown_pin", "changed_version"}:
        data = json.loads(resolved.read_text())
        if defect == "unknown_pin":
            data["pins"][0]["location"] = "https://example.invalid/proprietary-runtime.git"
        else:
            data["pins"][0]["state"]["version"] = "8.5.3"
        resolved.write_text(json.dumps(data))
    elif defect == "checksum":
        url = next(value for value in public if value.endswith("Capacitor.xcframework.zip"))
        public[url] += b"changed-synthetic-archive"
    elif defect == "changed_tree":
        file = (
            repo
            / "apps/capture-pwa/ios/App/build/SourcePackages/artifacts"
            / "capacitor-swift-pm/Capacitor/Capacitor.xcframework/Info.plist"
        )
        file.write_bytes(b"changed-synthetic-framework")
    elif defect == "pod_resolution":
        (repo / "apps/capture-pwa/ios/Podfile.lock").write_text("synthetic unknown pod")
    else:
        public["https://raw.githubusercontent.com/ionic-team/capacitor/8.5.2/LICENSE"] = (
            b"different license"
        )
    with pytest.raises(audit.AuditError):
        audit.collect_ios(repo, tmp_path / "refused.json", repo / "fixture-ios.zip")


@pytest.mark.parametrize(
    "defect", ["unexpected_jar", "closed_license", "foreign_link", "valid_empty_source"]
)
def test_npm_project_source_does_not_license_unexpected_binary(tmp_path: Path, defect: str) -> None:
    repo = tmp_path / "repo"
    package = repo / "node_modules/.pnpm/synthetic/node_modules/@capacitor/local-notifications"
    package.mkdir(parents=True)
    installed = repo / "apps/capture-pwa/node_modules/@capacitor"
    installed.mkdir(parents=True)
    (installed / "local-notifications").symlink_to(package, target_is_directory=True)
    (package / "package.json").write_text(
        json.dumps({"name": "@capacitor/local-notifications", "version": "8.3.1", "license": "MIT"})
    )
    (package / "LICENSE").write_text(
        "MIT License: Permission is hereby granted, synthetic fixture."
    )
    if defect == "unexpected_jar":
        zipped(package / "android/libs/runtime.jar")
    elif defect == "closed_license":
        data = json.loads((package / "package.json").read_text())
        data["license"] = "Proprietary"
        (package / "package.json").write_text(json.dumps(data))
    elif defect == "foreign_link":
        external = tmp_path / "external"
        external.mkdir()
        (installed / "local-notifications").unlink()
        (installed / "local-notifications").symlink_to(external, target_is_directory=True)
    else:
        (package / "empty-source-placeholder").write_bytes(b"")
        result = audit.npm_evidence(repo, ("@capacitor/local-notifications",))
        assert result[0]["installed_file_count"] == 3
        assert result[0]["license"] == "MIT"
        return
    with pytest.raises(audit.AuditError):
        audit.npm_evidence(repo, ("@capacitor/local-notifications",))


def test_feature_receipt_refuses_unknown_private_sidecar_fields(tmp_path: Path) -> None:
    parent, candidate = tmp_path / "parent.apk", tmp_path / "candidate.apk"
    zipped(parent, b"parent", False)
    zipped(candidate, b"candidate", False)
    left, right, native = receipts(parent, candidate)
    right["unexpected_private_context"] = "synthetic private sentinel"
    with pytest.raises(audit.AuditError):
        audit.feature_comparison(
            parent,
            candidate,
            left,
            right,
            "a" * 40,
            {**native, "source_commit": audit.BASELINE},
            complete_native("a" * 40, right["artifact_sha256"]),
        )


def test_pom_depth_bound_prevents_oversized_structural_evidence(tmp_path: Path) -> None:
    cached(tmp_path, COORD, b"<project>" + b"<nested>" * 65 + b"</nested>" * 65 + b"</project>")
    with pytest.raises(audit.AuditError):
        audit.pom_evidence(COORD, tmp_path, False)


def test_review_traversal_refuses_before_reading_outside_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"synthetic outside-root evidence")
    with pytest.raises(audit.AuditError):
        audit.read(allowed / ".." / "outside", (allowed,))


def test_review_binary_coordinate_cannot_escape_through_traversal(
    graph: tuple[dict[str, Any], Path, Path, Path], tmp_path: Path
) -> None:
    data, repo, cache, _ = graph
    outside = tmp_path / "unmatched.jar"
    zipped(outside, b"synthetic unbound binary")
    selected = cache / "modules-2/files-2.1" / COORD[0] / COORD[1] / COORD[2]
    escaped = selected / "../../../../../../unmatched.jar"
    assert escaped.resolve() == outside
    data["views"][0]["artifacts"][0]["file"] = str(escaped)
    with pytest.raises(audit.AuditError):
        audit.runtime_evidence(data, repo, cache, False)


@pytest.mark.parametrize(
    "field",
    ["version", "groupId", "artifactId", "license_name", "license_url", "parent", "licenses"],
)
def test_review_duplicate_pom_identity_or_license_fields_refuse(tmp_path: Path, field: str) -> None:
    raw = pom()
    if field == "license_name":
        raw = raw.replace(b"</name>", b"</name><name>Proprietary commercial runtime</name>")
    elif field == "license_url":
        raw = raw.replace(b"</url>", b"</url><url>https://example.invalid/private-license</url>")
    elif field == "parent":
        raw = pom(parent=COORD).replace(
            b"</parent>",
            b"</parent><parent><groupId>org.other</groupId><artifactId>other</artifactId><version>9</version></parent>",
        )
    elif field == "licenses":
        raw = raw.replace(
            b"</licenses>",
            b"</licenses><licenses><license><name>Proprietary</name><url>https://example.invalid/private</url></license></licenses>",
        )
    else:
        raw = raw.replace(
            f"</{field}>".encode(), f"</{field}><{field}>different</{field}>".encode()
        )
    cached(tmp_path, COORD, raw)
    with pytest.raises(audit.AuditError):
        audit.pom_evidence(COORD, tmp_path, False)


def test_review_header_only_native_sidecars_refuse_feature_comparison(tmp_path: Path) -> None:
    parent, candidate = tmp_path / "parent.apk", tmp_path / "candidate.apk"
    zipped(parent, b"parent", False)
    zipped(candidate, b"candidate", False)
    left, right, _ = receipts(parent, candidate)
    native = {
        "platform": "android",
        "debug_signing_key_sha256": "b" * 64,
        "schema_version": "gsip-app-notification-native-audit-v1",
        "source_inputs": {"pnpm-lock.yaml": "f" * 64},
    }
    with pytest.raises(audit.AuditError):
        audit.feature_comparison(
            parent,
            candidate,
            left,
            right,
            "a" * 40,
            {**native, "source_commit": audit.BASELINE},
            {**native, "source_commit": "a" * 40},
        )


def test_review_spm_pin_revision_must_match_actual_checkout(
    ios_evidence: tuple[Path, Path, dict[str, bytes]], tmp_path: Path
) -> None:
    repo, resolved, _ = ios_evidence
    data = json.loads(resolved.read_text())
    data["pins"][0]["state"]["revision"] = "f" * 40
    resolved.write_text(json.dumps(data))
    with pytest.raises(audit.AuditError):
        audit.collect_ios(repo, tmp_path / "refused.json", repo / "fixture-ios.zip")


@pytest.mark.parametrize(
    "defect",
    [
        "missing_graph",
        "missing_npm",
        "missing_binary",
        "missing_pom",
        "closed_pom",
        "module_binding",
        "project_binding",
        "source_lock",
        "artifact_binding",
        "tree_digest",
        "unknown_field",
    ],
)
def test_complete_native_sidecar_rejects_removed_or_conflicting_bindings(
    tmp_path: Path, defect: str
) -> None:
    parent, candidate = tmp_path / "parent.apk", tmp_path / "candidate.apk"
    zipped(parent, b"parent", False)
    zipped(candidate, b"candidate", False)
    left, right, native = receipts(parent, candidate)
    other = complete_native("a" * 40, right["artifact_sha256"])
    if defect == "missing_graph":
        other["runtime_views"] = []
    elif defect == "missing_npm":
        other["npm_sources"] = []
    elif defect == "missing_binary":
        other["runtime_views"][0]["resolved_runtime_inputs"] = []
    elif defect == "missing_pom":
        other["runtime_views"][0]["selected_modules"][0]["pom_license_evidence"] = []
    elif defect == "closed_pom":
        other["runtime_views"][0]["selected_modules"][0]["pom_license_evidence"][0]["licenses"][0][
            "declared_name"
        ] = "Proprietary commercial runtime"
    elif defect == "module_binding":
        other["runtime_views"][0]["resolved_runtime_inputs"][0]["coordinate"][2] = "99.0"
    elif defect == "project_binding":
        other["runtime_views"][0]["project_sources"][0]["source_manifest_sha256"] = "1" * 64
    elif defect == "source_lock":
        other["source_inputs"]["apps/capture-pwa/android/build.gradle"] = "1" * 64
    elif defect == "artifact_binding":
        other["built_artifact_sha256"] = "1" * 64
    elif defect == "tree_digest":
        other["runtime_tree_sha256"]["releaseRuntimeClasspath"] = "not a digest"
    else:
        other["unexpected_private_field"] = "synthetic context must not be copied"
    with pytest.raises(audit.AuditError):
        audit.feature_comparison(parent, candidate, left, right, "a" * 40, native, other)


def ios_build_fixture(repo: Path, native: dict[str, Any]) -> dict[str, Any]:
    return {
        "platform": "ios",
        "source_commit": native["source_commit"],
        "artifact_sha256": native["built_artifact_sha256"],
        "lockfile_sha256": {
            "pnpm-lock.yaml": FIXTURE_LOCK_SHA,
            "uv.lock": FIXTURE_LOCK_SHA,
            **{
                str(path.relative_to(repo)): audit.sha(path.read_bytes())
                for path in (repo / "apps/capture-pwa/ios").rglob("Package.resolved")
            },
        },
    }


def test_collected_ios_sidecar_passes_complete_validation_after_serialization(
    ios_evidence: tuple[Path, Path, dict[str, bytes]], tmp_path: Path
) -> None:
    repo, _, _ = ios_evidence
    output = tmp_path / "validated-ios.json"
    audit.collect_ios(repo, output, repo / "fixture-ios.zip")
    native = json.loads(output.read_text())
    audit.validate_native(native, ios_build_fixture(repo, native))
    assert native["spm"]["checkout_revision"] == native["spm"]["pins"][0]["state"]["revision"]
    assert native["spm"]["release_tag_revision"] == native["spm"]["checkout_revision"]


@pytest.mark.parametrize(
    "defect",
    [
        "missing_spm",
        "missing_tree",
        "tree_digest",
        "binary_digest",
        "license_binding",
        "revision_binding",
        "missing_checkout",
        "source_lock",
    ],
)
def test_ios_sidecar_cannot_substitute_partial_or_conflicting_native_evidence(
    ios_evidence: tuple[Path, Path, dict[str, bytes]], tmp_path: Path, defect: str
) -> None:
    repo, _, _ = ios_evidence
    output = tmp_path / "ios-native.json"
    audit.collect_ios(repo, output, repo / "fixture-ios.zip")
    native = json.loads(output.read_text())
    build = ios_build_fixture(repo, native)
    if defect == "missing_spm":
        native["spm"] = {}
    elif defect == "missing_tree":
        native["spm"]["binary_inputs"][0]["actual_resolved_tree"] = {}
    elif defect == "tree_digest":
        native["spm"]["binary_inputs"][0]["actual_resolved_tree"]["files"][0]["sha256"] = "f" * 64
    elif defect == "binary_digest":
        native["spm"]["binary_inputs"][0]["archive"]["sha256"] = "f" * 64
    elif defect == "license_binding":
        native["spm"]["upstream_capacitor_source_license"]["sha256"] = "f" * 64
    elif defect == "revision_binding":
        native["spm"]["checkout_revision"] = "f" * 40
    elif defect == "missing_checkout":
        native["spm"].pop("checkout_revision")
    else:
        build["lockfile_sha256"][
            next(key for key in build["lockfile_sha256"] if key.endswith("Package.resolved"))
        ] = "f" * 64
    with pytest.raises(audit.AuditError):
        audit.validate_native(native, build)


@pytest.mark.parametrize("mismatch", ["checkout", "release_tag"])
def test_spm_local_git_readback_refuses_mismatched_pin_or_release(
    ios_evidence: tuple[Path, Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    repo, _, _ = ios_evidence

    def readback(args: list[str], *unused: Any) -> str:
        if "capacitor-swift-pm" not in " ".join(args):
            return next(
                (
                    cast(str, entry["revision"])
                    for identity, entry in audit.ION_PACKAGES.items()
                    if identity in " ".join(args)
                ),
                "a" * 40,
            )
        if (mismatch == "checkout" and args[-1] == "HEAD") or (
            mismatch == "release_tag" and args[-1] == "refs/tags/8.5.2^{commit}"
        ):
            return "f" * 40
        return "1" * 40

    monkeypatch.setattr(audit, "run", readback)
    with pytest.raises(audit.AuditError):
        audit.collect_ios(repo, tmp_path / "refused.json", repo / "fixture-ios.zip")


def test_workflow_native_audit_commands_match_the_cli_contract() -> None:
    import shlex

    lines = (ROOT / ".github/workflows/app-build.yml").read_text().splitlines()
    commands = [
        shlex.split(line) for line in lines if "python -m scripts.app_notification_audit " in line
    ]
    assert len(commands) == 6
    for argv in commands:
        assert len(argv) == {"android": 8, "ios": 7, "compare": 14}[argv[3]]


def test_project_artifact_must_belong_to_its_inspected_package_output() -> None:
    with pytest.raises(audit.AuditError):
        complete_native(audit.BASELINE, "a" * 64, project_artifact_outside=True)


@pytest.mark.parametrize(
    ("path", "bad"),
    [
        (("comparison",), {}),
        (("comparison", "unknown"), "synthetic private sentinel"),
        (("toolchain", "unknown"), "synthetic private sentinel"),
        (("toolchain", "runner_image", "unknown"), "synthetic private sentinel"),
        (("reference_sha256",), "not-a-digest"),
        (("reference_sha256",), "f" * 64),
        (("source_commit",), "z" * 40),
        (("artifact_sha256",), "f" * 64),
        (("run_number",), False),
        (("run_number",), float("nan")),
        (("run_number",), float("inf")),
        (("run_number",), 123.0),
        (("run_number",), 0),
        (("run_number",), app_build.MAX_RUN_NUMBER + 1),
        (("android_version_code",), True),
        (("android_version_code",), "garbage"),
        (("android_version_code",), 124),
        (("ios_build_version",), {"private": "synthetic"}),
        (("ios_build_version",), "1.1.23"),
        (("marketing_version",), "01.1.0"),
        (("marketing_version",), {"private": "synthetic"}),
        (("source_tree_clean",), 1),
        (("comparison_scope",), "unverified"),
        (("platform",), {}),
        (("lockfile_sha256",), {}),
        (("lockfile_sha256", "pnpm-lock.yaml"), "not-a-digest"),
        (("lockfile_sha256", "unknown"), "f" * 64),
        (("toolchain",), {}),
        (("toolchain", "node"), "v23.0.0"),
        (("toolchain", "pnpm"), []),
        (("toolchain", "python"), "synthetic private sentinel"),
        (("toolchain", "runner"), "macOS-26.0-arm64"),
        (("toolchain", "runner_image"), {}),
        (("toolchain", "runner_image", "RUNNER_ARCH"), []),
        (("toolchain", "runner_image", "RUNNER_ARCH"), "ARM64"),
        (("toolchain", "runner_image", "RUNNER_OS"), "macOS"),
        (("toolchain", "runner_image", "ImageOS"), "unavailable"),
        (("toolchain", "runner_image", "ImageVersion"), "20260230.1.0"),
        (("toolchain", "java"), {}),
        (("toolchain", "gradle"), "Gradle 8.14.3"),
        (("toolchain", "aapt2"), "synthetic private sentinel"),
        (("comparison", "byte_equal"), 1),
        (("comparison", "entry_content_equal"), "true"),
        (("comparison", "byte_equal"), False),
        (("comparison", "normalization"), "invented proof"),
        (("comparison", "changed_entries"), ["../private"]),
        (("comparison", "changed_entries"), ["classes.dex", "classes.dex"]),
        (("comparison", "first_only"), ["z", "a"]),
        (("comparison", "second_only"), {}),
        (("comparison", "second_only"), ["unmeasured"]),
        (("unknown",), {"private": "synthetic"}),
    ],
)
def test_full_build_receipt_refuses_invalid_nested_proof(
    tmp_path: Path, path: tuple[str, ...], bad: Any
) -> None:
    artifact = tmp_path / "candidate.apk"
    zipped(artifact, b"synthetic", False)
    value = genuine_build_receipt(artifact, "a" * 40)
    nested = value
    for part in path[:-1]:
        nested = nested[part]
    nested[path[-1]] = bad
    with pytest.raises(audit.AuditError):
        audit.validate_build_receipt(value, artifact, artifact)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"proof":{"a":1,"a":2}}',
        b'{"proof":NaN}',
        b'{"proof":{"nested":Infinity}}',
        b'{"proof":-Infinity}',
        b'{"proof":1e999}',
    ],
)
def test_json_nested_proofs_reject_duplicate_and_nonfinite_values(raw: bytes) -> None:
    with pytest.raises(audit.AuditError):
        audit.decoded(raw)


def test_json_finite_decimal_is_preserved_for_incidental_package_metadata() -> None:
    assert audit.decoded(b'{"metadata":0.5}') == {"metadata": 0.5}


def repacked(path: Path, reference: Path, variant: str) -> None:
    with zipfile.ZipFile(reference) as first, zipfile.ZipFile(path, "w") as second:
        second.comment = b"synthetic different archive metadata"
        for entry in first.infolist():
            second.writestr(entry, first.read(entry.filename))
        if variant == "content":
            second.writestr("synthetic-feature-marker.txt", b"synthetic repeated content")


@pytest.mark.parametrize("target", ["android", "ios"])
@pytest.mark.parametrize("variant", ["identical", "metadata", "content"])
def test_actual_producer_current_and_repeated_build_receipts_pass(
    tmp_path: Path, target: str, variant: str
) -> None:
    reference = tmp_path / "reference.zip"
    artifact = tmp_path / "current.zip"
    if target == "android":
        zipped(reference, b"synthetic", False)
    else:
        with zipfile.ZipFile(reference, "w") as archive:
            archive.writestr(
                "App.app/public/gsip-activation.json",
                json.dumps({"capture_live": False, "library_intake_live": False}),
            )
    if variant == "identical":
        artifact.write_bytes(reference.read_bytes())
    else:
        repacked(artifact, reference, variant)
    value = genuine_build_receipt(artifact, "a" * 40, target, reference)
    audit.validate_build_receipt(audit.decoded(json.dumps(value).encode()), artifact, reference)
    assert value["comparison"]["byte_equal"] is (variant == "identical")
    assert value["comparison"]["entry_content_equal"] is (variant != "content")
    if variant != "identical":
        with pytest.raises(audit.AuditError):
            audit.validate_build_receipt(value, artifact, None)
        with pytest.raises(audit.AuditError):
            audit.validate_build_receipt(value, artifact, artifact)


@pytest.mark.parametrize("variant", ["identical", "metadata", "content"])
def test_ios_complete_feature_comparison_accepts_real_producer_proofs(
    ios_evidence: tuple[Path, Path, dict[str, bytes]], tmp_path: Path, variant: str
) -> None:
    repo, resolved, _ = ios_evidence
    reference = repo / "fixture-ios.zip"
    parent = tmp_path / "parent.zip"
    candidate = tmp_path / "candidate.zip"
    parent.write_bytes(reference.read_bytes())
    if variant == "identical":
        candidate.write_bytes(reference.read_bytes())
    else:
        repacked(candidate, reference, variant)
    output = tmp_path / "native.json"
    audit.collect_ios(repo, output, candidate)
    right_native = audit.decoded(output.read_bytes())
    left_native = copy.deepcopy(right_native)
    left_native["source_commit"] = audit.BASELINE
    left_native["built_artifact_sha256"] = audit.sha(parent.read_bytes())
    left_native["npm_sources"] = [
        entry
        for entry in left_native["npm_sources"]
        if entry["name"] != "@capacitor/local-notifications"
    ]
    left = genuine_build_receipt(parent, audit.BASELINE, "ios", reference, resolved.read_bytes())
    right = genuine_build_receipt(candidate, "a" * 40, "ios", reference, resolved.read_bytes())
    result = audit.feature_comparison(
        parent, candidate, left, right, "a" * 40, left_native, right_native, reference, reference
    )
    assert result["input_receipts"]["candidate"]["comparison"] == app_build.comparison(
        reference, candidate
    )


@pytest.mark.parametrize("field", ["xcode", "sdk", "runner", "runner_image"])
def test_ios_toolchain_receipt_requires_each_actual_field(tmp_path: Path, field: str) -> None:
    artifact = tmp_path / "ios.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr(
            "App.app/public/gsip-activation.json",
            json.dumps({"capture_live": False, "library_intake_live": False}),
        )
    value = genuine_build_receipt(artifact, "a" * 40, "ios")
    value["toolchain"][field] = {"private": "synthetic"}
    with pytest.raises(audit.AuditError):
        audit.validate_build_receipt(value, artifact, artifact)


def test_cli_never_writes_unknown_build_proof_fields(tmp_path: Path) -> None:
    parent, candidate = tmp_path / "parent.apk", tmp_path / "candidate.apk"
    zipped(parent, b"parent", False)
    zipped(candidate, b"candidate", False)
    left, right, native = receipts(parent, candidate)
    right["toolchain"]["unknown_private_context"] = "synthetic private sentinel"
    paths = []
    for name, value in [
        ("left", left),
        ("right", right),
        ("left-native", native),
        ("right-native", complete_native("a" * 40, right["artifact_sha256"])),
    ]:
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(value))
        paths.append(path)
    output = tmp_path / "never-written.json"
    assert (
        audit.main(
            [
                "compare",
                str(parent),
                str(candidate),
                str(paths[0]),
                str(paths[1]),
                "a" * 40,
                str(output),
                str(paths[2]),
                str(paths[3]),
                str(parent),
                str(candidate),
            ]
        )
        == 1
    )
    assert not output.exists()


def test_ios_exact_ci_four_package_graph_and_nested_tool_inventory_passes(
    ios_evidence: tuple[Path, Path, dict[str, bytes]], tmp_path: Path
) -> None:
    repo, _, _ = ios_evidence
    output = tmp_path / "complete-ci-shape.json"
    audit.collect_ios(repo, output, repo / "fixture-ios.zip")
    native = audit.decoded(output.read_bytes())
    assert {pin["identity"] for pin in native["spm"]["pins"]} == {
        "capacitor-swift-pm",
        "ion-ios-camera",
        "ion-ios-filesystem",
        "ion-ios-geolocation",
    }
    assert len(native["spm"]["remote_source_packages"]) == 3
    assert len(native["spm"]["resolved_inventory"]) == 3
    assert (
        sum(
            row["scope"] == "application selected graph"
            for row in native["spm"]["resolved_inventory"]
        )
        == 1
    )
    assert all(
        row["runtime_remote_dependencies"] == [] and row["binary_targets"] == []
        for row in native["spm"]["remote_source_packages"]
    )
    assert (
        native["spm"]["remote_source_packages"][0]["test_only_dependencies"]
        == audit.ION_PACKAGES["ion-ios-camera"]["test_dependencies"]
    )
    audit.validate_native(native, ios_build_fixture(repo, native))


@pytest.mark.parametrize(
    "defect",
    [
        "missing_pin",
        "unknown_pin",
        "duplicate_pin",
        "wrong_location",
        "wrong_version",
        "wrong_revision",
        "wrong_kind",
        "private_pin_field",
        "missing_checkout",
        "wrong_head",
        "wrong_tag",
        "changed_manifest",
        "missing_license",
        "changed_license",
        "changed_source",
        "source_symlink",
        "archive_changed",
        "archive_repacked",
        "archive_missing",
        "extra_resolved",
        "tool_pin_changed",
        "tool_unknown",
        "tool_nested_extra",
    ],
)
def test_ios_complete_graph_refuses_unbound_source_selection(
    ios_evidence: tuple[Path, Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    defect: str,
) -> None:
    repo, resolved, public = ios_evidence
    pins = audit.decoded(resolved.read_bytes())
    entry = pins["pins"][1]
    checkout = repo / "apps/capture-pwa/ios/App/build/SourcePackages/checkouts/ion-ios-camera"
    if defect == "missing_pin":
        pins["pins"].pop()
    elif defect == "unknown_pin":
        entry["identity"] = "unreviewed-sdk"
    elif defect == "duplicate_pin":
        pins["pins"][2] = copy.deepcopy(entry)
    elif defect == "wrong_location":
        entry["location"] = "https://example.invalid/closed.git"
    elif defect == "wrong_version":
        entry["state"]["version"] = "99.0.0"
    elif defect == "wrong_revision":
        entry["state"]["revision"] = "f" * 40
    elif defect == "wrong_kind":
        entry["kind"] = "binary"
    elif defect == "private_pin_field":
        entry["private"] = "synthetic private sentinel"
    elif defect == "missing_checkout":
        (checkout / "Package.swift").unlink()
    elif defect in {"wrong_head", "wrong_tag"}:
        original = audit.run

        def mismatched(args: list[str], *unused: Any) -> str:
            if "ion-ios-camera" in " ".join(args) and (
                args[-1] == "HEAD" if defect == "wrong_head" else args[-1].startswith("refs/tags/")
            ):
                return "f" * 40
            return original(args)

        monkeypatch.setattr(audit, "run", mismatched)
    elif defect == "changed_manifest":
        (checkout / "Package.swift").write_text('.binaryTarget(name: "unreviewed")')
    elif defect == "missing_license":
        (checkout / "LICENSE").unlink()
    elif defect == "changed_license":
        (checkout / "LICENSE").write_text("proprietary licence")
    elif defect == "changed_source":
        (checkout / "unmatched.swift").write_text("synthetic different source")
    elif defect == "source_symlink":
        (checkout / "unmatched.swift").symlink_to(repo / "fixture-ios.zip")
    elif defect in {"archive_changed", "archive_repacked", "archive_missing"}:
        url = next(url for url in public if "codeload.github.com/ionic-team/ion-ios-camera" in url)
        if defect == "archive_changed":
            public[url] = b"synthetic corrupt source archive"
        elif defect == "archive_repacked":
            public[url] = gzip.compress(gzip.decompress(public[url]), mtime=1)
        else:
            public.pop(url)
    elif defect == "extra_resolved":
        (repo / "apps/capture-pwa/ios/unreviewed").mkdir()
        (repo / "apps/capture-pwa/ios/unreviewed/Package.resolved").write_text('{"pins":[]}')
    else:
        nested = (
            repo
            / "apps/capture-pwa/ios/App/build/SourcePackages/checkouts/ion-ios-filesystem"
            / audit.UPSTREAM_RESOLVED["ion-ios-filesystem"]
        )
        tool = audit.decoded(nested.read_bytes())
        if defect == "tool_pin_changed":
            tool["pins"][0]["state"]["revision"] = "f" * 40
        elif defect == "tool_unknown":
            tool["pins"][0]["identity"] = "unreviewed-tool"
        else:
            tool["private"] = {"sentinel": "synthetic"}
        nested.write_text(json.dumps(tool))
    resolved.write_text(json.dumps(pins))
    with pytest.raises((audit.AuditError, OSError, KeyError)):
        audit.collect_ios(repo, tmp_path / "never-written.json", repo / "fixture-ios.zip")
    assert not (tmp_path / "never-written.json").exists()


@pytest.mark.parametrize(
    "defect",
    [
        "missing_sources",
        "unknown_source",
        "missing_inventory",
        "extra_inventory",
        "source_revision",
        "source_tag",
        "source_license",
        "source_manifest",
        "source_archive",
        "source_tree",
        "source_tree_bytes",
        "selected_runtime_dependency",
        "binary_target",
        "unbound_tool_lock",
        "unknown_nested_metadata",
    ],
)
def test_full_ios_receipt_rejects_ambiguous_or_partial_four_graph_proof(
    ios_evidence: tuple[Path, Path, dict[str, bytes]], tmp_path: Path, defect: str
) -> None:
    repo, _, _ = ios_evidence
    output = tmp_path / "source.json"
    audit.collect_ios(repo, output, repo / "fixture-ios.zip")
    native = audit.decoded(output.read_bytes())
    build = ios_build_fixture(repo, native)
    spm = native["spm"]
    row = spm["remote_source_packages"][0]
    if defect == "missing_sources":
        spm["remote_source_packages"] = []
    elif defect == "unknown_source":
        row["identity"] = "unknown"
    elif defect == "missing_inventory":
        spm["resolved_inventory"] = []
    elif defect == "extra_inventory":
        spm["resolved_inventory"].append(copy.deepcopy(spm["resolved_inventory"][0]))
    elif defect == "source_revision":
        row["checkout_revision"] = "f" * 40
    elif defect == "source_tag":
        row["release_tag_revision"] = "f" * 40
    elif defect == "source_license":
        row["license"]["sha256"] = "f" * 64
    elif defect == "source_manifest":
        row["manifest_sha256"] = "f" * 64
    elif defect == "source_archive":
        row["source_archive"]["sha256"] = "f" * 64
    elif defect == "source_tree":
        row["actual_source_tree"]["tree_sha256"] = "f" * 64
    elif defect == "source_tree_bytes":
        row["actual_source_tree"]["bytes"] = False
    elif defect == "selected_runtime_dependency":
        row["runtime_remote_dependencies"] = [{"location": "https://example.invalid/closed"}]
    elif defect == "binary_target":
        row["binary_targets"] = [{"unknown": "synthetic"}]
    elif defect == "unknown_nested_metadata":
        row["license"]["private"] = "synthetic private sentinel"
    else:
        row = next(
            entry
            for entry in spm["resolved_inventory"]
            if entry["scope"] != "application selected graph"
        )
        row["sha256"] = "f" * 64
        build["lockfile_sha256"][row["path"]] = "f" * 64
    with pytest.raises(audit.AuditError):
        audit.validate_native(native, build)


def test_missing_release_artifact_is_refused_with_fixed_safe_diagnostic(
    graph: tuple[dict[str, Any], Path, Path, Path],
) -> None:
    data, repo, cache, file = graph
    data["views"][1]["artifacts"][0]["file"] = str(file.parent / "unbuilt-release.jar")
    with pytest.raises(FileNotFoundError) as caught:
        audit.runtime_evidence(data, repo, cache, False)
    diagnostic = audit.diagnostic(caught.value)
    assert diagnostic["stage"] == "android-runtime-binaries"
    assert diagnostic["error_class"] == "MISSING_FILE"
    assert set(diagnostic) == {"stage", "error_class", "source_line", "counts"}
    assert 0 < diagnostic["source_line"] < 10_000
    assert diagnostic["counts"] == {"module_inputs": 1, "project_inputs": 1}
    assert "unbuilt-release" not in json.dumps(diagnostic)
    assert str(repo) not in json.dumps(diagnostic)


@pytest.mark.parametrize("defect", ["stage", "count_name", "bool_count", "huge_count"])
def test_diagnostic_inputs_are_fixed_enum_and_bounded_counts(defect: str) -> None:
    with pytest.raises(audit.AuditError):
        if defect == "stage":
            audit.mark("synthetic private sentinel")
        elif defect == "count_name":
            audit.mark("start", private_context=1)
        elif defect == "bool_count":
            audit.mark("start", remote_pins=True)
        else:
            audit.mark("start", remote_pins=30_001)


def test_error_diagnostic_does_not_emit_paths_payloads_or_tool_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    def private_error(*unused: Any) -> None:
        audit.mark("android-gradle-inspection")
        raise __import__("subprocess").CalledProcessError(
            1,
            ["synthetic private path"],
            output="synthetic private payload",
            stderr="synthetic private stderr",
        )

    monkeypatch.setattr(audit, "collect_android", private_error)
    assert (
        audit.main(
            [
                "android",
                str(tmp_path),
                str(tmp_path),
                str(tmp_path / "out.json"),
                str(tmp_path / "synthetic-key"),
            ]
        )
        == 1
    )
    text = capsys.readouterr().err
    assert "synthetic private" not in text
    assert "BUILD_TOOL" in text and "android-gradle-inspection" in text
    assert str(tmp_path) not in text


def test_fake_gradle_inspection_preserves_both_actual_views_and_reports_missing_release(
    graph: tuple[dict[str, Any], Path, Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data, repo, cache, file = graph
    data["views"][1]["artifacts"][0]["file"] = str(file.parent / "unbuilt-release.jar")
    output = tmp_path / "evidence/native.json"
    output.parent.mkdir()
    calls: list[list[str]] = []

    def fake_gradle(args: list[str], *unused: Any) -> str:
        calls.append(args)
        if ":app:gsipRuntimeEvidence" in args:
            task = Path(args[args.index("-I") + 1])
            assert task.read_text() == audit.GRADLE_TASK
            assert "debugRuntimeClasspath" in task.read_text()
            assert "releaseRuntimeClasspath" in task.read_text()
            graph_output = Path(
                next(
                    arg.split("=", 1)[1] for arg in args if arg.startswith("-PgsipEvidenceOutput=")
                )
            )
            graph_output.write_text(json.dumps(data))
            return ""
        return "synthetic runtime tree\n+--- org.example:example-runtime:1.2.3"

    monkeypatch.setattr(audit, "run", fake_gradle)
    with pytest.raises(FileNotFoundError) as caught:
        audit.collect_android(repo, cache, output, tmp_path / "unused-debug-key")
    assert len(calls) == 4
    assert audit.diagnostic(caught.value)["stage"] == "android-runtime-binaries"
    assert not output.exists()
    assert data["views"][1]["artifacts"][0]["file"] != data["views"][0]["artifacts"][0]["file"]


def test_primary_source_tree_uses_canonical_string_paths_for_shared_stems(tmp_path: Path) -> None:
    import io

    root = tmp_path / "repo"
    checkout = root / "checkout"
    payloads = {
        "Library/source.swift": b"synthetic source",
        "Library.xcodeproj/project.pbxproj": b"synthetic project",
    }
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, data in payloads.items():
            file = checkout / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
            member = tarfile.TarInfo("synthetic-library-1.0.0/" + name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    actual = audit.checkout_source_tree(checkout, root)
    published = audit.source_archive(stream.getvalue(), "synthetic-library", "1.0.0")
    assert actual == published
    assert [file["path"] for file in actual["files"]] == sorted(payloads)


@pytest.mark.parametrize("defect", ["traversal", "symlink", "binary", "wrong_root", "duplicate"])
def test_remote_source_archives_reject_unreviewed_file_inputs(defect: str) -> None:
    import io

    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        name = "synthetic-library-1.0.0/source.swift"
        if defect == "traversal":
            name = "synthetic-library-1.0.0/../private"
        elif defect == "binary":
            name = "synthetic-library-1.0.0/unknown.xcframework/binary"
        elif defect == "wrong_root":
            name = "other-library-1.0.0/source.swift"
        member = tarfile.TarInfo(name)
        if defect == "symlink":
            member.type = tarfile.SYMTYPE
            member.linkname = "../private"
            archive.addfile(member)
        else:
            member.size = 1
            archive.addfile(member, io.BytesIO(b"a"))
            if defect == "duplicate":
                archive.addfile(member, io.BytesIO(b"b"))
    with pytest.raises(audit.AuditError):
        audit.source_archive(stream.getvalue(), "synthetic-library", "1.0.0")


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_source",
        "source_target",
        "source_dependency",
        "missing_manifest",
        "missing_readme",
        "source_symlink",
        "archive_changed",
        "archive_repacked",
        "readme_changed",
        "coordinated_source_license",
        "changed_apache_header",
    ],
)
def test_capacitor_full_reviewed_checkout_and_primary_bytes_are_required(
    ios_evidence: tuple[Path, Path, dict[str, bytes]], tmp_path: Path, mutation: str
) -> None:
    repo, _, public = ios_evidence
    checkout = repo / "apps/capture-pwa/ios/App/build/SourcePackages/checkouts/capacitor-swift-pm"
    if mutation == "extra_source":
        (checkout / "Unreviewed.swift").write_text("// synthetic added code")
    elif mutation in {"source_target", "source_dependency"}:
        with (checkout / "Package.swift").open("a") as stream:
            stream.write(
                '\n.target(name: "Unreviewed")'
                if mutation == "source_target"
                else '\n.package(url: "https://example.invalid/unreviewed.git", from: "1.0.0")'
            )
    elif mutation in {"missing_manifest", "missing_readme"}:
        (checkout / ("Package.swift" if mutation == "missing_manifest" else "README.md")).unlink()
    elif mutation == "source_symlink":
        (checkout / "Unreviewed.swift").symlink_to(repo / "fixture-ios.zip")
    elif mutation in {"archive_changed", "archive_repacked"}:
        url = "https://codeload.github.com/ionic-team/capacitor-swift-pm/tar.gz/refs/tags/8.5.2"
        public[url] = (
            b"synthetic corrupt source archive"
            if mutation == "archive_changed"
            else gzip.compress(gzip.decompress(public[url]), mtime=1)
        )
    elif mutation == "readme_changed":
        url = "https://raw.githubusercontent.com/ionic-team/capacitor-swift-pm/8.5.2/README.md"
        public[url] += b"\nsynthetic unreviewed description"
    elif mutation == "coordinated_source_license":
        url = "https://raw.githubusercontent.com/ionic-team/capacitor/8.5.2/LICENSE"
        changed = public[url] + b"\nsynthetic unreviewed license content"
        public[url] = changed
        (repo / "node_modules/@capacitor/ios/LICENSE").write_bytes(changed)
    else:
        header = (
            repo
            / "node_modules/@capacitor/ios/CapacitorCordova/CapacitorCordova/Classes/Public/CDV.h"
        )
        header.write_bytes(header.read_bytes() + b"\nsynthetic unreviewed licence header")
    with pytest.raises((audit.AuditError, OSError)):
        audit.collect_ios(repo, tmp_path / "must-refuse.json", repo / "fixture-ios.zip")
    assert not (tmp_path / "must-refuse.json").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "manifest",
        "coordinated_revision",
        "binary_checksum",
        "description",
        "source_missing",
        "source_archive",
        "source_tree",
        "source_tree_count",
        "source_unknown",
        "binary_archive_size",
        "binary_tree",
        "binary_notice",
        "coordinated_license",
        "header",
    ],
)
def test_capacitor_sidecar_proofs_are_bound_to_fixed_primary_expectations(
    ios_evidence: tuple[Path, Path, dict[str, bytes]], tmp_path: Path, mutation: str
) -> None:
    repo, _, _ = ios_evidence
    output = tmp_path / "valid.json"
    audit.collect_ios(repo, output, repo / "fixture-ios.zip")
    native = audit.decoded(output.read_bytes())
    build = ios_build_fixture(repo, native)
    audit.validate_native(native, build)
    spm = native["spm"]
    source = spm["capacitor_source"]
    if mutation == "manifest":
        spm["selected_manifest_sha256"] = source["manifest_sha256"] = "f" * 64
    elif mutation == "coordinated_revision":
        spm["pins"][0]["state"]["revision"] = "f" * 40
        spm["checkout_revision"] = spm["release_tag_revision"] = "f" * 40
        source["checkout_revision"] = source["release_tag_revision"] = "f" * 40
        for entry in spm["resolved_inventory"]:
            if entry["scope"] == "application selected graph":
                entry["pins"][0]["state"]["revision"] = "f" * 40
    elif mutation == "binary_checksum":
        row = spm["binary_inputs"][0]
        row["swift_manifest_checksum"] = row["archive"]["sha256"] = "f" * 64
    elif mutation == "description":
        spm["upstream_binary_host_description"]["sha256"] = "f" * 64
    elif mutation == "source_missing":
        spm.pop("capacitor_source")
    elif mutation == "source_archive":
        source["source_archive"]["sha256"] = "f" * 64
    elif mutation == "source_tree":
        source["actual_source_tree"]["files"][0]["sha256"] = "f" * 64
        source["actual_source_tree"]["tree_sha256"] = audit.sha(
            json.dumps(
                source["actual_source_tree"]["files"], sort_keys=True, separators=(",", ":")
            ).encode()
        )
    elif mutation == "source_tree_count":
        source["actual_source_tree"]["file_count"] = True
    elif mutation == "source_unknown":
        source["private"] = "synthetic private sentinel"
    elif mutation == "binary_archive_size":
        spm["binary_inputs"][0]["archive"]["bytes"] += 1
    elif mutation == "binary_tree":
        row = spm["binary_inputs"][0]["actual_resolved_tree"]
        row["files"][0]["sha256"] = "f" * 64
        row["tree_sha256"] = audit.sha(
            json.dumps(row["files"], sort_keys=True, separators=(",", ":")).encode()
        )
    elif mutation == "binary_notice":
        spm["binary_inputs"][0]["archive"]["embedded_license_notice_files"] = [
            {"path": "LICENSE", "sha256": "f" * 64, "bytes": 1}
        ]
    elif mutation == "coordinated_license":
        spm["upstream_capacitor_source_license"]["sha256"] = "f" * 64
        next(package for package in native["npm_sources"] if package["name"] == "@capacitor/ios")[
            "license_sha256"
        ] = "f" * 64
    else:
        native["cordova_apache_source_header"]["sha256"] = "f" * 64
    with pytest.raises(audit.AuditError):
        audit.validate_native(native, build)


@pytest.mark.parametrize("kind", ["regular", "fifo", "fifo_allow_empty", "swapped_fifo"])
def test_bounded_descriptor_read_refuses_fifo_without_waiting_for_a_writer(
    tmp_path: Path, kind: str
) -> None:
    """Actual FIFO/open-time substitution; every child is bounded and reaped."""
    import select
    import subprocess
    import sys

    path = tmp_path / "synthetic-input"
    if kind in {"fifo", "fifo_allow_empty"}:
        os.mkfifo(path)
    else:
        path.write_bytes(b"synthetic regular content")
    child_code = """import sys,os
from pathlib import Path
from scripts import app_notification_audit as audit
path=Path(sys.argv[1]);kind=sys.argv[2]
if kind=='swapped_fifo':
 original_open=audit.os.open
 def replace_at_open(file,flags,*args,**kwargs):
  if Path(file)==path:
   path.unlink();os.mkfifo(path)
  return original_open(file,flags,*args,**kwargs)
 audit.os.open=replace_at_open
print('ready',flush=True)
if sys.stdin.readline().strip()!='go':sys.exit(2)
try:
 data=audit.read(path,(path.parent,),allow_empty=kind=='fifo_allow_empty')
except (audit.AuditError,OSError):print('refused',flush=True)
else:print('regular-ok' if data==b'synthetic regular content' else 'unexpected',flush=True)
"""
    command = [sys.executable, "-c", child_code, str(path), kind]
    child = subprocess.Popen(  # noqa: S603 - fixed synthetic read-only child, explicitly bounded and reaped
        command,
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={"PYTHONPATH": str(ROOT), "PATH": os.defpath},
    )
    completed = False
    output = stderr = ""
    try:
        assert child.stdout is not None
        ready, _, _ = select.select([child.stdout], [], [], 2)
        assert ready, "synthetic child did not start within its startup bound"
        assert child.stdout.readline() == "ready\n"
        try:
            output, stderr = child.communicate(input="go\n", timeout=0.25)
            completed = True
        except subprocess.TimeoutExpired:
            child.kill()
            output, stderr = child.communicate(timeout=2)
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=2)
    assert child.poll() is not None
    assert completed, "special-file open blocked before descriptor type refusal"
    assert child.returncode == 0
    assert stderr == ""
    assert output == ("regular-ok\n" if kind == "regular" else "refused\n")


def test_nonblocking_open_keeps_nofollow_and_descriptor_type_checks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    file = tmp_path / "regular"
    file.write_bytes(b"synthetic bytes")
    actual_open = os.open
    flags_seen: list[int] = []

    def checked_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        flags_seen.append(flags)
        return actual_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", checked_open)
    assert audit.read(file, (tmp_path,)) == b"synthetic bytes"
    assert len(flags_seen) == 1
    assert flags_seen[0] & os.O_NOFOLLOW
    assert flags_seen[0] & os.O_NONBLOCK


GRADLE_INSPECTION_COMMAND = [
    "/synthetic/private/android/gradlew",
    "--no-daemon",
    "--console=plain",
    "-I",
    "/synthetic/private/inspection.gradle",
    ":app:gsipRuntimeEvidence",
    "-PgsipEvidenceOutput=/synthetic/private/resolved.json",
]


def gradle_failure_fixture(reason: str) -> str:
    return (
        "FAILURE: Build failed with an exception.\n\n* What went wrong:\n"
        "Execution failed for task ':app:gsipRuntimeEvidence'.\n> "
        + reason
        + "\n\n* Try:\n> Run with --stacktrace option.\n\nBUILD FAILED in 1s\n"
    )


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("unsupported runtime component", "GRADLE_COMPONENT_UNSUPPORTED"),
        ("unsupported runtime artifact", "GRADLE_ARTIFACT_UNSUPPORTED"),
        (
            "Configuration with name 'releaseRuntimeClasspath' not found.",
            "GRADLE_CONFIGURATION_MISSING",
        ),
        (
            "Could not resolve all artifacts for configuration ':app:releaseRuntimeClasspath'.\n"
            "> File /synthetic/private/unbuilt-release.jar does not exist.",
            "GRADLE_RUNTIME_FILE_MISSING",
        ),
        (
            "Could not resolve all artifacts for configuration ':app:debugRuntimeClasspath'.\n"
            "> Could not GET https://example.invalid/private.\n> Connection timed out",
            "GRADLE_DEPENDENCY_NETWORK",
        ),
    ],
)
def test_gradle_tool_failure_uses_only_fixed_reason_class(reason: str, expected: str) -> None:
    import subprocess

    audit.mark("android-gradle-inspection")
    error = subprocess.CalledProcessError(
        1, GRADLE_INSPECTION_COMMAND, output="", stderr=gradle_failure_fixture(reason)
    )
    value = audit.diagnostic(error)
    assert value["error_class"] == expected
    assert set(value) == {"stage", "error_class", "source_line", "counts"}
    assert value["counts"] == {}
    assert "synthetic/private" not in json.dumps(value)
    assert "https://" not in json.dumps(value)


@pytest.mark.parametrize("location", ["stdout", "stderr", "bytes", "crlf"])
def test_gradle_fixed_class_handles_supported_output_encodings(location: str) -> None:
    import subprocess

    audit.mark("android-gradle-inspection")
    text = gradle_failure_fixture("unsupported runtime component")
    output: Any = text if location == "stdout" else ""
    stderr: Any = text if location != "stdout" else None
    if location == "bytes":
        stderr = text.encode("utf-8")
    elif location == "crlf":
        stderr = text.replace("\n", "\r\n")
    value = audit.diagnostic(
        subprocess.CalledProcessError(1, GRADLE_INSPECTION_COMMAND, output=output, stderr=stderr)
    )
    assert value["error_class"] == "GRADLE_COMPONENT_UNSUPPORTED"


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        (
            "Could not get unknown property 'projectPath' for synthetic private object.",
            "GRADLE_INSPECTION_API",
        ),
        ("Task 'gsipRuntimeEvidence' not found in project ':app'.", "GRADLE_TASK_MISSING"),
    ],
)
def test_gradle_fixed_class_identifies_task_and_known_api_only(reason: str, expected: str) -> None:
    import subprocess

    audit.mark("android-gradle-inspection")
    text = gradle_failure_fixture(reason)
    if expected == "GRADLE_TASK_MISSING":
        text = text.replace("Execution failed for task ':app:gsipRuntimeEvidence'.\n> ", "")
    error = subprocess.CalledProcessError(1, GRADLE_INSPECTION_COMMAND, stderr=text)
    value = audit.diagnostic(error)
    assert value["error_class"] == expected
    assert "synthetic private" not in json.dumps(value)


@pytest.mark.parametrize(
    "defect",
    [
        "wrong_stage",
        "wrong_command",
        "string_command",
        "short_command",
        "relative_tool",
        "relative_script",
        "wrong_task",
        "relative_output",
        "control_argument",
        "huge_argument",
        "bool_code",
        "zero_code",
        "string_code",
        "invalid_bytes",
        "surrogate_text",
        "huge_stdout",
        "huge_stderr",
        "combined_bound",
        "unexpected_stream",
        "bool_stream",
        "control_stream",
        "duplicate_failure",
        "missing_header",
        "wrong_task_context",
        "reason_only",
        "missing_try",
        "missing_footer",
        "footer_before_context",
        "duplicate_section",
        "private_unknown",
        "similar_reason",
        "outside_reason",
        "unprefixed_reason",
        "ambiguous",
        "network_without_resolution",
        "network_without_cause",
        "unknown_api",
        "unknown_config",
    ],
)
def test_gradle_fixed_class_refuses_unbounded_or_ambiguous_context(defect: str) -> None:
    import subprocess

    audit.mark("android-gradle-inspection")
    command: Any = list(GRADLE_INSPECTION_COMMAND)
    code: Any = 1
    output: Any = ""
    text: Any = gradle_failure_fixture("unsupported runtime component")
    if defect == "wrong_stage":
        audit.mark("android-dependency-trees")
    elif defect == "wrong_command":
        command = ["/synthetic/private/gradlew", "--version"]
    elif defect == "string_command":
        command = " ".join(command)
    elif defect == "short_command":
        command.pop()
    elif defect == "relative_tool":
        command[0] = "gradlew"
    elif defect == "relative_script":
        command[4] = "inspection.gradle"
    elif defect == "wrong_task":
        command[5] = ":app:privateTask"
    elif defect == "relative_output":
        command[6] = "-PgsipEvidenceOutput=relative.json"
    elif defect == "control_argument":
        command[0] += "\n"
    elif defect == "huge_argument":
        command[0] = "/" + "x" * 4096
    elif defect == "bool_code":
        code = True
    elif defect == "zero_code":
        code = 0
    elif defect == "string_code":
        code = "1"
    elif defect == "invalid_bytes":
        text = text.encode() + b"\xff"
    elif defect == "surrogate_text":
        text += "\ud800"
    elif defect == "huge_stdout":
        output = "x" * (audit.MAX_DIAGNOSTIC_BYTES + 1)
    elif defect == "huge_stderr":
        text += "x" * audit.MAX_DIAGNOSTIC_BYTES
    elif defect == "combined_bound":
        output = "x" * audit.MAX_DIAGNOSTIC_BYTES
    elif defect == "unexpected_stream":

        class PrivatePayload:
            def __str__(self) -> str:
                pytest.fail("private stream must not be coerced to text")

        output = PrivatePayload()
    elif defect == "bool_stream":
        output = True
    elif defect == "control_stream":
        text += "\x00"
    elif defect == "duplicate_failure":
        text += text
    elif defect == "missing_header":
        text = text.replace("FAILURE: Build failed with an exception.\n", "")
    elif defect == "wrong_task_context":
        text = text.replace(":app:gsipRuntimeEvidence", ":app:privateTask")
    elif defect == "reason_only":
        text = "unsupported runtime component"
    elif defect == "missing_try":
        text = text.replace("* Try:\n", "")
    elif defect == "missing_footer":
        text = text.replace("BUILD FAILED in 1s", "")
    elif defect == "footer_before_context":
        text = "BUILD FAILED in 1s\n" + text.replace("BUILD FAILED in 1s", "")
    elif defect == "duplicate_section":
        text += "* What went wrong:\n"
    elif defect == "private_unknown":
        text = gradle_failure_fixture("synthetic private payload https://example.invalid/private")
    elif defect == "similar_reason":
        text = gradle_failure_fixture("synthetic unsupported runtime component private")
    elif defect == "outside_reason":
        text = "unsupported runtime component\n" + gradle_failure_fixture("private unknown")
    elif defect == "unprefixed_reason":
        text = text.replace("> unsupported runtime component", "unsupported runtime component")
    elif defect == "ambiguous":
        text = gradle_failure_fixture(
            "unsupported runtime component\n> unsupported runtime artifact"
        )
    elif defect == "network_without_resolution":
        text = gradle_failure_fixture(
            "Could not GET https://example.invalid\n> Connection timed out"
        )
    elif defect == "network_without_cause":
        text = gradle_failure_fixture(
            "Could not resolve all artifacts for configuration ':app:debugRuntimeClasspath'.\n"
            "> Could not GET https://example.invalid\n> synthetic private cause"
        )
    elif defect == "unknown_api":
        text = gradle_failure_fixture("Could not get unknown property 'privateInput' for object.")
    elif defect == "unknown_config":
        text = gradle_failure_fixture("Configuration with name 'privateInput' not found.")
    error = subprocess.CalledProcessError(code, command, output=output, stderr=text)
    value = audit.diagnostic(error)
    assert value["error_class"] == "BUILD_TOOL"
    assert set(value) == {"stage", "error_class", "source_line", "counts"}
    assert value["counts"] == {}
    assert "private" not in json.dumps(value)
    assert "https://" not in json.dumps(value)


def test_gradle_failure_diagnostic_main_retains_source_line_and_no_tool_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    import subprocess

    private = "synthetic private payload https://example.invalid/private"

    def failure(*args: Any, **kwargs: Any) -> Any:
        raise subprocess.CalledProcessError(
            1,
            GRADLE_INSPECTION_COMMAND,
            output=private,
            stderr=gradle_failure_fixture("unsupported runtime component"),
        )

    monkeypatch.setattr("scripts.app_notification_audit.subprocess.run", failure)
    audit.mark("android-gradle-inspection")
    with pytest.raises(subprocess.CalledProcessError) as caught:
        audit.run(GRADLE_INSPECTION_COMMAND, tmp_path)
    value = audit.diagnostic(caught.value)
    assert value["error_class"] == "GRADLE_COMPONENT_UNSUPPORTED"
    assert 0 < value["source_line"] < 10_000
    assert private not in json.dumps(value)
    assert capsys.readouterr().out == ""
    assert capsys.readouterr().err == ""


GRADLE_FAILURE_PHASES = {
    "DEBUG_CONFIGURATION": "android-gradle-debug-configuration",
    "DEBUG_RESOLUTION": "android-gradle-debug-resolution",
    "DEBUG_COMPONENTS": "android-gradle-debug-components",
    "DEBUG_ARTIFACTS": "android-gradle-debug-artifacts",
    "RELEASE_CONFIGURATION": "android-gradle-release-configuration",
    "RELEASE_RESOLUTION": "android-gradle-release-resolution",
    "RELEASE_COMPONENTS": "android-gradle-release-components",
    "RELEASE_ARTIFACTS": "android-gradle-release-artifacts",
    "OUTPUT": "android-gradle-output",
}


@pytest.mark.parametrize("phase", list(GRADLE_FAILURE_PHASES))
def test_gradle_task_marker_supplies_only_fixed_fault_phase(phase: str) -> None:
    import subprocess

    audit.mark("android-gradle-inspection")
    error = subprocess.CalledProcessError(
        1,
        GRADLE_INSPECTION_COMMAND,
        stderr="GSIP_RUNTIME_FAILURE_V1|" + phase + "|UNKNOWN\n",
    )
    value = audit.diagnostic(error)
    assert value["stage"] == GRADLE_FAILURE_PHASES[phase]
    assert value["error_class"] == "BUILD_TOOL"
    assert set(value) == {"stage", "error_class", "source_line", "counts"}
    assert value["counts"] == {}


@pytest.mark.parametrize(
    ("cause", "expected"),
    [
        ("CONFIGURATION_MISSING", "GRADLE_CONFIGURATION_MISSING"),
        ("DEPENDENCY_UNRESOLVED", "GRADLE_DEPENDENCY_UNRESOLVED"),
        ("API_PROPERTY", "GRADLE_INSPECTION_PROPERTY"),
        ("API_METHOD", "GRADLE_INSPECTION_METHOD"),
        ("FILE_MISSING", "GRADLE_RUNTIME_FILE_MISSING"),
        ("NETWORK", "GRADLE_DEPENDENCY_NETWORK"),
        ("INVALID_ARGUMENT", "GRADLE_INVALID_ARGUMENT"),
        ("NULL_VALUE", "GRADLE_NULL_VALUE"),
        ("TYPE_MISMATCH", "GRADLE_TYPE_MISMATCH"),
        ("ILLEGAL_STATE", "GRADLE_ILLEGAL_STATE"),
    ],
)
def test_gradle_task_marker_supplies_only_fixed_public_cause(cause: str, expected: str) -> None:
    import subprocess

    audit.mark("android-gradle-inspection")
    error = subprocess.CalledProcessError(
        1,
        GRADLE_INSPECTION_COMMAND,
        stderr="GSIP_RUNTIME_FAILURE_V1|DEBUG_RESOLUTION|" + cause + "\n",
    )
    value = audit.diagnostic(error)
    assert value["stage"] == "android-gradle-debug-resolution"
    assert value["error_class"] == expected
    assert set(value) == {"stage", "error_class", "source_line", "counts"}


@pytest.mark.parametrize(
    "defect",
    [
        "duplicate",
        "duplicate_streams",
        "unknown_phase",
        "unknown_cause",
        "private_extra",
        "prefix",
        "timestamp",
        "space",
        "lowercase",
        "missing_field",
        "extra_field",
        "embedded",
        "unicode",
        "control",
        "oversized",
        "unknown_version",
        "wrong_command",
        "wrong_stage",
        "malformed_with_legacy",
        "ambiguous_with_legacy",
        "absent",
    ],
)
def test_gradle_task_marker_refuses_malformed_ambiguous_and_private_context(defect: str) -> None:
    import subprocess

    audit.mark("android-gradle-inspection")
    command = list(GRADLE_INSPECTION_COMMAND)
    marker = "GSIP_RUNTIME_FAILURE_V1|DEBUG_COMPONENTS|API_PROPERTY\n"
    text = marker
    output = ""
    if defect == "duplicate":
        text += marker
    elif defect == "duplicate_streams":
        output = marker
    elif defect == "unknown_phase":
        text = marker.replace("DEBUG_COMPONENTS", "SYNTHETIC_PRIVATE")
    elif defect == "unknown_cause":
        text = marker.replace("API_PROPERTY", "SYNTHETIC_PRIVATE")
    elif defect == "private_extra":
        text = marker.rstrip() + "|synthetic private payload\n"
    elif defect == "prefix":
        text = "synthetic private prefix" + marker
    elif defect == "timestamp":
        text = "2026-01-01T00:00:00Z " + marker
    elif defect == "space":
        text = marker.replace("|API_PROPERTY", "| API_PROPERTY")
    elif defect == "lowercase":
        text = marker.lower()
    elif defect == "missing_field":
        text = "GSIP_RUNTIME_FAILURE_V1|DEBUG_COMPONENTS\n"
    elif defect == "extra_field":
        text = marker.rstrip() + "|UNKNOWN\n"
    elif defect == "embedded":
        text = "synthetic private " + marker + "synthetic private"
    elif defect == "unicode":
        text = marker.replace("API_PROPERTY", "API_PROPΕRTY")
    elif defect == "control":
        text += "\x00"
    elif defect == "oversized":
        text += "x" * audit.MAX_DIAGNOSTIC_BYTES
    elif defect == "unknown_version":
        text = marker.replace("_V1", "_V2")
    elif defect == "wrong_command":
        command[5] = ":app:privateTask"
    elif defect == "wrong_stage":
        audit.mark("android-dependency-trees")
    elif defect == "malformed_with_legacy":
        text = (
            marker.rstrip() + "|private\n" + gradle_failure_fixture("unsupported runtime component")
        )
    elif defect == "ambiguous_with_legacy":
        text += marker + gradle_failure_fixture("unsupported runtime component")
    elif defect == "absent":
        text = "synthetic private failure payload"
    error = subprocess.CalledProcessError(1, command, output=output, stderr=text)
    value = audit.diagnostic(error)
    assert value["stage"] in {"android-gradle-inspection", "android-dependency-trees"}
    assert value["error_class"] == "BUILD_TOOL"
    assert set(value) == {"stage", "error_class", "source_line", "counts"}
    assert value["counts"] == {}
    assert "private" not in json.dumps(value)


def test_gradle_task_marker_can_report_known_unknown_fallback() -> None:
    import subprocess

    audit.mark("android-gradle-inspection")
    error = subprocess.CalledProcessError(
        1, GRADLE_INSPECTION_COMMAND, stderr="GSIP_RUNTIME_FAILURE_V1|UNKNOWN|UNKNOWN\n"
    )
    value = audit.diagnostic(error)
    assert value["stage"] == "android-gradle-inspection"
    assert value["error_class"] == "BUILD_TOOL"


def test_gradle_emitter_preserves_validation_and_exact_original_exception() -> None:
    task = audit.GRADLE_TASK
    assert "['debugRuntimeClasspath','releaseRuntimeClasspath']" in task
    assert task.count("config.resolvedConfiguration.rethrowFailure()") == 1
    assert task.count("config.incoming.resolutionResult.allComponents.each") == 1
    assert task.count("config.resolvedConfiguration.resolvedArtifacts.collect") == 1
    assert task.count("throw new GradleException('unsupported runtime component')") == 1
    assert task.count("throw new GradleException('unsupported runtime artifact')") == 1
    assert task.count("output.text = JsonOutput.toJson([views:views])") == 1
    assert "catch (Throwable failure)" in task
    assert "try { gsipEmitFault(phase, failure) } catch (Throwable ignored) {}" in task
    assert "throw failure" in task
    assert "depth < 16 && seen.add(current)" in task
    assert "current == null && labels.size() == 1" in task
    assert "new IdentityHashMap()" in task
    assert "System.err.println('GSIP_RUNTIME_FAILURE_V1|' + safePhase + '|' + cause)" in task
    assert "getMessage" not in task
    assert "printStackTrace" not in task
    assert "System.getenv" not in task
    assert "failure.toString" not in task


@pytest.mark.parametrize("case", ["unknown", "overflow", "pretask"])
def test_gradle_context_main_exposes_fixed_origin_and_preserves_failure(
    case: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    import subprocess

    private = "synthetic private payload https://example.invalid/private"
    stderr = private
    expected = (
        "GSIP_GRADLE_CONTEXT_V1|COMMAND_VALID|TEXT_VALID|TEXT_VALID|"
        "WITHIN_BOUND|ABSENT|ABSENT|UNKNOWN"
    )
    if case == "overflow":
        stderr += "x" * audit.MAX_DIAGNOSTIC_BYTES
        expected = (
            "GSIP_GRADLE_CONTEXT_V1|COMMAND_VALID|TEXT_VALID|SIZE_REJECTED|"
            "UNINSPECTED|UNINSPECTED|UNINSPECTED|UNINSPECTED"
        )
    elif case == "pretask":
        stderr = gradle_failure_fixture(private).replace(
            "Execution failed for task ':app:gsipRuntimeEvidence'.",
            "A problem occurred evaluating initialization script.",
        )
        expected = (
            "GSIP_GRADLE_CONTEXT_V1|COMMAND_VALID|TEXT_VALID|TEXT_VALID|"
            "WITHIN_BOUND|ABSENT|SINGLE|INIT_EVALUATION"
        )
    failure = subprocess.CalledProcessError(
        1, GRADLE_INSPECTION_COMMAND, output=private, stderr=stderr
    )

    def fail(*args: Any, **kwargs: Any) -> None:
        raise failure

    def collect(*args: Any) -> None:
        audit.mark("android-gradle-inspection")
        audit.run(GRADLE_INSPECTION_COMMAND, tmp_path)

    monkeypatch.setattr("scripts.app_notification_audit.subprocess.run", fail)
    monkeypatch.setattr(audit, "collect_android", collect)
    assert (
        audit.main(
            [
                "android",
                str(tmp_path),
                str(tmp_path),
                str(tmp_path / "out.json"),
                str(tmp_path / "key"),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert expected in captured.err.splitlines()
    assert (
        sum(line.startswith("GSIP_GRADLE_CONTEXT_V1|") for line in captured.err.splitlines()) == 1
    )
    diagnostic = json.loads(captured.err.split("native-audit: diagnostic ", 1)[1])
    assert set(diagnostic) == {"stage", "error_class", "source_line", "counts"}
    assert diagnostic["stage"] == "android-gradle-inspection"
    assert diagnostic["error_class"] == "BUILD_TOOL"
    assert 0 < diagnostic["source_line"] < 10_000
    assert diagnostic["counts"] == {}
    assert private not in captured.err
    assert str(tmp_path) not in captured.err
    assert "https://" not in captured.err
    assert captured.out == ""
    assert failure.__traceback__ is not None


@pytest.mark.parametrize(
    ("case", "stdout_state", "stderr_state", "combined", "marker", "structure", "framing"),
    [
        ("missing", "MISSING", "MISSING", "WITHIN_BOUND", "ABSENT", "ABSENT", "UNKNOWN"),
        ("bytes", "BYTES_VALID", "TEXT_VALID", "WITHIN_BOUND", "ABSENT", "ABSENT", "UNKNOWN"),
        ("private", "TEXT_VALID", "TEXT_VALID", "WITHIN_BOUND", "ABSENT", "ABSENT", "UNKNOWN"),
        (
            "type",
            "TYPE_REJECTED",
            "MISSING",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
        ),
        (
            "bool",
            "TYPE_REJECTED",
            "MISSING",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
        ),
        (
            "raw_size",
            "SIZE_REJECTED",
            "MISSING",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
        ),
        (
            "encoded_size",
            "SIZE_REJECTED",
            "MISSING",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
        ),
        (
            "combined_size",
            "TEXT_VALID",
            "TEXT_VALID",
            "SIZE_REJECTED",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
        ),
        (
            "bad_utf8",
            "UTF8_REJECTED",
            "MISSING",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
        ),
        (
            "surrogate",
            "UTF8_REJECTED",
            "MISSING",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
        ),
        (
            "control",
            "CONTROL_REJECTED",
            "MISSING",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
        ),
        ("valid_marker", "MISSING", "TEXT_VALID", "WITHIN_BOUND", "VALID", "ABSENT", "UNKNOWN"),
        ("invalid_marker", "MISSING", "TEXT_VALID", "WITHIN_BOUND", "INVALID", "ABSENT", "UNKNOWN"),
        (
            "duplicate_marker",
            "MISSING",
            "TEXT_VALID",
            "WITHIN_BOUND",
            "INVALID",
            "ABSENT",
            "UNKNOWN",
        ),
        (
            "marker_control",
            "MISSING",
            "CONTROL_REJECTED",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
            "UNINSPECTED",
        ),
        (
            "malformed_structure",
            "MISSING",
            "TEXT_VALID",
            "WITHIN_BOUND",
            "ABSENT",
            "MALFORMED",
            "UNKNOWN",
        ),
        (
            "ambiguous_structure",
            "MISSING",
            "TEXT_VALID",
            "WITHIN_BOUND",
            "ABSENT",
            "MULTIPLE",
            "AMBIGUOUS",
        ),
        (
            "partial_structure",
            "MISSING",
            "TEXT_VALID",
            "WITHIN_BOUND",
            "ABSENT",
            "MULTIPLE",
            "AMBIGUOUS",
        ),
    ],
)
def test_gradle_context_fields_are_bounded_typed_and_fixed(
    case: str,
    stdout_state: str,
    stderr_state: str,
    combined: str,
    marker: str,
    structure: str,
    framing: str,
) -> None:
    import subprocess

    audit.mark("android-gradle-inspection")
    stdout: Any = None
    stderr: Any = None
    if case == "bytes":
        stdout = b"synthetic private bytes"
        stderr = "synthetic private text"
    elif case == "private":
        stdout = "synthetic private /private/payload https://example.invalid"
        stderr = "synthetic private failure"
    elif case == "type":

        class PrivatePayload:
            def __str__(self) -> str:
                pytest.fail("context must not stringify private payload")

        stdout = PrivatePayload()
    elif case == "bool":
        stdout = True
    elif case == "raw_size":
        stdout = "x" * (audit.MAX_DIAGNOSTIC_BYTES + 1)
    elif case == "encoded_size":
        stdout = "é" * audit.MAX_DIAGNOSTIC_BYTES
    elif case == "combined_size":
        stdout = "x" * audit.MAX_DIAGNOSTIC_BYTES
        stderr = "x"
    elif case == "bad_utf8":
        stdout = b"\xff"
    elif case == "surrogate":
        stdout = "\ud800"
    elif case == "control":
        stdout = "\x1b[31msynthetic private"
    elif case == "valid_marker":
        stderr = "GSIP_RUNTIME_FAILURE_V1|DEBUG_COMPONENTS|UNKNOWN\n"
    elif case == "invalid_marker":
        stderr = "GSIP_RUNTIME_FAILURE_V1|synthetic private|UNKNOWN\n"
    elif case == "duplicate_marker":
        stderr = "GSIP_RUNTIME_FAILURE_V1|DEBUG_COMPONENTS|UNKNOWN\n" * 2
    elif case == "marker_control":
        stderr = "GSIP_RUNTIME_FAILURE_V1|DEBUG_COMPONENTS|UNKNOWN\n\x00"
    elif case == "malformed_structure":
        stderr = "FAILURE: Build failed with an exception.\n* What went wrong:\nsynthetic private"
    elif case == "ambiguous_structure":
        first = gradle_failure_fixture("synthetic private").replace(
            "Execution failed for task ':app:gsipRuntimeEvidence'.",
            "A problem occurred evaluating initialization script.",
        )
        second = gradle_failure_fixture("synthetic private").replace(
            "Execution failed for task ':app:gsipRuntimeEvidence'.",
            "A problem occurred evaluating settings 'synthetic'.",
        )
        stderr = first + second
    elif case == "partial_structure":
        known = gradle_failure_fixture("synthetic private").replace(
            "Execution failed for task ':app:gsipRuntimeEvidence'.",
            "A problem occurred evaluating initialization script.",
        )
        unknown = gradle_failure_fixture("synthetic private").replace(
            "Execution failed for task ':app:gsipRuntimeEvidence'.", "synthetic private reason"
        )
        stderr = known + unknown
    error = subprocess.CalledProcessError(
        1, GRADLE_INSPECTION_COMMAND, output=stdout, stderr=stderr
    )
    expected = "|".join(
        (
            "GSIP_GRADLE_CONTEXT_V1",
            "COMMAND_VALID",
            stdout_state,
            stderr_state,
            combined,
            marker,
            structure,
            framing,
        )
    )
    before = audit.diagnostic(error)
    assert audit.gradle_failure_context(error) == expected
    assert audit.diagnostic(error) == before
    assert "private" not in expected
    assert "https://" not in expected
    assert len(expected.split("|")) == 8
    assert len(expected) <= 200


@pytest.mark.parametrize(
    ("reason", "category"),
    [
        ("Could not compile initialization script 'synthetic-private'.", "INIT_COMPILE"),
        ("A problem occurred evaluating initialization script.", "INIT_EVALUATION"),
        ("A problem occurred evaluating settings 'synthetic-private'.", "SETTINGS_EVALUATION"),
        ("Could not compile settings file 'synthetic-private'.", "SETTINGS_COMPILE"),
        ("Could not compile build file 'synthetic-private'.", "PROJECT_COMPILE"),
        ("A problem occurred evaluating root project 'synthetic-private'.", "PROJECT_EVALUATION"),
        ("A problem occurred evaluating project ':synthetic-private'.", "PROJECT_EVALUATION"),
        (
            "A problem occurred configuring root project 'synthetic-private'.",
            "PROJECT_CONFIGURATION",
        ),
        ("A problem occurred configuring project ':synthetic-private'.", "PROJECT_CONFIGURATION"),
        ("Task 'gsipRuntimeEvidence' not found in project ':app'.", "TASK_SELECTION"),
        ("Execution failed for task ':app:gsipRuntimeEvidence'.", "TASK_EXECUTION"),
        (
            "Could not resolve all files for configuration 'synthetic-private'.",
            "DEPENDENCY_RESOLUTION",
        ),
        (
            "Could not resolve all artifacts for configuration 'synthetic-private'.",
            "DEPENDENCY_RESOLUTION",
        ),
    ],
)
def test_gradle_context_structured_category_never_copies_input_values(
    reason: str, category: str
) -> None:
    import subprocess

    audit.mark("android-gradle-inspection")
    text = gradle_failure_fixture("synthetic-private-failure").replace(
        "Execution failed for task ':app:gsipRuntimeEvidence'.", reason
    )
    error = subprocess.CalledProcessError(1, GRADLE_INSPECTION_COMMAND, stderr=text)
    context = audit.gradle_failure_context(error)
    assert context is not None
    assert context.endswith("|ABSENT|SINGLE|" + category)
    assert "synthetic-private" not in context


@pytest.mark.parametrize(
    "case", ["wrong_stage", "wrong_command", "noninteger_code", "unexpected_error"]
)
def test_gradle_context_outside_scope_has_no_supplemental_line(case: str) -> None:
    import subprocess

    audit.mark("android-gradle-inspection")
    command = list(GRADLE_INSPECTION_COMMAND)
    code: Any = 1
    if case == "wrong_stage":
        audit.mark("ios-resolution")
    elif case == "wrong_command":
        command[5] = ":app:synthetic-private"
    elif case == "noninteger_code":
        code = True
    error: Any = subprocess.CalledProcessError(code, command, stderr="synthetic private")
    if case == "unexpected_error":
        error = ValueError("synthetic private")
    assert audit.gradle_failure_context(error) is None


@pytest.mark.parametrize(("case", "expected"), [
    ("valid", "GSIP_FIXED_FAULT_V1|VALID|RELEASE_CONFIGURATION|CONFIGURATION_MISSING"),
    ("absent", "GSIP_FIXED_FAULT_V1|UNKNOWN"),
    ("setup", "GSIP_FIXED_FAULT_V1|VALID|TASK_SETUP|UNKNOWN"),
])
def test_fixed_fault_channel_survives_oversized_stderr_without_relaxing_it(
    case: str, expected: str, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], tmp_path: Path,
) -> None:
    import subprocess

    errors: list[subprocess.CalledProcessError] = []
    def fake_run(args: list[str], *unused: Any) -> str:
        if ":app:gsipRuntimeEvidence" not in args:
            return "+--- org.synthetic:public:1.0"
        graph = Path(args[-1].removeprefix("-PgsipEvidenceOutput="))
        directory = graph.with_name(graph.name + ".faults")
        directory.mkdir(exist_ok=True)
        if case != "absent":
            payload = {"schema": "gsip-fixed-fault-v1", "phase": "RELEASE_CONFIGURATION",
                       "cause": "CONFIGURATION_MISSING"}
            if case == "setup":
                payload.update(phase="TASK_SETUP", cause="UNKNOWN")
            (directory / "fault-0.json").write_text(json.dumps(payload))
        error = subprocess.CalledProcessError(
            1, args, output="synthetic private stdout",
            stderr="synthetic private oversized stderr " + "x" * audit.MAX_DIAGNOSTIC_BYTES,
        )
        errors.append(error)
        raise error
    monkeypatch.setattr(audit, "run", fake_run)
    target = tmp_path / "out.json"
    assert (
        audit.main(["android", str(tmp_path), str(tmp_path), str(target), str(tmp_path / "key")])
        == 1
    )
    captured = capsys.readouterr()
    assert expected in captured.err.splitlines()
    assert len(errors) == 1 and errors[0].returncode == 1
    assert not target.exists()
    assert "synthetic private" not in captured.err
    assert str(tmp_path) not in captured.err
    assert "SIZE_REJECTED|UNINSPECTED" in captured.err
    diagnostic = json.loads(captured.err.split("native-audit: diagnostic ", 1)[1])
    assert set(diagnostic) == {"stage", "error_class", "source_line", "counts"}
    assert diagnostic["error_class"] == "BUILD_TOOL"
    assert diagnostic["stage"] == "android-gradle-inspection"
    assert diagnostic["counts"] == {}
    assert captured.out == ""


@pytest.mark.parametrize("defect", [
    "absent", "multiple", "foreign_name", "directory", "fifo", "symlink", "hardlink",
    "empty", "oversize", "duplicate", "extra", "phase", "cause", "schema", "type", "nan",
])
def test_fixed_fault_channel_refuses_untrusted_receipts(defect: str, tmp_path: Path) -> None:
    directory = tmp_path / "resolved.json.faults"
    directory.mkdir()
    receipt = directory / "fault-0.json"
    payload: dict[str, Any] = {
        "schema": "gsip-fixed-fault-v1", "phase": "RELEASE_CONFIGURATION",
        "cause": "CONFIGURATION_MISSING",
    }
    if defect == "absent":
        assert audit.read_fixed_fault(directory, tmp_path) is None
        return
    if defect == "extra":
        payload["private"] = "synthetic private payload"
    elif defect in {"phase", "cause", "schema"}:
        payload[defect] = "synthetic private payload"
    elif defect == "type":
        payload["phase"] = True
    elif defect == "nan":
        payload["cause"] = float("nan")
    raw = json.dumps(payload)
    if defect == "duplicate":
        raw = raw.replace('"schema":', '"schema":"gsip-fixed-fault-v1","schema":', 1)
    elif defect == "empty":
        raw = ""
    elif defect == "oversize":
        raw += " " * audit.MAX_FIXED_FAULT_BYTES
    receipt.write_text(raw)
    if defect == "multiple":
        (directory / "fault-1.json").write_text(raw)
    elif defect == "foreign_name":
        receipt.rename(directory / "private.json")
    elif defect == "directory":
        receipt.unlink()
        receipt.mkdir()
    elif defect == "fifo":
        receipt.unlink()
        os.mkfifo(receipt)
    elif defect == "symlink":
        source = tmp_path / "elsewhere.json"
        receipt.rename(source)
        receipt.symlink_to(source)
    elif defect == "hardlink":
        os.link(receipt, tmp_path / "elsewhere.json")
    assert audit.read_fixed_fault(directory, tmp_path) is None


@pytest.mark.parametrize("defect", ["swapped", "command", "returncode", "stage", "reset"])
def test_fixed_fault_lease_is_bound_to_original_failure(
    defect: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import subprocess

    directory = tmp_path / "resolved.json.faults"
    directory.mkdir()
    (directory / "fault-0.json").write_text(json.dumps({
        "schema": "gsip-fixed-fault-v1", "phase": "RELEASE_CONFIGURATION",
        "cause": "CONFIGURATION_MISSING",
    }))
    command = list(GRADLE_INSPECTION_COMMAND)
    error = subprocess.CalledProcessError(1, command, stderr="private synthetic payload")
    audit.mark("android-gradle-inspection")
    audit.lease_fixed_fault(error, command, directory, tmp_path)
    assert audit.fixed_fault_diagnostic(error) == (
        "GSIP_FIXED_FAULT_V1|VALID|RELEASE_CONFIGURATION|CONFIGURATION_MISSING"
    )
    if defect == "swapped":
        error = subprocess.CalledProcessError(1, command, stderr="private synthetic payload")
    elif defect == "command":
        error.cmd = [*command[:-1], "-PgsipEvidenceOutput=/synthetic/another.json"]
    elif defect == "returncode":
        error.returncode = 2
    elif defect == "stage":
        audit.mark("android-build-environment")
    else:
        def stale_failure(*unused: Any) -> None:
            audit.mark("android-gradle-inspection")
            raise error
        monkeypatch.setattr(audit, "collect_android", stale_failure)
        assert audit.main([
            "android", str(tmp_path), str(tmp_path), str(tmp_path / "out.json"),
            str(tmp_path / "key"),
        ]) == 1
        captured = capsys.readouterr()
        assert "GSIP_FIXED_FAULT_V1|UNKNOWN" in captured.err.splitlines()
        assert "GSIP_FIXED_FAULT_V1|VALID|" not in captured.err
        assert "private synthetic payload" not in captured.err
    assert audit.fixed_fault_diagnostic(error) == (
        None if defect == "stage" else "GSIP_FIXED_FAULT_V1|UNKNOWN"
    )
    audit.reset_fixed_fault()


def test_fixed_fault_run_rethrows_original_error_and_resets_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import subprocess

    errors = []
    def fail(args: list[str], *unused: Any) -> str:
        if ":app:gsipRuntimeEvidence" not in args:
            return "+--- org.synthetic:public:1.0"
        graph = Path(args[-1].removeprefix("-PgsipEvidenceOutput="))
        (graph.with_name(graph.name + ".faults") / "fault-0.json").write_text(json.dumps({
            "schema": "gsip-fixed-fault-v1", "phase": "RELEASE_CONFIGURATION",
            "cause": "CONFIGURATION_MISSING",
        }))
        error = subprocess.CalledProcessError(1, args, stderr="private synthetic payload")
        errors.append(error)
        raise error
    monkeypatch.setattr(audit, "run", fail)
    with pytest.raises(subprocess.CalledProcessError) as caught:
        audit.collect_android(tmp_path, tmp_path, tmp_path / "output.json", tmp_path / "key")
    assert caught.value is errors[0]
    fixed = audit.fixed_fault_diagnostic(caught.value)
    assert fixed is not None and fixed.startswith("GSIP_FIXED_FAULT_V1|VALID|")
    def early_failure(*unused: Any) -> str:
        raise caught.value
    monkeypatch.setattr(audit, "run", early_failure)
    with pytest.raises(subprocess.CalledProcessError):
        audit.collect_android(tmp_path, tmp_path, tmp_path / "output.json", tmp_path / "key")
    audit.mark("android-gradle-inspection")
    assert audit.fixed_fault_diagnostic(caught.value) == "GSIP_FIXED_FAULT_V1|UNKNOWN"
    audit.reset_fixed_fault()


def gradle_producer_fixture(root: Path, mode: str) -> None:
    """Offline built-in Java projects; transforms consume real ZIP contents."""
    root.mkdir()
    names = ["app", "library", "other-library"] + (["foreign"] if mode == "foreign" else [])
    (root / "settings.gradle").write_text(
        "rootProject.name='synthetic-producer-proof'\ngradle.startParameter.offline=true\n"
        + "include " + ",".join(repr(":" + name) for name in names) + "\n"
    )
    (root / "build.gradle").write_text(
        "allprojects { repositories { maven { url=uri(rootProject.file('local-maven')) } } }\n"
    )
    for name in names:
        (root / name).mkdir()
        if name != "app":
            (root / name / "build.gradle").write_text("plugins { id 'java-library' }\n")
    module = root / "local-maven" / COORD[0].replace(".", "/") / COORD[1] / COORD[2]
    module.mkdir(parents=True)
    (module / f"{COORD[1]}-{COORD[2]}.pom").write_bytes(pom())
    zipped(module / f"{COORD[1]}-{COORD[2]}.jar")
    configurations = ["debugRuntimeClasspath"]
    if mode != "missing_configuration":
        configurations.append("releaseRuntimeClasspath")
    declarations = "\n".join(
        name + " { canBeConsumed=false; canBeResolved=true }" for name in configurations
    )
    dependencies = "\n".join(
        name + " project(':" + ("library" if name.startswith("debug") else "other-library")
        + "')\n" + name + " '" + ":".join(COORD) + "'" for name in configurations
    )
    if mode == "foreign":
        dependencies += "\ndebugRuntimeClasspath project(':foreign')"
    attributes = "\n".join(
        "configurations." + name + ".attributes.attribute(\n"
        + "    ArtifactTypeDefinition.ARTIFACT_TYPE_ATTRIBUTE, 'verified-jar')"
        for name in configurations
    )
    (root / "app/build.gradle").write_text(
        """import org.gradle.api.artifacts.transform.TransformAction
import org.gradle.api.artifacts.transform.TransformOutputs
import org.gradle.api.artifacts.transform.TransformParameters
import org.gradle.api.artifacts.transform.InputArtifact
import org.gradle.api.artifacts.type.ArtifactTypeDefinition
import org.gradle.api.file.FileSystemLocation
import org.gradle.api.provider.Provider
plugins { id 'java' }
abstract class RequireJarContents implements TransformAction<TransformParameters.None> {
    @InputArtifact abstract Provider<FileSystemLocation> getInputArtifact()
    void transform(TransformOutputs outputs) {
        new java.util.zip.ZipFile(inputArtifact.get().asFile).close()
        System.out.println('GSIP_SYNTHETIC_TRANSFORM_EXECUTED')
        outputs.file(inputArtifact.get().asFile)
    }
}
""" + "configurations {\n" + declarations + "\n}\ndependencies {\n" + dependencies
        + """
    registerTransform(RequireJarContents) {
        from.attribute(ArtifactTypeDefinition.ARTIFACT_TYPE_ATTRIBUTE, 'jar')
        to.attribute(ArtifactTypeDefinition.ARTIFACT_TYPE_ATTRIBUTE, 'verified-jar')
    }
}
""" + attributes + "\n"
    )
    if mode == "missing_producer":
        with (root / "library/build.gradle").open("a") as stream:
            stream.write("tasks.named('jar') { enabled=false }\n")
    elif mode == "producer_failure":
        with (root / "library/build.gradle").open("a") as stream:
            stream.write(
                "tasks.named('jar') { doFirst { "
                "throw new IllegalStateException('synthetic-producer-failure') } }\n"
            )


@pytest.mark.parametrize("mode", [
    "success", "no_debug_dependency", "no_release_dependency", "missing_producer",
    "producer_failure", "missing_configuration", "foreign",
])
def test_real_gradle_runtime_producers_precede_content_transforms(
    mode: str, tmp_path: Path, graph: tuple[dict[str, Any], Path, Path, Path]
) -> None:
    """Opt in with a verified Gradle 8.14.3 home; no SDK or remote dependency is used."""
    import subprocess

    selected = os.environ.get("GSIP_TEST_GRADLE_HOME")
    if not selected:
        pytest.skip("real Gradle producer control requires explicit verified tool home")
    home = Path(selected)
    if not home.is_absolute() or ".." in home.parts or not (home / "bin/gradle").is_file():
        pytest.fail("invalid explicit Gradle tool home")
    project = tmp_path / "producer-fixture"
    gradle_producer_fixture(project, mode)
    task = audit.GRADLE_TASK
    if mode in {"no_debug_dependency", "no_release_dependency"}:
        configuration = (
            "releaseRuntimeClasspath" if mode == "no_debug_dependency"
            else "debugRuntimeClasspath"
        )
        task = task.replace(
            "['debugRuntimeClasspath','releaseRuntimeClasspath'].collect { name ->\n"
            "                app.configurations.getByName(name).buildDependencies",
            "['" + configuration + "'].collect { name ->\n"
            "                app.configurations.getByName(name).buildDependencies",
            1,
        )
    inspection = tmp_path / "inspection.gradle"
    inspection.write_text(task)
    output = tmp_path / "resolved.json"
    output.with_name(output.name + ".faults").mkdir(mode=0o700)
    environment = dict(os.environ, GRADLE_USER_HOME=str(tmp_path / "gradle-user-home"))
    completed = subprocess.run(  # noqa: S603 - explicit verified opt-in tool, owned offline fixture
        [str(home / "bin/gradle"), "--no-daemon", "--console=plain", "-I", str(inspection),
         ":app:gsipRuntimeEvidence", "-PgsipEvidenceOutput=" + str(output)],
        cwd=project, env=environment, capture_output=True, timeout=120,
    )
    if len(completed.stdout) + len(completed.stderr) > 2_000_000:
        pytest.fail("synthetic Gradle control exceeded fixed output bound")
    succeeds = mode in {"success", "foreign"}
    if (completed.returncode == 0) != succeeds or output.exists() != succeeds:
        pytest.fail("real Gradle producer control has incorrect exit or graph status")
    if succeeds:
        data = audit.decoded(output.read_bytes())
        assert {view["name"] for view in data["views"]} == {
            "debugRuntimeClasspath", "releaseRuntimeClasspath",
        }
        assert all(Path(item["file"]).is_file() for v in data["views"] for item in v["artifacts"])
        assert b"GSIP_SYNTHETIC_TRANSFORM_EXECUTED" in completed.stdout
        inspection_offset = completed.stdout.find(b"> Task :app:gsipRuntimeEvidence")
        for name in ["library", "other-library"] + (["foreign"] if mode == "foreign" else []):
            offset = completed.stdout.find(("> Task :" + name + ":jar").encode())
            assert 0 <= offset < inspection_offset
        assert [view["projects"] for view in data["views"]] == [
            [":app", ":foreign", ":library"] if mode == "foreign" else [":app", ":library"],
            [":app", ":other-library"],
        ]
        if mode == "foreign":
            licensed, repo, cache, unused = graph
            licensed["views"][0]["projects"].append(":foreign")
            with pytest.raises(audit.AuditError):
                audit.runtime_evidence(licensed, repo, cache, False)
    else:
        assert not (project / "library/build/libs/library.jar").exists() or mode in {
            "no_release_dependency", "missing_configuration",
        }
        if mode in {"no_debug_dependency", "no_release_dependency", "missing_producer"}:
            expected_phase = (
                "RELEASE_ARTIFACTS" if mode == "no_release_dependency" else "DEBUG_ARTIFACTS"
            )
            assert audit.read_fixed_fault(output.with_name(output.name + ".faults"), tmp_path) == (
                expected_phase, "FILE_MISSING",
            )
        elif mode == "producer_failure":
            assert b"> Task :app:gsipRuntimeEvidence" not in completed.stdout
            assert b"> Task :library:jar FAILED" in completed.stdout
        elif mode == "missing_configuration":
            assert (
                b"Configuration with name 'releaseRuntimeClasspath' not found."
                in completed.stderr
            )
    control = {
        "mode": mode,
        "tool_exit_code": completed.returncode,
        "graph_created": output.exists(),
        "graph_sha256": audit.sha(output.read_bytes()) if output.exists() else None,
        "task_sha256": audit.sha(task.encode()),
        "project_jars": {
            name: (project / name / "build/libs" / (name + ".jar")).is_file()
            for name in ["library", "other-library"]
        },
        "stdout_sha256": audit.sha(completed.stdout),
        "stderr_sha256": audit.sha(completed.stderr),
        "stdout_bytes": len(completed.stdout),
        "stderr_bytes": len(completed.stderr),
        "fixed_fault": audit.read_fixed_fault(output.with_name(output.name + ".faults"), tmp_path),
        "raw_tool_output_persisted": False,
        "native_acceptance_claimed": False,
    }
    (tmp_path / "producer-control.json").write_text(json.dumps(control, sort_keys=True) + "\n")


@pytest.mark.parametrize("cause", ["ILLEGAL_STATE", "STACK_OVERFLOW", "OUT_OF_MEMORY"])
def test_fixed_build_failure_channel_keeps_original_cli_status_caps_and_privacy(
    cause: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    import subprocess

    failures = []
    def fail(args: list[str], *unused: Any) -> str:
        if ":app:gsipRuntimeEvidence" not in args:
            return "+--- org.synthetic:public:1.0"
        graph = Path(args[-1].removeprefix("-PgsipEvidenceOutput="))
        (graph.with_name(graph.name + ".faults") / "fault-0.json").write_text(json.dumps({
            "schema": "gsip-fixed-fault-v1", "phase": "BUILD_FAILURE", "cause": cause,
        }))
        error = subprocess.CalledProcessError(
            1, args, output="synthetic private stdout",
            stderr="synthetic private " + "x" * audit.MAX_DIAGNOSTIC_BYTES,
        )
        failures.append(error)
        raise error
    monkeypatch.setattr(audit, "run", fail)
    assert audit.main([
        "android", str(tmp_path), str(tmp_path), str(tmp_path / "output.json"),
        str(tmp_path / "key"),
    ]) == 1
    captured = capsys.readouterr()
    assert "GSIP_FIXED_FAULT_V1|VALID|BUILD_FAILURE|" + cause in captured.err.splitlines()
    assert "SIZE_REJECTED|UNINSPECTED" in captured.err
    diagnostic = json.loads(captured.err.split("native-audit: diagnostic ", 1)[1])
    assert set(diagnostic) == {"stage", "error_class", "source_line", "counts"}
    assert diagnostic["error_class"] == "BUILD_TOOL"
    assert diagnostic["stage"] == "android-gradle-inspection"
    assert diagnostic["counts"] == {}
    assert len(failures) == 1 and failures[0].returncode == 1
    assert failures[0].__traceback__ is not None
    assert not (tmp_path / "output.json").exists()
    assert "synthetic private" not in captured.err and str(tmp_path) not in captured.err
    assert captured.out == ""


@pytest.mark.parametrize("mode", [
    "success", "producer", "stack", "memory", "task", "setup", "configuration",
    "unregistered", "cyclic", "depth", "existing_malformed", "existing_multiple",
])
def test_real_gradle_build_observer_preserves_failure_and_prior_fault(
    mode: str, tmp_path: Path
) -> None:
    """Diagnostic-only callback, synthetic thrown errors; never exhaust memory or stack."""
    import subprocess

    selected = os.environ.get("GSIP_TEST_GRADLE_HOME")
    if not selected:
        pytest.skip("real Gradle observer control requires explicit verified tool home")
    home = Path(selected)
    if not home.is_absolute() or ".." in home.parts or not (home / "bin/gradle").is_file():
        pytest.fail("invalid explicit Gradle tool home")
    fixture_mode = (
        "missing_producer" if mode == "task" else "missing_configuration"
        if mode == "configuration" else "success" if mode in {"success", "setup"}
        else "producer_failure"
    )
    project = tmp_path / "observer-fixture"
    gradle_producer_fixture(project, fixture_mode)
    if fixture_mode == "producer_failure":
        error = {
            "stack": "StackOverflowError", "memory": "OutOfMemoryError",
        }.get(mode, "IllegalStateException")
        path = project / "library/build.gradle"
        path.write_text(path.read_text().replace(
            "new IllegalStateException('synthetic-producer-failure')",
            "new " + error + "('synthetic-private-'+('x'*70000))",
        ))
    task = audit.GRADLE_TASK
    if mode == "setup":
        path = project / "settings.gradle"
        path.write_text(path.read_text().replace("':app',", "", 1))
    elif mode == "unregistered":
        task = "invalid initialization syntax !!!\n" + task
    elif mode in {"cyclic", "depth"}:
        construction = (
            "def other=new IllegalStateException('synthetic-private'); "
            "cause.initCause(other); other.initCause(cause)"
            if mode == "cyclic" else
            "for (int i=0; i<17; i++) { def outer=new IllegalStateException('synthetic-private'); "
            "outer.initCause(cause); cause=outer }"
        )
        task += (
            "\ngradle.projectsEvaluated { "
            "def cause=new IllegalStateException('synthetic-private'); "
            + construction + "; gsipEmitFault('BUILD_FAILURE',cause); "
            + "throw new IllegalStateException('synthetic-private-'+('x'*70000)) }\n"
        )
    inspection = tmp_path / "inspection.gradle"
    inspection.write_text(task)
    graph = tmp_path / "resolved.json"
    directory = graph.with_name(graph.name + ".faults")
    directory.mkdir(mode=0o700)
    before = {}
    if mode in {"existing_malformed", "existing_multiple"}:
        (directory / "fault-0.json").write_text('{"private":"synthetic-private"}')
        if mode == "existing_multiple":
            (directory / "fault-1.json").write_text(json.dumps({
                "schema": "gsip-fixed-fault-v1", "phase": "BUILD_FAILURE", "cause": "UNKNOWN",
            }))
        before = {p.name: audit.sha(p.read_bytes()) for p in directory.iterdir()}
    environment = dict(os.environ, GRADLE_USER_HOME=str(tmp_path / "gradle-user-home"))
    completed = subprocess.run(  # noqa: S603 - explicit verified tool, bounded owned offline fixture
        [str(home / "bin/gradle"), "--no-daemon", "--console=plain", "-I", str(inspection),
         ":app:gsipRuntimeEvidence", "-PgsipEvidenceOutput=" + str(graph)],
        cwd=project, env=environment, capture_output=True, timeout=120,
    )
    if len(completed.stdout) + len(completed.stderr) > 2_000_000:
        pytest.fail("synthetic observer control exceeded fixed output bound")
    if completed.returncode != (0 if mode == "success" else 1):
        pytest.fail("observer changed original Gradle exit status")
    entries = list(directory.iterdir())
    fault = audit.read_fixed_fault(directory, tmp_path)
    if mode == "success":
        assert graph.is_file() and not entries and fault is None
        candidate = graph.read_bytes()
        # Remove only the new callback, keeping identical project/artifact paths and toolchain.
        start = task.index("gradle.buildFinished { result ->\n")
        end = task.index("gradle.projectsEvaluated {", start)
        inspection.write_text(task[:start] + task[end:])
        baseline = subprocess.run(  # noqa: S603 - same verified offline successful fixture
            [str(home / "bin/gradle"), "--no-daemon", "--console=plain", "-I", str(inspection),
             ":app:gsipRuntimeEvidence", "-PgsipEvidenceOutput=" + str(graph)],
            cwd=project, env=environment, capture_output=True, timeout=120,
        )
        if baseline.returncode != 0:
            pytest.fail("successful graph comparison failed")
        assert graph.read_bytes() == candidate and not list(directory.iterdir())
    else:
        assert not graph.exists()
        expected = {
            "producer": ("BUILD_FAILURE", "ILLEGAL_STATE"),
            "stack": ("BUILD_FAILURE", "STACK_OVERFLOW"),
            "memory": ("BUILD_FAILURE", "OUT_OF_MEMORY"),
            "task": ("DEBUG_ARTIFACTS", "FILE_MISSING"),
            "setup": ("TASK_SETUP", "UNKNOWN"),
            "configuration": ("BUILD_FAILURE", "CONFIGURATION_MISSING"),
            "cyclic": ("BUILD_FAILURE", "UNKNOWN"),
            "depth": ("BUILD_FAILURE", "UNKNOWN"),
        }.get(mode)
        assert fault == expected
        assert len(entries) == (2 if mode == "existing_multiple" else 0 if mode == "unregistered"
                                else 1)
        if before:
            assert {p.name: audit.sha(p.read_bytes()) for p in entries} == before
        if expected:
            assert completed.stderr.count(b"GSIP_RUNTIME_FAILURE_V1|") == 1
            assert all(p.stat().st_size <= audit.MAX_FIXED_FAULT_BYTES for p in entries)
            assert all(b"synthetic-private" not in p.read_bytes() for p in entries)
    control = {
        "mode": mode, "original_tool_exit_code": completed.returncode,
        "graph_exists": graph.exists(), "fault": fault, "fault_file_count": len(entries),
        "stdout_bytes": len(completed.stdout), "stderr_bytes": len(completed.stderr),
        "stdout_sha256": audit.sha(completed.stdout), "stderr_sha256": audit.sha(completed.stderr),
        "task_sha256": audit.sha(task.encode()), "raw_streams_persisted": False,
        "native_acceptance_claimed": False,
    }
    (tmp_path / "observer-control.json").write_text(json.dumps(control, sort_keys=True) + "\n")
SPLIT_VIEW_FIXTURE_TEXT = {
    "app/build.gradle": "import org.gradle.api.attributes.Attribute\n"
    "def buildType = Attribute.of('gsip.fixture.buildType', String)\n"
    "['debug','release'].each { variant ->\n"
    "    def runtime = configurations.create(variant + "
    "'RuntimeClasspath') {\n"
    "        canBeConsumed = false\n"
    "        canBeResolved = true\n"
    "        attributes.attribute(buildType, variant)\n"
    "        "
    "attributes.attribute(Attribute.of('com.android.build.api.attributes.AgpVersionAttr', "
    "String), '8.13.0')\n"
    "    }\n"
    "    dependencies.add(runtime.name, project(':library'))\n"
    "}\n"
    "\n"
    "repositories { maven { url = uri(rootProject.file('repo'));\n"
    "metadataSources { gradleMetadata();\n"
    "mavenPom() } } }\n"
    "['debug','release'].each { variant ->\n"
    " def name = variant + 'RuntimeClasspath'\n"
    " dependencies.add(name, 'synthetic.publicview:plain:1.0')\n"
    " dependencies.add(name, 'synthetic.publicview:androidraw:1.0')\n"
    " dependencies.add(name, "
    "dependencies.platform('synthetic.publicview:bom:1.0'))\n"
    " if (findProperty('caseName') == 'emptyLibrary') { "
    "dependencies.add(name, 'synthetic.publicview:empty:1.0') }\n"
    " if (findProperty('caseName') == 'unresolved') { "
    "dependencies.add(name, 'synthetic.publicview:absent:1.0') }\n"
    "}\n",
    "build.gradle": "",
    "library/build.gradle": "import org.gradle.api.artifacts.type.ArtifactTypeDefinition\n"
    "import org.gradle.api.attributes.Attribute\n"
    "def buildType = Attribute.of('gsip.fixture.buildType', "
    "String)\n"
    "['debug','release'].each { variant ->\n"
    "    def classes = tasks.register(variant + 'Classes') {\n"
    "        def output = layout.buildDirectory.file(variant + "
    "'/classes.jar')\n"
    "        outputs.file(output)\n"
    "        doLast { output.get().asFile.parentFile.mkdirs();\n"
    "def zip = new "
    "java.util.zip.ZipOutputStream(output.get().asFile.newOutputStream());\n"
    "zip.putNextEntry(new "
    "java.util.zip.ZipEntry('fixture-variant.txt'));\n"
    "zip.write((variant + '-classes').getBytes('UTF-8'));\n"
    "zip.closeEntry();\n"
    "zip.close() }\n"
    "    }\n"
    "    def resources = tasks.register(variant + 'Resources') {\n"
    "        def output = layout.buildDirectory.file(variant + "
    "'/resources.zip')\n"
    "        outputs.file(output)\n"
    "        doLast { output.get().asFile.parentFile.mkdirs();\n"
    "output.get().asFile.text = variant + '-resources' }\n"
    "    }\n"
    "    configurations.create(variant + 'RuntimeElements') {\n"
    "        canBeConsumed = true\n"
    "        canBeResolved = false\n"
    "        attributes.attribute(buildType, variant)\n"
    "        outgoing.variants.create('classes') {\n"
    "            "
    "attributes.attribute(ArtifactTypeDefinition.ARTIFACT_TYPE_ATTRIBUTE, "
    "'android-classes-jar')\n"
    "            artifact(layout.buildDirectory.file(variant + "
    "'/classes.jar')) { builtBy(classes) }\n"
    "        }\n"
    "        outgoing.variants.create('resources') {\n"
    "            "
    "attributes.attribute(ArtifactTypeDefinition.ARTIFACT_TYPE_ATTRIBUTE, "
    "'android-res')\n"
    "            artifact(layout.buildDirectory.file(variant + "
    "'/resources.zip')) { builtBy(resources) }\n"
    "        }\n"
    "    }\n"
    "}\n",
    "repo/synthetic/publicview/androidraw/1.0/androidraw-1.0.pom": "<project>\n"
    "<modelVersion>4.0.0</modelVersion>\n"
    "<groupId>synthetic.publicview</groupId>\n"
    "<artifactId>androidraw</artifactId>\n"
    "<version>1.0</version>\n"
    "<packaging>aar</packaging>\n"
    "</project>",
    "repo/synthetic/publicview/bom/1.0/bom-1.0.module": "{\n"
    '  "formatVersion": "1.1",\n'
    '  "component": {\n'
    '    "group": '
    '"synthetic.publicview",\n'
    '    "module": "bom",\n'
    '    "version": "1.0"\n'
    "  },\n"
    '  "variants": [\n'
    "    {\n"
    '      "name": '
    '"platformRuntime",\n'
    '      "attributes": {\n'
    '        "org.gradle.category": '
    '"platform",\n'
    '        "org.gradle.usage": '
    '"java-runtime"\n'
    "      },\n"
    '      "dependencyConstraints": '
    "[\n"
    "        {\n"
    '          "group": '
    '"synthetic.publicview",\n'
    '          "module": "plain",\n'
    '          "version": {\n'
    '            "requires": "1.0"\n'
    "          }\n"
    "        }\n"
    "      ]\n"
    "    }\n"
    "  ]\n"
    "}\n",
    "repo/synthetic/publicview/bom/1.0/bom-1.0.pom": "<project>\n"
    "<modelVersion>4.0.0</modelVersion>\n"
    "<groupId>synthetic.publicview</groupId>\n"
    "<artifactId>bom</artifactId>\n"
    "<version>1.0</version>\n"
    "<packaging>pom</packaging>\n"
    "<dependencyManagement>\n"
    "<dependencies>\n"
    "<dependency>\n"
    "<groupId>synthetic.publicview</groupId>\n"
    "<artifactId>plain</artifactId>\n"
    "<version>1.0</version>\n"
    "</dependency>\n"
    "</dependencies>\n"
    "</dependencyManagement>\n"
    "</project>",
    "repo/synthetic/publicview/empty/1.0/empty-1.0.module": "{\n"
    '  "formatVersion": "1.1",\n'
    '  "component": {\n'
    '    "group": '
    '"synthetic.publicview",\n'
    '    "module": "empty",\n'
    '    "version": "1.0"\n'
    "  },\n"
    '  "variants": [\n'
    "    {\n"
    '      "name": "runtime",\n'
    '      "attributes": {\n'
    "        "
    '"org.gradle.category": '
    '"library",\n'
    '        "org.gradle.usage": '
    '"java-runtime"\n'
    "      },\n"
    '      "files": []\n'
    "    }\n"
    "  ]\n"
    "}\n",
    "repo/synthetic/publicview/plain/1.0/plain-1.0.pom": "<project>\n"
    "<modelVersion>4.0.0</modelVersion>\n"
    "<groupId>synthetic.publicview</groupId>\n"
    "<artifactId>plain</artifactId>\n"
    "<version>1.0</version>\n"
    "<packaging>jar</packaging>\n"
    "</project>",
    "settings.gradle": "rootProject.name = 'gsip-public-secondary-variant-fixture'\n"
    "include ':app', ':library'\n",
}


def split_view_fixture(root: Path, mode: str) -> None:
    """Public Gradle secondary variants, local raw JAR/AAR and selected platform only."""
    root.mkdir()
    for relative, text in SPLIT_VIEW_FIXTURE_TEXT.items():
        file = root / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        if mode == "unknown_agp":
            text = text.replace("'8.13.0'", "'99.0.0'")
        if mode == "library_metadata":
            text = text.replace("findProperty('caseName') == 'emptyLibrary'", "true")
        if mode == "unresolved":
            text = text.replace("findProperty('caseName') == 'unresolved'", "true")
        file.write_text(text)
    zipped(root / "repo/synthetic/publicview/plain/1.0/plain-1.0.jar", b"raw jar")
    zipped(root / "repo/synthetic/publicview/androidraw/1.0/androidraw-1.0.aar", b"raw aar")
    if mode == "missing_binary":
        (root / "repo/synthetic/publicview/plain/1.0/plain-1.0.jar").unlink()


@pytest.mark.parametrize(
    "mode",
    [
        "success",
        "unknown_agp",
        "wrong_type",
        "missing_project",
        "omit_module",
        "no_debug_producer",
        "no_release_producer",
        "wrong_variant",
        "library_metadata",
        "missing_binary",
        "unresolved",
    ],
)
def test_real_gradle_split_views_preserve_raw_inputs_and_selected_variants(
    mode: str, tmp_path: Path
) -> None:
    import subprocess

    selected = os.environ.get("GSIP_TEST_GRADLE_HOME")
    if not selected:
        pytest.skip("real split-view control requires explicit verified Gradle tool home")
    home = Path(selected)
    if not home.is_absolute() or ".." in home.parts or not (home / "bin/gradle").is_file():
        pytest.fail("invalid explicit Gradle tool home")
    project = tmp_path / "split-fixture"
    split_view_fixture(project, mode)
    task = audit.GRADLE_TASK
    if mode == "wrong_type":
        task = task.replace("'android-classes-jar')", "'gsip-missing-type')", 1)
    elif mode == "missing_project":
        task = task.replace("it instanceof ProjectComponentIdentifier && it != rootId", "false", 1)
    elif mode == "omit_module":
        task = task.replace(
            "it instanceof ModuleComponentIdentifier }",
            "it instanceof ModuleComponentIdentifier && it.module != 'plain' }",
            1,
        )
    elif mode in {"no_debug_producer", "no_release_producer"}:
        kept = "release" if mode == "no_debug_producer" else "debug"
        task = task.replace(
            "configs.collectMany { config ->",
            "configs.findAll { it.name.startsWith('" + kept + "') }.collectMany { config ->",
            1,
        )
    elif mode == "wrong_variant":
        task = task.replace(
            "'android-classes-jar')",
            "'android-classes-jar')\n                        "
            "attributes.attribute(org.gradle.api.attributes.Attribute.of("
            "'gsip.fixture.buildType', String), 'debug')",
            1,
        )
    inspection = tmp_path / "inspection.gradle"
    inspection.write_text(task)
    output = tmp_path / "resolved.json"
    output.with_name(output.name + ".faults").mkdir(mode=0o700)
    environment = dict(os.environ, GRADLE_USER_HOME=str(tmp_path / "gradle-user-home"))
    completed = subprocess.run(  # noqa: S603 - verified explicit tool and owned offline fixture
        [
            str(home / "bin/gradle"),
            "--no-daemon",
            "--console=plain",
            "-I",
            str(inspection),
            ":app:gsipRuntimeEvidence",
            "-PgsipEvidenceOutput=" + str(output),
        ],
        cwd=project,
        env=environment,
        capture_output=True,
        timeout=120,
    )
    if len(completed.stdout) + len(completed.stderr) > 2_000_000:
        pytest.fail("synthetic split-view control exceeded fixed output bound")
    fails_build = mode in {
        "unknown_agp",
        "wrong_type",
        "missing_project",
        "missing_binary",
        "unresolved",
        "wrong_variant",
    }
    if (completed.returncode != 0) != fails_build or output.exists() == fails_build:
        pytest.fail("split-view control has incorrect fixed exit/graph status")
    if mode == "wrong_variant":
        assert audit.read_fixed_fault(output.with_name(output.name + ".faults"), tmp_path) == (
            "RELEASE_ARTIFACTS", "UNKNOWN",
        )
    data = audit.decoded(output.read_bytes()) if output.exists() else None
    expected_modules = {
        ("synthetic.publicview", name, "1.0") for name in ["plain", "androidraw", "bom"]
    }
    if data is not None:
        assert [view["name"] for view in data["views"]] == [
            "debugRuntimeClasspath",
            "releaseRuntimeClasspath",
        ]
        for view in data["views"]:
            assert expected_modules <= {tuple(v) for v in view["modules"]}
            assert set(view["projects"]) == {":app", ":library"}
            artifacts = view["artifacts"]
            module_artifacts = [v for v in artifacts if v["kind"] == "module"]
            actual_modules = {tuple(v["coordinate"]) for v in module_artifacts}
            assert actual_modules == expected_modules - {("synthetic.publicview", "bom", "1.0")} - (
                {("synthetic.publicview", "plain", "1.0")} if mode == "omit_module" else set()
            )
            for artifact in module_artifacts:
                coordinate = artifact["coordinate"]
                expected = (
                    project
                    / "repo/synthetic/publicview"
                    / coordinate[1]
                    / "1.0"
                    / Path(artifact["file"]).name
                )
                assert Path(artifact["file"]).read_bytes() == expected.read_bytes()
            projects = [v for v in artifacts if v["kind"] == "project"]
            assert len(projects) == 1 and projects[0]["project"] == ":library"
            file = Path(projects[0]["file"])
            missing = (
                mode == "no_debug_producer"
                and view["name"].startswith("debug")
                or mode == "no_release_producer"
                and view["name"].startswith("release")
            )
            assert file.is_file() != missing
            if file.is_file():
                with zipfile.ZipFile(file) as archive:
                    actual = archive.read("fixture-variant.txt")
                variant = "debug" if view["name"].startswith("debug") else "release"
                assert (actual == (variant + "-classes").encode()) != (
                    mode == "wrong_variant" and variant == "release"
                )
        if mode == "success":
            offset = completed.stdout.find(b"> Task :app:gsipRuntimeEvidence")
            for variant in ["debug", "release"]:
                producer = completed.stdout.find(
                    ("> Task :library:" + variant + "Classes").encode()
                )
                assert 0 <= producer < offset
    control = {
        "mode": mode,
        "tool_exit_code": completed.returncode,
        "graph_created": output.exists(),
        "task_sha256": audit.sha(task.encode()),
        "stdout_sha256": audit.sha(completed.stdout),
        "stderr_sha256": audit.sha(completed.stderr),
        "stdout_bytes": len(completed.stdout),
        "stderr_bytes": len(completed.stderr),
        "raw_output_persisted": False,
        "native_acceptance_claimed": False,
    }
    (tmp_path / "split-view-control.json").write_text(json.dumps(control, sort_keys=True) + "\n")


@pytest.mark.parametrize(
    "defect", ["missing_module", "missing_project", "pom_metadata", "jar_metadata"]
)
def test_split_view_sidecar_keeps_existing_full_component_coverage(
    defect: str, tmp_path: Path
) -> None:
    native = complete_native("a" * 40, "b" * 64)
    if defect == "missing_project":
        for row in native["runtime_views"]:
            row["resolved_runtime_inputs"] = [
                v for v in row["resolved_runtime_inputs"] if v.get("project") != ":capacitor-camera"
            ]
    elif defect == "missing_module":
        for row in native["runtime_views"]:
            row["resolved_runtime_inputs"] = [
                v for v in row["resolved_runtime_inputs"] if "coordinate" not in v
            ]
    else:
        coord = ("synthetic.publicview", "metadata", "1.0")
        raw = pom(coord).replace(
            b"</project>",
            (
                "<packaging>"
                + ("pom" if defect == "pom_metadata" else "jar")
                + "</packaging></project>"
            ).encode(),
        )
        cached(tmp_path, coord, raw)
        proof = audit.pom_evidence(coord, tmp_path, False)
        for row in native["runtime_views"]:
            row["selected_modules"].append(
                {"coordinate": list(coord), "pom_license_evidence": proof}
            )
    if defect == "pom_metadata":
        audit.validate_android(native, audit.validate_npm(native["npm_sources"], "a" * 40))
    else:
        with pytest.raises(audit.AuditError):
            audit.validate_android(native, audit.validate_npm(native["npm_sources"], "a" * 40))


# Actual empty AGP 8.13 R output, independently checked against its pinned generator.
# This literal is independent of the maintained expected-class builder.
CORDOVA_EMPTY_R = bytes.fromhex(
    "cafebabe00000034000a010023636170616369746f722f636f72646f76612f616e64726f6964"
    "2f706c7567696e732f520700010100106a6176612f6c616e672f4f626a6563740700030100"
    "063c696e69743e0100032829560c000500060a00040007010004436f646500310002000400"
    "0000000001000200050006000100090000001100010001000000052ab70008b1000000000000"
)
CORDOVA_R_MEMBER = "capacitor/cordova/android/plugins/R.class"


def cordova_output_project(root: Path) -> tuple[Path, list[Path], list[Path]]:
    generated = root / "apps/capture-pwa/android/capacitor-cordova-android-plugins"
    generated.mkdir(parents=True)
    (generated / "build.gradle").write_text(
        'android { namespace "capacitor.cordova.android.plugins" }\n'
    )
    runtime, resources = [], []
    for variant in ("debug", "release"):
        suffix = variant.capitalize()
        classes = generated / (
            f"build/intermediates/runtime_library_classes_jar/{variant}/"
            f"bundleLibRuntimeToJar{suffix}/classes.jar"
        )
        classes.parent.mkdir(parents=True)
        classes.write_bytes(b"PK\x05\x06" + b"\0" * 18)
        resource = generated / (
            f"build/intermediates/compile_r_class_jar/{variant}/generate{suffix}RFile/R.jar"
        )
        resource.parent.mkdir(parents=True)
        with zipfile.ZipFile(resource, "w") as archive:
            archive.writestr(CORDOVA_R_MEMBER, CORDOVA_EMPTY_R)
        runtime.append(classes)
        resources.append(resource)
    return generated, runtime, resources


def test_generated_cordova_outputs_are_proven_empty_not_prebundled(
    graph: tuple[dict[str, Any], Path, Path, Path],
) -> None:
    data, repo, cache, _ = graph
    generated, runtime, resources = cordova_output_project(repo)
    assert len(CORDOVA_EMPTY_R) == 150
    assert audit.sha(CORDOVA_EMPTY_R) == (
        "3bcff37a8da344d813483fecde266705db27eb75c73f85f6de2c85449064a077"
    )
    for index, view in enumerate(data["views"]):
        view["projects"].append(":capacitor-cordova-android-plugins")
        view["artifacts"].append(
            {
                "kind": "project",
                "project": ":capacitor-cordova-android-plugins",
                "file": str(runtime[index]),
            }
        )
    result = audit.runtime_evidence(data, repo, cache, False)
    for index, view in enumerate(result["runtime_views"]):
        assert view["project_sources"][0]["project"] == ":capacitor-cordova-android-plugins"
        binary = view["resolved_runtime_inputs"][-1]
        assert binary["sha256"] == audit.sha(runtime[index].read_bytes())
        assert binary["bytes"] == 22
        assert binary["embedded_license_notice_files"] == []
        with zipfile.ZipFile(resources[index]) as archive:
            assert archive.read(CORDOVA_R_MEMBER) == CORDOVA_EMPTY_R


@pytest.mark.parametrize(
    "defect",
    [
        "libs_jar",
        "source_jar",
        "unknown_build_jar",
        "wrong_variant_path",
        "aar",
        "java",
        "kotlin",
        "wrong_namespace",
        "duplicate_namespace",
        "nonempty_runtime",
        "runtime_trailing",
        "wrong_r_class",
        "constructor_code",
        "extra_constant",
        "extra_member",
        "duplicate_member",
        "wrong_member",
        "archive_comment",
        "member_comment",
        "member_extra",
        "compressed",
        "prefix_payload",
        "trailing_payload",
        "local_extra",
        "oversize",
        "hardlink",
        "symlink",
        "directory_symlink",
        "fifo",
        "symlink_project",
    ],
)
def test_generated_cordova_source_or_archive_payload_is_refused(
    defect: str, tmp_path: Path
) -> None:
    generated, runtime, resources = cordova_output_project(tmp_path)
    r = resources[0]
    if defect in {"libs_jar", "source_jar", "unknown_build_jar", "aar", "java", "kotlin"}:
        relative = {
            "libs_jar": "libs/empty.jar",
            "source_jar": "src/main/empty.jar",
            "unknown_build_jar": "build/unknown/empty.jar",
            "aar": "build/empty.aar",
            "java": "src/main/java/Unexpected.java",
            "kotlin": "src/main/kotlin/Unexpected.kt",
        }[defect]
        extra = generated / relative
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_bytes(b"PK\x05\x06" + b"\0" * 18)
    elif defect == "wrong_variant_path":
        runtime[0].rename(runtime[0].with_name("Classes.jar"))
    elif defect in {"wrong_namespace", "duplicate_namespace"}:
        (generated / "build.gradle").write_text(
            'namespace "synthetic.other"\n'
            if defect == "wrong_namespace"
            else 'namespace "capacitor.cordova.android.plugins"\n' * 2
        )
    elif defect in {"nonempty_runtime", "runtime_trailing"}:
        if defect == "nonempty_runtime":
            with zipfile.ZipFile(runtime[0], "w") as archive:
                archive.writestr("Unexpected.class", b"synthetic")
        else:
            runtime[0].write_bytes(runtime[0].read_bytes() + b"synthetic payload")
    elif defect in {"prefix_payload", "trailing_payload", "local_extra", "oversize"}:
        raw = r.read_bytes()
        if defect == "prefix_payload":
            raw = b"synthetic payload" + raw
        elif defect == "trailing_payload":
            raw += b"synthetic payload"
        elif defect == "local_extra":
            raw = raw[:28] + b"\x01\x00" + raw[30:]
        else:
            raw += b"x" * 2_000
        r.write_bytes(raw)
    elif defect in {"hardlink", "symlink", "directory_symlink", "fifo", "symlink_project"}:
        if defect == "directory_symlink":
            (generated / "linked").symlink_to(tmp_path, target_is_directory=True)
        elif defect == "symlink_project":
            linked = generated.parent / "linked-project"
            linked.symlink_to(generated, target_is_directory=True)
            generated = linked
        elif defect == "hardlink":
            os.link(r, r.with_name("hardlinked.jar"))
        elif defect == "symlink":
            r.rename(r.with_name("source.jar"))
            r.symlink_to(r.with_name("source.jar"))
        else:
            r.unlink()
            os.mkfifo(r)
    else:
        payload = CORDOVA_EMPTY_R
        member = CORDOVA_R_MEMBER
        if defect == "wrong_r_class":
            payload = payload.replace(b"plugins/R", b"plugins/X")
        elif defect == "constructor_code":
            payload = payload[:-11] + b"\x00" + payload[-10:]
        elif defect == "extra_constant":
            payload += b"synthetic constant"
        elif defect == "wrong_member":
            member = "synthetic/Unexpected.class"
        entry = zipfile.ZipInfo(member)
        if defect == "member_comment":
            entry.comment = b"synthetic private metadata"
        elif defect == "member_extra":
            entry.extra = b"\x01\x00\x00\x00"
        elif defect == "compressed":
            entry.compress_type = zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(r, "w") as archive:
            archive.writestr(entry, payload)
            if defect == "extra_member":
                archive.writestr("Unexpected.class", b"synthetic")
            elif defect == "duplicate_member":
                with pytest.warns(UserWarning, match="Duplicate name"):
                    archive.writestr(member, payload)
            elif defect == "archive_comment":
                archive.comment = b"synthetic private metadata"
    with pytest.raises(audit.AuditError):
        audit.validate_empty_cordova_project(generated)


@pytest.mark.parametrize("location", ["root", "child"])
def test_generated_cordova_unreadable_tree_is_refused(
    location: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    generated, _, _ = cordova_output_project(tmp_path)
    target = generated if location == "root" else generated / "unreadable"
    target.mkdir(exist_ok=True)
    original = os.scandir

    def unreadable(path: Any) -> Any:
        if Path(path) == target:
            raise PermissionError("synthetic private directory metadata")
        return original(path)

    monkeypatch.setattr(os, "scandir", unreadable)
    with pytest.raises(audit.AuditError):
        audit.validate_empty_cordova_project(generated)


def test_generated_cordova_tree_entry_bound_is_enforced(tmp_path: Path) -> None:
    generated, _, _ = cordova_output_project(tmp_path)
    for index in range(30_001):
        (generated / f"synthetic-{index}.txt").touch()
    with pytest.raises(audit.AuditError):
        audit.validate_empty_cordova_project(generated)


@pytest.mark.parametrize("directory", ["src/main/jniLibs/arm64-v8a", "jniLibs", "build", "libs"])
@pytest.mark.parametrize("suffix", [".so", ".SO"])
def test_generated_cordova_prebundled_native_library_is_refused(
    directory: str, suffix: str, tmp_path: Path
) -> None:
    generated, _, _ = cordova_output_project(tmp_path)
    library = generated / directory / ("synthetic-bundled" + suffix)
    library.parent.mkdir(parents=True, exist_ok=True)
    library.write_bytes(b"\x7fELF synthetic fixture, not a real native library")
    with pytest.raises(audit.AuditError):
        audit.validate_empty_cordova_project(generated)


# Exact public selected-coordinate POM metadata, independently retrieved 2026-10-13.
# These compressed metadata fixtures contain no app binary, credentials or contributor data.
_REVIEWED_PUBLIC_POMS_GZIP_BASE64 = {
    ("androidx.camera", "camera-core", "1.4.2"): (
        "H4sIAAAAAAAC/81Y31PjNhB+569Q08diiQSmvWaMb65AO9eB3k2hnfbpRrHXicCWPJKcH/3ru5Ll4ISQ"
        "cEBueLIlfVp93+5qZTl+Py8LMgVthJKnvT496hGQqcqEHJ/2/rr5NXrXe58cxJVWt5BagmhpTnsTa6sh"
        "YyWfgqS84ukEqNJj9vnTFTuhR86KRw7nRizRs9mMzo49bnB01Gf/XF1e48SSR0Iay2UKOMuIofGdlyrl"
        "1pPauRhxCLMJMjdZ0xl5IMV2LzkgJP4uisjNRBhSqqwugMy4IbwwilT1qBBmAhmZCTshnGiBxrTDQXFI"
        "ftM8Q3gJlmfc8kNComhpcDZBLDETVRcZGQGpDZpx2oBnlJwrIpUlaAYsEDsBkquiUDP0NCmEhDC9axD5"
        "WYUWMoG+APce1leacLlYsmk0tKRILrCVKmnqEpl3DdoJt27pRcuy0pAjpgE7JsLeM+5MzNQXJP9FQ6mm"
        "MLz3UuS8FI09j2hJIEz0Pvu7ya3EByBmK30ONNaqrj5mCZeZViKb05Qjax6zdsCBuLYi56nFZjMcpUpD"
        "zDr9DhbyOOnTEzqI2bSzDObEHR+jwoRzHbP7phuUaDM584bJmTfse9xQBibVonKZmLghdFVZKQnSGoyf"
        "9nH8HayzR4KFSzHSXC8OMXmK5hXdrKbC7Snsc74W6GFpMYYZ0VAIPnIBa2bnqpaZz/wmWiDdqCFjDdgK"
        "oEwLTGoC8wq0wP2K4zzVyrgkLojKyYfGmzRmXQFOUK2LpN0vGUyhUGiDBu9TVMduGzmsjQhDisANGNas"
        "/n1wr7PkLApc39v/F7hOBkf9n2O22udQuB25FP/xlkjr9ht0YGBLPlUo6lrVOgXyuak4nVCwdRNxIVKQ"
        "SCzYC82mtWLfVwS0nNsZxxheNsBDEhKRDFxqtgv5ua2bQt3q1JR2UXb58ezij+uLCCdTO7dLh/j5GYZY"
        "i1HtuWqoFEai29UwZiuUNwv45fq8JfwIRxfKdKJVKeqSjpUaY754J/pwYg4u6mn7+AGjmRs2wQ1usDQK"
        "yf68+HB+dUFbAy+VsWyYsH9CirVBWnZsCNNT0sCtsGKj02yWNGkZgLjVJE52RLFzOBZ22PqrTfgH7qoK"
        "bnFjlyzXuOJM6TvDTF1VSiOJjsGDhyEwK9touX22Wmw3EQus0T+oPsM9vbjiko+hxEKxdF0YEm3Kr+Db"
        "ricW1QDdUFr9Y7BeXQP+8Rrbxmadzx4oQp5jGMybpjjHEu/WfdMsC4GOXKQFvGWSZXEnbDQVbum3zBOP"
        "eFBvmyDMXolfpydUoy5mtXRtKFwbxD2UxiV+c/rT/oG8rrgu7KG2jjJ/yq8rMymeHIn7qhNuFzTNg0dE"
        "74V11HzGOW/xYoeEE9r/Ggk4aBfY8N+8/u0lyvD0S2utkedWZfewKK9trcHsENV/PC66lhY98xpxeTb7"
        "6M7O34gCdzXZyl3D85nuP4FgLnIhLWikt13JGnKrpONNBetx57+upM4BukXOEoX31rLcUagG3yidvpZ6"
        "gXdOd71/Pvn9Z5jVPMVr9lZFS8xzD4u9ZRX6J1xIKK+tolNe1Nuj42CRh0X3B8quevsjPd5fenU0jGs+"
        "5TuSy/0IcT84mlq7g/gej2+82dNbsCONV2JD75QtxPbzu4FExmZ4s97B+x0dDL4t9fkTuM/dTzSF93iJ"
        "Z1zYQTuE/PSyzFn/aIxZ+K+c/A9g6W8kiBYAAA=="
    ),
    ("io.ionic.libs", "ioncamera-android", "1.0.2"): (
        "H4sIAAAAAAAC/82XXZPbJhSG7/dXUF8H8MembTyKks427eyM03YmaSd3GSywxC4CDSB//PsekCzJrqvd"
        "SbI78ZWBl8NzDucASt7sS4W2wjpp9OvJjEwnSOjMcKnz15O/P/6Gf568Sa+Sypo7kXm0d3LpskKUbGUy"
        "5uOkwvtqSWnJtkITVjEYJsbm9K8/39NrMiVTFBTukmTveNOJo5BAe4KASLtHmJ1cIfhF9RK4uhm73Y7s"
        "FlE7n05n9NP71YeIjKV2nulMTFKYmvyAMfpYSIdKw2sl0I45xJQzqKrXSrpCcLSTvkAMWQnzbdAJ9QL9"
        "bhkHeSk848yzFwhh3BncFaBFrjC14mgtUO3ATFhXME7QrwZp4xGYEV4gXwi0MUqZHUQbKalFO31oEPi8"
        "AQtcQrxF+N+ubyxi+tDRND4codBGQisz2tUlkA8N+oL5sPThSFlZsQFNIw4k0vfEg4ncfAb4z1aUZiuW"
        "fZRwiBLOIwfuANqJMWb/NPmVxm1L6ElfEOXW1NUtT6Uh0CUzouTaJfTYHSTMerlhmY8qnTHwimGmuTWS"
        "J3QwGsRtPqeQzmSe0O1gKcije5aDlyljNqF9MwxqMHvJfOwPAi5cZmUV8j69iSL0SyNCK7lO6HA86Gur"
        "0mPy5xClek0yU9LoJIYAx7/HdXCzbELDrDBbyUxoJ1waE/3YbFpH2lXT2TPGoS9Zl66VWUO5SU25yRxd"
        "3d68++PDuw4HzNIBQtdwbWS2QpkKIt1qu45T3tuAcEYLpSmBV75tNl+ahDZd7aonpgbNZmWXla0QMljD"
        "IRWCD51LcHzZO78cdZ6AMKEDA2dO3PzXtHPFSXQfs8Ale1dfvmPeChF3rM8Z2oYD0CuhOZzlUvRb0nYd"
        "utAfSwwOS3In/NqCMUfujVfB6KAAo3pQZo0EO89VSPzTAozivghfkfnLkyqM4y6DQKTgZAVHVeAOzW7H"
        "T0nH0NuY7CFeVowyBwG+9/sHcGcvwyF1GdfW2svym+CyqgrOMz/KPFCNQv/0PMyQslvpD+PIregRoX5F"
        "Fk9HDXEjuTG5EqR1gJRwhVrJ1Ch/LxpPk/mzhDxcyz6UpVfsYGr/QIafi0dcmJMn9eCu1nKctlWMIF6T"
        "2eLsBv+mjJeOvf0jzr09hrME4gtPNofjsXK3LR+s0MV37sj/PKee049BzcJHiCC5M+P3UCMYzfLZlMye"
        "o1Db19tYeTbvyuaiGg3y9VNmfYcs9nIDZ4WwwDF+dZ4pR9kX5MevYR+049MFHunNx2d69S/ckBmOrg4A"
        "AA=="
    ),
    ("io.ionic.libs", "ionfilesystem-android", "1.1.0"): (
        "H4sIAAAAAAAC/81W204bMRB9z1e4ecZ2AlQq0bK0olAhhbYStOobctZO1rBrr2xvNvn7jr3XUC5Rkarm"
        "KTM+M3PmeMZJdLbJM7QWxkqtTsdTMhkjoRLNpVqdjn/cXuIP47N4FBVG34vEoY2VM5ukImdznTAXglLn"
        "ihmlOVsLRVjB4Jhos6Lfv13TYzIhE+QR9inIxvLaiQOQgD1GwEjZPdKORwg+AT0DXl1EVVWkOgrYw8lk"
        "Sn9dz28CZSyVdUwlYhxDaPQOY3SbSotyzctMoIpZxDKrUVEuMmlTwVElXYoYMhLijceJ7AB9MYwDPBeO"
        "cebYAUIYdwmrFLDIprrMOFoIVFpI4+sKxgn6rJHSDkEa4QRyqUBLnWW6ArVRJpVowocJgZ/TkIFL0Fv4"
        "7019bRBT245N3UNLCi0lWIlWtsyB+TChS5nzpbcty8KIJWBqsGciXc94EMj1HZC/MyLXazHrVcJeJbwK"
        "PHBHoAkMmv2s5ysO1xbRHZ8HrYwuiyseS03AJROSyYWNaOv2EGacXLLEBZTy3dktUMwxU9xoySM6QPiA"
        "ZqbjKZn6mutBOZilB7aCTmPGTER70x8qlovnSoQzD+LCJkYWfv7jS690jUSfaiSay0VEhyAfVJosbjdh"
        "BZKVC5LonIaOMagdvrbFcF8/oj7SZ8hkIpQVNg6T35q11VKf186ebDj629p0kekF7KBUdH51fvH15qJj"
        "A1npgEFn2Eahtch0Aao32M6xS/fKM3hEFlZVAl35sR4GqSNau5qqO6kGZl3ZJnkDhIlW8Gh5/cE5g75n"
        "fe+zV3snAI7oIMmjRs7/TG9tuiPwvkWeyjl628U5I0S4uH58aCMNtFAIxeGdl6K/nsa17a6hXT94SMm9"
        "cAsDySx50C7zSQfLGdCD9ash2Dqe+T3YXcwA7pfzhBwe72xnOLcJiBFDowU05Hl7s7v9XaYvUW902YBm"
        "RrzI2QPwg9u8Qnf6/tFjMqBrSuVk/ha6Tym92UPqDQb6unTwC2Jx3eorov/vTTzzqv/LPrrZgepyLd32"
        "xR5a0B4zdEKO3sJ6YIf1hR+w+s9ZPPoNlr/ydM4JAAA="
    ),
    ("junit", "junit", "4.13.2"): (
        "H4sIAAAAAAAC/+08a3PcuJHf9Suwuq3L2hFJSfb6oZud2GvJKe1atmplb3KVDymIxMzA4isAKWni8n+/"
        "bgAkQQ7BGerheOvsykMDoBuNRqNfaHDyl+skJpdMSJ6lP23v+bvbhKVhFvF0/tP2h/evvWfbf5luTXKR"
        "fWRhQWB0Kn/aXhRFfhAECb1kqU9zGi6Yn4l5cPruJHjs7yIWNfLgWvJ69NXVlX/1SI3b393dC/5+8uYM"
        "ABPq8VQWNA0ZQEl+IFXjmyykhSJq7WTENeJaRrrRU+N8+L093SLwb5JkEYt/1+ueqt5J0Grb0uPmIivz"
        "42j6sUx5MQmqn7qTioLPaFg0/VaLHnJZT7H3yN+fBJdt9ClN2PSXDwpW/a2bIyZDwXNcv+4lXBJKcA5S"
        "MFnA7pCZgPFXmbggs0yQX+gl3SGhYLRgETlfkiPBwwX5K00SSmgakV9ZWpCfWXjhTwIbvZ6wFPHUcFGt"
        "BNk3CbBV93PYHTX+fxkVU9g+WEq7TY8DMJryf9MG9cAyuzOjgPTOHqyincQ8ZKlk0kJlmpqWZu6jMOa5"
        "ZOS0PIdR5I0eSfZw29sE9RHFNLSSqZjNaRywPPYu93b9RZHEFqU1gojLQvDzUhEsWJ4B0+2mhuigRXX9"
        "U1YSErFLFmc5iI0FVDd2puXRNJJ0NoPNifrYcEgveUTO1IieZcOx4/E0wkEvEI2fMtgw3WpR3DP7EEUX"
        "YZalbOmi6Vd2yVPyyoxxUmWwvJhn2Txmfpglt6dMFmxG03MuLlImXPSdqUHk52qUk0L8nxcapWdw+hG7"
        "PZUJFWG+4CCCuYvGExhCTqsxwxRa6DYiz2owIjgJs1SLctaSSqu5j0ityGzYXlJbZ93ojH61Yq2sYDR5"
        "YemOzqJah1rCqZ7zYlGeoxRpfechAv3nY1DyNF/IoE3p6hkXWWyrn1b7tOHZJFANbdigAzwJVpjXaqrV"
        "QS6YYP8queRFC16ZuekjMGSPJ9rmVVg6ELpVhkl741Kw7shc6DgA5qj/DrPJn+POWKA9wvyqF/GLBu2B"
        "A20fhq3RO9natUlB51NR2WH8sYXsqTkx4VKW7ISmdM4SMJbWfHIJxzqZ6qkARP8cT0+gppAt09Y76yTk"
        "90sIVSxtU7I6Z8uM9RIUZVdpnNHow6YTX/ELHhwaKA8cE+8Ynb8YrKiNy1pySnO5yIrfwIiCCGdiuaoh"
        "9TTVSE/b235N+ZZdl5KcmaGkwTroB+CyMil9maW0WObaE8DjCdwIRIWDMxlURMigozImwdBKJmLt8gSL"
        "GQXHYIPl/aaH3mp1kolLcEWCGPzwOIAtmoPTCecyj7OlVjD7q0vsW8UEFY9jUb6RFd63IMQN/Qje0Rou"
        "ZdRleD1x2/uyJbnSqqhrCt5SqR+jiyoY2PN/nATWb2txpWAzLljVs+/vPff3YO5OewOxoAm46bJocD+a"
        "BN3GZjhLwb0PmTiNS9iBBgiUW3+XtQDa6dr3n8Ay6ADAJY2ysAsEfu4jhOvpbGBNhOiflzyOQJRKoOzI"
        "RJLT47N33rNnPz739tAeDQxs8FExL3GLJAms1nk+9y/YUgnzk6fPnj969QoYYbfWVq/Z0cqRzlkaQXDb"
        "3uW6uXvwqlAPDoNfbU8nALSIrcO+aqgXZoKtBoQ1SBUIfv+ps/efrSDRdsoaMr8A8TE/FxTVxt3Qb3wO"
        "2JJpoSjRfzvW12mx9lDJTEtravmRXdfMtPd4ZxEcylBpqO8/1aIIyhLaPwdShKDbeBrUiFFzVABdF653"
        "kpvO7Zyoir/jMupzN+3u6ZvjV0dvz448rVyL60JF6aprFWfQj7RvYU2bfXRypQq64N95Xqvh56xYkG0U"
        "RJ2Z2VbpCNUAh54taCmhSTASQeRUxgUBzkAACiJEshk5effLO2ImaqG9WmB+A+GYzFnIwYVYAoqIhyoD"
        "UmTkBI0UMXyWfgv6/YJp1Jh4iqRKoWwbgBgEgLyLI5VTIe/OEXy7DX4ECyFJ9jFTeZmUsGsWlgU9jxmZ"
        "ZzQmgEAh21FrpWYBOoljWyJYYQsvRLgEKElAdRCw92olOE2H+tfVGI4WIFFhEZGMORNhen6vCUpg7yN2"
        "rdIXWyuMmWVxnF1hjskwXrE5E7AnQA8NQbOhsiYFMlHxTJ1LEvMZC5chROctlC6i5iXsMlJSiCwqlUPa"
        "+uEVmQdTeA1aRa6N2vM6wqcJ7hH2rlTiv1cLFl5IWAYt1FqM2kKxK8H9+ZMkimbCtYeq2Qx7qKKsnRV0"
        "iOKXw19xBPgLf94haQb/ST0lYlRExHYUFUuV4M44MJWnveiM8O4QFcHBGQQJATE3rmBFsDootrrE33Dq"
        "mCCV+u4IUB/vurZAJ04rH8PTnHUbhI5R6PVNXKZBOzrqDOFyHEquHtDfXzmWZmavYs6qZ9mWmAVwcspB"
        "X4IK4f8Gk61b3BB4wqW7vx5TUQJ2F3+5EQZrMGJ8PuPzUtDh1auxM5UOESVMO1vJgazmKsqYrVmLMWpK"
        "/tRp/921hb2QcPDIWZawSgfOGC1KlGSDEjQimD1MTmtVIsq04DAcFLhKbmtHDoS+T157Z0yYlODfT1+V"
        "QiBe61jrKb7/pHWR6fhckaKshlZl1uHbaFL8B7FdCaDnjDTWvZV88dW0n3dQxS/4HM7nd5utKKiWtNnw"
        "6oz9Yw0dDwaO4yoNNxKBSnDQlI6Tm+4uomatdvL7TxiMNPtnc76J0r4co1uz3oSpo9hT8fRt9ptlUEay"
        "9Wdww8mpwDxQyNBkgein4B4IdMN4ytrGCs5tniU+3hX+AKZRndkq0t/4fCQq7BbKnDIaPfDvek9qdo7l"
        "TMVRkzc5ZPlYdr7N6pySJIe2KX6JvhSLvrvJOjamByCGFblK1K6zIZNgwMRanSsBQ5/XNc4V+5BH4OxK"
        "Yg7Bf/HohwcbuixVUBuCgNaXQxHTSg6TZTG1/ZfeGLjr+1RQG7o74O5hhuSefRvtl4BGhyhMenV8emfu"
        "iln0rdyVG4rQpl7OhM9TiHtOuJQQgLzmMZvOgBagebWjH8EMu6zo20pCHVbx92edVIQzlaZMBEYmfWVz"
        "CpbkGJeBd+WeJCuLvCxe326qSWCh2XKorTm7rjigf/QPLLILlk5fGAF9MQl0Q//gSxqXNuGXjWFTPVuj"
        "lMuwdlDu4QfcMwImFOMmf/ef+/s7BMLEC1CWHka4ih0E+a3DJjjpOfyI4A+BfIyXfr9q6NM0CpfBIGqn"
        "FDxNFYVBJF8ISswhu2HMVGEfFzM9GlYhm5yOqnLHIXVVlvUzpo67Cdd2qk7nfzp+jSuvZW7XxJwVXRDT"
        "6gABH+Ssdyarxw36vn/GpmfLEUzp3Wnl9ruNDrYssiswxiBzehd0mNVtdcP+jYoUmC4twLqpHypi5+Xc"
        "DNd/O9QaCHAV9eGfw0t/KeZDvgJwb+r9PeZpcVCmISZJWIRC7Jo8WI93ktDrhCXTvf1nCd5Pqx93qUjc"
        "foGdaPQxmbahD0BTntDYkymfzeAs66M96kTv+XuPv0TGQ4LxU0G1pzZro4SHTsPfme9gJv6SiY561Rs4"
        "1E5Z8GssA1IxJCVoTvZ+HBaIAQHZ3TBaxMvMtcv92p38l5W51bl7CCSlTpqqwqCmnhFGqGQzxqQSLMhq"
        "CgZMA1GOE5ElLxjZhijrPUg03iTMCoQEtMZDbrkMN02DVte5Y9OgnWvgz7e18HhsUYqN24g/ZVAt3riN"
        "akw/OLD8TNWMvIqplG8yClw2ZqO3y+Vm4E3HSynxghUlxXigK+1boyXUcUvbP2Q5pLmsE2/uHHTSr9qR"
        "Dc67LQa1AOh6g6ebnfibSUL/jaijl7N7OKnvF1xWhzWkaeWNq2OF96P1vcKfZH3MfqgvT1EMH6zgBCg4"
        "zx8pXkqEC37JfHLGAKXy1UxFx8MqrAVRFjc+qwrFuJO677ss9X2wc84g2IMgUt0wRlmI9drUBCErwCYW"
        "UTeJwP/2ZhgEfcy2ON1lsinluA2TDYqx+rCviOTWSlEWSwgNF4wVJrpfvc838wbNUD+UchJ0QN2uO+Zd"
        "Cgio0BNWv/uH0rJYZKJSiObX1qBqMGOHtUHEcPI3PL2ota3d1A8UY5+OorSOtxr6IS7YEixwVAUo9U+n"
        "NWmMh2PMFU+j7KrgRVwVAL88PZ4EdvOaWFY9QlkbsaoyNTZlIIrmz/5xRhB+78/cd3rdKF7mfIDzdk3Z"
        "co1jp4qWaM7/2SFltV7Pkagx1+tAtvQzQUNdHK+WIlnQwurvqmEBTBc4szmW4htcgebWMCMgglElJqda"
        "Zb2FNcnpQx8iSyZSGvsP0eFcHeE8MOdZLXLVL0e4yVOIMLGW5tE+Bpz1z6HoFPvtANU9Hm9W36VHQmTC"
        "umutWgZrdOrLgeWZKajRCJzd65wgPe54sEBoCKRVI3bQKl87eGi7IW2otV7LOrruNNhfsU+mRGKsF/Bj"
        "643WjayRmv9IhVGZgOm0WfdyWixMZb7V6VSs5urnVGQzK8u92rHlyuDo4smpd1o5Gx4e/Z1WLTH5/lM9"
        "8rPK8BgoV4pvjufztSo5mooXPRni9pAvvOd4uT025zqYoLnrYERdUekqZoi0cnDmQv+KzrN0ZDCiYDxT"
        "Gz0yEtn1H2N98i2CjzsIwqLsmtORi1YwXpJFZcy8hIoLfC8wcvEq1/uVxF09LrUY706Lu3WlTcAwtCNR"
        "pEpADs0bUsvbXe1xo0loymfORIU926EuCz1O8ljV7Cvyj/BlVG07140a8HHW01GTuhabGv0SNDtWZIbe"
        "iRZV1IfV8+D+zg3Iq+Z2jXTIsnM771cRgw9K07Gm94lTLd2aHv1qZSxBz5y+wK0JMhWld+ed3IG/ZDIv"
        "Y2l6ujFFVUv1ijQw1fxb5i47z0TRfgPSX2C++aKMf6IukT09wej1PbutSm3sSfVJA3mkEqVRE8k7R2w5"
        "ayqvKNefAcgEOTk9/s3bf/K0P3ezNueqOXPGnI5fPWBAVRn2rqs3VaOmqvpcPxcTxWYgDZPUdo4D1l6D"
        "HAdkXuKPA6pEDt+mjYOU4UgA9XLUKyDkvwBBGMkQCFcByIs5XgPecB+S+h3dDVHwsVtiTQ5CDecSgptw"
        "5A6FfCSf7Qcbo9ZcjXDWSg2cK6vz7v3Mryd1G4Fvc8jFtMrPYmmVVO+/dfu3hO+3hO+3hO8fPOGrXyM+"
        "3PmW+P2W+P1KHVKjB74em74SLFnxUf3NAlUS236Dv2rVVr4g0fOphe6l9Rmf46vPOG4eEJJzNsvUK12M"
        "pdXzz+qJ7SvwhgQc6uGnmZ2328NB3lq3ZvC+vbl3r97jqvctWELVWZTMmuef+OaTJHSJz4z4bIltSb1q"
        "820SWLc/OB2tMjzmIZn+RItCK5h677bE4iUwtOT4UD8PzqmU+UJgPr55EFqqmmgD3XzM4MA5uXeIX0Fo"
        "cP20PWl+TLdNv/lKAnRaZEy3nViPrVIs/XE5xSqEyykXO8g01QIWKFHvumEW8t9pROXif8z/gY/uAcC2"
        "m3E/tAHsR9lRVuKramx/4F67t1kKWfu/QOFGvm9P9vjJBuV6a8s6x5R32ocY6UYRHq7v7NR5alleW+k5"
        "puKzXfmpKRou/Ny4AHRtgeL6QsXhMKlHtTbN3a9LBCv61K1hW7dsG2jYv1YlQHh4AKask9bWm+12Wvct"
        "xCMHMB5riTQZ6oMCMeiw1gNWUEJhgVU/eH6Mzm8hUuuUJCrVK1v11FU5YahxDCb95ZVspnqNfldv/v4j"
        "Ov42JV73fixpUdBw0bzHGnE4c+AoxaJS7QPf4ynFu6U08/Au+o91WG8oIGNyHF9KQmofc4yEfAnJ+Ka+"
        "pxj5CB4WqL7x4Uu/BiemF/Wu+hCHLHP0yvUXd/GF+rNVnaiUsSvSgVh9+o89/xm+xce/O0tywX4xRTvq"
        "KduYzJ81dpM3SXZly5i3ST2wZg8PaIhltfycx7xY7gg2YwKTyTtyCYb4egOcm7x72ije/Xo04JiNo1HE"
        "cRiNwYbRxMVZ0rTXPFY39i3g+2LepsrCdQV5bwfr2/YMbk/fbfAYfY7sfd6jxDdRxs939vZHquO+70e2"
        "DAfahuck4epNoXkyoSv6VWV+8yUnfKwEcWb/TW7ri5RP+r9I2crkrhYpfSnDce/yba41FB+Grji+KZE/"
        "OJPvQhXs7d9MF+zv3Ici2NvfXBM83UATPHVrAnOz1vedWPyK3a538mjtd2Ste7AVFPv4gtX9RdnuLZwD"
        "fOjDsv/v9NnT9Udt5SrK3BCvvYv6z7mjX2kgUfk+aZayr8fl/2ZwvvZTcAtrVf8E2Ppr2NOt/wOJ4nVv"
        "imkAAA=="
    ),
    ("org.hamcrest", "hamcrest-core", "1.3"): (
        "H4sIAAAAAAAC/4VSTWvjMBC9B/IfBt8tOW0X2uA4LL1soKWFLqW3okqTWGkkGUmx03+/Y9kOLd1lwQfP"
        "mzfvzYfK9ckcoEUftLOrbMGKDNBKp7TdrbLN00N+ff3jJl9k62o+Kxvv9igjUI0Nq6yOsVlybkSLlolG"
        "yBqZ8zv++HDPr1jRayXm8hT0md11HesuE++iKBb85f7uiQqNyLUNUViJ2XwGQCXLkPA7J0VM3f3XD/7F"
        "SEDeXr0WrwU7BZVVvUdpnMLD8zB8lRRK/gWbzxKvER5tTDUU7bw7NhtVkTCrhZEeQyz5hI4k4aPeChkJ"
        "mTj5IFPyT7mRPR6gWrDLkrdnc8rws3cK/yYrncdvotSzfBc7OmO1F76XmcKUtcJg9WtUgNukkLCUVRik"
        "102cugD4XesA9MUaofeDn48bcFuYmgAjIi3bw9aTSuf8O0QHbwjHgArePqhQe9VvIH584tCDarWiedno"
        "YOXhSO7JR8DWHa1Kx4eAsfebbLRpDmhoMSkbiOmpL2OI6Rr0A8qGDX6dhlYxvGL6/wO8BxQo/gIAAA=="
    ),
    ("org.hamcrest", "hamcrest-parent", "1.3"): (
        "H4sIAAAAAAAC/8VVbWvbMBD+Huh/EP4eKVk76ILjjhG2tjRtIWPbt6LIV0edLBlJzsu/31l+ibOmBAaj"
        "HwK5u+funnskn+Krba7IGqyTRk+jMR1FBLQwqdTZNLpZPAwvLz9+Go6jq+RsEBfWvIDwBHO0m0Yr74sJ"
        "Yzlfg6a84GIF1NiMPT7M2QUdVbUCcrJ1skNvNhu6OQ+4D6PRmP2a3y0wMedDqZ3nWkB0NiAEUyYu+O+M"
        "4D6wO9mPvIUIjuH64mn0NKJbl0ZJ1SPOTQrqRz18EirE7MB3Ngi4zJqyuEkTLEVXPBcWnI9Z6w0Qbr18"
        "5sKj3SKGBbegEdiLBWwjdzKm5zFbd60wgox/8wy1TwqTx2xvDqqo5jkk1011Mq9mIo9NjxALNUqrkkoH"
        "h0Jk0q/KJRUmZy0rdsvX/LobokKHtBScsLKolE6+gQbLFakHIKgveTaWcKVIW4YoubTcSnA0Zv3cRjIl"
        "BWgHLhTf243ZDnMPG/JlMSN3dbQ3RsC0ozTXxhQIMqUV9aG2LdjSpcPGoMWq2A8ViqTSeSuXZWBnoTDI"
        "t+9qCLI+w85y7TxO5C3y3wTGRGG0xs+naorlJphb/T7va0yO1qAIiFkvuWZYM2rObg0K1bGd3J1nr4NM"
        "kxcDdMOVBhczmf51FrcGyM8meHgM1qjuIDtHMmtbxCzYHZz18dXlOKTyBjfNPS3sTsARavccL2Edewdm"
        "Ls+eLeAm0keoLTzmkK9t/D2EA6nSUh8jd48hMgux99BNcLvz1R57Rey7yckMtILd/2TWs7vvGNd72cuo"
        "zf3KFsZCeAPKrssrTBa2ozf2FLBekbtTMKk9ZDa8cQfQ1qjI4ltQv734/w9CkPRztAcAAA=="
    ),
}
_REVIEWED_PUBLIC_POM_ROWS: dict[tuple[str, str, str], dict[str, Any]] = {
    ("androidx.camera", "camera-core", "1.4.2"): {
        "coordinate": ["androidx.camera", "camera-core", "1.4.2"],
        "pom_sha256": "ea820b7874afa1047d288c29d6dbb4c9795b70bf12d3e229235af4e7bd08c072",
        "pom_bytes": 5768,
        "origin": "resolved Gradle metadata cache",
        "packaging": "aar",
        "licenses": [
            {
                "spdx": "Apache-2.0",
                "declared_name": "The Apache Software License, Version 2.0",
                "declared_url": "http://www.apache.org/licenses/LICENSE-2.0.txt",
            },
            {
                "spdx": "BSD-3-Clause",
                "declared_name": "BSD License",
                "declared_url": "https://chromium.googlesource.com/libyuv/libyuv/+/refs/heads/main/README.chromium",
            },
        ],
    },
    ("io.ionic.libs", "ioncamera-android", "1.0.2"): {
        "coordinate": ["io.ionic.libs", "ioncamera-android", "1.0.2"],
        "pom_sha256": "5c1bc27a7c7442ba6ebdb731f88f2a74ed620d7c9847a357c26389800e63a958",
        "pom_bytes": 3758,
        "origin": "resolved Gradle metadata cache",
        "packaging": "aar",
        "licenses": [
            {
                "spdx": "MIT",
                "declared_name": "License",
                "declared_url": "https://github.com/ionic-team/ion-android-camera/blob/main/docs/LICENSE",
            }
        ],
    },
    ("io.ionic.libs", "ionfilesystem-android", "1.1.0"): {
        "coordinate": ["io.ionic.libs", "ionfilesystem-android", "1.1.0"],
        "pom_sha256": "5fc8a9c96e200e19673596aba8c66e7e1bdaa217146a3c04eae75e154b844ecb",
        "pom_bytes": 2510,
        "origin": "resolved Gradle metadata cache",
        "packaging": "aar",
        "licenses": [
            {
                "spdx": "MIT",
                "declared_name": "License",
                "declared_url": "https://github.com/ionic-team/ion-android-filesystem/blob/main/LICENSE",
            }
        ],
    },
    ("junit", "junit", "4.13.2"): {
        "coordinate": ["junit", "junit", "4.13.2"],
        "pom_sha256": "569b6977ee4603c965c1c46c3058fa6e969291b0160eb6964dd092cd89eadd94",
        "pom_bytes": 27018,
        "origin": "resolved Gradle metadata cache",
        "packaging": "jar",
        "licenses": [
            {
                "spdx": "EPL-1.0",
                "declared_name": "Eclipse Public License 1.0",
                "declared_url": "http://www.eclipse.org/legal/epl-v10.html",
            }
        ],
    },
    ("org.hamcrest", "hamcrest-core", "1.3"): {
        "coordinate": ["org.hamcrest", "hamcrest-core", "1.3"],
        "pom_sha256": "fde386a7905173a1b103de6ab820727584b50d0e32282e2797787c20a64ffa93",
        "pom_bytes": 766,
        "origin": "resolved Gradle metadata cache",
        "packaging": "jar",
        "licenses": [],
        "inherits_license_from": ["org.hamcrest", "hamcrest-parent", "1.3"],
    },
    ("org.hamcrest", "hamcrest-parent", "1.3"): {
        "coordinate": ["org.hamcrest", "hamcrest-parent", "1.3"],
        "pom_sha256": "6d535f94efb663bdb682c9f27a50335394688009642ba7a9677504bc1be4129b",
        "pom_bytes": 1972,
        "origin": "resolved Gradle metadata cache",
        "packaging": "pom",
        "licenses": [
            {
                "spdx": "BSD-3-Clause",
                "declared_name": "New BSD License",
                "declared_url": "http://www.opensource.org/licenses/bsd-license.php",
            }
        ],
    },
}


def reviewed_public_pom_bytes(coord: tuple[str, str, str]) -> bytes:
    import base64

    return gzip.decompress(base64.b64decode(_REVIEWED_PUBLIC_POMS_GZIP_BASE64[coord]))


def reviewed_public_chain(coord: tuple[str, str, str]) -> list[dict[str, Any]]:
    row = copy.deepcopy(_REVIEWED_PUBLIC_POM_ROWS[coord])
    chain = [row]
    if "inherits_license_from" in row:
        parent = row["inherits_license_from"]
        chain.extend(reviewed_public_chain((parent[0], parent[1], parent[2])))
    return chain


@pytest.fixture
def reviewed_public_cache(tmp_path: Path) -> Path:
    cache = tmp_path / "reviewed-public-cache"
    for coord in _REVIEWED_PUBLIC_POM_ROWS:
        cached(cache, coord, reviewed_public_pom_bytes(coord))
    return cache


@pytest.mark.parametrize("coord", _REVIEWED_PUBLIC_POM_ROWS)
def test_reviewed_exact_public_pom_producer_retains_complete_context(
    reviewed_public_cache: Path, coord: tuple[str, str, str]
) -> None:
    assert audit.pom_evidence(coord, reviewed_public_cache, False) == reviewed_public_chain(coord)


@pytest.mark.parametrize("coord", _REVIEWED_PUBLIC_POM_ROWS)
def test_reviewed_exact_public_pom_offline_validator_retains_classification(
    coord: tuple[str, str, str],
) -> None:
    assert (
        audit.validate_pom_chain(reviewed_public_chain(coord), coord)
        == (_REVIEWED_PUBLIC_POM_ROWS[coord]["packaging"])
    )


@pytest.mark.parametrize(
    "name", ["License", "BSD License", "New BSD License", "Eclipse Public License 1.0"]
)
def test_reviewed_context_does_not_expand_name_only_license_aliases(name: str) -> None:
    with pytest.raises(audit.AuditError):
        audit.license_id(name)


@pytest.mark.parametrize("coord", _REVIEWED_PUBLIC_POM_ROWS)
def test_reviewed_public_pom_producer_refuses_changed_bytes_even_with_same_declarations(
    reviewed_public_cache: Path, coord: tuple[str, str, str]
) -> None:
    # Whitespace preserves parsed declarations but changes the reviewed publisher bytes.
    cached(reviewed_public_cache, coord, reviewed_public_pom_bytes(coord) + b"\n")
    with pytest.raises(audit.AuditError):
        audit.pom_evidence(coord, reviewed_public_cache, False)


@pytest.mark.parametrize("coord", _REVIEWED_PUBLIC_POM_ROWS)
@pytest.mark.parametrize("defect", ["digest", "size", "packaging", "rebound_coordinate"])
def test_reviewed_public_pom_offline_validator_refuses_rebound_context(
    coord: tuple[str, str, str], defect: str
) -> None:
    chain = reviewed_public_chain(coord)
    expected = coord
    if defect == "digest":
        chain[0]["pom_sha256"] = "f" * 64
    elif defect == "size":
        chain[0]["pom_bytes"] += 1
    elif defect == "packaging":
        chain[0]["packaging"] = "jar" if chain[0]["packaging"] != "jar" else "aar"
    else:
        expected = (coord[0], coord[1], "999.0")
        chain[0]["coordinate"] = list(expected)
    with pytest.raises(audit.AuditError):
        audit.validate_pom_chain(chain, expected)


@pytest.mark.parametrize("coord", _REVIEWED_PUBLIC_POM_ROWS)
@pytest.mark.parametrize("defect", ["name", "url", "spdx", "duplicate", "partial"])
def test_reviewed_public_pom_offline_validator_requires_complete_license_tuples(
    coord: tuple[str, str, str], defect: str
) -> None:
    chain = reviewed_public_chain(coord)
    leaf = chain[-1]
    if defect == "name":
        leaf["licenses"][0]["declared_name"] = "Apache License, Version 2.0"
        leaf["licenses"][0]["spdx"] = "Apache-2.0"
    elif defect == "url":
        leaf["licenses"][0]["declared_url"] = "https://example.test/reviewed-license"
    elif defect == "spdx":
        leaf["licenses"][0]["spdx"] = (
            "MIT" if leaf["licenses"][0]["spdx"] != "MIT" else "BSD-3-Clause"
        )
    elif defect == "duplicate":
        leaf["licenses"].append(copy.deepcopy(leaf["licenses"][0]))
    else:
        leaf["licenses"].pop()
    with pytest.raises(audit.AuditError):
        audit.validate_pom_chain(chain, coord)


@pytest.mark.parametrize("defect", ["flatten", "parent", "new_inheritance", "reordered"])
def test_reviewed_hamcrest_inheritance_and_camera_multilicense_are_not_malleable(
    defect: str,
) -> None:
    coord = ("org.hamcrest", "hamcrest-core", "1.3")
    chain = reviewed_public_chain(coord)
    if defect == "flatten":
        chain[0].pop("inherits_license_from")
        chain[0]["licenses"] = chain[1]["licenses"]
        chain.pop()
    elif defect == "parent":
        chain[0]["inherits_license_from"] = ["org.hamcrest", "different-parent", "1.3"]
        chain[1]["coordinate"] = chain[0]["inherits_license_from"]
    elif defect == "new_inheritance":
        coord = ("io.ionic.libs", "ioncamera-android", "1.0.2")
        chain = reviewed_public_chain(coord)
        chain[0]["licenses"] = []
        chain[0]["inherits_license_from"] = ["org.hamcrest", "hamcrest-parent", "1.3"]
        chain.append(reviewed_public_chain(("org.hamcrest", "hamcrest-parent", "1.3"))[0])
    else:
        coord = ("androidx.camera", "camera-core", "1.4.2")
        chain = reviewed_public_chain(coord)
        chain[0]["licenses"].reverse()
    with pytest.raises(audit.AuditError):
        audit.validate_pom_chain(chain, coord)


def test_reviewed_exception_cannot_be_injected_into_generic_pom() -> None:
    coord = ("org.example", "generic-runtime", "1.0")
    chain = reviewed_public_chain(("junit", "junit", "4.13.2"))
    chain[0]["coordinate"] = list(coord)
    chain[0]["pom_sha256"] = "a" * 64
    with pytest.raises(audit.AuditError):
        audit.validate_pom_chain(chain, coord)


def test_reviewed_hamcrest_cannot_inherit_from_an_ordinary_licensed_replacement() -> None:
    coord = ("org.hamcrest", "hamcrest-core", "1.3")
    chain = reviewed_public_chain(coord)
    replacement = ("org.example", "ordinary-parent", "1.0")
    chain[0]["inherits_license_from"] = list(replacement)
    chain[1] = {
        "coordinate": list(replacement),
        "pom_sha256": "e" * 64,
        "pom_bytes": 200,
        "origin": "resolved Gradle metadata cache",
        "packaging": "pom",
        "licenses": [
            {
                "spdx": "Apache-2.0",
                "declared_name": "Apache License, Version 2.0",
                "declared_url": "https://www.apache.org/licenses/LICENSE-2.0",
            }
        ],
    }
    with pytest.raises(audit.AuditError):
        audit.validate_pom_chain(chain, coord)


def test_reviewed_digest_cannot_be_rebound_to_generic_recognized_declarations() -> None:
    expected = ("org.example", "ordinary-runtime", "1.0")
    chain = reviewed_public_chain(("androidx.camera", "camera-core", "1.4.2"))
    chain[0]["coordinate"] = list(expected)
    chain[0]["licenses"] = chain[0]["licenses"][:1]
    with pytest.raises(audit.AuditError):
        audit.validate_pom_chain(chain, expected)


def cordova_compile_jar(generated: Path, variant: str, payload: bytes = CORDOVA_EMPTY_R) -> Path:
    path = generated / (
        f"build/intermediates/compile_library_classes_jar/{variant}/"
        f"bundleLibCompileToJar{variant.capitalize()}/classes.jar"
    )
    path.parent.mkdir(parents=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(CORDOVA_R_MEMBER, payload)
    return path


@pytest.mark.parametrize("variant", ["debug", "release"])
def test_generated_cordova_compile_role_accepts_only_proven_R_stub(
    variant: str, graph: tuple[dict[str, Any], Path, Path, Path]
) -> None:
    data, repo, cache, _ = graph
    generated, runtime, _ = cordova_output_project(repo)
    compile_jar = cordova_compile_jar(generated, variant)
    for index, view in enumerate(data["views"]):
        view["projects"].append(":capacitor-cordova-android-plugins")
        view["artifacts"].append(
            {
                "kind": "project",
                "project": ":capacitor-cordova-android-plugins",
                "file": str(runtime[index]),
            }
        )
    result = audit.runtime_evidence(data, repo, cache, False)
    assert len(compile_jar.read_bytes()) == 330
    for view in result["runtime_views"]:
        assert view["project_sources"][0]["project"] == ":capacitor-cordova-android-plugins"
        assert view["resolved_runtime_inputs"][-1]["bytes"] == 22


@pytest.mark.parametrize("variant", ["debug", "release"])
@pytest.mark.parametrize(
    "defect",
    [
        "wrong_role",
        "wrong_variant",
        "wrong_filename",
        "foreign_class",
        "constructor",
        "extra_member",
        "hidden_payload",
        "empty_compile",
    ],
)
def test_generated_cordova_compile_role_cannot_hide_other_inputs(
    variant: str, defect: str, tmp_path: Path
) -> None:
    generated, _, _ = cordova_output_project(tmp_path)
    path = cordova_compile_jar(generated, variant)
    if defect in {"wrong_role", "wrong_variant", "wrong_filename"}:
        if defect == "wrong_role":
            relative = (
                path.relative_to(generated)
                .as_posix()
                .replace("compile_library_classes_jar", "unknown_compile_library_classes_jar")
            )
            other = generated / relative
        elif defect == "wrong_variant":
            other = (
                path.parent.with_name(
                    "bundleLibCompileToJar" + ("Release" if variant == "debug" else "Debug")
                )
                / "classes.jar"
            )
        else:
            other = path.with_name("other.jar")
        other.parent.mkdir(parents=True, exist_ok=True)
        path.rename(other)
    elif defect == "hidden_payload":
        path.write_bytes(path.read_bytes() + b"synthetic private payload")
    elif defect == "empty_compile":
        path.write_bytes(b"PK\x05\x06" + b"\0" * 18)
    else:
        payload = CORDOVA_EMPTY_R
        if defect == "foreign_class":
            payload = payload.replace(b"plugins/R", b"plugins/X")
        elif defect == "constructor":
            payload = payload[:-11] + b"\x00" + payload[-10:]
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(CORDOVA_R_MEMBER, payload)
            if defect == "extra_member":
                archive.writestr("Unexpected.class", b"synthetic")
    with pytest.raises(audit.AuditError):
        audit.validate_empty_cordova_project(generated)


def test_native_workflow_builds_only_app_targets_and_keeps_repeat_flags() -> None:
    import re
    import shlex

    commands = []
    for line in (ROOT / ".github/workflows/app-build.yml").read_text().splitlines():
        match = re.search(r"(?:^|\s)(\./gradlew\s+.+)$", line)
        if match:
            tokens = shlex.split(match[1])
            if any(token.split(":")[-1] == "assembleDebug" for token in tokens):
                commands.append(tokens)
    assert len(commands) == 4
    for command in commands:
        assert [token for token in command if token.endswith("assembleDebug")] == [
            ":app:assembleDebug"
        ]
        assert "--no-daemon" in command
        assert ("--rerun-tasks" in command) == ("--no-build-cache" in command)
    assert sum("--rerun-tasks" in command for command in commands) == 2


def diagnostic_owned_function(function: Any, name: str | None = None) -> Any:
    from types import FunctionType

    code = function.__code__.replace(co_filename=audit.__file__)
    if name is not None:
        code = code.replace(co_name=name, co_qualname=name)
    return FunctionType(code, function.__globals__, closure=function.__closure__)


@pytest.mark.parametrize("operation", ["read", "contained", "refuse"])
def test_diagnostic_reports_last_owned_guard_caller_not_io_wrappers(
    operation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from collections.abc import Callable

    path = tmp_path / "synthetic-private-missing-file"
    calls: dict[str, Callable[[], object]] = {
        "read": lambda: audit.read(path, (tmp_path,)),
        "contained": lambda: audit.contained(path, (tmp_path,)),
        "refuse": lambda: audit.refuse(),
    }

    def guard() -> Any:
        return calls[operation]()

    owned_guard = diagnostic_owned_function(guard)

    def outer() -> Any:
        return owned_guard()

    owned_outer = diagnostic_owned_function(outer)
    monkeypatch.setattr(audit, "_diagnostic_stage", "android-source-bindings")
    monkeypatch.setattr(audit, "_diagnostic_counts", {"module_inputs": 2})
    expected_type = audit.AuditError if operation == "refuse" else FileNotFoundError
    with pytest.raises(expected_type) as caught:
        owned_outer()
    value = audit.diagnostic(caught.value)
    assert value == {
        "stage": "android-source-bindings",
        "error_class": "AUDIT_REFUSAL" if operation == "refuse" else "MISSING_FILE",
        "source_line": guard.__code__.co_firstlineno + 1,
        "counts": {"module_inputs": 2},
    }
    assert "synthetic-private" not in json.dumps(value)
    assert str(tmp_path) not in json.dumps(value)
    assert set(value) == {"stage", "error_class", "source_line", "counts"}


@pytest.mark.parametrize("wrapper_name", ["read", "contained", "refuse"])
def test_diagnostic_preserves_unrelated_owned_frame_with_wrapper_name(
    wrapper_name: str,
) -> None:
    failure = PermissionError("synthetic-private-message https://example.invalid/private")

    def other() -> None:
        raise failure

    owned_other = diagnostic_owned_function(other, wrapper_name)
    with pytest.raises(PermissionError) as caught:
        owned_other()
    value = audit.diagnostic(caught.value)
    assert value["source_line"] == other.__code__.co_firstlineno + 1
    assert value["error_class"] == "FILE_PERMISSION"
    assert "synthetic-private" not in json.dumps(value)
    assert "https://" not in json.dumps(value)


def test_diagnostic_wrapper_exclusion_uses_exact_code_object_identity() -> None:
    from types import FunctionType

    cloned_code = audit.refuse.__code__.replace()
    assert cloned_code == audit.refuse.__code__
    assert cloned_code is not audit.refuse.__code__
    clone = FunctionType(cloned_code, audit.__dict__)
    with pytest.raises(audit.AuditError) as caught:
        clone()
    assert audit.diagnostic(caught.value)["source_line"] == cloned_code.co_firstlineno + 1


@pytest.mark.parametrize("operation", ["read", "contained", "refuse"])
def test_diagnostic_has_zero_line_when_only_original_owned_wrappers_exist(
    operation: str, tmp_path: Path
) -> None:
    expected_type = audit.AuditError if operation == "refuse" else FileNotFoundError
    with pytest.raises(expected_type) as caught:
        if operation == "read":
            audit.read(tmp_path / "synthetic-private-missing-file", (tmp_path,))
        elif operation == "contained":
            audit.contained(tmp_path / "synthetic-private-missing-file", (tmp_path,))
        else:
            audit.refuse()
    assert audit.diagnostic(caught.value)["source_line"] == 0


def test_diagnostic_has_zero_line_for_tracebackless_or_external_only_error() -> None:
    error = FileNotFoundError("synthetic-private-message")
    assert audit.diagnostic(error)["source_line"] == 0
    with pytest.raises(FileNotFoundError) as caught:
        raise error
    assert audit.diagnostic(caught.value)["source_line"] == 0
    assert "synthetic-private" not in json.dumps(audit.diagnostic(caught.value))


def test_missing_file_main_keeps_failure_status_and_four_field_private_diagnostic(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    path = tmp_path / "synthetic-private-missing-file"

    def collect(*args: Any) -> bytes:
        audit.mark("android-source-bindings")
        return audit.read(path, (tmp_path,))

    monkeypatch.setattr(audit, "collect_android", diagnostic_owned_function(collect))
    assert (
        audit.main(
            [
                "android",
                str(tmp_path),
                str(tmp_path),
                str(tmp_path / "out.json"),
                str(tmp_path / "synthetic-private-key"),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert len(lines) == 2
    assert lines[0] == "native-audit: evidence missing, invalid or unreviewed"
    assert lines[1].startswith("native-audit: diagnostic ")
    value = json.loads(lines[1].removeprefix("native-audit: diagnostic "))
    assert value == {
        "stage": "android-source-bindings",
        "error_class": "MISSING_FILE",
        "source_line": collect.__code__.co_firstlineno + 2,
        "counts": {},
    }
    assert "synthetic-private" not in captured.err
    assert str(tmp_path) not in captured.err
    assert "https://" not in captured.err
