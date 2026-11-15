"""GSIP Node Card v1: a credit-card-size reference for people who order a printed card.

Kept apart from ``card.design`` on purpose: the photo-privacy calibration binds the bytes of
``card/design.py`` and ``card/validate.py``, so the A6 card's files do not change here.

The patch values are digital targets, not a claim about any print. A print run is characterised
only when one card from it has been measured; until then a node card is no better known than a
home print.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from card.design import PATCHES as A6_PATCHES

# ISO/IEC 7810 ID-1 (CR80), landscape.
CARD_WIDTH_MM = 85.6
CARD_HEIGHT_MM = 53.98
SAFE_MARGIN_MM = 3.0

# A different marker from the A6 card (ID 7), so a detector knows which layout it sees. Four IDs
# in this dictionary (8, 9, 17 and 47) read as themselves in a mirror; 12 does not, so a mirrored
# photograph is refused and never read as a card.
MARKER_ID = 12
MARKER_X_MM = 5.0
MARKER_Y_MM = 12.0
MARKER_SIZE_MM = 24.0
# ArUco needs a light border at least one module wide; a 4x4 marker has six modules a side.
MARKER_QUIET_MM = MARKER_SIZE_MM / 6

PATCH_SIZE_MM = 10.0
RAMP_WIDTH_MM = 10.0
RAMP_STEP_MM = 6.6

SCALE_X_MM = 5.0
SCALE_Y_MM = 47.8
TEXT_BASELINE_MM = 50.2
SCALE_LENGTH_MM = 20.0


@dataclass(frozen=True)
class NodePatch:
    name: str
    rgb: tuple[int, int, int]
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float


def _colour_patches() -> tuple[NodePatch, ...]:
    """The A6 card's nine colours, same names and values, in a tighter three-by-three grid."""

    columns = (34.0, 45.5, 57.0)
    rows = (11.0, 22.5, 34.0)
    return tuple(
        NodePatch(
            patch.name,
            patch.rgb,
            columns[index % 3],
            rows[index // 3],
            PATCH_SIZE_MM,
            PATCH_SIZE_MM,
        )
        for index, patch in enumerate(A6_PATCHES)
    )


# A five-step neutral ramp. Its ends and middle repeat the black, grey and white patches, so a
# reading can be checked against itself; the other two steps add tones the A6 card lacks.
RAMP_VALUES = (28, 78, 128, 180, 232)
RAMP_X_MM = 70.5
RAMP_Y_MM = 11.0

PATCHES = _colour_patches()
RAMP = tuple(
    NodePatch(
        f"ramp_{index}",
        (value, value, value),
        RAMP_X_MM,
        RAMP_Y_MM + index * RAMP_STEP_MM,
        RAMP_WIDTH_MM,
        RAMP_STEP_MM,
    )
    for index, value in enumerate(RAMP_VALUES)
)
ALL_PATCHES = PATCHES + RAMP

# A run code names a print run: every card in the run carries the same code. Two letters, two
# digits, a dash and four digits.
RUN_CODE = re.compile(r"[A-Z]{2}[0-9]{2}-[0-9]{4}")
UNCHARACTERISED_RUN = "HOME-0000"

# Pairs that are printed with nearly the same value (white differs by up to 12 levels).
# A reading in which they disagree is not trusted.
REPEATED = (("black", "ramp_0"), ("neutral_gray", "ramp_2"), ("white", "ramp_4"))


def check_run_code(run: str) -> str:
    """Return a valid run code or refuse.

    The format has no room for an e-mail address or a full name. It cannot stop someone choosing
    initials and a year, or numbering cards one by one: whoever orders a run must give every card
    in it the same code."""

    if not isinstance(run, str) or (run != UNCHARACTERISED_RUN and not RUN_CODE.fullmatch(run)):
        raise ValueError("run code must look like AB12-0001: 2 letters, 2 digits, a dash, 4 digits")
    return run
