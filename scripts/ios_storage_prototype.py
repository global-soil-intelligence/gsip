"""APP-2C2A's finite synthetic simulator harness, never an app storage backend.

Only standard-library host tooling. The v13 scope is immutable; the owner's separate
approval supplies authority. Raw build/test output stays under a new private run root.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import plistlib
import re
import shlex
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, cast

PREFIX = "apps/capture-pwa/native/ios/GSIPPrivateStorePrototype"
SCOPE_SHA = "810bca4dcaa09a796e3622f72c0c5f48f56d0ce70b0688eb24de4cf6fab7ac9d"
TEMPLATE_SHA = "a00e318f82fcaa9bc5fa7d851fa1ce1f3a15ae59147b703afbed5dff6279556d"
BUNDLE_ID = "com.globalsoilintelligence.app.storageprototype"
APP_TARGET = "504EC3031FED79650016851F"
TEST_TARGET = "AC2C2A000000000000000001"
PLUGINS = (
    ("CapacitorCamera", "camera", "8.2.4"),
    ("CapacitorFilesystem", "filesystem", "8.1.3"),
    ("CapacitorGeolocation", "geolocation", "8.2.2"),
    ("CapacitorLocalNotifications", "local-notifications", "8.3.1"),
)
# Inert generated namespace/Podspec metadata: exact bytes are bound, never reconstructed.
GENERATED_METADATA_SHA256 = {
    "App/App/config.xml": "e9dcda493e663c5c4db9e3cb3bd968477a6e90aa8840bcbba40d72ed54b767ce",
    "capacitor-cordova-ios-plugins/CordovaPluginsResources.podspec": (
        "6ace787f88f8c8da88526ed2ecdf0b9bd659cdb64f56bd5e73a684e0d26b7e06"
    ),
}
# No web app/auth SDK is present in this resource. Native XCTest owns admission.
PROBE_HTML = (
    b'<!doctype html><meta charset="utf-8"><title>Synthetic storage '
    b"probe</title><p>Held synthetic prototype</p>\n"
)
ACTIVATION = b'{"capture_live":false,"library_intake_live":false}\n'
SCENE = """import UIKit

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    func scene(_ scene: UIScene, willConnectTo session: UISceneSession,
               options connectionOptions: UIScene.ConnectionOptions) {
        guard let scene = scene as? UIWindowScene else { return }
        window = UIWindow(windowScene: scene)
        window?.rootViewController = PrototypeHostController()
        window?.makeKeyAndVisible()
    }
    func sceneWillResignActive(_ scene: UIScene) { hold() }
    func sceneDidEnterBackground(_ scene: UIScene) { hold() }
    func sceneDidDisconnect(_ scene: UIScene) { hold() }
    func scene(_ scene: UIScene, openURLContexts contexts: Set<UIOpenURLContext>) { hold() }
    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) { hold() }
    private func hold() {
        (window?.rootViewController as? PrototypeHostController)?.suspendForLifecycle()
    }
}
"""


class PrototypeError(ValueError):
    """A bounded refusal; never include private input in the public exception."""


def require(value: object, reason: str = "prototype admission refused") -> None:
    if not value:
        raise PrototypeError(reason)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_relative(value: str) -> PurePosixPath:
    p = PurePosixPath(value)
    require(bool(value) and not p.is_absolute() and ".." not in p.parts)
    require(str(p) == value and "\\" not in value and "\x00" not in value)
    return p


def regular_bytes(path: Path) -> bytes:
    # Walk every ancestor: resolving first would erase evidence of a symlink.
    for parent in (path, *path.parents):
        require(not parent.is_symlink(), "linked input refused")
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "nonregular input refused")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as f:
        opened = os.fstat(f.fileno())
        require((opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino))
        data = f.read()
        after = os.fstat(f.fileno())
        require((after.st_size, after.st_mtime_ns) == (info.st_size, info.st_mtime_ns))
    return data


def load_scope(root: Path) -> dict[str, Any]:
    data = regular_bytes(root / "docs/ios-native-scope.json")
    require(digest(data) == SCOPE_SHA, "reviewed scope drift")
    value: dict[str, Any] = json.loads(data)
    require(len(value["native_files"]) == 21 and len(value["generated_copies"]) == 21)
    require(len(value["generated_edits"]) == 9)
    return value


def validate_native(root: Path, scope: dict[str, Any]) -> dict[str, str]:
    expected = {item["path"] for item in scope["native_files"]}
    directory = root / PREFIX
    nodes = list(directory.rglob("*"))
    require(not any(p.is_symlink() for p in nodes), "linked native directory")
    actual = {str(p.relative_to(root)) for p in nodes if not p.is_dir()}
    require(actual == expected, "native file scope drift")
    result: dict[str, str] = {}
    for item in scope["native_files"]:
        data = regular_bytes(root / safe_relative(item["path"]))
        text = data.decode("utf-8")
        imports = set(re.findall(r"(?m)^\s*(?:@testable\s+)?import\s+(\w+)", text))
        require(imports <= set(item["imports"]), "native import scope drift")
        # Supplemental source guard; native behavior must also pass direct tests.
        forbidden = (
            r"\b(?:SecItemDelete|URLSession|UserDefaults|dlopen|dlsym|system|"
            r"popen|fork|execv|socket|sqlite3_load_extension|"
            r"sqlite3_enable_load_extension|sqlite3_vfs_register)\s*\("
        )
        require(not re.search(forbidden, text), "unapproved native effect")
        if item["kind"] not in {"core-test", "host-test"}:
            require("kSecAttrAccessibleAfterFirstUnlock" not in text)
            require("kSecAttrAccessibleWhenUnlocked" not in text)
        result[item["path"]] = digest(data)
    package = (root / PREFIX / "Package.swift").read_text()
    require(".iOS(.v15)" in package and ".macOS(" not in package)
    require(not re.search(r"\.(?:executableTarget|binaryTarget|plugin|package)\s*\(", package))
    require('name: "GSIPStorageCore"' in package and 'name: "GSIPStorageCoreTests"' in package)
    return result


def validate_sources(root: Path) -> dict[str, str]:
    scope = load_scope(root)
    for path, expected in scope["source_bindings"].items():
        require(digest(regular_bytes(root / safe_relative(path))) == expected, "frozen input drift")
    return validate_native(root, scope)


def validate_output(root: Path, fresh: Path, output: Path) -> None:
    require(output.is_absolute() and not output.exists() and not output.is_symlink())
    require(output == output.resolve(), "aliased output")
    for forbidden in (root.resolve(), fresh.resolve()):
        require(not output.is_relative_to(forbidden) and not forbidden.is_relative_to(output))
    allowed = [Path("/private/tmp"), Path(tempfile.gettempdir()).resolve()]
    if os.environ.get("RUNNER_TEMP"):
        allowed.append(Path(os.environ["RUNNER_TEMP"]).resolve())
    require(any(output.is_relative_to(base) for base in allowed), "runner-owned output required")
    parent = output.parent
    while not parent.exists():
        parent = parent.parent
    require(parent.stat().st_uid == os.getuid() or parent == Path("/private/tmp"))


def template_inputs(root: Path) -> tuple[bytes, dict[str, bytes]]:
    # The npm package link itself is expected pnpm indirection. Resolve that one
    # dependency root, then reject links/special members inside the pinned archive.
    cli = (root / "apps/capture-pwa/node_modules/@capacitor/cli").resolve(strict=True)
    require(json.loads(regular_bytes(cli / "package.json"))["version"] == "8.5.2")
    archive = regular_bytes(cli / "assets/ios-spm-template.tar.gz")
    require(len(archive) == 155545 and digest(archive) == TEMPLATE_SHA, "CLI template drift")
    members: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for item in tar.getmembers():
            name = item.name.removeprefix("./")
            safe_relative(name)
            require(item.isdir() or item.isfile(), "special template member")
            if item.isfile():
                require(name not in members)
                stream = tar.extractfile(item)
                require(stream is not None)
                if stream is None:
                    raise PrototypeError("missing template stream")
                members[name] = stream.read()
    return archive, members


def expected_package() -> str:
    entries = [
        (
            f'        .package(name: "{name}", path: "../../../../../'
            f"node_modules/.pnpm/"
            f"@capacitor+{slug}@{version}_@capacitor+core@8.5.2/node_modules/"
            f'@capacitor/{slug}")'
        )
        for name, slug, version in PLUGINS
    ]
    products = [
        f'                .product(name: "{name}", package: "{name}")' for name, _, _ in PLUGINS
    ]
    return (
        """// swift-tools-version: 5.9
import PackageDescription

