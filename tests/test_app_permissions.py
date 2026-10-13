"""WP-APP-1: the phone app asks only for the camera and for location while in use."""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import Any

import pytest

from scripts import app_permissions as permissions

FIXTURES = Path(__file__).parent / "fixtures" / "app"


def template_plist() -> dict[str, Any]:
    """The Info.plist that `cap add ios` generates (Capacitor 8 template)."""

    data: dict[str, Any] = plistlib.loads((FIXTURES / "Info.plist").read_bytes())
    return data


def template_manifest() -> str:
    """The AndroidManifest.xml that `cap add android` generates (Capacitor 8 template)."""

    return (FIXTURES / "AndroidManifest.xml").read_text(encoding="utf-8")


def test_ios_gets_a_purpose_string_for_each_request_and_nothing_else() -> None:
    applied = permissions.apply_ios(template_plist())

    assert permissions.ios_problems(applied) == []
    for key in permissions.IOS_REQUESTED:
        assert applied[key].strip()
    # The template's own keys survive.
    assert applied["CFBundleIdentifier"] == "$(PRODUCT_BUNDLE_IDENTIFIER)"
    assert applied["UILaunchStoryboardName"] == "LaunchScreen"
    # Location is asked for only while the app is in use.
    assert not any(key.startswith("NSLocationAlways") for key in applied)


def test_ios_drops_other_usages_and_background_location() -> None:
    plist = template_plist() | {
        "NSLocationAlwaysAndWhenInUseUsageDescription": "always",
        "NSMicrophoneUsageDescription": "audio",
        "UIBackgroundModes": ["location", "remote-notification"],
    }
    assert permissions.ios_problems(plist) != []

    applied = permissions.apply_ios(plist)
    assert "NSLocationAlwaysAndWhenInUseUsageDescription" not in applied
    assert "NSMicrophoneUsageDescription" not in applied
    assert applied["UIBackgroundModes"] == ["remote-notification"]
    assert permissions.ios_problems(applied) == []
    only_location = permissions.apply_ios(template_plist() | {"UIBackgroundModes": ["location"]})
    assert "UIBackgroundModes" not in only_location


def test_ios_check_refuses_background_location_alone() -> None:
    applied = permissions.apply_ios(template_plist())
    assert permissions.ios_problems(applied | {"UIBackgroundModes": ["location"]}) == [
        "UIBackgroundModes includes background location"
    ]


def test_ios_check_reads_the_built_apps_binary_plist(tmp_path: Path) -> None:
    built = tmp_path / "Info.plist"
    built.write_bytes(
        plistlib.dumps(permissions.apply_ios(template_plist()), fmt=plistlib.FMT_BINARY)
    )
    assert permissions.main(["app_permissions.py", "check-ios", str(built)]) == 0
    built.write_bytes(plistlib.dumps(template_plist(), fmt=plistlib.FMT_BINARY))
    assert permissions.main(["app_permissions.py", "check-ios", str(built)]) == 1


def test_apply_ios_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "Info.plist"
    target.write_bytes((FIXTURES / "Info.plist").read_bytes())
    assert permissions.main(["app_permissions.py", "apply-ios", str(target)]) == 0
    once = target.read_bytes()
    assert permissions.main(["app_permissions.py", "apply-ios", str(target)]) == 0
    assert target.read_bytes() == once


def test_android_requests_location_while_in_use_and_removes_the_rest() -> None:
    applied = permissions.apply_android(template_manifest())
    granted = permissions.manifest_permissions(applied)

    assert granted == {
        "android.permission.INTERNET",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.ACCESS_FINE_LOCATION",
    }
    assert permissions.android_permission_problems(granted) == []
    # Any library that declares these loses them in the merged manifest, the camera included:
    # without it, the camera plugin opens the system camera app without asking.
    for name in permissions.ANDROID_REMOVED:
        assert f'android:name="{name}" tools:node="remove"' in applied
    assert 'android:name="android.permission.CAMERA" tools:node="remove"' in applied
    # The prefixes Android tooling expects, and the template's application, survive.
    assert 'xmlns:android="http://schemas.android.com/apk/res/android"' in applied
    assert 'xmlns:tools="http://schemas.android.com/tools"' in applied
    assert "ns0:" not in applied
    assert 'android:name=".MainActivity"' in applied
    assert "${applicationId}.fileprovider" in applied


