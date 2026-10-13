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
import tarfile
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


DIAGNOSTIC_STAGES = {
    "start",
    "android-dependency-trees",
    "android-build-environment",
    "android-gradle-inspection",
    "android-npm-sources",
    "android-runtime-graph",
    "android-runtime-licenses",
    "android-project-sources",
    "android-runtime-binaries",
    "android-source-bindings",
    "ios-pods",
    "ios-resolution",
    "ios-remote-sources",
    "ios-capacitor-checkout",
    "ios-capacitor-licenses",
    "ios-capacitor-binaries",
    "ios-npm-sources",
    "ios-source-bindings",
    "feature-comparison",
}
DIAGNOSTIC_COUNTS = {
    "runtime_views",
    "module_inputs",
    "project_inputs",
    "remote_pins",
    "resolved_files",
    "source_packages",
}
_diagnostic_stage = "start"
_diagnostic_counts: dict[str, int] = {}
MAX_DIAGNOSTIC_BYTES = 65_536


def mark(stage: str, **counts: int) -> None:
    global _diagnostic_stage, _diagnostic_counts
    if stage not in DIAGNOSTIC_STAGES or not set(counts) <= DIAGNOSTIC_COUNTS:
        refuse()
    if any(type(value) is not int or not 0 <= value <= 30_000 for value in counts.values()):
        refuse()
    _diagnostic_stage = stage
    _diagnostic_counts = counts


def gradle_failure_class(error: subprocess.CalledProcessError) -> str:
    """Inspect bounded tool output in memory; return only an unambiguous fixed label."""
    args = error.cmd
    if (
        type(error.returncode) is not int
        or error.returncode == 0
        or type(args) not in (list, tuple)
        or len(args) != 7
        or any(
            type(arg) is not str
            or not 0 < len(arg) <= 4096
            or any(ord(char) < 32 or ord(char) == 127 for char in arg)
            for arg in args
        )
        or not Path(args[0]).is_absolute()
        or Path(args[0]).name != "gradlew"
        or list(args[1:4]) != ["--no-daemon", "--console=plain", "-I"]
        or not Path(args[4]).is_absolute()
        or Path(args[4]).name != "inspection.gradle"
        or args[5] != ":app:gsipRuntimeEvidence"
        or not args[6].startswith("-PgsipEvidenceOutput=")
        or not Path(args[6].removeprefix("-PgsipEvidenceOutput=")).is_absolute()
    ):
        return "BUILD_TOOL"
    streams = []
    size = 0
    for raw in (error.stdout, error.stderr):
        if raw is None:
            continue
        if type(raw) not in (str, bytes) or len(raw) > MAX_DIAGNOSTIC_BYTES:
            return "BUILD_TOOL"
        try:
            text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            size += len(text.encode("utf-8"))
        except UnicodeError:
            return "BUILD_TOOL"
        if size > MAX_DIAGNOSTIC_BYTES or any(
            (ord(char) < 32 and char not in "\n\r\t") or ord(char) == 127 for char in text
        ):
            return "BUILD_TOOL"
        streams.append(text.replace("\r\n", "\n"))
    text = "\n".join(streams)
    header = "FAILURE: Build failed with an exception.\n"
    marker = "* What went wrong:\n"
    if text.count(header) != 1 or text.count(marker) != 1 or text.count("* Try:\n") != 1:
        return "BUILD_TOOL"
    after_header = text.split(header, 1)[1]
    if marker not in after_header:
        return "BUILD_TOOL"
    after_marker = after_header.split(marker, 1)[1]
    if "* Try:\n" not in after_marker:
        return "BUILD_TOOL"
    section, after_try = after_marker.split("* Try:\n", 1)
    if not re.search(r"(?m)^BUILD FAILED in [0-9][0-9a-z .]*$", after_try):
        return "BUILD_TOOL"
    section = section.strip()
    if section == "Task 'gsipRuntimeEvidence' not found in project ':app'.":
        return "GRADLE_TASK_MISSING"
    execution = "Execution failed for task ':app:gsipRuntimeEvidence'.\n"
    if not section.startswith(execution):
        return "BUILD_TOOL"
    reason_lines = [line.strip() for line in section[len(execution) :].splitlines() if line.strip()]
    if not reason_lines or any(not line.startswith("> ") for line in reason_lines):
        return "BUILD_TOOL"
    reasons = {line.removeprefix("> ").strip() for line in reason_lines}
    labels = set()
    for reason, label in (
        ("unsupported runtime component", "GRADLE_COMPONENT_UNSUPPORTED"),
        ("unsupported runtime artifact", "GRADLE_ARTIFACT_UNSUPPORTED"),
    ):
        if reason in reasons:
            labels.add(label)
    if any(
        re.fullmatch(r"Configuration with name '(?:debug|release)RuntimeClasspath' not found\.", r)
        for r in reasons
    ):
        labels.add("GRADLE_CONFIGURATION_MISSING")
    if any(
        re.fullmatch(
            r"Could not get unknown property '(?:projectPath|componentIdentifier|group|module|"
            r"version|resolvedArtifacts|canonicalPath)' for .+\.",
            reason,
        )
        for reason in reasons
    ):
        labels.add("GRADLE_INSPECTION_API")
    resolution = any(
        re.fullmatch(
            r"Could not resolve all artifacts for configuration ':app:(?:debug|release)"
            r"RuntimeClasspath'\.",
            reason,
        )
        for reason in reasons
    )
    if resolution and any(re.fullmatch(r"File .+ does not exist\.", r) for r in reasons):
        labels.add("GRADLE_RUNTIME_FILE_MISSING")
    if (
        resolution
        and any(re.fullmatch(r"Could not GET .+", r) for r in reasons)
        and reasons & {"Connection timed out", "Remote host terminated the handshake"}
    ):
        labels.add("GRADLE_DEPENDENCY_NETWORK")
    return next(iter(labels)) if len(labels) == 1 else "BUILD_TOOL"


