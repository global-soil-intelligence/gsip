"""Serve synthetic capture fixtures on loopback without opening the Pages artifact."""

from __future__ import annotations

import json
import os
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def build_fixtures(root: Path, capture: Path) -> None:
    pnpm = which("pnpm")
    if pnpm is None:
        raise ValueError("Pinned pnpm executable is required")
    # These fixed endpoints are reserved test names; inherited build configuration is discarded.
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("VITE_", "SUPABASE_"))
    }
    env.update(
        VITE_CAPTURE_LIVE="false",
        VITE_LIBRARY_INTAKE_LIVE="false",
        VITE_GSIP_PUBLIC_API="https://supabase.test/functions/v1/gsip-public",
        VITE_SUPABASE_PUBLISHABLE_KEY="e2e-key",
        VITE_SUPABASE_URL="https://supabase.test",
    )
    subprocess.run(  # noqa: S603 - fixed repository build, no shell or user arguments
        [pnpm, "build:pages"], cwd=root, env=env, check=True
    )
    closed = json.loads((root / "_site/capture/gsip-activation.json").read_text())
    if closed != {"capture_live": False, "library_intake_live": False}:
        raise ValueError("Pages activation must remain closed")
    subprocess.run(  # noqa: S603 - isolated test output, never packaged into Pages
        [
            pnpm,
            "--filter",
            "@gsip/capture-pwa",
            "exec",
            "vite",
            "build",
            "--outDir",
            str(capture),
            "--emptyOutDir",
        ],
        cwd=root,
        env={**env, "VITE_CAPTURE_LIVE": "true"},
        check=True,
    )
    fixture = json.loads((capture / "gsip-activation.json").read_text())
    if fixture != {"capture_live": True, "library_intake_live": False}:
        raise ValueError("Unexpected synthetic fixture activation")


def handler_type(site: Path, capture: Path) -> type[SimpleHTTPRequestHandler]:
    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self, path: str) -> str:
            pathname = unquote(urlsplit(path).path)
            if pathname.startswith("/gsip/capture/"):
                base, relative = capture, pathname[len("/gsip/capture/") :]
            elif pathname.startswith("/gsip/"):
                base, relative = site, pathname[len("/gsip/") :]
            else:
                return str(site / ".not-found")
            resolved = (base / relative).resolve()
            if not resolved.is_relative_to(base.resolve()):
                return str(site / ".not-found")
            return str(resolved)

        def list_directory(self, path: str | os.PathLike[str]) -> BytesIO | None:
            self.send_error(403, "Directory listing disabled")
            return None

        def log_message(self, format: str, *args: object) -> None:
            # Synthetic routes only; do not log request contents.
            pass

    return Handler


def main() -> None:
    with TemporaryDirectory(prefix="gsip-e2e-capture-") as directory:
        capture = Path(directory)
        build_fixtures(ROOT, capture)
        with ThreadingHTTPServer(
            ("127.0.0.1", 4173), handler_type(ROOT / "_site", capture)
        ) as server:
            server.serve_forever()


if __name__ == "__main__":
    main()
