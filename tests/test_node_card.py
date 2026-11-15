import re
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
import pytest
from pypdf import PdfReader

from card.design import PATCHES as A6_PATCHES
from card.fixtures import canonical_card
from card.node_design import (
    ALL_PATCHES,
    CARD_HEIGHT_MM,
    CARD_WIDTH_MM,
    MARKER_ID,
    MARKER_QUIET_MM,
    MARKER_SIZE_MM,
    MARKER_X_MM,
    MARKER_Y_MM,
    PATCHES,
    RAMP,
    REPEATED,
    SAFE_MARGIN_MM,
    SCALE_LENGTH_MM,
    SCALE_X_MM,
    SCALE_Y_MM,
    check_run_code,
)
from card.node_fixtures import canonical_node_card, photograph
from card.node_generate import generate_node
from card.node_validate import (
    MIN_MARKER_SIDE_PX,
    card_scale,
    node_card_corners,
    node_card_transform,
    read_patches,
)
from card.validate import card_transform

TARGETS = {patch.name: patch.rgb for patch in ALL_PATCHES}
POINT_MM = 25.4 / 72


def worst_error(measured: dict[str, tuple[int, int, int]]) -> int:
    return max(
        abs(actual - expected)
        for name, target in TARGETS.items()
        for actual, expected in zip(measured[name], target, strict=True)
    )


# ---- the print file ----------------------------------------------------------------------


def test_print_file_is_credit_card_size_and_deterministic_per_run(tmp_path: Path) -> None:
    first = generate_node(tmp_path / "first", "AB12-0001")
    second = generate_node(tmp_path / "second", "AB12-0001")
    other = generate_node(tmp_path / "other", "AB12-0002")
    for one, two, another in zip(first, second, other, strict=True):
        assert one.read_bytes() == two.read_bytes()
        assert one.read_bytes() != another.read_bytes()
        reader = PdfReader(one)
        assert len(reader.pages) == 1
        page = reader.pages[0]
        assert abs(float(page.mediabox.width) * POINT_MM - 85.6) < 0.02
        assert abs(float(page.mediabox.height) * POINT_MM - 53.98) < 0.02
        assert "RUN AB12-0001" in page.extract_text()
        assert reader.metadata is not None and "AB12-0001" in (reader.metadata.title or "")


def test_the_print_file_draws_what_the_detector_expects(tmp_path: Path) -> None:
    """The detector and the fixtures share layout constants; this reads the PDF itself."""

    page = PdfReader(generate_node(tmp_path, "AB12-0001")[0]).pages[0]
    contents = page.get_contents()
    assert contents is not None
    stream = contents.get_data().decode("latin-1")
    number = r"(-?\d+(?:\.\d+)?)"
    drawn = {
        tuple(round(float(value) * POINT_MM, 1) for value in match)
        for match in re.findall(rf"{number} {number} {number} {number} re", stream)
    }
    for patch in ALL_PATCHES:
        box = (
            round(patch.x_mm, 1),
            round(CARD_HEIGHT_MM - patch.y_mm - patch.height_mm, 1),
            round(patch.width_mm, 1),
            round(patch.height_mm, 1),
        )
        assert box in drawn, patch.name
    assert len(drawn) == len(ALL_PATCHES)
    line = re.search(rf"{number} {number} m {number} {number} l", stream)
    assert line is not None
    x1, y1, x2, y2 = (float(value) * POINT_MM for value in line.groups())
    assert (x2 - x1) == pytest.approx(20.0, abs=0.01) and y1 == y2
    assert x1 == pytest.approx(SCALE_X_MM, abs=0.05)
    assert CARD_HEIGHT_MM - y1 == pytest.approx(SCALE_Y_MM, abs=0.05)
    placed = [
        tuple(float(value) * POINT_MM for value in match)
        for match in re.findall(rf"{number} 0 0 {number} {number} {number} cm", stream)
    ]
    # The first such matrix is the page's identity; the marker image is the only other one.
    images = [match for match in placed if match[0] > 1]
    assert len(images) == 1
    width, height, x, y = images[0]
    assert (width, height) == pytest.approx((MARKER_SIZE_MM, MARKER_SIZE_MM), abs=0.05)
    assert x == pytest.approx(MARKER_X_MM, abs=0.05)
    assert CARD_HEIGHT_MM - y - height == pytest.approx(MARKER_Y_MM, abs=0.05)


