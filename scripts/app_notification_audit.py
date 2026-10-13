"""APP-2B CI evidence only: exact resolved native inputs and overall feature delta.

No contributor data, credentials, deployment or signing is read. The temporary Gradle
inspection task is build configuration, never shipped app source. Missing evidence fails.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET  # noqa: S405 - bounded public POM metadata only
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn, cast

from scripts import app_build, app_permissions

BASELINE = "d7ed716ed0921381da04f542e90902ede36cb462"
MAX_META = 2_000_000
MAX_BINARY = 200_000_000
MAX_ZIP_BYTES = 500_000_000
MAX_ITEMS = 2_000
TOKEN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.+-]{0,127}\Z")
REPOSITORIES = ("https://dl.google.com/dl/android/maven2/", "https://repo.maven.apache.org/maven2/")
LICENSE_NAMES = {
    "Apache-2.0": {
        "apache license, version 2.0",
        "apache 2.0",
        "the apache license, version 2.0",
        "apache license version 2.0",
        "apache license 2.0",
        "apache-2.0",
        "the apache software license, version 2.0",
    },
    "MIT": {"mit", "mit license", "the mit license"},
    "BSD-2-Clause": {"bsd 2-clause", "bsd 2-clause license", "bsd-2-clause"},
    "BSD-3-Clause": {"bsd 3-clause", "bsd 3-clause license", "bsd-3-clause", "the bsd license"},
}
PROJECT_PACKAGES = {
    ":capacitor-android": "@capacitor/android",
    ":capacitor-camera": "@capacitor/camera",
    ":capacitor-filesystem": "@capacitor/filesystem",
    ":capacitor-local-notifications": "@capacitor/local-notifications",
}
NPM_PACKAGES = (
    "@capacitor/core",
    "@capacitor/android",
    "@capacitor/ios",
    "@capacitor/camera",
    "@capacitor/filesystem",
    "@capacitor/geolocation",
    "@capacitor/local-notifications",
)


class AuditError(ValueError):
    """Generic refusal; never copy arbitrary parser, tool or network error details."""


def refuse() -> NoReturn:
    raise AuditError("native evidence missing, invalid or unreviewed")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def contained(path: Path, roots: tuple[Path, ...]) -> Path:
    """Reject lexical traversal first, then verify physical containment without symlink inputs."""
    if ".." in path.parts or any(".." in root.parts for root in roots):
        refuse()
    absolute = path.absolute()
    permitted = next(
        (root.absolute() for root in roots if absolute.is_relative_to(root.absolute())), None
    )
    if permitted is None:
        refuse()
    for ancestor in (
        permitted,
        *reversed(absolute.parents[: len(absolute.parents) - len(permitted.parents)]),
        absolute,
    ):
        if ancestor.is_symlink():
            refuse()
    physical = absolute.resolve(strict=True)
    if not physical.is_relative_to(permitted.resolve(strict=True)):
        refuse()
    return physical


def read(
    path: Path, roots: tuple[Path, ...], limit: int = MAX_META, *, allow_empty: bool = False
) -> bytes:
    """Only explicit bounded regular single-link files beneath trusted CI roots."""
    absolute = contained(path, roots)
    fd = os.open(absolute, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or not (0 if allow_empty else 1) <= info.st_size <= limit
        ):
            refuse()
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) != info.st_size or len(data) > limit:
            refuse()
        return data
    finally:
        os.close(fd)


def decoded(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                refuse()
            result[key] = value
        return result

    if len(raw) > MAX_META:
        refuse()

    def finite_float(text: str) -> float:
        value = float(text)
        if not math.isfinite(value):
            refuse()
        return value

    result = json.loads(
        raw,
        object_pairs_hook=pairs,
        parse_constant=lambda unused: refuse(),
        parse_float=finite_float,
    )
    if not isinstance(result, dict):
        refuse()
    return cast(dict[str, Any], result)


def coordinate(value: Any) -> tuple[str, str, str]:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or any(not isinstance(item, str) or not TOKEN.fullmatch(item) for item in value)
    ):
        refuse()
    return value[0], value[1], value[2]


def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)  # noqa: S603 - fixed CI build tools
    return result.stdout.strip()


def public_bytes(url: str, limit: int, redirects: bool = False) -> bytes:
    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(
            self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
        ) -> Any:
            if not redirects or not newurl.startswith(
                "https://release-assets.githubusercontent.com/"
            ):
                refuse()
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(Redirect())
    with opener.open(url, timeout=30) as response:  # noqa: S310 - caller constructs pinned public repository URLs
        length = response.headers.get("Content-Length")
        if length is not None and (not length.isdecimal() or int(length) > limit):
            refuse()
        data = response.read(limit + 1)
    if not 0 < len(data) <= limit:
        refuse()
    if not isinstance(data, bytes):
        refuse()
    return data


def pom_bytes(coord: tuple[str, str, str], cache: Path, allow_fetch: bool) -> tuple[bytes, str]:
    group, artifact, version = coord
    folder = cache / "modules-2/files-2.1" / group / artifact / version
    matches = sorted(folder.glob(f"*/{artifact}-{version}.pom"))
    if len(matches) > 1:
        refuse()
    if matches:
        return read(matches[0], (cache,)), "resolved Gradle metadata cache"
    if not allow_fetch:
        refuse()
    relative = f"{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}.pom"
    for repository in REPOSITORIES:
        try:
            return public_bytes(repository + relative, MAX_META), repository + relative
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    refuse()
    raise AssertionError("unreachable")


def license_id(name: str) -> str:
    normal = " ".join(name.casefold().split())
    for identifier, names in LICENSE_NAMES.items():
        if normal in names:
            return identifier
    refuse()
    raise AssertionError("unreachable")


def singleton_text(element: ET.Element, key: str, *, required: bool) -> str | None:
    matches = element.findall(key)
    if len(matches) > 1 or (required and not matches):
        refuse()
    if not matches:
        return None
    field = matches[0]
    if len(field) or field.attrib or not isinstance(field.text, str) or not field.text.strip():
        refuse()
    return field.text.strip()


def pom_evidence(
    coord: tuple[str, str, str],
    cache: Path,
    allow_fetch: bool,
    seen: tuple[tuple[str, str, str], ...] = (),
) -> list[dict[str, Any]]:
    if len(seen) >= 8 or coord in seen:
        refuse()
    raw, origin = pom_bytes(coord, cache, allow_fetch)
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper() or raw.count(b"<") > 10_000:
        refuse()
    root = ET.fromstring(raw)  # noqa: S314 - bounded entity/doctype-free public metadata
    pending = [(root, 1)]
    while pending:
        node, depth = pending.pop()
        if depth > 64:
            refuse()
        pending.extend((child, depth + 1) for child in node)
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    if root.tag != "project":
        refuse()
    parents = root.findall("parent")
    if len(parents) > 1 or len(root.findall("licenses")) > 1:
        refuse()
    parent = parents[0] if parents else None
    parent_coord = (
        None
        if parent is None
        else coordinate(
            [
                singleton_text(parent, key, required=True)
                for key in ("groupId", "artifactId", "version")
            ]
        )
    )
    actual = tuple(
        singleton_text(root, key, required=(index == 1))
        or (parent_coord[index] if parent_coord and index != 1 else "")
        for index, key in enumerate(("groupId", "artifactId", "version"))
    )
    if actual != coord:
        refuse()
    licenses = root.findall("./licenses/license")
    record: dict[str, Any] = {
        "coordinate": list(coord),
        "pom_sha256": sha(raw),
        "pom_bytes": len(raw),
        "origin": origin,
        "packaging": singleton_text(root, "packaging", required=False) or "jar",
        "licenses": [],
    }
    for item in licenses:
        name, url = (singleton_text(item, key, required=True) for key in ("name", "url"))
        if (
            not name
            or len(name) > 200
            or not url
            or len(url) > 500
            or not re.fullmatch(r"https?://[^\s<>]+", url)
        ):
            refuse()
        record["licenses"].append(
            {"spdx": license_id(name), "declared_name": name, "declared_url": url}
        )
    if licenses:
        return [record]
    if parent_coord is None:
        refuse()
    inherited = pom_evidence(parent_coord, cache, allow_fetch, (*seen, coord))
    record["inherits_license_from"] = list(parent_coord)
    return [record, *inherited]


def zip_evidence(path: Path, roots: tuple[Path, ...]) -> dict[str, Any]:
    raw = read(path, roots, MAX_BINARY)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if (
            len(entries) > 30_000
            or sum(item.file_size for item in entries) > MAX_ZIP_BYTES
            or len({item.filename for item in entries}) != len(entries)
        ):
            refuse()
        notices = []
        for item in entries:
            if (
                Path(item.filename).is_absolute()
                or ".." in Path(item.filename).parts
                or stat.S_ISLNK(item.external_attr >> 16)
            ):
                refuse()
            if not item.is_dir() and re.search(
                r"(^|/)(LICENSE|NOTICE|COPYING)([._-][^/]*)?$", item.filename, re.I
            ):
                if item.file_size > MAX_META:
                    refuse()
                payload = archive.read(item)
                notices.append(
                    {"entry": item.filename, "sha256": sha(payload), "bytes": len(payload)}
                )
    return {"sha256": sha(raw), "bytes": len(raw), "embedded_license_notice_files": notices}


def npm_evidence(repo: Path, names: tuple[str, ...]) -> list[dict[str, Any]]:
    result = []
    for name in names:
        installed = repo / "apps/capture-pwa/node_modules" / name
        if not installed.exists():
            if name == "@capacitor/local-notifications":
                continue
            refuse()
        directory = installed.resolve()
        # pnpm's explicit installed package link resolves only into this clone's node_modules.
        if not directory.is_relative_to((repo / "node_modules").resolve()):
            refuse()
        raw = read(directory / "package.json", (repo / "node_modules",))
        package = decoded(raw)
        if (
            package.get("name") != name
            or package.get("license") != "MIT"
            or not isinstance(package.get("version"), str)
            or not TOKEN.fullmatch(package["version"])
        ):
            refuse()
        license_raw = read(directory / "LICENSE", (repo / "node_modules",))
        if b"Permission is hereby granted" not in license_raw:
            refuse()
        files: list[tuple[str, str]] = []
        total = 0
        for file in sorted(directory.rglob("*")):
            relative = file.relative_to(directory)
            if any(part in {"build", ".gradle", "node_modules"} for part in relative.parts):
                continue  # Generated compilation/cache files are not published npm source.
            if file.is_symlink():
                refuse()
            if not file.is_file():
                continue
            if file.suffix in {".jar", ".aar", ".so"} or any(
                part.endswith((".xcframework", ".framework")) for part in relative.parts
            ):
                refuse()  # A package MIT label does not license an unexpected bundled binary.
            payload = read(file, (repo / "node_modules",), MAX_BINARY, allow_empty=True)
            total += len(payload)
            if total > MAX_ZIP_BYTES or len(files) >= 10_000:
                refuse()
            files.append((str(file.relative_to(directory)), sha(payload)))
        result.append(
            {
                "name": name,
                "version": package["version"],
                "package_json_sha256": sha(raw),
                "license": "MIT",
                "license_sha256": sha(license_raw),
                "installed_source_bytes": total,
                "installed_file_count": len(files),
                "installed_source_manifest_sha256": sha(
                    json.dumps(files, separators=(",", ":")).encode()
                ),
            }
        )
    return result


# Only inspect already resolved configurations; no network, shell, environment or credentials.
GRADLE_TASK = """import groovy.json.JsonOutput
import org.gradle.api.artifacts.component.ModuleComponentIdentifier
import org.gradle.api.artifacts.component.ProjectComponentIdentifier
gradle.projectsEvaluated {
    def app = gradle.rootProject.project(':app')
    app.tasks.register('gsipRuntimeEvidence') {
        doLast {
            def views = ['debugRuntimeClasspath','releaseRuntimeClasspath'].collect { name ->
                def config = app.configurations.getByName(name)
                config.resolvedConfiguration.rethrowFailure()
                def modules = []
                def projects = []
                config.incoming.resolutionResult.allComponents.each { component ->
                    def id = component.id
                    if (id instanceof ModuleComponentIdentifier) {
                        modules.add([id.group,id.module,id.version])
                    } else if (id instanceof ProjectComponentIdentifier) {
                        projects.add(id.projectPath)
                    } else { throw new GradleException('unsupported runtime component') }
                }
                def artifacts = config.resolvedConfiguration.resolvedArtifacts.collect { artifact ->
                    def id = artifact.id.componentIdentifier
                    if (id instanceof ModuleComponentIdentifier) {
                        [kind:'module', coordinate:[id.group,id.module,id.version],
                         file:artifact.file.canonicalPath]
                    } else if (id instanceof ProjectComponentIdentifier) {
                        [kind:'project', project:id.projectPath, file:artifact.file.canonicalPath]
                    } else { throw new GradleException('unsupported runtime artifact') }
                }
                [name:name,modules:modules.unique().sort { it.join(':') },
                 projects:projects.unique().sort(),artifacts:artifacts]
            }
            def output = new File(app.findProperty('gsipEvidenceOutput').toString())
            output.text = JsonOutput.toJson([views:views])
        }
    }
}
"""


def runtime_evidence(
    data: dict[str, Any], repo: Path, cache: Path, allow_fetch: bool
) -> dict[str, Any]:
    views = data.get("views")
    if (
        not isinstance(views, list)
        or len(views) != 2
        or {view.get("name") for view in views if isinstance(view, dict)}
        != {"debugRuntimeClasspath", "releaseRuntimeClasspath"}
    ):
        refuse()
    npm = npm_evidence(repo, NPM_PACKAGES)
    npm_by_name = {item["name"]: item for item in npm}
    receipts = []
    for view in views:
        if (
            not isinstance(view, dict)
            or set(view) != {"name", "modules", "projects", "artifacts"}
            or not all(
                isinstance(view[key], list) and len(view[key]) <= MAX_ITEMS
                for key in ("modules", "projects", "artifacts")
            )
        ):
            refuse()
        modules = [coordinate(item) for item in view["modules"]]
        if not modules or len(set(modules)) != len(modules):
            refuse()
        if app_permissions.closed_dependencies("\n".join(":".join(item) for item in modules)):
            refuse()
        selected = []
        for coord in modules:
            selected.append(
                {
                    "coordinate": list(coord),
                    "pom_license_evidence": pom_evidence(coord, cache, allow_fetch),
                }
            )
        projects = []
        for project in view["projects"]:
            if project == ":app":
                continue
            if project == ":capacitor-cordova-android-plugins":
                generated = repo / "apps/capture-pwa/android/capacitor-cordova-android-plugins"
                if (
                    any(generated.rglob("*.jar"))
                    or any(generated.rglob("*.aar"))
                    or any((generated / "src").rglob("*.java"))
                    or any((generated / "src").rglob("*.kt"))
                ):
                    refuse()
                projects.append(
                    {
                        "project": project,
                        "source": (
                            "generated empty Cordova compatibility project; "
                            "no third-party plugin source/binary"
                        ),
                    }
                )
                continue
            name = PROJECT_PACKAGES.get(project)
            if name is None or name not in npm_by_name:
                refuse()
            projects.append(
                {
                    "project": project,
                    "npm": name,
                    "source_manifest_sha256": npm_by_name[name]["installed_source_manifest_sha256"],
                }
            )
        binaries = []
        for artifact in view["artifacts"]:
            if (
                not isinstance(artifact, dict)
                or artifact.get("kind") not in {"project", "module"}
                or not isinstance(artifact.get("file"), str)
            ):
                refuse()
            file = Path(artifact["file"])
            if artifact["kind"] == "module":
                coord = coordinate(artifact.get("coordinate"))
                if coord not in modules:
                    refuse()
                file = contained(
                    file, (cache / "modules-2/files-2.1" / coord[0] / coord[1] / coord[2],)
                )
                identity: dict[str, Any] = {"coordinate": list(coord)}
            else:
                project = artifact.get("project")
                if not isinstance(project, str) or project not in view["projects"]:
                    refuse()
                if project == ":capacitor-cordova-android-plugins":
                    output_root = (
                        repo / "apps/capture-pwa/android/capacitor-cordova-android-plugins/build"
                    )
                else:
                    package = PROJECT_PACKAGES.get(project)
                    if package is None:
                        refuse()
                    package_root = (repo / "apps/capture-pwa/node_modules" / package).resolve(
                        strict=True
                    )
                    if not package_root.is_relative_to(
                        (repo / "node_modules").resolve(strict=True)
                    ):
                        refuse()
                    output_root = (
                        package_root
                        / ("capacitor" if project == ":capacitor-android" else "android")
                        / "build"
                    )
                file = contained(file, (output_root,))
                identity = {"project": project}
            if file.suffix not in {".jar", ".aar"}:
                refuse()
            binaries.append(
                {**identity, "filename": file.name, **zip_evidence(file, (repo, cache))}
            )
        if not binaries:
            refuse()
        receipts.append(
            {
                "configuration": view["name"],
                "selected_modules": selected,
                "project_sources": projects,
                "resolved_runtime_inputs": binaries,
            }
        )
    return {
        "runtime_views": receipts,
        "npm_sources": npm,
        "temporary_gradle_task_sha256": sha(GRADLE_TASK.encode()),
        "scope": (
            "resolved inputs of both shipped runtime configurations; "
            "build/test/toolchain inputs are separate, not inferred shipped"
        ),
    }


def collect_android(repo: Path, cache: Path, output: Path, debug_key: Path) -> None:
    for configuration in ("debugRuntimeClasspath", "releaseRuntimeClasspath"):
        text = run(
            [
                str(repo / "apps/capture-pwa/android/gradlew"),
                "--no-daemon",
                "--console=plain",
                "-q",
                ":app:dependencies",
                "--configuration",
                configuration,
            ],
            repo / "apps/capture-pwa/android",
        )
        if "--- " not in text or app_permissions.closed_dependencies(text):
            refuse()
        (output.parent / f"{output.stem}-{configuration}.txt").write_text(text + "\n")
    build_environment = run(
        [
            str(repo / "apps/capture-pwa/android/gradlew"),
            "--no-daemon",
            "--console=plain",
            ":app:buildEnvironment",
        ],
        repo / "apps/capture-pwa/android",
    )
    (output.parent / f"{output.stem}-build-environment.txt").write_text(build_environment + "\n")
    with tempfile.TemporaryDirectory(prefix="gsip-runtime-audit-") as directory:
        temporary = Path(directory)
        task, graph = temporary / "inspection.gradle", temporary / "resolved.json"
        task.write_text(GRADLE_TASK)
        run(
            [
                str(repo / "apps/capture-pwa/android/gradlew"),
                "--no-daemon",
                "--console=plain",
                "-I",
                str(task),
                ":app:gsipRuntimeEvidence",
                f"-PgsipEvidenceOutput={graph}",
            ],
            repo / "apps/capture-pwa/android",
        )
        raw = read(graph, (temporary,))
        result = runtime_evidence(decoded(raw), repo, cache, True)
    result["build_only_environment_sha256"] = sha(build_environment.encode())
    result["runtime_tree_sha256"] = {
        configuration: sha(
            read(output.parent / f"{output.stem}-{configuration}.txt", (output.parent,))
        )
        for configuration in ("debugRuntimeClasspath", "releaseRuntimeClasspath")
    }
    result.update(
        {
            "schema_version": "gsip-app-notification-native-audit-v1",
            "platform": "android",
            "resolved_graph_sha256": sha(raw),
            "source_inputs": source_inputs(repo),
            "source_commit": run(["git", "-C", str(repo), "rev-parse", "HEAD"]),
            "debug_signing_key_sha256": sha(read(debug_key, (debug_key.parent,), MAX_META)),
            "built_artifact_sha256": sha(
                read(
                    repo / "apps/capture-pwa/android/app/build/outputs/apk/debug/app-debug.apk",
                    (repo,),
                    MAX_BINARY,
                )
            ),
        }
    )
    write(output, result)


def source_inputs(repo: Path) -> dict[str, str]:
    names: tuple[str, ...] = (
        "pnpm-lock.yaml",
        "apps/capture-pwa/package.json",
        "apps/capture-pwa/capacitor.config.ts",
        "scripts/app_permissions.py",
        "scripts/app_build.py",
    )
    names += tuple(
        name
        for name in (
            "apps/capture-pwa/android/gradle/wrapper/gradle-wrapper.properties",
            "apps/capture-pwa/android/build.gradle",
            "apps/capture-pwa/android/variables.gradle",
        )
        if (repo / name).exists()
    )
    return {name: sha(read(repo / name, (repo,))) for name in names}


def tree_evidence(root: Path, allowed: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    total = 0
    for file in sorted(root.rglob("*")):
        if file.is_symlink():
            refuse()
        if not file.is_file():
            continue
        payload = read(file, (allowed,), MAX_BINARY)
        total += len(payload)
        if len(files) >= 30_000 or total > MAX_ZIP_BYTES:
            refuse()
        files.append(
            {"path": str(file.relative_to(root)), "sha256": sha(payload), "bytes": len(payload)}
        )
    if not files:
        refuse()
    return {
        "bytes": total,
        "file_count": len(files),
        "files": files,
        "tree_sha256": sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()),
    }


def collect_ios(repo: Path, output: Path, artifact: Path | None = None) -> None:
    artifact = artifact if artifact is not None else repo / "gsip-capture-ios-simulator.zip"
    ios = repo / "apps/capture-pwa/ios"
    if list(ios.rglob("Podfile.lock")):
        refuse()  # This workflow selects SPM; a new Pod resolution needs an explicit audit adapter.
    resolved_paths = list(ios.rglob("Package.resolved"))
    if len(resolved_paths) != 1:
        refuse()
    raw = read(resolved_paths[0], (repo,))
    resolved = decoded(raw)
    pins = resolved.get("pins")
    if not isinstance(pins, list) or len(pins) != 1:
        refuse()
    pin = pins[0]
    if (
        not isinstance(pin, dict)
        or pin.get("identity") != "capacitor-swift-pm"
        or pin.get("location") != "https://github.com/ionic-team/capacitor-swift-pm.git"
    ):
        refuse()
    state = pin.get("state")
    if (
        not isinstance(state, dict)
        or state.get("version") != "8.5.2"
        or not isinstance(state.get("revision"), str)
        or not re.fullmatch(r"[0-9a-f]{40}", state["revision"])
    ):
        refuse()
    checkout = ios / "App/build/SourcePackages/checkouts/capacitor-swift-pm"
    contained(checkout, (repo,))
    checkout_revision = run(["git", "-C", str(checkout), "rev-parse", "HEAD"])
    release_revision = run(["git", "-C", str(checkout), "rev-parse", "refs/tags/8.5.2^{commit}"])
    if checkout_revision != state["revision"] or release_revision != checkout_revision:
        refuse()
    manifest = read(checkout / "Package.swift", (repo,))
    manifest_text = manifest.decode()
    matches = re.findall(
        r'\.binaryTarget\(\s*name:\s*"(Capacitor|Cordova)",\s*url:\s*"(https://github\.com/ionic-team/capacitor-swift-pm/releases/download/8\.5\.2/(?:Capacitor|Cordova)\.xcframework\.zip)",\s*checksum:\s*"([0-9a-f]{64})"\s*\)',
        manifest_text,
    )
    if (
        len(matches) != 2
        or {item[0] for item in matches} != {"Capacitor", "Cordova"}
        or manifest_text.count(".binaryTarget(") != 2
    ):
        refuse()
    readme_url = "https://raw.githubusercontent.com/ionic-team/capacitor-swift-pm/8.5.2/README.md"
    license_url = "https://raw.githubusercontent.com/ionic-team/capacitor/8.5.2/LICENSE"
    upstream_readme = public_bytes(readme_url, MAX_META)
    upstream_license = public_bytes(license_url, MAX_META)
    installed_ios = (repo / "apps/capture-pwa/node_modules/@capacitor/ios").resolve()
    if (
        b"binary xcframework releases of Capacitor and CapacitorCordova" not in upstream_readme
        or upstream_license != read(installed_ios / "LICENSE", (repo / "node_modules",))
    ):
        refuse()
    frameworks = []
    for name, url, checksum in matches:
        if not url.endswith(f"/{name}.xcframework.zip"):
            refuse()
        data = public_bytes(url, MAX_BINARY, redirects=True)
        if sha(data) != checksum:
            refuse()
        folder = (
            ios / f"App/build/SourcePackages/artifacts/capacitor-swift-pm/{name}/{name}.xcframework"
        )
        tree = tree_evidence(folder, repo)
        with tempfile.TemporaryDirectory(prefix="gsip-swift-binary-") as directory:
            archive = Path(directory) / "binary.zip"
            archive.write_bytes(data)
            zip_metadata = zip_evidence(archive, (Path(directory),))
            with zipfile.ZipFile(archive) as zipped:
                entries = {
                    item.filename: sha(zipped.read(item))
                    for item in zipped.infolist()
                    if not item.is_dir() and not item.filename.startswith("__MACOSX/")
                }
            expected = {
                f"{name}.xcframework/{item['path']}": item["sha256"] for item in tree["files"]
            }
            if entries != expected:
                refuse()
        frameworks.append(
            {
                "name": name,
                "published_archive_url": url,
                "swift_manifest_checksum": checksum,
                "actual_resolved_tree": tree,
                "archive": zip_metadata,
                "license_source": (
                    "Capacitor npm ios MIT LICENSE; Cordova files additionally "
                    "retain Apache-2.0 source headers; package metadata alone "
                    "does not license other binary contents"
                ),
            }
        )
    npm = npm_evidence(repo, NPM_PACKAGES)
    ios_package = (repo / "apps/capture-pwa/node_modules/@capacitor/ios").resolve()
    header = read(
        ios_package / "CapacitorCordova/CapacitorCordova/Classes/Public/CDV.h",
        (repo / "node_modules",),
    )
    if b"Apache License, Version 2.0" not in header:
        refuse()
    write(
        output,
        {
            "schema_version": "gsip-app-notification-native-audit-v1",
            "platform": "ios",
            "built_artifact_sha256": sha(read(artifact, (repo, output.parent), MAX_BINARY)),
            "source_commit": run(["git", "-C", str(repo), "rev-parse", "HEAD"]),
            "source_inputs": source_inputs(repo),
            "npm_sources": npm,
            "spm": {
                "package_resolved_sha256": sha(raw),
                "pins": pins,
                "selected_manifest_sha256": sha(manifest),
                "checkout_revision": checkout_revision,
                "release_tag_revision": release_revision,
                "upstream_binary_host_description": {
                    "url": readme_url,
                    "sha256": sha(upstream_readme),
                },
                "upstream_capacitor_source_license": {
                    "url": license_url,
                    "spdx": "MIT",
                    "sha256": sha(upstream_license),
                },
                "binary_inputs": frameworks,
            },
            "cordova_apache_source_header": {
                "spdx": "Apache-2.0",
                "sha256": sha(header),
                "source": "@capacitor/ios/CapacitorCordova/CapacitorCordova/Classes/Public/CDV.h",
            },
            "pods": "not selected; no Podfile.lock",
            "system_frameworks": (
                "Apple SDK/toolchain inputs; not claimed open-source plugin dependencies"
            ),
        },
    )


def artifact_stats(path: Path, platform: str) -> dict[str, Any]:
    raw = read(path, (path.parent,), MAX_BINARY)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if (
            len(entries) > 30_000
            or sum(item.file_size for item in entries) > MAX_ZIP_BYTES
            or len({item.filename for item in entries}) != len(entries)
        ):
            refuse()
        activation = (
            "assets/public/gsip-activation.json"
            if platform == "android"
            else "App.app/public/gsip-activation.json"
        )
        if archive.namelist().count(activation) != 1:
            refuse()
        app_build.check_activation(archive.read(activation))
        kinds: dict[str, int] = {"dex": 0, "native_libraries": 0, "resources": 0, "other": 0}
        for item in entries:
            if item.is_dir():
                continue
            kind = (
                "dex"
                if re.fullmatch(r"classes[0-9]*\.dex", item.filename)
                else "native_libraries"
                if item.filename.startswith("lib/")
                else "resources"
                if item.filename.startswith("res/") or item.filename == "resources.arsc"
                else "other"
            )
            kinds[kind] += item.file_size
    return {
        "sha256": sha(raw),
        "archive_bytes": len(raw),
        "uncompressed_entry_bytes_by_kind": kinds,
    }


def record(value: Any, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        refuse()
    return cast(dict[str, Any], value)


def items(value: Any, limit: int, minimum: int = 1) -> list[Any]:
    if not isinstance(value, list) or not minimum <= len(value) <= limit:
        refuse()
    return value


def evidence_digest(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        refuse()
    return value


def count(value: Any, maximum: int, minimum: int = 1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        refuse()
    return value


def relative_name(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 512
        or "\\" in value
        or any(ord(char) < 32 for char in value)
        or Path(value).is_absolute()
        or not Path(value).parts
        or str(Path(value)) != value
        or ".." in Path(value).parts
    ):
        refuse()
    return value


def validate_notices(value: Any) -> None:
    names = []
    for notice in items(value, MAX_ITEMS, 0):
        row = record(notice, {"entry", "sha256", "bytes"})
        names.append(relative_name(row["entry"]))
        evidence_digest(row["sha256"])
        count(row["bytes"], MAX_META, 0)
    if len(set(names)) != len(names):
        refuse()


def validate_pom_chain(value: Any, expected: tuple[str, str, str]) -> str:
    chain = items(value, 8)
    seen = set()
    packaging = ""
    for index, entry in enumerate(chain):
        inherited = isinstance(entry, dict) and "inherits_license_from" in entry
        fields = {"coordinate", "pom_sha256", "pom_bytes", "origin", "packaging", "licenses"}
        row = record(entry, fields | ({"inherits_license_from"} if inherited else set()))
        actual = coordinate(row["coordinate"])
        if actual != expected or actual in seen:
            refuse()
        seen.add(actual)
        evidence_digest(row["pom_sha256"])
        count(row["pom_bytes"], MAX_META)
        if row["packaging"] not in {"jar", "aar", "pom"}:
            refuse()
        if index == 0:
            packaging = row["packaging"]
        relative = (
            f"{actual[0].replace('.', '/')}/{actual[1]}/{actual[2]}/{actual[1]}-{actual[2]}.pom"
        )
        if row["origin"] not in {
            "resolved Gradle metadata cache",
            *(base + relative for base in REPOSITORIES),
        }:
            refuse()
        licenses = items(row["licenses"], 10, 0)
        for entry_license in licenses:
            license_row = record(entry_license, {"spdx", "declared_name", "declared_url"})
            name, url = license_row["declared_name"], license_row["declared_url"]
            if (
                not isinstance(name, str)
                or len(name) > 200
                or license_id(name) != license_row["spdx"]
                or not isinstance(url, str)
                or len(url) > 500
                or not re.fullmatch(r"https?://[^\s<>]+", url)
            ):
                refuse()
        if inherited:
            if licenses or index == len(chain) - 1:
                refuse()
            expected = coordinate(row["inherits_license_from"])
        elif not licenses or index != len(chain) - 1:
            refuse()
    return packaging


def validate_npm(value: Any, source_commit: str) -> dict[str, dict[str, Any]]:
    required = set(NPM_PACKAGES) - {"@capacitor/local-notifications"}
    if source_commit != BASELINE:
        required.add("@capacitor/local-notifications")
    result = {}
    for entry in items(value, len(NPM_PACKAGES)):
        row = record(
            entry,
            {
                "name",
                "version",
                "package_json_sha256",
                "license",
                "license_sha256",
                "installed_source_bytes",
                "installed_file_count",
                "installed_source_manifest_sha256",
            },
        )
        name, version = row["name"], row["version"]
        if (
            not isinstance(name, str)
            or name not in NPM_PACKAGES
            or name in result
            or row["license"] != "MIT"
            or not isinstance(version, str)
            or not TOKEN.fullmatch(version)
        ):
            refuse()
        if (
            name in {"@capacitor/core", "@capacitor/android", "@capacitor/ios"}
            and version != "8.5.2"
        ):
            refuse()
        if name == "@capacitor/local-notifications" and version != "8.3.1":
            refuse()
        for key in ("package_json_sha256", "license_sha256", "installed_source_manifest_sha256"):
            evidence_digest(row[key])
        count(row["installed_source_bytes"], MAX_ZIP_BYTES)
        count(row["installed_file_count"], 10_000)
        result[name] = row
    if set(result) != required:
        refuse()
    return result


def validate_android(native: dict[str, Any], npm: dict[str, dict[str, Any]]) -> None:
    if native["scope"] != (
        "resolved inputs of both shipped runtime configurations; "
        "build/test/toolchain inputs are separate, not inferred shipped"
    ):
        refuse()
    for key in (
        "resolved_graph_sha256",
        "build_only_environment_sha256",
        "debug_signing_key_sha256",
    ):
        evidence_digest(native[key])
    if native["temporary_gradle_task_sha256"] != sha(GRADLE_TASK.encode()):
        refuse()
    trees = record(
        native["runtime_tree_sha256"], {"debugRuntimeClasspath", "releaseRuntimeClasspath"}
    )
    for digest in trees.values():
        evidence_digest(digest)
    configurations = set()
    for view in items(native["runtime_views"], 2):
        row = record(
            view,
            {"configuration", "selected_modules", "project_sources", "resolved_runtime_inputs"},
        )
        name = row["configuration"]
        if name not in trees or name in configurations:
            refuse()
        configurations.add(name)
        modules = {}
        for module in items(row["selected_modules"], MAX_ITEMS):
            selected = record(module, {"coordinate", "pom_license_evidence"})
            coord = coordinate(selected["coordinate"])
            if coord in modules or app_permissions.closed_dependencies(":".join(coord)):
                refuse()
            modules[coord] = validate_pom_chain(selected["pom_license_evidence"], coord)
        projects = {}
        for project in items(row["project_sources"], MAX_ITEMS):
            if not isinstance(project, dict) or not isinstance(project.get("project"), str):
                refuse()
            project_name = project["project"]
            if project_name in projects:
                refuse()
            if project_name == ":capacitor-cordova-android-plugins":
                project = record(project, {"project", "source"})
                if project["source"] != (
                    "generated empty Cordova compatibility project; "
                    "no third-party plugin source/binary"
                ):
                    refuse()
            else:
                project = record(project, {"project", "npm", "source_manifest_sha256"})
                package = PROJECT_PACKAGES.get(project_name)
                if (
                    package not in npm
                    or project["npm"] != package
                    or project["source_manifest_sha256"]
                    != npm[package]["installed_source_manifest_sha256"]
                ):
                    refuse()
            projects[project_name] = project
        expected_projects = {
            project for project, package in PROJECT_PACKAGES.items() if package in npm
        }
        if not expected_projects <= set(projects):
            refuse()
        module_binaries = set()
        project_binaries = set()
        identities = set()
        for binary in items(row["resolved_runtime_inputs"], MAX_ITEMS):
            if not isinstance(binary, dict):
                refuse()
            module = "coordinate" in binary
            fields = {"filename", "sha256", "bytes", "embedded_license_notice_files"}
            binary = record(binary, fields | ({"coordinate"} if module else {"project"}))
            filename = binary["filename"]
            if (
                not isinstance(filename, str)
                or not TOKEN.fullmatch(filename)
                or Path(filename).suffix not in {".aar", ".jar"}
            ):
                refuse()
            evidence_digest(binary["sha256"])
            count(binary["bytes"], MAX_BINARY)
            validate_notices(binary["embedded_license_notice_files"])
            if module:
                identity = coordinate(binary["coordinate"])
                if identity not in modules or modules[identity] == "pom":
                    refuse()
                module_binaries.add(identity)
            else:
                identity = binary["project"]
                if not isinstance(identity, str) or identity not in projects:
                    refuse()
                project_binaries.add(identity)
            if (identity, filename) in identities:
                refuse()
            identities.add((identity, filename))
        if (
            any(
                coord not in module_binaries
                for coord, packaging in modules.items()
                if packaging != "pom"
            )
            or not expected_projects <= project_binaries
        ):
            refuse()
    if configurations != set(trees):
        refuse()


def validate_tree(value: Any) -> None:
    tree = record(value, {"bytes", "file_count", "files", "tree_sha256"})
    files = items(tree["files"], 30_000)
    total = 0
    names = []
    for file in files:
        row = record(file, {"path", "sha256", "bytes"})
        names.append(relative_name(row["path"]))
        evidence_digest(row["sha256"])
        total += count(row["bytes"], MAX_BINARY)
    if (
        names != sorted(set(names))
        or tree["file_count"] != len(files)
        or tree["bytes"] != total
        or total > MAX_ZIP_BYTES
        or tree["tree_sha256"]
        != sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())
    ):
        refuse()


def validate_ios(
    native: dict[str, Any], npm: dict[str, dict[str, Any]], locks: dict[str, Any]
) -> None:
    spm = record(
        native["spm"],
        {
            "package_resolved_sha256",
            "pins",
            "selected_manifest_sha256",
            "checkout_revision",
            "release_tag_revision",
            "upstream_binary_host_description",
            "upstream_capacitor_source_license",
            "binary_inputs",
        },
    )
    pin = items(spm["pins"], 1)[0]
    if not isinstance(pin, dict):
        refuse()
    pin = record(pin, {"identity", "location", "state"} | ({"kind"} if "kind" in pin else set()))
    state = record(pin["state"], {"version", "revision"})
    revision = state["revision"]
    if (
        pin["identity"] != "capacitor-swift-pm"
        or pin["location"] != "https://github.com/ionic-team/capacitor-swift-pm.git"
        or ("kind" in pin and pin["kind"] != "remoteSourceControl")
        or state["version"] != "8.5.2"
        or not isinstance(revision, str)
        or not re.fullmatch(r"[0-9a-f]{40}", revision)
        or revision != spm["checkout_revision"]
        or revision != spm["release_tag_revision"]
    ):
        refuse()
    evidence_digest(spm["selected_manifest_sha256"])
    resolved = [value for name, value in locks.items() if name.endswith("/Package.resolved")]
    if len(resolved) != 1 or evidence_digest(spm["package_resolved_sha256"]) != resolved[0]:
        refuse()
    description = record(spm["upstream_binary_host_description"], {"url", "sha256"})
    license_source = record(spm["upstream_capacitor_source_license"], {"url", "spdx", "sha256"})
    if (
        description["url"]
        != "https://raw.githubusercontent.com/ionic-team/capacitor-swift-pm/8.5.2/README.md"
        or license_source["url"]
        != "https://raw.githubusercontent.com/ionic-team/capacitor/8.5.2/LICENSE"
        or license_source["spdx"] != "MIT"
        or license_source["sha256"] != npm["@capacitor/ios"]["license_sha256"]
    ):
        refuse()
    evidence_digest(description["sha256"])
    names = set()
    for binary in items(spm["binary_inputs"], 2):
        row = record(
            binary,
            {
                "name",
                "published_archive_url",
                "swift_manifest_checksum",
                "actual_resolved_tree",
                "archive",
                "license_source",
            },
        )
        name = row["name"]
        if name not in {"Capacitor", "Cordova"} or name in names:
            refuse()
        names.add(name)
        if (
            row["published_archive_url"]
            != f"https://github.com/ionic-team/capacitor-swift-pm/releases/download/8.5.2/{name}.xcframework.zip"
        ):
            refuse()
        archive = record(row["archive"], {"sha256", "bytes", "embedded_license_notice_files"})
        if evidence_digest(row["swift_manifest_checksum"]) != evidence_digest(archive["sha256"]):
            refuse()
        count(archive["bytes"], MAX_BINARY)
        validate_notices(archive["embedded_license_notice_files"])
        validate_tree(row["actual_resolved_tree"])
        if row["license_source"] != (
            "Capacitor npm ios MIT LICENSE; Cordova files additionally "
            "retain Apache-2.0 source headers; package metadata alone "
            "does not license other binary contents"
        ):
            refuse()
    if names != {"Capacitor", "Cordova"}:
        refuse()
    header = record(native["cordova_apache_source_header"], {"spdx", "sha256", "source"})
    if (
        header["spdx"] != "Apache-2.0"
        or header["source"]
        != "@capacitor/ios/CapacitorCordova/CapacitorCordova/Classes/Public/CDV.h"
    ):
        refuse()
    evidence_digest(header["sha256"])
    if (
        native["pods"] != "not selected; no Podfile.lock"
        or native["system_frameworks"]
        != "Apple SDK/toolchain inputs; not claimed open-source plugin dependencies"
    ):
        refuse()


def validate_native(native: dict[str, Any], build: dict[str, Any]) -> None:
    platform = build["platform"]
    common = {
        "schema_version",
        "platform",
        "source_commit",
        "source_inputs",
        "npm_sources",
        "built_artifact_sha256",
    }
    android = {
        "runtime_views",
        "temporary_gradle_task_sha256",
        "scope",
        "build_only_environment_sha256",
        "runtime_tree_sha256",
        "resolved_graph_sha256",
        "debug_signing_key_sha256",
    }
    ios = {"spm", "cordova_apache_source_header", "pods", "system_frameworks"}
    record(native, common | (android if platform == "android" else ios))
    if (
        native["schema_version"] != "gsip-app-notification-native-audit-v1"
        or native["source_commit"] != build["source_commit"]
        or native["platform"] != platform
    ):
        refuse()
    source_names = {
        "pnpm-lock.yaml",
        "apps/capture-pwa/package.json",
        "apps/capture-pwa/capacitor.config.ts",
        "scripts/app_permissions.py",
        "scripts/app_build.py",
    }
    if platform == "android":
        source_names |= {
            "apps/capture-pwa/android/gradle/wrapper/gradle-wrapper.properties",
            "apps/capture-pwa/android/build.gradle",
            "apps/capture-pwa/android/variables.gradle",
        }
    if evidence_digest(native["built_artifact_sha256"]) != build["artifact_sha256"]:
        refuse()
    inputs = record(native["source_inputs"], source_names)
    locks = build["lockfile_sha256"]
    if not isinstance(locks, dict) or not {"pnpm-lock.yaml", "uv.lock"} <= set(locks):
        refuse()
    for key, digest in inputs.items():
        evidence_digest(digest)
        if key in locks and digest != locks[key]:
            refuse()
    for key, digest in locks.items():
        relative_name(key)
        evidence_digest(digest)
        if key != "uv.lock" and not key.endswith("/Package.resolved") and key not in inputs:
            refuse()
    npm = validate_npm(native["npm_sources"], native["source_commit"])
    if platform == "android":
        if not {name for name in source_names if name.endswith((".gradle", ".properties"))} <= set(
            locks
        ):
            refuse()
        validate_android(native, npm)
    else:
        validate_ios(native, npm, locks)


def text_value(value: Any, maximum: int, *, multiline: bool = False) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= maximum
        or any(ord(char) < 32 and not (multiline and char == "\n") for char in value)
        or any(ord(char) > 126 for char in value)
    ):
        refuse()
    return value


def canonical_version(value: Any, *, prefix: str = "", minimum_major: int = 0) -> str:
    text = text_value(value, 64)
    match = re.fullmatch(
        re.escape(prefix) + r"(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})", text
    )
    if not match or int(match[1]) < minimum_major:
        refuse()
    return text


def validate_toolchain(value: Any, target: str) -> None:
    common = {"node", "pnpm", "python", "runner", "runner_image"}
    tools = record(
        value, common | ({"gradle", "java", "aapt2"} if target == "android" else {"xcode", "sdk"})
    )
    canonical_version(tools["node"], prefix="v", minimum_major=24)
    canonical_version(tools["pnpm"], minimum_major=1)
    python = text_value(tools["python"], 1_024)
    if not re.fullmatch(
        r"3\.(?:1[1-9]|[2-9][0-9])\.[0-9]{1,4} \([^\n\[\]]{1,512}\) \[[^\n\[\]]{1,256}\]", python
    ):
        refuse()
    runner = text_value(tools["runner"], 512)
    host = "Linux" if target == "android" else "macOS"
    if not re.fullmatch(re.escape(host) + r"-[A-Za-z0-9_.+-]{1,480}", runner):
        refuse()
    image = record(tools["runner_image"], {"ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH"})
    if (
        image["RUNNER_OS"] != host
        or not isinstance(image["RUNNER_ARCH"], str)
        or image["RUNNER_ARCH"] not in {"X64", "ARM64"}
    ):
        refuse()
    image_os = text_value(image["ImageOS"], 64)
    if not re.fullmatch(
        r"ubuntu[0-9]{2}" if target == "android" else r"macos[0-9]{2}(?:-arm64)?", image_os
    ):
        refuse()
    image_version = text_value(image["ImageVersion"], 64)
    if not re.fullmatch(r"[0-9]{8}\.[0-9]{1,8}(?:\.[0-9]{1,8})?", image_version):
        refuse()
    try:
        datetime.strptime(image_version.split(".")[0], "%Y%m%d")
    except ValueError:
        refuse()
    architecture = (
        "(?:x86_64|x86-64|amd64)" if image["RUNNER_ARCH"] == "X64" else "(?:arm64|aarch64)"
    )
    if not re.search(architecture, runner):
        refuse()
    if target == "ios":
        xcode = text_value(tools["xcode"], 256, multiline=True)
        if not re.fullmatch(
            r"Xcode [1-9][0-9]{0,3}(?:\.(?:0|[1-9][0-9]{0,3})){1,2}\n"
            r"Build version [0-9]{1,4}[A-Z][0-9]{1,8}[a-z]?",
            xcode,
        ):
            refuse()
        sdk = text_value(tools["sdk"], 32)
        if not re.fullmatch(r"[1-9][0-9]{0,3}(?:\.(?:0|[1-9][0-9]{0,3})){1,2}", sdk):
            refuse()
        return
    aapt = text_value(tools["aapt2"], 128)
    if not re.fullmatch(
        r"Android Asset Packaging Tool \(aapt\) [0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}-[0-9]{1,16}",
        aapt,
    ):
        refuse()
    java = text_value(tools["java"], 4_096, multiline=True).splitlines()
    if (
        len(java) != 3
        or not re.fullmatch(
            r'openjdk version "21(?:\.[0-9]{1,4}){0,3}" [0-9]{4}-[0-9]{2}-[0-9]{2}(?: LTS)?',
            java[0],
        )
        or not re.fullmatch(
            r"OpenJDK Runtime Environment [A-Za-z0-9._+ -]{1,256}\(build [A-Za-z0-9._+,-]{1,128}\)",
            java[1],
        )
        or not re.fullmatch(
            r"OpenJDK 64-Bit Server VM [A-Za-z0-9._+ -]{1,256}\(build "
            r"[A-Za-z0-9._+,-]{1,128}, mixed mode(?:, sharing)?\)",
            java[2],
        )
    ):
        refuse()
    try:
        datetime.strptime(java[0].split()[3], "%Y-%m-%d")
    except ValueError:
        refuse()
    gradle = text_value(tools["gradle"], 8_192, multiline=True)
    lines = [line.strip() for line in gradle.splitlines() if line.strip()]
    if (
        len(lines) < 10
        or lines[0] != "-" * 60
        or lines[2] != "-" * 60
        or not re.fullmatch(r"Gradle [1-9][0-9]{0,3}(?:\.[0-9]{1,4}){1,2}", lines[1])
    ):
        refuse()
    fields = {}
    for line in lines[3:]:
        name, separator, body = line.partition(":")
        if not separator or name in fields:
            refuse()
        fields[name] = body.strip()
    base = {"Build time", "Revision", "Kotlin", "Groovy", "Ant", "OS"}
    if set(fields) not in (base | {"JVM"}, base | {"Launcher JVM", "Daemon JVM"}):
        refuse()
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} UTC", fields["Build time"]
    ) or not re.fullmatch(r"[0-9a-f]{40}", fields["Revision"]):
        refuse()
    try:
        datetime.strptime(fields["Build time"], "%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        refuse()
    canonical_version(fields["Kotlin"])
    canonical_version(fields["Groovy"])
    if not re.fullmatch(
        r"Apache Ant\(TM\) version [0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4} "
        r"compiled on [A-Za-z]{3,12} [0-9]{1,2} [0-9]{4}",
        fields["Ant"],
    ):
        refuse()
    try:
        datetime.strptime(fields["Ant"].split(" compiled on ")[1], "%B %d %Y")
    except ValueError:
        refuse()
    if not re.fullmatch(
        r"Linux [A-Za-z0-9_.+-]{1,128} (?:amd64|x86_64|aarch64|arm64)", fields["OS"]
    ):
        refuse()
    for name in ("JVM", "Launcher JVM"):
        if name in fields and not re.fullmatch(
            r"21(?:\.[0-9]{1,4}){0,3} \([A-Za-z0-9 ._+(),=-]{1,256}\)", fields[name]
        ):
            refuse()
    if "Daemon JVM" in fields and not re.fullmatch(
        r"/[A-Za-z0-9_./+-]{1,512} \(no JDK specified, using current Java home\)",
        fields["Daemon JVM"],
    ):
        refuse()


def validate_build_receipt(value: dict[str, Any], artifact: Path, reference: Path | None) -> None:
    fields = {
        "source_commit",
        "platform",
        "marketing_version",
        "run_number",
        "android_version_code",
        "ios_build_version",
        "lockfile_sha256",
        "toolchain",
        "source_tree_clean",
        "comparison_scope",
        "artifact_sha256",
        "reference_sha256",
        "comparison",
    }
    record(value, fields)
    target = value["platform"]
    if (
        not isinstance(target, str)
        or target not in {"android", "ios"}
        or not isinstance(value["source_commit"], str)
        or not re.fullmatch(r"[0-9a-f]{40}", value["source_commit"])
    ):
        refuse()
    number = count(value["run_number"], app_build.MAX_RUN_NUMBER)
    if count(value["android_version_code"], app_build.MAX_RUN_NUMBER) != number:
        refuse()
    canonical_version(value["marketing_version"])
    index = number - 1
    if value["ios_build_version"] != f"{1 + index // 10_000}.{index // 100 % 100}.{index % 100}":
        refuse()
    if value["source_tree_clean"] is not True:
        refuse()
    expected_scope = "same run/generated project; actual repeated native build; " + (
        "Android shared disposable debug key"
        if target == "android"
        else "iOS unsigned simulator; signing disabled"
    )
    if value["comparison_scope"] != expected_scope:
        refuse()
    locks = value["lockfile_sha256"]
    if not isinstance(locks, dict):
        refuse()
    lock_names = {"pnpm-lock.yaml", "uv.lock"}
    if target == "android":
        lock_names |= {
            "apps/capture-pwa/android/gradle/wrapper/gradle-wrapper.properties",
            "apps/capture-pwa/android/build.gradle",
            "apps/capture-pwa/android/variables.gradle",
        }
    else:
        resolved = [
            name
            for name in locks
            if isinstance(name, str)
            and name.startswith("apps/capture-pwa/ios/")
            and name.endswith("/Package.resolved")
        ]
        if len(resolved) != 1:
            refuse()
        relative_name(resolved[0])
        lock_names.add(resolved[0])
    record(locks, lock_names)
    for digest in locks.values():
        evidence_digest(digest)
    validate_toolchain(value["toolchain"], target)
    actual = artifact_stats(artifact, target)
    if evidence_digest(value["artifact_sha256"]) != actual["sha256"]:
        refuse()
    reference_digest = evidence_digest(value["reference_sha256"])
    if reference is None:
        if reference_digest != actual["sha256"]:
            refuse()
        reference = artifact
    if artifact_stats(reference, target)["sha256"] != reference_digest:
        refuse()
    compared = record(
        value["comparison"],
        {
            "byte_equal",
            "entry_content_equal",
            "normalization",
            "changed_entries",
            "first_only",
            "second_only",
        },
    )
    if (
        type(compared["byte_equal"]) is not bool
        or type(compared["entry_content_equal"]) is not bool
    ):
        refuse()
    for name in ("changed_entries", "first_only", "second_only"):
        names = [relative_name(entry) for entry in items(compared[name], 30_000, 0)]
        if names != sorted(set(names)):
            refuse()
    if (
        sum(len(compared[name]) for name in ("changed_entries", "first_only", "second_only"))
        > 30_000
    ):
        refuse()
    if compared != app_build.comparison(reference, artifact):
        refuse()


def feature_comparison(
    parent: Path,
    candidate: Path,
    parent_receipt: dict[str, Any],
    candidate_receipt: dict[str, Any],
    expected_candidate: str,
    parent_audit: dict[str, Any],
    candidate_audit: dict[str, Any],
    parent_reference: Path | None = None,
    candidate_reference: Path | None = None,
) -> dict[str, Any]:
    validate_build_receipt(parent_receipt, parent, parent_reference)
    validate_build_receipt(candidate_receipt, candidate, candidate_reference)

    if (
        parent_receipt.get("source_commit") != BASELINE
        or candidate_receipt.get("source_commit") != expected_candidate
        or not re.fullmatch(r"[0-9a-f]{40}", expected_candidate)
    ):
        refuse()
    for key in (
        "platform",
        "run_number",
        "marketing_version",
        "android_version_code",
        "ios_build_version",
        "toolchain",
        "comparison_scope",
    ):
        if parent_receipt.get(key) != candidate_receipt.get(key) or key not in parent_receipt:
            refuse()
    if (
        candidate_receipt.get("source_tree_clean") is not True
        or parent_receipt.get("source_tree_clean") is not True
    ):
        refuse()
    if parent_receipt.get("artifact_sha256") != sha(
        read(parent, (parent.parent,), MAX_BINARY)
    ) or candidate_receipt.get("artifact_sha256") != sha(
        read(candidate, (candidate.parent,), MAX_BINARY)
    ):
        refuse()
    platform = parent_receipt["platform"]
    if (
        platform not in {"android", "ios"}
        or parent_audit.get("platform") != platform
        or candidate_audit.get("platform") != platform
    ):
        refuse()
    for native, build in ((parent_audit, parent_receipt), (candidate_audit, candidate_receipt)):
        validate_native(native, build)
    if platform == "android":
        signing_key = parent_audit.get("debug_signing_key_sha256")
        if (
            not isinstance(signing_key, str)
            or not re.fullmatch(r"[0-9a-f]{64}", signing_key)
            or signing_key != candidate_audit.get("debug_signing_key_sha256")
        ):
            refuse()
    left, right = artifact_stats(parent, platform), artifact_stats(candidate, platform)
    return {
        "schema_version": "gsip-app2b-feature-comparison-v1",
        "scope": (
            "overall APP-2B feature delta from exact pinned parent; "
            "no dependency-only attribution or universal reproducibility claim"
        ),
        "parent_source_commit": BASELINE,
        "candidate_source_commit": expected_candidate,
        "identical_toolchain": parent_receipt["toolchain"],
        "run_number": parent_receipt["run_number"],
        "closed_flags": {"capture_live": False, "library_intake_live": False},
        "parent": left,
        "candidate": right,
        "archive_byte_delta": right["archive_bytes"] - left["archive_bytes"],
        "zip_comparison": app_build.comparison(parent, candidate),
        "input_receipts": {"parent": parent_receipt, "candidate": candidate_receipt},
        "native_audit_sha256": {
            "parent": sha(json.dumps(parent_audit, sort_keys=True).encode()),
            "candidate": sha(json.dumps(candidate_audit, sort_keys=True).encode()),
        },
        "android_shared_disposable_debug_key_sha256": parent_audit.get("debug_signing_key_sha256"),
    }


def write(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
    if len(payload) > 10_000_000:
        refuse()
    path.write_bytes(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    android = commands.add_parser("android")
    android.add_argument("repo", type=Path)
    android.add_argument("cache", type=Path)
    android.add_argument("output", type=Path)
    android.add_argument("debug_key", type=Path)
    ios = commands.add_parser("ios")
    ios.add_argument("repo", type=Path)
    ios.add_argument("output", type=Path)
    ios.add_argument("artifact", type=Path)
    compare = commands.add_parser("compare")
    compare.add_argument("parent", type=Path)
    compare.add_argument("candidate", type=Path)
    compare.add_argument("parent_receipt", type=Path)
    compare.add_argument("candidate_receipt", type=Path)
    compare.add_argument("candidate_commit")
    compare.add_argument("output", type=Path)
    compare.add_argument("parent_audit", type=Path)
    compare.add_argument("candidate_audit", type=Path)
    compare.add_argument("parent_reference", type=Path)
    compare.add_argument("candidate_reference", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "android":
            collect_android(args.repo.resolve(), args.cache.resolve(), args.output, args.debug_key)
        elif args.action == "ios":
            collect_ios(args.repo.resolve(), args.output, args.artifact)
        else:
            left = decoded(read(args.parent_receipt, (args.parent_receipt.parent,), 10_000_000))
            right = decoded(
                read(args.candidate_receipt, (args.candidate_receipt.parent,), 10_000_000)
            )
            left_audit = decoded(read(args.parent_audit, (args.parent_audit.parent,), 10_000_000))
            right_audit = decoded(
                read(args.candidate_audit, (args.candidate_audit.parent,), 10_000_000)
            )
            write(
                args.output,
                feature_comparison(
                    args.parent,
                    args.candidate,
                    left,
                    right,
                    args.candidate_commit,
                    left_audit,
                    right_audit,
                    args.parent_reference,
                    args.candidate_reference,
                ),
            )
        print("native-audit: bounded evidence recorded")
        return 0
    except (
        ValueError,
        OSError,
        ET.ParseError,
        subprocess.SubprocessError,
        zipfile.BadZipFile,
        urllib.error.URLError,
        TypeError,
        KeyError,
        RecursionError,
        RuntimeError,
    ):
        print("native-audit: evidence missing, invalid or unreviewed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
