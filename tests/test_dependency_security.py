"""Exercise the actual CommonJS UUID consumer in the native project generator."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SETUP = """
const { createRequire } = require('node:module');
const capture = createRequire(process.cwd() + '/apps/capture-pwa/package.json');
const cli = createRequire(capture.resolve('@capacitor/cli'));
const xcodePath = cli.resolve('xcode');
const consumer = createRequire(xcodePath);
const uuid = consumer('uuid');
const assert = require('node:assert/strict');
"""


def node_check(code: str) -> None:
    node = shutil.which("node")
    assert node is not None, "Node is required by this repository's CI"
    result = subprocess.run(  # noqa: S603 - static test program; no user data or shell
        [node, "-e", SETUP + code], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("method", ["v3", "v5"])
def test_uuid_rejects_small_output_buffer(method: str) -> None:
    node_check(
        f"assert.throws(() => uuid.{method}('synthetic-boundary', "
        "'6ba7b810-9dad-11d1-80b4-00c04fd430c8', new Uint8Array(15)), RangeError);"
    )


def test_commonjs_xcode_generator_works_with_patched_uuid() -> None:
    node_check("""
const project = consumer(xcodePath).project('synthetic-no-file-read.pbxproj');
project.hash = { project: { objects: {} } };
const ids = Array.from({length: 100}, () => project.generateUuid());
assert(ids.every(id => /^[0-9A-F]{24}$/.test(id)));
assert.equal(new Set(ids).size, 100);
""")
