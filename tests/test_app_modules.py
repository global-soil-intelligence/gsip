"""Capture modules resolve unambiguously on case-insensitive phone-build hosts."""

from __future__ import annotations

from pathlib import Path

CAPTURE_SOURCE = Path(__file__).resolve().parents[1] / "apps" / "capture-pwa" / "src"
MODULE_SUFFIXES = frozenset({".ts", ".tsx", ".mts", ".cts"})


def test_capture_modules_have_unique_case_insensitive_names() -> None:
    # Resolvers try .ts before .tsx. On macOS, an import of MySoil may therefore
    # select mySoil.ts rather than MySoil.tsx, even though both files survive checkout.
    modules: dict[str, list[str]] = {}
    for path in sorted(CAPTURE_SOURCE.rglob("*")):
        if path.is_file() and path.suffix in MODULE_SUFFIXES:
            relative = path.relative_to(CAPTURE_SOURCE)
            key = relative.with_suffix("").as_posix().casefold()
            modules.setdefault(key, []).append(relative.as_posix())

    collisions = [paths for paths in modules.values() if len(paths) > 1]
    assert not collisions, f"Ambiguous capture module imports on macOS: {collisions}"
