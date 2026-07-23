from __future__ import annotations

import io
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import numpy as np
import pytest
from PIL import Image

from pipeline.qa_worker import SupabaseQaWorker


def jpeg(size: int) -> bytes:
    grid = np.indices((size, size)).sum(axis=0) % 2
    image = Image.fromarray(np.repeat((grid * 220 + 20)[..., None], 3, axis=2).astype(np.uint8))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=94)
    return output.getvalue()


class WorkerHarness(SupabaseQaWorker):
    def __init__(self, hostile: bytes) -> None:
        super().__init__("https://supabase.test", "service-key")
        self.hostile = hostile
        self.job_states: dict[str, str] = {}
        self.promotions: list[str] = []
        self.submission_updates: list[dict[str, Any]] = []
        self.client = httpx.Client(transport=httpx.MockTransport(self._http))

    def _response(self, body: Any = None) -> httpx.Response:
        return httpx.Response(200, json=body, request=httpx.Request("GET", self.url))

    def _rest(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if method == "GET" and path.startswith("qa_jobs?"):
            return self._response(
                [
                    {"attempts": 3, "photo_id": "hostile"},
                    {"attempts": 0, "photo_id": "good"},
                ]
            )
        if method == "GET" and path.startswith("photos?id=eq.hostile"):
            return self._response(
                [
                    {
                        "id": "hostile",
                        "shot_type": "A",
                        "storage_path": "uid/submission/A/hostile.jpg",
                        "submission_id": "submission",
                    }
                ]
            )
        if method == "GET" and path.startswith("photos?id=eq.good"):
            return self._response(
                [
                    {
                        "id": "good",
                        "shot_type": "B",
                        "storage_path": "uid/submission/B/good.jpg",
                        "submission_id": "submission",
                    }
                ]
            )
        if method == "GET" and path.startswith("submissions?"):
            return self._response(
                [
                    {
                        "geom_precise": {"coordinates": [-79.982, 40.446], "type": "Point"},
                        "gps_accuracy_m": 8,
                        "id": "submission",
                        "land_cover": "urban",
                    }
                ]
            )
        if method == "GET" and path.startswith(("priors?", "photos?submission_id=neq.")):
            return self._response([])
        if method == "GET" and path.startswith("qa_events?"):
            return self._response(
                [
                    {"check_name": "sharpness_B", "passed": True},
                    {"check_name": "exposure_B", "passed": True},
                    {"check_name": "gps_plausibility_B", "passed": True},
                    {"check_name": "duplicate_B", "passed": True},
                ]
            )
        if method == "PATCH" and path.startswith("qa_jobs?photo_id=eq."):
            photo_id = path.rsplit(".", 1)[-1]
            self.job_states[photo_id] = str(kwargs["json"]["status"])
        if method == "PATCH" and path.startswith("submissions?"):
            self.submission_updates.append(kwargs["json"])
        return self._response([])

    def _http(self, request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and "hostile.jpg" in request.url.path:
            return httpx.Response(200, content=self.hostile)
        if request.method == "GET" and "good.jpg" in request.url.path:
            return httpx.Response(200, content=jpeg(8))
        if request.method == "POST" and "/submission-photos/" in request.url.path:
            self.promotions.append(request.url.path)
            return httpx.Response(200, json={})
        return httpx.Response(200, json={})


@pytest.mark.parametrize("hostile", [b"not-an-image", jpeg(20)])
def test_hostile_images_dead_letter_and_do_not_block_following_jobs(
    hostile: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    if hostile.startswith(b"\xff\xd8"):
        monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    worker = WorkerHarness(hostile)

    assert worker.process_pending() == 1
    assert worker.job_states["hostile"] == "dead_letter"
    assert worker.job_states["good"] == "completed"
    assert len(worker.promotions) == 1
    assert "good.jpg" in worker.promotions[0]
    assert worker.submission_updates[-1]["status"] == "qa_pass"
    assert worker.submission_updates[-1]["h3_r8"].startswith("88")


def test_cleanup_recurses_to_old_leaf_objects_and_ignores_folder_placeholders() -> None:
    deleted: list[str] = []
    old = (datetime.now(UTC) - timedelta(hours=25)).isoformat()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE":
            deleted.append(request.url.path)
            return httpx.Response(200, json={})
        body = json.loads(request.content)
        prefix = body["prefix"]
        pages = {
            "": [{"created_at": None, "id": None, "name": "uid"}],
            "uid": [{"created_at": None, "id": None, "name": "submission"}],
            "uid/submission": [{"created_at": None, "id": None, "name": "A"}],
            "uid/submission/A": [
                {"created_at": old, "id": "leaf", "name": "object.jpg"},
                {"created_at": None, "id": None, "name": "empty-folder"},
            ],
            "uid/submission/A/empty-folder": [],
        }
        return httpx.Response(200, json=pages[prefix])

    worker = SupabaseQaWorker("https://supabase.test", "service-key")
    worker.client = httpx.Client(transport=httpx.MockTransport(handler))

    assert worker.cleanup_quarantine() == 1
    assert deleted == ["/storage/v1/object/incoming-photos/uid/submission/A/object.jpg"]


def test_paginated_hash_reads_do_not_truncate_after_one_thousand_rows() -> None:
    class PagingWorker(SupabaseQaWorker):
        def __init__(self) -> None:
            super().__init__("https://supabase.test", "service-key")
            self.ranges: list[str] = []

        def _rest(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
            range_header = str(kwargs["headers"]["Range"])
            self.ranges.append(range_header)
            count = 1000 if range_header.startswith("0-") else 1
            return httpx.Response(
                200,
                json=[{"perceptual_hash": f"{index:016x}"} for index in range(count)],
            )

    worker = PagingWorker()
    assert len(worker._paged_rows("photos?select=perceptual_hash")) == 1001
    assert worker.ranges == ["0-999", "1000-1999"]


def test_stale_processing_jobs_are_moved_back_to_retrying() -> None:
    class RequeueWorker(SupabaseQaWorker):
        def __init__(self) -> None:
            super().__init__("https://supabase.test", "service-key")
            self.path = ""
            self.payload: dict[str, Any] = {}

        def _rest(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
            self.path = path
            self.payload = kwargs["json"]
            return httpx.Response(200, json=[])

    worker = RequeueWorker()
    worker.requeue_stale_processing()
    assert "status=eq.processing" in worker.path
    assert "updated_at=lt." in worker.path
    assert worker.payload["status"] == "retrying"
