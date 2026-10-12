from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import h3  # type: ignore[import-untyped]
import httpx

from pipeline.paths import StoragePathMismatch, expected_photo_path_pattern, verify_photo_path
from pipeline.qa import evaluate_photo

__all__ = [
    "MAX_QA_ATTEMPTS",
    "StoragePathMismatch",
    "SupabaseQaWorker",
    "expected_photo_path_pattern",
    "verified_storage_path",
]

MAX_QA_ATTEMPTS = 4


def verified_storage_path(photo: dict[str, Any], submission: dict[str, Any]) -> str:
    """Re-derive the photo's storage path from database facts before touching Storage."""

    contributor = submission.get("contributor") or {}
    return verify_photo_path(
        str(photo.get("storage_path") or ""),
        str(contributor.get("auth_uid") or ""),
        str(photo["submission_id"]),
        str(photo["shot_type"]),
    )


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
        cutoff = quote(
            (datetime.now(UTC) - timedelta(minutes=older_than_minutes)).isoformat(), safe=""
        )
        self._rest(
            "PATCH",
            f"qa_jobs?status=eq.processing&updated_at=lt.{cutoff}&attempts=lt.{MAX_QA_ATTEMPTS}",
            json={
                "last_error": "stale_processing_requeued",
                "status": "retrying",
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    def exhaust_stuck_jobs(self, older_than_minutes: int = 15) -> int:
        """Dead-letter jobs that have used their retry budget but never reached a verdict.

        A run killed during a job's last attempt leaves it in ``processing`` with no attempts
        left; claiming it again would violate the attempts constraint and stop every later run.
        """

        cutoff = quote(
            (datetime.now(UTC) - timedelta(minutes=older_than_minutes)).isoformat(), safe=""
        )
        rows = [
            *self._rest(
                "GET",
                f"qa_jobs?status=in.(pending,retrying)&attempts=gte.{MAX_QA_ATTEMPTS}"
                "&select=photo_id",
            ).json(),
            *self._rest(
                "GET",
                f"qa_jobs?status=eq.processing&attempts=gte.{MAX_QA_ATTEMPTS}"
                f"&updated_at=lt.{cutoff}&select=photo_id",
            ).json(),
        ]
        for row in rows:
            photo_id = str(row["photo_id"])
            photos = self._rest("GET", f"photos?id=eq.{photo_id}&select=submission_id").json()
            submission_id = str(photos[0]["submission_id"]) if photos else None
            self._fail(photo_id, submission_id, "retry_budget_exhausted", terminal=True)
        return len(rows)

    def settle(self, submission_id: str) -> str:
        response = self._rest(
            "POST", "rpc/settle_submission", json={"p_submission_id": submission_id}
        )
        return str(response.json())

    def settle_finalized(self, limit: int = 200) -> int:
        """Settle finalized submissions whose photos finished QA before finalize arrived."""

        rows = self._rest(
            "GET",
            "submissions?status=eq.pending&finalized_at=not.is.null"
            f"&select=id&order=finalized_at.asc&limit={limit}",
        ).json()
        settled = 0
        for row in rows:
            # One failing row never stops the sweep; the next run retries it.
            try:
                if self.settle(str(row["id"])) != "pending":
                    settled += 1
            except httpx.HTTPError:
                continue
        return settled

    def process_pending(self, limit: int = 25) -> int:
        self.requeue_stale_processing()
        self.exhaust_stuck_jobs()
        jobs = self._rest(
            "GET",
            "qa_jobs?select=photo_id,attempts&status=in.(pending,retrying)"
            f"&attempts=lt.{MAX_QA_ATTEMPTS}&order=updated_at.asc&limit={limit}",
        ).json()
        completed = 0
        for job in jobs:
            if self.process_one(str(job["photo_id"]), int(job["attempts"])):
                completed += 1
        self.settle_finalized()
        return completed

    def _fail(self, photo_id: str, submission_id: str | None, reason: str, terminal: bool) -> None:
        # Record the verdict and settle before closing the job: if either write fails, the job
        # stays claimable (or is exhausted later) and a subsequent run finishes the work.
        if terminal:
            self._rest("PATCH", f"photos?id=eq.{photo_id}", json={"qa_status": "error"})
            if submission_id:
                self.settle(submission_id)
        self._rest(
            "PATCH",
            f"qa_jobs?photo_id=eq.{photo_id}",
            json={
                "last_error": reason[:1000],
                "status": "dead_letter" if terminal else "retrying",
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    def process_one(self, photo_id: str, attempts: int) -> bool:
        if attempts >= MAX_QA_ATTEMPTS:
            return False
        now = datetime.now(UTC).isoformat()
        try:
            self._rest(
                "PATCH",
                f"qa_jobs?photo_id=eq.{photo_id}",
                json={"attempts": attempts + 1, "status": "processing", "updated_at": now},
            )
        except httpx.HTTPError:
            return False
        submission_id: str | None = None
        try:
            photo = self._rest(
                "GET", f"photos?id=eq.{photo_id}&select=id,submission_id,shot_type,storage_path"
            ).json()[0]
            submission_id = str(photo["submission_id"])
            submission = self._rest(
                "GET",
                f"submissions?id=eq.{submission_id}"
                "&select=id,geom_precise,gps_accuracy_m,land_cover,contributor:contributors(auth_uid)",
            ).json()[0]
            # WP-6b: never trust the stored path. A mismatch is terminal and touches no object.
            path = verified_storage_path(photo, submission)
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
            object_path = quote(path, safe="/")
            raw = self.client.get(
                f"{self.url}/storage/v1/object/authenticated/incoming-photos/{object_path}"
            )
            raw.raise_for_status()
            result = evaluate_photo(
                raw.content,
                accuracy_m=submission["gps_accuracy_m"],
                existing_hashes=existing_hashes,
                land_cover=submission["land_cover"],
                priors=priors,
            )
            promoted = self.client.post(
                f"{self.url}/storage/v1/object/submission-photos/{object_path}",
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
                    "qa_status": result.status,
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
                        "model_version": result.model_version,
                        "submission_id": submission_id,
                    }
                    for event in result.events
                ],
            )
            self._rest(
                "PATCH",
                f"submissions?id=eq.{submission_id}",
                json={
                    "h3_r6": h3.latlng_to_cell(latitude, longitude, 6),
                    "h3_r8": h3.latlng_to_cell(latitude, longitude, 8),
                },
            )
            self.settle(submission_id)
            removed = self.client.delete(
                f"{self.url}/storage/v1/object/incoming-photos/{object_path}"
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
        except StoragePathMismatch:
            self._fail(photo_id, submission_id, "storage_path_mismatch", terminal=True)
            return False
        except Exception as error:
            self._fail(
                photo_id,
                submission_id,
                f"qa_processing_failure:{type(error).__name__}",
                terminal=attempts + 1 >= MAX_QA_ATTEMPTS,
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
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="only delete quarantine objects older than 24 hours (runs on its own schedule)",
    )
    args = parser.parse_args()
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    worker = SupabaseQaWorker(url, key)
    if not args.cleanup_only:
        worker.process_pending(args.limit)
    removed = worker.cleanup_quarantine()
    print(f"quarantine objects removed: {removed}")


if __name__ == "__main__":
    main()
