"""V11: documentation must not turn an unproven directory into a storage guarantee."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def plan() -> str:
    path = ROOT / "docs" / "IOS_PRIVATE_STORAGE.md"
    assert path.is_file(), "iOS storage feasibility and owner gates must be documented"
    return re.sub(r"\s+", " ", path.read_text()).lower()


def test_backend_selection_is_held_and_implementation_is_not_claimed() -> None:
    text = plan()
    assert "no backend is selected" in text
    assert "no migration or runtime implementation" in text
    assert "blocked/unverified" in text


def test_inventory_covers_every_current_indexeddb_store() -> None:
    source = (ROOT / "apps/capture-pwa/src/queue.ts").read_text()
    stores = set(re.findall(r"createObjectStore\('([^']+)'", source))
    assert len(stores) == 6
    text = plan()
    assert all(f"`{name.lower()}`" in text for name in stores)
    assert "combined transaction" in text and "queue generation" in text
    assert "cleanup-pending" in text and "no resurrection" in text


@pytest.mark.parametrize(
    "surface",
    [
        "gsip-last-auth-uid",
        "pkce",
        "user storage",
        "cookie",
        "cache",
        "camera",
        "notification",
        "journal",
    ],
)
def test_inventory_extends_beyond_photo_and_session_files(surface: str) -> None:
    assert surface in plan()


def test_pinned_source_limitations_and_resolution_scope_are_explicit() -> None:
    text = plan()
    for value in (
        "8.1.3",
        "1.1.4",
        "56bd6f9e77cb4f2269c03f2d92a9fe58fe168a1c",
        "try?",
        "non-atomic",
        "deletes an existing destination",
        "not a repository-native lock",
    ):
        assert value in text


def test_exclusion_precedes_private_writes_and_cannot_fall_back() -> None:
    text = plan()
    assert "before any private byte is written" in text
    assert all(value in text for value in ("readback", "propagate", "replacement"))
    assert "no fallback to indexeddb or localstorage" in text
    assert "guidance, not a universal guarantee" in text
    assert "tmp/caches are unsuitable for durable offline work" in text


def test_transactions_migration_and_restore_preserve_rights() -> None:
    text = plan()
    for value in (
        "acknowledged writes",
        "single-writer",
        "current ownership",
        "verified copy before deletion",
        "downgrade",
        "server rights fences",
        "older provider backups cannot be retracted",
    ):
        assert value in text


def test_device_proof_and_language_exception_are_separate_gates() -> None:
    text = plan()
    assert "physical-device backup/restore" in text
    assert "synthetic canaries only" in text
    assert "no device or backup experiment has run" in text
    assert "native-language exception" in text and "justin" in text
    assert "no deployment or capture authority" in text


def test_spec_first_packages_hold_migration_until_mechanism_is_reviewed() -> None:
    spec = (ROOT / "docs/SPEC.md").read_text()
    build = (ROOT / "docs/BUILD_ORDER.md").read_text()
    assert "### 15.10" in spec and "v11 amendment status" in spec
    section = spec.split("### 15.10", 1)[1].split("## 16.", 1)[0].lower()
    assert "no backend is selected" in section
    assert "ios_private_storage.md" in section
    assert all(value in build for value in ("WP-APP-2C1", "WP-APP-2C2", "WP-APP-2C3"))
    assert "C2 remains held" in build
    assert "native-language exception" in build
