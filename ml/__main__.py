from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ml.experiment import train_experiment
from ml.inference import predict
from ml.pilot import Observation, read_samples
from ml.prior_cache import lookup_prior


def template() -> dict[str, Any]:
    return {
        "submission_id": "COPY_FROM_MY_OBSERVATIONS",
        "sample_id": "YOUR_LAB_SAMPLE_ID",
        "site_id": "YOUR_SITE_ID",
        "region": "YOUR_PILOT_REGION",
        "h3_r8": "YOUR_PUBLIC_H3_R8_CELL",
        "depth_top_cm": 0,
        "depth_bottom_cm": 5,
        "image_path": "photos/sample-B.jpg",
        "soil_roi": [0, 0, 128, 128],
        "roi_verified": False,
        "phone_group": "PHONE_MODEL_FAMILY",
        "lighting": "diffuse_daylight",
        "surface_condition": "dry",
        "is_synthetic": False,
        "prior": {
            "source": "SoilGrids",
            "version": "PINNED_SOURCE_VERSION",
            "property": "soc",
            "unit": "g/kg",
            "depth_top_cm": 0,
            "depth_bottom_cm": 5,
            "mean": None,
            "lower": None,
            "upper": None,
        },
        "lab": {
            "sample_id": "YOUR_LAB_SAMPLE_ID",
            "lab_name": "LAB_NAME",
            "method": "LAB_SOC_METHOD",
            "document_sha256": "SHA256_OF_LAB_REPORT",
            "document_path": "lab/sample-report.pdf",
            "verified_by": "REVIEWER",
            "verified": False,
            "property": "soc",
            "unit": "g/kg",
            "depth_top_cm": 0,
            "depth_bottom_cm": 5,
            "value": None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="GSIP local soil-carbon research pipeline")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("template", help="Print an intentionally incomplete photo/lab record")
    status = commands.add_parser("status", help="Check supplied pilot pairs without training")
    status.add_argument("--dataset", type=Path)
    train = commands.add_parser("train", help="Train and compare the four research baselines")
    train.add_argument("--dataset", type=Path, required=True)
    train.add_argument("--output", type=Path, required=True)
    inference = commands.add_parser(
        "predict", help="Predict locally or explain why only priors apply"
    )
    inference.add_argument("--observation", type=Path, required=True)
    inference.add_argument("--model", type=Path)
    cache = commands.add_parser("prior", help="Read a pinned offline soil-map cache record")
    cache.add_argument("--cache", type=Path, required=True)
    cache.add_argument("--cell", required=True)
    cache.add_argument("--source", required=True)
    cache.add_argument("--version", required=True)
    args = parser.parse_args()
    try:
        if args.command == "template":
            result = template()
        elif args.command == "status":
            samples = read_samples(args.dataset) if args.dataset else []
            result = {
                "status": "READY_FOR_EXPERIMENT" if samples else "AWAITING_PAIRED_LAB_DATA",
                "structurally_valid_pairs_supplied": len(samples),
                "synthetic_pairs": sum(s.is_synthetic for s in samples),
                "trained_model_evaluated": False,
                "public_release_approved": False,
                "next_step": "Audit paired lab records, then run a spatially held-out experiment.",
            }
        elif args.command == "train":
            if args.output.exists():
                raise ValueError("output exists; choose a new immutable experiment filename")
            result = train_experiment(args.dataset)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x") as stream:
                stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
            result = result["report"]
        elif args.command == "predict":
            observation = Observation.model_validate_json(args.observation.read_text())
            artifact = json.loads(args.model.read_text()) if args.model else None
            result = predict(observation, args.observation.parent, artifact)
        else:
            result = lookup_prior(args.cache, args.cell, args.source, args.version).model_dump()
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, OSError) as error:
        parser.exit(2, f"Pilot input rejected: {error}\n")


if __name__ == "__main__":
    main()