// DO NOT MODIFY THIS FILE - managed by Capacitor CLI commands
let package = Package(
    name: "CapApp-SPM",
    platforms: [.iOS(.v15)],
    products: [
        .library(
            name: "CapApp-SPM",
            targets: ["CapApp-SPM"])
    ],
    dependencies: [
        .package(url: "https://github.com/ionic-team/capacitor-swift-pm.git", exact: "8.5.2"),
"""
        + ",\n".join(entries)
        + """
    ],
    targets: [
        .target(
            name: "CapApp-SPM",
            dependencies: [
                .product(name: "Capacitor", package: "capacitor-swift-pm"),
                .product(name: "Cordova", package: "capacitor-swift-pm"),
"""
        + ",\n".join(products)
        + """
            ]
        )
    ]
)
"""
    )


def expected_generated(root: Path, members: dict[str, bytes]) -> dict[str, bytes]:
    del root  # exact deterministic CLI output, not caller-selected substitutions
    result = dict(members)
    pbx = result["App/App.xcodeproj/project.pbxproj"].decode()
    require(pbx.count("com.getcapacitor.App") == 2)
    result["App/App.xcodeproj/project.pbxproj"] = pbx.replace(
        "com.getcapacitor.App", "com.globalsoilintelligence.app"
    ).encode()
    info = result["App/App/Info.plist"].decode()
    info = replace_once(info, "\t<string>My App</string>", "        <string>GSIP Capture</string>")
    result["App/App/Info.plist"] = info.encode()
    result["App/CapApp-SPM/Package.swift"] = expected_package().encode()
    config = {
        "appId": "com.globalsoilintelligence.app",
        "appName": "GSIP Capture",
        "webDir": "dist",
        "loggingBehavior": "none",
        "android": {
            "allowMixedContent": False,
            "includePlugins": [
                "@capacitor/camera",
                "@capacitor/filesystem",
                "@capacitor/local-notifications",
            ],
        },
        "packageClassList": [
            "CAPCameraPlugin",
            "FilesystemPlugin",
            "GeolocationPlugin",
            "LocalNotificationsPlugin",
        ],
    }
    result["App/App/capacitor.config.json"] = (json.dumps(config, indent="\t") + "\n").encode()
    result["capacitor-cordova-ios-plugins/resources/.gitkeep"] = b"\n"
    result["capacitor-cordova-ios-plugins/sources/.gitkeep"] = b"\n"
    return result


def replace_once(text: str, old: str, new: str) -> str:
    require(text.count(old) == 1, "template anchor drift")
    return text.replace(old, new, 1)


def pbx_patch(text: str, host: list[str], tests: list[str]) -> str:
    """Fixed IDs/sections, no generic PBX parser or caller-defined code targets."""

    def ident(index: int) -> str:
        return f"AC2C2A{index:018X}"

    entries: dict[str, list[str]] = {}

    def add(section: str, line: str) -> None:
        entries.setdefault(section, []).append("\t\t" + line)

    for start, files, group in [
        (100, host, "App/GSIPStorageHostPrototype"),
        (200, tests, "GSIPStorageHostPrototypeTests"),
    ]:
        for index, name in enumerate(files):
            ref, build = ident(start + index * 2), ident(start + index * 2 + 1)
            add(
                "PBXFileReference",
                (
                    f"{ref} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType "
                    f'= sourcecode.swift; path = "{group}/{name}"; sourceTree = '
                    f"SOURCE_ROOT; }};"
                ),
            )
            add(
                "PBXBuildFile",
                f"{build} /* {name} in Sources */ = {{isa = PBXBuildFile; fileRef = {ref}; }};",
            )
    host_refs = "\n".join(f"\t\t\t\t{ident(100 + i * 2)}," for i in range(6))
    test_refs = "\n".join(f"\t\t\t\t{ident(200 + i * 2)}," for i in range(6))
    host_builds = "\n".join(f"\t\t\t\t{ident(101 + i * 2)}," for i in range(6))
    test_builds = "\n".join(f"\t\t\t\t{ident(201 + i * 2)}," for i in range(6))
    text = replace_once(
        text,
        "\t\t\t\t958DCC722DB07C7200EA8C5F /* debug.xcconfig */,",
        host_refs + "\n" + test_refs + "\n\t\t\t\t958DCC722DB07C7200EA8C5F /* debug.xcconfig */,",
    )
    text = replace_once(
        text,
        "\t\t\t\t9582B6832FE993A70072D4E8 /* SceneDelegate.swift in Sources */,",
        "\t\t\t\t9582B6832FE993A70072D4E8 /* SceneDelegate.swift in Sources */,\n" + host_builds,
    )
    text = replace_once(
        text,
        "\t\t\t\t4D22ABE92AF431CB00220026 /* CapApp-SPM in Frameworks */,",
        "\t\t\t\t4D22ABE92AF431CB00220026 /* CapApp-SPM in Frameworks */,\n\t\t\t\t"
        + ident(10)
        + ",",
    )
    text = replace_once(
        text,
        "\t\t\t\t4D22ABE82AF431CB00220026 /* CapApp-SPM */,",
        "\t\t\t\t4D22ABE82AF431CB00220026 /* CapApp-SPM */,\n\t\t\t\t" + ident(11) + ",",
    )
    text = replace_once(
        text,
        '\t\t\t\tD4C12C0A2AAA248700AAC8A2 /* XCLocalSwiftPackageReference "CapApp-SPM" */,',
        (
            "\t\t\t\tD4C12C0A2AAA248700AAC8A2 /* XCLocalSwiftPackageReference "
            '"CapApp-SPM" */,\n\t\t\t\t'
        )
        + ident(12)
        + ",",
    )
    text = replace_once(
        text,
        "\t\t\t\t504EC3031FED79650016851F /* App */,",
        "\t\t\t\t504EC3031FED79650016851F /* App */,\n\t\t\t\t" + TEST_TARGET + ",",
    )
    text = replace_once(
        text,
        "\t\t\t\t504EC3041FED79650016851F /* App.app */,",
        "\t\t\t\t504EC3041FED79650016851F /* App.app */,\n\t\t\t\t" + ident(20) + ",",
    )
    require(text.count("PRODUCT_BUNDLE_IDENTIFIER = com.globalsoilintelligence.app;") == 2)
    text = text.replace(
        "PRODUCT_BUNDLE_IDENTIFIER = com.globalsoilintelligence.app;",
        (
            f"PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID};\n"
            f"\t\t\t\tCODE_SIGNING_ALLOWED = NO;\n\t\t\t\tSUPPORTED_PLATFORMS "
            f"= iphonesimulator;"
        ),
    )
    add("PBXBuildFile", f"{ident(10)} = {{isa = PBXBuildFile; productRef = {ident(11)}; }};")
    add("PBXBuildFile", f"{ident(13)} = {{isa = PBXBuildFile; productRef = {ident(11)}; }};")
    add(
        "PBXBuildFile",
        f"{ident(14)} = {{isa = PBXBuildFile; productRef = 4D22ABE82AF431CB00220026; }};",
    )
    add(
        "XCLocalSwiftPackageReference",
        (
            f"{ident(12)} = {{isa = XCLocalSwiftPackageReference; relativePath "
            f'= "../GSIPPrivateStorePrototype"; }};'
        ),
    )
    add(
        "XCSwiftPackageProductDependency",
        (
            f"{ident(11)} = {{isa = XCSwiftPackageProductDependency; package = "
            f"{ident(12)}; productName = GSIPStorageCore; }};"
        ),
    )
    add(
        "PBXFileReference",
        (
            f"{ident(20)} = {{isa = PBXFileReference; explicitFileType = "
            f"wrapper.cfbundle; includeInIndex = 0; path = "
            f"GSIPStorageHostPrototypeTests.xctest; sourceTree = "
            f"BUILT_PRODUCTS_DIR; }};"
        ),
    )
    add(
        "PBXSourcesBuildPhase",
        (
            f"{ident(21)} = {{isa = PBXSourcesBuildPhase; buildActionMask = "
            f"2147483647; files = (\n{test_builds}\n); "
            f"runOnlyForDeploymentPostprocessing = 0; }};"
        ),
    )
    add(
        "PBXFrameworksBuildPhase",
        (
            f"{ident(22)} = {{isa = PBXFrameworksBuildPhase; buildActionMask = "
            f"2147483647; files = ({ident(13)}, {ident(14)},); "
            f"runOnlyForDeploymentPostprocessing = 0; }};"
        ),
    )
    add(
        "PBXResourcesBuildPhase",
        (
            f"{ident(23)} = {{isa = PBXResourcesBuildPhase; buildActionMask = "
            f"2147483647; files = (); runOnlyForDeploymentPostprocessing = 0; "
            f"}};"
        ),
    )
    add(
        "PBXNativeTarget",
        (
            f"{TEST_TARGET} = {{isa = PBXNativeTarget; buildConfigurationList "
            f"= {ident(24)}; buildPhases = ({ident(21)}, {ident(22)}, "
            f"{ident(23)},); buildRules = (); dependencies = ({ident(27)},); "
            f"name = GSIPStorageHostPrototypeTests; packageProductDependencies "
            f"= ({ident(11)}, 4D22ABE82AF431CB00220026,); productName = "
            f"GSIPStorageHostPrototypeTests; productReference = {ident(20)}; "
            f'productType = "com.apple.product-type.bundle.unit-test"; }};'
        ),
    )
    add(
        "XCConfigurationList",
        (
            f"{ident(24)} = {{isa = XCConfigurationList; buildConfigurations = "
            f"({ident(25)}, {ident(26)},); defaultConfigurationIsVisible = 0; "
            f"defaultConfigurationName = Debug; }};"
        ),
    )
    for index, config in [(25, "Debug"), (26, "Release")]:
        settings = (
            f'BUNDLE_LOADER = "$(TEST_HOST)"; CODE_SIGNING_ALLOWED = NO; '
            f"GENERATE_INFOPLIST_FILE = YES; IPHONEOS_DEPLOYMENT_TARGET = 15.0;"
            f" PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID}.tests; PRODUCT_NAME = "
            f'"$(TARGET_NAME)"; SDKROOT = iphonesimulator; SUPPORTED_PLATFORMS '
            f"= iphonesimulator; SWIFT_VERSION = 5.0; ENABLE_TESTABILITY = YES;"
            f' TEST_HOST = "$(BUILT_PRODUCTS_DIR)/App.app/App"; '
            f'LD_RUNPATH_SEARCH_PATHS = ("$(inherited)", "@executable_path/'
            f'Frameworks", "@loader_path/Frameworks",);'
        )
        add(
            "XCBuildConfiguration",
            (
                f"{ident(index)} = {{isa = XCBuildConfiguration; buildSettings = "
                f"{{{settings}}}; name = {config}; }};"
            ),
        )
    # These sections do not exist in the stock template; append their finite objects.
    extra = f"""\n/* Begin PBXContainerItemProxy section */
        {ident(28)} = {{isa = PBXContainerItemProxy; containerPortal = 504EC2FC1FED79650016851F;
        proxyType = 1; remoteGlobalIDString = {APP_TARGET}; remoteInfo = App; }};
