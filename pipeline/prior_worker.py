from __future__ import annotations

import argparse
import os

import httpx


class SupabasePriorWorker:
    def __init__(self, url: str, service_key: str) -> None:
        self.url = url.rstrip("/")
        self.client = httpx.Client(
            timeout=90,
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        )

    def drain(self, limit: int = 25) -> tuple[int, int]:
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
        completed = 0
        failed = 0
        for row in response.json():
            invoked = self.client.post(
                f"{self.url}/functions/v1/prior-attach",
                json={"submissionId": str(row["submission_id"])},
            )
            if invoked.is_success:
                completed += 1
            else:
                failed += 1
        return completed, failed


def main() -> None:
    parser = argparse.ArgumentParser(description="Drain GSIP prior-enrichment jobs")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    worker = SupabasePriorWorker(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )
    completed, failed = worker.drain(args.limit)
    if failed:
        raise SystemExit(f"{failed} prior job(s) remain retryable; {completed} completed")


if __name__ == "__main__":
    main()
