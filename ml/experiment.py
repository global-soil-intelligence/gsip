"""Reproducible local SOC baselines with spatially separated calibration/test data."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import h3  # type: ignore[import-untyped]
import numpy as np

from ml.features import (
    CONTEXT_FEATURES,
    FEATURE_VERSION,
    IMAGE_FEATURES,
    fused_features,
    image_features,
)
from ml.pilot import Sample, fingerprint, read_samples

FEATURES = ["prior_soc", *IMAGE_FEATURES, *CONTEXT_FEATURES]
POLICY = {
    "minimum_train_blocks": 30,
    "minimum_calibration_blocks": 20,
    "minimum_test_blocks": 20,
    "minimum_relative_mae_improvement": 0.10,
    "target_coverage": 0.90,
}


def spatial_split(samples: list[Sample]) -> tuple[list[str], list[str]]:
    # Connected components keep both repeated sites and H3-r4 cells together,
    # including sites whose samples straddle a cell boundary.
    parents = list(range(len(samples)))

    def find(i: int) -> int:
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    seen: dict[str, int] = {}
    for i, sample in enumerate(samples):
        for key in (f"site:{sample.site_id}", f"cell:{h3.cell_to_parent(sample.h3_r8, 4)}"):
            if key in seen:
                parents[find(i)] = find(seen[key])
            seen[key] = i
    components: dict[int, list[str]] = {}
    for i, sample in enumerate(samples):
        components.setdefault(find(i), []).append(h3.cell_to_parent(sample.h3_r8, 4))
    keys = {root: min(cells) for root, cells in components.items()}
    groups = [keys[find(i)] for i in range(len(samples))]
    ordered = sorted(
        set(groups), key=lambda k: hashlib.sha256(f"gsip-soc-v1:{k}".encode()).digest()
    )
    if len(ordered) < 5:
        raise ValueError("at least five independent spatial blocks are needed for an experiment")
    n_holdout = max(1, len(ordered) // 5)
    test = set(ordered[:n_holdout])
    calibration = set(ordered[n_holdout : 2 * n_holdout])
    splits = [
        "test" if g in test else "calibration" if g in calibration else "train" for g in groups
    ]
    return groups, splits


def fit_ridge(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    center = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-8] = 1.0
    design = np.column_stack([np.ones(len(x)), (x - center) / scale])
    penalty = np.eye(design.shape[1])
    penalty[0, 0] = 0
    weights = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return {"center": center.tolist(), "scale": scale.tolist(), "weights": weights.tolist()}


def ridge_predict(model: dict[str, Any], x: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), (x - model["center"]) / model["scale"]])
    return np.asarray(design @ model["weights"], dtype=np.float64)


def conformal_radius(errors: np.ndarray, groups: list[str]) -> float | None:
    # One maximum error per calibration block avoids treating clustered photos
    # as independent calibration examples. Generalization still needs field review.
    scores = sorted(
        max(float(e) for e, g in zip(errors, groups, strict=True) if g == group)
        for group in set(groups)
    )
    rank = math.ceil((len(scores) + 1) * POLICY["target_coverage"])
    return scores[rank - 1] if rank <= len(scores) else None


def metrics(
    y: np.ndarray,
    prediction: np.ndarray,
    groups: list[str],
    lower: np.ndarray | None = None,
    upper: np.ndarray | None = None,
) -> dict[str, Any]:
    errors = prediction - y
    block_mae = [
        float(np.abs(errors[np.array(groups) == group]).mean()) for group in sorted(set(groups))
    ]
    return {
        "samples": len(y),
        "blocks": len(set(groups)),
        "mae_g_kg": float(np.abs(errors).mean()),
        "block_balanced_mae_g_kg": float(np.mean(block_mae)),
        "rmse_g_kg": float(np.sqrt(np.mean(errors**2))),
        "bias_g_kg": float(errors.mean()),
        "interval_coverage": float(np.mean((y >= lower) & (y <= upper)))
        if lower is not None and upper is not None
        else None,
        "mean_interval_width_g_kg": float(np.mean(upper - lower))
        if lower is not None and upper is not None
        else None,
    }


def improvement_lower_bound(
    y: np.ndarray, baseline: np.ndarray, fused: np.ndarray, groups: list[str]
) -> float:
    improvement = np.abs(y - baseline) - np.abs(y - fused)
    values = np.array(
        [improvement[np.array(groups) == group].mean() for group in sorted(set(groups))]
    )
    rng = np.random.default_rng(20260914)
    boot = rng.choice(values, size=(2000, len(values)), replace=True).mean(axis=1)
    return float(np.quantile(boot, 0.025))


def train_experiment(path: Path) -> dict[str, Any]:
    samples = sorted(read_samples(path), key=lambda s: s.sample_id)
    extracted = [image_features(s, path.parent) for s in samples]
    hashes = [digest for _, digest in extracted]
    if len(set(hashes)) != len(hashes):
        raise ValueError("duplicate image bytes across samples; audit repeated observations")
    x = np.array(
        [fused_features(s, features) for s, (features, _) in zip(samples, extracted, strict=True)]
    )
    y = np.array([s.lab.value for s in samples])
    groups, splits = spatial_split(samples)
    training = np.array([split == "train" for split in splits])
    calibration = np.array([split == "calibration" for split in splits])
    testing = np.array([split == "test" for split in splits])
    test_groups = [g for g, is_test in zip(groups, testing, strict=True) if is_test]
    calibration_groups = [g for g, selected in zip(groups, calibration, strict=True) if selected]
    context_indexes = [0, *range(1 + len(IMAGE_FEATURES), len(FEATURES))]
    models = {
        "image_only": fit_ridge(x[training, 1 : 1 + len(IMAGE_FEATURES)], y[training]),
        "prior_context": fit_ridge(x[training][:, context_indexes], y[training]),
        "combined": fit_ridge(x[training], y[training] - x[training, 0]),
    }
    predictions = {
        "map_only": x[:, 0],
        "image_only": np.clip(
            ridge_predict(models["image_only"], x[:, 1 : 1 + len(IMAGE_FEATURES)]), 0, 1000
        ),
        "prior_context": np.clip(
            ridge_predict(models["prior_context"], x[:, context_indexes]), 0, 1000
        ),
        "combined": np.clip(x[:, 0] + ridge_predict(models["combined"], x), 0, 1000),
    }
    radius = conformal_radius(
        np.abs(y[calibration] - predictions["combined"][calibration]), calibration_groups
    )
    lower = np.clip(predictions["combined"] - radius, 0, 1000) if radius is not None else None
    upper = np.clip(predictions["combined"] + radius, 0, 1000) if radius is not None else None
    comparison = {}
    for name, values in predictions.items():
        lo = lower[testing] if name == "combined" and lower is not None else None
        hi = upper[testing] if name == "combined" and upper is not None else None
        if name == "map_only":
            lo = np.array(
                [s.prior.lower for s, selected in zip(samples, testing, strict=True) if selected]
            )
            hi = np.array(
                [s.prior.upper for s, selected in zip(samples, testing, strict=True) if selected]
            )
        comparison[name] = metrics(y[testing], values[testing], test_groups, lo, hi)
    counts = {
        name: len({g for g, split in zip(groups, splits, strict=True) if split == name})
        for name in ("train", "calibration", "test")
    }
    reasons = []
    for name, count in counts.items():
        if count < POLICY[f"minimum_{name}_blocks"]:
            reasons.append(f"insufficient_{name}_blocks")
    if any(s.is_synthetic for s in samples):
        reasons.append("synthetic_data_present")
    gains = {}
    for baseline in ("map_only", "prior_context"):
        base_mae = comparison[baseline]["block_balanced_mae_g_kg"]
        model_mae = comparison["combined"]["block_balanced_mae_g_kg"]
        relative = (base_mae - model_mae) / base_mae if base_mae > 0 else 0.0
        gains[baseline] = improvement_lower_bound(
            y[testing],
            predictions[baseline][testing],
            predictions["combined"][testing],
            test_groups,
        )
        if relative < POLICY["minimum_relative_mae_improvement"] or gains[baseline] <= 0:
            reasons.append(f"no_demonstrated_improvement_over_{baseline}")
    if radius is None or comparison["combined"]["interval_coverage"] < POLICY["target_coverage"]:
        reasons.append("insufficient_interval_coverage")
    strata: dict[str, dict[str, Any]] = {}
    for field in ("phone_group", "lighting", "surface_condition"):
        strata[field] = {}
        for value in sorted({str(getattr(s, field)) for s in samples}):
            selected = testing & np.array([getattr(s, field) == value for s in samples])
            if not selected.any():
                continue
            strata[field][value] = metrics(
                y[selected],
                predictions["combined"][selected],
                [g for g, keep in zip(groups, selected, strict=True) if keep],
                lower[selected] if lower is not None else None,
                upper[selected] if upper is not None else None,
            )
    training_samples = [s for s, keep in zip(samples, training, strict=True) if keep]
    return {
        "schema_version": "gsip-soc-experiment-v1",
        "feature_version": FEATURE_VERSION,
        "features": FEATURES,
        "dataset_sha256": fingerprint(samples, hashes),
        "property": "soc",
        "unit": "g/kg",
        "depth_top_cm": 0,
        "depth_bottom_cm": 5,
        "region": samples[0].region,
        "prior_source": samples[0].prior.source,
        "prior_version": samples[0].prior.version,
        "models": models,
        "conformal_radius": radius,
        "domain": {
            "minimum": x[training].min(axis=0).tolist(),
            "maximum": x[training].max(axis=0).tolist(),
            "h3_r3": sorted({h3.cell_to_parent(s.h3_r8, 3) for s in training_samples}),
            "phone_groups": sorted({s.phone_group for s in training_samples}),
            "lighting": sorted({s.lighting for s in training_samples}),
            "surface_conditions": sorted({s.surface_condition for s in training_samples}),
        },
        "report": {
            "status": "HOLD" if reasons else "RESEARCH_CANDIDATE",
            "reasons": reasons,
            "public_release_approved": False,
            "policy": POLICY,
            "spatial_block_counts": counts,
            "comparison": comparison,
            "improvement_95pct_lower_bound_g_kg": gains,
            "test_strata": strata,
            "split_manifest": [
                {"sample_id": s.sample_id, "block": g, "split": split}
                for s, g, split in zip(samples, groups, splits, strict=True)
            ],
            "limitations": [
                "Research baselines; no measured or reconstructed spectrum.",
                "RGB features are uncalibrated; ROI selection is manually reviewed.",
                "Block splits have no distance buffer; adjacent blocks may remain correlated.",
                "Intervals assume exchangeable blocks; domain shift can break coverage.",
                "Lab review is a human attestation; document checksums only prove file identity.",
                "Do not tune against this holdout; new releases need fresh evaluation.",
                "Passing gates does not authorize deployment or establish global validity.",
            ],
        },
    }
