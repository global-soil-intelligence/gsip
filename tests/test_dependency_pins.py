"""zod is resolved twice: by pnpm for the apps and by Deno for the Edge Functions.

A security update that moves only one of them leaves the other on the old release."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_edge_functions_and_the_schema_package_pin_the_same_zod() -> None:
    package = json.loads((ROOT / "packages/schema/package.json").read_text())
    version = package["dependencies"]["zod"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), "zod must be pinned to an exact version"

    imports = json.loads((ROOT / "supabase/functions/deno.json").read_text())["imports"]
    assert imports["zod"] == f"npm:zod@{version}"

    lock = json.loads((ROOT / "supabase/functions/deno.lock").read_text())
    assert lock["specifiers"][f"npm:zod@{version}"] == version
    assert f"npm:zod@{version}" in lock["workspace"]["dependencies"]
    assert [name for name in lock["npm"] if name.startswith("zod@")] == [f"zod@{version}"]

    pnpm = (ROOT / "pnpm-lock.yaml").read_text()
    locked = re.findall(r"^  zod@([^:\n]+):\n    resolution: \{integrity: ([^}]+)\}", pnpm, re.M)
    assert locked == [(version, lock["npm"][f"zod@{version}"]["integrity"])]
