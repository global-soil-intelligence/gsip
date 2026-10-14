"""Execute the native workflow's parent Git setup against isolated synthetic repositories."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/app-build.yml"
CANONICAL = "https://github.com/global-soil-intelligence/gsip.git"
BASELINE = "d7ed716ed0921381da04f542e90902ede36cb462"
PARENT_STEPS = (
    "Build the exact APP-2B parent in an isolated checkout",
    "Build the exact iOS parent in an isolated checkout",
)


def parent_setup(step: str) -> str:
    """Extract the actual run body up to its first install, without rebuilding Git commands."""
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"      - name: {step}")
    start = lines.index("        run: |", start) + 1
    commands = []
    for line in lines[start:]:
        if line == "          pnpm install --frozen-lockfile --package-import-method copy":
            break
        assert line.startswith("          "), "unexpected parent setup boundary"
        commands.append(line[10:])
    else:
        pytest.fail("parent install boundary is missing")
    assert commands[0] == f"baseline={BASELINE}"
    return "\n".join(commands) + "\n"


def run(
    args: list[str], env: dict[str, str], cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 -- fixed tools and owned synthetic repository arguments.
        args, env=env, cwd=cwd, text=True, capture_output=True, check=False
    )


def git(env: dict[str, str], *args: str) -> str:
    executable = shutil.which("git")
    assert executable is not None, "Git is required for the workflow's checkout regression"
    result = run([executable, *args], env)
    result.check_returncode()
    return result.stdout.strip()


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def fixture(tmp_path: Path) -> tuple[dict[str, str], Path, str]:
    """Hide the baseline from advertised refs and leave its trees out of the candidate clone."""
    seed, remote, candidate = (tmp_path / name for name in ("seed", "public.git", "candidate"))
    env = {
        **os.environ,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "file",
        "GIT_AUTHOR_NAME": "Synthetic fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_AUTHOR_DATE": "2026-10-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2026-10-01T00:00:00Z",
    }
    git(env, "init", "-b", "baseline", str(seed))
    (seed / "version.txt").write_text("synthetic baseline\n", encoding="utf-8")
    git(env, "-C", str(seed), "add", "version.txt")
    git(env, "-C", str(seed), "commit", "-m", "synthetic baseline")
    baseline = git(env, "-C", str(seed), "rev-parse", "HEAD")
    git(env, "-C", str(seed), "checkout", "--orphan", "candidate")
    git(env, "-C", str(seed), "rm", "-rf", ".")
    (seed / "version.txt").write_text("synthetic candidate\n", encoding="utf-8")
    git(env, "-C", str(seed), "add", "version.txt")
    git(env, "-C", str(seed), "commit", "-m", "synthetic candidate")
    git(env, "init", "--bare", str(remote))
    git(env, "-C", str(seed), "push", remote.as_uri(), "baseline", "candidate")
    git(env, "-C", str(remote), "symbolic-ref", "HEAD", "refs/heads/candidate")
    git(env, "-C", str(remote), "update-ref", "-d", "refs/heads/baseline")
    git(env, "-C", str(remote), "config", "uploadpack.allowAnySHA1InWant", "true")
    git(env, "-C", str(remote), "config", "uploadpack.allowFilter", "true")
    git(env, "clone", "--depth=1", "--filter=tree:0", remote.as_uri(), str(candidate))
    # Enumerate stored objects; looking up a missing SHA can trigger a lazy fetch.
    local_objects = git(
        env, "-C", str(candidate), "cat-file", "--batch-all-objects", "--batch-check"
    )
    assert baseline not in {line.split()[0] for line in local_objects.splitlines()}
    assert baseline not in git(env, "-C", str(remote), "show-ref")
    (candidate / "candidate-only.txt").write_text("synthetic dirty workspace\n", encoding="utf-8")
    runner = tmp_path / "runner"
    runner.mkdir()
    # Git rewrites only this canonical public URL to the local bare fixture; all other
    # protocols are prohibited. The extracted workflow's Git commands remain unchanged.
    env.update(
        GITHUB_WORKSPACE=str(candidate),
        RUNNER_TEMP=str(runner),
        GIT_CONFIG_COUNT="1",
        GIT_CONFIG_KEY_0=f"url.{remote.as_uri()}.insteadOf",
        GIT_CONFIG_VALUE_0=CANONICAL,
    )
    return env, candidate, baseline


def execute_setup(
    shell: str, env: dict[str, str], candidate: Path, baseline: str
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("bash")
    assert executable is not None
    shell = shell.replace(f"baseline={BASELINE}\n", f"baseline={baseline}\n", 1)
    shell += 'touch "$RUNNER_TEMP/parent-build-started"\n'
    return run(
        [executable, "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", shell], env, candidate
    )


@pytest.mark.parametrize("step", PARENT_STEPS)
def test_parent_fetches_unadvertised_baseline_without_borrowing_candidate(
    tmp_path: Path, step: str
) -> None:
    env, candidate, baseline = fixture(tmp_path)
    before = tree_hashes(candidate)
    result = execute_setup(parent_setup(step), env, candidate, baseline)
    assert result.returncode == 0, result.stderr
    parent = Path(env["RUNNER_TEMP"]) / "gsip-app2b-parent"
    assert git(env, "-C", str(parent), "rev-parse", "HEAD") == baseline
    assert git(env, "-C", str(parent), "config", "--get", "remote.origin.url") == CANONICAL
    assert (parent / "version.txt").read_text() == "synthetic baseline\n"
    assert not (parent / "candidate-only.txt").exists()
    assert not (parent / ".git/objects/info/alternates").exists()
    assert tree_hashes(candidate) == before
    assert (Path(env["RUNNER_TEMP"]) / "parent-build-started").exists()


@pytest.mark.parametrize("step", PARENT_STEPS)
def test_missing_baseline_stops_before_parent_build(tmp_path: Path, step: str) -> None:
    env, candidate, _ = fixture(tmp_path)
    before = tree_hashes(candidate)
    result = execute_setup(parent_setup(step), env, candidate, "f" * 40)
    assert result.returncode != 0
    assert tree_hashes(candidate) == before
    assert not (Path(env["RUNNER_TEMP"]) / "parent-build-started").exists()


@pytest.mark.parametrize("step", PARENT_STEPS)
def test_explicit_parent_fetch_is_needed_for_unadvertised_baseline(
    tmp_path: Path, step: str
) -> None:
    env, candidate, baseline = fixture(tmp_path)
    shell = parent_setup(step)
    fetch_lines = [line for line in shell.splitlines() if " fetch --no-tags origin " in line]
    assert len(fetch_lines) == 1
    shell = shell.replace(fetch_lines[0] + "\n", "")
    result = execute_setup(shell, env, candidate, baseline)
    assert result.returncode != 0
    assert not (Path(env["RUNNER_TEMP"]) / "parent-build-started").exists()


@pytest.mark.parametrize("step", PARENT_STEPS)
def test_exact_head_readback_rejects_a_different_checkout(tmp_path: Path, step: str) -> None:
    env, candidate, baseline = fixture(tmp_path)
    shell = parent_setup(step).replace(
        'checkout --detach "$baseline"', "checkout --detach refs/remotes/origin/candidate"
    )
    result = execute_setup(shell, env, candidate, baseline)
    assert result.returncode != 0
    assert not (Path(env["RUNNER_TEMP"]) / "parent-build-started").exists()
