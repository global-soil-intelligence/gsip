"""The gallery lister reads metadata only (WP-COLLECT-6). No live service is contacted."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from scripts import list_photo_galleries as galleries

KEY = "fictional-key"
PROFILE = "https://www.flickr.com/photos/fictional-account/"


def reply(payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json={"stat": "ok", **payload})


def router(request: httpx.Request) -> httpx.Response:
    params = dict(request.url.params)
    method = params["method"]
    if method == "flickr.urls.lookupUser":
        return reply({"user": {"id": "00000000@N00"}})
    if method == "flickr.photos.licenses.getInfo":
        return reply(
            {
                "licenses": {
                    "license": [
                        {"id": "0", "name": "All Rights Reserved", "url": ""},
                        {"id": "4", "name": "Attribution", "url": "https://example.test/by"},
                    ]
                }
            }
        )
    if method == "flickr.photosets.getList":
        return reply(
            {"photosets": {"photoset": [{"id": "111", "title": {"_content": "Fictional album"}}]}}
        )
    if method == "flickr.photosets.getPhotos":
        page = params["page"]
        photos = [{"id": "1", "license": "4"}, {"id": "2", "license": "0"}]
        return reply({"photoset": {"pages": 2, "photo": photos if page == "1" else photos[:1]}})
    return httpx.Response(404)


@respx.mock
def test_lists_albums_with_licence_tallies_and_requests_no_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(galleries, "PAUSE_SECONDS", 0.0)
    route = respx.get(galleries.FLICKR_API).mock(side_effect=router)
    with httpx.Client() as client:
        listing = galleries.build_listing(client, KEY, [PROFILE])
    [gallery] = listing["galleries"]
    [album] = gallery["albums"]
    assert gallery["albums_truncated"] is False
    assert album["title_untrusted"] == "Fictional album"
    assert album["photos_counted"] == 3 and album["truncated"] is False
    assert album["licences"] == [
        {"licence_id": "0", "name": "All Rights Reserved", "url": "", "photos": 1},
        {"licence_id": "4", "name": "Attribution", "url": "https://example.test/by", "photos": 2},
    ]
    assert "not permission" in listing["notice"]
    # Every request went to the metadata API and asked for the licence field only.
    assert route.call_count == 5
    for call in route.calls:
        assert call.request.url.host == "api.flickr.com"
        extras = call.request.url.params.get("extras", "license")
        assert extras == "license" and "url" not in extras
    # Nothing identifying a photo or its owner is kept, and the key is not in the output.
    written = json.dumps(listing)
    for forbidden in (KEY, "00000000@N00", '"id"', "staticflickr", ".jpg"):
        assert forbidden not in written


@respx.mock
def test_a_refused_request_is_reported_without_the_key() -> None:
    respx.get(galleries.FLICKR_API).mock(
        return_value=httpx.Response(200, json={"stat": "fail", "message": KEY})
    )
    with httpx.Client() as client:
        listing = galleries.build_listing(client, KEY, [PROFILE])
    assert listing["galleries"][0]["error"] == "gallery request refused: flickr.urls.lookupUser"
    assert KEY not in json.dumps(listing)


def test_without_a_key_nothing_is_requested(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("FLICKR_API_KEY", raising=False)
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(galleries.FLICKR_API)
        assert galleries.main(["--flickr-user", PROFILE]) == 2
        assert route.call_count == 0
    assert "nothing was requested" in capsys.readouterr().err


@respx.mock
def test_more_albums_than_listed_and_an_odd_page_count_are_reported_not_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(galleries, "PAUSE_SECONDS", 0.0)

    def odd(request: httpx.Request) -> httpx.Response:
        method = request.url.params["method"]
        if method == "flickr.photosets.getList":
            return reply({"photosets": {"pages": 3, "photoset": [{"id": "111", "title": "x"}]}})
        if method == "flickr.photosets.getPhotos":
            return reply({"photoset": {"pages": "many", "photo": [{"license": "4"}]}})
        return router(request)

    respx.get(galleries.FLICKR_API).mock(side_effect=odd)
    with httpx.Client() as client:
        [gallery] = galleries.build_listing(client, KEY, [PROFILE])["galleries"]
    assert gallery["albums_truncated"] is True
    assert gallery["albums"][0]["photos_counted"] == 1


def test_no_account_is_built_in_and_only_a_public_profile_address_is_taken() -> None:
    source = (galleries.__file__ and open(galleries.__file__, encoding="utf-8").read()) or ""
    assert "flickr.com/photos/" in source and "photos/j" not in source
    with pytest.raises(SystemExit):
        galleries.main([])
    with pytest.raises(SystemExit):
        galleries.main(["--flickr-user", "https://example.test/photos/x/"])