/* End PBXContainerItemProxy section */
/* Begin PBXTargetDependency section */
        {ident(27)} = {{isa = PBXTargetDependency; target = {APP_TARGET}; targetProxy =
        {ident(28)}; }};
/* End PBXTargetDependency section */
"""
    for section, objects in entries.items():
        text = replace_once(
            text,
            f"/* End {section} section */",
            "\n".join(objects) + f"\n/* End {section} section */",
        )
    return replace_once(text, "\t};\n\trootObject =", extra + "\t};\n\trootObject =")


def scheme() -> bytes:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="1600" version="1.3">
  <BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries>
    <BuildActionEntry buildForTesting="YES" buildForRunning="NO" buildForProfiling="NO"
        buildForArchiving="NO" buildForAnalyzing="YES"><BuildableReference
        BuildableIdentifier="primary" BlueprintIdentifier="{APP_TARGET}" BuildableName="App.app"
        BlueprintName="App" ReferencedContainer="container:App.xcodeproj"/></BuildActionEntry>
  </BuildActionEntries></BuildAction>
  <TestAction buildConfiguration="Debug"
        selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB"
        selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB"
        shouldUseLaunchSchemeArgsEnv="NO">
    <Testables><TestableReference skipped="NO"><BuildableReference BuildableIdentifier="primary"
        BlueprintIdentifier="{TEST_TARGET}" BuildableName="GSIPStorageHostPrototypeTests.xctest"
        BlueprintName="GSIPStorageHostPrototypeTests"
        ReferencedContainer="container:App.xcodeproj"/></TestableReference></Testables>
  </TestAction>
  <AnalyzeAction buildConfiguration="Debug"/>
</Scheme>
'''.encode()


def prepare(root: Path, fresh: Path, output: Path) -> dict[str, Any]:
    scope = load_scope(root)
    sources = validate_sources(root)
    _, members = template_inputs(root)
    expected = expected_generated(root, members)
    # Everything is validated BEFORE output mkdir, no partial mutation on drift.
    require(not output.exists() and not output.is_symlink(), "fresh destination required")
    for parent in output.parents:
        require(not parent.is_symlink(), "linked destination refused")
    require(fresh != root / "apps/capture-pwa/ios", "ordinary project cannot be modified")
    require(fresh.is_dir() and not fresh.is_symlink())
    validate_output(root, fresh, output)
    actual: dict[str, bytes] = {}
    for p in fresh.rglob("*"):
        if p.is_symlink():
            raise PrototypeError("linked generated input")
        if p.is_dir():
            continue
        relative = p.relative_to(fresh).as_posix()
        if relative.startswith("App/App/public/"):
            continue
        actual[relative] = regular_bytes(p)
    require(
        set(actual) == set(expected) | set(GENERATED_METADATA_SHA256),
        "unknown or missing generated input",
    )
    require(all(actual[k] == expected[k] for k in expected), "generated preimage drift")
    require(
        all(digest(actual[k]) == checksum for k, checksum in GENERATED_METADATA_SHA256.items()),
        "generated metadata drift",
    )
    files = dict(actual)
    host = [Path(x["path"]).name for x in scope["native_files"] if x["kind"] == "host"]
    tests = [Path(x["path"]).name for x in scope["native_files"] if x["kind"] == "host-test"]
    require(len(host) == 6 and len(tests) == 6)
    files["App/App.xcodeproj/project.pbxproj"] = pbx_patch(
        files["App/App.xcodeproj/project.pbxproj"].decode(), host, tests
    ).encode()
    files["App/App/SceneDelegate.swift"] = SCENE.encode()
    storyboard = files["App/App/Base.lproj/Main.storyboard"].decode()
    files["App/App/Base.lproj/Main.storyboard"] = replace_once(
        storyboard,
        'customClass="CAPBridgeViewController" customModule="Capacitor"',
        'customClass="PrototypeHostController" customModule="App"',
    ).encode()
    info = plistlib.loads(files["App/App/Info.plist"])
    info["CFBundleDisplayName"] = "GSIP Synthetic Storage Prototype"
    files["App/App/Info.plist"] = plistlib.dumps(info, sort_keys=False)
    package = files["App/CapApp-SPM/Package.swift"].decode()
    # Rebase only the SAME previously verified local plugin contents, never a new selection.
    for _name, slug, version in PLUGINS:
        old = (
            f"../../../../../node_modules/.pnpm/"
            f"@capacitor+{slug}@{version}_@capacitor+core@8.5.2/node_modules/"
            f"@capacitor/{slug}"
        )
        resolved = (fresh / "App/CapApp-SPM" / old).resolve(strict=True)
        require(json.loads(regular_bytes(resolved / "package.json"))["version"] == version)
        package = replace_once(package, f'path: "{old}"', f'path: "{resolved}"')
    package = replace_once(
        package,
        "\n    dependencies: [\n",
        '\n    dependencies: [\n        .package(path: "../../GSIPPrivateStorePrototype"),\n',
    )
    package = replace_once(
        package,
        '                .product(name: "Capacitor", package: "capacitor-swift-pm"),',
        (
            '                .product(name: "GSIPStorageCore", package: '
            '"GSIPPrivateStorePrototype"),\n                .product(name: '
            '"Capacitor", package: "capacitor-swift-pm"),'
        ),
    )
    files["App/CapApp-SPM/Package.swift"] = package.encode()
    files["App/App.xcodeproj/xcshareddata/xcschemes/GSIPStoragePrototype.xcscheme"] = scheme()
    files["App/App/public/index.html"] = PROBE_HTML
    files["App/App/public/gsip-activation.json"] = ACTIVATION
    files["App/App/capacitor.config.json"] = json.dumps(
        {
            "appId": BUNDLE_ID,
            "appName": "GSIP Synthetic Storage Prototype",
            "webDir": "public",
            "loggingBehavior": "none",
            "ios": {"handleApplicationNotifications": False},
        },
        separators=(",", ":"),
    ).encode()
    edited = {
        k: {"before": digest(actual[k]) if k in actual else None, "after": digest(files[k])}
        for k in files
        if k not in actual or files[k] != actual[k]
    }
    require(set(edited) == set(scope["generated_edits"]), "generated write scope mismatch")
    copies = scope["generated_copies"]
    require(len(set(copies.values())) == 21 and not set(copies.values()) & set(edited))
    for source, target in copies.items():
        safe_relative(target)
        data = regular_bytes(root / source)
        require(digest(data) == sources[source])
        files[target] = data
    output.mkdir(mode=0o700)
    for relative, data in files.items():
        p = output / safe_relative(relative)
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        p.write_bytes(data)
        require(digest(regular_bytes(p)) == digest(data))
    return {
        "scope_sha256": SCOPE_SHA,
        "template_sha256": TEMPLATE_SHA,
        "sources": sources,
        "edited": edited,
        "copied": {target: sources[source] for source, target in copies.items()},
        "full_generated_manifest": {k: digest(v) for k, v in files.items()},
    }


def classify_tests(summary: dict[str, Any]) -> dict[str, Any]:
    passed, failed = summary.get("passedTests"), summary.get("failedTests")
    require(summary.get("result") == "Passed" and type(passed) is int and passed > 0)
    require(type(failed) is int and failed == 0)
    require(summary.get("skippedTests", 0) == 0, "unexpected native test skip")
    return {
        "passed": passed,
        "failed": 0,
        "skipped": summary.get("skippedTests", 0),
        "physical_device_backup_proven": False,
    }


def expected_native_tests(root: Path, kind: str) -> set[str]:
    scope = load_scope(root)
    result: set[str] = set()
    for item in scope["native_files"]:
        if item["kind"] != kind + "-test":
            continue
        text = regular_bytes(root / item["path"]).decode()
        classes = re.findall(r"class (\w+)\s*:\s*XCTestCase", text)
        methods = re.findall(r"func (test\w+)\s*\(", text)
        if not classes:
            require(not methods)
            continue
        require(len(classes) == 1)
        for method in methods:
            name = classes[0] + "/" + method
            require(name not in result)
            result.add(name)
    require(result, "missing authored native tests")
    return result


def audit_test_tree(root: Path, kind: str, tree: dict[str, Any]) -> int:
    expected = expected_native_tests(root, kind)
    found: set[str] = set()

    def visit(nodes: list[dict[str, Any]], depth: int) -> None:
        require(depth <= 12 and len(nodes) < 10000)
        for node in nodes:
            if node.get("nodeType") == "Test Case":
                identifier = node.get("nodeIdentifier", "").removesuffix("()")
                require(identifier in expected and identifier not in found)
                require(node.get("result") == "Passed", "native case did not pass")
                found.add(identifier)
            else:
                visit(node.get("children", []), depth + 1)

    visit(tree.get("testNodes", []), 0)
    require(found == expected, "missing or unexecuted native test")
    return len(found)


def public_receipt(results: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "core",
        "host",
        "ordinary",
        "simulator_runtime",
        "generated_source_manifest_sha256",
        "keychain_api_probe",
    }
    require(set(results) <= allowed, "unknown public receipt field")
    clean: dict[str, Any] = {}
    for name, value in results.items():
        if name in {"core", "host"}:
            require(
                isinstance(value, dict)
                and set(value) <= {"passed", "failed", "skipped", "physical_device_backup_proven"}
            )
            require(type(value.get("passed")) is int and 0 < value["passed"] < 10000)
            require(value.get("failed", 0) == 0 and value.get("skipped", 0) == 0)
            clean[name] = {"passed": value["passed"], "failed": 0, "skipped": 0}
        elif name == "simulator_runtime":
            require(isinstance(value, dict) and set(value) == {"version", "build"})
            require(
                all(
                    isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9.]{1,32}", v)
                    for v in value.values()
                )
            )
            clean[name] = value
        elif name == "generated_source_manifest_sha256":
            require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value))
            clean[name] = value
        elif name == "keychain_api_probe":
            require(value in {"held-group-unverified", "held-api", "api-readback"})
            clean[name] = value
        else:
            fields = {
                "ordinary_bundle_files",
                "ordinary_bundle_manifest_sha256",
                "emitted_code_inputs",
                "ordinary_compile_link_closure_sha256",
                "native_audit_sha256",
                "ordinary_backend_admitted",
            }
            require(isinstance(value, dict) and set(value) == {"debug", "release"})
            for receipt in value.values():
                require(isinstance(receipt, dict) and set(receipt) == fields)
                require(receipt["ordinary_backend_admitted"] is False)
                for key, item in receipt.items():
                    if key.endswith("sha256"):
                        require(isinstance(item, str) and re.fullmatch(r"[0-9a-f]{64}", item))
                    elif key != "ordinary_backend_admitted":
                        require(type(item) is int and 0 < item < 100000)
            clean[name] = value
    return {
        "schema": "gsip-app2c2a-synthetic-receipt-v1",
        "results": clean,
        "production_changed": False,
        "capture_opened": False,
        "ordinary_backend_admitted": False,
        "physical_device_backup_proven": False,
        "power_loss_proven": False,
        "platform_anchor": "held: simulator does not establish physical passcode/restore behavior",
    }


def bind_tree(directory: Path, rows: list[dict[str, Any]]) -> dict[Path, str]:
    require(isinstance(rows, list) and rows, "missing native tree")
    expected: dict[str, str] = {}
    for row in rows:
        require(isinstance(row, dict) and {"path", "sha256"} <= set(row))
        relative, checksum = row["path"], row["sha256"]
        require(isinstance(relative, str) and isinstance(checksum, str))
        safe_relative(relative)
        require(relative not in expected and re.fullmatch(r"[0-9a-f]{64}", checksum))
        expected[relative] = checksum
    actual: set[str] = set()
    for p in directory.rglob("*"):
        if ".git" in p.relative_to(directory).parts:
            continue
        require(not p.is_symlink(), "native tree link refused")
        if not p.is_dir():
            actual.add(p.relative_to(directory).as_posix())
    require(actual == set(expected), "native tree membership drift")
    result: dict[Path, str] = {}
    for relative, checksum in expected.items():
        p = directory / safe_relative(relative)
        require(digest(regular_bytes(p)) == checksum, "native binary/source tree drift")
        result[p.resolve()] = checksum
    return result


def listed_paths(path: Path) -> list[Path]:
    """Xcode emits quoted Swift response rows and literal ld file-list rows."""
    paths: list[Path] = []
    for line in regular_bytes(path).decode().splitlines():
        require(bool(line) and line == line.strip() and "\x00" not in line)
        if line[0] in {"'", '"'}:
            parts = shlex.split(line)
            require(len(parts) == 1, "unresolved emitted list")
            line = parts[0]
        require(Path(line).is_absolute(), "unresolved emitted list")
        resolved = Path(line).resolve()
        regular_bytes(resolved)
        require(resolved not in paths, "duplicate emitted input")
        paths.append(resolved)
    return paths


def link_map_inputs(data: bytes) -> tuple[Path, list[str]]:
    text = data.decode()
    require(text.count("# Path: ") == 1 and text.count("# Object files:\n") == 1)
    require(text.count("# Sections:") == 1 and text.count("# Symbols:") == 1)
    raw = Path(text.split("# Path: ", 1)[1].splitlines()[0])
    require(raw.is_absolute(), "relative link-map output")
    output = raw.resolve()
    rows = text.split("# Object files:\n", 1)[1].split("# Sections:", 1)[0].splitlines()
    require(rows, "missing link-map objects")
    names: list[str] = []
    for index, row in enumerate(rows):
        match = re.fullmatch(r"\[\s*(\d+)\] (.+)", row)
        require(match is not None and int(match[1]) == index, "unknown link-map row")
        if match is None:
            raise PrototypeError("missing link-map row")
        if index == 0:
            require(match[2] == "linker synthesized", "unknown synthesized linker input")
        else:
            names.append(match[2])
    return output, names


def classify_link_input(
    name: str, known: set[Path], developer: Path, sdk: Path, sdk_stubs: dict[str, list[Path]]
) -> dict[str, str]:
    from typing import Literal

    require(name.startswith("/") and "\n" not in name, "unclassified linker input")
    archive = re.fullmatch(r"(.+)\(([^/()]+)\)", name)
    raw = Path(archive[1] if archive else name)
    resolved = raw.resolve()
    admitted = resolved in known
    system = resolved.is_relative_to(developer) and (
        resolved.is_relative_to(sdk)
        or "/Toolchains/" in str(resolved)
        or "/iPhoneSimulator.platform/Developer/usr/lib/" in str(resolved)
    )
    if admitted or system:
        data = regular_bytes(resolved)
        slices = [data]
        if data[:4] in {
            b"\xca\xfe\xba\xbe",
            b"\xbe\xba\xfe\xca",
            b"\xca\xfe\xba\xbf",
            b"\xbf\xba\xfe\xca",
        }:
            order: Literal["big", "little"] = "big" if data[0] == 0xCA else "little"
            wide = data[:4] in {b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca"}
            count = int.from_bytes(data[4:8], order)
            stride = 32 if wide else 20
            require(
                0 < count <= 8 and len(data) >= 8 + count * stride, "invalid universal container"
            )
            slices = []
            for index in range(count):
                start = 8 + index * stride
                offset = int.from_bytes(data[start + 8 : start + (16 if wide else 12)], order)
                size = int.from_bytes(
                    data[start + (16 if wide else 12) : start + (24 if wide else 16)], order
                )
                require(
                    size > 0 and offset >= 8 + count * stride and offset + size <= len(data),
                    "invalid universal slice",
                )
                slices.append(data[offset : offset + size])
        archive_container = all(part.startswith(b"!<arch>\n") for part in slices)
        if archive:
            # Parse every architecture's exact archive member without choosing
            # the Mac host architecture or creating mutable temporary slices.
            require(archive_container, "unknown archive container")
            selected: list[bytes] = []
            for part in slices:
                offset = 8
                matches: list[bytes] = []
                while offset < len(part):
                    header = part[offset : offset + 60]
                    require(len(header) == 60 and header[58:60] == b"`\n", "invalid archive header")
                    size = int(header[48:58].strip())
                    payload = part[offset + 60 : offset + 60 + size]
                    require(len(payload) == size, "truncated archive member")
                    member = header[:16].decode().strip()
                    if member.startswith("#1/"):
                        length = int(member[3:])
                        require(0 < length <= len(payload))
                        member, payload = (
                            payload[:length].rstrip(b"\x00").decode(),
                            payload[length:],
                        )
                    else:
                        member = member.removesuffix("/")
                    if member == archive[2]:
                        matches.append(payload)
                    offset += 60 + size + size % 2
                require(len(matches) == 1 and matches[0], "unresolved or duplicate archive member")
                selected.append(matches[0])
            framed = b"".join(len(part).to_bytes(8, "big") + part for part in selected)
            return {str(resolved): digest(data), name: digest(framed)}
        require(
            admitted
            or resolved.suffix == ".tbd"
            or (resolved.suffix == ".a" and archive_container),
            "unclassified toolchain linker input",
        )
        return {str(resolved): digest(data)}
    # Selected SDK .tbd declarations bind cache/re-export install names. Never
    # read similarly named host libraries or trust an arbitrary system prefix.
    stubs = sdk_stubs.get(name, [])
    require(stubs, "unknown system install name")
    require(all(p.resolve().is_relative_to(sdk) and p.suffix == ".tbd" for p in stubs))
    return {str(p): digest(regular_bytes(p)) for p in stubs}


def audit_ordinary(
    root: Path,
    derived: Path,
    bundle: Path,
    *,
    source: Path | None = None,
    native_path: Path | None = None,
    artifact: Path | None = None,
    build_log: Path | None = None,
) -> dict[str, Any]:
    """Join actual source→driver/map→objects→link/lipo→bundle→ZIP evidence."""
    import zipfile

    from scripts import app_notification_audit as audit

    require(
        all(v is not None for v in (source, native_path, artifact, build_log)),
        "missing ordinary closure",
    )
    source, native_path, artifact, build_log = (
        cast(Path, v) for v in (source, native_path, artifact, build_log)
    )
    derived, bundle = derived.resolve(), bundle.resolve()
    require(
        derived.is_dir() and bundle.is_dir() and bundle.is_relative_to(derived),
        "missing ordinary artifact",
    )
    configuration = bundle.parent.name
    require(
        configuration in {"Debug-iphonesimulator", "Release-iphonesimulator"},
        "unknown ordinary configuration",
    )

    def configuration_outputs(pattern: str) -> set[Path]:
        return {
            p.resolve()
            for p in derived.rglob(pattern)
            if configuration in p.parts or p.parent == derived
        }

    scope = load_scope(root)
    native_hashes = set(validate_native(root, scope).values())
    for path, expected in scope["source_bindings"].items():
        require(digest(regular_bytes(source / path)) == expected, "ordinary frozen source drift")
    native = json.loads(regular_bytes(native_path))
    # The receipt cannot choose the expected source identity itself.
    head = subprocess.run(  # noqa: S603 - fixed read-only source identity
        ["/usr/bin/git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, check=False
    )  # noqa: S603
    require(head.returncode == 0 and re.fullmatch(rb"[0-9a-f]{40}\n", head.stdout))
    expected_commit = head.stdout.decode().strip()
    copied_head = subprocess.run(  # noqa: S603 - fixed read-only copy identity
        ["/usr/bin/git", "-C", str(source), "rev-parse", "HEAD"],
        capture_output=True,
        check=False,
    )  # noqa: S603
    require(
        copied_head.returncode == 0 and copied_head.stdout == head.stdout,
        "ordinary copy source identity mismatch",
    )
    locks = {
        p.relative_to(source).as_posix(): digest(regular_bytes(p))
        for p in (source / "apps/capture-pwa/ios").rglob("Package.resolved")
    }
    locks.update({p: digest(regular_bytes(source / p)) for p in ("pnpm-lock.yaml", "uv.lock")})
    audit.validate_native(
        native,
        {
            "platform": "ios",
            "source_commit": expected_commit,
            "artifact_sha256": digest(regular_bytes(artifact)),
            "lockfile_sha256": locks,
        },
    )
    require(native["source_inputs"] == audit.source_inputs(source))
    require(native["npm_sources"] == audit.npm_evidence(source, audit.NPM_PACKAGES))
    allowed_sources: dict[Path, str] = {}
    for item in native["npm_sources"]:
        package = (source / "apps/capture-pwa/node_modules" / item["name"]).resolve()
        for p in package.rglob("*"):
            if any(
                part in {"build", ".gradle", "node_modules"}
                for part in p.relative_to(package).parts
            ):
                continue
            if p.is_file():
                allowed_sources[p.resolve()] = digest(regular_bytes(p))
    for item in native["spm"]["remote_source_packages"]:
        allowed_sources.update(
            bind_tree(
                derived / "SourcePackages/checkouts" / item["identity"],
                item["actual_source_tree"]["files"],
            )
        )
    binary_files: dict[Path, str] = {}
    for item in native["spm"]["binary_inputs"]:
        directory = (
            derived
            / f"SourcePackages/artifacts/capacitor-swift-pm/{item['name']}"
            / f"{item['name']}.xcframework"
        )
        binary_files.update(bind_tree(directory, item["actual_resolved_tree"]["files"]))
    _, template = template_inputs(root)
    for relative in (
        "App/App/AppDelegate.swift",
        "App/App/SceneDelegate.swift",
        "App/CapApp-SPM/Sources/CapApp-SPM/CapApp-SPM.swift",
    ):
        p = source / "apps/capture-pwa/ios" / relative
        require(regular_bytes(p) == template[relative], "ordinary native source drift")
        allowed_sources[p.resolve()] = digest(regular_bytes(p))
    log = regular_bytes(build_log).decode()
    require("** BUILD SUCCEEDED **" in log)
    developer_match = re.search(
        r"(/Applications/[^\n]*?\.app/Contents/Developer)/Toolchains/[^\s]+/usr/bin/clang ", log
    )
    require(developer_match is not None, "unknown compiler identity")
    if developer_match is None:
        raise PrototypeError("missing developer identity")
    developer = Path(developer_match[1]).resolve()
    sdk_values = set(re.findall(r"(?:-isysroot|-sdk) (\S+\.sdk)", log))
    require(len(sdk_values) == 1)
    sdk = Path(next(iter(sdk_values))).resolve()
    require(sdk.is_relative_to(developer) and "iPhoneSimulator" in str(sdk))
    sdk_stubs: dict[str, list[Path]] = {}
    for candidate in sdk.rglob("*.tbd"):
        p = candidate.resolve()
        require(p.is_relative_to(sdk), "SDK link escaped selected SDK")
        for name in set(
            re.findall(rb"/(?:usr/lib|System/Library)/[^\s'\",\]\[{}]+", regular_bytes(p))
        ):
            sdk_stubs.setdefault(name.decode(), []).append(p)
    closure: dict[str, str] = {
        str(build_log): digest(regular_bytes(build_log)),
        "source_commit": expected_commit,
    }
    compiled: set[Path] = set()
    source_files: set[Path] = set()
    compiler_metadata: set[Path] = set()
    used_maps: set[Path] = set()
    used_swift_lists: set[Path] = set()
    # These are actual Xcode-27 generated sources from the frozen resource
    # inputs. A toolchain generation change holds for review instead of trusting
    # any arbitrary source with an Xcode-like filename.
    generated_hashes = {
        "GeneratedAssetSymbols.swift": {
            "91bcf87722aa68b70dc97ae7ae2b9ef50cf7d934ad02324e5b4ae64924c01e35",
            "caac48dace23df6452e335eec51795419a5c0304989153901ab67608ec73ed61",
        },
        "resource_bundle_accessor.swift": {
            "cb1d5f46f892ae559578f333df45815ca04926e5c8e26820fd80db7e14399d21"
        },
    }
    for line in log.splitlines():
        stripped = line.strip()
        if not stripped.startswith("builtin-SwiftDriver -- "):
            continue
        tokens = shlex.split(stripped)[2:]
        require(
            tokens
            and Path(tokens[0]).resolve().is_relative_to(developer)
            and Path(tokens[0]).name == "swiftc"
        )
        require(
            tokens.count("-output-file-map") == 1 and "-c" in tokens, "unknown Swift compiler role"
        )
        file_map = Path(tokens[tokens.index("-output-file-map") + 1]).resolve()
        require(
            file_map.is_relative_to(derived) and file_map not in used_maps, "unbound compiler map"
        )
        responses = [t[1:] for t in tokens if t.startswith("@")]
        require(
            len(responses) == 1 and responses[0].endswith(".SwiftFileList"),
            "unknown Swift response input",
        )
        listing = Path(responses[0]).resolve()
        require(listing.is_relative_to(derived) and listing not in used_swift_lists)
        selected = set(listed_paths(listing))
        require(selected, "empty compiler input")
        rows = json.loads(regular_bytes(file_map))
        require(isinstance(rows, dict), "compiler output map type")
        normalized = [Path(name).resolve() for name in rows if name]
        require(
            all(Path(name).is_absolute() for name in rows if name)
            and len(normalized) == len(set(normalized))
            and set(normalized) == selected,
            "compiler input/map mismatch",
        )
        for p in selected:
            checksum = digest(regular_bytes(p))
            if p in allowed_sources:
                require(checksum == allowed_sources[p], "compiled source drift")
            else:
                require(
                    p.is_relative_to(derived) and checksum in generated_hashes.get(p.name, set()),
                    "unclassified generated source",
                )
                if p.name == "GeneratedAssetSymbols.swift":
                    require(
                        any(
                            "/usr/bin/actool " in entry
                            and "--generate-swift-asset-symbols " in entry
                            and any(
                                str(p) == str(Path(t).resolve())
                                for t in shlex.split(entry)
                                if t.endswith(".swift")
                            )
                            for entry in log.splitlines()
                        ),
                        "unbound asset generator",
                    )
                else:
                    require(
                        any(
                            entry.strip().startswith("write-file ")
                            and Path(entry.strip()[len("write-file ") :]).resolve() == p
                            for entry in log.splitlines()
                        ),
                        "unbound resource generator",
                    )
            require(checksum not in native_hashes, "prototype source in ordinary build")
            source_files.add(p)
            closure[str(p)] = checksum
        for option in ("-emit-module-path", "-emit-objc-header-path"):
            if option in tokens:
                require(tokens.count(option) == 1)
                emitted = Path(tokens[tokens.index(option) + 1]).resolve()
                require(emitted.is_relative_to(derived), "compiler metadata outside build")
                compiler_metadata.add(emitted)
                closure[str(emitted)] = digest(regular_bytes(emitted))
        objects: set[Path] = set()
        for outputs in rows.values():
            require(isinstance(outputs, dict))
            if "object" in outputs:
                obj = Path(outputs["object"]).resolve()
                require(obj.is_relative_to(derived) and obj.suffix == ".o")
                regular_bytes(obj)
                objects.add(obj)
                closure[str(obj)] = digest(regular_bytes(obj))
        require(objects, "compiler emitted no objects")
        compiled.update(objects)
        used_maps.add(file_map)
        used_swift_lists.add(listing)
        closure[str(file_map)] = digest(regular_bytes(file_map))
        closure[str(listing)] = digest(regular_bytes(listing))
        closure["compiler-command:" + digest(stripped.encode())] = digest(stripped.encode())
    require(
        used_maps and used_maps == configuration_outputs("*OutputFileMap.json"),
        "unused or missing compiler map",
    )
    require(
        used_swift_lists == configuration_outputs("*.SwiftFileList"),
        "unused or missing compiler input list",
    )
    known = set(compiled) | set(binary_files)
    binary_hashes = set(binary_files.values())
    # Xcode's ProcessXCFramework outputs preserve the selected audited bytes.
    for p in (derived / "Build/Products").rglob("*"):
        if (
            p.is_file()
            and not p.is_symlink()
            and ".framework" in str(p)
            and digest(regular_bytes(p)) in binary_hashes
        ):
            known.add(p.resolve())
    commands: list[tuple[Path, list[str], str, Path | None]] = []
    used_link_lists: set[Path] = set()
    command_maps: dict[Path, set[Path]] = {}
    metadata: set[Path] = set()
    for line in log.splitlines():
        stripped = line.strip()
        if not stripped.startswith(str(developer)):
            continue
        tokens = shlex.split(stripped)
        tool = Path(tokens[0])
        if tool.name not in {"clang", "lipo", "swiftc"} or not tool.resolve().is_relative_to(
            developer
        ):
            continue
        if tool.name == "swiftc" and "-emit-library" not in tokens:
            continue
        require("-c" not in tokens, "unclassified C/Objective-C compilation")
        if "-o" in tokens:
            require(tokens.count("-o") == 1)
            output = Path(tokens[tokens.index("-o") + 1]).resolve()
        elif "-output" in tokens:
            require(tokens.count("-output") == 1)
            output = Path(tokens[tokens.index("-output") + 1]).resolve()
        else:
            continue
        require(output.is_relative_to(derived), "link output outside owned build")
        # Flatten argument wrappers, preserving linker option/value order.
        flat = [t for t in tokens[1:] if t not in {"-Xlinker", "-Xclang-linker"}]
        inputs: list[str] = []
        frameworks: list[str] = []
        libraries: list[str] = []
        fdirs: list[Path] = []
        ldirs: list[Path] = []
        map_path: Path | None = None
        i = 0
        value_options = {
            "-o",
            "-output",
            "-target",
            "-isysroot",
            "-sdk",
            "-install_name",
            "-rpath",
            "-object_path_lto",
            "-dependency_info",
            "-objc_abi_version",
            "-e",
            "-compatibility_version",
            "-current_version",
            "-swift-version",
        }
        while i < len(flat):
            word = flat[i]
            if word in {"-framework", "-weak_framework", "-reexport_framework"}:
                require(i + 1 < len(flat) and re.fullmatch(r"[A-Za-z0-9_]+", flat[i + 1]))
                frameworks.append(flat[i + 1])
                i += 2
                continue
            if word == "-add_ast_path":
                require(i + 1 < len(flat))
                ast = Path(flat[i + 1]).resolve()
                require(ast in compiler_metadata, "unbound linker AST input")
                closure[str(ast)] = digest(regular_bytes(ast))
                i += 2
                continue
            if word == "-alias":
                require(
                    flat[i + 1 : i + 3] == ["_main", "___debug_main_executable_dylib_entry_point"],
                    "unknown linker alias",
                )
                i += 3
                continue
            if word == "-map":
                require(i + 1 < len(flat) and map_path is None)
                map_path = Path(flat[i + 1]).resolve()
                require(map_path.is_relative_to(derived))
                command_maps.setdefault(map_path, set()).add(output)
                i += 2
                continue
            if word == "-sectcreate":
                require(
                    i + 3 < len(flat)
                    and flat[i + 1] == "__TEXT"
                    and flat[i + 2] in {"__debug_dylib", "__debug_instlnm"},
                    "unknown synthesized section",
                )
                p = Path(flat[i + 3]).resolve()
                require(
                    p.is_relative_to(derived)
                    and p.name.startswith("App-DebugDylib")
                    and p.name.endswith(("-normal-arm64.txt", "-normal-x86_64.txt"))
                )
                expected = (
                    b"App.debug.dylib"
                    if flat[i + 2] == "__debug_dylib"
                    else b"@rpath/App.debug.dylib"
                )
                require(regular_bytes(p).strip() == expected, "synthesized debug metadata drift")
                metadata.add(p)
                closure[str(p)] = digest(regular_bytes(p))
                i += 4
                continue
            if word == "-filelist" or word.startswith("@"):
                value = flat[i + 1] if word == "-filelist" else word[1:]
                listing = Path(value).resolve()
                require(listing.is_relative_to(derived), "link list outside owned build")
                inputs.extend(str(p) for p in listed_paths(listing))
                used_link_lists.add(listing)
                closure[str(listing)] = digest(regular_bytes(listing))
                i += 2 if word == "-filelist" else 1
                continue
            if word in value_options:
                require(i + 1 < len(flat))
                i += 2
                continue
            if word in {"-F", "-Fsystem", "-iframework", "-L"}:
                require(i + 1 < len(flat))
                (ldirs if word == "-L" else fdirs).append(Path(flat[i + 1]).resolve())
                i += 2
                continue
            if word.startswith(("-F", "-L")) and len(word) > 2:
                (ldirs if word.startswith("-L") else fdirs).append(Path(word[2:]).resolve())
                i += 1
                continue
            if word.startswith("-l") and word not in {"-link-objc-runtime"}:
                require(re.fullmatch(r"-l[A-Za-z0-9_+.-]+", word))
                libraries.append(word[2:])
                i += 1
                continue
            if word.startswith("/"):
                inputs.append(str(Path(word).resolve()))
            elif not word.startswith("-"):
                require(False, "unclassified linker argument")
            elif word.startswith("-Wl,") or word in {
                "-force_load",
                "-load_hidden",
                "-reexport_library",
                "-weak_library",
                "-bundle_loader",
                "-add_empty_section",
            }:
                require(False, "unsupported linker argument")
            i += 1
        for name in frameworks:
            candidates = [
                q
                for d in [*fdirs, sdk / "System/Library/Frameworks"]
                for q in (d / f"{name}.framework" / name, d / f"{name}.framework/{name}.tbd")
                if q.is_file()
            ]
            require(candidates, "unresolved framework selection")
            inputs.append(str(candidates[0].resolve()))
        for name in libraries:
            candidates = [
                d / f"lib{name}{suffix}"
                for d in [
                    *ldirs,
                    sdk / "usr/lib",
                    developer / "Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/17/lib/darwin",
                ]
                for suffix in (".tbd", ".a", ".dylib")
                if (d / f"lib{name}{suffix}").is_file()
            ]
            require(candidates, "unresolved library selection")
            inputs.append(str(candidates[0].resolve()))
        require(inputs or output.name == "__preview.dylib", "empty unexplained link output")
        commands.append((output, inputs, stripped, map_path))
    require(commands, "missing actual linker commands")
    pending = list(commands)
    while pending:
        progress = False
        for output, inputs, command, map_path in pending[:]:
            # The only additional leaves are exact audited framework copies or
            # selected SDK/toolchain inputs classified below.
            unresolved = [Path(re.sub(r"\([^()]*\)$", "", v)).resolve() for v in inputs]
            if not all(p in known or p.is_relative_to(developer) for p in unresolved):
                continue
            regular_bytes(output)
            for name in inputs:
                closure.update(classify_link_input(name, known, developer, sdk, sdk_stubs))
            known.add(output)
            closure[str(output)] = digest(regular_bytes(output))
            closure["link-command:" + digest(command.encode())] = digest(command.encode())
            pending.remove((output, inputs, command, map_path))
            progress = True
        require(progress, "unclassified object or linker dependency")
    require(
        configuration_outputs("*.LinkFileList") <= used_link_lists,
        "unused linker input list",
    )
    maps = configuration_outputs("*LinkMap*.txt")
    require(maps and maps == set(command_maps), "unbound link map")
    for p in maps:
        output, names = link_map_inputs(regular_bytes(p))
        require(output in command_maps[p] and output in known, "unknown link-map output")
        for name in names:
            if Path(name).resolve() in metadata:
                closure[name] = digest(regular_bytes(Path(name).resolve()))
            else:
                closure.update(classify_link_input(name, known, developer, sdk, sdk_stubs))
        closure[str(p)] = digest(regular_bytes(p))
    code_hashes = {digest(regular_bytes(p)) for p in known}
    macho_magic = {
        b"\xce\xfa\xed\xfe",
        b"\xcf\xfa\xed\xfe",
        b"\xfe\xed\xfa\xce",
        b"\xfe\xed\xfa\xcf",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf",
        b"\xbf\xba\xfe\xca",
    }
    canary_substrings: set[bytes] = set()
    canary_hashes: set[str] = set()
    for item in scope["native_files"]:
        native_data = regular_bytes(root / item["path"])
        for literal in re.findall(rb'Data\("([^"\\]*)"\.utf8\)', native_data):
            canary_hashes.add(digest(literal))
            if len(literal) >= 16:
                canary_substrings.add(literal)
        for raw in re.findall(rb"Data\(\[([0-9, ]+)\]\)", native_data):
            values = [int(v.strip()) for v in raw.split(b",")]
            require(all(0 <= v <= 255 for v in values))
            canary_hashes.add(digest(bytes(values)))
    entries: dict[str, str] = {}
    for p in bundle.rglob("*"):
        require(not p.is_symlink(), "unclassified ordinary bundle link")
        if p.is_dir():
            continue
        data = regular_bytes(p)
        checksum = digest(data)
        require(checksum not in native_hashes and data != PROBE_HTML)
        require(
            checksum not in canary_hashes and not any(v in data for v in canary_substrings),
            "native canary in ordinary resource",
        )
        require(
            b"GSIPPrivateStorePrototype" not in data and b"GSIPStorageHostPrototype" not in data
        )
        require("GSIPStorage" not in p.name and ".xctest" not in str(p))
        if data[:4] in macho_magic or data.startswith(b"!<arch>\n"):
            require(checksum in code_hashes, "ordinary bundle code outside audited link closure")
        entries[p.relative_to(bundle).as_posix()] = checksum
    require(entries and "Info.plist" in entries)
    info = plistlib.loads(regular_bytes(bundle / "Info.plist"))
    require(info["CFBundleIdentifier"] == "com.globalsoilintelligence.app")
    require(bundle / info["CFBundleExecutable"] in known, "unbound ordinary executable")
    require(
        json.loads(regular_bytes(bundle / "public/gsip-activation.json"))
        == {"capture_live": False, "library_intake_live": False}
    )
    # An artifact hash alone does not join a ZIP to this inspected directory.
    # Require a clean archive containing exactly the same regular file bytes.
    zipped: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(regular_bytes(artifact))) as archive:
        all_names: set[str] = set()
        for member in archive.infolist():
            name = member.filename
            require(
                name not in all_names and "\\" not in name and "\x00" not in name,
                "ambiguous ZIP entry",
            )
            all_names.add(name)
            archive_relative = safe_relative(name.removesuffix("/"))
            require(archive_relative.parts[0] == bundle.name, "unexpected ZIP root")
            mode = member.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if member.is_dir():
                require(kind in {0, stat.S_IFDIR}, "special ZIP directory")
                require((bundle.parent / str(archive_relative)).is_dir(), "unknown ZIP directory")
                continue
            require(kind in {0, stat.S_IFREG}, "special ZIP file")
            key = PurePosixPath(*archive_relative.parts[1:]).as_posix()
            require(
                key in entries and member.file_size == (bundle / key).stat().st_size,
                "unexpected ZIP member",
            )
            zipped[key] = digest(archive.read(member))
    require(zipped == entries, "ordinary artifact/bundle mismatch")
    closure[str(artifact)] = digest(regular_bytes(artifact))
    return {
        "ordinary_bundle_files": len(entries),
        "ordinary_bundle_manifest_sha256": digest(json.dumps(entries, sort_keys=True).encode()),
        "emitted_code_inputs": len(compiled) + len(source_files),
        "ordinary_compile_link_closure_sha256": digest(
            json.dumps(closure, sort_keys=True).encode()
        ),
        "native_audit_sha256": digest(regular_bytes(native_path)),
        "ordinary_backend_admitted": False,
    }


# Only these fixed labels may leave the private tool logs.
PRIVATE_STEP_LABELS = {
    "runtimes.json": "simulator-inventory",
    "toolchain.log": "audited-toolchain",
    "created-simulator.txt": "simulator-create",
    "boot.log": "simulator-boot",
    "bootstatus.log": "simulator-ready",
    "shutdown.log": "simulator-shutdown",
    "delete.log": "simulator-delete",
}
for _kind in ("core", "host"):
    for _suffix in ("build.log", "test.log", "summary.json", "tests.json"):
        PRIVATE_STEP_LABELS[f"{_kind}-{_suffix}"] = f"{_kind}-{_suffix.split('.')[0]}"
for _configuration in ("debug", "release"):
    for _suffix in ("build", "zip", "native-audit", "app_build.py", "app_permissions.py"):
        PRIVATE_STEP_LABELS[f"ordinary-{_configuration}-{_suffix}.log"] = (
            f"ordinary-{_configuration}-{_suffix.removesuffix('.py')}"
        )
for _helper in ("app_build.py", "app_permissions.py"):
    PRIVATE_STEP_LABELS[f"ordinary-apply-{_helper}.log"] = (
        f"ordinary-apply-{_helper.removesuffix('.py')}"
    )


def private_failure_labels(log: Path, expected_tests: set[str]) -> tuple[list[str], list[str]]:
    """Return only fixed categories and already-authored test identities, never excerpts."""
    try:
        if log.stat().st_size > 16 * 1024 * 1024:
            return ["diagnostic-size-held"], []
        text = regular_bytes(log).decode("utf-8", errors="replace")
    except (OSError, PrototypeError):
        return ["diagnostic-unavailable"], []
    categories = {
        "error: no such module": "missing-module",
        "Could not resolve package dependencies": "package-resolution",
        "Missing package product": "missing-package-product",
        "linker command failed": "linker-failure",
        "Failed to load the test bundle": "test-bundle-load",
        "Failed to establish communication": "test-runner-communication",
        "Failed to launch": "test-runner-launch",
        "Unable to boot": "simulator-boot-failure",
        "TEST EXECUTE FAILED": "native-test-failure",
        "TEST BUILD FAILED": "native-build-failure",
        "** BUILD FAILED **": "ordinary-build-failure",
        "Testing failed": "native-test-failure",
        "Timed out waiting": "runner-reported-timeout",
        "code signature": "code-signature-diagnostic",
        "dyld": "dynamic-loader-diagnostic",
        "Test Suite '": "xctest-suite-started",
    }
    found_labels = {label for token, label in categories.items() if token in text}
    # Match fixed enum spellings only; never return an NSError description or value.
    for hold in ("boundary", "unavailable", "unsupportedPlatform", "invalidRequest", "corrupt"):
        if re.search(r'(?:caught error:|threw error:?) "' + hold + r'"', text):
            found_labels.add("storage-hold-" + hold)
    for code, label in {
        4: "cocoa-no-such-file",
        260: "cocoa-no-such-file",
        257: "cocoa-read-permission",
        513: "cocoa-write-permission",
    }.items():
        if re.search(r"Error Domain=NSCocoaErrorDomain Code=" + str(code) + r"\b", text):
            found_labels.add(label)
    found_categories = sorted(found_labels)
    failures: set[str] = set()
    for class_name, method in re.findall(
        r"(?m)^Test Case '-\[(?:[A-Za-z0-9_]+\.)?([A-Za-z0-9_]+) "
        r"([A-Za-z0-9_]+)\]' failed",
        text,
    ):
        identity = class_name + "/" + method
        if identity in expected_tests and re.fullmatch(
            r"[A-Za-z0-9_]{1,128}/test\w{1,128}", identity
        ):
            failures.add(identity)
    return found_categories or ["unclassified"], sorted(failures)[:16]


def private_test_progress(log: Path, expected_tests: set[str]) -> dict[str, Any]:
    """Observe only allowlisted case status; this never certifies test acceptance."""
    unavailable = {
        "available": False,
        "observed_started": 0,
        "observed_passed": 0,
        "observed_failed": 0,
        "unfinished_test_identities": [],
    }
    try:
        if log.stat().st_size > 16 * 1024 * 1024:
            return unavailable
        text = regular_bytes(log).decode("utf-8", errors="replace")
    except (OSError, PrototypeError):
        return unavailable
    statuses: dict[str, set[str]] = {"started": set(), "passed": set(), "failed": set()}
    latest: dict[str, str] = {}
    for class_name, method, status in re.findall(
        r"(?m)^Test Case '-\[(?:[A-Za-z0-9_]+\.)?([A-Za-z0-9_]+) "
        r"([A-Za-z0-9_]+)\]' (started|passed|failed)\b",
        text,
    ):
        identity = class_name + "/" + method
        if identity in expected_tests and re.fullmatch(
            r"[A-Za-z0-9_]{1,128}/test\w{1,128}", identity
        ):
            statuses[status].add(identity)
            latest[identity] = status
    unfinished = {identity for identity, status in latest.items() if status == "started"}
    return {
        "available": True,
        "observed_started": len(statuses["started"]),
        "observed_passed": len(statuses["passed"]),
        "observed_failed": len(statuses["failed"]),
        "unfinished_test_identities": sorted(unfinished)[:16],
    }


def run_private(
    args: list[str],
    cwd: Path,
    log: Path,
    *,
    env: dict[str, str] | None = None,
    expected_tests: set[str] | None = None,
) -> None:
    """Raw tool output remains private; emit fixed stage/category labels only."""
    stage = PRIVATE_STEP_LABELS.get(log.name, "private-tool")
    print("APP-2C2A step: " + stage, flush=True)
    with log.open("wb") as stream:
        try:
            result = subprocess.run(  # noqa: S603 - fixed internal native/build commands, no shell
                args,
                cwd=cwd,
                env=env,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=300 if "test-without-building" in args else 1800,
            )
        except subprocess.TimeoutExpired as error:
            categories, identities = private_failure_labels(log, expected_tests or set())
            diagnostic: dict[str, Any] = {
                "stage": stage,
                "categories": sorted(set(categories) | {"timeout"}),
                "test_identities": identities,
            }
            if expected_tests:
                diagnostic["progress"] = private_test_progress(log, expected_tests)
            print("APP-2C2A bounded failure: " + json.dumps(diagnostic, sort_keys=True), flush=True)
            raise PrototypeError(
                "owned native tool timed out at " + stage + "; evidence retained"
            ) from error
    if result.returncode != 0:
        categories, identities = private_failure_labels(log, expected_tests or set())
        diagnostic = {
            "stage": stage,
            "exit": result.returncode,
            "categories": categories,
            "test_identities": identities,
        }
        if expected_tests:
            diagnostic["progress"] = private_test_progress(log, expected_tests)
        print("APP-2C2A bounded failure: " + json.dumps(diagnostic, sort_keys=True), flush=True)
        raise PrototypeError("native tool step failed at " + stage + "; private evidence retained")


def read_json_tool(args: list[str], cwd: Path, log: Path) -> dict[str, Any]:
    run_private(args, cwd, log)
    value: dict[str, Any] = json.loads(regular_bytes(log))
    return value


def bind_test_environment(derived: Path, expected_host: bool) -> Path:
    plans = list((derived / "Build/Products").glob("*.xctestrun"))
    require(len(plans) == 1, "unknown test plan layout")
    plan = plans[0]
    content = plistlib.loads(regular_bytes(plan))
    targets: list[dict[str, Any]] = []
    if "TestConfigurations" in content:
        for config in content["TestConfigurations"]:
            targets.extend(config.get("TestTargets", []))
    else:
        targets = [v for k, v in content.items() if not k.startswith("__") and isinstance(v, dict)]
    require(len(targets) == 1, "unknown test target")
    target = targets[0]
    host = str(target.get("TestHostPath", ""))
    host_path = Path(host.replace("__TESTROOT__", str(plan.parent)))
    if expected_host:
        require(host_path.is_dir() and host_path.suffix == ".app", "unknown fresh host")
        info = plistlib.loads(regular_bytes(host_path / "Info.plist"))
        identifier = info.get("CFBundleIdentifier", "")
        require(identifier == BUNDLE_ID)
    else:
        require(
            host == "__PLATFORMS__/iPhoneSimulator.platform/Developer/Library/Xcode/Agents/xctest",
            "unknown package test agent",
        )
        bundle = str(target.get("TestBundlePath", ""))
        bundle_path = Path(bundle.replace("__TESTROOT__", str(plan.parent)))
        require(bundle_path.is_relative_to(plan.parent) and bundle_path.suffix == ".xctest")
        info = plistlib.loads(regular_bytes(bundle_path / "Info.plist"))
        identifier = info.get("CFBundleIdentifier", "")
        require(isinstance(identifier, str) and "GSIPStorageCore" in identifier)
    environment = target.setdefault("EnvironmentVariables", {})
    environment["GSIP_PROTOTYPE_EXPECTED_BUNDLE_ID"] = identifier
    if not expected_host:
        environment["GSIP_PROTOTYPE_HOSTLESS_CORE_TESTS"] = "1"
    plan.write_bytes(plistlib.dumps(content))
    return plan


def require_audited_xcode(output: bytes) -> None:
    require(
        output.splitlines() == [b"Xcode 27.0", b"Build version 27A266a"],
        "audited Xcode 27.0 build 27A266a required",
    )


def execute(root: Path, fresh: Path, run_root: Path) -> dict[str, Any]:
    require(not run_root.exists() and not run_root.is_symlink(), "new run root required")
    require(os.uname().sysname == "Darwin", "iOS simulator toolchain required")
    validate_output(root, fresh, run_root)
    run_root.mkdir(mode=0o700)
    harness = run_root / "harness"
    receipt = prepare(root, fresh, harness)
    evidence = run_root / "private-evidence"
    evidence.mkdir(mode=0o700)
    run_private(["xcodebuild", "-version"], root, evidence / "toolchain.log")
    require_audited_xcode(regular_bytes(evidence / "toolchain.log"))
    (evidence / "generated.json").write_text(json.dumps(receipt, sort_keys=True))
    runtimes = read_json_tool(
        ["xcrun", "simctl", "list", "runtimes", "-j"], root, evidence / "runtimes.json"
    )
    available = [
        r
        for r in runtimes.get("runtimes", [])
        if r.get("isAvailable")
        and r.get("identifier", "").startswith("com.apple.CoreSimulator.SimRuntime.iOS-")
    ]
    require(available, "no supported iOS simulator")
    runtime = sorted(available, key=lambda r: tuple(int(x) for x in r["version"].split(".")))[-1]
    runtime_public = public_receipt(
        {"simulator_runtime": {"version": runtime["version"], "build": runtime["buildversion"]}}
    )["results"]["simulator_runtime"]
    print("APP-2C2A runtime: " + json.dumps(runtime_public, sort_keys=True), flush=True)
    # Only this new simulator may be booted, tested, shut down or deleted.
    run_private(
        [
            "xcrun",
            "simctl",
            "create",
            "GSIP-APP2C2A-owned-synthetic",
            "com.apple.CoreSimulator.SimDeviceType.iPhone-16",
            runtime["identifier"],
        ],
        root,
        evidence / "created-simulator.txt",
    )
    udid = regular_bytes(evidence / "created-simulator.txt").decode().strip()
    require(re.fullmatch(r"[A-Fa-f0-9-]{36}", udid), "unknown owned simulator identity")
    results: dict[str, Any] = {}
    try:
        run_private(["xcrun", "simctl", "boot", udid], root, evidence / "boot.log")
        run_private(
            ["xcrun", "simctl", "bootstatus", udid, "-b"], root, evidence / "bootstatus.log"
        )
        dest = f"platform=iOS Simulator,id={udid}"
        for name, cwd, selection in [
            (
                "core",
                harness / "GSIPPrivateStorePrototype",
                ["-scheme", "GSIPPrivateStorePrototype"],
            ),
            (
                "host",
                harness / "App",
                ["-project", "App.xcodeproj", "-scheme", "GSIPStoragePrototype"],
            ),
        ]:
            derived = run_root / (name + "-derived")
            common = [
                "xcodebuild",
                *selection,
                "-configuration",
                "Debug",
                "-sdk",
                "iphonesimulator",
                "-destination",
                dest,
                "-derivedDataPath",
                str(derived),
                "CODE_SIGNING_ALLOWED=NO",
            ]
            run_private([*common, "build-for-testing"], cwd, evidence / (name + "-build.log"))
            plan = bind_test_environment(derived, name == "host")
            result_bundle = evidence / (name + ".xcresult")
            run_private(
                [
                    "xcodebuild",
                    "test-without-building",
                    "-xctestrun",
                    str(plan),
                    "-destination",
                    dest,
                    "-resultBundlePath",
                    str(result_bundle),
                    "-parallel-testing-enabled",
                    "NO",
                    "CODE_SIGNING_ALLOWED=NO",
                ],
                cwd,
                evidence / (name + "-test.log"),
                expected_tests=expected_native_tests(root, name),
            )
            summary = read_json_tool(
                [
                    "xcrun",
                    "xcresulttool",
                    "get",
                    "test-results",
                    "summary",
                    "--path",
                    str(result_bundle),
                ],
                root,
                evidence / (name + "-summary.json"),
            )
            tree = read_json_tool(
                [
                    "xcrun",
                    "xcresulttool",
                    "get",
                    "test-results",
                    "tests",
                    "--path",
                    str(result_bundle),
                ],
                root,
                evidence / (name + "-tests.json"),
            )
            require(audit_test_tree(root, name, tree) == summary.get("passedTests"))
            results[name] = classify_tests(summary)
            if name == "core":
                markers = re.findall(
                    r"^GSIP_SIMULATOR_ANCHOR=(held-group-unverified|held-api|api-readback)$",
                    regular_bytes(evidence / "core-test.log").decode(),
                    re.MULTILINE,
                )
                require(len(markers) == 1, "missing or ambiguous anchor probe result")
                results["keychain_api_probe"] = markers[0]
        results["simulator_runtime"] = {
            "version": runtime["version"],
            "build": runtime["buildversion"],
        }
        results["generated_source_manifest_sha256"] = digest(
            json.dumps(receipt, sort_keys=True).encode()
        )
        return public_receipt(results)
    finally:
        try:
            run_private(["xcrun", "simctl", "shutdown", udid], root, evidence / "shutdown.log")
        finally:
            run_private(["xcrun", "simctl", "delete", udid], root, evidence / "delete.log")


def execute_ordinary(root: Path, fresh: Path, run_root: Path) -> dict[str, Any]:
    source = fresh.parents[2]
    evidence = run_root / "private-evidence"
    version = os.environ.get("GITHUB_RUN_NUMBER", "1")
    for helper, args in [
        ("app_permissions.py", []),
        ("app_build.py", [version, "apps/capture-pwa/package.json"]),
    ]:
        run_private(
            [
                "python3",
                "scripts/" + helper,
                "apply-ios",
                "apps/capture-pwa/ios/App/App/Info.plist",
                *args,
            ],
            source,
            evidence / ("ordinary-apply-" + helper + ".log"),
        )
    results: dict[str, Any] = {}
    for configuration in ("Debug", "Release"):
        tag = configuration.lower()
        log = evidence / ("ordinary-" + tag + "-build.log")
        run_private(
            [
                "xcodebuild",
                "-project",
                "App.xcodeproj",
                "-scheme",
                "App",
                "-configuration",
                configuration,
                "-sdk",
                "iphonesimulator",
                "-destination",
                "generic/platform=iOS Simulator",
                "-derivedDataPath",
                "build",
                "CODE_SIGNING_ALLOWED=NO",
                "LD_GENERATE_MAP_FILE=YES",
                "build",
            ],
            fresh / "App",
            log,
        )
        bundle = fresh / f"App/build/Build/Products/{configuration}-iphonesimulator/App.app"
        for helper in ("app_permissions.py", "app_build.py"):
            args = ["python3", "scripts/" + helper, "check-ios", str(bundle / "Info.plist")]
            if helper == "app_build.py":
                args += [version, "apps/capture-pwa/package.json"]
            run_private(args, source, evidence / ("ordinary-" + tag + "-" + helper + ".log"))
        artifact = evidence / ("ordinary-" + tag + ".zip")
        run_private(
            [
                "ditto",
                "-c",
                "-k",
                "--norsrc",
                "--noextattr",
                "--noacl",
                "--keepParent",
                str(bundle),
                str(artifact),
            ],
            source,
            evidence / ("ordinary-" + tag + "-zip.log"),
        )
        native_path = evidence / ("ordinary-" + tag + "-native-audit.json")
        run_private(
            [
                "python3",
                "-m",
                "scripts.app_notification_audit",
                "ios",
                str(source),
                str(native_path),
                str(artifact),
            ],
            source,
            evidence / ("ordinary-" + tag + "-native-audit.log"),
        )
        results[tag] = audit_ordinary(
            root,
            fresh / "App/build",
            bundle,
            source=source,
            native_path=native_path,
            artifact=artifact,
            build_log=log,
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for action in ("prepare", "run"):
        p = sub.add_parser(action)
        p.add_argument("root", type=Path)
        p.add_argument("input", type=Path)
        p.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.root, args.input, args.output)
        elif args.command == "run":
            result = execute(args.root, args.input, args.output)
            result["results"]["ordinary"] = execute_ordinary(args.root, args.input, args.output)
            result = public_receipt(result["results"])
            descriptor = os.open(
                args.output / "public-receipt.json",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(descriptor, "w") as public:
                public.write(json.dumps(result, indent=2) + "\n")
    except (PrototypeError, OSError, ValueError, KeyError) as error:
        # Do not print exception text from an OS/JSON/tool invocation.
        print(
            "APP-2C2A refused: "
            + (str(error) if isinstance(error, PrototypeError) else "invalid or unavailable input")
        )
        return 1
    print("APP-2C2A bounded step completed; no backend or device acceptance implied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
