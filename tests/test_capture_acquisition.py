"""WP-COLLECT-6: the capture standard's five testable rules, named S1 to S5 here.

S1  Phone photos are RGB observations, never called spectra; no soil-property estimate.
S2  Every capture record made under the standard carries the acquisition metadata.
S3  No detected reference card means uncalibrated, never mixed with calibrated in exports.
S4  The colour normalisation is deterministic: same image and card, same values.
S5  Contracts stay backward compatible: optional field, bumped version, old records validate.

Every input is fictional or generated. No printed card and no phone was used."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
import pytest
from test_card_pipeline import flat_soil, photographed, with_a6, with_node
from test_library import record as library_record
from test_qa import jpeg

from pipeline.capture_acquisition import (
    ACQUISITION_VERSION,
    CARD_EDITIONS,
    CaptureAcquisition,
    assert_unmixed,
    calibration_digest,
    calibration_status_of,
    card_gate,
    gate_from_qa,
    parse_acquisition,
    partition_by_calibration,
    with_pipeline_findings,
    write_partitions,
)
from pipeline.export import FORBIDDEN_PUBLIC_KEYS, assert_public_record
from pipeline.library import LibraryRecord, PrivateLibrary, encoded
from pipeline.phone_optics import extract_phone_record
from pipeline.qa_cards import evaluate_photo_with_cards

ROOT = Path(__file__).parents[1]
CORPUS = json.loads(
    (ROOT / "packages/schema/tests/fixtures/capture-acquisition-conformance.json").read_text()
)
CASES: dict[str, dict[str, Any]] = {case["name"]: case for case in CORPUS["acquisition_cases"]}


def block(name: str = "complete-calibrated-fictional") -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(CASES[name]["raw"])
    return loaded


def camera_v2(number: int = 1, name: str = "complete-calibrated-fictional") -> dict[str, object]:
    return library_record(number) | {
        "schema_version": "gsip-library-v2",
        "acquisition": block(name),
    }


# ---- the shared corpus ---------------------------------------------------------------------


@pytest.mark.parametrize("case", CORPUS["acquisition_cases"], ids=lambda case: case["name"])
def test_shared_acquisition_corpus(case: dict[str, Any]) -> None:
    if case["valid"]:
        assert parse_acquisition(case["raw"]).schema_version == ACQUISITION_VERSION
    else:
        with pytest.raises(ValueError, match="^invalid capture acquisition$"):
            parse_acquisition(case["raw"])


def test_rejections_are_generic_and_bounded() -> None:
    secret = block() | {"device": block()["device"] | {"model": "SECRET\nVALUE"}}
    with pytest.raises(ValueError) as caught:
        parse_acquisition(json.dumps(secret))
    assert "SECRET" not in str(caught.value) and caught.value.__cause__ is None
    with pytest.raises(ValueError):
        parse_acquisition(b" " * 8_001)
    with pytest.raises(ValueError):
        parse_acquisition('{"lighting":"shade","lighting":"overcast"}')


# ---- S1: RGB observations, never spectra, no soil-property estimate -------------------------


def test_s1_the_block_is_an_rgb_photo_and_holds_no_spectrum_or_soil_property() -> None:
    assert parse_acquisition(CASES["complete-calibrated-fictional"]["raw"]).observation_kind == (
        "rgb_photo"
    )
    for name in ("called-a-spectrum", "soil-property-estimate-refused", "wavelengths-refused"):
        assert not CASES[name]["valid"]
    names = json.dumps(CaptureAcquisition.model_json_schema()).lower()
    for word in ("spectr", "wavelength", "reflectance", "soc", "clay", "munsell", "estimate"):
        assert word not in names, word


STANDARD_DOCS = (
    "docs/capture-protocol.md",
    "docs/field-kit.md",
    "docs/validation-plan.md",
)
STANDARD_COPY = (
    *STANDARD_DOCS,
    "apps/capture-pwa/src/captureStandard.ts",
    "apps/capture-pwa/src/CaptureChecklist.tsx",
    "packages/schema/src/captureAcquisition.ts",
    "scripts/list_photo_galleries.py",
)
# A sentence may use the word only to say what a phone photo is not, or to name an instrument.
_DENIAL = re.compile(
    r"\b(not|never|no|neither|nor|without|instrument|spectrometer|library)\b", re.IGNORECASE
)
_SPECTRAL = re.compile(r"spectr(?:um|a|al)\b", re.IGNORECASE)
_CLAIM = re.compile(
    r"\b(predicts?|estimates?|measures?|determines?|detects?)\s+(?:the\s+)?(?:soil\s+)?"
    r"(organic carbon|carbon|soc|texture|clay|sand|silt|ph|nitrogen|fertility|moisture)\b",
    re.IGNORECASE,
)


@pytest.mark.parametrize("path", STANDARD_COPY)
def test_s1_no_copy_calls_a_phone_photo_a_spectrum_or_claims_a_soil_property(path: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    assert not re.search(r"soil[\s-]+test", text, re.IGNORECASE)
    for sentence in re.split(r"(?<=[.!?])\s+|\n\s*\n|\n[-*|#] ?", text):
        if _SPECTRAL.search(sentence):
            assert _DENIAL.search(sentence), f"{path}: {sentence.strip()[:120]}"
        assert not _CLAIM.search(sentence) or _DENIAL.search(sentence), (
            f"{path}: {sentence.strip()[:120]}"
        )


@pytest.mark.parametrize("path", STANDARD_DOCS)
def test_s1_each_document_states_the_limit_in_words(path: str) -> None:
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert "RGB observation" in text
    assert re.search(r"not (?:a )?(?:wavelength-resolved )?spectr", text)
    assert re.search(r"no soil-property estimate", text, re.IGNORECASE)


# ---- S2: every record under the standard carries the acquisition metadata -------------------

REQUIRED = {
    "device": {"make", "model", "os_name", "os_version", "app_version"},
    "camera": {
        "exposure_time_s",
        "iso",
        "exposure",
        "white_balance",
        "hdr",
        "filters",
        "flash",
        "angle",
        "distance_cm",
        "field_of_view_cm",
    },
    "reference_card": {"detection", "card_id", "card_version"},
    "location": {"consent", "h3_r9"},
}
REQUIRED_TOP = {"lighting", "captured_at", "calibration_status", "replicate_count", "procedure"}


def test_s2_every_listed_field_is_required_and_unknown_is_written_out() -> None:
    whole = block()
    for group, fields in REQUIRED.items():
        assert set(whole[group]) == fields
        for name in fields:
            broken = copy.deepcopy(whole)
            del broken[group][name]
            with pytest.raises(ValueError):
                parse_acquisition(json.dumps(broken))
    for name in REQUIRED_TOP | set(REQUIRED):
        broken = copy.deepcopy(whole)
        del broken[name]
        with pytest.raises(ValueError):
            parse_acquisition(json.dumps(broken))
    unknown = parse_acquisition(CASES["every-unknown-explicit"]["raw"])
    assert unknown.camera.iso is None and unknown.lighting == "unknown"


def test_s2_location_is_recorded_only_with_consent_and_never_as_a_point() -> None:
    assert parse_acquisition(CASES["location-with-consent"]["raw"]).location.h3_r9 is not None
    for name in ("location-without-consent", "precise-coordinates-refused"):
        with pytest.raises(ValueError):
            parse_acquisition(CASES[name]["raw"])
    fields = set(CaptureAcquisition.model_json_schema()["$defs"]["Location"]["properties"])
    assert fields == {"consent", "h3_r9"}


def test_s2_the_block_is_private_and_never_in_a_public_row() -> None:
    assert "acquisition" in FORBIDDEN_PUBLIC_KEYS
    with pytest.raises(ValueError):
        assert_public_record({"id": "x", "photos": [{"acquisition": block()}]})


def test_s2_the_extractor_keeps_the_block_and_fills_what_the_photo_states() -> None:
    template = LibraryRecord.model_validate(camera_v2(name="every-unknown-explicit"))
    made = extract_phone_record(jpeg(with_node(flat_soil(2))), template)
    assert made.acquisition is not None
    assert set(made.acquisition.model_dump()) == set(block())


def test_s2_the_photo_s_own_metadata_fills_only_what_was_left_unknown() -> None:
    metadata: dict[str, float | int | str] = {
        "exposure_time_s": 0.004,
        "iso": 200,
        "make": " Example Maker ",
        "model": "Phone 2",
        "color_space": "srgb",
    }
    unknown = parse_acquisition(CASES["every-unknown-explicit"]["raw"])
    filled = with_pipeline_findings(
        unknown, card_outlines=0, edition=None, camera_metadata=metadata
    )
    assert (filled.camera.exposure_time_s, filled.camera.iso) == (0.004, 200)
    assert (filled.device.make, filled.device.model) == ("Example Maker", "Phone 2")
    stated = parse_acquisition(CASES["complete-calibrated-fictional"]["raw"])
    kept = with_pipeline_findings(stated, card_outlines=0, edition=None, camera_metadata=metadata)
    assert (kept.camera.exposure_time_s, kept.camera.iso) == (0.008, 100)
    assert (kept.device.make, kept.device.model) == ("Example", "Phone 1")
    odd: dict[str, float | int | str] = {
        "exposure_time_s": 900.0,
        "iso": 100.5,
        "make": "two\nlines",
        "model": "",
    }
    refused = with_pipeline_findings(unknown, card_outlines=0, edition=None, camera_metadata=odd)
    assert refused.camera.exposure_time_s is None and refused.camera.iso is None
    assert refused.device.make is None and refused.device.model is None


# ---- S3: no detected card means uncalibrated, never mixed in an export ----------------------


def test_s3_only_one_detected_identified_card_is_calibrated() -> None:
    assert card_gate("one", "gsip-node", "v1")[0] == "calibrated"
    for finding in (
        ("none", None, None),
        ("not_run", None, None),
        ("multiple", None, None),
        ("one", None, None),
        ("one", "gsip-node", None),
        ("none", "gsip-node", "v1"),
        ("not_run", "gsip-a6", "v1"),
        ("one", "Not A Card Id", "v1"),
    ):
        status, card = card_gate(*finding)
        assert status == "uncalibrated"
        assert card.card_id is None and card.card_version is None
    assert gate_from_qa(card_outlines=0, edition=None)[0] == "uncalibrated"
    assert gate_from_qa(card_outlines=2, edition=None)[1].detection == "multiple"
    assert gate_from_qa(card_outlines=1, edition=None)[0] == "uncalibrated"
    for edition, (card_id, version) in CARD_EDITIONS.items():
        status, card = gate_from_qa(card_outlines=1, edition=edition)
        assert (status, card.card_id, card.card_version) == ("calibrated", card_id, version)


def test_s3_the_pipeline_overrules_a_client_that_claims_a_card() -> None:
    claimed = LibraryRecord.model_validate(camera_v2())
    assert claimed.acquisition is not None
    assert claimed.acquisition.calibration_status == "calibrated"
    no_card = extract_phone_record(jpeg(flat_soil(3)), claimed)
    assert no_card.acquisition is not None
    assert no_card.acquisition.calibration_status == "uncalibrated"
    assert no_card.acquisition.reference_card.model_dump() == {
        "detection": "none",
        "card_id": None,
        "card_version": None,
    }
    two = extract_phone_record(
        jpeg(with_node(with_node(flat_soil(4), x=600, y=80), x=600, y=500)), claimed
    )
    assert two.acquisition is not None and two.acquisition.calibration_status == "uncalibrated"
    one = extract_phone_record(jpeg(with_node(flat_soil(5))), claimed)
    assert one.acquisition is not None
    assert one.acquisition.calibration_status == "calibrated"
    assert one.acquisition.reference_card.card_id == "gsip-node"
    # The RGB summary itself stays uncalibrated sRGB whatever the capture's status (SPEC L1).
    assert one.measurement.kind == "camera_rgb"
    assert one.measurement.calibration_status == "uncalibrated"


def test_s3_findings_never_keep_a_claimed_card() -> None:
    claimed = parse_acquisition(CASES["complete-calibrated-fictional"]["raw"])
    found = with_pipeline_findings(claimed, card_outlines=0, edition=None)
    assert found.calibration_status == "uncalibrated" and found.reference_card.card_id is None


def test_s3_partitions_never_mix_and_legacy_records_are_uncalibrated(tmp_path: Path) -> None:
    calibrated = LibraryRecord.model_validate(camera_v2(1))
    no_card = LibraryRecord.model_validate(camera_v2(2, "no-card-uncalibrated"))
    legacy = LibraryRecord.model_validate(library_record(3))
    as_dict = {"acquisition": block("two-cards-uncalibrated")}
    assert calibration_status_of(legacy) == "uncalibrated"
    parts = partition_by_calibration([calibrated, no_card, legacy, as_dict])
    assert parts["calibrated"] == [calibrated]
    assert parts["uncalibrated"] == [no_card, legacy, as_dict]
    assert_unmixed(parts["calibrated"], "calibrated")
    assert_unmixed(parts["uncalibrated"], "uncalibrated")
    for mixed, status in (
        ([calibrated, legacy], "calibrated"),
        ([no_card, calibrated], "uncalibrated"),
    ):
        with pytest.raises(ValueError, match="must not be mixed"):
            assert_unmixed(mixed, status)  # type: ignore[arg-type]

    target = tmp_path / "export"
    assert write_partitions([calibrated, no_card, legacy], target) == {
        "calibrated": 1,
        "uncalibrated": 2,
    }
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    seen: dict[str, set[str]] = {}
    for name in ("calibrated", "uncalibrated"):
        path = target / f"{name}.jsonl"
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        seen[name] = {row["measurement_id"] for row in rows}
        assert all(calibration_status_of(row) == name for row in rows)
    assert seen == {
        "calibrated": {str(UUID(int=1))},
        "uncalibrated": {str(UUID(int=2)), str(UUID(int=3))},
    }
    with pytest.raises(FileExistsError):
        write_partitions([calibrated], target)


def test_s3_a_tampered_status_cannot_enter_the_calibrated_partition() -> None:
    forged = block("no-card-uncalibrated") | {"calibration_status": "calibrated"}
    with pytest.raises(ValueError):
        partition_by_calibration([{"acquisition": forged}])


# ---- S4: the colour normalisation is deterministic ------------------------------------------

# Pinned on generated photographs under the locked environment (uv.lock). These are not
# measurements of any printed card or phone.
NODE_DIGEST = "d6f502661126da06bb2eb1f82826c7625da3ab62e2b088fc5baf4b7ce2601700"
A6_DIGEST = "2d665beed88e7d887627b099143b1452e456f3a7c125778db8242543acdfd2b7"
NO_CARD_DIGEST = hashlib.sha256(b"null").hexdigest()


def _digest(image: Any) -> tuple[str, str]:
    result = evaluate_photo_with_cards(jpeg(image), accuracy_m=10)
    return result.calibration_status, calibration_digest(result.card_color_correction)


def test_s4_the_same_image_and_card_give_the_same_values_and_a_fixed_hash() -> None:
    node = photographed(with_node(flat_soil(7)), (1.0, 0.86, 0.77), 0.8)
    a6 = photographed(with_a6(flat_soil(7)), (0.77, 0.9, 1.0), 1.25)
    first, second = _digest(node), _digest(node.copy())
    assert first == second == ("calibrated", NODE_DIGEST)
    assert _digest(a6) == _digest(a6.copy()) == ("calibrated", A6_DIGEST)
    assert _digest(flat_soil(7)) == ("uncalibrated", NO_CARD_DIGEST)
    assert len({NODE_DIGEST, A6_DIGEST, NO_CARD_DIGEST}) == 3


def test_s4_another_image_or_another_card_changes_the_hash() -> None:
    base = _digest(with_node(flat_soil(7)))[1]
    darker = (flat_soil(7).astype(np.float64) * 0.7).astype(np.uint8)
    assert _digest(with_node(darker))[1] != base
    assert _digest(photographed(with_node(flat_soil(7)), (1.0, 0.85, 0.7), 1.0))[1] != base
    assert _digest(with_a6(flat_soil(7)))[1] != base


def test_s4_the_digest_ignores_key_order_and_float_noise_below_the_sixth_place() -> None:
    record = {"soil_rgb": [141.2, 104.0, 77.1], "normalised": True, "matrix": [[1.0000001, 0.0]]}
    same = {"matrix": [[1.0000002, 0.0]], "normalised": True, "soil_rgb": [141.2, 104.0, 77.1]}
    assert calibration_digest(record) == calibration_digest(same)
    assert calibration_digest(record | {"normalised": False}) != calibration_digest(record)
    with pytest.raises(ValueError):
        calibration_digest({"soil_rgb": float("nan")})


# ---- S5: backward compatible contracts ------------------------------------------------------

# SHA-256 of a version-1 camera record as stored before this package. It must never change:
# a store written by an earlier version compares these bytes on re-import.
V1_CAMERA_SHA256 = "7f37ac8ca4bae1ac69a216dce188272fcf7bfb70275403c6c294823a3e2a207b"


def test_s5_a_version_1_record_validates_and_is_stored_as_the_same_bytes(tmp_path: Path) -> None:
    old = LibraryRecord.model_validate(library_record(1))
    assert old.schema_version == "gsip-library-v1" and old.acquisition is None
    data = encoded(old)
    assert b"acquisition" not in data
    assert hashlib.sha256(data).hexdigest() == V1_CAMERA_SHA256
    library = PrivateLibrary(tmp_path / "store")
    assert library.add(old) is True
    # Identical re-import stays idempotent: the stored bytes still match.
    assert library.add(LibraryRecord.model_validate(library_record(1))) is False
    instrument = LibraryRecord.model_validate(library_record(2, kind="instrument_reflectance"))
    assert library.add(instrument) is True


def test_s5_the_new_field_is_optional_and_belongs_to_version_2_camera_records(
    tmp_path: Path,
) -> None:
    without = library_record(1) | {"schema_version": "gsip-library-v2"}
    assert LibraryRecord.model_validate(without).acquisition is None
    with_block = LibraryRecord.model_validate(camera_v2(2))
    assert with_block.acquisition is not None
    library = PrivateLibrary(tmp_path / "store")
    assert library.add(with_block) is True and library.add(with_block) is False
    assert library.records()[0].acquisition == with_block.acquisition
    # A version-1 record cannot carry the version-2 member.
    with pytest.raises(ValueError):
        LibraryRecord.model_validate(library_record(3) | {"acquisition": block()})
    # An instrument record has no camera to describe.
    with pytest.raises(ValueError):
        LibraryRecord.model_validate(
            library_record(4, kind="instrument_reflectance")
            | {"schema_version": "gsip-library-v2", "acquisition": block()}
        )
    with pytest.raises(ValueError):
        LibraryRecord.model_validate(library_record(5) | {"schema_version": "gsip-library-v3"})


def test_s5_the_published_schema_lists_both_versions_and_does_not_require_the_field() -> None:
    schema = LibraryRecord.model_json_schema()
    assert schema["properties"]["schema_version"]["enum"] == ["gsip-library-v1", "gsip-library-v2"]
    assert "acquisition" not in schema["required"]
    assert set(schema["required"]) >= {"schema_version", "measurement", "labels", "context"}
