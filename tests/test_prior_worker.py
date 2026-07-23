from __future__ import annotations

import httpx

from pipeline.prior_worker import SupabasePriorWorker


def test_drain_retries_pending_and_dead_letter_jobs_with_service_role() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/rest/v1/prior_jobs":
            return httpx.Response(200, json=[{"submission_id": "a"}, {"submission_id": "b"}])
        return httpx.Response(200, json={"status": "completed"})

    worker = SupabasePriorWorker("https://supabase.test", "service-key")
    worker.client = httpx.Client(transport=httpx.MockTransport(handler))

    assert worker.drain() == (2, 0)
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
        if request.url.path == "/rest/v1/prior_jobs":
            return httpx.Response(200, json=[{"submission_id": "a"}, {"submission_id": "b"}])
        if request.url.path.endswith("requeue_stale_prior_jobs"):
            return httpx.Response(200)
        calls += 1
        return httpx.Response(502 if calls == 1 else 200)

    worker = SupabasePriorWorker("https://supabase.test", "service-key")
    worker.client = httpx.Client(transport=httpx.MockTransport(handler))

    assert worker.drain() == (1, 1)
    assert calls == 2
