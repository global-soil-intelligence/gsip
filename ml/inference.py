"""Local research inference with explicit reasons for withholding a correction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h3  # type: ignore[import-untyped]
import numpy as np

from ml.experiment import FEATURES, ridge_predict
from ml.features import FEATURE_VERSION, fused_features, image_features
from ml.pilot import Observation


def predict(
    observation: Observation, root: Path, artifact: dict[str, Any] | None
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "PRIOR_ONLY",
        "prediction": None,
        "prior": observation.prior.model_dump(),
        "basis": ["existing_soil_map"],
        "public_release_approved": False,
        "reason": "no_validated_model",
    }
    if artifact is None:
        return result
    if (
        artifact.get("schema_version") != "gsip-soc-experiment-v1"
        or artifact.get("feature_version") != FEATURE_VERSION
        or artifact.get("features") != FEATURES
    ):
        raise ValueError("unsupported model/feature schema")
    if artifact["report"]["status"] != "RESEARCH_CANDIDATE":
        result["reason"] = "model_on_hold"
        return result
    if observation.is_synthetic:
        result["reason"] = "synthetic_observation"
        return result
    domain = artifact["domain"]
    if (
        observation.region != artifact["region"]
        or observation.prior.source != artifact["prior_source"]
        or observation.prior.version != artifact["prior_version"]
        or h3.cell_to_parent(observation.h3_r8, 3) not in domain["h3_r3"]
        or observation.phone_group not in domain["phone_groups"]
        or observation.lighting not in domain["lighting"]
        or observation.surface_condition not in domain["surface_conditions"]
    ):
        result["reason"] = "outside_validated_scope"
        return result
    try:
        features, _ = image_features(observation, root)
    except (ValueError, OSError):
        result["reason"] = "image_unusable"
        return result
    vector = np.array(fused_features(observation, features))
    minimum, maximum = np.array(domain["minimum"]), np.array(domain["maximum"])
    # This deliberately conservative range screen is a first check, not a
    # claim to detect every unfamiliar soil or combination of characteristics.
    if np.any(vector < minimum - 1e-8) or np.any(vector > maximum + 1e-8):
        result["reason"] = "image_or_context_outside_training_range"
        return result
    radius = artifact["conformal_radius"]
    if radius is None or not np.isfinite(radius) or radius < 0:
        raise ValueError("candidate lacks a finite calibrated interval")
    correction = float(ridge_predict(artifact["models"]["combined"], vector[None, :])[0])
    value = float(np.clip(observation.prior.mean + correction, 0, 1000))
    if not np.isfinite(value):
        raise ValueError("model returned a non-finite prediction")
    result.update(
        {
            "status": "RESEARCH_ESTIMATE",
            "reason": None,
            "basis": [
                "existing_soil_map",
                "rgb_surface_features",
                "field_conditions",
                "lab_trained_model",
            ],
            "model_dataset_sha256": artifact["dataset_sha256"],
            "prediction": {
                "property": "soc",
                "unit": "g/kg",
                "value": value,
                "lower": max(0, value - radius),
                "upper": min(1000, value + radius),
                "nominal_interval_coverage": 0.9,
                "depth_top_cm": 0,
                "depth_bottom_cm": 5,
            },
            "limitations": [
                "Uncalibrated RGB features, not measured spectroscopy.",
                "Research only; prediction intervals may fail under domain shift.",
            ],
        }
    )
    return result
