"""List candidate public soil photo galleries with their licences (WP-COLLECT-6).

Reads album and licence metadata only, through the gallery host's public API. It never requests
an image, a thumbnail or an image address, and it writes no photo, photo ID, owner name or
description: only album titles, photo counts and a tally of licences per album.

A listing is a starting point for a rights review, not permission to use anything. A licence
tally says what the host reports, which can be wrong or can change. Nothing here downloads,
redistributes, trains on or publishes a photo.

Needs a Flickr API key in ``FLICKR_API_KEY`` (see ``.env.example``). Not run against the live
service by GSIP: the tests use recorded-shape fixtures only.

    uv run python -m scripts.list_photo_galleries > galleries.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

FLICKR_API = "https://api.flickr.com/services/rest/"
# Only these fields are ever asked for about a photo.
PHOTO_EXTRAS = "license"
MAX_ALBUMS = 200
MAX_PAGES_PER_ALBUM = 20
PAGE_SIZE = 500
PAUSE_SECONDS = 1.0


@dataclass(frozen=True)
class Candidate:
    name: str
    kind: str
    url: str
    note: str


# Galleries people have pointed GSIP to. Being listed says nothing about licence or suitability.
CANDIDATES: tuple[Candidate, ...] = (
    Candidate(
        name="SSSNC soil photo albums",
        kind="flickr_user",
        url="https://www.flickr.com/photos/jakelley/",
        note="Suggested in feedback of November 2026; ownership and licences not verified.",
    ),
)


class GalleryError(RuntimeError):
    """A generic failure. It never carries the request address, which holds the API key."""


def _call(client: httpx.Client, api_key: str, method: str, **params: str) -> dict[str, Any]:
    try:
        response = client.get(
            FLICKR_API,
            params={
                "method": method,
                "api_key": api_key,
                "format": "json",
                "nojsoncallback": "1",
                **params,
            },
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError):
        raise GalleryError(f"gallery request failed: {method}") from None
    if not isinstance(body, dict) or body.get("stat") != "ok":
        raise GalleryError(f"gallery request refused: {method}")
    return body


def _text(value: object) -> str:
    """Flickr wraps text as ``{"_content": "..."}``. Titles are other people's text: data only."""

    content = value.get("_content") if isinstance(value, dict) else value
    return content[:200] if isinstance(content, str) else ""


def licence_names(client: httpx.Client, api_key: str) -> dict[str, dict[str, str]]:
    body = _call(client, api_key, "flickr.photos.licenses.getInfo")
    result: dict[str, dict[str, str]] = {}
    for item in body.get("licenses", {}).get("license", []):
        if isinstance(item, dict):
            result[str(item.get("id"))] = {
                "name": str(item.get("name", ""))[:120],
                "url": str(item.get("url", ""))[:200],
            }
    return result


def list_flickr_user(
    client: httpx.Client,
    api_key: str,
    profile_url: str,
    *,
    pause: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    """Albums of one public account, each with a photo count and a licence tally."""

    user = _call(client, api_key, "flickr.urls.lookupUser", url=profile_url)
    user_id = str(user.get("user", {}).get("id", ""))
    if not user_id:
        raise GalleryError("gallery account not found")
    names = licence_names(client, api_key)
    sets = _call(
        client, api_key, "flickr.photosets.getList", user_id=user_id, per_page=str(MAX_ALBUMS)
    )
    albums: list[dict[str, Any]] = []
    for album in sets.get("photosets", {}).get("photoset", [])[:MAX_ALBUMS]:
        if not isinstance(album, dict) or not album.get("id"):
            continue
        album_id = str(album["id"])
        tally: Counter[str] = Counter()
        pages, page = 1, 1
        while page <= min(pages, MAX_PAGES_PER_ALBUM):
            pause(PAUSE_SECONDS)
            body = _call(
                client,
                api_key,
                "flickr.photosets.getPhotos",
                photoset_id=album_id,
                user_id=user_id,
                extras=PHOTO_EXTRAS,
                media="photos",
                per_page=str(PAGE_SIZE),
                page=str(page),
            )
            listing = body.get("photoset", {})
            pages = int(listing.get("pages", 1) or 1)
            for photo in listing.get("photo", []):
                if isinstance(photo, dict):
                    tally[str(photo.get("license", "unknown"))] += 1
            page += 1
        albums.append(
            {
                "album_url": f"{profile_url.rstrip('/')}/albums/{album_id}",
                "title_untrusted": _text(album.get("title")),
                "photos_counted": sum(tally.values()),
                "truncated": pages > MAX_PAGES_PER_ALBUM,
                "licences": [
                    {
                        "licence_id": licence_id,
                        "name": names.get(licence_id, {}).get("name", "unknown"),
                        "url": names.get(licence_id, {}).get("url", ""),
                        "photos": count,
                    }
                    for licence_id, count in sorted(tally.items())
                ],
            }
        )
    return albums


def build_listing(client: httpx.Client, api_key: str) -> dict[str, Any]:
    galleries = []
    for candidate in CANDIDATES:
        entry: dict[str, Any] = {
            "name": candidate.name,
            "url": candidate.url,
            "note": candidate.note,
        }
        try:
            entry["albums"] = list_flickr_user(client, api_key, candidate.url)
        except GalleryError as error:
            entry["error"] = str(error)
        galleries.append(entry)
    return {
        "notice": (
            "Metadata only. No photo was downloaded. A licence shown here is what the host "
            "reported and is not permission: review each album's terms and attribution before "
            "any use. Titles are untrusted text."
        ),
        "galleries": galleries,
    }


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    api_key = os.environ.get("FLICKR_API_KEY", "").strip()
    if not api_key:
        print("Set FLICKR_API_KEY to list galleries; nothing was requested.", file=sys.stderr)
        return 2
    with httpx.Client(timeout=20.0, follow_redirects=False) as client:
        print(json.dumps(build_listing(client, api_key), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
