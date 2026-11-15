"""Both card editions in photo QA, and the per-photo colour correction (SPEC section 17)."""

import json

import cv2
import numpy as np
import pytest
from test_qa import jpeg, soil_texture

from card.fixtures import canonical_card
from card.node_design import PATCHES as NODE_PATCHES
from card.node_design import RAMP
from card.node_fixtures import canonical_node_card
from pipeline.cards import find_cards
from pipeline.colour_correction import (
    MAX_RESIDUAL_DELTA_E,
    apply,
    delta_e,
    fit,
    soil_colour,
    srgb_to_lab,
)
from pipeline.qa import SHARPNESS_MIN, sanitize_jpeg, sharpness
from pipeline.qa import evaluate_photo as evaluate_a6_only
from pipeline.qa_cards import CardQaResult as QaResult
from pipeline.qa_cards import evaluate_photo_with_cards as evaluate_photo

SOIL_RGB = (141, 104, 77)
CASTS = [
    ((1.0, 1.0, 1.0), 1.0),
    ((1.0, 0.85, 0.7), 1.0),
    ((0.7, 0.84, 1.0), 1.0),
    ((1.0, 1.0, 1.0), 0.75),
    ((1.0, 1.0, 1.0), 1.35),
    ((1.0, 0.86, 0.77), 0.8),
    ((0.77, 0.9, 1.0), 1.25),
    ((0.8, 0.8, 0.8), 1.1),
]


def flat_soil(seed: int = 0, *, height: int = 900, width: int = 1200) -> np.ndarray:
    """Soil of one known colour with fine grain, so that sharpness passes (BGR)."""

    rng = np.random.default_rng(seed)
    grain = rng.normal(0, 14, (height, width, 1))
    return np.clip(np.array(SOIL_RGB[::-1], dtype=np.float64) + grain, 0, 255).astype(np.uint8)


def place(scene: np.ndarray, card: np.ndarray, *, x: int, y: int, width: int) -> np.ndarray:
    height = round(card.shape[0] * width / card.shape[1])
    composed = scene.copy()
    composed[y : y + height, x : x + width] = cv2.resize(
        card, (width, height), interpolation=cv2.INTER_AREA
    )
    return composed


def with_node(scene: np.ndarray, *, x: int = 60, y: int = 250, width: int = 560) -> np.ndarray:
    return place(scene, canonical_node_card(), x=x, y=y, width=width)


def with_a6(scene: np.ndarray, *, x: int = 40, y: int = 220, width: int = 320) -> np.ndarray:
    return place(scene, canonical_card(), x=x, y=y, width=width)


def photographed(image: np.ndarray, gains: tuple[float, float, float], gamma: float) -> np.ndarray:
    """The same scene through another camera: a colour cast (RGB gains) and a tone curve."""

    rgb = image[..., ::-1].astype(np.float64) / 255.0
    out = np.clip(rgb * np.array(gains), 0, 1) ** gamma
    return np.ascontiguousarray((out[..., ::-1] * 255).round().astype(np.uint8))


def events(result: QaResult) -> dict[str, tuple[bool, float | None]]:
    return {event.check_name: (event.passed, event.score) for event in result.events}


def record(result: QaResult) -> dict[str, object]:
    assert result.card_color_correction is not None
    return result.card_color_correction


# ---- the node card in photo QA ------------------------------------------------------------


def test_a_node_card_is_masked_read_and_calibrates_the_photo() -> None:
    result = evaluate_photo(jpeg(with_node(soil_texture(1))), accuracy_m=12)
    assert result.status == "pass"
    assert result.calibration_status == "calibrated"
    assert record(result)["edition"] == "node"
    patches = record(result)["patches"]
    assert isinstance(patches, dict) and set(patches) >= {"ramp_0", "ramp_4", "neutral_gray"}
    passed, fraction = events(result)["soil_region"]
    assert passed and fraction is not None and 0.6 < fraction < 0.9
    json.dumps(record(result))


