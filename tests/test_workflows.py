"""WP-6b workflow hygiene: one Supabase URL variable and pinned toolchains everywhere."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WORKFLOWS = sorted((Path(__file__).resolve().parents[1] / ".github" / "workflows").glob("*.yml"))


def _step_blocks(text: str) -> list[str]:
    """Split a workflow into its `- uses:` / `- run:` steps (indentation-based, no YAML lib)."""

    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*- (uses|run|name|id|if):", line):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_workflows_read_one_supabase_url_variable(workflow: Path) -> None:
    assert "vars.VITE_SUPABASE_URL" not in workflow.read_text(encoding="utf-8")


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_uv_and_python_are_pinned(workflow: Path) -> None:
    text = workflow.read_text(encoding="utf-8")
    for block in _step_blocks(text):
        if "astral-sh/setup-uv" in block:
            assert re.search(r"version:\s*'\d+\.\d+\.\d+'", block), workflow.name
        if "actions/setup-python" in block:
            assert re.search(r"python-version:\s*'3\.\d+'", block), workflow.name
    if "uv run" in text:
        assert "actions/setup-python" in text, workflow.name
        assert "astral-sh/setup-uv" in text, workflow.name


def test_quarantine_cleanup_runs_on_its_own_schedule() -> None:
    cleanup = next(path for path in WORKFLOWS if path.name == "quarantine-cleanup.yml")
    text = cleanup.read_text(encoding="utf-8")
    assert "schedule:" in text
    assert "python -m pipeline.qa_worker --cleanup-only" in text
    assert "vars.SUPABASE_URL" in text


def test_prior_drain_waits_less_than_its_schedule_interval() -> None:
    drain = next(path for path in WORKFLOWS if path.name == "prior-enrichment.yml")
    text = drain.read_text(encoding="utf-8")
    interval = re.search(r"cron: '\*/(\d+) \* \* \* \*'", text)
    budget = re.search(r"pipeline\.prior_worker --budget-seconds (\d+)", text)
    assert interval and budget, "the drain must declare its schedule and time budget"
    assert int(budget.group(1)) < int(interval.group(1)) * 60
    assert re.search(r"timeout-minutes: \d+", text)


def test_pages_deploy_checks_the_prior_tiles_match_the_palette() -> None:
    pages = next(path for path in WORKFLOWS if path.name == "pages.yml")
    [gate] = [
        block
        for block in _step_blocks(pages.read_text(encoding="utf-8"))
        if "pnpm check:prior-tiles" in block
    ]
    assert "VITE_PRIOR_TILES_BASE: ${{ vars.VITE_PRIOR_TILES_BASE }}" in gate


def test_rights_requests_are_processed_hourly_and_failures_raise_an_alert() -> None:
    rights = next(path for path in WORKFLOWS if path.name == "rights-worker.yml")
    text = rights.read_text(encoding="utf-8")
    assert re.search(r"cron: '\d+ \* \* \* \*'", text), "hourly schedule"
    budget = re.search(r"pipeline\.rights_worker --budget-seconds (\d+)", text)
    timeout = re.search(r"timeout-minutes: (\d+)", text)
    assert budget and timeout and int(budget.group(1)) < int(timeout.group(1)) * 60
    assert "secrets.SUPABASE_SERVICE_ROLE_KEY" in text and "vars.SUPABASE_URL" in text
    assert "cancel-in-progress: false" in text, "a new run never cancels one mid-deletion"
    assert "if: failure()" in text and "issues: write" in text and "gh issue" in text
