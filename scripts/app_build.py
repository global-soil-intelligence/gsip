"""WP-APP-2A: native build versions, Android backup rules and build receipts.

The projects are generated; this helper applies policy, then checks the built artifacts.
It does not sign apps or claim iOS WebKit storage is excluded from backups.

Usage: python scripts/app_build.py <command> <target> <run_number> <package.json>
Commands: apply-android (target: android/app), apply-ios/check-ios (target: Info.plist),
check-apk (append the aapt2 path), receipt (append reference artifact, output JSON, platform).
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import plistlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET  # noqa: S405 - generated build files and aapt2 output only
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ANDROID_NS = "http://schemas.android.com/apk/res/android"
TOOLS_NS = "http://schemas.android.com/tools"
DOMAINS = (
    "root",
    "file",
    "database",
    "sharedpref",
    "external",
    "device_root",
    "device_file",
    "device_database",
    "device_sharedpref",
)
MAX_RUN_NUMBER = 99_990_000
MODERN_RULES = "gsip_data_extraction_rules"
LEGACY_RULES = "gsip_backup_rules"


@dataclass(frozen=True)
class Versions:
    marketing: str
    android: int
    ios: str


def versions(run_number: str, package: Path) -> Versions:
    # Canonical ASCII input prevents aliases such as 01 from colliding with run 1.
    if not re.fullmatch(r"[1-9][0-9]{0,7}", run_number):
        raise ValueError("run_number must be a canonical positive ASCII integer")
    number = int(run_number)
    if number > MAX_RUN_NUMBER:
        raise ValueError(f"run_number exceeds {MAX_RUN_NUMBER}")
    marketing = json.loads(package.read_text(encoding="utf-8")).get("version")
    if not isinstance(marketing, str) or not re.fullmatch(
        r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", marketing
    ):
        raise ValueError("package version must have three canonical integer components")
    index = number - 1
    return Versions(marketing, number, f"{1 + index // 10_000}.{index // 100 % 100}.{index % 100}")


def xml(text: str) -> ET.Element:
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))  # noqa: S314
    return ET.fromstring(text, parser=parser)  # noqa: S314


def serialize(root: ET.Element) -> str:
    ET.register_namespace("android", ANDROID_NS)
    ET.register_namespace("tools", TOOLS_NS)
    ET.indent(root, space="    ")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def backup_rules(modern: bool) -> str:
    root = ET.Element("data-extraction-rules" if modern else "full-backup-content")
    cloud = ET.SubElement(root, "cloud-backup") if modern else root
    for domain in DOMAINS:
        ET.SubElement(cloud, "exclude", {"domain": domain, "path": "."})
    if modern:
        transfer = ET.SubElement(root, "device-transfer")
        for domain in DOMAINS:
            ET.SubElement(transfer, "include", {"domain": domain, "path": "."})
    return serialize(root)


def check_rules(root: ET.Element, modern: bool) -> None:
    expected = xml(backup_rules(modern))

    # Compare the full tree: no permissive include, duplicate domain, qualifier or new mode.
    def structure(element: ET.Element) -> tuple[Any, ...]:
        return (
            element.tag,
            sorted(element.attrib.items()),
            [structure(child) for child in element],
        )

    if structure(root) != structure(expected):
        raise ValueError("backup rules differ from the approved nine-domain transport policy")


def application(root: ET.Element) -> ET.Element:
    apps = root.findall("application")
    if len(apps) != 1:
        raise ValueError("manifest must contain exactly one application")
    app = apps[0]
    if f"{{{ANDROID_NS}}}backupAgent" in app.attrib:
        raise ValueError("custom backupAgent requires separate review")
    return app


def apply_android(app_dir: Path, value: Versions) -> None:
    manifest = app_dir / "src" / "main" / "AndroidManifest.xml"
    root = xml(manifest.read_text(encoding="utf-8"))
    app = application(root)
    app.set(f"{{{ANDROID_NS}}}allowBackup", "true")
    app.set(f"{{{ANDROID_NS}}}dataExtractionRules", f"@xml/{MODERN_RULES}")
    app.set(f"{{{ANDROID_NS}}}fullBackupContent", f"@xml/{LEGACY_RULES}")
    gradle = app_dir / "build.gradle"
    text = gradle.read_text(encoding="utf-8")
    for name, replacement in (
        ("versionCode", str(value.android)),
        ("versionName", f'"{value.marketing}"'),
    ):
        text, count = re.subn(rf"(?m)^(\s*){name}\s+[^\n]+$", rf"\g<1>{name} {replacement}", text)
        if count != 1:
            raise ValueError(f"generated Gradle file must contain exactly one {name}")
    # Validate every input before mutating the generated project.
    resources = app_dir / "src" / "main" / "res" / "xml"
    resources.mkdir(parents=True, exist_ok=True)
    for name, modern in ((MODERN_RULES, True), (LEGACY_RULES, False)):
        (resources / f"{name}.xml").write_text(backup_rules(modern), encoding="utf-8")
    manifest.write_text(serialize(root), encoding="utf-8")
    gradle.write_text(text, encoding="utf-8")


def apply_ios(path: Path, value: Versions) -> None:
    data = plistlib.loads(path.read_bytes())
    data["CFBundleShortVersionString"] = value.marketing
    data["CFBundleVersion"] = value.ios
    path.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_XML))


def check_activation(raw: bytes) -> None:
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("packaged activation receipt is invalid") from error
    if data != {"capture_live": False, "library_intake_live": False} or any(
        type(value) is not bool for value in data.values()
    ):
        raise ValueError("packaged activation must keep capture and library intake closed")


def check_ios(path: Path, value: Versions) -> None:
    check_activation((path.parent / "public" / "gsip-activation.json").read_bytes())
    data = plistlib.loads(path.read_bytes())
    if (
        data.get("CFBundleShortVersionString") != value.marketing
        or data.get("CFBundleVersion") != value.ios
    ):
        raise ValueError("built iOS marketing/build versions differ from declared inputs")


def command(args: list[str]) -> str:
    # Commands are fixed build tools, never a shell string or contributor-controlled input.
    result = subprocess.run(args, capture_output=True, text=True, check=True)  # noqa: S603
    return (result.stdout + result.stderr).strip()


def aapt_xml(dump: str) -> ET.Element:
    """Decode the structure/attributes of aapt2's compiled XML tree, failing on unknown values."""
    stack: list[tuple[int, ET.Element]] = []
    root: ET.Element | None = None
    for line in dump.splitlines():
        element = re.fullmatch(r"(\s*)E: ([\w.-]+)(?: \(line=\d+\))?", line)
        if element:
            depth = len(element[1])
            while stack and stack[-1][0] >= depth:
                stack.pop()
            node = ET.Element(element[2])
            if stack:
                stack[-1][1].append(node)
            elif root is None:
                root = node
            else:
                raise ValueError("multiple compiled XML roots")
            stack.append((depth, node))
            continue
        attribute = re.fullmatch(
            r"\s*A: ((?:android:|http://schemas.android.com/apk/res/android:)?[\w]+)"
            r"(?:\(0x[0-9a-f]+\))?=(.+)",
            line,
        )
        if not attribute:
            continue
        if not stack:
            raise ValueError("compiled XML attribute has no element")
        name, raw = attribute[1], attribute[2]
        name = name.replace(f"{ANDROID_NS}:", f"{{{ANDROID_NS}}}")
        name = name.replace("android:", f"{{{ANDROID_NS}}}")
        quoted = re.search(r'\(Raw: "([^"\n]*)"\)$', raw) or re.fullmatch(r'"([^"\n]*)"', raw)
        typed = re.fullmatch(r"\(type 0x(10|11|12)\)(0x[0-9a-f]+)", raw)
        if quoted:
            value = quoted[1]
        elif typed:
            number = int(typed[2], 16)
            value = ("true" if number else "false") if typed[1] == "12" else str(number)
        elif re.fullmatch(r"@0x[0-9a-f]+", raw) or raw in {"true", "false"}:
            value = raw
        elif re.fullmatch(r"[0-9]+|0x[0-9a-f]+", raw):
            value = str(int(raw, 16 if raw.startswith("0x") else 10))
        else:
            raise ValueError(f"unsupported compiled XML attribute encoding: {name}")
        stack[-1][1].set(name, value)
    if root is None:
        raise ValueError("empty compiled XML tree")
    return root


