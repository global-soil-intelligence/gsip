"""Closed deployable Pages and isolated, loopback-only synthetic browser fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import e2e_server
import pytest


def test_builds_pages_closed_and_mock_capture_only_in_temporary_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, capture = tmp_path / "repository", tmp_path / "temporary-capture"
    root.mkdir()
    capture.mkdir()
    monkeypatch.setenv("VITE_CAPTURE_LIVE", "true")
    monkeypatch.setenv("VITE_LIBRARY_INTAKE_LIVE", "true")
    monkeypatch.setenv("VITE_SUPABASE_URL", "https://unexpected.invalid")
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def run(command: list[str], **kwargs: Any) -> None:
        calls.append((command, kwargs))
        destination = root / "_site/capture" if len(calls) == 1 else capture
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "gsip-activation.json").write_text(
            json.dumps({"capture_live": len(calls) == 2, "library_intake_live": False})
        )

    monkeypatch.setattr("e2e_server.subprocess.run", run)
    monkeypatch.setattr("e2e_server.which", lambda name: "/synthetic/bin/pnpm")
    e2e_server.build_fixtures(root, capture)
    assert calls[0][0] == ["/synthetic/bin/pnpm", "build:pages"]
    assert calls[0][1]["env"]["VITE_CAPTURE_LIVE"] == "false"
    assert calls[1][0][-3:] == ["--outDir", str(capture), "--emptyOutDir"]
    assert calls[1][1]["env"]["VITE_CAPTURE_LIVE"] == "true"
    for _, options in calls:
        assert options["check"] is True
        assert options["cwd"] == root
        assert options["env"]["VITE_LIBRARY_INTAKE_LIVE"] == "false"
        assert options["env"]["VITE_SUPABASE_URL"] == "https://supabase.test"
        assert options["env"]["VITE_SUPABASE_PUBLISHABLE_KEY"] == "e2e-key"
    assert json.loads((root / "_site/capture/gsip-activation.json").read_text()) == {
        "capture_live": False,
        "library_intake_live": False,
    }


def test_refuses_open_pages_before_mock_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: Any) -> None:
        calls.append(command)
        destination = tmp_path / "_site/capture"
        destination.mkdir(parents=True)
        (destination / "gsip-activation.json").write_text(
            json.dumps({"capture_live": True, "library_intake_live": False})
        )

    monkeypatch.setattr("e2e_server.subprocess.run", run)
    monkeypatch.setattr("e2e_server.which", lambda name: "/synthetic/bin/pnpm")
    with pytest.raises(ValueError, match="Pages activation"):
        e2e_server.build_fixtures(tmp_path, tmp_path / "unused")
    assert len(calls) == 1


@pytest.mark.parametrize("path", ["/elsewhere", "/gsip/../outside", "/gsip/capture/%2e%2e/private"])
def test_routes_cannot_escape_roots(tmp_path: Path, path: str) -> None:
    handler = object.__new__(e2e_server.handler_type(tmp_path / "site", tmp_path / "fixture"))
    assert handler.translate_path(path) == str(tmp_path / "site/.not-found")


def test_only_capture_route_uses_fixture(tmp_path: Path) -> None:
    handler = object.__new__(e2e_server.handler_type(tmp_path / "site", tmp_path / "fixture"))
    assert handler.translate_path("/gsip/capture/index.html") == str(
        tmp_path / "fixture/index.html"
    )
    assert handler.translate_path("/gsip/map/index.html") == str(tmp_path / "site/map/index.html")


def test_main_cleans_fixture_and_binds_loopback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[Path] = []

    def build(root: Path, capture: Path) -> None:
        observed.append(capture)
        assert capture.is_dir()

    class Server:
        def __init__(self, address: tuple[str, int], handler: object) -> None:
            assert address == ("127.0.0.1", 4173)

        def __enter__(self) -> Server:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def serve_forever(self) -> None:
            raise RuntimeError("synthetic stop")

    monkeypatch.setattr(e2e_server, "build_fixtures", build)
    monkeypatch.setattr(e2e_server, "ThreadingHTTPServer", Server)
    with pytest.raises(RuntimeError, match="synthetic stop"):
        e2e_server.main()
    assert len(observed) == 1 and not observed[0].exists()


def test_playwright_uses_isolated_server_and_disallows_server_reuse() -> None:
    config = (e2e_server.ROOT / "playwright.config.ts").read_text()
    assert "uv run python tests/e2e_server.py" in config
    assert "reuseExistingServer: false" in config
    assert "VITE_CAPTURE_LIVE: 'true'" not in config
