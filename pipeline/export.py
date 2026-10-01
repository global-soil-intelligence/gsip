from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from datasets import Dataset, load_dataset  # type: ignore[import-untyped]
from huggingface_hub import HfApi

from pipeline.qa import has_embedded_metadata, sanitize_jpeg

FORBIDDEN_PUBLIC_KEYS = {
    "camera_metadata_private",
    "contributor_id",
    "device_model",
    "geom_precise",
    "gps_accuracy_m",
    "grant_id",
    "latitude",
    "longitude",
}


@dataclass(frozen=True)
class Grant:
    attribution_name: str
    data_license: str
    photo_license: str
    terms_version: str


@dataclass(frozen=True)
class ExportPhoto:
    shot_type: str
    storage_path: str


@dataclass(frozen=True)
class ExportSubmission:
    captured_at: str
    disturbed: bool | None
    grant: Grant | None
    gold_labels: tuple[dict[str, Any], ...]
    h3_r6: str
    h3_r8: str
    id: str
    is_synthetic: bool
    land_cover: str | None
    photos: tuple[ExportPhoto, ...]
    precip_flag: bool | None
    priors: tuple[dict[str, Any], ...]
    status: str
    surface_condition: str | None


def assert_public_record(value: Any, path: str = "record") -> None:
    if isinstance(value, dict):
        forbidden = FORBIDDEN_PUBLIC_KEYS.intersection(value)
        if forbidden:
            raise ValueError(f"{path} contains forbidden private fields: {sorted(forbidden)}")
        for key, child in value.items():
            assert_public_record(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            assert_public_record(child, f"{path}[{index}]")


def dataset_card(records: list[dict[str, Any]], export_date: date) -> str:
    attributions = sorted(
        {str(photo["attribution_name"]) for record in records for photo in record["photos"]}
    )
    attribution_list = "\n".join(f"- {name}" for name in attributions) or "- None"
    return f"""---
license: other
license_name: ODbL-1.0 structured data; CC-BY-SA-4.0 photographs
language:
- en
pretty_name: Global Soil Intelligence Project public contributions
---

# GSIP public soil contributions

Export date: {export_date.isoformat()}. Rows: {len(records)}. This release contains only QA-passed,
non-synthetic contributions with immutable contribution grants. Locations are H3 cells, never
precise points.

## Licenses

Structured/database content is provided under the Open Database License 1.0 (ODbL-1.0).
Sanitized contributed photographs are provided separately under CC BY-SA 4.0. Contributors retain
ownership. SoilGrids-derived prior values retain ISRIC attribution and their source license.

## Photo attribution

{attribution_list}

## Schema

Each row contains a submission ID, H3-r8 and H3-r6 cells, protocol metadata, sanitized photo paths,
canonical prior values with uncertainty, and any verified gold labels. No precise geometry, GPS
accuracy, contributor ID, device model, private camera metadata, EXIF, or XMP is included.

## Citation

```bibtex
@dataset{{gsip_{export_date.strftime("%Y%m%d")},
  title = {{Global Soil Intelligence Project public contributions}},
  year = {{{export_date.year}}},
  publisher = {{Global Soil Intelligence Project}},
  note = {{ODbL-1.0 structured data; CC BY-SA 4.0 photos}}
}}
```
"""


def _manifest(target: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(target.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files[str(path.relative_to(target))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def build_export(
    submissions: list[ExportSubmission],
    output_root: Path,
    export_date: date,
    photo_loader: Callable[[str], bytes],
) -> Path:
    qualifying = sorted(
        (
            submission
            for submission in submissions
            if submission.status == "qa_pass" and not submission.is_synthetic
        ),
        key=lambda submission: submission.id,
    )
    target = output_root / export_date.isoformat()
    temporary = output_root / f".{export_date.isoformat()}.building"
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    try:
        for submission in qualifying:
            if submission.photos and submission.grant is None:
                raise ValueError(f"Submission {submission.id} has photos but no immutable grant")
            public_photos: list[dict[str, Any]] = []
            for photo in sorted(submission.photos, key=lambda item: item.shot_type):
                if submission.grant is None:
                    raise ValueError("Photo export requires a contribution grant")
                raw_photo = photo_loader(photo.storage_path)
                if has_embedded_metadata(raw_photo):
                    raise ValueError("Canonical export photo contains embedded metadata")
                sanitized, _ = sanitize_jpeg(raw_photo)
                if has_embedded_metadata(sanitized):
                    raise ValueError("Export photo metadata scan failed")
                relative = Path("photos") / submission.id / f"{photo.shot_type}.jpg"
                destination = temporary / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(sanitized)
                public_photos.append(
                    {
                        "attribution_name": submission.grant.attribution_name,
                        "license": submission.grant.photo_license,
                        "path": str(relative),
                        "shot_type": photo.shot_type,
                    }
                )
            record = {
                "captured_at": submission.captured_at[:10],
                "disturbed": submission.disturbed,
                "gold_labels": list(submission.gold_labels),
                "h3_r6": submission.h3_r6,
                "h3_r8": submission.h3_r8,
                "id": submission.id,
                "land_cover": submission.land_cover,
                "photos": public_photos,
                "precip_flag": submission.precip_flag,
                "priors": list(submission.priors),
                "status": submission.status,
                "surface_condition": submission.surface_condition,
            }
            assert_public_record(record)
            records.append(record)
        data_dir = temporary / "data"
        data_dir.mkdir()
        if records:
            parquet = data_dir / "train.parquet"
            Dataset.from_list(records).to_parquet(str(parquet))
            loaded = load_dataset("parquet", data_files=str(parquet), split="train")
            if len(loaded) != len(records):
                raise ValueError("Hugging Face Datasets round-trip changed the row count")
        else:
            (data_dir / "EMPTY.md").write_text(
                "No non-synthetic QA-passed contributions were available for this export.\n",
                encoding="utf-8",
            )
        (temporary / "README.md").write_text(dataset_card(records, export_date), encoding="utf-8")
        (temporary / "manifest.json").write_text(
            json.dumps(_manifest(temporary), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if target.exists():
            shutil.rmtree(target)
        temporary.replace(target)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return target


class SupabaseExportSource:
    def __init__(self, url: str, service_key: str) -> None:
        self.url = url.rstrip("/")
        self.client = httpx.Client(
            timeout=60,
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        )

    def _rows(self, path: str, page_size: int = 1000) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        expected_total: int | None = None
        for start in range(0, 2_147_483_647, page_size):
            response = self.client.get(
                f"{self.url}/rest/v1/{path}",
                headers={
                    "Prefer": "count=exact",
                    "Range": f"{start}-{start + page_size - 1}",
                },
            )
            response.raise_for_status()
            page: list[dict[str, Any]] = response.json()
            content_range = response.headers.get("Content-Range")
            if content_range and "/" in content_range:
                total_text = content_range.rsplit("/", 1)[1]
                if total_text != "*":
                    expected_total = int(total_text)
            rows.extend(page)
            if expected_total is not None and len(rows) >= expected_total:
                if len(rows) != expected_total:
                    raise ValueError("PostgREST pagination returned an inconsistent row count")
                return rows
            if len(page) < page_size:
                if expected_total is not None and len(rows) != expected_total:
                    raise ValueError("PostgREST truncated a paginated export response")
                return rows
            if not page:
                raise ValueError("PostgREST pagination made no progress")
        raise ValueError("PostgREST pagination exceeded the supported row range")

    def photo(self, storage_path: str) -> bytes:
        path = quote(storage_path, safe="/")
        response = self.client.get(
            f"{self.url}/storage/v1/object/authenticated/submission-photos/{path}"
        )
        response.raise_for_status()
        return response.content

    def submissions(self) -> list[ExportSubmission]:
        rows = self._rows(
            "submissions?status=eq.qa_pass&is_synthetic=eq.false&order=id&select="
            "id,h3_r8,h3_r6,captured_at,land_cover,surface_condition,disturbed,"
            "precip_flag,status,is_synthetic,grant_id"
        )
        exported: list[ExportSubmission] = []
        for row in rows:
            submission_id = str(row["id"])
            grants = self._rows(
                "contribution_grants?"
                f"id=eq.{row['grant_id']}&select=attribution_name,data_license,photo_license,terms_version"
            )
            grant = Grant(**grants[0]) if grants else None
            photos = tuple(
                ExportPhoto(**photo)
                for photo in self._rows(
                    f"photos?submission_id=eq.{submission_id}&order=shot_type&select=shot_type,storage_path"
                )
            )
            priors = tuple(
                self._rows(
                    f"priors?submission_id=eq.{submission_id}&order=source,property,depth_top_cm"
                    "&select=source,property,value,uncertainty_lo,uncertainty_hi,unit,depth_top_cm,depth_bottom_cm"
                )
            )
            gold = tuple(
                self._rows(
                    f"gold_labels?submission_id=eq.{submission_id}&order=property,depth_top_cm"
                    "&select=lab_name,method,property,value,uncertainty,unit,depth_top_cm,depth_bottom_cm"
                )
            )
            exported.append(
                ExportSubmission(
                    captured_at=str(row["captured_at"]),
                    disturbed=row["disturbed"],
                    grant=grant,
                    gold_labels=gold,
                    h3_r6=str(row["h3_r6"]),
                    h3_r8=str(row["h3_r8"]),
                    id=submission_id,
                    is_synthetic=bool(row["is_synthetic"]),
                    land_cover=row["land_cover"],
                    photos=photos,
                    precip_flag=row["precip_flag"],
                    priors=priors,
                    status=str(row["status"]),
                    surface_condition=row["surface_condition"],
                )
            )
        return exported

    def refresh_h3_cells(self, submissions: list[ExportSubmission]) -> None:
        counts = Counter(submission.h3_r8 for submission in submissions)
        latest_dates: dict[str, date] = {}
        for submission in submissions:
            captured_date = date.fromisoformat(submission.captured_at[:10])
            latest_dates[submission.h3_r8] = max(
                latest_dates.get(submission.h3_r8, captured_date), captured_date
            )
        payload = [
            {
                "h3_index": h3_index,
                "latest_submission_date": latest_dates[h3_index].isoformat(),
                "n_submissions": count,
            }
            for h3_index, count in sorted(counts.items())
        ]
        response = self.client.post(
            f"{self.url}/rest/v1/rpc/refresh_public_h3_cells",
            json={"payload": payload},
        )
        response.raise_for_status()


def publish_export(
    source: SupabaseExportSource,
    submissions: list[ExportSubmission],
    target: Path,
    export_date: date,
    token: str,
    repo_id: str,
    api: HfApi | None = None,
) -> None:
    hub = api or HfApi(token=token)
    hub.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=target,
        commit_message=f"GSIP public export {export_date.isoformat()}",
        delete_patterns=["photos/**", "data/**"],
    )
    for attempt in range(3):
        try:
            source.refresh_h3_cells(submissions)
            break
        except httpx.HTTPError:
            if attempt == 2:
                raise
            time.sleep(2**attempt)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build GSIP's fail-closed public dataset export")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--output", type=Path, default=Path("output/export"))
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()
    source = SupabaseExportSource(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )
    submissions = source.submissions()
    target = build_export(submissions, args.output, args.date, source.photo)
    if args.push:
        publish_export(
            source,
            submissions,
            target,
            args.date,
            os.environ["HF_TOKEN"],
            os.environ["HF_DATASET_REPO"],
        )
    row_count = sum(
        submission.status == "qa_pass" and not submission.is_synthetic for submission in submissions
    )
    print(json.dumps({"export": str(target), "rows": row_count, "pushed": args.push}))


if __name__ == "__main__":
    main()
