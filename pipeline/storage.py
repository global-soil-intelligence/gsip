"""Supabase Storage helpers for the service-role workers.

The Storage list endpoint returns one folder level at a time (folders have no `id`), so listing a
prefix walks it. GSIP object paths are `{auth_uid}/{submission_id}/{shot_type}/{uuid}.jpg`.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

PAGE_SIZE = 1000
MAX_DEPTH = 8
DELETE_BATCH = 100


class SupabaseStorage:
    def __init__(self, client: httpx.Client, url: str) -> None:
        self.client = client
        self.url = url.rstrip("/")

    def list_objects(self, bucket: str, prefix: str, depth: int = 0) -> list[str]:
        """Every object path under `prefix` (no trailing slash), depth-first."""

        if depth > MAX_DEPTH:
            raise ValueError("storage prefix depth exceeded")
        found: list[str] = []
        offset = 0
        while True:
            response = self.client.post(
                f"{self.url}/storage/v1/object/list/{quote(bucket, safe='')}",
                json={
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "prefix": prefix,
                    "sortBy": {"column": "name", "order": "asc"},
                },
            )
            response.raise_for_status()
            page: list[dict[str, Any]] = response.json()
            for item in page:
                name = str(item.get("name") or "")
                if not name:
                    continue
                # Some Storage versions return names relative to the bucket rather than the prefix.
                if prefix and name.startswith(f"{prefix}/"):
                    path = name
                else:
                    path = f"{prefix}/{name}" if prefix else name
                if item.get("id") is None:
                    found.extend(self.list_objects(bucket, path, depth + 1))
                else:
                    found.append(path)
            if len(page) < PAGE_SIZE:
                return found
            offset += PAGE_SIZE

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
