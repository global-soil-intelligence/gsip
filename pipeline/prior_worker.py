from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

import httpx


@dataclass
class DrainSummary:
    completed: int = 0
    deferred: bool = False
    failed: int = 0
    requeued: int = 0
    skipped: int = 0


class SupabasePriorWorker:
    """Retries prior enrichment through the `prior-attach` Edge Function (WP-4, WP-6c).

    The function enforces the upstream token buckets. A 202 means a bucket is empty, so the
    drain stops instead of hammering it; the next scheduled run continues.
    """

    def __init__(self, url: str, service_key: str) -> None:
        self.url = url.rstrip("/")
        self.client = httpx.Client(
            timeout=90,
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        )

    def requeue_stale(self) -> int:
        response = self.client.post(f"{self.url}/rest/v1/rpc/requeue_stale_prior_jobs", json={})
        response.raise_for_status()
        return int(response.json())

    def drain(self, limit: int = 25) -> DrainSummary:
        summary = DrainSummary(requeued=self.requeue_stale())
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
        for row in response.json():
            invoked = self.client.post(
                f"{self.url}/functions/v1/prior-attach",
                json={"submissionId": str(row["submission_id"])},
            )
            if invoked.status_code == 202:
                summary.deferred = True
                break
            if invoked.status_code == 409:
                summary.skipped += 1
            elif invoked.is_success:
                summary.completed += 1
            else:
                summary.failed += 1
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Drain GSIP prior-enrichment jobs")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    worker = SupabasePriorWorker(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )
    summary = worker.drain(args.limit)
    print(
        f"prior jobs: {summary.completed} completed, {summary.failed} failed, "
        f"{summary.skipped} skipped, {summary.requeued} requeued"
        + (", deferred by upstream rate limits" if summary.deferred else "")
    )
    if summary.failed:
        raise SystemExit(f"{summary.failed} prior job(s) remain retryable")


if __name__ == "__main__":
    main()
