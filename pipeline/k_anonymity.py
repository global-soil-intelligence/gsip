"""k-anonymous publication cells (SPEC I7).

Each observation is published at the finest H3 resolution among 8, 6 and 4 whose published
cell aggregates observations from at least ``k`` distinct contributors. Observations that
qualify at none of them are withheld until they do.

Groups are formed bottom-up and only from observations not already published at a finer
resolution, so every published cell's own members span at least ``k`` contributors. A coarse
cell may overlap finer published cells; its counts cover only the observations assigned to it.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import h3  # type: ignore[import-untyped]

K_ANONYMITY = 3
PUBLISHED_RESOLUTIONS = (8, 6, 4)


@dataclass(frozen=True)
class Observation:
    key: str
    contributor: str
    h3_r8: str
    observed_on: date


@dataclass(frozen=True)
class PublishedCell:
    h3_index: str
    resolution: int
    n_submissions: int
    n_contributors: int
    latest_submission_date: date

    def payload(self) -> dict[str, object]:
        return {
            "h3_index": self.h3_index,
            "latest_submission_date": self.latest_submission_date.isoformat(),
            "n_contributors": self.n_contributors,
            "n_submissions": self.n_submissions,
            "resolution": self.resolution,
        }


@dataclass(frozen=True)
class Assignment:
    cells: tuple[PublishedCell, ...]
    placement: dict[str, tuple[str, int]]
    withheld: tuple[str, ...]


def is_resolution_8_cell(value: str) -> bool:
    return bool(h3.is_valid_cell(value)) and h3.get_resolution(value) == 8


def assign_cells(observations: Iterable[Observation], k: int = K_ANONYMITY) -> Assignment:
    if k < 1:
        raise ValueError("k must be at least 1")
    remaining = sorted(observations, key=lambda observation: observation.key)
    for observation in remaining:
        if not is_resolution_8_cell(observation.h3_r8):
            raise ValueError("observations must carry a valid resolution-8 H3 cell")

    placement: dict[str, tuple[str, int]] = {}
    cells: list[PublishedCell] = []
    for resolution in PUBLISHED_RESOLUTIONS:
        groups: dict[str, list[Observation]] = defaultdict(list)
        for observation in remaining:
            cell = (
                observation.h3_r8
                if resolution == 8
                else str(h3.cell_to_parent(observation.h3_r8, resolution))
            )
            groups[cell].append(observation)
        unplaced: list[Observation] = []
        for cell in sorted(groups):
            members = groups[cell]
            contributors = {member.contributor for member in members}
            if len(contributors) < k:
                unplaced.extend(members)
                continue
            for member in members:
                placement[member.key] = (cell, resolution)
            cells.append(
                PublishedCell(
                    h3_index=cell,
                    resolution=resolution,
                    n_submissions=len(members),
                    n_contributors=len(contributors),
                    latest_submission_date=max(member.observed_on for member in members),
                )
            )
        remaining = sorted(unplaced, key=lambda observation: observation.key)
    return Assignment(
        cells=tuple(cells),
        placement=placement,
        withheld=tuple(observation.key for observation in remaining),
    )
