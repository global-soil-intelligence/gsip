from __future__ import annotations

import io
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import numpy as np
import pytest
from PIL import Image

from pipeline.qa import evaluate_photo
from pipeline.qa_worker import (
    StoragePathMismatch,
    SupabaseQaWorker,
    expected_photo_path_pattern,
    verified_storage_path,
)

AUTH_UID = "30000000-0000-4000-8000-000000000001"
OTHER_UID = "30000000-0000-4000-8000-000000000002"
SUBMISSION = "50000000-0000-4000-8000-000000000001"


def jpeg(size: int) -> bytes:
    grid = np.indices((size, size)).sum(axis=0) % 2
    image = Image.fromarray(np.repeat((grid * 220 + 20)[..., None], 3, axis=2).astype(np.uint8))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=94)
    return output.getvalue()


def bound_path(shot: str, object_id: str) -> str:
    return f"{AUTH_UID}/{SUBMISSION}/{shot}/{object_id}.jpg"


HOSTILE_PATH = bound_path("A", "60000000-0000-4000-8000-0000000000a1")
GOOD_PATH = bound_path("B", "60000000-0000-4000-8000-0000000000b1")


class WorkerHarness(SupabaseQaWorker):
    def __init__(
        self,
        hostile: bytes,
        *,
        geometry: dict[str, Any] | None = None,
        prior_rows: list[dict[str, Any]] | None = None,
        paths: dict[str, str] | None = None,
        finalized_pending: list[str] | None = None,
    ) -> None:
        super().__init__("https://supabase.test", "service-key")
        self.hostile = hostile
        self.geometry = geometry or {
            "coordinates": [-79.982, 40.446],
            "type": "Point",
        }
        self.paths = {"hostile": HOSTILE_PATH, "good": GOOD_PATH, **(paths or {})}
        self.finalized_pending = finalized_pending or []
        self.job_states: dict[str, str] = {}
        self.photo_updates: dict[str, dict[str, Any]] = {}
        self.prior_rows = prior_rows or []
        self.promotions: list[str] = []
        self.settled: list[str] = []
        self.storage_requests: list[str] = []
        self.submission_updates: list[dict[str, Any]] = []
        self.client = httpx.Client(transport=httpx.MockTransport(self._http))

    def _response(self, body: Any = None) -> httpx.Response:
        return httpx.Response(200, json=body, request=httpx.Request("GET", self.url))

    def _photo(self, photo_id: str, shot: str) -> dict[str, Any]:
        return {
            "id": photo_id,
            "shot_type": shot,
            "storage_path": self.paths[photo_id],
            "submission_id": SUBMISSION,
        }

    def _rest(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if method == "GET" and path.startswith("qa_jobs?"):
            return self._response(
                [
                    {"attempts": 3, "photo_id": "hostile"},
                    {"attempts": 0, "photo_id": "good"},
                ]
            )
        if method == "GET" and path.startswith("photos?id=eq.hostile"):
            return self._response([self._photo("hostile", "A")])
        if method == "GET" and path.startswith("photos?id=eq.good"):
            return self._response([self._photo("good", "B")])
        if method == "GET" and path.startswith("submissions?status=eq.pending"):
            return self._response([{"id": value} for value in self.finalized_pending])
        if method == "GET" and path.startswith("submissions?"):
            assert "contributor:contributors(auth_uid)" in path
            return self._response(
                [
                    {
                        "contributor": {"auth_uid": AUTH_UID},
                        "geom_precise": self.geometry,
                        "gps_accuracy_m": 8,
                        "id": SUBMISSION,
                        "land_cover": "urban",
                    }
                ]
            )
        if method == "GET" and path.startswith("priors?"):
            return self._response(self.prior_rows)
        if method == "GET" and path.startswith("photos?submission_id=neq."):
            return self._response([])
        if method == "POST" and path == "rpc/settle_submission":
            self.settled.append(str(kwargs["json"]["p_submission_id"]))
            return self._response("qa_pass")
        if method == "PATCH" and path.startswith("qa_jobs?photo_id=eq."):
            photo_id = path.rsplit(".", 1)[-1]
            self.job_states[photo_id] = str(kwargs["json"]["status"])
        if method == "PATCH" and path.startswith("photos?id=eq."):
            photo_id = path.rsplit(".", 1)[-1]
            self.photo_updates.setdefault(photo_id, {}).update(kwargs["json"])
        if method == "PATCH" and path.startswith("submissions?"):
            self.submission_updates.append(kwargs["json"])
        return self._response([])

    def _http(self, request: httpx.Request) -> httpx.Response:
        self.storage_requests.append(f"{request.method} {request.url.path}")
        if request.method == "GET" and HOSTILE_PATH in request.url.path:
            return httpx.Response(200, content=self.hostile)
        if request.method == "GET" and GOOD_PATH in request.url.path:
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
    assert worker.photo_updates["hostile"] == {"qa_status": "error"}
    assert worker.job_states["good"] == "completed"
    assert worker.photo_updates["good"]["qa_status"] == "pass"
    assert len(worker.promotions) == 1
    assert GOOD_PATH in worker.promotions[0]
    # Status is never written photo by photo; the database settles it from shots A and B.
    assert all("status" not in update for update in worker.submission_updates)
    assert worker.submission_updates[-1]["h3_r8"].startswith("88")
    assert worker.settled == [SUBMISSION, SUBMISSION]


def test_zero_valued_prior_reaches_gps_plausibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_priors: dict[str, float] = {}

    def capture_priors(*args: Any, **kwargs: Any) -> Any:
        captured_priors.update(kwargs["priors"])
        return evaluate_photo(*args, **kwargs)

    monkeypatch.setattr("pipeline.qa_worker.evaluate_photo", capture_priors)
    worker = WorkerHarness(
        b"unused",
        prior_rows=[{"property": "sand", "value": 0}],
    )

    assert worker.process_one("good", 0)
    assert captured_priors == {"sand": 0.0}


def test_out_of_range_geometry_dead_letters_without_h3_or_promotion() -> None:
    worker = WorkerHarness(
        b"unused",
        geometry={"coordinates": [200, 95], "type": "Point"},
    )

    assert not worker.process_one("good", 3)
    assert worker.job_states["good"] == "dead_letter"
    assert worker.submission_updates == []
    assert worker.promotions == []


@pytest.mark.parametrize(
    "path",
    [
        f"{OTHER_UID}/{SUBMISSION}/B/60000000-0000-4000-8000-0000000000b1.jpg",
        f"{AUTH_UID}/50000000-0000-4000-8000-000000000009/B/60000000-0000-4000-8000-0000000000b1.jpg",
        f"{AUTH_UID}/{SUBMISSION}/C/60000000-0000-4000-8000-0000000000b1.jpg",
        f"{AUTH_UID}/{SUBMISSION}/B/../../../{OTHER_UID}/{SUBMISSION}/B/60000000-0000-4000-8000-0000000000b1.jpg",
        f"{AUTH_UID}/{SUBMISSION}/B/photo.jpg",
    ],
)
def test_mismatched_storage_paths_dead_letter_before_any_storage_request(path: str) -> None:
    worker = WorkerHarness(b"unused", paths={"good": path})

    assert not worker.process_one("good", 0)
    assert worker.job_states["good"] == "dead_letter"
    assert worker.photo_updates["good"] == {"qa_status": "error"}
    assert worker.storage_requests == []
    assert worker.settled == [SUBMISSION]


def test_path_pattern_rejects_unbindable_database_facts() -> None:
    with pytest.raises(StoragePathMismatch):
        expected_photo_path_pattern("not-a-uuid", SUBMISSION, "B")
    with pytest.raises(StoragePathMismatch):
        expected_photo_path_pattern(AUTH_UID, SUBMISSION, "D")
    with pytest.raises(StoragePathMismatch):
        verified_storage_path(
            {"shot_type": "B", "storage_path": GOOD_PATH, "submission_id": SUBMISSION},
            {"contributor": None},
        )
    assert (
        verified_storage_path(
            {"shot_type": "B", "storage_path": GOOD_PATH, "submission_id": SUBMISSION},
            {"contributor": {"auth_uid": AUTH_UID}},
        )
        == GOOD_PATH
    )


def test_finalized_submissions_are_settled_after_their_photos_finished() -> None:
    worker = WorkerHarness(
        b"unused",
        finalized_pending=[
            "50000000-0000-4000-8000-000000000011",
            "50000000-0000-4000-8000-000000000012",
        ],
    )
    assert worker.settle_finalized() == 2
    assert worker.settled == [
        "50000000-0000-4000-8000-000000000011",
        "50000000-0000-4000-8000-000000000012",
    ]


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
