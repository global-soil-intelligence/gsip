from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipeline.library import InstrumentReflectance, _unique_fields

CORPUS = json.loads(
    (
        Path(__file__).parents[1] / "packages/schema/tests/fixtures/library-intake-conformance.json"
    ).read_text()
)


@pytest.mark.parametrize("case", CORPUS["instrument_cases"], ids=lambda case: case["name"])
def test_shared_instrument_contract_corpus(case: dict[str, Any]) -> None:
    def validate() -> InstrumentReflectance:
        return InstrumentReflectance.model_validate(
            json.loads(case["raw"], object_pairs_hook=_unique_fields)
        )

    if case["valid"]:
        assert validate().kind == "instrument_reflectance"
    else:
        with pytest.raises(ValueError):
            validate()


@pytest.mark.parametrize("case", CORPUS["band_count_cases"])
def test_shared_instrument_band_count_bounds(case: dict[str, Any]) -> None:
    count = case["count"]
    candidate = json.loads(CORPUS["instrument_cases"][0]["raw"]) | {
        "wavelength_nm": [200.0 + i for i in range(count)],
        "reflectance": [0.4] * count,
        "uncertainty": [0.01] * count,
    }
    if case["valid"]:
        assert len(InstrumentReflectance.model_validate(candidate).wavelength_nm) == count
    else:
        with pytest.raises(ValueError):
            InstrumentReflectance.model_validate(candidate)