def test_blurred_soil_beside_a_sharp_node_card_fails_sharpness() -> None:
    composed = with_node(soil_texture(3, blur=31))
    assert sharpness(composed) >= SHARPNESS_MIN
    result = evaluate_photo(jpeg(composed), accuracy_m=8)
    passed, score = events(result)["sharpness"]
    assert not passed and score is not None and score < SHARPNESS_MIN
    assert result.status == "fail"


def test_a_refused_node_card_is_masked_and_uncalibrated_never_rejected() -> None:
    composed = with_node(soil_texture(4))
    sky = next(patch for patch in NODE_PATCHES if patch.name == "sky")
    scale = 560 / 85.6
    centre = (round(60 + (sky.x_mm + 3) * scale), round(250 + (sky.y_mm + 5) * scale))
    cv2.circle(composed, centre, 16, (150, 170, 210), -1)
    result = evaluate_photo(jpeg(composed), accuracy_m=12)
    assert result.status == "pass"
    assert result.calibration_status == "uncalibrated"
    assert result.card_color_correction is None
    assert result.card_detected
    assert events(result)["card_detection"] == (True, 0.0)
    fraction = events(result)["soil_region"][1]
    assert fraction is not None and fraction < 0.9


def test_a_node_card_too_small_to_read_is_still_masked() -> None:
    scene = soil_texture(5)
    result = evaluate_photo(jpeg(with_node(scene, width=300)), accuracy_m=12)
    assert result.calibration_status == "uncalibrated"
    fraction = events(result)["soil_region"][1]
    assert fraction is not None and 0.85 < fraction < 0.97


@pytest.mark.parametrize("pair", ["a6+node", "node+node", "a6+a6"])
def test_two_cards_give_no_calibration_and_both_are_masked(pair: str) -> None:
    scene = soil_texture(6)
    one_node = with_node(scene, x=600, y=80, width=560)
    one_a6 = with_a6(scene)
    if pair == "a6+node":
        both, single = with_node(one_a6, x=600, y=80, width=560), one_node
    elif pair == "node+node":
        both, single = with_node(one_node, x=600, y=500, width=560), one_node
    else:
        both, single = with_a6(one_a6, x=700, y=220, width=320), one_a6
    assert evaluate_photo(jpeg(single), accuracy_m=12).calibration_status == "calibrated"
    result = evaluate_photo(jpeg(both), accuracy_m=12)
    assert result.calibration_status == "uncalibrated"
    assert result.card_color_correction is None
    assert len(find_cards(both).outlines) == 2
    alone = events(evaluate_photo(jpeg(single), accuracy_m=12))["soil_region"][1]
    together = events(result)["soil_region"][1]
    assert alone is not None and together is not None and together < alone - 0.05


def test_a_photo_without_a_card_is_untouched_by_this_package() -> None:
    result = evaluate_photo(jpeg(soil_texture(7)), accuracy_m=12)
    assert result.calibration_status == "uncalibrated"
    assert result.card_color_correction is None and not result.card_detected
    assert events(result)["soil_region"] == (True, 1.0)


class RecordingClassifier:
    def __init__(self) -> None:
        self.seen: list[np.ndarray] = []

    def score(self, image: np.ndarray) -> float:
        self.seen.append(image.copy())
        return 0.3 if len(self.seen) % 2 else 0.9