def test_all_printed_text_is_inside_the_safe_margin_and_off_the_patches(tmp_path: Path) -> None:
    page = PdfReader(generate_node(tmp_path, "AB12-0001")[0]).pages[0]
    placed: list[tuple[str, float, float]] = []

    def visit(text: str, _cm: object, tm: list[float], _font: object, _size: float) -> None:
        if text.strip():
            placed.append((text.strip(), tm[4] * POINT_MM, CARD_HEIGHT_MM - tm[5] * POINT_MM))

    page.extract_text(visitor_text=visit)
    assert {text for text, _, _ in placed} >= {"GSIP NODE CARD v1", "20 mm", "RUN AB12-0001"}
    patch_top = min(patch.y_mm for patch in ALL_PATCHES)
    patch_bottom = max(patch.y_mm + patch.height_mm for patch in ALL_PATCHES)
    for text, x, baseline in placed:
        assert SAFE_MARGIN_MM <= x <= CARD_WIDTH_MM - SAFE_MARGIN_MM, text
        assert SAFE_MARGIN_MM <= baseline <= CARD_HEIGHT_MM - SAFE_MARGIN_MM, text
        # Text sits in the band above the patches or the band below them, never across them.
        assert baseline < patch_top - 2 or baseline - 2 > patch_bottom, text


@pytest.mark.parametrize(
    "run",
    [
        "",
        "ab12-0001",
        "AB12",
        "AB12-001",
        "AB12-00001",
        "A1-0001",
        "ABC1-0001",
        "ABCD-0001",
        "JUSTIN-0001",
        "JHART-1984",
        "a@b.co-0001",
        "AB12-0001 ",
        "AB12_0001",
        "AB12-0001\n",
        "AB12-0001\nX",
        "../A1-0001",
        "AB١٢-0001",
        "ＡＢ12-0001",
    ],
)
def test_run_codes_outside_the_format_are_refused(run: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        check_run_code(run)
    with pytest.raises(ValueError):
        generate_node(tmp_path, run)
    assert not list(tmp_path.iterdir())


def test_a_run_code_is_not_a_guarantee_against_naming_a_person() -> None:
    """Recorded so the claim is not made again: initials and a year fit the format.

    Only the person ordering a run can keep it impersonal, by giving every card the same code."""

    assert check_run_code("JH84-0001") == "JH84-0001"
    assert check_run_code("HOME-0000") == "HOME-0000"
    with pytest.raises(ValueError):
        check_run_code(None)  # type: ignore[arg-type]


# ---- the layout --------------------------------------------------------------------------


def test_layout_fits_the_card_and_nothing_overlaps() -> None:
    quiet = (
        MARKER_X_MM - MARKER_QUIET_MM,
        MARKER_Y_MM - MARKER_QUIET_MM,
        MARKER_X_MM + MARKER_SIZE_MM + MARKER_QUIET_MM,
        MARKER_Y_MM + MARKER_SIZE_MM + MARKER_QUIET_MM,
    )
    boxes = {"marker and its light border": quiet} | {
        patch.name: (
            patch.x_mm,
            patch.y_mm,
            patch.x_mm + patch.width_mm,
            patch.y_mm + patch.height_mm,
        )
        for patch in ALL_PATCHES
    }
    for name, (x1, y1, x2, y2) in boxes.items():
        limit = 0.0 if name.startswith("marker") else SAFE_MARGIN_MM
        assert x1 >= limit and y1 >= limit, name
        assert x2 <= CARD_WIDTH_MM - limit and y2 <= CARD_HEIGHT_MM - limit, name
    for (first, a), (second, b) in combinations(boxes.items(), 2):
        touching_ramp = first.startswith("ramp_") and second.startswith("ramp_")
        slack = (0.0 if touching_ramp else 0.5) - 1e-6
        apart = (
            a[2] + slack <= b[0]
            or b[2] + slack <= a[0]
            or a[3] + slack <= b[1]
            or b[3] + slack <= a[1]
        )
        assert apart, (first, second)
    assert SCALE_X_MM >= SAFE_MARGIN_MM
    assert SCALE_X_MM + SCALE_LENGTH_MM <= CARD_WIDTH_MM - SAFE_MARGIN_MM
    assert max(box[3] for box in boxes.values()) < SCALE_Y_MM < CARD_HEIGHT_MM - SAFE_MARGIN_MM


def test_it_carries_the_a6_colours_and_a_ramp_that_repeats_three_of_them() -> None:
    assert [(patch.name, patch.rgb) for patch in PATCHES] == [
        (patch.name, patch.rgb) for patch in A6_PATCHES
    ]
    values = [patch.rgb for patch in RAMP]
    assert all(r == g == b for r, g, b in values)
    assert [rgb[0] for rgb in values] == sorted({rgb[0] for rgb in values})
    assert len(values) == 5
    for colour, step in REPEATED:
        gap = max(abs(a - b) for a, b in zip(TARGETS[colour], TARGETS[step], strict=True))
        assert gap <= 12, (colour, step)


def test_the_marker_cannot_be_read_in_a_mirror() -> None:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    marker = cv2.copyMakeBorder(
        cv2.aruco.generateImageMarker(dictionary, MARKER_ID, 240),
        60,
        60,
        60,
        60,
        cv2.BORDER_CONSTANT,
        value=255,
    )
    assert detector.detectMarkers(marker)[1].flatten().tolist() == [MARKER_ID]
    for mirrored in (cv2.flip(marker, 1), cv2.flip(marker, 0), cv2.transpose(marker)):
        assert detector.detectMarkers(mirrored)[1] is None


# ---- reading a photograph -----------------------------------------------------------------


@pytest.mark.parametrize("index", range(10))
@pytest.mark.parametrize("width_px", [560.0, 1100.0])
def test_every_window_sits_inside_its_patch(index: int, width_px: float) -> None:
    # A clashing 1 mm band is painted just inside every patch edge. A window that strays reads
    # the band or the gap, and the reading is refused or wrong.
    image, _ = photograph(
        index, card_width_px=width_px, shift=False, source=canonical_node_card(ring=True)
    )
    assert worst_error(read_patches(image)) <= 2


def test_the_ring_fixture_does_catch_a_stray_window(monkeypatch: pytest.MonkeyPatch) -> None:
    import card.node_validate as subject

    image, _ = photograph(4, shift=False, source=canonical_node_card(ring=True))
    monkeypatch.setattr(subject, "INSET", 0.02)
    with pytest.raises(ValueError, match="flat colour|printed nearly alike|out of order"):
        subject.read_patches(image)


@pytest.mark.parametrize("quarter_turns", [1, 2, 3])
def test_a_rotated_photograph_reads_the_same(quarter_turns: int) -> None:
    image, _ = photograph(5, card_width_px=800.0, canvas=(1500, 1500), shift=False)
    assert worst_error(read_patches(np.ascontiguousarray(np.rot90(image, quarter_turns)))) <= 2


@pytest.mark.parametrize("index", range(10))
def test_colour_cast_tone_and_noise_leave_every_patch_in_its_own_cell(index: int) -> None:
    measured = read_patches(photograph(index)[0])
    assert set(measured) == set(TARGETS)
    names = list(TARGETS)
    for channel in range(3):
        seen = np.argsort(np.argsort([measured[name][channel] for name in names]))
        want = np.argsort(np.argsort([TARGETS[name][channel] for name in names]))
        # Rank agreement across the fourteen patches: swapped cells would break it.
        assert np.corrcoef(seen, want)[0, 1] > 0.95


def test_reading_applies_no_correction() -> None:
    assert worst_error(read_patches(photograph(9)[0])) > 10


def test_a_compressed_photograph_is_read_within_a_few_levels() -> None:
    image, _ = photograph(3, card_width_px=800.0, shift=False)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 40])
    assert ok
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    assert decoded is not None
    assert worst_error(read_patches(decoded)) <= 6


