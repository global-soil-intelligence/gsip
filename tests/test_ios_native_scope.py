"""V13 prospective scope guards; these tests never grant or execute native code."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "apps/capture-pwa/native/ios/GSIPPrivateStorePrototype/"
CORE = ("StorageContract", "ExcludedSQLiteStore", "KeychainAnchor", "StorageCoordinator")
CORE_TESTS = (
    "ExcludedSQLiteStoreTests",
    "KeychainAnchorTests",
    "StorageCoordinatorTests",
    "NativeTestDoubles",
)
HOST = (
    "PrototypeHostController",
    "BridgeMessageGate",
    "AssetRequestGate",
    "PrototypeDelegationHandler",
    "OwnedTemporaryPhotoBroker",
    "PrototypeStorePlugin",
)
NATIVE = {PREFIX + "Package.swift"} | {
    f"{PREFIX}{folder}/{name}.swift"
    for folder, names in (
        ("Sources/GSIPStorageCore", CORE),
        ("Tests/GSIPStorageCoreTests", CORE_TESTS),
        ("Sources/GSIPStorageHostPrototype", HOST),
        ("Tests/GSIPStorageHostPrototypeTests", tuple(f"{name}Tests" for name in HOST)),
    )
    for name in names
}
SUPPORT = {
    "scripts/ios_storage_prototype.py",
    "tests/test_ios_storage_prototype.py",
    ".github/workflows/ios-storage-prototype.yml",
}
GENERATED = {
    "App/App.xcodeproj/project.pbxproj",
    "App/App/SceneDelegate.swift",
    "App/App/Base.lproj/Main.storyboard",
    "App/App/Info.plist",
    "App/CapApp-SPM/Package.swift",
    "App/App.xcodeproj/xcshareddata/xcschemes/GSIPStoragePrototype.xcscheme",
    "App/App/public/index.html",
    "App/App/public/gsip-activation.json",
    "App/App/capacitor.config.json",
}
MODULES = {
    "PackageDescription",
    "Foundation",
    "Dispatch",
    "Darwin",
    "SQLite3",
    "Security",
    "CryptoKit",
    "UIKit",
    "WebKit",
    "Capacitor",
    "Cordova",
    "XCTest",
    "GSIPStorageCore",
    "App",
}


IMPORT_CEILINGS = {
    "Package": "PackageDescription",
    "StorageContract": "Foundation",
    "ExcludedSQLiteStore": "Foundation Darwin SQLite3 CryptoKit",
    "KeychainAnchor": "Foundation Security",
    "StorageCoordinator": "Foundation Dispatch",
    "ExcludedSQLiteStoreTests": "XCTest Foundation Darwin SQLite3 GSIPStorageCore",
    "KeychainAnchorTests": "XCTest Foundation Security GSIPStorageCore",
    "StorageCoordinatorTests": "XCTest Foundation Dispatch GSIPStorageCore",
    "NativeTestDoubles": "Foundation GSIPStorageCore",
    "PrototypeHostController": "Foundation UIKit WebKit Capacitor Cordova GSIPStorageCore",
    "BridgeMessageGate": "Foundation WebKit Capacitor GSIPStorageCore",
    "AssetRequestGate": "Foundation WebKit Capacitor GSIPStorageCore",
    "PrototypeDelegationHandler": "Foundation UIKit WebKit Capacitor GSIPStorageCore",
    "OwnedTemporaryPhotoBroker": "Foundation Darwin CryptoKit GSIPStorageCore",
    "PrototypeStorePlugin": "Foundation Capacitor GSIPStorageCore",
}
for name in HOST:
    IMPORT_CEILINGS[name + "Tests"] = "XCTest " + IMPORT_CEILINGS[name] + " App"
EFFECTS = dict(
    zip(
        CORE + HOST,
        (
            "bounded-values",
            "excluded-fixed-sqlite",
            "synthetic-anchor",
            "serialized-coordinator",
            "nonpersistent-held-host",
            "main-frame-allowlist",
            "owned-asset-allowlist",
            "prompt-navigation-deny",
            "synthetic-canary-broker",
            "typed-synthetic-operations",
        ),
        strict=True,
    )
)
BINDINGS = {
    "pnpm-lock.yaml",
    "apps/capture-pwa/capacitor.config.ts",
    "apps/capture-pwa/package.json",
    ".github/workflows/app-build.yml",
    "scripts/app_build.py",
    "scripts/app_permissions.py",
    "scripts/app_notification_audit.py",
    "tests/test_app_build.py",
    "tests/test_app_permissions.py",
}


def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        assert key not in result, "Duplicate scope fields cannot override a restriction"
        result[key] = value
    return result


def scope() -> dict[str, Any]:
    path = ROOT / "docs/ios-native-scope.json"
    assert path.is_file(), "An exact finite scope must exist before native implementation"
    raw = path.read_bytes()
    assert len(raw) <= 65_536
    value = json.loads(raw, object_pairs_hook=no_duplicates)
    assert isinstance(value, dict)
    return value


def literal(path: str) -> None:
    assert path.isascii() and not re.search(r"[\x00-\x20*?\[\]{}\\]", path)
    assert str(PurePosixPath(path)) == path and not path.startswith("/")
    assert not {".", ".."} & set(path.split("/"))


def validate(value: dict[str, Any]) -> None:
    assert set(value) == {
        "schema",
        "baseline",
        "owner_policy",
        "document_grants_implementation",
        "native_files",
        "support_files",
        "generated_edits",
        "generated_copies",
        "execution",
        "namespaces",
        "package",
        "limits",
        "prohibited",
        "source_bindings",
        "artifact_boundary",
    }
    assert value["schema"] == "gsip-app2c2a-scope-v1"
    assert value["baseline"] == "6a652f94b220be7eeff49508283883c502baa527"
    assert value["document_grants_implementation"] is False
    assert value["owner_policy"] == {
        "design": "approved-2026-10-14",
        "passcode_required": True,
        "preserve_quarantine": True,
        "automatic_reset": False,
        "accessibility": "kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly",
        "synchronizable": False,
        "access_group": "ordinary-default-only",
    }
    native = value["native_files"]
    assert len(native) == 21 and {row["path"] for row in native} == NATIVE
    for row in native:
        assert set(row) == {"path", "kind", "imports", "effect"}
        literal(row["path"])
        assert row["kind"] in {"manifest", "core", "core-test", "host", "host-test"}
        assert row["imports"] and len(set(row["imports"])) == len(row["imports"])
        assert set(row["imports"]) <= MODULES
        name = PurePosixPath(row["path"]).stem
        assert set(row["imports"]) <= set(IMPORT_CEILINGS[name].split())
        expected_kind = (
            "manifest"
            if name == "Package"
            else "core-test"
            if "/Tests/GSIPStorageCoreTests/" in row["path"]
            else "host-test"
            if "/Tests/GSIPStorageHostPrototypeTests/" in row["path"]
            else "core"
            if "/Sources/GSIPStorageCore/" in row["path"]
            else "host"
        )
        assert row["kind"] == expected_kind
        expected_effect = (
            "core-package-only"
            if expected_kind == "manifest"
            else "direct-synthetic-tests"
            if expected_kind.endswith("test")
            else EFFECTS[name]
        )
        assert row["effect"] == expected_effect
        assert row["effect"] in {
            "core-package-only",
            "bounded-values",
            "excluded-fixed-sqlite",
            "synthetic-anchor",
            "serialized-coordinator",
            "nonpersistent-held-host",
            "main-frame-allowlist",
            "owned-asset-allowlist",
            "prompt-navigation-deny",
            "synthetic-canary-broker",
            "typed-synthetic-operations",
            "direct-synthetic-tests",
        }
        if row["kind"] in {"core", "core-test"}:
            assert not {"Capacitor", "Cordova", "UIKit", "WebKit", "App"} & set(row["imports"])
        if row["kind"] not in {"core-test", "host-test"}:
            assert "XCTest" not in row["imports"]
        if row["kind"] == "manifest":
            assert row["path"] == PREFIX + "Package.swift"
            assert row["imports"] == ["PackageDescription"]
    assert len(value["support_files"]) == 3 and set(value["support_files"]) == SUPPORT
    assert len(value["generated_edits"]) == 9 and set(value["generated_edits"]) == GENERATED
    for path in value["support_files"] + value["generated_edits"]:
        literal(path)
    copies = {}
    for source in NATIVE:
        relative = source.removeprefix(PREFIX)
        if relative.startswith("Sources/GSIPStorageHostPrototype/"):
            destination = "App/App/GSIPStorageHostPrototype/" + PurePosixPath(relative).name
        elif relative.startswith("Tests/GSIPStorageHostPrototypeTests/"):
            destination = "App/GSIPStorageHostPrototypeTests/" + PurePosixPath(relative).name
        else:
            destination = "GSIPPrivateStorePrototype/" + relative
        literal(destination)
        copies[source] = destination
    assert len(set(copies.values())) == 21
    assert not set(copies.values()) & GENERATED
    assert value["generated_copies"] == copies
    assert value["execution"] == {
        "target": "future-disposable-ios-simulator-only",
        "physical_device": False,
        "macos_keychain": False,
        "ordinary_app_wiring": False,
        "signing": False,
        "native_network": False,
        "real_camera_or_location": False,
        "automatic_package_registration": False,
        "application_notification_routing": False,
        "notification_operations": False,
    }
    assert value["namespaces"] == {
        "bundle_id": "com.globalsoilintelligence.app.storageprototype",
        "root": "Library/GSIPStoragePrototype-v1/<native-run-nonce>",
        "database": "gsip-app2c2a.sqlite3",
        "keychain_service": "com.globalsoilintelligence.app.storageprototype.synthetic.v1",
        "keychain_account": "anchor-<native-run-nonce>",
        "core_test_identity": "bind-fresh-ios-test-runner-never-ordinary-app",
    }
    assert value["package"] == {
        "targets": ["GSIPStorageCore", "GSIPStorageCoreTests"],
        "external_dependencies": [],
        "plugins": [],
        "binary_targets": [],
        "host_linkage": "fresh-existing-CapApp-SPM-products-only",
        "npm_ios_is_swift_package": False,
    }
    assert value["limits"] == {
        "max_counter": 9_007_199_254_740_991,
        "wrap_counters": False,
        "chunk_bytes": 131_072,
        "frame_bytes": 524_288,
        "managed_bytes": 268_435_456,
    }
    assert value["artifact_boundary"] == "compiled-inputs-link-graph-and-bundle-not-debug-only"
    assert set(value["prohibited"]) == {
        "ordinary-app-data",
        "ordinary-app-registration",
        "auth-sdk",
        "legacy-export-migration",
        "reset-or-new-account",
        "arbitrary-path-sql-or-keychain-query",
        "new-dependency-or-core-fork",
        "entitlement-permission-background-mode-change",
        "production-deployment-or-worker",
        "capture-or-signin-opening",
        "secret-or-photo-logging",
        "weaker-keychain-class",
        "real-camera-or-picker-integration",
        "physical-device-or-backup-operation",
    }
    assert set(value["source_bindings"]) == BINDINGS
    for path, digest in value["source_bindings"].items():
        literal(path)
        assert re.fullmatch(r"[0-9a-f]{64}", digest)
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_finite_source_scope_and_approved_policy_have_no_implicit_implementation_grant() -> None:
    validate(scope())


@pytest.mark.parametrize("case", range(34))
def test_unsafe_scope_expansion_or_policy_weakening_is_rejected(case: int) -> None:
    value = copy.deepcopy(scope())
    if case == 0:
        value["native_files"][0]["path"] = PREFIX + "**/*.swift"
    elif case == 1:
        value["native_files"][0]["path"] = PREFIX + "../Escape.swift"
    elif case == 2:
        value["native_files"].append(copy.deepcopy(value["native_files"][0]))
    elif case == 3:
        value["native_files"].pop()
    elif case == 4:
        value["native_files"][1]["imports"].append("Network")
    elif case == 5:
        value["native_files"][1]["imports"].append("Capacitor")
    elif case == 6:
        value["owner_policy"]["accessibility"] = "kSecAttrAccessibleWhenUnlockedThisDeviceOnly"
    elif case == 7:
        value["owner_policy"]["synchronizable"] = True
    elif case == 8:
        value["owner_policy"]["automatic_reset"] = True
    elif case == 9:
        value["owner_policy"]["passcode_required"] = False
    elif case == 10:
        value["owner_policy"]["access_group"] = "shared-group"
    elif case == 11:
        value["namespaces"]["bundle_id"] = "com.globalsoilintelligence.app"
    elif case == 12:
        value["execution"]["target"] = "macos-host"
    elif case == 13:
        value["execution"]["physical_device"] = True
    elif case == 14:
        value["execution"]["ordinary_app_wiring"] = True
    elif case == 15:
        value["execution"]["native_network"] = True
    elif case == 16:
        value["package"]["external_dependencies"].append("unreviewed-engine")
    elif case == 17:
        value["generated_edits"].append("App/App/AppDelegate.swift")
    elif case == 18:
        value["support_files"][0] = ".github/workflows/app-build.yml"
    elif case == 19:
        value["artifact_boundary"] = "debug-flag-only"
    elif case == 20:
        value["limits"]["wrap_counters"] = True
    elif case == 21:
        value["document_grants_implementation"] = True
    elif case == 22:
        value["prohibited"].remove("reset-or-new-account")
    elif case == 23:
        value["source_bindings"]["pnpm-lock.yaml"] = "0" * 64
    elif case == 24:
        value["native_files"][1]["imports"].append("Security")
    elif case == 25:
        value["native_files"][1]["kind"] = "host"
    elif case == 26:
        value["native_files"][1]["effect"] = "synthetic-anchor"
    elif case == 27:
        value["source_bindings"].pop("scripts/app_permissions.py")
    elif case == 28:
        value["execution"]["automatic_package_registration"] = True
    elif case == 29:
        value["execution"]["application_notification_routing"] = True
    elif case == 30:
        value["execution"]["notification_operations"] = True
    elif case == 31:
        value["namespaces"]["core_test_identity"] = "com.globalsoilintelligence.app"
    elif case == 32:
        value["generated_copies"][PREFIX + "Package.swift"] = "App/App/Package.swift"
    else:
        value["generated_copies"].pop(PREFIX + "Package.swift")
    with pytest.raises(AssertionError):
        validate(value)


def test_duplicate_manifest_fields_cannot_replace_a_restriction() -> None:
    validate(scope())
    with pytest.raises(AssertionError):
        json.loads('{"grant":false,"grant":true}', object_pairs_hook=no_duplicates)


def test_review_doc_enumerates_every_native_path_and_current_owner_status() -> None:
    value = scope()
    text = re.sub(r"\s+", " ", (ROOT / "docs/IOS_NATIVE_SCOPE.md").read_text())
    for row in value["native_files"]:
        assert f"`{row['path'].removeprefix(PREFIX)}`" in text
    for phrase in (
        "passcode and recovery safeguards are approved",
        "native-code exception remains pending",
        "No native implementation",
        "synthetic",
        "not a standalone Swift package",
        "no automatic destructive reset",
        "not device or backup proof",
        "normal app",
        "AppDelegate",
        "stop for amended scope",
    ):
        assert phrase.lower() in text.lower()
    foundation = text.split("- Foundation:", 1)[1].split("- SQLite3:", 1)[0]
    assert "No URLSession, external URL load, arbitrary directory traversal" in foundation
    assert "no process/exit/socket or generic native syscall bridge" in foundation
    sqlite = text.split("- SQLite3:", 1)[1].split("- Security:", 1)[0]
    assert "No caller SQL/PRAGMA/path, ATTACH, extensions, VACUUM" in sqlite
    assert "global temp override or hot-journal deletion" in sqlite
    security = text.split("- Security:", 1)[1].split("- Dispatch:", 1)[0]
    assert "No SecItemDelete, broad query, sharing group, personal Keychain search" in security
    assert "no weaker class or fake device pass" in security
    host = text.split("- UIKit/WebKit/Capacitor/Cordova:", 1)[1].split(
        "- The temporary-photo broker", 1
    )[0]
    for requirement in (
        "autoRegisterPlugins:false",
        "handleApplicationNotifications=false",
        "before InstanceConfiguration/bridge construction",
        "verify the readonly configuration",
        "ios.handleApplicationNotifications:false",
        "core plugins and NotificationRouter are still constructed",
        "no real pending/delivered enumeration, scheduling, cancellation or callbacks",
    ):
        assert requirement in host


def test_scope_does_not_check_off_existing_implementation_or_device_acceptance() -> None:
    validate(scope())
    spec = (ROOT / "docs/SPEC.md").read_text()
    build = (ROOT / "docs/BUILD_ORDER.md").read_text()
    assert "### 15.12 Proposed v13" in spec and "IOS_NATIVE_SCOPE.md" in spec
    assert "Exact v13 native-scope review" in build
    section = build.split("Exact v13 native-scope review", 1)[1].split("**WP-APP-2C2B", 1)[0]
    assert section.count("- [ ]") == 2 and "- [x]" not in section
