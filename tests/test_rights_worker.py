"""WP-6d rights worker against an in-memory stand-in for Supabase (REST, Storage and Auth)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from pipeline.rights_worker import (
    BUCKETS,
    SupabaseRightsWorker,
    owning_submission,
)
from pipeline.storage import SupabaseStorage

UID = "31600000-0000-4000-8000-00000000000a"
CONTRIBUTOR = "21600000-0000-4000-8000-00000000000a"
OLD = "51600000-0000-4000-8000-0000000000a1"
NEWER = "51600000-0000-4000-8000-0000000000a3"


def path(submission: str, shot: str = "B", name: str = "x") -> str:
    return f"{UID}/{submission}/{shot}/{name}.jpg"


@dataclass
class Request:
    request_id: str
    kind: str
    covered: set[str]
    status: str = "pending"
    attempts: int = 0
    last_error: str | None = None


@dataclass
class FakeSupabase:
    requests: list[Request]
    submissions: set[str]
    objects: dict[str, set[str]]
    auth_users: set[str] = field(default_factory=lambda: {UID})
    claim_uid: str | None = UID
    failures: dict[str, int] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)

    def _request(self, request_id: str) -> Request:
        return next(r for r in self.requests if r.request_id == request_id)

    def _children(self, bucket: str, prefix: str) -> list[dict[str, Any]]:
        children: dict[str, dict[str, Any]] = {}
        for name in sorted(self.objects[bucket]):
            if not name.startswith(f"{prefix}/"):
                continue
            rest = name[len(prefix) + 1 :]
            head, _, tail = rest.partition("/")
            children.setdefault(head, {"id": "object" if not tail else None, "name": head})
        return list(children.values())

    def __call__(self, request: httpx.Request) -> httpx.Response:
        route = f"{request.method} {request.url.path}"
        self.calls.append(route)
        for step, status in self.failures.items():
            if step in route:
                return httpx.Response(status, json={"message": "injected failure"})
        body = json.loads(request.content) if request.content else {}
        if route == "POST /rest/v1/rpc/claim_deletion_request":
            for item in self.requests:
                if item.status == "pending":
                    item.status, item.attempts = "processing", item.attempts + 1
                    return httpx.Response(
                        200,
                        json=[
                            {
                                "attempts": item.attempts,
                                "auth_uid": self.claim_uid,
                                "contributor_id": CONTRIBUTOR,
                                "kind": item.kind,
                                "request_id": item.request_id,
                            }
                        ],
                    )
            return httpx.Response(200, json=[])
        if route == "POST /rest/v1/rpc/orphaned_photo_objects":
            listed = [name for name in self.orphans if name in self.objects["submission-photos"]]
            return httpx.Response(200, json=[{"name": name} for name in listed[: body["p_limit"]]])
        if route == "POST /rest/v1/rpc/apply_deletion_request":
            item = self._request(body["p_request_id"])
            covered = item.covered if item.kind == "withdraw_contributions" else self.submissions
            deleted = len(self.submissions & covered)
            self.submissions -= covered
            return httpx.Response(
                200, json=[{"deleted_submissions": deleted, "withdrawn_grants": 0}]
            )
        if route == "GET /rest/v1/submissions":
            assert request.url.params["contributor_id"] == f"eq.{CONTRIBUTOR}"
            return httpx.Response(200, json=[{"id": s} for s in sorted(self.submissions)])
        if request.url.path.startswith("/storage/v1/object/list/"):
            bucket = request.url.path.rsplit("/", 1)[1]
            children = self._children(bucket, body["prefix"])
            return httpx.Response(
                200, json=children[body["offset"] : body["offset"] + body["limit"]]
            )
        if request.method == "DELETE" and request.url.path.startswith("/storage/v1/object/"):
            bucket = request.url.path.rsplit("/", 1)[1]
            self.objects[bucket] -= set(body["prefixes"])
            return httpx.Response(200, json=[])
        if request.url.path.startswith("/auth/v1/admin/users/"):
            uid = request.url.path.rsplit("/", 1)[1]
            if uid not in self.auth_users:
                return httpx.Response(404, json={"error_code": "user_not_found"})
            self.auth_users.discard(uid)
            return httpx.Response(200, json={})
        if route == "POST /rest/v1/rpc/complete_deletion_request":
            item = self._request(body["p_request_id"])
            if self.submissions & (
                item.covered if item.kind == "withdraw_contributions" else self.submissions
            ):
                return httpx.Response(400, json={"code": "55000"})
            item.status = "completed"
            return httpx.Response(204)
        if route == "POST /rest/v1/rpc/release_deletion_request":
            item = self._request(body["p_request_id"])
            # Released requests wait before their retry (not_before), so a run never re-claims them.
            item.status, item.last_error = "released", body["p_error"]
            return httpx.Response(204)
        raise AssertionError(f"unexpected request {route}")


def worker_for(fake: FakeSupabase) -> SupabaseRightsWorker:
    worker = SupabaseRightsWorker("https://supabase.test", "service-key")
    worker.client = httpx.Client(transport=httpx.MockTransport(fake))
    return worker


def contributor_objects(*submissions: str) -> dict[str, set[str]]:
    return {
        "incoming-photos": {path(s, "A", "raw") for s in submissions},
        "submission-photos": {path(s, shot) for s in submissions for shot in ("A", "B")},
    }


def test_a_withdrawal_deletes_covered_rows_and_objects_but_keeps_newer_contributions() -> None:
    fake = FakeSupabase(
        requests=[Request("r1", "withdraw_contributions", covered={OLD})],
        submissions={OLD, NEWER},
        objects=contributor_objects(OLD, NEWER),
    )
    fake.objects["incoming-photos"].add(f"{UID}/stray.jpg")  # an orphan with no submission

    summary = worker_for(fake).run()

    assert (summary.completed, summary.failed, summary.submissions_deleted) == (1, 0, 1)
    assert fake.submissions == {NEWER}
    assert fake.objects == contributor_objects(NEWER)
    assert summary.objects_deleted == 4  # raw A, canonical A and B of OLD, and the stray
    assert fake.auth_users == {UID}, "a withdrawal never deletes the account"
    assert fake.requests[0].status == "completed"


def test_an_account_deletion_removes_everything_and_the_auth_user_before_completing() -> None:
    fake = FakeSupabase(
        requests=[Request("r2", "delete_account", covered=set())],
        submissions={OLD, NEWER},
        objects=contributor_objects(OLD, NEWER),
    )

    summary = worker_for(fake).run()

    assert summary.completed == 1
    assert fake.submissions == set()
    assert fake.objects == {bucket: set() for bucket in BUCKETS}
    assert fake.auth_users == set()
    # The auth user goes before the contributor row loses its auth id (complete pseudonymizes).
    auth = fake.calls.index(f"DELETE /auth/v1/admin/users/{UID}")
    assert auth < fake.calls.index("POST /rest/v1/rpc/complete_deletion_request")


def test_an_auth_user_that_is_already_gone_still_completes_the_request() -> None:
    # An earlier attempt deleted the auth user, then failed before completing.
    fake = FakeSupabase(
        requests=[Request("r3", "delete_account", covered=set())],
        submissions=set(),
        objects=contributor_objects(),
        auth_users=set(),
    )

    summary = worker_for(fake).run()

    assert (summary.completed, summary.failed) == (1, 0)
    assert f"DELETE /auth/v1/admin/users/{UID}" in fake.calls
    assert fake.requests[0].status == "completed"


@pytest.mark.parametrize(
    ("failing", "step"),
    [
        ("/storage/v1/object/list/", "storage:HTTPStatusError:500"),
        ("/auth/v1/admin/users/", "auth:HTTPStatusError:500"),
        ("rpc/apply_deletion_request", "apply:HTTPStatusError:500"),
    ],
)
def test_a_failed_step_releases_the_request_and_never_reports_it_done(
    failing: str, step: str
) -> None:
    fake = FakeSupabase(
        requests=[Request("r4", "delete_account", covered=set())],
        submissions={OLD},
        objects=contributor_objects(OLD),
        failures={failing: 500},
    )

    summary = worker_for(fake).run()

    assert (summary.completed, summary.failed) == (0, 1)
    assert fake.requests[0].last_error == step
    assert "POST /rest/v1/rpc/complete_deletion_request" not in fake.calls

    # The next run, with the outage over, finishes the job from wherever it stopped.
    fake.failures = {}
    fake.requests[0].status = "pending"
    retried = worker_for(fake).run()
    assert (retried.completed, retried.failed) == (1, 0)
    assert fake.submissions == set()
    assert fake.objects == {bucket: set() for bucket in BUCKETS}
    assert fake.auth_users == set()


def test_a_failed_release_does_not_stop_the_run() -> None:
    fake = FakeSupabase(
        requests=[
            Request("r5", "withdraw_contributions", covered={OLD}),
            Request("r6", "withdraw_contributions", covered=set()),
        ],
        submissions={OLD},
        objects=contributor_objects(OLD),
        failures={"rpc/apply_deletion_request": 500, "rpc/release_deletion_request": 503},
    )

    summary = worker_for(fake).run()

    assert summary.failed == 2
    assert fake.calls.count("POST /rest/v1/rpc/claim_deletion_request") == 3


def test_nothing_to_do_is_one_claim_and_one_orphan_check() -> None:
    fake = FakeSupabase(requests=[], submissions=set(), objects=contributor_objects())

    summary = worker_for(fake).run()

    assert (summary.completed, summary.failed, summary.orphans_deleted) == (0, 0, 0)
    assert fake.calls == [
        "POST /rest/v1/rpc/claim_deletion_request",
        "POST /rest/v1/rpc/orphaned_photo_objects",
    ]


def test_every_run_removes_canonical_objects_that_no_photo_row_owns() -> None:
    fake = FakeSupabase(requests=[], submissions={NEWER}, objects=contributor_objects(OLD, NEWER))
    fake.orphans = [path(OLD, "A"), path(OLD, "B")]  # left behind by a race with a withdrawal

    summary = worker_for(fake).run()

    assert summary.orphans_deleted == 2
    assert fake.objects["submission-photos"] == {path(NEWER, "A"), path(NEWER, "B")}


@pytest.mark.parametrize(
    ("object_path", "owner"),
    [
        (f"{UID}/{OLD}/B/x.jpg", OLD),
        (f"{UID}/stray.jpg", None),
        (f"{UID}//B/x.jpg", None),
    ],
)
def test_objects_are_owned_by_the_submission_in_their_path(
    object_path: str, owner: str | None
) -> None:
    assert owning_submission(object_path) == owner


def test_storage_listing_walks_folders_and_pages() -> None:
    names = {f"{UID}/{OLD}/B/{index:04d}.jpg" for index in range(1001)}
    fake = FakeSupabase(requests=[], submissions=set(), objects={"submission-photos": names})
    storage = SupabaseStorage(httpx.Client(transport=httpx.MockTransport(fake)), "https://s.test")

    listed = storage.list_objects("submission-photos", UID)

    assert set(listed) == names
    assert (
        fake.calls.count("POST /storage/v1/object/list/submission-photos") == 4
    )  # 3 levels, 2 pages


def test_storage_deletes_in_batches() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[])

    storage = SupabaseStorage(
        httpx.Client(transport=httpx.MockTransport(handler)), "https://s.test"
    )

    assert storage.delete_objects("incoming-photos", [f"p{index}" for index in range(250)]) == 250
    assert [len(json.loads(request.content)["prefixes"]) for request in requests] == [100, 100, 50]
    assert storage.delete_objects("incoming-photos", []) == 0
    assert len(requests) == 3