# ---- refusals -----------------------------------------------------------------------------


@pytest.mark.parametrize("flip", [0, 1])
def test_a_mirrored_photograph_is_refused(flip: int) -> None:
    image, _ = photograph(2, shift=False)
    assert node_card_transform(image) is not None
    mirrored = cv2.flip(image, flip)
    assert node_card_transform(mirrored) is None
    with pytest.raises(ValueError):
        read_patches(mirrored)


@pytest.mark.parametrize("keep", [0.5, 0.7, 0.8, 0.93])
def test_a_card_cut_off_by_the_frame_is_refused(keep: float) -> None:
    image, truth = photograph(0, card_width_px=900.0, shift=False, flat=True)
    left, right = float(truth[:, 0].min()), float(truth[:, 0].max())
    cropped = np.ascontiguousarray(image[:, : round(left + (right - left) * keep)])
    # The marker is still in view, so only the out-of-frame check can refuse this.
    assert card_transform(cropped) is None
    assert node_card_transform(cropped) is None
    with pytest.raises(ValueError):
        read_patches(cropped)


def test_a_patch_window_outside_the_photograph_is_refused_even_with_a_transform() -> None:
    image, truth = photograph(0, card_width_px=900.0, shift=False, flat=True)
    transform = node_card_transform(image)
    assert transform is not None
    left, right = float(truth[:, 0].min()), float(truth[:, 0].max())
    cropped = np.ascontiguousarray(image[:, : round(left + (right - left) * 0.8)])
    with pytest.raises(ValueError, match="not wholly inside"):
        read_patches(cropped, transform)


