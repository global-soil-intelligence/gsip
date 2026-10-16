"""Strict separate review artifacts never enter ordinary Pages/native deployment."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest

SHA = "a" * 40


def receipt() -> dict[str, Any]:
    return {
        "version": "gsip-invited-browser-v1",
        "mode": "invited_private",
        "capture_live": True,
        "library_intake_live": True,
        "publication_held": True,
        "source_commit": SHA,
        "target": {
            "project_ref": "toxldjgwkxtneoqsazym",
            "supabase_url": "https://toxldjgwkxtneoqsazym.supabase.co",
            "site_origin": "https://globalsoilintelligence.com",
        },
    }


def api() -> Any:
    return importlib.import_module("scripts.build_collection")


def test_reviewed_receipt_binds_exact_target_and_commit() -> None:
    assert api().validate_activation(receipt(), SHA) == receipt()


@pytest.mark.parametrize("field", list(receipt()))
def test_missing_activation_fields_refuse(field: str) -> None:
    value = receipt()
    del value[field]
    with pytest.raises(ValueError):
        api().validate_activation(value, SHA)


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", "fixture"),
        ("mode", "public"),
        ("capture_live", False),
        ("library_intake_live", False),
        ("publication_held", False),
        ("capture_live", "true"),
        ("source_commit", "b" * 40),
        ("extra", True),
    ],
)
def test_unknown_or_mismatched_receipt_refuses(field: str, value: Any) -> None:
    document = receipt()
    document[field] = value
    with pytest.raises(ValueError):
        api().validate_activation(document, SHA)


@pytest.mark.parametrize(
    "field,value",
    [
        ("project_ref", "other"),
        ("supabase_url", "https://supabase.test"),
        ("site_origin", "https://elsewhere.invalid"),
        ("site_origin", "https://globalsoilintelligence.com/path"),
        ("extra", "x"),
    ],
)
def test_wrong_target_refuses(field: str, value: str) -> None:
    document = receipt()
    document["target"][field] = value
    with pytest.raises(ValueError):
        api().validate_activation(document, SHA)


def fixtures(tmp_path: Path) -> tuple[Path, Path, Path]:
    closed, pilot, out = tmp_path / "closed", tmp_path / "pilot", tmp_path / "review"
    (closed / "capture").mkdir(parents=True)
    pilot.mkdir()
    (closed / "index.html").write_text("closed public fixture")
    (closed / "capture/gsip-activation.json").write_text(
        json.dumps({"capture_live": False, "library_intake_live": False})
    )
    (pilot / "index.html").write_text("synthetic unit fixture; no application or upload controls")
    (pilot / "gsip-activation.json").write_text(json.dumps(receipt()))
    return closed, pilot, out


def test_package_is_separate_and_inventory_detects_tampering(tmp_path: Path) -> None:
    closed, pilot, out = fixtures(tmp_path)
    result = api().package_review(closed, pilot, out, SHA)
    assert json.loads((closed / "capture/gsip-activation.json").read_text()) == {
        "capture_live": False,
        "library_intake_live": False,
    }
    assert result["source_commit"] == SHA
    api().verify_review(out, SHA)
    (out / "capture/index.html").write_text("tampered")
    with pytest.raises(ValueError):
        api().verify_review(out, SHA)


@pytest.mark.parametrize("variant", ["fixture", "open_base", "symlink", "overlap", "extra_file"])
def test_unsafe_artifacts_are_never_packaged(tmp_path: Path, variant: str) -> None:
    closed, pilot, out = fixtures(tmp_path)
    if variant == "fixture":
        value = receipt()
        value["version"] = "gsip-invited-browser-fixture-v1"
        (pilot / "gsip-activation.json").write_text(json.dumps(value))
    elif variant == "open_base":
        (closed / "capture/gsip-activation.json").write_text(
            json.dumps({"capture_live": True, "library_intake_live": False})
        )
    elif variant == "symlink":
        (pilot / "leak").symlink_to(closed / "index.html")
    elif variant == "overlap":
        out = closed
    else:
        (pilot / ".env").write_text("synthetic blocked file")
    with pytest.raises(ValueError):
        api().package_review(closed, pilot, out, SHA)


@pytest.mark.parametrize("role", ["service_role", "authenticated", "", "anon"])
def test_legacy_browser_keys_allow_only_anonymous_role(role: str) -> None:
    import base64

    encoded = base64.urlsafe_b64encode(json.dumps({"role": role}).encode()).decode().rstrip("=")
    assert api().browser_key_allowed("header." + encoded + ".synthetic") is (role == "anon")


@pytest.mark.parametrize("value", ["", "fixture", "sb_" + "secret_" + "x" * 32, "not.a.jwt"])
def test_opaque_or_secret_browser_configuration_refuses(value: str) -> None:
    assert not api().browser_key_allowed(value)


@pytest.mark.parametrize("metadata", ['{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}'])
def test_duplicate_and_nonfinite_metadata_refuse(tmp_path: Path, metadata: str) -> None:
    path = tmp_path / "metadata.json"
    path.write_text(metadata)
    with pytest.raises(ValueError):
        api().read_json(path)


def test_integer_review_flags_refuse(tmp_path: Path) -> None:
    closed, pilot, out = fixtures(tmp_path)
    result = api().package_review(closed, pilot, out, SHA)
    result["activation"]["capture_live"] = 1
    (out / api().REVIEW).write_text(json.dumps(result))
    with pytest.raises(ValueError):
        api().verify_review(out, SHA)


def test_review_source_rejects_dirty_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api().subprocess,
        "check_output",
        lambda command, **kwargs: SHA if command[1] == "rev-parse" else " M source.ts",
    )
    with pytest.raises(ValueError):
        api().assert_reviewed_source("synthetic-git", SHA)


def test_native_validator_refuses_invited_or_fixture_receipts() -> None:
    from scripts.app_build import check_activation

    for version in ["gsip-invited-browser-v1", "gsip-invited-browser-fixture-v1"]:
        document = receipt()
        document["version"] = version
        with pytest.raises(ValueError, match="closed"):
            check_activation(json.dumps(document).encode())


def test_ordinary_pages_refuses_pilot_receipt_before_copy(tmp_path: Path) -> None:
    import shutil
    import subprocess

    from scripts import build_collection

    node = shutil.which("node")
    assert node is not None
    script = tmp_path / "scripts/build-pages.mjs"
    script.parent.mkdir()
    script.write_text((build_collection.ROOT / "scripts/build-pages.mjs").read_text())
    capture = tmp_path / "apps/capture-pwa/dist"
    capture.mkdir(parents=True)
    (capture / "gsip-activation.json").write_text(json.dumps(receipt()))
    result = subprocess.run([node, str(script)], check=False, capture_output=True)  # noqa: S603 - fixed local guard on synthetic metadata
    assert result.returncode != 0
    assert b"activation must be closed" in result.stderr
    assert not (tmp_path / "_site").exists()


def test_realistic_closed_base_retains_sitemap_in_review_inventory(tmp_path: Path) -> None:
    closed, pilot, out = fixtures(tmp_path)
    content = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>'
    (closed / "sitemap.xml").write_text(content)
    record = api().package_review(closed, pilot, out, SHA)
    assert "sitemap.xml" in record["files"]
    assert (out / "sitemap.xml").read_text() == content
    api().verify_review(out, SHA)
