from __future__ import annotations

import httpx

from pipeline.prior_worker import SupabasePriorWorker


def worker_for(handler: httpx.MockTransport) -> SupabasePriorWorker:
    worker = SupabasePriorWorker("https://supabase.test", "service-key")
    worker.client = httpx.Client(transport=handler)
    return worker


def test_drain_requeues_stale_claims_then_retries_pending_and_dead_letter_jobs() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/rest/v1/rpc/requeue_stale_prior_jobs":
            return httpx.Response(200, json=1)
        if request.url.path == "/rest/v1/prior_jobs":
            return httpx.Response(200, json=[{"submission_id": "a"}, {"submission_id": "b"}])
        return httpx.Response(200, json={"status": "completed"})

    summary = worker_for(httpx.MockTransport(handler)).drain()

    assert (summary.completed, summary.failed, summary.requeued) == (2, 0, 1)
    assert requests[0].url.path == "/rest/v1/rpc/requeue_stale_prior_jobs"
    assert requests[1].url.params["status"] == "in.(pending,dead_letter)"
    assert requests[1].url.params["attempts"] == "lt.32"
    assert [request.url.path for request in requests[2:]] == [
        "/functions/v1/prior-attach",
        "/functions/v1/prior-attach",
    ]


def test_drain_continues_after_one_invocation_fails() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path == "/rest/v1/rpc/requeue_stale_prior_jobs":
            return httpx.Response(200, json=0)
        if request.url.path == "/rest/v1/prior_jobs":
            return httpx.Response(200, json=[{"submission_id": "a"}, {"submission_id": "b"}])
        calls += 1
        return httpx.Response(502 if calls == 1 else 200)

    summary = worker_for(httpx.MockTransport(handler)).drain()

    assert (summary.completed, summary.failed) == (1, 1)
    assert calls == 2


def test_drain_stops_at_the_first_rate_limit_deferral() -> None:
    invoked: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/rpc/requeue_stale_prior_jobs":
            return httpx.Response(200, json=0)
        if request.url.path == "/rest/v1/prior_jobs":
            return httpx.Response(
                200,
                json=[{"submission_id": "a"}, {"submission_id": "b"}, {"submission_id": "c"}],
            )
        invoked.append(request.content.decode())
        return httpx.Response(202 if len(invoked) == 2 else 200, json={"status": "deferred"})

    summary = worker_for(httpx.MockTransport(handler)).drain()

    assert summary.deferred
    assert summary.completed == 1
    assert len(invoked) == 2


def test_jobs_that_cannot_be_claimed_are_skipped_not_failed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/rpc/requeue_stale_prior_jobs":
            return httpx.Response(200, json=0)
        if request.url.path == "/rest/v1/prior_jobs":
            return httpx.Response(200, json=[{"submission_id": "a"}])
        return httpx.Response(409, json={"status": "not_claimable"})

    summary = worker_for(httpx.MockTransport(handler)).drain()

    assert (summary.completed, summary.failed, summary.skipped) == (0, 0, 1)
