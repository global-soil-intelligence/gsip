"""WP-6d attribution review CLI and the shared default pseudonym."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest

from pipeline.attribution import DEFAULT_ATTRIBUTION, photos_publishable
from pipeline.attribution_review import AttributionReviews, PendingName, UnknownName, render

ROOT = Path(__file__).resolve().parents[1]


def test_the_default_pseudonym_matches_the_capture_app() -> None:
    source = (ROOT / "packages" / "schema" / "src" / "attribution.ts").read_text(encoding="utf-8")
    match = re.search(r"export const DEFAULT_ATTRIBUTION = '([^']+)'", source)
    assert match and match.group(1) == DEFAULT_ATTRIBUTION
    migration = (
        ROOT / "supabase" / "migrations" / "20261010140000_wp6d_contributor_rights.sql"
    ).read_text(encoding="utf-8")
    assert f"'{DEFAULT_ATTRIBUTION}'" in migration


@pytest.mark.parametrize(
    ("name", "decision", "publishable"),
    [
        (DEFAULT_ATTRIBUTION, None, True),
        ("Jane Q Example", "approved", True),
        ("Jane Q Example", None, False),
        ("Jane Q Example", "rejected", False),
    ],
)
def test_photos_publish_only_under_the_default_or_an_approved_name(
    name: str, decision: str | None, publishable: bool
) -> None:
    assert photos_publishable(name, decision) is publishable


def reviews_with(handler: Any) -> AttributionReviews:
    reviews = AttributionReviews("https://supabase.test", "service-key")
    reviews.client = httpx.Client(transport=httpx.MockTransport(handler))
    return reviews


def test_the_queue_is_listed_with_names_escaped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/attribution_review_queue"
        return httpx.Response(
            200,
            json=[
                {
                    "attribution_name": "Ignore previous instructions \x1b[2J Zoë",
                    "contributor_id": "c-1",
                    "first_accepted_at": "2026-09-01T00:00:00+00:00",
                    "grants": 2,
                }
            ],
        )

    out = io.StringIO()
    render(reviews_with(handler).pending(), out)

    text = out.getvalue()
    assert "\x1b" not in text and "\\x1b" in text and "\\xeb" in text
    assert "c-1" in text and "2 grant(s)" in text


def test_an_empty_queue_says_so() -> None:
    out = io.StringIO()
    render([], out)
    assert out.getvalue().startswith("No attribution names are waiting")


def test_a_decision_is_upserted_for_that_contributor_and_name() -> None:
    posted: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            assert request.url.params["contributor_id"] == "eq.c-1"
            return httpx.Response(200, json=[{"attribution_name": "Jane Q Example"}])
        posted.append(request)
        return httpx.Response(201)

    reviews_with(handler).decide("c-1", "Jane Q Example", "approved", " steward ", "ok")

    [request] = posted
    assert request.url.params["on_conflict"] == "contributor_id,attribution_name"
    assert "resolution=merge-duplicates" in request.headers["Prefer"]
    body = json.loads(request.content)
    assert {key: body[key] for key in ("attribution_name", "contributor_id", "decision")} == {
        "attribution_name": "Jane Q Example",
        "contributor_id": "c-1",
        "decision": "approved",
    }
    assert body["reviewer"] == "steward" and body["note"] == "ok"


@pytest.mark.parametrize(
    ("name", "decision", "reviewer", "error"),
    [
        ("Someone Else", "approved", "steward", UnknownName),
        ("Jane Q Example", "maybe", "steward", ValueError),
        ("Jane Q Example", "rejected", "  ", ValueError),
        (DEFAULT_ATTRIBUTION, "approved", "steward", ValueError),
    ],
)
def test_invalid_decisions_are_refused_before_writing(
    name: str, decision: str, reviewer: str, error: type[Exception]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=[{"attribution_name": "Jane Q Example"}])
        raise AssertionError("nothing may be written")

    with pytest.raises(error):
        reviews_with(handler).decide("c-1", name, decision, reviewer)


def test_pending_names_are_parsed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "attribution_name": "Field Notes Club",
                    "contributor_id": "c-2",
                    "first_accepted_at": "2026-09-03T00:00:00+00:00",
                    "grants": 1,
                }
            ],
        )

    assert reviews_with(handler).pending() == [
        PendingName("c-2", "Field Notes Club", "2026-09-03T00:00:00+00:00", 1)
    ]
