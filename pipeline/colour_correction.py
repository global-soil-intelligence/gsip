"""Per-photo colour correction fitted to a photographed reference card (SPEC section 17.3).

Pure functions: no file, network or database access. The photograph is never altered; the
correction produces numbers that are stored beside it.

The reference values are the card's digital targets. Until a print run has been measured with an
instrument, the correction brings different phones and lights toward a common scale. It does not
make a colour colorimetrically true."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

Rgb = tuple[int, int, int]

CORRECTION_VERSION = 2
# Largest colour difference (CIE76, D65) allowed between a reference value and the correction's
# prediction for a patch left out of the affine fit. Set on synthetic photographs only; a printed
# card and a real phone will need it set again.
MAX_RESIDUAL_DELTA_E = 5.0
# At most this many soil pixels are corrected to summarise the soil colour.
MAX_SOIL_SAMPLES = 200_000
MIN_PATCHES = 6


@dataclass(frozen=True)
class Correction:
    """A neutral tone curve (optional) followed by an affine map, both in sRGB code values."""

    tone_seen: tuple[tuple[float, float, float], ...] | None
    tone_want: tuple[tuple[float, float, float], ...] | None
    matrix: tuple[tuple[float, float, float], ...]
    # Worst leave-one-patch-out colour difference.
    residual_delta_e: float

    @property
    def method(self) -> str:
        return "ramp-tone-then-affine" if self.tone_seen is not None else "affine"

    @property
    def within_limit(self) -> bool:
        return self.residual_delta_e <= MAX_RESIDUAL_DELTA_E


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """CIELAB (D65) of sRGB code values 0 to 255, any shape ending in 3."""

    encoded = np.clip(np.asarray(rgb, dtype=np.float64), 0.0, 255.0) / 255.0
    linear = np.where(encoded <= 0.04045, encoded / 12.92, ((encoded + 0.055) / 1.055) ** 2.4)
    xyz = linear @ np.array(
        [
            [0.4124564, 0.2126729, 0.0193339],
            [0.3575761, 0.7151522, 0.1191920],
            [0.1804375, 0.0721750, 0.9503041],
        ]
    )
    scaled = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(scaled > 216 / 24389, np.cbrt(scaled), (24389 / 27 * scaled + 16) / 116)
    return np.stack(
        [116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])],
        axis=-1,
    )


def delta_e(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    """CIE76 colour difference between sRGB code values."""

    return np.asarray(np.linalg.norm(srgb_to_lab(first) - srgb_to_lab(second), axis=-1))


def _tone(rgb: np.ndarray, seen: np.ndarray, want: np.ndarray) -> np.ndarray:
    # Outside the ramp the end segments are extended, so a soil darker than the darkest step
    # is not clamped to it.
    out = np.empty_like(rgb, dtype=np.float64)
    for channel in range(3):
        x, y = seen[:, channel], want[:, channel]
        values = rgb[..., channel].astype(np.float64)
        inside = np.interp(values, x, y)
        low = y[0] + (values - x[0]) * (y[1] - y[0]) / (x[1] - x[0])
        high = y[-1] + (values - x[-1]) * (y[-1] - y[-2]) / (x[-1] - x[-2])
        out[..., channel] = np.where(values < x[0], low, np.where(values > x[-1], high, inside))
    return out


def _design(rgb: np.ndarray) -> np.ndarray:
    return np.concatenate([rgb / 255.0, np.ones((*rgb.shape[:-1], 1))], axis=-1)


def apply(correction: Correction, rgb: np.ndarray) -> np.ndarray:
    """Corrected sRGB code values (floats, not clipped) for RGB values of any shape ending in 3."""

    values = np.asarray(rgb, dtype=np.float64)
    if correction.tone_seen is not None and correction.tone_want is not None:
        values = _tone(values, np.array(correction.tone_seen), np.array(correction.tone_want))
    return np.asarray(_design(values) @ np.array(correction.matrix)) * 255.0


def fit(
    measured: Mapping[str, Rgb],
    targets: Mapping[str, Rgb],
    ramp: Sequence[str] = (),
) -> Correction:
    """Fit the correction that takes the photographed patches to their reference values.

    ``ramp`` names the neutral steps from dark to light, when the card has them. Raises
    ValueError when the patches cannot support a fit."""

    names = [name for name in targets if name in measured]
    if len(names) < MIN_PATCHES or len(names) != len(targets):
        raise ValueError("every reference patch must be measured to fit a correction")
    seen = np.array([measured[name] for name in names], dtype=np.float64)
    want = np.array([targets[name] for name in names], dtype=np.float64)
    tone_seen = tone_want = None
    worked = seen
    if ramp:
        if len(ramp) < 3 or any(name not in measured for name in ramp):
            raise ValueError("the neutral ramp is incomplete")
        tone_seen = np.array([measured[name] for name in ramp], dtype=np.float64)
        tone_want = np.array([targets[name] for name in ramp], dtype=np.float64)
        if bool((np.diff(tone_seen, axis=0) <= 0).any()):
            raise ValueError("the neutral ramp does not rise in every channel")
        worked = _tone(seen, tone_seen, tone_want)
    design = _design(worked)
    if np.linalg.matrix_rank(design, tol=1e-3) < 4:
        raise ValueError("the reference patches do not span colour space")
    matrix, *_ = np.linalg.lstsq(design, want / 255.0, rcond=None)
    if not bool(np.isfinite(matrix).all()):
        raise ValueError("the correction could not be fitted")
    # Leave each patch out in turn, refit, and see how well it is predicted. An in-sample
    # residual flatters a fit with few patches. The tone curve is not refitted, so on a card
    # with a ramp this is still somewhat optimistic.
    held_out = []
    for index in range(len(names)):
        keep = np.arange(len(names)) != index
        if np.linalg.matrix_rank(design[keep], tol=1e-3) < 4:
            raise ValueError("the reference patches do not span colour space")
        partial, *_ = np.linalg.lstsq(design[keep], want[keep] / 255.0, rcond=None)
        held_out.append(float(delta_e(design[index] @ partial * 255.0, want[index])))

    def rows(values: np.ndarray | None) -> tuple[tuple[float, float, float], ...] | None:
        if values is None:
            return None
        return tuple((float(r), float(g), float(b)) for r, g, b in values)

    return Correction(rows(tone_seen), rows(tone_want), rows(matrix) or (), round(max(held_out), 3))


def soil_colour(
    image_bgr: np.ndarray, mask: np.ndarray, correction: Correction | None
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Median soil colour as (sRGB, CIELAB) over the masked soil pixels, corrected when given.

    None when the mask selects no pixel."""

    pixels = image_bgr[mask.astype(bool)]
    if pixels.size == 0:
        return None
    step = max(1, len(pixels) // MAX_SOIL_SAMPLES)
    rgb = pixels[::step, ::-1].astype(np.float64)
    if correction is not None:
        rgb = apply(correction, rgb)
    median = np.clip(np.median(rgb, axis=0), 0.0, 255.0)
    lab = srgb_to_lab(median)
    return (
        (round(float(median[0]), 1), round(float(median[1]), 1), round(float(median[2]), 1)),
        (round(float(lab[0]), 2), round(float(lab[1]), 2), round(float(lab[2]), 2)),
    )
