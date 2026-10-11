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