def test_a_card_too_small_to_place_its_far_patches_is_refused() -> None:
    marker_share = MARKER_SIZE_MM / CARD_WIDTH_MM
    small = (MIN_MARKER_SIDE_PX - 12) / marker_share
    large = (MIN_MARKER_SIDE_PX + 12) / marker_share
    assert (
        node_card_transform(photograph(1, card_width_px=small, shift=False, flat=True)[0]) is None
    )
    assert (
        node_card_transform(photograph(1, card_width_px=large, shift=False, flat=True)[0])
        is not None
    )


def _on_card(image: np.ndarray, x_mm: float, y_mm: float) -> tuple[int, int]:
    transform = node_card_transform(image)
    assert transform is not None
    point = np.array([[[x_mm * 12, y_mm * 12]]], dtype=np.float32)
    x, y = cv2.perspectiveTransform(point, np.linalg.inv(transform).astype(np.float32))[0, 0]
    return int(round(x)), int(round(y))


def test_a_half_covered_patch_is_refused() -> None:
    image, _ = photograph(3, shift=False)
    sky = next(patch for patch in PATCHES if patch.name == "sky")
    x, y = _on_card(image, sky.x_mm + sky.width_mm * 0.35, sky.y_mm + sky.height_mm / 2)
    cv2.circle(image, (x, y), 34, (150, 170, 210), -1)
    with pytest.raises(ValueError, match="sky is not one flat colour"):
        read_patches(image)


@pytest.mark.parametrize(("name", "paint"), [("black", 255), ("white", 40), ("neutral_gray", 250)])
def test_glare_or_a_cover_over_a_repeated_patch_is_refused(name: str, paint: int) -> None:
    image, _ = photograph(3, shift=False)
    patch = next(item for item in PATCHES if item.name == name)
    x, y = _on_card(image, patch.x_mm + patch.width_mm / 2, patch.y_mm + patch.height_mm / 2)
    cv2.circle(image, (x, y), 110, (paint, paint, paint), -1)
    with pytest.raises(ValueError, match="printed nearly alike"):
        read_patches(image)


def test_glare_over_a_ramp_step_is_refused() -> None:
    image, _ = photograph(3, shift=False)
    step = RAMP[1]
    x, y = _on_card(image, step.x_mm + step.width_mm / 2, step.y_mm + step.height_mm / 2)
    cv2.circle(image, (x, y), 70, (255, 255, 255), -1)
    with pytest.raises(ValueError, match="out of order|flat colour"):
        read_patches(image)


def test_a_ramp_printed_out_of_order_is_refused() -> None:
    source = canonical_node_card()
    boxes = []
    for step in (RAMP[1], RAMP[3]):
        x, y = round(step.x_mm * 12), round(step.y_mm * 12)
        boxes.append(
            (slice(y, y + round(step.height_mm * 12)), slice(x, x + round(step.width_mm * 12)))
        )
    first, second = source[boxes[0]].copy(), source[boxes[1]].copy()
    assert first.shape == second.shape
    source[boxes[0]], source[boxes[1]] = second, first
    image, _ = photograph(3, shift=False, source=source)
    with pytest.raises(ValueError, match="^the neutral ramp is out of order$"):
        read_patches(image)


def test_a_photograph_bright_enough_to_clip_a_patch_is_refused() -> None:
    image, _ = photograph(4, shift=False, flat=True)
    bright = np.clip(image.astype(np.float64) * 1.4, 0, 255).astype(np.uint8)
    with pytest.raises(ValueError, match="clipped"):
        read_patches(bright)


def _graded(image: np.ndarray, fall: float) -> np.ndarray:
    ramp = np.linspace(1.0 - fall, 1.0, image.shape[1])[None, :, None]
    return np.clip(image.astype(np.float64) * ramp, 0, 255).astype(np.uint8)


@pytest.mark.parametrize("index", range(10))
@pytest.mark.parametrize("width_px", [560.0, 1100.0])
def test_light_falling_off_across_the_frame_is_still_read(index: int, width_px: float) -> None:
    # white and ramp_4 are printed up to 12 levels apart. Judged against zero instead of
    # against that printed difference, some of these photographs are refused.
    measured = read_patches(_graded(photograph(index, card_width_px=width_px, shift=False)[0], 0.4))
    assert set(measured) == set(TARGETS)


