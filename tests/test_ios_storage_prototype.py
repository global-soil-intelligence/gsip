"""Synthetic policy regressions; mocked files never certify native behavior."""

from __future__ import annotations

import hashlib
import json
import plistlib
from pathlib import Path
from typing import Any

import pytest

from scripts import ios_storage_prototype as prototype

ROOT = Path(__file__).resolve().parents[1]


# Readable inert CLI metadata fixtures; these namespace/homepage strings are never contacted.
INERT_METADATA_FIXTURES = {
    "App/App/config.xml": (
        b"<?xml version='1.0' encoding='utf-8'?>\n"
        b'<widget version="1.0.0" xmlns="http://www.w3.org/ns/widgets" '
        b'xmlns:cdv="http://cordova.apache.org/ns/1.0">\n  <access origin="*" />\n  \n  \n'
        b"</widget>"
    ),
    "capacitor-cordova-ios-plugins/CordovaPluginsResources.podspec": (
        b"""Pod::Spec.new do |s|
  s.name = 'CordovaPluginsResources'
  s.version = '0.0.105'
  s.summary = 'Resources for Cordova plugins'
  s.license = 'MIT'
  s.homepage = 'https://capacitorjs.com/'
  s.authors = { 'Ionic Team' => 'hi@ionicframework.com' }
  s.source = { :git => 'https://github.com/ionic-team/capacitor.git', :tag => s.version.to_s }
  s.resources = ['resources/*']
end
"""
    ),
}


