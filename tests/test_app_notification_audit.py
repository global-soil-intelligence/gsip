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
