"""Process contributor rights requests (WP-6d): withdraw contributions or delete an account.

Invariants:
  * a request withdraws the contributor's grants for publication the moment it is made (database
    trigger); this worker makes the deletion physical within a day;
  * every step is idempotent, and a failed step releases the request for a later run with the
    step and error kept for the operator; a request is reported done only when every step is;
  * a Storage object is deleted only when no submission row owns it, so a contributor who keeps
    contributing after a withdrawal never loses newer observations, while everything a request
    covers (and any upload orphaned by a race) goes;
  * for an account deletion the auth user is deleted before the contributor row loses its auth id,
    so a retry can always finish the job;
  * catch-all: every run deletes canonical photo objects that no photo row owns, whatever race or
    failed compensation left them (`orphaned_photo_objects`);
  * workflow logs of a public repository are public: output is counts only.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar
from urllib.parse import quote

import httpx

from pipeline.storage import SupabaseStorage

BUCKETS = ("incoming-photos", "submission-photos")
T = TypeVar("T")


@dataclass(frozen=True)
class Claim:
    request_id: str
    contributor_id: str
    kind: str
    auth_uid: str | None
    attempts: int


@dataclass
class RightsSummary:
    completed: int = 0
    failed: int = 0
    objects_deleted: int = 0
    orphans_deleted: int = 0
    submissions_deleted: int = 0


class StepFailed(Exception):  # noqa: N818 - carries the failed step's name to the release
    def __init__(self, step: str, error: Exception) -> None:
        status = (
            f":{error.response.status_code}" if isinstance(error, httpx.HTTPStatusError) else ""
        )
        super().__init__(f"{step}:{type(error).__name__}{status}")


def owning_submission(path: str) -> str | None:
    """`{auth_uid}/{submission_id}/...` -> submission_id; anything else has no owner."""

    parts = path.split("/")
    return parts[1] if len(parts) >= 3 and parts[1] else None


class SupabaseRightsWorker:
    def __init__(self, url: str, service_key: str) -> None:
        self.url = url.rstrip("/")
        self.client = httpx.Client(
            timeout=60,
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        )

    @property
    def storage(self) -> SupabaseStorage:
        return SupabaseStorage(self.client, self.url)

    def _rpc(self, name: str, payload: dict[str, Any]) -> Any:
        response = self.client.post(f"{self.url}/rest/v1/rpc/{name}", json=payload)
        response.raise_for_status()
        return response.json() if response.content else None

    def claim(self) -> Claim | None:
        rows = self._rpc("claim_deletion_request", {})
        if not rows:
            return None
        row = rows[0]
        return Claim(
            request_id=str(row["request_id"]),
            contributor_id=str(row["contributor_id"]),
            kind=str(row["kind"]),
            auth_uid=str(row["auth_uid"]) if row.get("auth_uid") else None,
            attempts=int(row["attempts"]),
        )

    def live_submission_ids(self, contributor_id: str) -> set[str]:
        ids: set[str] = set()
        offset = 0
        while True:
            response = self.client.get(
                f"{self.url}/rest/v1/submissions",
                params={
                    "contributor_id": f"eq.{contributor_id}",
                    "limit": "1000",
                    "offset": str(offset),
                    "order": "id",
                    "select": "id",
                },
            )
            response.raise_for_status()
            page: list[dict[str, Any]] = response.json()
            ids.update(str(row["id"]) for row in page)
            if len(page) < 1000:
                return ids
            offset += 1000

    def sweep_storage(self, claim: Claim) -> int:
        """Deletes every object under the contributor's prefix that no submission owns."""

        if not claim.auth_uid:
            return 0
        live = self.live_submission_ids(claim.contributor_id)
        deleted = 0
        for bucket in BUCKETS:
            orphans = [
                path
                for path in self.storage.list_objects(bucket, claim.auth_uid)
                if owning_submission(path) not in live
            ]
            deleted += self.storage.delete_objects(bucket, orphans)
        return deleted

    def delete_auth_user(self, auth_uid: str) -> None:
        response = self.client.delete(f"{self.url}/auth/v1/admin/users/{quote(auth_uid, safe='')}")
        if response.status_code == 404:
            return  # already deleted by an earlier attempt
        response.raise_for_status()

    def _step(self, name: str, action: Callable[[], T]) -> T:
        try:
            return action()
        except Exception as error:
            raise StepFailed(name, error) from error

    def process(self, claim: Claim) -> tuple[int, int]:
        applied = self._step(
            "apply",
            lambda: self._rpc("apply_deletion_request", {"p_request_id": claim.request_id}),
        )
        deleted_rows = int(applied[0]["deleted_submissions"]) if applied else 0
        objects = self._step("storage", lambda: self.sweep_storage(claim))
        if claim.kind == "delete_account" and claim.auth_uid:
            auth_uid = claim.auth_uid
            self._step("auth", lambda: self.delete_auth_user(auth_uid))
        self._step(
            "complete",
            lambda: self._rpc("complete_deletion_request", {"p_request_id": claim.request_id}),
        )
        return deleted_rows, objects

    def release(self, claim: Claim, reason: str) -> None:
        self._rpc(
            "release_deletion_request",
            {"p_error": reason, "p_request_id": claim.request_id},
        )

    def sweep_orphans(self, rounds: int = 10) -> int:
        """Deletes canonical objects without a photo row, 1000 per round."""

        deleted = 0
        for _ in range(rounds):
            rows = self._rpc("orphaned_photo_objects", {"p_limit": 1000}) or []
            names = [str(row["name"]) for row in rows]
            if not names:
                break
            deleted += self.storage.delete_objects("submission-photos", names)
            if len(names) < 1000:
                break
        return deleted

    def run(self, limit: int = 50) -> RightsSummary:
        summary = RightsSummary()
        for _ in range(limit):
            claim = self.claim()
            if claim is None:
                break
            try:
                deleted_rows, objects = self.process(claim)
            except StepFailed as failure:
                summary.failed += 1
                try:
                    self.release(claim, str(failure))
                except httpx.HTTPError:
                    pass  # an unreleased claim is reclaimed after an hour
                continue
            summary.completed += 1
            summary.submissions_deleted += deleted_rows
            summary.objects_deleted += objects
        summary.orphans_deleted = self.sweep_orphans()
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Process GSIP withdrawal and deletion requests")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    worker = SupabaseRightsWorker(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )
    summary = worker.run(args.limit)
    print(
        f"rights requests: {summary.completed} completed, {summary.failed} failed; "
        f"{summary.submissions_deleted} submissions and {summary.objects_deleted} objects deleted; "
        f"{summary.orphans_deleted} orphaned objects removed"
    )
    if summary.failed:
        raise SystemExit(f"{summary.failed} rights request(s) failed and will be retried")


if __name__ == "__main__":
    main()
