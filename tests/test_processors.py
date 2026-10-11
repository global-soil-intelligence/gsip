"""WP-6d: every external host GSIP code calls is listed in the privacy notice processor table."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVACY = ROOT / "docs" / "legal" / "PRIVACY.md"
# Code that runs in production or in GSIP's workers and builds. Tests and fixtures are excluded.
SOURCES = (
    "apps/capture-pwa/src",
    "apps/capture-pwa/index.html",
    "apps/map-web/src",
    "apps/map-web/index.html",
    "apps/map-web/scripts",
    "apps/site-web/src",
    "apps/site-web/index.html",
    "card",
    "packages/schema/src",
    "pipeline",
    "scripts",
    "supabase/functions",
    ".github/workflows",
)
CODE_SUFFIXES = {".html", ".js", ".mjs", ".py", ".ts", ".tsx", ".yml"}
URL = re.compile(r"https?://([A-Za-z0-9.-]+\.[A-Za-z]{2,}|127\.0\.0\.1|localhost)")
# Strings that look like URLs but are never contacted.
NOT_CONTACTED = {
    "127.0.0.1": "local development server",
    "localhost": "local development server",
    "ns.adobe.com": "XMP namespace identifier, matched when stripping metadata",
    "schema.org": "JSON-LD vocabulary identifier",
    "soilgrids.org": "citation link in the dataset card",
}
# Services the code reaches through configuration or a client library rather than a literal URL.
CONFIGURED = {
    "*.supabase.co": "SUPABASE_URL / VITE_SUPABASE_URL",
    "huggingface.co": "huggingface_hub in pipeline/export.py",
    "*.github.io": "GitHub Pages hosting (pages.yml)",
}


def code_hosts() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for source in SOURCES:
        base = ROOT / source
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for path in files:
            if path.suffix not in CODE_SUFFIXES or "node_modules" in path.parts:
                continue
            for host in URL.findall(path.read_text(encoding="utf-8", errors="ignore")):
                found.setdefault(host.lower(), set()).add(str(path.relative_to(ROOT)))
    return found


def listed_hosts() -> set[str]:
    text = PRIVACY.read_text(encoding="utf-8")
    section = text.split("## Processors and external services", 1)[1].split("\n## ", 1)[0]
    hosts: set[str] = set()
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        hosts_cell = line.rstrip("|").rsplit("|", 1)[-1]
        hosts.update(token.lower() for token in re.findall(r"`([^`]+)`", hosts_cell))
    return hosts


def covered(host: str, listed: set[str]) -> bool:
    return any(
        host == entry or (entry.startswith("*.") and host.endswith(entry[1:])) for entry in listed
    )


def test_the_processor_table_is_found_and_parsed() -> None:
    listed = listed_hosts()
    assert {"*.supabase.co", "huggingface.co", "rest.isric.org"} <= listed


def test_every_external_host_in_the_code_is_in_the_privacy_notice() -> None:
    listed = listed_hosts()
    missing = {
        host: sorted(paths)
        for host, paths in code_hosts().items()
        if host not in NOT_CONTACTED and not covered(host, listed)
    }
    assert not missing, (
        "List these hosts in docs/legal/PRIVACY.md (Processors and external services) "
        f"or explain them in NOT_CONTACTED: {missing}"
    )


def test_configured_services_are_listed_too() -> None:
    listed = listed_hosts()
    assert all(covered(entry.removeprefix("*."), listed) or entry in listed for entry in CONFIGURED)


def test_the_check_would_catch_a_new_upstream() -> None:
    assert not covered("api.example-weather.net", listed_hosts())
    assert covered("abcdefgh.supabase.co", listed_hosts())
    assert URL.findall("fetch('https://api.example-weather.net/v1')") == ["api.example-weather.net"]


def test_exemptions_are_only_for_hosts_the_code_mentions() -> None:
    mentioned = code_hosts()
    stale = sorted(set(NOT_CONTACTED) - set(mentioned) - {"localhost"})
    assert not stale, f"remove exemptions the code no longer needs: {stale}"
