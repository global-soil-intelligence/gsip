"""Policy contracts keep the three reader-facing plans aligned with owner decisions."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
POLICY_DOCS = ("SPEC.md", "BUILD_ORDER.md", "PHOTO_PRIVACY_SCREENING.md")


def text(name: str) -> str:
    return re.sub(r"\s+", " ", (ROOT / "docs" / name).read_text()).lower()


def spec_section(number: str) -> str:
    source = (ROOT / "docs" / "SPEC.md").read_text()
    start = re.search(rf"^#{{2,3}} {re.escape(number)}[. :]", source, re.MULTILINE)
    assert start is not None, f"SPEC section {number} must exist"
    level = len(start.group().split()[0])
    following = re.search(rf"^#{{2,{level}}} ", source[start.end() :], re.MULTILINE)
    end = start.end() + following.start() if following else len(source)
    return re.sub(r"\s+", " ", source[start.start() : end]).lower()


def test_section_11_gates_photo_publication_on_deployment_and_owner_calibration() -> None:
    launch = spec_section("11")
    assert "photo-publication gate" in launch
    assert all(word in launch for word in ("wp-6f", "deployed", "justin", "calibration"))
    assert "structured data only" in launch
    assert "no photo publication" in launch


@pytest.mark.parametrize("name", POLICY_DOCS)
def test_plans_keep_releases_data_only_until_photo_gate(name: str) -> None:
    policy = text(name)
    assert "structured data only" in policy
    assert all(word in policy for word in ("wp-6f", "deployed", "calibration", "justin"))


@pytest.mark.parametrize("name", POLICY_DOCS)
def test_version_1_notifications_are_sync_only_and_nearby_is_deferred(name: str) -> None:
    policy = text(name)
    assert re.search(r"version 1.{0,80}sync reminders only", policy)
    assert re.search(r"nearby.{0,100}deferred.{0,160}most wanted", policy)
    assert "land-access eligibility" in policy


@pytest.mark.parametrize("name", POLICY_DOCS)
def test_card_exclusion_is_bounded_to_scene_text_and_faces_still_cover_frame(name: str) -> None:
    policy = text(name)
    assert all(
        word in policy
        for word in ("scene-text", "detected gsip reference-card", "quadrilateral", "margin")
    )
    assert "existing marker homography" in policy
    assert "remainder of the frame" in policy
    assert re.search(r"face.{0,70}entire.{0,30}frame", policy)
    assert re.search(r"no.{0,25}card.{0,70}entire.{0,30}frame", policy)


@pytest.mark.parametrize("name", POLICY_DOCS)
def test_dedicated_plate_model_needs_a_material_evaluation_gap_and_licensed_weights(
    name: str,
) -> None:
    policy = text(name)
    assert re.search(r"dedicated plate.{0,180}staged.{0,120}material gap", policy)
    assert re.search(r"dedicated plate.{0,400}verified.{0,80}weight license", policy)
    assert "face and scene-text" in policy


def test_app_2a_keeps_comparison_scope_and_no_readiness_overclaim() -> None:
    readiness = spec_section("15.2")
    assert "comparing two builds of the same inputs" in readiness
    assert (
        "byte-identical" in readiness
        and "normalizes nondeterministic packaging metadata" in readiness
    )
    assert "successful build alone is not reproducibility evidence" in readiness
    assert "ios remains an explicit readiness gate" in readiness


def test_privacy_state_and_existing_gates_remain_independent() -> None:
    screening = spec_section("15.4")
    assert "privacy status is independent" in screening
    assert "empty photo list" in screening
    assert "never automatically blur" in screening
    assert all(
        word in screening
        for word in ("consent", "withdrawal", "provenance", "holdout", "k-anonymity")
    )