@pytest.fixture(autouse=True)
def owned_pinned_cli_template(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Unit fixtures may copy the package store's regular hardlinked bytes. Actual
    # harness admission still uses the original strict reader and the copy install.
    source = ROOT
    installed = (source / "apps/capture-pwa/node_modules/@capacitor/cli").resolve(strict=True)
    owned = tmp_path_factory.mktemp("pinned-template-root")
    scope = prototype.load_scope(source)
    paths = (
        {"docs/ios-native-scope.json", ".github/workflows/ios-storage-prototype.yml"}
        | set(scope["source_bindings"])
        | {item["path"] for item in scope["native_files"]}
    )
    for relative in paths:
        path = owned / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((source / relative).read_bytes())
    destination = owned / "apps/capture-pwa/node_modules/@capacitor/cli"
    for relative in ("package.json", "assets/ios-spm-template.tar.gz"):
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((installed / relative).read_bytes())
    prototype.template_inputs(owned)  # Real pinned version/length/hash/no-link admission.
    monkeypatch.setitem(globals(), "ROOT", owned)


def test_scope_and_fixed_bindings() -> None:
    scope = prototype.load_scope(ROOT)
    assert len(scope["native_files"]) == 21
    assert len(scope["generated_copies"]) == 21
    assert len(scope["generated_edits"]) == 9
    prototype.validate_sources(ROOT)


def test_exact_native_files_and_no_arbitrary_import(tmp_path: Path) -> None:
    scope = prototype.load_scope(ROOT)
    copy_sources(ROOT, tmp_path)
    path = tmp_path / scope["native_files"][1]["path"]
    path.write_text(path.read_text() + "\nimport Network\n")
    with pytest.raises(prototype.PrototypeError):
        prototype.validate_native(tmp_path, scope)


def copy_sources(root: Path, dest: Path) -> None:
    for item in prototype.load_scope(root)["native_files"]:
        p = dest / item["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((root / item["path"]).read_bytes())


@pytest.mark.parametrize("name", ["Other.swift", "shim.h", "nested/Other.swift"])
def test_no_unlisted_native_source(tmp_path: Path, name: str) -> None:
    scope = prototype.load_scope(ROOT)
    copy_sources(ROOT, tmp_path)
    p = tmp_path / prototype.PREFIX / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("unapproved")
    with pytest.raises(prototype.PrototypeError):
        prototype.validate_native(tmp_path, scope)


@pytest.mark.parametrize("part", ["../elsewhere", "/absolute", "x/../escape", "x//escape"])
def test_path_policy_rejects_aliases(part: str) -> None:
    with pytest.raises(prototype.PrototypeError):
        prototype.safe_relative(part)


def test_links_and_multiple_links_are_refused(tmp_path: Path) -> None:
    original = tmp_path / "file"
    original.write_bytes(b"synthetic")
    alias = tmp_path / "alias"
    alias.symlink_to(original)
    with pytest.raises(prototype.PrototypeError):
        prototype.regular_bytes(alias)
    alias.unlink()
    import os

    os.link(original, alias)
    with pytest.raises(prototype.PrototypeError):
        prototype.regular_bytes(original)


def test_exact_replacement_requires_single_anchor() -> None:
    for content in ["missing", "x x"]:
        with pytest.raises(prototype.PrototypeError):
            prototype.replace_once(content, "x", "y")
    assert prototype.replace_once("before @target after", "@target", "new") == "before new after"


def test_template_archive_is_bound() -> None:
    archive, members = prototype.template_inputs(ROOT)
    assert len(archive) == 155545
    assert hashlib.sha256(archive).hexdigest() == prototype.TEMPLATE_SHA
    assert "App/App/AppDelegate.swift" in members


def fresh_fixture(root: Path, dest: Path) -> None:
    _, members = prototype.template_inputs(root)
    expected = prototype.expected_generated(root, members) | INERT_METADATA_FIXTURES
    # Reproduce only the already selected local plugin metadata in the synthetic fixture.
    for _, slug, version in prototype.PLUGINS:
        relative = (
            f"../../../../../node_modules/.pnpm/"
            f"@capacitor+{slug}@{version}_@capacitor+core@8.5.2/node_modules/"
            f"@capacitor/{slug}"
        )
        package = (dest / "App/CapApp-SPM" / relative).resolve()
        package.mkdir(parents=True, exist_ok=True)
        (package / "package.json").write_text(json.dumps({"version": version}))
    for relative, data in expected.items():
        p = dest / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    public = dest / "App/App/public"
    public.mkdir(parents=True)
    (public / "private-original.js").write_text("ordinary-asset-never-copied")


def test_finite_prepare_omits_ordinary_public_and_preserves_other_bytes(tmp_path: Path) -> None:
    fresh = tmp_path / "workspace/apps/capture-pwa/ios"
    fresh_fixture(ROOT, fresh)
    output = tmp_path / "prototype"
    receipt = prototype.prepare(ROOT, fresh, output)
    assert set(receipt["edited"]) == set(prototype.load_scope(ROOT)["generated_edits"])
    assert len(receipt["copied"]) == 21
    assert {p.name for p in (output / "App/App/public").iterdir()} == {
        "index.html",
        "gsip-activation.json",
    }
    for relative, data in INERT_METADATA_FIXTURES.items():
        assert (output / relative).read_bytes() == data == (fresh / relative).read_bytes()
    assert (output / "App/App/AppDelegate.swift").read_bytes() == (
        fresh / "App/App/AppDelegate.swift"
    ).read_bytes()
    config = json.loads((output / "App/App/capacitor.config.json").read_bytes())
    assert config["ios"]["handleApplicationNotifications"] is False
    assert config["loggingBehavior"] == "none"
    assert config["appId"] != "com.globalsoilintelligence.app"
    assert "server" not in config


@pytest.mark.parametrize(
    "target",
    [
        "App/App.xcodeproj/project.pbxproj",
        "App/App/SceneDelegate.swift",
        "App/App/AppDelegate.swift",
        "App/App/Info.plist",
        "App/CapApp-SPM/Package.swift",
        "App/App/Base.lproj/Main.storyboard",
        "App/App/config.xml",
        "capacitor-cordova-ios-plugins/CordovaPluginsResources.podspec",
    ],
)
def test_template_drift_stops_before_any_write(tmp_path: Path, target: str) -> None:
    fresh = tmp_path / "workspace/apps/capture-pwa/ios"
    fresh_fixture(ROOT, fresh)
    p = fresh / target
    p.write_bytes(p.read_bytes() + b"\nunreviewed")
    output = tmp_path / "prototype"
    with pytest.raises(prototype.PrototypeError):
        prototype.prepare(ROOT, fresh, output)
    assert not output.exists()


def test_unknown_generated_input_stops(tmp_path: Path) -> None:
    fresh = tmp_path / "workspace/apps/capture-pwa/ios"
    fresh_fixture(ROOT, fresh)
    (fresh / "App/Unexpected.swift").write_text("unreviewed")
    with pytest.raises(prototype.PrototypeError):
        prototype.prepare(ROOT, fresh, tmp_path / "out")


def test_existing_destination_and_alias_are_not_modified(tmp_path: Path) -> None:
    fresh = tmp_path / "workspace/apps/capture-pwa/ios"
    fresh_fixture(ROOT, fresh)
    output = tmp_path / "out"
    output.mkdir()
    sentinel = output / "keep"
    sentinel.write_bytes(b"untouched")
    with pytest.raises(prototype.PrototypeError):
        prototype.prepare(ROOT, fresh, output)
    assert sentinel.read_bytes() == b"untouched"


def test_source_copy_map_and_patch_targets_do_not_overlap() -> None:
    scope = prototype.load_scope(ROOT)
    destinations = list(scope["generated_copies"].values())
    assert len(set(destinations)) == len(destinations)
    assert not set(destinations) & set(scope["generated_edits"])


def test_missing_compile_or_link_evidence_cannot_pass(tmp_path: Path) -> None:
    with pytest.raises(prototype.PrototypeError):
        prototype.audit_ordinary(ROOT, tmp_path, tmp_path / "App.app")


def test_native_result_missing_failures_or_zero_tests_refused() -> None:
    for value in [
        {},
        {"result": "Passed", "passedTests": 0},
        {"result": "Failed", "passedTests": 5, "failedTests": 1},
    ]:
        with pytest.raises(prototype.PrototypeError):
            prototype.classify_tests(value)
    value = prototype.classify_tests({"result": "Passed", "passedTests": 5, "failedTests": 0})
    assert value["passed"] == 5
    assert value["physical_device_backup_proven"] is False


def test_public_receipt_has_no_raw_paths_or_payloads() -> None:
    receipt = prototype.public_receipt({"core": {"passed": 2}})
    assert receipt["production_changed"] is False
    assert receipt["capture_opened"] is False
    assert receipt["ordinary_backend_admitted"] is False
    assert receipt["physical_device_backup_proven"] is False
    assert "paths" not in receipt


def test_native_link_directory_refused(tmp_path: Path) -> None:
    scope = prototype.load_scope(ROOT)
    copy_sources(ROOT, tmp_path)
    (tmp_path / prototype.PREFIX / "alias").symlink_to(
        tmp_path / prototype.PREFIX, target_is_directory=True
    )
    with pytest.raises(prototype.PrototypeError):
        prototype.validate_native(tmp_path, scope)


def test_output_cannot_be_nested_in_source_or_fresh(tmp_path: Path) -> None:
    for output in [
        ROOT / "unapproved-output",
        tmp_path / "workspace/apps/capture-pwa/ios" / "nested",
    ]:
        with pytest.raises(prototype.PrototypeError):
            prototype.validate_output(ROOT, tmp_path / "workspace/apps/capture-pwa/ios", output)
        assert not output.exists()


def test_skipped_critical_native_test_is_not_success() -> None:
    with pytest.raises(prototype.PrototypeError):
        prototype.classify_tests(
            {"result": "Passed", "passedTests": 1, "failedTests": 0, "skippedTests": 1}
        )


def test_nested_private_receipt_fields_refused() -> None:
    payloads: list[dict[str, Any]] = [
        {"core": {"passed": 2, "private_path": "/private/synthetic"}},
        {"unknown": {"raw": "synthetic"}},
    ]
    for payload in payloads:
        with pytest.raises(prototype.PrototypeError):
            prototype.public_receipt(payload)


def test_unclassified_link_input_refused(tmp_path: Path) -> None:
    p = tmp_path / "renamed.o"
    p.write_bytes(b"synthetic-object")
    with pytest.raises(prototype.PrototypeError):
        prototype.classify_link_input(str(p), set(), tmp_path / "developer", tmp_path / "sdk", {})


def test_hidden_link_map_object_cannot_be_ignored() -> None:
    data = (
        b"# Path: /synthetic/App\n# Object files:\n[  0] linker "
        b"synthesized\n[  1] /hidden/renamed.o\n# Sections:\n# Symbols:\n"
    )
    _, names = prototype.link_map_inputs(data)
    assert names == ["/hidden/renamed.o"]
    with pytest.raises(prototype.PrototypeError):
        prototype.classify_link_input(
            names[0], set(), Path("/synthetic/Developer"), Path("/synthetic/SDK"), {}
        )


def test_native_binary_tree_hashes_bytes_not_only_info(tmp_path: Path) -> None:
    p = tmp_path / "Binary"
    p.write_bytes(b"approved-synthetic-binary")
    rows = [{"path": "Binary", "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}]
    prototype.bind_tree(tmp_path, rows)
    p.write_bytes(b"different-synthetic-binary")
    with pytest.raises(prototype.PrototypeError):
        prototype.bind_tree(tmp_path, rows)


def test_every_native_case_must_run_and_pass() -> None:
    expected = prototype.expected_native_tests(ROOT, "core")
    tree = {
        "testNodes": [
            {"nodeType": "Test Case", "nodeIdentifier": name + "()", "result": "Passed"}
            for name in sorted(expected)
        ]
    }
    assert prototype.audit_test_tree(ROOT, "core", tree) == len(expected)
    tree["testNodes"].pop()
    with pytest.raises(prototype.PrototypeError):
        prototype.audit_test_tree(ROOT, "core", tree)


def test_skipped_or_unknown_native_case_is_refused() -> None:
    name = next(iter(prototype.expected_native_tests(ROOT, "host")))
    for identifier, status in [(name, "Skipped"), ("Unknown/testUnknown", "Passed")]:
        with pytest.raises(prototype.PrototypeError):
            prototype.audit_test_tree(
                ROOT,
                "host",
                {
                    "testNodes": [
                        {"nodeType": "Test Case", "nodeIdentifier": identifier, "result": status}
                    ]
                },
            )


@pytest.mark.parametrize("modern", [False, True])
def test_actual_generated_host_xctestrun_directory_layout(tmp_path: Path, modern: bool) -> None:
    products = tmp_path / "Build/Products"
    app = products / "Debug-iphonesimulator/App.app"
    app.mkdir(parents=True)
    (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": prototype.BUNDLE_ID}))
    target = {"TestHostPath": "__TESTROOT__/Debug-iphonesimulator/App.app"}
    content: dict[str, Any] = (
        {"TestConfigurations": [{"TestTargets": [target]}]}
        if modern
        else {"GSIPStorageHostPrototypeTests": target}
    )
    plan = products / "prototype.xctestrun"
    plan.write_bytes(plistlib.dumps(content))
    assert prototype.bind_test_environment(tmp_path, True) == plan
    value = plistlib.loads(plan.read_bytes())
    actual = (
        value["TestConfigurations"][0]["TestTargets"][0]
        if modern
        else value["GSIPStorageHostPrototypeTests"]
    )
    assert (
        actual["EnvironmentVariables"]["GSIP_PROTOTYPE_EXPECTED_BUNDLE_ID"] == prototype.BUNDLE_ID
    )


def ordinary_closure_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A fake compiler graph tests refusal policy, never native correctness."""
    import plistlib
    import re
    import shlex
    import subprocess
    import zipfile

    from scripts import app_notification_audit as native_audit

    root = tmp_path / "source"
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "native.swift").write_text('let canary = Data("GSIP synthetic alpha".utf8)\n')
    derived = tmp_path / "derived"
    bundle = derived / "Build/Products/Debug-iphonesimulator/App.app"
    bundle.mkdir(parents=True)
    developer = tmp_path / "Developer"
    sdk = developer / "Platforms/iPhoneSimulator.platform/iPhoneSimulator.sdk"
    sdk.mkdir(parents=True)
    tool = developer / "Toolchains/Fake.xctoolchain/usr/bin"
    tool.mkdir(parents=True)
    (tool / "swiftc").write_bytes(b"fake compiler, not native evidence")
    (tool / "clang").write_bytes(b"fake linker, not native evidence")
    templates = {
        name: b"// synthetic ordinary source\n"
        for name in (
            "App/App/AppDelegate.swift",
            "App/App/SceneDelegate.swift",
            "App/CapApp-SPM/Sources/CapApp-SPM/CapApp-SPM.swift",
        )
    }
    for name, data in templates.items():
        p = root / "apps/capture-pwa/ios" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    for name in ("pnpm-lock.yaml", "uv.lock"):
        (root / name).write_text("synthetic lock\n")
    selected = root / "apps/capture-pwa/ios/App/App/AppDelegate.swift"
    swift_list = derived / "App.SwiftFileList"
    swift_list.write_text(shlex.quote(str(selected)) + "\n")
    obj = derived / "ordinary.o"
    obj.write_bytes(b"\xcf\xfa\xed\xfe" + b"synthetic object")
    output_map = derived / "App-OutputFileMap.json"
    output_map.write_text(json.dumps({str(selected): {"object": str(obj)}}))
    link_list = derived / "App.LinkFileList"
    link_list.write_text(str(obj) + "\n")
    executable = bundle / "App"
    executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"synthetic ordinary executable")
    (bundle / "Info.plist").write_bytes(
        plistlib.dumps(
            {"CFBundleIdentifier": "com.globalsoilintelligence.app", "CFBundleExecutable": "App"}
        )
    )
    (bundle / "public").mkdir()
    (bundle / "public/gsip-activation.json").write_text(
        '{"capture_live":false,"library_intake_live":false}'
    )
    link_map = derived / "App-LinkMap.txt"
    link_map.write_text(
        f"# Path: {executable}\n# Object files:\n[  0] linker synthesized\n"
        f"[  1] {obj}\n# Sections:\n# Symbols:\n"
    )
    log = tmp_path / "build.log"
    log.write_text(
        f"builtin-SwiftDriver -- {tool}/swiftc -c @{swift_list} -output-file-map {output_map}\n"
        f"{tool}/clang -target x86_64-apple-ios15.0-simulator -isysroot {sdk} "
        f"-filelist {link_list} -Xlinker -map -Xlinker {link_map} -o {executable}\n"
        "** BUILD SUCCEEDED **\n"
    )
    artifact = tmp_path / "ordinary.zip"

    def zip_bundle() -> None:
        with zipfile.ZipFile(artifact, "w") as archive:
            for p in bundle.rglob("*"):
                if p.is_file():
                    archive.write(p, f"App.app/{p.relative_to(bundle).as_posix()}")

    zip_bundle()
    evidence = tmp_path / "native.json"
    commit = "1" * 40
    evidence.write_text(
        json.dumps(
            {
                "source_commit": commit,
                "source_inputs": {},
                "npm_sources": [],
                "spm": {"remote_source_packages": [], "binary_inputs": []},
            }
        )
    )
    monkeypatch.setattr(
        prototype,
        "load_scope",
        lambda _: {"source_bindings": {}, "native_files": [{"path": "native.swift"}]},
    )
    monkeypatch.setattr(prototype, "validate_native", lambda *_: {"prototype": "2" * 64})
    monkeypatch.setattr(prototype, "template_inputs", lambda _: (b"", templates))
    monkeypatch.setattr(native_audit, "source_inputs", lambda _: {})
    monkeypatch.setattr(native_audit, "npm_evidence", lambda *_: [])

    def validate_receipt(receipt: dict[str, Any], expected: dict[str, Any]) -> None:
        prototype.require(
            receipt["source_commit"] == expected["source_commit"], "receipt source mismatch"
        )

    monkeypatch.setattr(native_audit, "validate_native", validate_receipt)
    real_run, real_search = subprocess.run, re.search

    def fake_git(args: list[str], **kwargs: Any) -> Any:
        if args[0] == "/usr/bin/git":
            return subprocess.CompletedProcess(args, 0, (commit + "\n").encode(), b"")
        return real_run(args, **kwargs)

    def developer_match(pattern: Any, text: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(pattern, str) and pattern.startswith("(/Applications/"):
            return real_search(r"(.*)", str(developer))
        return real_search(pattern, text, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_git)
    monkeypatch.setattr(re, "search", developer_match)
    return {
        "root": candidate,
        "derived": derived,
        "bundle": bundle,
        "source": root,
        "native_path": evidence,
        "artifact": artifact,
        "build_log": log,
        "output_map": output_map,
        "object": obj,
        "swift_list": swift_list,
        "link_list": link_list,
        "zip_bundle": zip_bundle,
    }


def run_ordinary_fixture(case: dict[str, Any]) -> dict[str, Any]:
    return prototype.audit_ordinary(
        case["root"],
        case["derived"],
        case["bundle"],
        **{name: case[name] for name in ("source", "native_path", "artifact", "build_log")},
    )


def test_ordinary_closure_policy_accepts_complete_synthetic_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = run_ordinary_fixture(ordinary_closure_fixture(tmp_path, monkeypatch))
    assert result["ordinary_backend_admitted"] is False
    assert result["emitted_code_inputs"] == 2


def test_unused_output_map_cannot_admit_hidden_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = ordinary_closure_fixture(tmp_path, monkeypatch)
    hidden = case["derived"] / "hidden.o"
    hidden.write_bytes(b"\xcf\xfa\xed\xfehidden synthetic object")
    rows = json.loads(case["output_map"].read_text())
    next(iter(rows.values()))["object"] = str(hidden)
    (case["derived"] / "unused-OutputFileMap.json").write_text(json.dumps(rows))
    case["link_list"].write_text(str(hidden) + "\n")
    with pytest.raises(prototype.PrototypeError):
        run_ordinary_fixture(case)


def test_compiler_map_must_match_actual_selected_source_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = ordinary_closure_fixture(tmp_path, monkeypatch)
    case["swift_list"].write_text("")
    with pytest.raises(prototype.PrototypeError):
        run_ordinary_fixture(case)


def test_release_whole_module_object_is_bound_to_actual_driver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = ordinary_closure_fixture(tmp_path, monkeypatch)
    rows = json.loads(case["output_map"].read_text())
    for row in rows.values():
        row.pop("object")
    rows[""] = {"object": str(case["object"])}
    case["output_map"].write_text(json.dumps(rows))
    assert run_ordinary_fixture(case)["emitted_code_inputs"] == 2


def test_ordinary_receipt_cannot_choose_expected_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = ordinary_closure_fixture(tmp_path, monkeypatch)
    value = json.loads(case["native_path"].read_text())
    value["source_commit"] = "3" * 40
    case["native_path"].write_text(json.dumps(value))
    with pytest.raises(prototype.PrototypeError):
        run_ordinary_fixture(case)


def test_unlinked_bundle_code_refused_even_without_prototype_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = ordinary_closure_fixture(tmp_path, monkeypatch)
    (case["bundle"] / "renamed").write_bytes(b"\xcf\xfa\xed\xfeforeign synthetic code")
    case["zip_bundle"]()
    with pytest.raises(prototype.PrototypeError):
        run_ordinary_fixture(case)


def test_zip_artifact_must_match_inspected_bundle_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import zipfile

    case = ordinary_closure_fixture(tmp_path, monkeypatch)
    with zipfile.ZipFile(case["artifact"], "a") as archive:
        archive.writestr("App.app/extra", b"synthetic")
    with pytest.raises(prototype.PrototypeError):
        run_ordinary_fixture(case)


def test_unclassified_link_response_input_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = ordinary_closure_fixture(tmp_path, monkeypatch)
    hidden = case["derived"] / "hidden.o"
    hidden.write_bytes(b"synthetic foreign object")
    response = case["derived"] / "unknown.response"
    response.write_text(str(hidden) + "\n")
    case["build_log"].write_text(case["build_log"].read_text().replace(" -o ", f" @{response} -o "))
    with pytest.raises(prototype.PrototypeError):
        run_ordinary_fixture(case)


def test_literal_ld_list_preserves_paths_with_spaces(tmp_path: Path) -> None:
    obj = tmp_path / "directory with spaces/ordinary.o"
    obj.parent.mkdir()
    obj.write_bytes(b"synthetic")
    listing = tmp_path / "link.list"
    listing.write_text(str(obj) + "\n")
    assert prototype.listed_paths(listing) == [obj]


def test_tree_receipt_rejects_duplicate_paths(tmp_path: Path) -> None:
    item = tmp_path / "ordinary.o"
    item.write_bytes(b"synthetic")
    row = {"path": item.name, "sha256": hashlib.sha256(item.read_bytes()).hexdigest()}
    with pytest.raises(prototype.PrototypeError):
        prototype.bind_tree(tmp_path, [row, row])


def test_unbound_swift_ast_input_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = ordinary_closure_fixture(tmp_path, monkeypatch)
    hidden = case["derived"] / "hidden.swiftmodule"
    hidden.write_bytes(b"synthetic foreign module")
    case["build_log"].write_text(
        case["build_log"]
        .read_text()
        .replace(" -o ", f" -Xlinker -add_ast_path -Xlinker {hidden} -o ")
    )
    with pytest.raises(prototype.PrototypeError):
        run_ordinary_fixture(case)


def test_renamed_native_canary_resource_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = ordinary_closure_fixture(tmp_path, monkeypatch)
    (case["bundle"] / "renamed.data").write_bytes(b"prefix GSIP synthetic alpha suffix")
    case["zip_bundle"]()
    with pytest.raises(prototype.PrototypeError):
        run_ordinary_fixture(case)


def test_zip_special_file_type_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import stat
    import zipfile

    case = ordinary_closure_fixture(tmp_path, monkeypatch)
    archive_path = case["artifact"]
    with zipfile.ZipFile(archive_path) as archive:
        rows = [(item, archive.read(item)) for item in archive.infolist()]
    with zipfile.ZipFile(archive_path, "w") as archive:
        for item, data in rows:
            if item.filename == "App.app/App":
                item.external_attr = (stat.S_IFIFO | 0o600) << 16
            archive.writestr(item, data)
    with pytest.raises(prototype.PrototypeError):
        run_ordinary_fixture(case)


def test_ordinary_copy_head_must_match_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    case = ordinary_closure_fixture(tmp_path, monkeypatch)
    previous = subprocess.run

    def wrong_copy(args: list[str], **kwargs: Any) -> Any:
        if args[:3] == ["/usr/bin/git", "-C", str(case["source"])]:
            return subprocess.CompletedProcess(args, 0, ("4" * 40 + "\n").encode(), b"")
        return previous(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", wrong_copy)
    with pytest.raises(prototype.PrototypeError):
        run_ordinary_fixture(case)


@pytest.mark.parametrize("generated_exists", [False, True])
def test_original_ordinary_generated_input_is_never_patched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, generated_exists: bool
) -> None:
    output = tmp_path / "prototype"
    fresh = ROOT / "apps/capture-pwa/ios"
    original = Path.is_dir
    monkeypatch.setattr(
        Path, "is_dir", lambda path: generated_exists if path == fresh else original(path)
    )
    with pytest.raises(prototype.PrototypeError, match="ordinary project cannot be modified"):
        prototype.prepare(ROOT, fresh, output)
    assert not output.exists()


def test_workflow_uses_independently_generated_exact_commit_copy() -> None:
    workflow = (ROOT / ".github/workflows/ios-storage-prototype.yml").read_text()
    assert (
        'git clone --no-hardlinks --no-checkout "$GITHUB_WORKSPACE" '
        '"$RUNNER_TEMP/gsip-app2c2a-ordinary-source"' in workflow
    )
    assert 'checkout --detach "$source_commit"' in workflow
    invocation = next(
        line
        for line in workflow.splitlines()
        if "ios_storage_prototype" in line and " run " in line
    )
    assert invocation.strip().startswith("run: python -m scripts.ios_storage_prototype run ")
    assert '"$RUNNER_TEMP/gsip-app2c2a-ordinary-source/apps/capture-pwa/ios"' in invocation
    assert '"$GITHUB_WORKSPACE/apps/capture-pwa/ios"' not in invocation
    assert "persist-credentials: false" in workflow


@pytest.mark.parametrize("target", list(INERT_METADATA_FIXTURES))
def test_missing_inert_metadata_stops_before_any_write(tmp_path: Path, target: str) -> None:
    fresh = tmp_path / "workspace/apps/capture-pwa/ios"
    fresh_fixture(ROOT, fresh)
    (fresh / target).unlink()
    output = tmp_path / "prototype"
    with pytest.raises(prototype.PrototypeError, match="unknown or missing generated input"):
        prototype.prepare(ROOT, fresh, output)
    assert not output.exists()


def test_metadata_fixture_bytes_match_exact_bindings() -> None:
    assert set(INERT_METADATA_FIXTURES) == set(prototype.GENERATED_METADATA_SHA256)
    for name, data in INERT_METADATA_FIXTURES.items():
        assert hashlib.sha256(data).hexdigest() == prototype.GENERATED_METADATA_SHA256[name]


def test_actual_template_reader_still_refuses_package_store_hardlinks(tmp_path: Path) -> None:
    import os

    installed = (ROOT / "apps/capture-pwa/node_modules/@capacitor/cli").resolve(strict=True)
    owned = tmp_path / "hardlinked-template-root"
    destination = owned / "apps/capture-pwa/node_modules/@capacitor/cli"
    for relative in ("package.json", "assets/ios-spm-template.tar.gz"):
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((installed / relative).read_bytes())
    archive = destination / "assets/ios-spm-template.tar.gz"
    os.link(archive, tmp_path / "archive-alias")
    with pytest.raises(prototype.PrototypeError, match="nonregular input refused"):
        prototype.template_inputs(owned)


def test_failed_tool_diagnostics_never_echo_raw_output_or_unapproved_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import subprocess

    private = "opaque-private-canary-payload"
    allowed = "StorageCoordinatorTests/testSyntheticFailure"

    def failed(args: list[str], **kwargs: Any) -> Any:
        kwargs["stdout"].write(
            (
                "error: no such module " + private + "\n"
                "Test Case '-[Module.StorageCoordinatorTests testSyntheticFailure]' failed\n"
                "Test Case '-[Module.PrivateFixture testUnapproved]' failed\n" + private + "\n"
            ).encode()
        )
        return subprocess.CompletedProcess(args, 65)

    monkeypatch.setattr(subprocess, "run", failed)
    with pytest.raises(prototype.PrototypeError, match="failed at core-test"):
        prototype.run_private(
            ["xcodebuild", "test-without-building"],
            tmp_path,
            tmp_path / "core-test.log",
            expected_tests={allowed},
        )
    output = capsys.readouterr().out
    assert allowed in output and "missing-module" in output and '"exit": 65' in output
    assert private not in output and "testUnapproved" not in output and str(tmp_path) not in output


def test_unknown_private_log_path_and_timeout_only_emit_fixed_labels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import subprocess

    def expired(args: list[str], **kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired(args, 300, "private-canary-timeout")

    monkeypatch.setattr(subprocess, "run", expired)
    with pytest.raises(prototype.PrototypeError, match="timed out at private-tool") as failure:
        prototype.run_private(["private-command"], tmp_path, tmp_path / "unapproved-private-name")
    combined = capsys.readouterr().out + str(failure.value)
    assert "private-canary" not in combined and "unapproved-private-name" not in combined
    assert "private-command" not in combined and str(tmp_path) not in combined


def test_diagnostic_binary_unknown_and_oversized_logs_remain_bounded(tmp_path: Path) -> None:
    path = tmp_path / "diagnostic.log"
    private = "opaque-private-diagnostic-value"
    allowed = {"KnownTests/testCase" + str(i) for i in range(20)}
    path.write_bytes(
        b"\xff\x1b[31m"
        + private.encode()
        + b"\n"
        + "".join(
            "Test Case '-[Module.KnownTests testCase" + str(i) + "]' failed: " + private + "\n"
            for i in range(20)
        ).encode()
    )
    categories, identities = prototype.private_failure_labels(path, allowed)
    assert categories == ["unclassified"]
    assert len(identities) == 16 and set(identities) <= allowed
    assert private not in str((categories, identities))
    with path.open("wb") as stream:
        stream.truncate(16 * 1024 * 1024 + 1)
    assert prototype.private_failure_labels(path, allowed) == (["diagnostic-size-held"], [])
    assert prototype.private_failure_labels(tmp_path / "missing", allowed) == (
        ["diagnostic-unavailable"],
        [],
    )


def test_test_build_failure_is_not_mislabelled_as_ordinary_build(tmp_path: Path) -> None:
    path = tmp_path / "build.log"
    path.write_text("** TEST BUILD FAILED **\n")
    assert prototype.private_failure_labels(path, set()) == (["native-build-failure"], [])


@pytest.mark.parametrize(
    "output",
    [
        b"Xcode 26.6\nBuild version 17F113\n",
        b"Xcode 27.1\nBuild version 27A9275\n",
        b"Xcode 27.0\nBuild version private-canary-version\n",
        b"Xcode 27.0\nBuild version 27A266a\nextra\n",
        b"",
    ],
)
def test_toolchain_drift_is_refused_without_echoing_input(output: bytes) -> None:
    with pytest.raises(prototype.PrototypeError, match="audited Xcode") as failure:
        prototype.require_audited_xcode(output)
    assert "private-canary-version" not in str(failure.value)


def test_exact_audited_toolchain_and_workflow_binding() -> None:
    prototype.require_audited_xcode(b"Xcode 27.0\nBuild version 27A266a\n")
    workflow = (ROOT / ".github/workflows/ios-storage-prototype.yml").read_text()
    assert "runs-on: xcode-27" in workflow
    assert "DEVELOPER_DIR: /Applications/Xcode_27.0.app/Contents/Developer" in workflow
    assert 'require_audited_xcode(subprocess.check_output(["xcodebuild", "-version"]))' in workflow
    assert "sort -V" not in workflow and "xcode-select" not in workflow


def test_partial_test_progress_is_allowlisted_and_distinguishes_unavailable(tmp_path: Path) -> None:
    path = tmp_path / "test.log"
    private = "opaque-private-status-payload"
    path.write_text(
        "Test Case '-[Module.KnownTests testDone]' started.\n"
        "Test Case '-[Module.KnownTests testDone]' passed: " + private + "\n"
        "Test Case '-[Module.KnownTests testStillRunning]' started.\n"
        "Test Case '-[Module.Unknown testPrivate]' started.\n"
    )
    allowed = {"KnownTests/testDone", "KnownTests/testStillRunning"}
    assert prototype.private_test_progress(path, allowed) == {
        "available": True,
        "observed_started": 2,
        "observed_passed": 1,
        "observed_failed": 0,
        "unfinished_test_identities": ["KnownTests/testStillRunning"],
    }
    result = prototype.private_test_progress(tmp_path / "missing", allowed)
    assert result["available"] is False
    assert private not in str(result) and "testPrivate" not in str(result)


def test_timeout_reports_only_allowlisted_partial_status_and_keeps_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import subprocess

    def expired(args: list[str], **kwargs: Any) -> Any:
        kwargs["stdout"].write(
            b"Test Case '-[Module.KnownTests testActive]' started.\nprivate-canary-timeout"
        )
        kwargs["stdout"].flush()
        raise subprocess.TimeoutExpired(args, 300, "private-canary-timeout")

    monkeypatch.setattr(subprocess, "run", expired)
    with pytest.raises(prototype.PrototypeError, match="timed out at core-test"):
        prototype.run_private(
            ["xcodebuild", "test-without-building"],
            tmp_path,
            tmp_path / "core-test.log",
            expected_tests={"KnownTests/testActive"},
        )
    output = capsys.readouterr().out
    assert "KnownTests/testActive" in output and '"observed_started": 1' in output
    assert "private-canary-timeout" not in output and str(tmp_path) not in output


def test_restarted_case_is_reported_unfinished_even_after_an_earlier_pass(tmp_path: Path) -> None:
    path = tmp_path / "test.log"
    path.write_text(
        "Test Case '-[Module.KnownTests testRestarted]' started.\n"
        "Test Case '-[Module.KnownTests testRestarted]' passed.\n"
        "Test Case '-[Module.KnownTests testRestarted]' started.\n"
    )
    progress = prototype.private_test_progress(path, {"KnownTests/testRestarted"})
    assert progress["observed_started"] == progress["observed_passed"] == 1
    assert progress["unfinished_test_identities"] == ["KnownTests/testRestarted"]


def test_native_exception_diagnostics_report_fixed_holds_and_cocoa_categories_only(
    tmp_path: Path,
) -> None:
    path = tmp_path / "test.log"
    private = "private-fixture-path-and-payload"
    path.write_text(
        'failed: caught error: "boundary"\n'
        'failed: threw error "unavailable"\n'
        'Error Domain=NSCocoaErrorDomain Code=260 "' + private + '"\n'
        'Error Domain=NSCocoaErrorDomain Code=513 "' + private + '"\n'
        'failed: caught error: "' + private + '"\n'
        'Error Domain=PrivateDomain Code=999 "' + private + '"\n'
    )
    categories, identities = prototype.private_failure_labels(path, set())
    assert categories == [
        "cocoa-no-such-file", "cocoa-write-permission", "storage-hold-boundary",
        "storage-hold-unavailable",
    ]
    assert identities == [] and private not in str(categories)


def test_failed_native_fixture_emits_only_fixed_boolean_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import subprocess

    private = "private-native-root-and-payload"
    allowed = {
        "part": "base", "ancestor_safe": True, "present": True,
        "expected_kind": True, "owned": True,
        "private_mode": True, "link_policy": True, "size_bounded": True,
        "identity_stable": True, "protection_query_ok": True, "protection_available": False,
        "protection_complete": False, "exclusion_query_ok": True, "exclusion_available": True,
        "backup_excluded": True, "volume_query_ok": True, "volume_protection_available": True,
        "volume_supports_protection": False,
    }

    def failed(args: list[str], **kwargs: Any) -> Any:
        records = [allowed, allowed | {"path": private}, allowed | {"owned": private}]
        kwargs["stdout"].write(
            ("".join("GSIP_SQLITE_FIXTURE=" + json.dumps(x) + "\n" for x in records)
             + private).encode()
        )
        return subprocess.CompletedProcess(args, 65)

    monkeypatch.setattr(subprocess, "run", failed)
    with pytest.raises(prototype.PrototypeError):
        prototype.run_private(
            ["xcodebuild", "test-without-building"], tmp_path, tmp_path / "core-test.log",
            expected_tests={"KnownTests/testCase"},
        )
    output = capsys.readouterr().out
    line = next(x for x in output.splitlines() if x.startswith("APP-2C2A bounded failure: "))
    diagnostic = json.loads(line.split(": ", 1)[1])
    assert diagnostic["fixture_metadata"] == [allowed]
    assert private not in output and str(tmp_path) not in output


def test_fixture_metadata_is_deduplicated_bounded_and_unknown_input_is_private(
    tmp_path: Path,
) -> None:
    path = tmp_path / "native.log"
    valid = {key: False for key in prototype.FIXTURE_BOOLEAN_FIELDS} | {"part": "root"}
    records = [valid, valid, valid | {"part": "private-path"}, valid | {"present": 1}]
    records += [valid | {key: True} for key in sorted(prototype.FIXTURE_BOOLEAN_FIELDS)]
    path.write_text("\n".join("GSIP_SQLITE_FIXTURE=" + json.dumps(x) for x in records))
    observed = prototype.private_fixture_metadata(path)
    assert len(observed) == 9 and observed[0] == valid
    assert all(x["part"] == "root" for x in observed)
    assert all(type(x[key]) is bool for x in observed for key in prototype.FIXTURE_BOOLEAN_FIELDS)
    path.write_text('GSIP_SQLITE_FIXTURE={malformed}\nGSIP_SQLITE_FIXTURE=[]\n')
    assert prototype.private_fixture_metadata(path) == []
    with path.open("wb") as stream:
        stream.truncate(16 * 1024 * 1024 + 1)
    assert prototype.private_fixture_metadata(path) == []
    assert prototype.private_fixture_metadata(tmp_path / "missing") == []


def test_injected_decoder_recursion_failure_stays_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "native.log"
    path.write_text('GSIP_SQLITE_FIXTURE={"private":"not-output"}')

    def unavailable_decoder(value: str) -> Any:
        raise RecursionError("private-decoder-failure")

    monkeypatch.setattr(json, "loads", unavailable_decoder)
    assert prototype.private_fixture_metadata(path) == []


def test_passing_suite_refuses_failure_marker_but_ignores_validation_control(
    tmp_path: Path,
) -> None:
    path = tmp_path / "native.log"
    report = {key: False for key in prototype.FIXTURE_BOOLEAN_FIELDS} | {"part": "root"}
    path.write_text("GSIP_SQLITE_FIXTURE=" + json.dumps(report))
    with pytest.raises(prototype.PrototypeError, match="fixture-failure marker"):
        prototype.require_clean_fixture_status(path)
    path.write_text("GSIP_SQLITE_CONTROL=" + json.dumps(report))
    prototype.require_clean_fixture_status(path)
    assert prototype.private_fixture_metadata(path) == []