def resource_file(dump: str, name: str) -> tuple[str, str]:
    blocks = re.split(r"(?m)^\s*resource ", dump)[1:]
    matches = [
        block for block in blocks if re.match(rf"0x[0-9a-f]+ (?:[\w.]+:)?xml/{name}(?:\s|$)", block)
    ]
    if len(matches) != 1:
        raise ValueError(f"compiled XML resource missing or ambiguous: {name}")
    block = matches[0]
    identifier = block.split()[0]
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    # Count every value record, including aliases and unknown encodings. A single file
    # beside a qualified alias does not establish the effective resource policy.
    payload = (
        re.fullmatch(r"\(\) \(file\) (res/[^\s]+\.xml) type=XML", lines[1])
        if len(lines) == 2
        else None
    )
    if payload is None:
        raise ValueError(f"compiled XML must have exactly one default file configuration: {name}")
    return f"@{identifier}", payload[1]


def check_apk(apk: Path, value: Versions, aapt2: str) -> None:
    badging = command([aapt2, "dump", "badging", str(apk)])
    package = re.search(
        r"^package: name='com\.globalsoilintelligence\.app' "
        r"versionCode='([0-9]+)' versionName='([^']+)'",
        badging,
        re.M,
    )
    if not package or int(package[1]) != value.android or package[2] != value.marketing:
        raise ValueError(
            "built APK identity or marketing/build versions differ from declared inputs"
        )
    target = re.search(r"^targetSdkVersion:'([0-9]+)'", badging, re.M)
    if not target or int(target[1]) < 31:
        raise ValueError("transport-separated backup rules require target SDK 31 or newer")
    app = application(
        aapt_xml(command([aapt2, "dump", "xmltree", "--file", "AndroidManifest.xml", str(apk)]))
    )
    if app.get(f"{{{ANDROID_NS}}}allowBackup") != "true":
        raise ValueError("compiled application must enable the explicitly restricted backup rules")
    resources = command([aapt2, "dump", "resources", str(apk)])
    for name, modern, attribute in (
        (MODERN_RULES, True, "dataExtractionRules"),
        (LEGACY_RULES, False, "fullBackupContent"),
    ):
        identifier, file = resource_file(resources, name)
        if app.get(f"{{{ANDROID_NS}}}{attribute}") != identifier:
            raise ValueError(f"compiled application does not reference its approved {attribute}")
        check_rules(aapt_xml(command([aapt2, "dump", "xmltree", "--file", file, str(apk)])), modern)

    with zipfile.ZipFile(apk) as archive:
        name = "assets/public/gsip-activation.json"
        if archive.namelist().count(name) != 1:
            raise ValueError("packaged activation receipt is missing or ambiguous")
        check_activation(archive.read(name))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def zip_contents(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        names = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
        if len(names) != len(set(names)):
            raise ValueError("artifact ZIP has duplicate entries")
        return {name: hashlib.sha256(archive.read(name)).hexdigest() for name in sorted(names)}


def comparison(first: Path, second: Path) -> dict[str, Any]:
    left, right = zip_contents(first), zip_contents(second)
    return {
        "byte_equal": digest(first) == digest(second),
        "entry_content_equal": left == right,
        "normalization": (
            "ZIP entry bytes only: excludes directory entries, archive metadata and container "
            "bytes including APK signing blocks; full hashes/byte_equal include everything"
        ),
        "changed_entries": sorted(
            name for name in left.keys() & right.keys() if left[name] != right[name]
        ),
        "first_only": sorted(left.keys() - right.keys()),
        "second_only": sorted(right.keys() - left.keys()),
    }


def source_clean(root: Path, artifacts: tuple[Path, ...]) -> bool:
    changed = command(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"])
    untracked = set(
        command(["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    for artifact in artifacts:
        if artifact.resolve().is_relative_to(root):
            untracked.discard(str(artifact.resolve().relative_to(root)))
    return not changed and not untracked


def receipt(
    artifact: Path,
    reference: Path,
    value: Versions,
    target_platform: str,
    aapt2: str | None = None,
    receipt_path: Path | None = None,
) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    toolchain = {
        "node": command(["node", "--version"]),
        "pnpm": command(["pnpm", "--version"]),
        "python": sys.version,
        "runner": platform.platform(),
        "runner_image": {
            name: os.environ.get(name, "unavailable")
            for name in ("ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH")
        },
    }
    if target_platform == "android":
        toolchain["gradle"] = command([str(root / "apps/capture-pwa/android/gradlew"), "--version"])
        toolchain["java"] = command(["java", "-version"])
        if aapt2 is None:
            raise ValueError("Android receipt requires the actual aapt2 path")
        toolchain["aapt2"] = command([aapt2, "version"])
        lockfiles_android = [
            root / "apps/capture-pwa/android" / name
            for name in (
                "gradle/wrapper/gradle-wrapper.properties",
                "build.gradle",
                "variables.gradle",
            )
        ]
    elif target_platform == "ios":
        toolchain["xcode"] = command(["xcodebuild", "-version"])
        toolchain["sdk"] = command(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"])
    else:
        raise ValueError("receipt platform must be android or ios")
    lockfiles = [root / "pnpm-lock.yaml", root / "uv.lock"]
    if target_platform == "android":
        lockfiles += lockfiles_android
    if target_platform == "ios":
        lockfiles += sorted((root / "apps/capture-pwa/ios").rglob("Package.resolved"))
    return {
        "source_commit": command(["git", "-C", str(root), "rev-parse", "HEAD"]),
        "platform": target_platform,
        "marketing_version": value.marketing,
        "run_number": value.android,
        "android_version_code": value.android,
        "ios_build_version": value.ios,
        "lockfile_sha256": {str(path.relative_to(root)): digest(path) for path in lockfiles},
        "toolchain": toolchain,
        "source_tree_clean": source_clean(
            root, (artifact, reference) + ((receipt_path,) if receipt_path else ())
        ),
        "comparison_scope": (
            "same run/generated project; actual repeated native build; "
            + (
                "Android shared disposable debug key"
                if target_platform == "android"
                else "iOS unsigned simulator; signing disabled"
            )
        ),
        "artifact_sha256": digest(artifact),
        "reference_sha256": digest(reference),
        "comparison": comparison(reference, artifact),
    }


def main(argv: list[str]) -> int:
    try:
        if len(argv) < 5:
            raise ValueError(__doc__ or "invalid arguments")
        action, target, run_number, package = argv[1:5]
        value = versions(run_number, Path(package))
        path = Path(target)
        if action == "apply-android" and len(argv) == 5:
            apply_android(path, value)
        elif action == "apply-ios" and len(argv) == 5:
            apply_ios(path, value)
        elif action == "check-ios" and len(argv) == 5:
            check_ios(path, value)
        elif action == "check-apk" and len(argv) == 6:
            check_apk(path, value, argv[5])
        elif action == "receipt" and len(argv) in (8, 9):
            Path(argv[6]).write_text(
                json.dumps(
                    receipt(
                        path,
                        Path(argv[5]),
                        value,
                        argv[7],
                        argv[8] if len(argv) == 9 else None,
                        Path(argv[6]),
                    ),
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        else:
            raise ValueError("unknown command or invalid argument count")
        print(
            f"{action}: completed with version inputs {value.marketing}/{value.android}/{value.ios}"
        )
        return 0
    except (
        ValueError,
        OSError,
        ET.ParseError,
        plistlib.InvalidFileException,
        subprocess.CalledProcessError,
        zipfile.BadZipFile,
    ) as error:
        print(f"app-build: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
