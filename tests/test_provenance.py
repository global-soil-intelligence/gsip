"""WP-6e capture evidence (I7, I10): allowlisted, coordinate-free, and the only path to tier 1."""

from __future__ import annotations

import inspect
import io
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from PIL import ExifTags, Image, TiffImagePlugin

from pipeline.provenance import (
    EVIDENCE_KEYS,
    EVIDENCE_VERSION,
    GPS_TOLERANCE_M,
    TIME_TOLERANCE_S,
    CaptureEvidence,
    capture_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
R = TiffImagePlugin.IFDRational

# The claimed capture: Burlington, Vermont, 12:00:00 UTC (08:00 local, UTC-4).
CLAIMED_AT = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
LATITUDE = 44.4759
LONGITUDE = -73.2121


def dms(value: float) -> tuple[R, R, R]:
    degrees = int(value)
    minutes_float = (value - degrees) * 60
    minutes = int(minutes_float)
    seconds = round((minutes_float - minutes) * 60 * 10_000)
    return (R(degrees), R(minutes), R(seconds, 10_000))


def photo(
    *,
    local_time: str | None = None,
    offset: str | None = None,
    gps_position: tuple[float, float] | None = None,
    gps_time: tuple[str, tuple[int, int, int]] | None = None,
) -> bytes:
    image = Image.new("RGB", (32, 24), (110, 80, 45))
    exif = Image.Exif()
    exif[ExifTags.Base.Make] = "Fixture camera"
    if local_time is not None or offset is not None:
        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        if local_time is not None:
            exif_ifd[ExifTags.Base.DateTimeOriginal] = local_time
        if offset is not None:
            exif_ifd[ExifTags.Base.OffsetTimeOriginal] = offset
    if gps_position is not None or gps_time is not None:
        gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        if gps_position is not None:
            latitude, longitude = gps_position
            gps[ExifTags.GPS.GPSLatitudeRef] = "N" if latitude >= 0 else "S"
            gps[ExifTags.GPS.GPSLatitude] = dms(abs(latitude))
            gps[ExifTags.GPS.GPSLongitudeRef] = "E" if longitude >= 0 else "W"
            gps[ExifTags.GPS.GPSLongitude] = dms(abs(longitude))
        if gps_time is not None:
            day, (hours, minutes, seconds) = gps_time
            gps[ExifTags.GPS.GPSDateStamp] = day
            gps[ExifTags.GPS.GPSTimeStamp] = (R(hours), R(minutes), R(seconds))
    output = io.BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return output.getvalue()


def evidence(raw: bytes, claimed_at: datetime | None = CLAIMED_AT) -> CaptureEvidence:
    return capture_evidence(raw, claimed_at=claimed_at, latitude=LATITUDE, longitude=LONGITUDE)


def test_a_consistent_camera_photo_is_corroborated() -> None:
    found = evidence(
        photo(
            local_time="2026:10:11 08:00:42",
            offset="-04:00",
            gps_position=(44.4762, -73.2125),
        )
    )
    assert found == CaptureEvidence(
        exif_time_present=True,
        exif_time_absolute=True,
        exif_time_delta_s=42,
        exif_gps_present=True,
        exif_gps_distance_m=found.exif_gps_distance_m,
    )
    assert found.exif_gps_distance_m is not None and 30 <= found.exif_gps_distance_m <= 60
    assert found.tier == 1


def test_evidence_holds_only_allowlisted_fields_and_never_coordinates_or_times() -> None:
    raw = photo(
        local_time="2026:10:11 08:00:42",
        offset="-04:00",
        gps_position=(44.4762, -73.2125),
        gps_time=("2026:10:11", (12, 0, 40)),
    )
    stored = evidence(raw).private_json()
    assert set(stored) == EVIDENCE_KEYS
    assert stored["evidence_version"] == EVIDENCE_VERSION
    assert all(
        isinstance(value, (bool, int, type(None)))
        for key, value in stored.items()
        if key != "evidence_version"
    )
    text = json.dumps(stored)
    for leak in ("44.47", "73.21", "2026", "08:00", "12:00"):
        assert leak not in text


def test_the_python_allowlist_is_the_database_allowlist() -> None:
    migration = (ROOT / "supabase/migrations/20261010150000_wp6e_provenance.sql").read_text()
    block = re.search(
        r"photos_capture_evidence_allowlist.*?array\[(.*?)\]::text\[\]", migration, re.S
    )
    assert block is not None
    assert set(re.findall(r"'([a-z_]+)'", block.group(1))) == EVIDENCE_KEYS


def test_a_wall_clock_time_without_an_offset_corroborates_nothing() -> None:
    found = evidence(photo(local_time="2026:10:11 12:00:00"))
    assert found.exif_time_present and not found.exif_time_absolute
    assert found.exif_time_delta_s is None
    assert found.tier == 0


def test_the_gps_fix_time_is_an_absolute_time() -> None:
    found = evidence(photo(gps_time=("2026:10:11", (11, 59, 30))))
    assert found.exif_time_absolute and found.exif_time_delta_s == 30
    assert not found.exif_gps_present
    assert found.tier == 1


def test_an_embedded_position_far_from_the_claim_blocks_corroboration() -> None:
    found = evidence(
        photo(
            local_time="2026:10:11 08:00:00",
            offset="-04:00",
            gps_position=(44.4859, -73.2121),  # about 1.1 km north
        )
    )
    assert found.exif_gps_present
    assert found.exif_gps_distance_m is not None and found.exif_gps_distance_m > GPS_TOLERANCE_M
    assert found.tier == 0


@pytest.mark.parametrize(
    ("local_time", "offset", "tier"),
    [
        ("2026:10:11 08:29:59", "-04:00", 1),
        ("2026:10:11 08:30:00", "-04:00", 1),
        ("2026:10:11 08:30:01", "-04:00", 0),
        # A mis-set time zone is off by whole hours and never corroborates.
        ("2026:10:11 08:00:00", "-05:00", 0),
        ("2026:10:10 08:00:00", "-04:00", 0),
    ],
)
def test_the_time_tolerance_is_inclusive_at_half_an_hour(
    local_time: str, offset: str, tier: int
) -> None:
    assert TIME_TOLERANCE_S == 1800
    assert evidence(photo(local_time=local_time, offset=offset)).tier == tier


def test_no_metadata_is_no_evidence() -> None:
    found = evidence(photo())
    assert found == CaptureEvidence()
    assert found.tier == 0


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"not-an-image",
        b"\xff\xd8\xff\xe1\x00\x10Exif\x00\x00MM\x00*garbage",
        photo(local_time="2026:13:45 25:61:61", offset="-04:00"),
        photo(local_time="2026:10:11 08:00:00", offset="+99:00"),
        photo(local_time="    :  :     :  :  ", offset="      "),
    ],
)
def test_hostile_or_malformed_metadata_is_no_evidence_and_never_raises(raw: bytes) -> None:
    found = evidence(raw)
    assert not found.exif_time_absolute
    assert found.tier == 0


