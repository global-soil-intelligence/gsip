"""Drain prior-enrichment jobs through the `prior-attach` Edge Function (WP-4, WP-6c).

Invariants:
  * the worker never calls an upstream service itself; the function and the database
    (`begin_prior_attempt`) decide whether a job may run and pay for its calls;
  * a 202 means an upstream bucket is empty: the worker waits the function's `Retry-After` and
    retries the same job, but only while the wait fits the run's time budget;
  * every run ends within its budget (each wait is at least one second), so scheduled runs
    never overlap;
  * a job whose invocation failed before it was claimed moves behind the rest of the queue, so a
    persistent failure cannot hold the head of the queue; claimed (`processing`) jobs are never
    touched, so stale-claim detection keeps working.
"""

from __future__ import annotations

import argparse
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

DEFAULT_RETRY_AFTER_SECONDS = 12
MAX_RETRY_AFTER_SECONDS = 300
DEFAULT_BUDGET_SECONDS = 240.0


@dataclass
class DrainSummary:
    completed: int = 0
    deferred: bool = False
    failed: int = 0
    out_of_time: bool = False
    requeued: int = 0
    skipped: int = 0
    waited_seconds: int = 0


def retry_after_seconds(response: httpx.Response) -> int:
    """The function's wait hint in whole seconds, bounded to [1, 300]; 12 when absent."""

    try:
        value = int(response.headers.get("Retry-After", "").strip())
    except ValueError:
        return DEFAULT_RETRY_AFTER_SECONDS
    return min(max(value, 1), MAX_RETRY_AFTER_SECONDS)


class SupabasePriorWorker:
    def __init__(
        self,
        url: str,
        service_key: str,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.url = url.rstrip("/")
        self.client = httpx.Client(
            timeout=90,
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        )
        self.clock = clock
        self.sleep = sleep

    def requeue_stale(self) -> int:
        response = self.client.post(f"{self.url}/rest/v1/rpc/requeue_stale_prior_jobs", json={})
        response.raise_for_status()
        return int(response.json())

    def due_jobs(self, limit: int) -> list[str]:
        response = self.client.get(
            f"{self.url}/rest/v1/prior_jobs",
            params={
                "attempts": "lt.32",
                "limit": str(limit),
                "order": "updated_at.asc",
                "select": "submission_id",
                "status": "in.(pending,dead_letter)",
            },
        )
        response.raise_for_status()
        return [str(row["submission_id"]) for row in response.json()]

    def rotate(self, submission_id: str) -> None:
        """Best effort: moves an unclaimed job behind the queue after a failed invocation."""

        try:
            self.client.patch(
                f"{self.url}/rest/v1/prior_jobs",
                params={
                    "status": "in.(pending,dead_letter)",
                    "submission_id": f"eq.{submission_id}",
                },
                json={"updated_at": datetime.now(UTC).isoformat()},
                headers={"Prefer": "return=minimal"},
            ).raise_for_status()
        except httpx.HTTPError:
            return

    def invoke(self, submission_id: str) -> httpx.Response:
        return self.client.post(
            f"{self.url}/functions/v1/prior-attach", json={"submissionId": submission_id}
        )

    def drain(
        self, limit: int = 25, budget_seconds: float = DEFAULT_BUDGET_SECONDS
    ) -> DrainSummary:
        deadline = self.clock() + budget_seconds
        summary = DrainSummary(requeued=self.requeue_stale())
        for submission_id in self.due_jobs(limit):
            if self.clock() >= deadline:
                summary.out_of_time = True
                break
            invoked = self.invoke(submission_id)
            while invoked.status_code == 202:
                wait = retry_after_seconds(invoked)
                if self.clock() + wait > deadline:
                    summary.deferred = True
                    return summary
                self.sleep(wait)
                summary.waited_seconds += wait
                invoked = self.invoke(submission_id)
            if invoked.status_code == 409:
                summary.skipped += 1
            elif invoked.is_success:
                summary.completed += 1
            else:
                summary.failed += 1
                self.rotate(submission_id)
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Drain GSIP prior-enrichment jobs")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--budget-seconds",
        type=float,
        default=DEFAULT_BUDGET_SECONDS,
        help="stop waiting on upstream rate limits after this long (keep below the schedule)",
    )
    args = parser.parse_args()
    worker = SupabasePriorWorker(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )
    summary = worker.drain(args.limit, args.budget_seconds)
    print(
        f"prior jobs: {summary.completed} completed, {summary.failed} failed, "
        f"{summary.skipped} skipped, {summary.requeued} requeued, "
        f"{summary.waited_seconds} s waiting on upstream rate limits"
        + (", stopped: next wait exceeds the time budget" if summary.deferred else "")
        + (", stopped: time budget spent" if summary.out_of_time else "")
    )
    if summary.failed:
        raise SystemExit(f"{summary.failed} prior job(s) remain retryable")


if __name__ == "__main__":
    main()
