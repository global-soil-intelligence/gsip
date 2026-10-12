"""WP-APP-2A: validated build versions and private cloud-backup exclusions."""

from __future__ import annotations

import json
import plistlib
import subprocess
import sys
import xml.etree.ElementTree as ET  # noqa: S405 - synthetic build fixtures only
import zipfile
from pathlib import Path
from typing import Any

import pytest

from scripts import app_build as build

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "app"


def test_apply_android_cli_hardens_generated_project(tmp_path: Path) -> None:
    app = tmp_path / "app"
    main = app / "src" / "main"
    main.mkdir(parents=True)
    (main / "AndroidManifest.xml").write_bytes((FIXTURES / "AndroidManifest.xml").read_bytes())
    (app / "build.gradle").write_text('versionCode 1\nversionName "1.0"\n')
    result = subprocess.run(  # noqa: S603 - the repository's helper, synthetic project only
        [
            sys.executable,
            str(ROOT / "scripts" / "app_build.py"),
            "apply-android",
            str(app),
            "101",
            str(ROOT / "apps" / "capture-pwa" / "package.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "versionCode 101" in (app / "build.gradle").read_text()
    assert 'versionName "0.1.0"' in (app / "build.gradle").read_text()
    manifest = (main / "AndroidManifest.xml").read_text()
    assert 'android:dataExtractionRules="@xml/gsip_data_extraction_rules"' in manifest
    assert 'android:fullBackupContent="@xml/gsip_backup_rules"' in manifest


def test_workflow_verifies_built_versions_and_repeats_same_inputs() -> None:
    workflow = (ROOT / ".github" / "workflows" / "app-build.yml").read_text()
    assert "scripts/app_build.py check-apk" in workflow
    assert "scripts/app_build.py check-ios" in workflow
    assert "assembleDebug --rerun-tasks" in workflow
    assert "clean build" in workflow


PACKAGE = ROOT / "apps" / "capture-pwa" / "package.json"
EXPECTED_DOMAINS = {
    "root",
    "file",
    "database",
    "sharedpref",
    "external",
    "device_root",
    "device_file",
    "device_database",
    "device_sharedpref",
}


@pytest.mark.parametrize(
    "number,ios",
    [
        ("1", "1.0.0"),
        ("100", "1.0.99"),
        ("101", "1.1.0"),
        ("10000", "1.99.99"),
        ("10001", "2.0.0"),
        ("99990000", "9999.99.99"),
    ],
)
def test_versions_roll_over_without_truncation(number: str, ios: str) -> None:
    value = build.versions(number, PACKAGE)
    assert (value.marketing, value.android, value.ios) == ("0.1.0", int(number), ios)


@pytest.mark.parametrize(
    "number", ["", "0", "-1", "+1", "01", "1.0", "1e2", " 1", "1\n", "１", "99990001", "2100000001"]
)
def test_invalid_or_colliding_run_inputs_are_rejected(number: str) -> None:
    with pytest.raises(ValueError):
        build.versions(number, PACKAGE)


def test_build_mapping_is_injective_and_numerically_monotonic() -> None:
    values = [build.versions(str(number), PACKAGE) for number in range(1, 20_002)]
    assert len({value.ios for value in values}) == len(values)
    tuples = [tuple(map(int, value.ios.split("."))) for value in values]
    assert tuples == sorted(tuples)
    assert len({value.android for value in values}) == len(values)


@pytest.mark.parametrize("version", ["1.0", "01.2.3", "1.2.3-beta", None, 1])
def test_marketing_version_has_one_canonical_source(tmp_path: Path, version: Any) -> None:
    package = tmp_path / "package.json"
    package.write_text(json.dumps({"version": version}))
    with pytest.raises(ValueError):
        build.versions("101", package)


def project(tmp_path: Path) -> Path:
    app = tmp_path / "app"
    main = app / "src" / "main"
    main.mkdir(parents=True)
    (main / "AndroidManifest.xml").write_bytes((FIXTURES / "AndroidManifest.xml").read_bytes())
    (app / "build.gradle").write_text('versionCode 1\nversionName "1.0"\n')
    return app


def test_android_rules_cover_every_domain_by_transport_and_are_idempotent(tmp_path: Path) -> None:
    app = project(tmp_path)
    value = build.versions("101", PACKAGE)
    build.apply_android(app, value)
    files = sorted(path for path in app.rglob("*") if path.is_file())
    once = {path: path.read_bytes() for path in files}
    build.apply_android(app, value)
    assert {path: path.read_bytes() for path in files} == once
    manifest = build.xml((app / "src/main/AndroidManifest.xml").read_text())
    application = manifest.find("application")
    assert application is not None
    assert application.get(f"{{{build.ANDROID_NS}}}allowBackup") == "true"
    assert application.get(f"{{{build.ANDROID_NS}}}backupAgent") is None
    modern = build.xml((app / "src/main/res/xml/gsip_data_extraction_rules.xml").read_text())
    legacy = build.xml((app / "src/main/res/xml/gsip_backup_rules.xml").read_text())
    assert modern.tag == "data-extraction-rules"
    cloud, transfer = list(modern)
    assert cloud.tag == "cloud-backup" and transfer.tag == "device-transfer"
    for parent, tag in [(cloud, "exclude"), (transfer, "include"), (legacy, "exclude")]:
        assert len(parent) == 9
        assert {child.get("domain") for child in parent} == EXPECTED_DOMAINS
        assert all(child.tag == tag and child.get("path") == "." for child in parent)
    assert legacy.tag == "full-backup-content"


@pytest.mark.parametrize(
    "gradle", ['versionName "1.0"\n', 'versionCode 1\nversionCode 2\nversionName "1.0"\n']
)
def test_ambiguous_gradle_versions_fail_before_any_write(tmp_path: Path, gradle: str) -> None:
    app = project(tmp_path)
    (app / "build.gradle").write_text(gradle)
    before = {path: path.read_bytes() for path in app.rglob("*") if path.is_file()}
    with pytest.raises(ValueError):
        build.apply_android(app, build.versions("101", PACKAGE))
    assert {path: path.read_bytes() for path in app.rglob("*") if path.is_file()} == before


def test_custom_backup_agent_is_never_silently_removed(tmp_path: Path) -> None:
    app = project(tmp_path)
    manifest = app / "src/main/AndroidManifest.xml"
    manifest.write_text(
        manifest.read_text().replace("<application", '<application android:backupAgent="Custom"')
    )
    with pytest.raises(ValueError, match="backupAgent"):
        build.apply_android(app, build.versions("101", PACKAGE))


def test_ios_versions_survive_binary_plist_and_rerun(tmp_path: Path) -> None:
    path = tmp_path / "Info.plist"
    path.write_bytes((FIXTURES / "Info.plist").read_bytes())
    value = build.versions("101", PACKAGE)
    build.apply_ios(path, value)
    first = path.read_bytes()
    build.apply_ios(path, value)
    assert path.read_bytes() == first
    data = plistlib.loads(first)
    assert data["CFBundleShortVersionString"] == "0.1.0"
    assert data["CFBundleVersion"] == "1.1.0"
    assert data["CFBundleIdentifier"] == "$(PRODUCT_BUNDLE_IDENTIFIER)"
    assert not any("backup" in key.lower() for key in data)
    path.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_BINARY))
    build.check_ios(path, value)
    data["CFBundleVersion"] = "1"
    path.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_BINARY))
    with pytest.raises(ValueError):
        build.check_ios(path, value)