@pytest.mark.parametrize("seed", range(4))
@pytest.mark.parametrize("scene", ["no card", "a6", "a6 blurred soil", "a6 only"])
@pytest.mark.parametrize(
    "options",
    [
        {"accuracy_m": 12},
        {"accuracy_m": None},
        {"accuracy_m": 900},
        {"accuracy_m": 12, "land_cover": "bare", "priors": {"soc": 130.0}},
        {"accuracy_m": 12, "duplicate": True},
        {"accuracy_m": 12, "classify": True},
    ],
)
def test_no_card_and_one_a6_card_score_exactly_as_the_bound_gate_does(
    seed: int, scene: str, options: dict[str, object]
) -> None:
    if scene == "no card":
        image = soil_texture(seed)
    elif scene == "a6":
        image = with_a6(soil_texture(seed))
    elif scene == "a6 blurred soil":
        image = with_a6(soil_texture(seed, blur=31))
    else:
        image = canonical_card()
    raw = jpeg(image)
    kwargs = {key: value for key, value in options.items() if key not in ("duplicate", "classify")}
    if options.get("duplicate"):
        kwargs["existing_hashes"] = (evaluate_a6_only(raw, accuracy_m=12).perceptual_hash,)
    old_classifier, new_classifier = RecordingClassifier(), RecordingClassifier()
    if options.get("classify"):
        old = evaluate_a6_only(raw, classifier=old_classifier, **kwargs)  # type: ignore[arg-type]
        new = evaluate_photo(raw, classifier=new_classifier, **kwargs)  # type: ignore[arg-type]
        assert len(new_classifier.seen) == len(old_classifier.seen) == 1
        assert np.array_equal(new_classifier.seen[0], old_classifier.seen[0])
    else:
        old = evaluate_a6_only(raw, **kwargs)  # type: ignore[arg-type]
        new = evaluate_photo(raw, **kwargs)  # type: ignore[arg-type]
    assert new.events == old.events
    outcome = {event.check_name: event.passed for event in new.events}
    if options.get("duplicate"):
        assert outcome["duplicate"] is False
    if options.get("land_cover"):
        assert outcome["gps_plausibility"] is False
    assert (new.status, new.calibration_status, new.perceptual_hash, new.sanitized_jpeg) == (
        old.status,
        old.calibration_status,
        old.perceptual_hash,
        old.sanitized_jpeg,
    )
    assert new.camera_metadata == old.camera_metadata
    assert new.card_detected == (scene != "no card")
    assert (old.model_version, new.model_version) == ("deterministic-v2", "deterministic-v3")


def test_a_card_cut_off_by_the_frame_is_masked_and_gives_no_record() -> None:
    scene = soil_texture(11)
    for composed in (
        with_node(scene, x=600, y=250, width=560)[:, :1000],
        with_a6(scene, x=860)[:, :1050],
    ):
        result = evaluate_photo(jpeg(np.ascontiguousarray(composed)), accuracy_m=12)
        assert result.card_detected and result.card_color_correction is None
        assert result.calibration_status == "uncalibrated"
        fraction = events(result)["soil_region"][1]
        assert fraction is not None and fraction < 0.9


