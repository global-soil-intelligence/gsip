"""WP-APP-1: the GSIP phone app's permissions and dependencies, applied and checked in CI.

The native projects are generated from apps/capture-pwa/capacitor.config.ts in CI and never
committed, so this script is where the app's permissions are decided:

* iOS asks for the camera and for location while the app is in use, each with a purpose string.
  Saved photos are chosen through the web view's file input, whose system picker needs no
  permission. The camera plugin links the photo-library APIs, so iOS still requires the two
  photo-library purpose strings; the app never triggers either prompt. No other usage
  description and no background location exist.
* Android asks for location while the app is in use (coarse and fine), through the web view.
  The camera opens the system camera app, which needs no permission because the app declares
  none. Camera, storage, media, microphone, background location and advertising-ID permissions
  that a library might declare are removed from the merged manifest.
* The Android app ships no closed SDK (BUILD_ORDER guardrail 6): Google Play services, Firebase
  and ML Kit are refused in its dependency tree.

Usage:
    python scripts/app_permissions.py apply-ios <Info.plist>
    python scripts/app_permissions.py check-ios <Info.plist or App.app/Info.plist>
    python scripts/app_permissions.py apply-android <AndroidManifest.xml>
    python scripts/app_permissions.py check-android-manifest <AndroidManifest.xml>
    python scripts/app_permissions.py check-apk <aapt2 dump permissions output, or ->
    python scripts/app_permissions.py check-dependencies <gradle dependencies output, or ->
"""

from __future__ import annotations

import plistlib
import re
import sys
import xml.etree.ElementTree as ET  # noqa: S405 - parses the build's own generated manifest
from pathlib import Path
from typing import Any

IOS_PURPOSES = {
    "NSCameraUsageDescription": (
        "GSIP uses the camera to photograph soil beside the printed reference card."
    ),
    "NSLocationWhenInUseUsageDescription": (
        "GSIP records where each soil photo was taken, privately. Only a broad area shared by "
        "at least 3 contributors is ever published."
    ),
    # Never shown: saved photos come from the system picker, which shares only the photo chosen.
    "NSPhotoLibraryUsageDescription": (
        "GSIP lets you choose a saved soil photo with the system picker, which shares only the "
        "photo you pick."
    ),
    # Never shown: the app does not save photos to the library.
    "NSPhotoLibraryAddUsageDescription": (
        "GSIP keeps your soil photos inside the app and does not save them to your library."
    ),
}
# Requested at runtime; the photo-library strings exist only because the plugin links those APIs.
IOS_REQUESTED = ("NSCameraUsageDescription", "NSLocationWhenInUseUsageDescription")
USAGE_KEY = re.compile(r"NS\w+UsageDescription")

ANDROID_NS = "http://schemas.android.com/apk/res/android"
TOOLS_NS = "http://schemas.android.com/tools"
ANDROID_REQUESTED = (
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_FINE_LOCATION",
)
# Declared by no part of GSIP; removed in case a library's manifest brings them in. Without a
# declared camera permission, the camera plugin opens the system camera app without asking.
ANDROID_REMOVED = (
    "android.permission.ACCESS_BACKGROUND_LOCATION",
    "android.permission.ACCESS_MEDIA_LOCATION",
    "android.permission.CAMERA",
    "com.google.android.gms.permission.AD_ID",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.READ_MEDIA_VISUAL_USER_SELECTED",
    "android.permission.RECORD_AUDIO",
    "android.permission.WRITE_EXTERNAL_STORAGE",
)
# Runtime ("dangerous") and other sensitive Android permissions. Of these the app may hold only
# the two location permissions.
ANDROID_ALLOWED_SENSITIVE = frozenset(ANDROID_REQUESTED)
ANDROID_SENSITIVE = frozenset(
    f"android.permission.{name}"
    for name in (
        "ACCEPT_HANDOVER ACCESS_BACKGROUND_LOCATION ACCESS_COARSE_LOCATION ACCESS_FINE_LOCATION "
        "ACCESS_MEDIA_LOCATION ACTIVITY_RECOGNITION ADD_VOICEMAIL ANSWER_PHONE_CALLS "
        "BLUETOOTH_ADVERTISE BLUETOOTH_CONNECT BLUETOOTH_SCAN BODY_SENSORS "
        "BODY_SENSORS_BACKGROUND CALL_PHONE CAMERA FOREGROUND_SERVICE_CAMERA "
        "FOREGROUND_SERVICE_LOCATION FOREGROUND_SERVICE_MICROPHONE GET_ACCOUNTS "
        "MANAGE_EXTERNAL_STORAGE NEARBY_WIFI_DEVICES POST_NOTIFICATIONS PROCESS_OUTGOING_CALLS "
        "QUERY_ALL_PACKAGES READ_CALENDAR READ_CALL_LOG READ_CONTACTS READ_EXTERNAL_STORAGE "
        "READ_MEDIA_AUDIO READ_MEDIA_IMAGES READ_MEDIA_VIDEO READ_MEDIA_VISUAL_USER_SELECTED "
        "READ_PHONE_NUMBERS READ_PHONE_STATE READ_SMS RECEIVE_MMS RECEIVE_SMS RECEIVE_WAP_PUSH "
        "RECORD_AUDIO REQUEST_INSTALL_PACKAGES SEND_SMS SYSTEM_ALERT_WINDOW USE_SIP UWB_RANGING "
        "WRITE_CALENDAR WRITE_CALL_LOG WRITE_CONTACTS WRITE_EXTERNAL_STORAGE"
    ).split()
) | {"com.google.android.gms.permission.AD_ID"}
# Closed SDKs the Android app must not ship (BUILD_ORDER guardrail 6; GOVERNANCE.md B5).
CLOSED_DEPENDENCY = re.compile(
    r"\b(com\.google\.android\.gms|com\.google\.firebase|com\.google\.android\.play"
    r"|com\.google\.mlkit|com\.google\.android\.ads):([\w.\-]+)"
)


