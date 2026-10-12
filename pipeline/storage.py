"""Supabase Storage helpers for the service-role workers."""

from __future__ import annotations

from urllib.parse import quote

import httpx

DELETE_BATCH = 100


class SupabaseStorage:
    def __init__(self, client: httpx.Client, url: str) -> None:
        self.client = client
        self.url = url.rstrip("/")

    def delete_objects(self, bucket: str, paths: list[str]) -> int:
        """Deletes objects in batches. Objects that are already gone are not an error."""

        for start in range(0, len(paths), DELETE_BATCH):
            response = self.client.request(
                "DELETE",
                f"{self.url}/storage/v1/object/{quote(bucket, safe='')}",
                json={"prefixes": paths[start : start + DELETE_BATCH]},
            )
            response.raise_for_status()
        return len(paths)
