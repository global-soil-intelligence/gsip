"""Process contributor rights requests (WP-6d): withdraw contributions or delete an account.

Invariants:
  * a request withdraws the contributor's grants for publication the moment it is made (database
    trigger); this worker, run hourly, makes the deletion physical;
  * every step is idempotent, and a failed step releases the request for a later run with the
    step and error kept for the operator; a request is reported done only when every step is;
  * a Storage object is deleted only when no submission row owns it, decided in one database
    snapshot, so a contributor who keeps contributing after a withdrawal never loses newer
    observations, while everything a request covers (and any upload orphaned by a race) goes;
  * for an account deletion the auth user is deleted before the contributor row loses its auth id
    (the database refuses otherwise), so a retry can always finish the job;
  * a run works until the queue is empty or its time budget is spent; requests with data are
    claimed first, so empty requests cannot starve real ones;
  * catch-all: every run deletes canonical photo objects that no photo row owns, whatever race or
    failed compensation left them (`orphaned_photo_objects`);
  * a request still open after 25 days fails the run, so the 30-day promise is never missed
    silently;
  * workflow logs of a public repository are public: output is counts only.
"""

from __future__ import annotations

import argparse
import os
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar
from urllib.parse import quote

import httpx

from pipeline.storage import SupabaseStorage

T = TypeVar("T")
PAGE = 1000
OVERDUE_AFTER = timedelta(days=25)
DEFAULT_BUDGET_SECONDS = 20 * 60.0


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
    out_of_time: bool = False
    overdue: int = 0
    submissions_deleted: int = 0


class StepFailed(Exception):  # noqa: N818 - carries the failed step's name to the release
    def __init__(self, step: str, error: Exception) -> None:
        status = (
            f":{error.response.status_code}" if isinstance(error, httpx.HTTPStatusError) else ""
        )
        super().__init__(f"{step}:{type(error).__name__}{status}")


class SupabaseRightsWorker:
    def __init__(
        self,
        url: str,
        service_key: str,
        *,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.url = url.rstrip("/")
        self.client = httpx.Client(
            timeout=60,
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        )
        self.clock = clock
        self.now = now

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

    def _delete_listed(self, rpc: str, payload: dict[str, Any], rounds: int) -> int:
        """Deletes what an orphan-listing function returns, 1000 at a time, until it is empty."""

        deleted = 0
        for _ in range(rounds):
            rows = self._rpc(rpc, {**payload, "p_limit": PAGE}) or []
            by_bucket: dict[str, list[str]] = defaultdict(list)
            for row in rows:
                by_bucket[str(row.get("bucket_id", "submission-photos"))].append(str(row["name"]))
            for bucket, names in sorted(by_bucket.items()):
                deleted += self.storage.delete_objects(bucket, names)
            if len(rows) < PAGE:
                return deleted
        raise RuntimeError(f"{rpc} still lists objects after {rounds} rounds")

    def sweep_storage(self, claim: Claim) -> int:
        """Deletes every object under the contributor's folder that no submission owns."""

        if not claim.auth_uid:
            return 0
        return self._delete_listed(
            "contributor_orphaned_objects", {"p_auth_uid": claim.auth_uid}, rounds=50
        )

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

    def sweep_orphans(self) -> int:
        """Deletes canonical objects without a photo row."""

        return self._delete_listed("orphaned_photo_objects", {}, rounds=10)

    def overdue_requests(self) -> int:
        cutoff = (self.now() - OVERDUE_AFTER).isoformat()
        response = self.client.get(
            f"{self.url}/rest/v1/deletion_requests",
            params={"requested_at": f"lt.{cutoff}", "select": "id", "status": "neq.completed"},
            headers={"Prefer": "count=exact", "Range": "0-0"},
        )
        response.raise_for_status()
        total = response.headers.get("Content-Range", "*/0").rsplit("/", 1)[-1]
        return int(total) if total.isdigit() else len(response.json())

    def run(self, budget_seconds: float = DEFAULT_BUDGET_SECONDS) -> RightsSummary:
        summary = RightsSummary()
        deadline = self.clock() + budget_seconds
        while True:
            if self.clock() >= deadline:
                summary.out_of_time = True
                break
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
        summary.overdue = self.overdue_requests()
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Process GSIP withdrawal and deletion requests")
    parser.add_argument(
        "--budget-seconds",
        type=float,
        default=DEFAULT_BUDGET_SECONDS,
        help="claim no new request after this long (keep below the schedule interval)",
    )
    args = parser.parse_args()
    worker = SupabaseRightsWorker(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )
    summary = worker.run(args.budget_seconds)
    print(
        f"rights requests: {summary.completed} completed, {summary.failed} failed; "
        f"{summary.submissions_deleted} submissions and {summary.objects_deleted} objects deleted; "
        f"{summary.orphans_deleted} orphaned objects removed"
        + ("; time budget spent, more requests wait" if summary.out_of_time else "")
    )
    problems = []
    if summary.failed:
        problems.append(f"{summary.failed} rights request(s) failed and will be retried")
    if summary.overdue:
        problems.append(f"{summary.overdue} rights request(s) are older than 25 days")
    if problems:
        raise SystemExit("; ".join(problems))


if __name__ == "__main__":
    main()
