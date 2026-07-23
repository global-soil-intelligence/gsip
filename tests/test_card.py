from pathlib import Path

from pypdf import PdfReader

from card.design import CARD_HEIGHT_MM, CARD_WIDTH_MM, PATCHES
from card.fixtures import generate_fixtures
from card.generate import generate
from card.validate import validate


def test_card_pdfs_are_a6_and_deterministic(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = generate(first_dir)
    second = generate(second_dir)
    for first_pdf, second_pdf in zip(first, second, strict=True):
        assert first_pdf.read_bytes() == second_pdf.read_bytes()
        page = PdfReader(first_pdf).pages[0]
        width_mm = float(page.mediabox.width) * 25.4 / 72
        height_mm = float(page.mediabox.height) * 25.4 / 72
        assert abs(width_mm - CARD_WIDTH_MM) < 0.02
        assert abs(height_mm - CARD_HEIGHT_MM) < 0.02


def test_validator_detects_marker_and_extracts_patches_from_ten_fixtures(
    tmp_path: Path,
) -> None:
    expected = {patch.name for patch in PATCHES}
    for fixture in generate_fixtures(tmp_path / "fixtures"):
        assert set(validate(fixture)) == expected


def test_validator_documents_color_recovery_under_adversarial_capture(
    tmp_path: Path,
) -> None:
    successes = 0
    targets = {patch.name: patch.rgb for patch in PATCHES if patch.name != "neutral_gray"}
    for fixture in generate_fixtures(tmp_path / "fixtures"):
        measured = validate(fixture)
        if all(
            max(
                abs(actual - expected)
                for actual, expected in zip(measured[name], target, strict=True)
            )
            <= 24
            for name, target in targets.items()
        ):
            successes += 1
    assert successes >= 8