def test_a_zero_zero_position_means_no_fix() -> None:
    found = evidence(
        photo(local_time="2026:10:11 08:00:00", offset="-04:00", gps_position=(0.0, 0.0))
    )
    assert not found.exif_gps_present
    assert found.tier == 1


@pytest.mark.parametrize("claimed_at", [None, datetime(2026, 10, 11, 12, 0, 0)])
def test_a_missing_or_naive_claim_corroborates_nothing(claimed_at: datetime | None) -> None:
    found = evidence(photo(local_time="2026:10:11 08:00:00", offset="-04:00"), claimed_at)
    assert found.exif_time_absolute and found.exif_time_delta_s is None
    assert found.tier == 0


def test_tiers_never_exceed_one() -> None:
    best = CaptureEvidence(
        exif_time_present=True,
        exif_time_absolute=True,
        exif_time_delta_s=0,
        exif_gps_present=True,
        exif_gps_distance_m=0,
    )
    assert best.tier == 1


def test_the_claim_inputs_are_only_time_and_place() -> None:
    # Client claims (ingest path, capture method, location source) are not parameters, so no
    # claim can raise a tier: only the photo's own bytes and the claimed time and point count.
    parameters = set(inspect.signature(capture_evidence).parameters)
    assert parameters == {"raw", "claimed_at", "latitude", "longitude"}


def test_evidence_survives_a_later_offset_shift_only_within_tolerance() -> None:
    # The claim is the file timestamp; a capture 29 minutes before it still corroborates.
    claimed = CLAIMED_AT + timedelta(minutes=29)
    found = evidence(photo(local_time="2026:10:11 08:00:00", offset="-04:00"), claimed)
    assert found.exif_time_delta_s == 29 * 60 and found.tier == 1
