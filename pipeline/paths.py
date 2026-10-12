"""Storage paths are derived facts, never client choices (SPEC section 6, WP-6b)."""

from __future__ import annotations

import re

UUID_PATTERN = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


class StoragePathMismatch(ValueError):
    """A stored photo path does not match the path the database facts require."""


def expected_photo_path_pattern(
    auth_uid: str, submission_id: str, shot_type: str
) -> re.Pattern[str]:
    """The only object path a photo row may name: {auth_uid}/{submission_id}/{shot}/{uuid}.jpg."""

    for value in (auth_uid, submission_id):
        if not re.fullmatch(UUID_PATTERN, value):
            raise StoragePathMismatch("database facts do not form a bindable path")
    if shot_type not in {"A", "B", "C"}:
        raise StoragePathMismatch("database facts do not form a bindable path")
    return re.compile(
        f"^{re.escape(auth_uid)}/{re.escape(submission_id)}/{shot_type}/{UUID_PATTERN}\\.jpg$"
    )


def verify_photo_path(path: str, auth_uid: str, submission_id: str, shot_type: str) -> str:
    """Return ``path`` if it is the bound path for these facts, else raise StoragePathMismatch."""

    if not expected_photo_path_pattern(auth_uid, submission_id, shot_type).fullmatch(path):
        raise StoragePathMismatch("photo storage path does not match its owner and submission")
    return path