def compiled_xml(root: ET.Element, indent: int = 0) -> str:
    output = [f"{' ' * indent}E: {root.tag} (line=1)"]
    for name, value in root.attrib.items():
        name = name.replace(f"{{{build.ANDROID_NS}}}", "android:")
        raw = value if value.startswith("@0x") else json.dumps(value)
        output.append(f"{' ' * (indent + 2)}A: {name}={raw}")
    output += [compiled_xml(child, indent + 2) for child in root]
    return "\n".join(output)


def apk_dumps() -> dict[str, str]:
    manifest = build.xml(
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
        '<application android:allowBackup="true" '
        'android:dataExtractionRules="@0x7f100001" '
        'android:fullBackupContent="@0x7f100002"/></manifest>'
    )
    return {
        "badging": (
            "package: name='com.globalsoilintelligence.app' "
            "versionCode='101' versionName='0.1.0'\ntargetSdkVersion:'36'"
        ),
        "resources": (
            "resource 0x7f100001 xml/gsip_data_extraction_rules\n"
            "  () (file) res/xml/gsip_data_extraction_rules.xml type=XML\n"
            "resource 0x7f100002 xml/gsip_backup_rules\n"
            "  () (file) res/xml/gsip_backup_rules.xml type=XML"
        ),
        "AndroidManifest.xml": compiled_xml(manifest),
        "res/xml/gsip_data_extraction_rules.xml": compiled_xml(build.xml(build.backup_rules(True))),
        "res/xml/gsip_backup_rules.xml": compiled_xml(build.xml(build.backup_rules(False))),
    }


