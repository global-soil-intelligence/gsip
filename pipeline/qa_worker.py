from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

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

    def process_pending(self, limit: int = 25) -> int:
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
                f"submissions?id=eq.{submission_id}&select=id,gps_accuracy_m,land_cover",
            ).json()[0]
            prior_rows = self._rest(
                "GET",
                f"priors?submission_id=eq.{submission_id}&depth_top_cm=eq.0&depth_bottom_cm=eq.30&select=property,value",
            ).json()
            priors = {
                str(row["property"]): float(row["value"]) for row in prior_rows if row["value"]
            }
            hashes = self._rest(
                "GET",
                f"photos?id=neq.{photo_id}&perceptual_hash=not.is.null&select=perceptual_hash",
            ).json()
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
                json={"status": submission_status},
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
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            next_status = "dead_letter" if attempts + 1 >= 4 else "retrying"
            self._rest(
                "PATCH",
                f"qa_jobs?photo_id=eq.{photo_id}",
                json={
                    "last_error": "qa_processing_failure",
                    "status": next_status,
                    "updated_at": now,
                },
            )
            return False

    def cleanup_quarantine(self) -> int:
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        response = self.client.post(
            f"{self.url}/storage/v1/object/list/incoming-photos",
            json={
                "limit": 1000,
                "offset": 0,
                "prefix": "",
                "sortBy": {"column": "created_at", "order": "asc"},
            },
        )
        response.raise_for_status()
        removed = 0
        for item in response.json():
            created = datetime.fromisoformat(str(item["created_at"]).replace("Z", "+00:00"))
            if created < cutoff:
                object_path = quote(str(item["name"]), safe="/")
                deleted = self.client.delete(
                    f"{self.url}/storage/v1/object/incoming-photos/{object_path}"
                )
                deleted.raise_for_status()
                removed += 1
        return removed


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
