"""Offline, version-pinned lookup of previously extracted soil-map values."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import h3  # type: ignore[import-untyped]

from ml.pilot import Prior, StrictRecord


class CachedPrior(StrictRecord):
    h3_r8: str
    sampling: Literal["h3_r8_centroid"]
    prior: Prior


def lookup_prior(path: Path, cell: str, source: str, version: str) -> Prior:
    if not h3.is_valid_cell(cell) or h3.get_resolution(cell) != 8:
        raise ValueError("a valid H3 resolution-8 cell is required")
    matches = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = CachedPrior.model_validate(json.loads(line))
        if row.h3_r8 == cell and row.prior.source == source and row.prior.version == version:
            matches.append(row.prior)
    if len(matches) != 1:
        raise ValueError("prior cache requires exactly one matching cell/source/version record")
    return matches[0]
