"""Prepare a separately reviewed invited browser artifact; never deploy it."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "toxldjgwkxtneoqsazym"
ORIGIN = "https://globalsoilintelligence.com"
API = f"https://{PROJECT}.supabase.co"
VERSION = "gsip-invited-browser-v1"
REVIEW = "gsip-collection-review.json"
MAX_BYTES = 800 * 1024 * 1024
EXTENSIONS = {
    ".html",
    ".js",
    ".css",
    ".json",
    ".webmanifest",
    ".svg",
    ".txt",
    ".md",
    ".pdf",
    ".pmtiles",
    ".wasm",
    ".png",
    ".webp",
    ".jpg",
    ".jpeg",
    ".ico",
    ".xml",
}


def read_json(path: Path) -> Any:
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Review metadata too large")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate metadata field")
            result[key] = value
        return result

    def constant(value: str) -> Any:
        raise ValueError("Nonfinite metadata refused")

    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_constant=constant)


def browser_key_allowed(value: str) -> bool:
    if re.fullmatch(r"sb_publishable_[A-Za-z0-9_-]{16,}", value):
        return True
    if len(value) > 8192 or value.count(".") != 2:
        return False
    try:
        payload = value.split(".")[1]
        decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return isinstance(decoded, dict) and decoded.get("role") == "anon"
    except (ValueError, UnicodeError):
        return False


def assert_reviewed_source(git: str, commit: str) -> None:
    actual = subprocess.check_output([git, "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()  # noqa: S603
    status = subprocess.check_output(  # noqa: S603 - fixed git command, no shell
        [git, "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True
    )  # noqa: S603
    if actual != commit or status.strip() or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Reviewed source must be exact and clean")


def validate_activation(value: Any, commit: str) -> dict[str, Any]:
    expected = {
        "version": VERSION,
        "mode": "invited_private",
        "capture_live": True,
        "library_intake_live": True,
        "publication_held": True,
        "source_commit": commit,
        "target": {"project_ref": PROJECT, "supabase_url": API, "site_origin": ORIGIN},
    }
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not isinstance(value, dict):
        raise ValueError("Invalid reviewed source")
    # JSON bools must not be accepted as integers or strings by Python equality.
    if value != expected or any(
        type(value.get(k)) is not bool
        for k in ("capture_live", "library_intake_live", "publication_held")
    ):
        raise ValueError("Invited activation target, mode or source mismatch")
    return expected


def inventory(directory: Path, *, omit_review: bool = False) -> dict[str, str]:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Artifact directory required")
    files: dict[str, str] = {}
    total = 0
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory).as_posix()
        if path.is_symlink():
            raise ValueError("Artifact symlinks refused")
        if path.is_dir():
            continue
        if (
            not path.is_file()
            or path.suffix not in EXTENSIONS
            or any(p.startswith(".") for p in path.relative_to(directory).parts)
        ):
            raise ValueError("Unexpected artifact file")
        total += path.stat().st_size
        if total > MAX_BYTES:
            raise ValueError("Review artifact exceeds the site size limit")
        if omit_review and relative == REVIEW:
            continue
        with path.open("rb") as source:
            files[relative] = hashlib.file_digest(source, "sha256").hexdigest()
    return files


def verify_review(directory: Path, commit: str) -> dict[str, Any]:
    activation = validate_activation(read_json(directory / "capture/gsip-activation.json"), commit)
    record = read_json(directory / REVIEW)
    if not isinstance(record, dict):
        raise ValueError("Review metadata object required")
    validate_activation(record.get("activation"), commit)
    expected = {
        "version": "gsip-collection-review-v1",
        "source_commit": commit,
        "activation": activation,
        "files": inventory(directory, omit_review=True),
    }
    if record != expected:
        raise ValueError("Review artifact inventory mismatch")
    return expected


def package_review(closed: Path, pilot: Path, output: Path, commit: str) -> dict[str, Any]:
    inventory(closed)
    inventory(pilot)
    closed_receipt = read_json(closed / "capture/gsip-activation.json")
    if closed_receipt != {"capture_live": False, "library_intake_live": False} or any(
        type(v) is not bool for v in closed_receipt.values()
    ):
        raise ValueError("Base Pages artifact must stay closed")
    activation = validate_activation(read_json(pilot / "gsip-activation.json"), commit)
    if not (pilot / "index.html").is_file():
        raise ValueError("Pilot entry missing")
    target = output.resolve()
    if (
        output.exists()
        or output.is_symlink()
        or any(
            target.is_relative_to(p.resolve()) or p.resolve().is_relative_to(target)
            for p in (closed, pilot)
        )
    ):
        raise ValueError("Review output must be new and separate from build inputs")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="gsip-review-", dir=output.parent) as temp:
        staged = Path(temp) / "site"
        shutil.copytree(closed, staged)
        shutil.rmtree(staged / "capture")
        shutil.copytree(pilot, staged / "capture")
        record = {
            "version": "gsip-collection-review-v1",
            "source_commit": commit,
            "activation": activation,
            "files": inventory(staged),
        }
        (staged / REVIEW).write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
        verify_review(staged, commit)
        staged.rename(output)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed-sha", required=True)
    parser.add_argument("--project-ref", required=True, choices=[PROJECT])
    parser.add_argument("--site-origin", required=True, choices=[ORIGIN])
    parser.add_argument("--prepare-review-artifact", required=True, action="store_true")
    args = parser.parse_args()
    git, pnpm = shutil.which("git"), shutil.which("pnpm")
    if not git or not pnpm:
        raise ValueError("Pinned build tools required")
    commit = subprocess.check_output([git, "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()  # noqa: S603
    assert_reviewed_source(git, args.reviewed_sha)
    if (ROOT / "_collection_capture").exists() or (ROOT / "_collection_capture").is_symlink():
        raise ValueError("Fresh isolated collection output required")
    # Do not accept inherited activation/mode/target values; closed build first.
    original = dict(os.environ)
    key = original.get("VITE_SUPABASE_PUBLISHABLE_KEY", "")
    if not browser_key_allowed(key):
        raise ValueError("Browser-safe publishable configuration required")
    env = {k: v for k, v in original.items() if not k.startswith("VITE_")}
    env.update(
        {
            k: original[k]
            for k in (
                "VITE_TERMS_URL",
                "VITE_PRIVACY_URL",
                "VITE_SAMPLING_RULES_URL",
                "VITE_PRIOR_TILES_BASE",
                "VITE_DATASET_URL",
                "VITE_GSIP_PUBLIC_API",
            )
            if k in original
        }
    )
    env.update(
        VITE_SUPABASE_URL=API,
        VITE_SUPABASE_PUBLISHABLE_KEY=key,
        VITE_CAPTURE_LIVE="false",
        VITE_LIBRARY_INTAKE_LIVE="false",
        GITHUB_SHA=commit,
    )
    subprocess.run([pnpm, "build:pages"], cwd=ROOT, env=env, check=True)  # noqa: S603
    assert_reviewed_source(git, commit)
    env.update(
        VITE_CAPTURE_LIVE="true",
        VITE_LIBRARY_INTAKE_LIVE="true",
        VITE_COLLECTION_MODE="invited_private",
        VITE_COLLECTION_PROJECT_REF=PROJECT,
        VITE_COLLECTION_SITE_ORIGIN=ORIGIN,
    )
    subprocess.run(  # noqa: S603 - fixed pinned build command, no shell
        [pnpm, "--filter", "@gsip/capture-pwa", "exec", "vite", "build", "--mode", "invited-pilot"],
        cwd=ROOT,
        env=env,
        check=True,
    )  # noqa: S603
    assert_reviewed_source(git, commit)
    output = ROOT / "_collection_review"
    package_review(ROOT / "_site", ROOT / "_collection_capture", output, commit)
    assert_reviewed_source(git, commit)
    print("Invited review artifact prepared; no deployment or activation performed.")


if __name__ == "__main__":
    main()
