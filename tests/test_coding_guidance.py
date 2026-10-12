"""WP-AGENT-0: a coding agent can follow the root guide without stale paths or commands."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "AGENTS.md"


def test_coding_guide_links_resolve_and_include_the_read_first_documents() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    local_links = {link for link in links if "://" not in link}
    assert {
        "docs/SPEC.md",
        "docs/BUILD_ORDER.md",
        "CONTRIBUTING.md",
        "GOVERNANCE.md",
        "docs/PHASE1_DEPLOYMENT.md",
        "docs/APP_STORE.md",
        "docs/legal/README.md",
        ".env.example",
        "docs/AGENTS.md",
    } <= local_links
    for link in local_links:
        path = ROOT / link.split("#", 1)[0]
        assert path.is_file(), f"broken coding-guide link: {link}"


def test_coding_guide_check_commands_resolve_to_repository_tools() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = set(package["scripts"])
    documented = set(re.findall(r"^pnpm ([\w:-]+)$", text, re.MULTILINE))
    assert {"lint", "typecheck", "test", "build", "check:map-budget", "check:site-budget"} <= (
        documented
    )
    assert documented <= scripts, f"stale root pnpm commands: {documented - scripts}"

    packages = {}
    for path in (ROOT / "apps").glob("*/package.json"):
        app = json.loads(path.read_text(encoding="utf-8"))
        packages[app["name"]] = set(app["scripts"])
    for name, script in re.findall(r"^pnpm --filter ([\w@/-]+) ([\w:-]+)$", text, re.MULTILINE):
        assert script in packages[name], f"stale workspace command: {name} {script}"

    assert "pnpm exec playwright test --project=desktop-chrome" in text
    playwright = ROOT / "playwright.config.ts"
    assert "desktop-chrome" in playwright.read_text(encoding="utf-8")
    assert "pnpm db:start && pnpm db:reset && pnpm db:test" in text
    assert {"db:start", "db:reset", "db:test"} <= scripts
    assert (ROOT / "scripts/db-migration-test.sh").is_file()
    assert (ROOT / "supabase/functions/deno.json").is_file()
    assert tuple((ROOT / "supabase/functions").glob("*/index.ts"))


def test_coding_guide_explicitly_prohibits_the_i5_ui_and_api_term() -> None:
    text = " ".join(GUIDE.read_text(encoding="utf-8").casefold().split())
    rule = re.search(r"\bi5\b[^.]*", text)
    assert rule is not None, "coding guide must state I5 explicitly"
    assert re.search(r"\bui\b", rule[0]) and re.search(r"\bapi\b", rule[0]), (
        "I5 must apply to both UI and API copy"
    )
    assert re.search(r"\b(?:never|must not)\b.*\b(?:says?|uses?)\b.*\bsoil test\b", rule[0]), (
        "I5 must explicitly prohibit the term in UI and API copy"
    )