# iOS ------------------------------------------------------------------------------------------


def apply_ios(plist: dict[str, Any]) -> dict[str, Any]:
    """The Info.plist with GSIP's purpose strings, and no other usage or background location."""

    result = {
        key: value
        for key, value in plist.items()
        if not (USAGE_KEY.fullmatch(key) and key not in IOS_PURPOSES)
    }
    result.update(IOS_PURPOSES)
    modes = [mode for mode in result.get("UIBackgroundModes", []) if mode != "location"]
    if modes:
        result["UIBackgroundModes"] = modes
    else:
        result.pop("UIBackgroundModes", None)
    return result


def ios_problems(plist: dict[str, Any]) -> list[str]:
    problems = [
        f"{key} is missing or differs from GSIP's purpose string"
        for key, text in IOS_PURPOSES.items()
        if plist.get(key) != text
    ]
    problems += [
        f"{key} is not a usage GSIP declares"
        for key in sorted(plist)
        if USAGE_KEY.fullmatch(key) and key not in IOS_PURPOSES
    ]
    if "location" in plist.get("UIBackgroundModes", []):
        problems.append("UIBackgroundModes includes background location")
    return problems


# Android --------------------------------------------------------------------------------------


def _name(element: ET.Element) -> str:
    return element.get(f"{{{ANDROID_NS}}}name", "")


def _removed(element: ET.Element) -> bool:
    return element.get(f"{{{TOOLS_NS}}}node") == "remove"


def parse_manifest(text: str) -> ET.Element:
    # The build's own generated manifest, never input from elsewhere.
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))  # noqa: S314
    return ET.fromstring(text, parser=parser)  # noqa: S314


def apply_android(text: str) -> str:
    """The manifest with location while in use, and every unwanted permission removed."""

    ET.register_namespace("android", ANDROID_NS)
    ET.register_namespace("tools", TOOLS_NS)
    root = parse_manifest(text)
    for element in root.findall("uses-permission"):
        if _name(element) in ANDROID_REQUESTED or _name(element) in ANDROID_REMOVED:
            root.remove(element)
    for name in ANDROID_REQUESTED:
        ET.SubElement(root, "uses-permission", {f"{{{ANDROID_NS}}}name": name})
    for name in ANDROID_REMOVED:
        ET.SubElement(
            root,
            "uses-permission",
            {f"{{{ANDROID_NS}}}name": name, f"{{{TOOLS_NS}}}node": "remove"},
        )
    ET.indent(root, space="    ")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def android_permission_problems(permissions: set[str]) -> list[str]:
    problems = [
        f"{name} is a sensitive permission GSIP does not request"
        for name in sorted(permissions)
        if (name in ANDROID_SENSITIVE or name.startswith("android.permission.health."))
        and name not in ANDROID_ALLOWED_SENSITIVE
    ]
    problems += [
        f"{name} is missing, so location cannot be requested"
        for name in ANDROID_REQUESTED
        if name not in permissions
    ]
    return problems


def manifest_permissions(text: str) -> set[str]:
    return {
        _name(element)
        for element in parse_manifest(text).findall("uses-permission")
        if not _removed(element)
    }


APK_PERMISSION = re.compile(r"^uses-permission(?:-sdk-\d+)?: (?:name=)?'?([\w.]+)'?", re.M)


def closed_dependencies(gradle_output: str) -> list[str]:
    """Closed artifacts in `gradle :app:dependencies` output, as group:artifact."""

    return sorted(
        {f"{group}:{artifact}" for group, artifact in CLOSED_DEPENDENCY.findall(gradle_output)}
    )


def apk_permissions(dump: str) -> set[str]:
    """Permissions from `aapt2 dump permissions <apk>`."""

    return set(APK_PERMISSION.findall(dump))


# Command line ---------------------------------------------------------------------------------


def _report(problems: list[str], what: str) -> int:
    for problem in problems:
        print(f"{what}: {problem}", file=sys.stderr)
    if not problems:
        print(f"{what}: permissions match GSIP's policy")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    command, target = argv[1], argv[2]
    if command == "apply-ios":
        path = Path(target)
        plist = plistlib.loads(path.read_bytes())
        path.write_bytes(plistlib.dumps(apply_ios(plist), fmt=plistlib.FMT_XML))
        return _report(ios_problems(apply_ios(plist)), str(path))
    if command == "check-ios":
        return _report(ios_problems(plistlib.loads(Path(target).read_bytes())), target)
    if command == "apply-android":
        path = Path(target)
        applied = apply_android(path.read_text(encoding="utf-8"))
        path.write_text(applied, encoding="utf-8")
        return _report(android_permission_problems(manifest_permissions(applied)), str(path))
    if command == "check-android-manifest":
        text = Path(target).read_text(encoding="utf-8")
        return _report(android_permission_problems(manifest_permissions(text)), target)
    if command == "check-dependencies":
        output = sys.stdin.read() if target == "-" else Path(target).read_text(encoding="utf-8")
        if "--- " not in output:
            print("dependencies: no dependency tree in the input", file=sys.stderr)
            return 2
        closed = closed_dependencies(output)
        return _report([f"{name} is a closed SDK" for name in closed], "dependencies")
    if command == "check-apk":
        dump = sys.stdin.read() if target == "-" else Path(target).read_text(encoding="utf-8")
        permissions = apk_permissions(dump)
        print("APK permissions: " + ", ".join(sorted(permissions)))
        return _report(android_permission_problems(permissions), "APK")
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
