"""V12 document-contract regressions, never native or backup acceptance tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def design() -> str:
    path = ROOT / "docs/IOS_NATIVE_STORAGE_DESIGN.md"
    assert path.is_file(), "A concrete, separately gated native design is required"
    return re.sub(r"\s+", " ", path.read_text()).lower()


@pytest.mark.parametrize(
    "requirements",
    [
        ("proposal only", "no backend is admitted", "no native-language exception is granted"),
        ("before sqlite open or recovery", "exclusion readback", "no fallback"),
        ("journal_mode=delete", "synchronous=extra", "unknown pragmas", "fullfsync"),
        ("temp_store=memory", "does not eliminate", "hot journal", "power-loss"),
        ("single native writer", "no caller sql", "no caller path", "no transaction across"),
        ("operation receipt", "original owner", "auth epoch", "launch lease", "queue generation"),
        ("incomplete staging", "not acknowledged", "quota", "no eviction or truncation"),
        ("pending anchor", "clean anchor", "quarantine", "not atomic with sqlite"),
        ("whenpasscodesetthisdeviceonly", "synchronizable=false", "passcode removal", "reinstall"),
        ("not a hardware monotonic counter", "pending-plus-old", "no automatic destructive reset"),
        ("ordinary offline restart", "current server rights", "co-restored local flags"),
        ("before ordinary javascript", "nonpersistent", "cookie observer", "enabled=false"),
        (
            "class-name",
            "main-frame",
            "allowlist",
            "prompt",
            "core fork",
            "webviewassethandler",
            "no native output-handle broker",
        ),
        ("isolated legacy exporter", "no ordinary app", "verified copy before deletion"),
        (
            "no bridge await inside",
            "without creation or upgrade",
            "user-driven full relaunch",
            "displayname",
            "physical erasure",
            "older provider backups",
        ),
        ("late auth callbacks", "unknown is not empty", "pkce", "user storage"),
        ("cleanup-pending", "os cancellation", "camera", "native cookie", "preferences"),
        ("no new third-party dependency", "public domain", "unmeasured", "swift"),
        (
            "physical-device",
            "synthetic canaries only",
            "no device experiment",
            "blocked/unverified",
        ),
        ("i1–i15", "l1–l7", "b1–b8", "capture", "production", "i12"),
    ],
)
def test_design_keeps_each_admission_and_failure_boundary(requirements: tuple[str, ...]) -> None:
    text = design()
    assert all(item in text for item in requirements)


def test_every_actual_queue_store_has_a_native_transaction_mapping() -> None:
    source = (ROOT / "apps/capture-pwa/src/queue.ts").read_text()
    stores = set(re.findall(r"createObjectStore\('([^']+)'", source))
    assert len(stores) == 6
    text = design()
    assert all(f"`{store.lower()}`" in text for store in stores)
    assert "six-store clear" in text and "four payload/namespace stores" in text


def test_current_public_queue_operations_are_not_silently_dropped() -> None:
    source = (ROOT / "apps/capture-pwa/src/queue.ts").read_text()
    operations = re.findall(r"export (?:async )?function (\w+)\(", source)
    assert len(operations) >= 20
    text = design()
    assert all(f"`{name.lower()}`" in text for name in operations)
    assert "currently materializes" in text
    assert "paged" in text and "web/android" in text


def test_spec_addition_is_proposed_and_does_not_grant_implementation() -> None:
    spec = (ROOT / "docs/SPEC.md").read_text()
    assert "### 15.11 Proposed v12" in spec
    amendment = spec.split("### 15.11", 1)[1].split("## 16.", 1)[0].lower()
    assert "ios_native_storage_design.md" in amendment
    assert "no native-language exception is granted" in amendment
    assert "no backend is admitted" in amendment
    assert "no implementation" in amendment
    assert "explicit" in amendment and "justin" in amendment


def test_implementation_packages_are_separate_and_all_new_criteria_are_unchecked() -> None:
    build = (ROOT / "docs/BUILD_ORDER.md").read_text()
    assert "Proposed v12 APP-2C2 decomposition" in build
    section = build.split("Proposed v12 APP-2C2 decomposition", 1)[1].split(
        "**WP-APP-2C3", 1
    )[0]
    for package in ("APP-2C2A", "APP-2C2B", "APP-2C2C"):
        assert package in section
    assert "[x]" not in section
    assert section.count("- [ ]") >= 6
    assert "held" in section.lower() and "native-language exception" in section


def test_owner_decisions_and_restore_rows_cannot_silently_admit_old_state() -> None:
    text = design()
    assert "owner decisions" in text and "pending" in text
    assert "passcode-required" in text and "preserve quarantined bytes" in text
    assert "privacy contact" in text and "new anonymous account" in text
    assert "design approval alone" in text and "not implementation permission" in text

    rows = {}
    for line in (ROOT / "docs/IOS_NATIVE_STORAGE_DESIGN.md").read_text().splitlines():
        if line.startswith("|"):
            columns = [re.sub(r"\s+", " ", cell.strip()).lower() for cell in line.split("|")]
            if len(columns) == 4:
                rows[columns[1]] = columns[2]
    old = rows["pending-plus-old database"]
    assert old.startswith("quarantine;")
    assert "preserve bytes and anchor" in old
    assert "never roll anchor back" in old
    mismatch = next(value for key, value in rows.items() if key.startswith("clean/db nonce"))
    assert mismatch.startswith("quarantine;")
    assert "no active use, import, sync, sdk boot or automatic account creation" in mismatch
    assert "absence alone cannot prove fresh" in rows["both absent"]
    clean = next(value for key, value in rows.items() if key.startswith("clean anchor plus"))
    assert clean.startswith("admit after protected-data/root checks;")
    assert "ordinary offline restart" in clean
    committed = next(value for key, value in rows.items() if key.startswith("pending anchor plus"))
    assert committed.startswith("finalize only after all checks/readback;")
    assert "without applying twice" in committed