def diagnostic(error: BaseException) -> dict[str, Any]:
    category = next(
        (
            label
            for kind, label in (
                (AuditError, "AUDIT_REFUSAL"),
                (FileNotFoundError, "MISSING_FILE"),
                (PermissionError, "FILE_PERMISSION"),
                (urllib.error.URLError, "PUBLIC_METADATA"),
                (subprocess.SubprocessError, "BUILD_TOOL"),
                (zipfile.BadZipFile, "INVALID_ARCHIVE"),
                (tarfile.TarError, "INVALID_ARCHIVE"),
                (ET.ParseError, "MALFORMED_METADATA"),
                (OSError, "FILE_ERROR"),
                (ValueError, "MALFORMED_METADATA"),
            )
            if isinstance(error, kind)
        ),
        "INVALID_EVIDENCE",
    )
    if _diagnostic_stage == "android-gradle-inspection" and isinstance(
        error, subprocess.CalledProcessError
    ):
        category = gradle_failure_class(error)
    line = 0
    trace = error.__traceback__
    while trace is not None:
        if trace.tb_frame.f_code.co_filename == __file__:
            line = trace.tb_lineno
        trace = trace.tb_next
    return {
        "stage": _diagnostic_stage,
        "error_class": category,
        "source_line": line,
        "counts": _diagnostic_counts,
    }


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
    fd = os.open(absolute, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
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
    mark("android-runtime-graph")
    views = data.get("views")
    if (
        not isinstance(views, list)
        or len(views) != 2
        or {view.get("name") for view in views if isinstance(view, dict)}
        != {"debugRuntimeClasspath", "releaseRuntimeClasspath"}
    ):
        refuse()
    mark("android-npm-sources")
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
        mark("android-runtime-licenses", module_inputs=len(modules))
        selected = []
        for coord in modules:
            selected.append(
                {
                    "coordinate": list(coord),
                    "pom_license_evidence": pom_evidence(coord, cache, allow_fetch),
                }
            )
        mark("android-project-sources", project_inputs=len(view["projects"]))
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
        mark(
            "android-runtime-binaries",
            module_inputs=len(modules),
            project_inputs=len(view["projects"]),
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
    mark("android-dependency-trees")
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
    mark("android-build-environment")
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
        mark("android-gradle-inspection")
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
    mark("android-source-bindings")
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
    files.sort(key=lambda item: item["path"])
    return {
        "bytes": total,
        "file_count": len(files),
        "files": files,
        "tree_sha256": sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()),
    }


# Reviewed existing selected remote source dependencies, exact public tag evidence.
ION_PACKAGES: dict[str, dict[str, Any]] = {
    "ion-ios-camera": {
        "version": "2.0.0",
        "revision": "00c3dfdd6267f80db299d9c5a0bad522156b6cbc",
        "manifest_sha256": "9c996d5e3d272926b9ca7375db032769554479b39088f3c6261a9b6db3f0e398",
        "license_sha256": "731d2fac39f3d6dc79c04f9a7d2e59c2999caa0dd1dbcf295f9c0e922580dacc",
        "archive_sha256": "973aa971e499abe35869c939dddb31ebec2c11b1e646cda3c2eb3fe95329b322",
        "source_tree_sha256": "ee2d399fea29b2136b17f6183fe7fb4afd528f71f193e40a78b1f34c233fd3bf",
        "source_bytes": 522080,
        "source_file_count": 110,
        "archive_bytes": 273170,
        "test_dependencies": [
            {"location": "https://github.com/Quick/Nimble.git", "minimum_version": "13.0.0"},
            {"location": "https://github.com/Quick/Quick.git", "minimum_version": "7.0.0"},
        ],
    },
    "ion-ios-filesystem": {
        "version": "1.1.4",
        "revision": "56bd6f9e77cb4f2269c03f2d92a9fe58fe168a1c",
        "manifest_sha256": "2af20bd56bf4fd79f19e89fcc8bf524c225edece060ea1e08d0970799481d465",
        "license_sha256": "de884404585ed20280150b0768082b6004d3548aaa0d6e596d6bfa0538ab331d",
        "archive_sha256": "8efe6d8d1dd40b6894d5c128e9bb81bc557f8d58d3c4c4f6dc12ab9ac5c891d9",
        "source_tree_sha256": "e9b94d4a60923891b387d45fe7be988ab21e343ccd705901bbc046acc590b057",
        "source_bytes": 150959,
        "source_file_count": 36,
        "archive_bytes": 31020,
        "test_dependencies": [],
    },
    "ion-ios-geolocation": {
        "version": "2.1.1",
        "revision": "db363927d3a954e3ea24d2e72b6e9814769a84be",
        "manifest_sha256": "1afefd99f4747c429c71ccd2823a8623095da3b9a2fa0df7f341f31beb310245",
        "license_sha256": "de884404585ed20280150b0768082b6004d3548aaa0d6e596d6bfa0538ab331d",
        "archive_sha256": "bbff6b0ab17490d7ef80b18af0f520a83f4eee3c042fa980c0f60c234bff33fb",
        "source_tree_sha256": "8d834e023fc57cdcf8cb183d29db71dd089219f802c5baf3aae24b78c7d0476b",
        "source_bytes": 95915,
        "source_file_count": 35,
        "archive_bytes": 23644,
        "test_dependencies": [],
    },
}
CAPACITOR_RELEASE: dict[str, Any] = {
    "version": "8.5.2",
    "revision": "0b6882e9a3288342aacf36348e5a94e4f1dd7b13",
    "manifest_sha256": "d438f723a12d16a803aeb0b81d1160a04ead205f74614a2b97aa8965acf95a72",
    "readme_sha256": "da248c966f5d41d4a36967eaace66fc6c8436f46c4fbad3434df3f54b737d9c4",
    "license_sha256": "9c6ebf3e5ab832ba4d5af38f340978e1fedbfee6e3d23662dfdb8917a9d864dd",
    "cordova_header_sha256": "5b015a36af3df0bb49cfc97f9092f75e48fd02c56f366d674667b7cde888db13",
    "source_archive_sha256": "4299321005ae1e8fa981eda92b2bd263eda6008baf249818cd794c2c8f22f667",
    "source_archive_bytes": 3549,
    "source_tree": {
        "bytes": 9594,
        "file_count": 9,
        "tree_sha256": "a9db722c3e4ffbb6bcd049ca844a64dafde4a92d70c70f170779502b09122652",
    },
    "binaries": {
        "Capacitor": {
            "sha256": "134c65a8bd30bfaa8ccb158d78142fa7231bf3f472e4a5d808c5fbed90fd4c75",
            "archive_bytes": 6611661,
            "tree_sha256": "50de18f4b668ee63f13f6def160a3793a0b4c2da64bed3bd6f4364ec7d82f8bc",
            "file_count": 54,
            "bytes": 23980848,
        },
        "Cordova": {
            "sha256": "57ff2c8f1e5dcd8d4379ac3cccde1407d81ccd575347dc2aff4f72272b8794a1",
            "archive_bytes": 1842451,
            "tree_sha256": "10f6b5162f8953a32d8a2285ea6fe885ae8f72955962c003160f51b77e4bf2da",
            "file_count": 58,
            "bytes": 4838267,
        },
    },
}

APPLICATION_RESOLVED = (
    "apps/capture-pwa/ios/App/App.xcodeproj/project.xcworkspace/"
    "xcshareddata/swiftpm/Package.resolved"
)
UPSTREAM_RESOLVED = {
    "ion-ios-filesystem": (
        "IONFilesystemLib.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
    ),
    "ion-ios-geolocation": (
        "IONGeolocationLib.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
    ),
}
SWIFTLINT_PIN = {
    "identity": "swiftlintplugins",
    "kind": "remoteSourceControl",
    "location": "https://github.com/SimplyDanny/SwiftLintPlugins",
    "state": {"revision": "f9731bef175c3eea3a0ca960f1be78fcc2bc7853", "version": "0.57.1"},
}


def selected_pins(value: Any) -> dict[str, dict[str, Any]]:
    pins = items(value, 4)
    result = {}
    for value in pins:
        if not isinstance(value, dict):
            refuse()
        pin = record(
            value, {"identity", "location", "state"} | ({"kind"} if "kind" in value else set())
        )
        identity = pin["identity"]
        if not isinstance(identity, str) or identity in result:
            refuse()
        expected = ION_PACKAGES.get(identity)
        version = expected["version"] if expected else "8.5.2"
        if (
            identity not in {"capacitor-swift-pm", *ION_PACKAGES}
            or pin["location"] != f"https://github.com/ionic-team/{identity}.git"
            or ("kind" in pin and pin["kind"] != "remoteSourceControl")
        ):
            refuse()
        state = record(pin["state"], {"version", "revision"})
        if (
            state["version"] != version
            or not isinstance(state["revision"], str)
            or not re.fullmatch(r"[0-9a-f]{40}", state["revision"])
            or state["revision"]
            != (expected["revision"] if expected is not None else CAPACITOR_RELEASE["revision"])
        ):
            refuse()
        result[identity] = pin
    if set(result) != {"capacitor-swift-pm", *ION_PACKAGES}:
        refuse()
    return result


def source_archive(data: bytes, identity: str, version: str) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    total = 0
    prefix = f"{identity}-{version}/"
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive:
            if member.isdir():
                continue
            if not member.isfile() or not member.name.startswith(prefix):
                refuse()
            path = relative_name(member.name[len(prefix) :])
            if path.endswith((".jar", ".aar", ".a", ".dylib", ".zip")) or any(
                part.endswith((".framework", ".xcframework")) for part in Path(path).parts
            ):
                refuse()
            if not 0 <= member.size <= MAX_BINARY:
                refuse()
            stream = archive.extractfile(member)
            if stream is None:
                refuse()
            payload = stream.read(MAX_BINARY + 1)
            if len(payload) != member.size:
                refuse()
            total += len(payload)
            files.append({"path": path, "bytes": len(payload), "sha256": sha(payload)})
            if total > MAX_ZIP_BYTES or len(files) > 30_000:
                refuse()
    files.sort(key=lambda item: item["path"])
    if not files or len({item["path"] for item in files}) != len(files):
        refuse()
    return {
        "bytes": total,
        "file_count": len(files),
        "files": files,
        "tree_sha256": sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()),
    }


