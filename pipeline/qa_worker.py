from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import h3  # type: ignore[import-untyped]
import httpx

from pipeline.qa import aggregate_submission_status, evaluate_photo


class SupabaseQaWorker:
    def __init__(self, url: str, service_key: str) -> None:
        self.url = url.rstrip("/")
        self.client = httpx.Client(
            timeout=45,
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
            },
        )

    def _rest(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = self.client.request(method, f"{self.url}/rest/v1/{path}", **kwargs)
        response.raise_for_status()
        return response

    def _paged_rows(self, path: str, page_size: int = 1000) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        start = 0
        while True:
            response = self._rest(
                "GET",
                path,
                headers={"Range": f"{start}-{start + page_size - 1}", "Range-Unit": "items"},
            )
            page: list[dict[str, Any]] = response.json()
            rows.extend(page)
            if len(page) < page_size:
                return rows
            start += page_size

    def requeue_stale_processing(self, older_than_minutes: int = 15) -> None:
        cutoff = (datetime.now(UTC) - timedelta(minutes=older_than_minutes)).isoformat()
        self._rest(
            "PATCH",
            f"qa_jobs?status=eq.processing&updated_at=lt.{quote(cutoff, safe='')}",
            json={
                "last_error": "stale_processing_requeued",
                "status": "retrying",
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    def process_pending(self, limit: int = 25) -> int:
        self.requeue_stale_processing()
        jobs = self._rest(
            "GET",
            f"qa_jobs?select=photo_id,attempts&status=in.(pending,retrying)&order=updated_at.asc&limit={limit}",
        ).json()
        completed = 0
        for job in jobs:
            if self.process_one(str(job["photo_id"]), int(job["attempts"])):
                completed += 1
        return completed

    def process_one(self, photo_id: str, attempts: int) -> bool:
        now = datetime.now(UTC).isoformat()
        self._rest(
            "PATCH",
            f"qa_jobs?photo_id=eq.{photo_id}",
            json={"attempts": attempts + 1, "status": "processing", "updated_at": now},
        )
        try:
            photo = self._rest(
                "GET", f"photos?id=eq.{photo_id}&select=id,submission_id,shot_type,storage_path"
            ).json()[0]
            submission_id = str(photo["submission_id"])
            submission = self._rest(
                "GET",
                f"submissions?id=eq.{submission_id}&select=id,geom_precise,gps_accuracy_m,land_cover",
            ).json()[0]
            latitude, longitude = _coordinates(submission["geom_precise"])
            prior_rows = self._rest(
                "GET",
                f"priors?submission_id=eq.{submission_id}&depth_top_cm=eq.0&depth_bottom_cm=eq.30&select=property,value",
            ).json()
            priors = {
                str(row["property"]): float(row["value"])
                for row in prior_rows
                if row["value"] is not None
            }
            hashes = self._paged_rows(
                f"photos?submission_id=neq.{submission_id}"
                "&perceptual_hash=not.is.null&select=perceptual_hash"
            )
            existing_hashes = tuple(str(row["perceptual_hash"]) for row in hashes)
            path = str(photo["storage_path"])
            incoming_url = (
                f"{self.url}/storage/v1/object/authenticated/incoming-photos/"
                f"{quote(path, safe='/')}"
            )
            raw = self.client.get(incoming_url)
            raw.raise_for_status()
            result = evaluate_photo(
                raw.content,
                accuracy_m=submission["gps_accuracy_m"],
                existing_hashes=existing_hashes,
                land_cover=submission["land_cover"],
                priors=priors,
            )
            promoted = self.client.post(
                f"{self.url}/storage/v1/object/submission-photos/{quote(path, safe='/')}",
                content=result.sanitized_jpeg,
                headers={"Content-Type": "image/jpeg", "x-upsert": "true"},
            )
            promoted.raise_for_status()
            self._rest(
                "PATCH",
                f"photos?id=eq.{photo_id}",
                json={
                    "calibration_status": result.calibration_status,
                    "camera_metadata_private": result.camera_metadata,
                    "card_color_correction": result.card_color_correction,
                    "card_detected": result.card_color_correction is not None,
                    "perceptual_hash": result.perceptual_hash,
                    "sharpness_score": next(
                        event.score for event in result.events if event.check_name == "sharpness"
                    ),
                },
            )
            self._rest(
                "POST",
                "qa_events?on_conflict=submission_id,check_name",
                headers={"Prefer": "resolution=merge-duplicates"},
                json=[
                    {
                        "check_name": f"{event.check_name}_{photo['shot_type']}",
                        "passed": event.passed,
                        "score": event.score,
                        "model_version": "deterministic-v1",
                        "submission_id": submission_id,
                    }
                    for event in result.events
                ],
            )
            all_events = self._rest(
                "GET",
                f"qa_events?submission_id=eq.{submission_id}&select=check_name,passed",
            ).json()
            submission_status = aggregate_submission_status(
                (str(event["check_name"]), bool(event["passed"])) for event in all_events
            )
            self._rest(
                "PATCH",
                f"submissions?id=eq.{submission_id}",
                json={
                    "h3_r6": h3.latlng_to_cell(latitude, longitude, 6),
                    "h3_r8": h3.latlng_to_cell(latitude, longitude, 8),
                    "status": submission_status,
                },
            )
            removed = self.client.delete(
                f"{self.url}/storage/v1/object/incoming-photos/{quote(path, safe='/')}"
            )
            removed.raise_for_status()
            self._rest(
                "PATCH",
                f"qa_jobs?photo_id=eq.{photo_id}",
                json={
                    "completed_at": now,
                    "last_error": None,
                    "status": "completed",
                    "updated_at": now,
                },
            )
            return True
        except Exception as error:
            next_status = "dead_letter" if attempts + 1 >= 4 else "retrying"
            self._rest(
                "PATCH",
                f"qa_jobs?photo_id=eq.{photo_id}",
                json={
                    "last_error": f"qa_processing_failure:{type(error).__name__}"[:1000],
                    "status": next_status,
                    "updated_at": now,
                },
            )
            return False

    def _quarantine_objects(self, prefix: str = "", depth: int = 0) -> list[tuple[str, datetime]]:
        if depth > 8:
            raise ValueError("quarantine prefix depth exceeded")
        objects: list[tuple[str, datetime]] = []
        offset = 0
        while True:
            response = self.client.post(
                f"{self.url}/storage/v1/object/list/incoming-photos",
                json={
                    "limit": 1000,
                    "offset": offset,
                    "prefix": prefix,
                    "sortBy": {"column": "created_at", "order": "asc"},
                },
            )
            response.raise_for_status()
            page: list[dict[str, Any]] = response.json()
            for item in page:
                name = str(item.get("name") or "")
                if not name:
                    continue
                full_name = (
                    name
                    if prefix and name.startswith(f"{prefix}/")
                    else "/".join(part for part in (prefix, name) if part)
                )
                created_at = item.get("created_at")
                if item.get("id") is None or created_at is None:
                    objects.extend(self._quarantine_objects(full_name, depth + 1))
                    continue
                created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                objects.append((full_name, created))
            if len(page) < 1000:
                return objects
            offset += 1000

    def cleanup_quarantine(self) -> int:
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        removed = 0
        for name, created in self._quarantine_objects():
            if created < cutoff:
                object_path = quote(name, safe="/")
                deleted = self.client.delete(
                    f"{self.url}/storage/v1/object/incoming-photos/{object_path}"
                )
                deleted.raise_for_status()
                removed += 1
        return removed


def _coordinates(geometry: Any) -> tuple[float, float]:
    latitude: float
    longitude: float
    if isinstance(geometry, dict):
        values = geometry.get("coordinates")
        if isinstance(values, list) and len(values) >= 2:
            longitude, latitude = map(float, values[:2])
        else:
            raise ValueError("submission geometry is unavailable")
    elif isinstance(geometry, str) and geometry.startswith("POINT(") and geometry.endswith(")"):
        longitude, latitude = map(float, geometry[6:-1].split())
    else:
        raise ValueError("submission geometry is unavailable")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("submission geometry is outside valid latitude/longitude bounds")
    return latitude, longitude


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process GSIP's deterministic private photo QA queue"
    )
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    worker = SupabaseQaWorker(url, key)
    worker.process_pending(args.limit)
    worker.cleanup_quarantine()


if __name__ == "__main__":
    main()