def test_apply_android_is_idempotent() -> None:
    once = permissions.apply_android(template_manifest())
    assert permissions.apply_android(once) == once


def test_the_template_alone_cannot_ask_for_location() -> None:
    problems = permissions.android_permission_problems(
        permissions.manifest_permissions(template_manifest())
    )
    assert any("ACCESS_FINE_LOCATION is missing" in problem for problem in problems)


APK_DUMP = """package: com.globalsoilintelligence.app
permission: com.globalsoilintelligence.app.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION
uses-permission: name='android.permission.INTERNET'
uses-permission: name='android.permission.ACCESS_COARSE_LOCATION'
uses-permission: name='android.permission.ACCESS_FINE_LOCATION'
uses-permission: name='android.permission.ACCESS_NETWORK_STATE'
uses-permission: name='com.globalsoilintelligence.app.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION'
"""


def test_the_built_apk_holds_no_sensitive_permission_beyond_location() -> None:
    granted = permissions.apk_permissions(APK_DUMP)
    assert "android.permission.ACCESS_NETWORK_STATE" in granted
    assert permissions.android_permission_problems(granted) == []


@pytest.mark.parametrize(
    "extra",
    [
        "uses-permission: name='android.permission.CAMERA'",
        "uses-permission: name='com.google.android.gms.permission.AD_ID'",
        "uses-permission: name='android.permission.ACCESS_BACKGROUND_LOCATION'",
        "uses-permission: name='android.permission.READ_MEDIA_IMAGES'",
        "uses-permission-sdk-23: name='android.permission.RECORD_AUDIO'",
        "uses-permission: name='android.permission.WRITE_EXTERNAL_STORAGE' maxSdkVersion='28'",
        "uses-permission: name='android.permission.health.READ_STEPS'",
    ],
)
def test_the_apk_check_fails_on_any_other_sensitive_permission(extra: str) -> None:
    problems = permissions.android_permission_problems(
        permissions.apk_permissions(APK_DUMP + extra + "\n")
    )
    assert len(problems) == 1


def test_the_apk_check_reads_standard_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(APK_DUMP))
    assert permissions.main(["app_permissions.py", "check-apk", "-"]) == 0
    assert "android.permission.ACCESS_FINE_LOCATION" in capsys.readouterr().out


GRADLE_TREE = """
debugRuntimeClasspath - Runtime classpath of /debug.
+--- project :capacitor-android
|    +--- androidx.webkit:webkit:1.14.0
|    \\--- org.apache.cordova:framework:14.0.1
+--- project :capacitor-camera
|    +--- io.ionic.libs:ioncamera-android:1.0.2
|    |    \\--- androidx.camera:camera-core:1.4.2
|    \\--- androidx.exifinterface:exifinterface:1.4.1
\\--- project :capacitor-filesystem
     \\--- io.ionic.libs:ionfilesystem-android:1.1.0
"""


def test_the_android_app_ships_no_closed_sdk(tmp_path: Path) -> None:
    assert permissions.closed_dependencies(GRADLE_TREE) == []
    with_play = GRADLE_TREE + (
        "+--- project :capacitor-geolocation\n"
        "|    +--- com.google.android.gms:play-services-location:21.3.0\n"
        "|    |    \\--- com.google.android.gms:play-services-base:18.5.0 (*)\n"
        "|    \\--- com.google.firebase:firebase-analytics -> 22.1.0\n"
    )
    assert permissions.closed_dependencies(with_play) == [
        "com.google.android.gms:play-services-base",
        "com.google.android.gms:play-services-location",
        "com.google.firebase:firebase-analytics",
    ]
    tree = tmp_path / "dependencies.txt"
    tree.write_text(GRADLE_TREE, encoding="utf-8")
    assert permissions.main(["app_permissions.py", "check-dependencies", str(tree)]) == 0
    tree.write_text(with_play, encoding="utf-8")
    assert permissions.main(["app_permissions.py", "check-dependencies", str(tree)]) == 1
    # An empty or failed Gradle run is not a pass.
    tree.write_text("", encoding="utf-8")
    assert permissions.main(["app_permissions.py", "check-dependencies", str(tree)]) == 2