def checkout_source_tree(checkout: Path, repo: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    total = 0
    for file in sorted(checkout.rglob("*")):
        relative = file.relative_to(checkout)
        if relative.parts[0] == ".git":
            continue  # Git metadata is not package source and is never read.
        if file.is_symlink():
            refuse()
        if file.is_dir():
            continue
        payload = read(file, (repo,), MAX_BINARY, allow_empty=True)
        total += len(payload)
        files.append({"path": str(relative), "bytes": len(payload), "sha256": sha(payload)})
        if total > MAX_ZIP_BYTES or len(files) > 30_000:
            refuse()
    if not files:
        refuse()
    files.sort(key=lambda item: item["path"])
    return {
        "bytes": total,
        "file_count": len(files),
        "files": files,
        "tree_sha256": sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()),
    }


def collect_remote_sources(repo: Path, pins: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for identity, expected in sorted(ION_PACKAGES.items()):
        checkout = repo / f"apps/capture-pwa/ios/App/build/SourcePackages/checkouts/{identity}"
        contained(checkout, (repo,))
        head = run(["git", "-C", str(checkout), "rev-parse", "HEAD"])
        tag = run(
            ["git", "-C", str(checkout), "rev-parse", f"refs/tags/{expected['version']}^{{commit}}"]
        )
        if head != pins[identity]["state"]["revision"] or tag != head:
            refuse()
        manifest = read(checkout / "Package.swift", (repo,))
        license_data = read(checkout / "LICENSE", (repo,))
        if (
            sha(manifest) != expected["manifest_sha256"]
            or sha(license_data) != expected["license_sha256"]
            or b".binaryTarget" in manifest
            or b"Permission is hereby granted" not in license_data
        ):
            refuse()
        url = f"https://codeload.github.com/ionic-team/{identity}/tar.gz/refs/tags/{expected['version']}"
        data = public_bytes(url, MAX_BINARY)
        if sha(data) != expected["archive_sha256"]:
            refuse()
        published = source_archive(data, identity, expected["version"])
        actual = checkout_source_tree(checkout, repo)
        if published != actual:
            refuse()
        result.append(
            {
                "identity": identity,
                "location": pins[identity]["location"],
                "version": expected["version"],
                "checkout_revision": head,
                "release_tag_revision": tag,
                "manifest_sha256": sha(manifest),
                "license": {
                    "spdx": "MIT",
                    "sha256": sha(license_data),
                    "source": f"https://raw.githubusercontent.com/ionic-team/{identity}/{expected['version']}/LICENSE",
                },
                "source_archive": {"url": url, "sha256": sha(data), "bytes": len(data)},
                "actual_source_tree": actual,
                "test_only_dependencies": expected["test_dependencies"],
                "runtime_remote_dependencies": [],
                "binary_targets": [],
            }
        )
    return result


def resolved_inventory(repo: Path, application_pins: Any) -> list[dict[str, Any]]:
    ios = repo / "apps/capture-pwa/ios"
    expected = {APPLICATION_RESOLVED: "application selected graph"}
    for identity, relative in UPSTREAM_RESOLVED.items():
        expected[
            f"apps/capture-pwa/ios/App/build/SourcePackages/checkouts/{identity}/{relative}"
        ] = "upstream development project tool lock; not selected in application graph"
    paths = list(ios.rglob("Package.resolved"))
    if {str(path.relative_to(repo)) for path in paths} != set(expected):
        refuse()
    result = []
    for path in sorted(paths):
        raw = read(path, (repo,))
        value = decoded(raw)
        relative = str(path.relative_to(repo))
        keys = (
            {"pins"}
            | ({"version"} if "version" in value else set())
            | ({"originHash"} if "originHash" in value else set())
        )
        record(value, keys)
        if "version" in value and (
            type(value["version"]) is not int or value["version"] not in {1, 2, 3}
        ):
            refuse()
        if "originHash" in value:
            evidence_digest(value["originHash"])
        if relative == APPLICATION_RESOLVED:
            selected_pins(value["pins"])
            if value["pins"] != application_pins:
                refuse()
        elif value["pins"] != [SWIFTLINT_PIN]:
            refuse()
        result.append(
            {
                "path": relative,
                "sha256": sha(raw),
                "scope": expected[relative],
                "pins": value["pins"],
            }
        )
    return result


def collect_ios(repo: Path, output: Path, artifact: Path | None = None) -> None:
    artifact = artifact if artifact is not None else repo / "gsip-capture-ios-simulator.zip"
    ios = repo / "apps/capture-pwa/ios"
    mark("ios-pods")
    if list(ios.rglob("Podfile.lock")):
        refuse()  # This workflow selects SPM; a new Pod resolution needs an explicit audit adapter.
    mark("ios-resolution")
    raw = read(repo / APPLICATION_RESOLVED, (repo,))
    resolved = decoded(raw)
    pins = resolved.get("pins")
    selected = selected_pins(pins)
    inventory = resolved_inventory(repo, pins)
    mark("ios-remote-sources", remote_pins=len(selected), resolved_files=len(inventory))
    remote_sources = collect_remote_sources(repo, selected)
    pin = selected["capacitor-swift-pm"]
    state = pin["state"]
    mark("ios-capacitor-checkout")
    checkout = ios / "App/build/SourcePackages/checkouts/capacitor-swift-pm"
    contained(checkout, (repo,))
    checkout_revision = run(["git", "-C", str(checkout), "rev-parse", "HEAD"])
    release_revision = run(["git", "-C", str(checkout), "rev-parse", "refs/tags/8.5.2^{commit}"])
    if checkout_revision != state["revision"] or release_revision != checkout_revision:
        refuse()
    manifest = read(checkout / "Package.swift", (repo,))
    manifest_text = manifest.decode()
    if sha(manifest) != CAPACITOR_RELEASE["manifest_sha256"]:
        refuse()
    source_url = "https://codeload.github.com/ionic-team/capacitor-swift-pm/tar.gz/refs/tags/8.5.2"
    source_data = public_bytes(source_url, MAX_BINARY)
    if (
        sha(source_data) != CAPACITOR_RELEASE["source_archive_sha256"]
        or len(source_data) != CAPACITOR_RELEASE["source_archive_bytes"]
    ):
        refuse()
    published_source = source_archive(source_data, "capacitor-swift-pm", "8.5.2")
    actual_source = checkout_source_tree(checkout, repo)
    if published_source != actual_source:
        refuse()
    capacitor_source = {
        "identity": "capacitor-swift-pm",
        "location": pin["location"],
        "version": "8.5.2",
        "checkout_revision": checkout_revision,
        "release_tag_revision": release_revision,
        "manifest_sha256": sha(manifest),
        "source_archive": {
            "url": source_url,
            "sha256": sha(source_data),
            "bytes": len(source_data),
        },
        "actual_source_tree": actual_source,
    }
    validate_capacitor_source(capacitor_source)

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
    mark("ios-capacitor-licenses")
    readme_url = "https://raw.githubusercontent.com/ionic-team/capacitor-swift-pm/8.5.2/README.md"
    license_url = "https://raw.githubusercontent.com/ionic-team/capacitor/8.5.2/LICENSE"
    upstream_readme = public_bytes(readme_url, MAX_META)
    upstream_license = public_bytes(license_url, MAX_META)
    installed_ios = (repo / "apps/capture-pwa/node_modules/@capacitor/ios").resolve()
    if (
        b"binary xcframework releases of Capacitor and CapacitorCordova" not in upstream_readme
        or sha(upstream_readme) != CAPACITOR_RELEASE["readme_sha256"]
        or sha(upstream_license) != CAPACITOR_RELEASE["license_sha256"]
        or upstream_license != read(installed_ios / "LICENSE", (repo / "node_modules",))
    ):
        refuse()
    mark("ios-capacitor-binaries")
    frameworks = []
    for name, url, checksum in matches:
        if (
            not url.endswith(f"/{name}.xcframework.zip")
            or checksum != CAPACITOR_RELEASE["binaries"][name]["sha256"]
        ):
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
        binary_record = {
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
        validate_capacitor_binary(binary_record)
        frameworks.append(binary_record)
    mark("ios-npm-sources")
    npm = npm_evidence(repo, NPM_PACKAGES)
    ios_package = (repo / "apps/capture-pwa/node_modules/@capacitor/ios").resolve()
    header = read(
        ios_package / "CapacitorCordova/CapacitorCordova/Classes/Public/CDV.h",
        (repo / "node_modules",),
    )
    if (
        b"Apache License, Version 2.0" not in header
        or sha(header) != CAPACITOR_RELEASE["cordova_header_sha256"]
    ):
        refuse()
    mark("ios-source-bindings")
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
                "resolved_inventory": inventory,
                "remote_source_packages": remote_sources,
                "capacitor_source": capacitor_source,
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


def validate_tree(value: Any, *, allow_empty_files: bool = False) -> None:
    tree = record(value, {"bytes", "file_count", "files", "tree_sha256"})
    files = items(tree["files"], 30_000)
    total = 0
    names = []
    for file in files:
        row = record(file, {"path", "sha256", "bytes"})
        names.append(relative_name(row["path"]))
        evidence_digest(row["sha256"])
        total += count(row["bytes"], MAX_BINARY, 0 if allow_empty_files else 1)
    if (
        names != sorted(set(names))
        or tree["file_count"] != len(files)
        or tree["bytes"] != total
        or total > MAX_ZIP_BYTES
        or tree["tree_sha256"]
        != sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())
    ):
        refuse()


def validate_source_packages(value: Any, pins: dict[str, dict[str, Any]]) -> None:
    identities = []
    for item in items(value, 3):
        row = record(
            item,
            {
                "identity",
                "location",
                "version",
                "checkout_revision",
                "release_tag_revision",
                "manifest_sha256",
                "license",
                "source_archive",
                "actual_source_tree",
                "test_only_dependencies",
                "runtime_remote_dependencies",
                "binary_targets",
            },
        )
        identity = row["identity"]
        if not isinstance(identity, str) or identity not in ION_PACKAGES or identity in identities:
            refuse()
        identities.append(identity)
        expected = ION_PACKAGES[identity]
        if (
            row["location"] != pins[identity]["location"]
            or row["version"] != expected["version"]
            or row["checkout_revision"] != pins[identity]["state"]["revision"]
            or row["release_tag_revision"] != row["checkout_revision"]
            or evidence_digest(row["manifest_sha256"]) != expected["manifest_sha256"]
            or row["test_only_dependencies"] != expected["test_dependencies"]
            or row["runtime_remote_dependencies"] != []
            or row["binary_targets"] != []
        ):
            refuse()
        license_source = record(row["license"], {"spdx", "sha256", "source"})
        archive = record(row["source_archive"], {"url", "sha256", "bytes"})
        if (
            license_source["spdx"] != "MIT"
            or evidence_digest(license_source["sha256"]) != expected["license_sha256"]
            or license_source["source"]
            != f"https://raw.githubusercontent.com/ionic-team/{identity}/{expected['version']}/LICENSE"
            or archive["url"]
            != f"https://codeload.github.com/ionic-team/{identity}/tar.gz/refs/tags/{expected['version']}"
            or evidence_digest(archive["sha256"]) != expected["archive_sha256"]
        ):
            refuse()
        if count(archive["bytes"], MAX_BINARY) != expected["archive_bytes"]:
            refuse()
        validate_tree(row["actual_source_tree"], allow_empty_files=True)
        if (
            row["actual_source_tree"]["tree_sha256"] != expected["source_tree_sha256"]
            or row["actual_source_tree"]["bytes"] != expected["source_bytes"]
            or row["actual_source_tree"]["file_count"] != expected["source_file_count"]
        ):
            refuse()
        source_files = {file["path"]: file["sha256"] for file in row["actual_source_tree"]["files"]}
        if (
            source_files.get("LICENSE") != license_source["sha256"]
            or source_files.get("Package.swift") != row["manifest_sha256"]
        ):
            refuse()
    if set(identities) != set(ION_PACKAGES):
        refuse()


def validate_resolved_inventory(
    value: Any, pins: Any, locks: dict[str, Any], remote_sources: Any
) -> None:
    expected = {APPLICATION_RESOLVED: "application selected graph"}
    for identity, relative in UPSTREAM_RESOLVED.items():
        expected[
            f"apps/capture-pwa/ios/App/build/SourcePackages/checkouts/{identity}/{relative}"
        ] = "upstream development project tool lock; not selected in application graph"
    actual = set()
    for item in items(value, 3):
        row = record(item, {"path", "sha256", "scope", "pins"})
        path = relative_name(row["path"])
        if path not in expected or path in actual or row["scope"] != expected[path]:
            refuse()
        actual.add(path)
        if evidence_digest(row["sha256"]) != locks.get(path):
            refuse()
        if row["pins"] != (pins if path == APPLICATION_RESOLVED else [SWIFTLINT_PIN]):
            refuse()
        if path != APPLICATION_RESOLVED:
            source = next((item for item in remote_sources if item["identity"] in path), None)
            if source is None:
                refuse()
            relative = UPSTREAM_RESOLVED[source["identity"]]
            digest = next(
                (
                    item["sha256"]
                    for item in source["actual_source_tree"]["files"]
                    if item["path"] == relative
                ),
                None,
            )
            if digest != row["sha256"]:
                refuse()
    if actual != set(expected) or set(locks) != {"pnpm-lock.yaml", "uv.lock", *expected}:
        refuse()


def validate_capacitor_source(value: Any) -> None:
    row = record(
        value,
        {
            "identity",
            "location",
            "version",
            "checkout_revision",
            "release_tag_revision",
            "manifest_sha256",
            "source_archive",
            "actual_source_tree",
        },
    )
    if (
        row["identity"] != "capacitor-swift-pm"
        or row["location"] != "https://github.com/ionic-team/capacitor-swift-pm.git"
        or row["version"] != CAPACITOR_RELEASE["version"]
        or row["checkout_revision"] != CAPACITOR_RELEASE["revision"]
        or row["release_tag_revision"] != CAPACITOR_RELEASE["revision"]
        or evidence_digest(row["manifest_sha256"]) != CAPACITOR_RELEASE["manifest_sha256"]
    ):
        refuse()
    archive = record(row["source_archive"], {"url", "sha256", "bytes"})
    if (
        archive["url"]
        != "https://codeload.github.com/ionic-team/capacitor-swift-pm/tar.gz/refs/tags/8.5.2"
        or evidence_digest(archive["sha256"]) != CAPACITOR_RELEASE["source_archive_sha256"]
        or count(archive["bytes"], MAX_BINARY) != CAPACITOR_RELEASE["source_archive_bytes"]
    ):
        refuse()
    tree = row["actual_source_tree"]
    validate_tree(tree, allow_empty_files=True)
    if any(tree[key] != expected for key, expected in CAPACITOR_RELEASE["source_tree"].items()):
        refuse()
    source_files = {file["path"]: file["sha256"] for file in tree["files"]}
    if (
        source_files.get("Package.swift") != row["manifest_sha256"]
        or source_files.get("README.md") != CAPACITOR_RELEASE["readme_sha256"]
    ):
        refuse()


def validate_capacitor_binary(value: Any) -> None:
    row = record(
        value,
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
    if not isinstance(name, str) or name not in CAPACITOR_RELEASE["binaries"]:
        refuse()
    expected = CAPACITOR_RELEASE["binaries"][name]
    archive = record(row["archive"], {"sha256", "bytes", "embedded_license_notice_files"})
    if (
        row["published_archive_url"]
        != f"https://github.com/ionic-team/capacitor-swift-pm/releases/download/8.5.2/{name}.xcframework.zip"
        or evidence_digest(row["swift_manifest_checksum"]) != expected["sha256"]
        or evidence_digest(archive["sha256"]) != expected["sha256"]
        or count(archive["bytes"], MAX_BINARY) != expected["archive_bytes"]
        or row["license_source"]
        != (
            "Capacitor npm ios MIT LICENSE; Cordova files additionally "
            "retain Apache-2.0 source headers; package metadata alone "
            "does not license other binary contents"
        )
    ):
        refuse()
    validate_notices(archive["embedded_license_notice_files"])
    if archive["embedded_license_notice_files"] != []:
        refuse()  # Exact reviewed archives contain no separate licence/notice entries.
    tree = row["actual_resolved_tree"]
    validate_tree(tree)
    if any(tree[key] != expected[key] for key in ("tree_sha256", "bytes", "file_count")):
        refuse()


def validate_ios(
    native: dict[str, Any], npm: dict[str, dict[str, Any]], locks: dict[str, Any]
) -> None:
    spm = record(
        native["spm"],
        {
            "package_resolved_sha256",
            "pins",
            "resolved_inventory",
            "remote_source_packages",
            "capacitor_source",
            "selected_manifest_sha256",
            "checkout_revision",
            "release_tag_revision",
            "upstream_binary_host_description",
            "upstream_capacitor_source_license",
            "binary_inputs",
        },
    )
    selected = selected_pins(spm["pins"])
    pin = selected["capacitor-swift-pm"]
    revision = pin["state"]["revision"]
    if revision != spm["checkout_revision"] or revision != spm["release_tag_revision"]:
        refuse()
    validate_source_packages(spm["remote_source_packages"], selected)
    validate_resolved_inventory(
        spm["resolved_inventory"], spm["pins"], locks, spm["remote_source_packages"]
    )
    validate_capacitor_source(spm["capacitor_source"])
    if evidence_digest(spm["selected_manifest_sha256"]) != CAPACITOR_RELEASE["manifest_sha256"]:
        refuse()
    if spm["capacitor_source"]["checkout_revision"] != revision:
        refuse()
    if evidence_digest(spm["package_resolved_sha256"]) != locks.get(APPLICATION_RESOLVED):
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
        or evidence_digest(license_source["sha256"]) != CAPACITOR_RELEASE["license_sha256"]
    ):
        refuse()
    if evidence_digest(description["sha256"]) != CAPACITOR_RELEASE["readme_sha256"]:
        refuse()
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
        validate_capacitor_binary(row)
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
    if evidence_digest(header["sha256"]) != CAPACITOR_RELEASE["cordova_header_sha256"]:
        refuse()
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
        lock_names.add(APPLICATION_RESOLVED)
        for identity, relative in UPSTREAM_RESOLVED.items():
            lock_names.add(
                f"apps/capture-pwa/ios/App/build/SourcePackages/checkouts/{identity}/{relative}"
            )
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
    mark("feature-comparison")
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
    mark("start")
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
        tarfile.TarError,
    ) as error:
        print("native-audit: evidence missing, invalid or unreviewed", file=sys.stderr)
        print(
            "native-audit: diagnostic " + json.dumps(diagnostic(error), sort_keys=True),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
