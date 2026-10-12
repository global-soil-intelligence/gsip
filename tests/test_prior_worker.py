from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from pipeline.prior_worker import SupabasePriorWorker, retry_after_seconds

Handler = Callable[[httpx.Request], httpx.Response]


class FakeClock:
    """A monotonic clock that only moves when the worker sleeps or a test advances it."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def worker_for(handler: Handler, clock: FakeClock | None = None) -> SupabasePriorWorker:
    clock = clock or FakeClock()
    worker = SupabasePriorWorker(
        "https://supabase.test", "service-key", clock=clock, sleep=clock.sleep
    )
    worker.client = httpx.Client(transport=httpx.MockTransport(handler))
    return worker


def queue(*submission_ids: str, function: Handler) -> Handler:
    """Serves requeue and the due-job list, records rotations, and delegates invocations."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/rpc/requeue_stale_prior_jobs":
            return httpx.Response(200, json=0)
        if request.url.path == "/rest/v1/prior_jobs" and request.method == "GET":
            return httpx.Response(200, json=[{"submission_id": s} for s in submission_ids])
        if request.url.path == "/rest/v1/prior_jobs" and request.method == "PATCH":
            return httpx.Response(204)
        return function(request)

    return handler


def invoked_ids(requests: list[httpx.Request]) -> list[str]:
    return [
        json.loads(request.content)["submissionId"]
        for request in requests
        if request.url.path == "/functions/v1/prior-attach"
    ]


def test_drain_requeues_stale_claims_then_retries_pending_and_dead_letter_jobs() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/rest/v1/rpc/requeue_stale_prior_jobs":
            return httpx.Response(200, json=1)
        if request.url.path == "/rest/v1/prior_jobs":
            return httpx.Response(200, json=[{"submission_id": "a"}, {"submission_id": "b"}])
        return httpx.Response(200, json={"status": "completed"})

    summary = worker_for(handler).drain()

    assert (summary.completed, summary.failed, summary.requeued) == (2, 0, 1)
    assert requests[0].url.path == "/rest/v1/rpc/requeue_stale_prior_jobs"
    assert requests[1].url.params["status"] == "in.(pending,dead_letter)"
    assert requests[1].url.params["attempts"] == "lt.32"
    assert requests[1].url.params["order"] == "updated_at.asc"
    assert invoked_ids(requests) == ["a", "b"]


def test_a_deferred_job_waits_for_retry_after_then_runs() -> None:
    requests: list[httpx.Request] = []
    clock = FakeClock()

    def function(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(202, json={"status": "deferred"}, headers={"Retry-After": "9"})
        return httpx.Response(200, json={"status": "completed"})

    summary = worker_for(queue("a", "b", function=function), clock).drain()

    assert clock.sleeps == [9]
    assert invoked_ids(requests) == ["a", "a", "b"]
    assert (summary.completed, summary.deferred, summary.waited_seconds) == (2, False, 9)


def test_the_drain_stops_when_the_next_wait_does_not_fit_its_budget() -> None:
    requests: list[httpx.Request] = []
    clock = FakeClock()

    def function(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202, json={"status": "deferred"}, headers={"Retry-After": "300"})

    summary = worker_for(queue("a", "b", function=function), clock).drain(budget_seconds=240)

    assert summary.deferred
    assert clock.sleeps == []
    assert invoked_ids(requests) == ["a"]


def test_endless_deferrals_still_end_within_the_budget() -> None:
    clock = FakeClock()

    def function(request: httpx.Request) -> httpx.Response:
        return httpx.Response(202, json={"status": "deferred"}, headers={"Retry-After": "0"})

    summary = worker_for(queue("a", function=function), clock).drain(budget_seconds=30)

    assert summary.deferred
    assert clock.now <= 30
    assert all(seconds >= 1 for seconds in clock.sleeps)


def test_no_new_job_starts_once_the_budget_is_spent() -> None:
    requests: list[httpx.Request] = []
    clock = FakeClock()

    def function(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        clock.now += 200  # a slow invocation
        return httpx.Response(200, json={"status": "completed"})

    summary = worker_for(queue("a", "b", function=function), clock).drain(budget_seconds=150)

    assert summary.out_of_time
    assert invoked_ids(requests) == ["a"]


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, 12),
        ("", 12),
        ("soon", 12),
        ("Wed, 21 Oct 2026 07:28:00 GMT", 12),
        ("0", 1),
        ("7", 7),
        ("100000", 300),
    ],
)
def test_retry_after_is_read_as_bounded_whole_seconds(header: str | None, expected: int) -> None:
    headers = {} if header is None else {"Retry-After": header}
    assert retry_after_seconds(httpx.Response(202, headers=headers)) == expected


def test_a_failed_invocation_moves_only_an_unclaimed_job_behind_the_queue() -> None:
    requests: list[httpx.Request] = []
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        requests.append(request)
        if request.url.path == "/rest/v1/rpc/requeue_stale_prior_jobs":
            return httpx.Response(200, json=0)
        if request.url.path == "/rest/v1/prior_jobs" and request.method == "GET":
            return httpx.Response(200, json=[{"submission_id": "a"}, {"submission_id": "b"}])
        if request.method == "PATCH":
            return httpx.Response(204)
        calls += 1
        return httpx.Response(503 if calls == 1 else 200)

    summary = worker_for(handler).drain()

    assert (summary.completed, summary.failed) == (1, 1)
    assert invoked_ids(requests) == ["a", "b"]
    [rotation] = [request for request in requests if request.method == "PATCH"]
    assert rotation.url.params["submission_id"] == "eq.a"
    # Never a processing job: that would hide a stale claim from requeue_stale_prior_jobs.
    assert rotation.url.params["status"] == "in.(pending,dead_letter)"
    assert set(json.loads(rotation.content)) == {"updated_at"}


def test_a_failed_rotation_does_not_stop_the_drain() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/rest/v1/rpc/requeue_stale_prior_jobs":
            return httpx.Response(200, json=0)
        if request.url.path == "/rest/v1/prior_jobs" and request.method == "GET":
            return httpx.Response(200, json=[{"submission_id": "a"}, {"submission_id": "b"}])
        if request.method == "PATCH":
            return httpx.Response(500)
        return httpx.Response(502)

    summary = worker_for(handler).drain()

    assert summary.failed == 2
    assert invoked_ids(requests) == ["a", "b"]


def test_jobs_that_cannot_be_claimed_are_skipped_not_failed() -> None:
    def function(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"status": "not_claimable"})

    summary = worker_for(queue("a", function=function)).drain()

    assert (summary.completed, summary.failed, summary.skipped) == (0, 0, 1)