def test_built_apk_checks_actual_application_resource_refs_and_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dumps = apk_dumps()

    def run(args: list[str]) -> str:
        return dumps[args[4] if args[2] == "xmltree" else args[2]]

    monkeypatch.setattr(build, "command", run)
    build.check_apk(Path("synthetic.apk"), build.versions("101", PACKAGE), "aapt2")


@pytest.mark.parametrize(
    "defect",
    [
        "version",
        "sdk",
        "allow",
        "wrong_element",
        "dangling",
        "backupAgent",
        "cloud_include",
        "legacy_include",
        "qualifier",
        "alias",
        "nondefault",
        "unknown_encoding",
        "missing_cloud",
    ],
)
def test_compiled_apk_rejects_privacy_or_version_drift(
    monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    dumps = apk_dumps()
    if defect == "version":
        dumps["badging"] = dumps["badging"].replace("versionCode='101'", "versionCode='1'")
    elif defect == "sdk":
        dumps["badging"] = dumps["badging"].replace("'36'", "'30'")
    elif defect in {"cloud_include", "legacy_include"}:
        name = "gsip_data_extraction_rules" if defect == "cloud_include" else "gsip_backup_rules"
        key = f"res/xml/{name}.xml"
        dumps[key] = dumps[key].replace("E: exclude", "E: include", 1)
    elif defect == "missing_cloud":
        dumps["res/xml/gsip_data_extraction_rules.xml"] = "E: data-extraction-rules (line=1)"
    elif defect == "qualifier":
        dumps["resources"] += "\n  (v31) (file) res/xml-v31/gsip_backup_rules.xml type=XML"
    elif defect == "nondefault":
        dumps["resources"] = dumps["resources"].replace("() (file)", "(v31) (file)", 1)
    elif defect == "unknown_encoding":
        dumps["resources"] = dumps["resources"].replace("type=XML", "type=STRING", 1)
    elif defect == "alias":
        dumps["resources"] = dumps["resources"].replace(
            "resource 0x7f100002", "  (v31) @0x7f100099\nresource 0x7f100002"
        )
    else:
        key = "AndroidManifest.xml"
        if defect == "allow":
            dumps[key] = dumps[key].replace('allowBackup="true"', 'allowBackup="false"')
        elif defect == "dangling":
            dumps[key] = dumps[key].replace("@0x7f100001", "@0x7f100099")
        elif defect == "backupAgent":
            dumps[key] += '\n    A: android:backupAgent="Custom"'
        else:
            dumps[key] = dumps[key].replace("E: application", "E: activity")

    def run(args: list[str]) -> str:
        return dumps[args[4] if args[2] == "xmltree" else args[2]]

    monkeypatch.setattr(build, "command", run)
    with pytest.raises(ValueError):
        build.check_apk(Path("synthetic.apk"), build.versions("101", PACKAGE), "aapt2")


def archive(path: Path, content: bytes, second: int = 0) -> None:
    with zipfile.ZipFile(path, "w") as output:
        info = zipfile.ZipInfo("App.app/synthetic.bin", (2026, 1, 1, 0, 0, second))
        output.writestr(info, content)


def test_comparison_normalizes_only_zip_metadata_and_reports_payload_changes(
    tmp_path: Path,
) -> None:
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    archive(first, b"synthetic", 0)
    archive(second, b"synthetic", 2)
    result = build.comparison(first, second)
    assert result["byte_equal"] is False
    assert result["entry_content_equal"] is True
    archive(second, b"changed", 2)
    result = build.comparison(first, second)
    assert result["entry_content_equal"] is False
    assert result["changed_entries"] == ["App.app/synthetic.bin"]


def test_actual_aapt2_namespace_and_scalar_encodings_are_decoded() -> None:
    root = build.aapt_xml("""N: android=http://schemas.android.com/apk/res/android (line=2)
  E: manifest (line=2)
    A: platformBuildVersionCode=36
      E: application (line=3)
        A: http://schemas.android.com/apk/res/android:allowBackup(0x01010280)=true
        A: http://schemas.android.com/apk/res/android:fullBackupContent(0x010104eb)=@0x7f120002
          E: activity (line=4)
            A: http://schemas.android.com/apk/res/android:configChanges(0x0101001f)=0x00001ff4
""")
    app = build.application(root)
    assert app.get(f"{{{build.ANDROID_NS}}}allowBackup") == "true"
    assert app.get(f"{{{build.ANDROID_NS}}}fullBackupContent") == "@0x7f120002"
    assert root.get("platformBuildVersionCode") == "36"
    assert list(app)[0].get(f"{{{build.ANDROID_NS}}}configChanges") == str(0x1FF4)


def test_receipt_binds_versions_locks_tools_and_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    (source / "scripts").mkdir(parents=True)
    helper = source / "scripts/app_build.py"
    helper.write_text("synthetic helper")
    for name in [
        "pnpm-lock.yaml",
        "uv.lock",
        "apps/capture-pwa/android/build.gradle",
        "apps/capture-pwa/android/variables.gradle",
        "apps/capture-pwa/android/gradle/wrapper/gradle-wrapper.properties",
    ]:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic input")
    first, second = tmp_path / "first.apk", tmp_path / "second.apk"
    archive(first, b"synthetic")
    archive(second, b"synthetic")
    monkeypatch.setattr(build, "__file__", str(helper))

    def run(args: list[str]) -> str:
        if "rev-parse" in args:
            return "0" * 40
        if "status" in args:
            return " M scripts/app_build.py"
        return "synthetic toolchain"

    monkeypatch.setattr(build, "command", run)
    value = build.versions("101", PACKAGE)
    result = build.receipt(second, first, value, "android", "aapt2")
    assert result["marketing_version"] == "0.1.0"
    assert result["run_number"] == result["android_version_code"] == 101
    assert result["ios_build_version"] == "1.1.0"
    assert result["source_tree_clean"] is False
    assert len(result["lockfile_sha256"]) == 5
    assert result["toolchain"]["aapt2"] == "synthetic toolchain"
    assert result["artifact_sha256"] == result["reference_sha256"]
    assert result["comparison"]["byte_equal"] is True
    assert result["comparison"]["entry_content_equal"] is True
    assert "Android shared disposable debug key" in result["comparison_scope"]
    ios = build.receipt(second, first, value, "ios")
    assert "iOS unsigned simulator; signing disabled" in ios["comparison_scope"]
    assert "debug key" not in ios["comparison_scope"]


def test_entry_equality_does_not_hide_container_difference_claims(tmp_path: Path) -> None:
    first, second = tmp_path / "first.apk", tmp_path / "second.apk"
    archive(first, b"synthetic")
    second.write_bytes(first.read_bytes() + b"synthetic-container-signing-block-like-bytes")
    result = build.comparison(first, second)
    assert result["byte_equal"] is False
    assert result["entry_content_equal"] is True
    assert "APK signing blocks" in result["normalization"]
    assert "full hashes/byte_equal include everything" in result["normalization"]


def test_source_clean_excludes_only_exact_generated_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "receipt.json"

    def run(args: list[str]) -> str:
        return "receipt.json\nnew_source.py" if "ls-files" in args else ""

    monkeypatch.setattr(build, "command", run)
    assert build.source_clean(tmp_path, (output,)) is False
    assert build.source_clean(tmp_path, (output, tmp_path / "new_source.py")) is True