def test_the_minimum_marker_size_is_the_measured_one() -> None:
    assert MIN_MARKER_SIDE_PX == 125.0


def test_an_evenly_covered_ordinary_patch_is_not_detected() -> None:
    """A stated limit, pinned so it is not forgotten: nothing repeats the ochre patch."""

    image, _ = photograph(3, shift=False)
    patch = next(item for item in PATCHES if item.name == "ochre")
    x, y = _on_card(image, patch.x_mm + patch.width_mm / 2, patch.y_mm + patch.height_mm / 2)
    cv2.circle(image, (x, y), 52, (200, 200, 200), -1)
    assert read_patches(image)["ochre"] == (200, 200, 200)


@pytest.mark.parametrize(
    "image",
    [
        np.zeros((600, 800), np.uint8),
        np.zeros((600, 800, 4), np.uint8),
        np.zeros((600, 800, 3), np.float32),
    ],
)
def test_an_image_that_is_not_plain_bgr_is_refused_clearly(image: np.ndarray) -> None:
    with pytest.raises(ValueError, match="three-channel"):
        node_card_transform(image)
    with pytest.raises(ValueError, match="three-channel"):
        read_patches(image)


def test_the_two_card_editions_are_never_mistaken_for_each_other() -> None:
    node, _ = photograph(3, shift=False)
    assert node_card_transform(node) is not None
    assert card_transform(node) is None
    a6 = cv2.copyMakeBorder(
        canonical_card(), 80, 80, 80, 80, cv2.BORDER_CONSTANT, value=(90, 120, 150)
    )
    assert card_transform(a6) is not None
    assert node_card_transform(a6) is None
    with pytest.raises(ValueError):
        read_patches(a6)
    # The node layout printed with the A6 marker is not a node card either.
    wrong, _ = photograph(3, shift=False, source=canonical_node_card(marker_id=7))
    assert node_card_transform(wrong) is None


def test_a_frame_without_a_card_or_with_two_is_refused() -> None:
    blank = np.full((900, 1200, 3), (96, 122, 148), np.uint8)
    assert node_card_transform(blank) is None
    one, _ = photograph(2, card_width_px=700.0, canvas=(1200, 900), shift=False)
    assert node_card_transform(one) is not None
    assert node_card_transform(np.hstack([one, one])) is None
    with pytest.raises(ValueError):
        read_patches(np.hstack([one, one]))


# ---- geometry -----------------------------------------------------------------------------


@pytest.mark.parametrize("index", range(10))
@pytest.mark.parametrize(("width_px", "limit"), [(560.0, 0.015), (900.0, 0.008)])
@pytest.mark.parametrize("shift", [False, True])
def test_card_corners_match_the_photograph(
    index: int, width_px: float, limit: float, shift: bool
) -> None:
    # One small marker locates the whole card, so the far corners carry the most error. The
    # narrowest patch inset is 1.85 percent of the card's width.
    image, truth = photograph(index, card_width_px=width_px, shift=shift)
    transform = node_card_transform(image)
    assert transform is not None
    assert np.abs(node_card_corners(transform) - truth).max() < limit * width_px


@pytest.mark.parametrize(("index", "width_px"), [(0, 560.0), (4, 900.0), (9, 1300.0)])
def test_scale_is_right_in_both_directions_for_a_card_seen_square_on(
    index: int, width_px: float
) -> None:
    image, _ = photograph(index, card_width_px=width_px, shift=False, flat=True)
    transform = node_card_transform(image)
    assert transform is not None
    across, down = card_scale(transform)
    assert across == pytest.approx(CARD_WIDTH_MM / width_px, rel=0.02)
    assert down == pytest.approx(CARD_WIDTH_MM / width_px, rel=0.02)


def test_scale_reports_a_stretched_image_as_two_different_numbers() -> None:
    upright, _ = photograph(4, card_width_px=1000.0, shift=False, flat=True)
    turned = cv2.warpAffine(
        upright,
        cv2.getRotationMatrix2D((1000, 750), -1.0, 1.0),
        (2000, 1500),
        borderValue=(96, 122, 148),
    )
    squashed = cv2.resize(turned, (2000, 750), interpolation=cv2.INTER_AREA)
    transform = node_card_transform(squashed)
    assert transform is not None
    across, down = card_scale(transform)
    assert across == pytest.approx(CARD_WIDTH_MM / 1000.0, rel=0.03)
    assert down == pytest.approx(2 * CARD_WIDTH_MM / 1000.0, rel=0.03)