def test_a_black_and_white_card_is_read_but_never_normalised() -> None:
    grey = cv2.cvtColor(cv2.cvtColor(canonical_card(), cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    result = evaluate_photo(
        jpeg(place(soil_texture(12), grey, x=40, y=220, width=320)), accuracy_m=12
    )
    saved = record(result)
    assert saved["normalised"] is False and saved["soil_rgb"] is None
    assert saved["method"] is None and saved["residual_delta_e"] is None


def test_the_colour_record_can_never_reach_a_public_row() -> None:
    from pipeline.export import FORBIDDEN_PUBLIC_KEYS

    assert "card_color_correction" in FORBIDDEN_PUBLIC_KEYS


def test_correction_never_changes_the_stored_photograph() -> None:
    raw = jpeg(with_node(soil_texture(8)))
    result = evaluate_photo(raw, accuracy_m=12)
    assert result.calibration_status == "calibrated"
    assert result.sanitized_jpeg == sanitize_jpeg(raw)[0]


# ---- the correction recovers a known soil colour -------------------------------------------


@pytest.mark.parametrize("edition", ["node", "a6"])
@pytest.mark.parametrize(("gains", "gamma"), CASTS)
def test_corrected_soil_is_closer_to_the_true_colour(
    edition: str, gains: tuple[float, float, float], gamma: float
) -> None:
    scene = with_node(flat_soil()) if edition == "node" else with_a6(flat_soil())
    result = evaluate_photo(jpeg(photographed(scene, gains, gamma)), accuracy_m=12)
    saved = record(result)
    assert saved["normalised"] is True, saved
    before = float(delta_e(np.array(saved["soil_rgb_uncorrected"]), np.array(SOIL_RGB)))
    after = float(delta_e(np.array(saved["soil_rgb"]), np.array(SOIL_RGB)))
    # Never worse; and when the camera changed the colour at all, clearly better.
    assert after <= max(before, 2.5)
    if before > 5:
        assert after < before / 2
    assert after < 2.5
    assert saved["method"] == "ramp-tone-then-affine"
    lab = srgb_to_lab(np.array(saved["soil_rgb"]))
    assert np.allclose(lab, np.array(saved["soil_lab"]), atol=0.1)


def test_two_cameras_agree_after_correction_and_not_before() -> None:
    scene = with_node(flat_soil())
    saved = [
        record(evaluate_photo(jpeg(photographed(scene, gains, gamma)), accuracy_m=12))
        for gains, gamma in (CASTS[1], CASTS[6])
    ]
    raw = float(
        delta_e(
            np.array(saved[0]["soil_rgb_uncorrected"]), np.array(saved[1]["soil_rgb_uncorrected"])
        )
    )
    fixed = float(delta_e(np.array(saved[0]["soil_rgb"]), np.array(saved[1]["soil_rgb"])))
    assert raw > 15 and fixed < 4


def test_a_card_whose_colours_do_not_fit_leaves_the_photo_uncalibrated() -> None:
    card = canonical_node_card()
    scale = 12
    boxes = []
    for name in ("ochre", "sky", "leaf", "clay_red"):
        patch = next(item for item in NODE_PATCHES if item.name == name)
        x, y = round(patch.x_mm * scale), round(patch.y_mm * scale)
        boxes.append((slice(y, y + round(10 * scale)), slice(x, x + round(10 * scale))))
    tiles = [card[box].copy() for box in boxes]
    for box, tile in zip(boxes, tiles[1:] + tiles[:1], strict=True):
        card[box] = tile
    scene = place(soil_texture(9), card, x=60, y=250, width=560)
    result = evaluate_photo(jpeg(scene), accuracy_m=12)
    saved = record(result)
    # The published field keeps its old meaning (a card's patches were read); the estimator
    # goes by ``normalised``.
    assert result.calibration_status == "calibrated"
    assert saved["normalised"] is False
    residual = saved["residual_delta_e"]
    assert isinstance(residual, float) and residual > MAX_RESIDUAL_DELTA_E
    assert saved["soil_rgb"] is None and "matrix" not in saved
    assert saved["soil_rgb_uncorrected"] is not None
    assert result.status == "pass"


BOUND_SOURCES = {
    "pipeline/qa.py": "bac8fe0b1ad179e999f7ec2b0d6718fd516fd0ee76f03c5b9f26723b3ca7c575",
    "card/design.py": "3821b5df5ab290d87178fadbffbbaafdddeaa229e25a79b1d1f2db35fad68820",
    "card/validate.py": "9fc732488419960c30259f0c5ada452f450468010733d59976f451a42100b5e9",
}


@pytest.mark.parametrize("path", sorted(BOUND_SOURCES))
def test_the_sources_bound_by_the_photo_privacy_configuration_are_unchanged(path: str) -> None:
    """These files are hashed into the photo-privacy configuration. A change here must be a
    deliberate package that re-derives that configuration, and must update this digest."""

    import hashlib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert hashlib.sha256((root / path).read_bytes()).hexdigest() == BOUND_SOURCES[path]


def vignetted(image: np.ndarray, fall: float) -> np.ndarray:
    height, width = image.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width]
    radius = np.hypot((xx - width / 2) / (width / 2), (yy - height / 2) / (height / 2))
    shaded = np.clip(image * (1 - fall * radius**2)[..., None], 0, 255)
    return np.asarray(shaded, dtype=np.uint8)


def uneven_scene(edition: str, position: str) -> np.ndarray:
    if edition == "node":
        return (
            with_node(flat_soil()) if position == "edge" else with_node(flat_soil(), x=320, y=270)
        )
    return with_a6(flat_soil()) if position == "edge" else with_a6(flat_soil(), x=440, y=340)


@pytest.mark.parametrize("edition", ["node", "a6"])
@pytest.mark.parametrize("position", ["edge", "centre"])
@pytest.mark.parametrize("fall", [0.15, 0.3, 0.45])
def test_uneven_light_is_not_reliably_caught_and_this_is_how_bad_it_gets(
    edition: str, position: str, fall: float
) -> None:
    """Light that differs between the card and the soil cannot be corrected from the card.

    The residual catches some of it and misses much of it. This pins, over every cast and two
    card positions, the largest error a normalised photo carried, so that the limit stated in
    SPEC section 17.3 and PHOTO_QA.md stays true. It is a measurement, not a guarantee."""

    errors = []
    for gains, gamma in CASTS:
        scene = vignetted(photographed(uneven_scene(edition, position), gains, gamma), fall)
        saved = evaluate_photo(jpeg(scene), accuracy_m=12).card_color_correction
        if saved is None or saved["normalised"] is False:
            continue
        errors.append(float(delta_e(np.array(saved["soil_rgb"]), np.array(SOIL_RGB))))
    if fall == 0.15:
        assert len(errors) == len(CASTS)
    assert all(error < 16.0 for error in errors)
    if position == "centre" and fall >= 0.3:
        # Stated limit: with the card in even light and darker soil around it, strong
        # unevenness is still normalised, and the error is far above the even-light 2.5.
        assert errors and max(errors) > 7.0


def test_soil_colour_comes_from_beside_the_card_not_from_across_the_frame() -> None:
    scene = flat_soil()
    scene[:, 900:] = np.clip(
        np.array([150, 120, 60], dtype=np.float64)
        + np.random.default_rng(1).normal(0, 14, (900, 300, 1)),
        0,
        255,
    ).astype(np.uint8)
    saved = record(evaluate_photo(jpeg(with_node(scene, x=60, y=250, width=480)), accuracy_m=12))
    assert saved["normalised"] is True
    near = float(delta_e(np.array(saved["soil_rgb"]), np.array(SOIL_RGB)))
    assert near < 2.5
    # The whole soil region, which includes the other soil, reads differently.
    from pipeline.cards import find_cards as locate
    from pipeline.qa_cards import soil_near_card, soil_region_without

    image = cv2.imdecode(
        np.frombuffer(sanitize_jpeg(jpeg(with_node(scene, x=60, y=250, width=480)))[0], np.uint8), 1
    )
    assert image is not None
    cards = locate(image)
    region = soil_region_without(image, cards.outlines)
    beside = soil_near_card(region.mask, cards.read_outline)
    assert 0 < int(beside.sum()) < int(region.mask.sum()) / 3
    assert not bool(beside[:, 900:].any())
    assert bool((beside <= region.mask).all())


def test_an_absurd_outline_is_ignored_instead_of_hiding_the_whole_photo() -> None:
    from pipeline.qa_cards import soil_region_without

    image = soil_texture(13)
    huge = np.array([[-9000.0, -9000.0], [9000.0, -9000.0], [9000.0, 9000.0], [-9000.0, 9000.0]])
    broken = np.array([[np.nan, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    region = soil_region_without(image, (huge, broken))
    assert region.fraction == 1.0 and not region.card_found
    real = np.array([[100.0, 100.0], [400.0, 100.0], [400.0, 300.0], [100.0, 300.0]])
    assert 0.9 < soil_region_without(image, (huge, real)).fraction < 1.0


def test_a_failure_while_fitting_never_costs_the_photo_its_qa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pipeline.qa_cards as subject

    def explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("unexpected")

    monkeypatch.setattr(subject, "colour_record", explode)
    result = subject.evaluate_photo_with_cards(jpeg(with_node(soil_texture(1))), accuracy_m=12)
    assert result.status == "pass" and result.card_detected
    assert result.card_color_correction is None and result.calibration_status == "uncalibrated"


# ---- the fit itself -----------------------------------------------------------------------

NODE_TARGETS = {patch.name: patch.rgb for patch in (*NODE_PATCHES, *RAMP)}
RAMP_NAMES = tuple(step.name for step in RAMP)


def through_camera(
    rgb: tuple[int, int, int], gains: tuple[float, float, float], gamma: float
) -> tuple[int, int, int]:
    out = np.clip(np.array(rgb) / 255.0 * np.array(gains), 0, 1) ** gamma * 255
    return (int(round(out[0])), int(round(out[1])), int(round(out[2])))


def test_reference_values_fit_themselves_exactly() -> None:
    correction = fit(NODE_TARGETS, NODE_TARGETS, RAMP_NAMES)
    assert correction.residual_delta_e < 0.01
    probe = np.array([[141.0, 104.0, 77.0], [20.0, 30.0, 40.0], [250.0, 240.0, 230.0]])
    assert np.allclose(apply(correction, probe), probe, atol=0.5)


@pytest.mark.parametrize(("gains", "gamma"), CASTS)
def test_the_fit_undoes_a_cast_and_tone_curve_on_an_unseen_colour(
    gains: tuple[float, float, float], gamma: float
) -> None:
    measured = {name: through_camera(rgb, gains, gamma) for name, rgb in NODE_TARGETS.items()}
    correction = fit(measured, NODE_TARGETS, RAMP_NAMES)
    assert correction.within_limit
    seen = np.array(through_camera(SOIL_RGB, gains, gamma), dtype=np.float64)
    assert float(delta_e(apply(correction, seen), np.array(SOIL_RGB))) < 3.5


def test_fits_that_cannot_be_trusted_are_refused() -> None:
    with pytest.raises(ValueError, match="every reference patch"):
        fit({name: rgb for name, rgb in NODE_TARGETS.items() if name != "sky"}, NODE_TARGETS)
    flat = {name: (100, 100, 100) for name in NODE_TARGETS}
    with pytest.raises(ValueError, match="span colour space"):
        fit(flat, NODE_TARGETS)
    swapped = dict(NODE_TARGETS)
    swapped["ramp_1"], swapped["ramp_3"] = swapped["ramp_3"], swapped["ramp_1"]
    with pytest.raises(ValueError, match="does not rise"):
        fit(swapped, NODE_TARGETS, RAMP_NAMES)
    with pytest.raises(ValueError, match="incomplete"):
        fit(NODE_TARGETS, NODE_TARGETS, ("ramp_0", "ramp_1"))


def test_lab_matches_published_values() -> None:
    assert np.allclose(srgb_to_lab(np.array([255, 255, 255])), [100, 0, 0], atol=0.02)
    assert np.allclose(srgb_to_lab(np.array([0, 0, 0])), [0, 0, 0], atol=0.02)
    assert np.allclose(srgb_to_lab(np.array([255, 0, 0])), [53.24, 80.09, 67.20], atol=0.05)
    assert np.allclose(srgb_to_lab(np.array([0, 0, 255])), [32.30, 79.19, -107.86], atol=0.05)


def test_soil_colour_uses_only_masked_pixels_and_handles_an_empty_mask() -> None:
    image = np.zeros((40, 40, 3), np.uint8)
    image[:, :20] = (77, 104, 141)
    image[:, 20:] = (255, 255, 255)
    mask = np.zeros((40, 40), np.uint8)
    mask[:, :20] = 1
    colour = soil_colour(image, mask, None)
    assert colour is not None and colour[0] == (141.0, 104.0, 77.0)
    assert soil_colour(image, np.zeros((40, 40), np.uint8), None) is None
