"""WP-6e capture evidence (I7, I10): allowlisted, coordinate-free measurements, never a tier.

The database derives tiers from this evidence; its rule and boundaries are tested in pgTAP
(`supabase/tests/database/wp6e_provenance.test.sql`).
"""

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
    CaptureEvidence,
    capture_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
R = TiffImagePlugin.IFDRational

# The claimed capture: Burlington, Vermont, 12:00:00 UTC (08:00 local, UTC-4); the person accepted
# the terms five minutes later.
CLAIMED_AT = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
ACCEPTED_AT = CLAIMED_AT + timedelta(minutes=5)
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


def evidence(
    raw: bytes,
    claimed_at: datetime | None = CLAIMED_AT,
    accepted_at: datetime | None = ACCEPTED_AT,
) -> CaptureEvidence:
    return capture_evidence(
        raw,
        claimed_at=claimed_at,
        accepted_at=accepted_at,
        latitude=LATITUDE,
        longitude=LONGITUDE,
    )


def test_a_camera_photo_is_measured_against_the_claim_and_the_acceptance() -> None:
    found = evidence(
        photo(
            local_time="2026:10:11 08:00:42",
            offset="-04:00",
            gps_position=(44.4762, -73.2125),
        )
    )
    assert found.exif_time_present and found.exif_time_absolute
    assert found.exif_time_delta_s == 42
    # Taken at 12:00:42 UTC, accepted at 12:05:00 UTC.
    assert found.exif_age_at_acceptance_s == 258
    assert found.exif_gps_present
    assert found.exif_gps_distance_m is not None and 30 <= found.exif_gps_distance_m <= 60


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
    for key, value in stored.items():
        if key != "evidence_version":
            assert value is None or type(value) in (bool, int), key
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
    assert f"evidence ->> 'evidence_version' = '{EVIDENCE_VERSION}'" in migration


def test_a_wall_clock_time_without_an_offset_is_no_comparison() -> None:
    found = evidence(photo(local_time="2026:10:11 12:00:00"))
    assert found.exif_time_present and not found.exif_time_absolute
    assert found.exif_time_delta_s is None and found.exif_age_at_acceptance_s is None


def test_the_gps_fix_time_is_an_absolute_time() -> None:
    found = evidence(photo(gps_time=("2026:10:11", (11, 59, 30))))
    assert found.exif_time_absolute
    assert (found.exif_time_delta_s, found.exif_age_at_acceptance_s) == (30, 330)
    assert not found.exif_gps_present


def test_an_old_gallery_photo_shows_its_age_at_acceptance() -> None:
    # A year-old photo whose file time became the claimed capture time agrees with the claim, but
    # the acceptance a year later gives it away; the database keeps it at tier 0.
    taken = datetime(2025, 10, 20, 13, 15, tzinfo=UTC)
    found = evidence(photo(local_time="2025:10:20 09:15:00", offset="-04:00"), claimed_at=taken)
    assert found.exif_time_delta_s == 0
    assert found.exif_age_at_acceptance_s == round((ACCEPTED_AT - taken).total_seconds())
    assert found.exif_age_at_acceptance_s > 300 * 24 * 3600


def test_a_photo_taken_after_the_acceptance_has_a_negative_age() -> None:
    found = evidence(photo(local_time="2026:10:11 08:06:00", offset="-04:00"))
    assert found.exif_age_at_acceptance_s == -60


def test_an_embedded_position_far_from_the_claim_is_measured() -> None:
    found = evidence(
        photo(
            local_time="2026:10:11 08:00:00",
            offset="-04:00",
            gps_position=(44.4859, -73.2121),  # about 1.1 km north
        )
    )
    assert found.exif_gps_distance_m is not None and 1000 <= found.exif_gps_distance_m <= 1200


def test_no_metadata_is_no_evidence() -> None:
    assert evidence(photo()) == CaptureEvidence()


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"not-an-image",
        b"\xff\xd8\xff\xe1\x00\x10Exif\x00\x00MM\x00*garbage",
        photo(local_time="2026:13:45 25:61:61", offset="-04:00"),
        photo(local_time="2026:10:11 08:00:00", offset="+99:00"),
        photo(local_time="    :  :     :  :  ", offset="      "),
        # The last moment EXIF can express, plus a leap second, overflows datetime arithmetic.
        photo(gps_time=("9999:12:31", (23, 59, 60))),
    ],
)
def test_hostile_or_malformed_metadata_is_no_evidence_and_never_raises(raw: bytes) -> None:
    found = evidence(raw)
    assert not found.exif_time_absolute
    assert found.exif_time_delta_s is None and found.exif_age_at_acceptance_s is None


def test_a_zero_zero_position_means_no_fix() -> None:
    found = evidence(
        photo(local_time="2026:10:11 08:00:00", offset="-04:00", gps_position=(0.0, 0.0))
    )
    assert not found.exif_gps_present and found.exif_gps_distance_m is None


@pytest.mark.parametrize("moment", [None, datetime(2026, 10, 11, 12, 0, 0)])
def test_a_missing_or_naive_claim_or_acceptance_is_no_comparison(
    moment: datetime | None,
) -> None:
    raw = photo(local_time="2026:10:11 08:00:00", offset="-04:00")
    assert evidence(raw, claimed_at=moment).exif_time_delta_s is None
    assert evidence(raw, accepted_at=moment).exif_age_at_acceptance_s is None


def test_client_claims_are_not_inputs() -> None:
    # Ingest path, capture method, location source and client version are not parameters, so no
    # claim can influence the evidence a tier is derived from.
    parameters = set(inspect.signature(capture_evidence).parameters)
    assert parameters == {"raw", "claimed_at", "accepted_at", "latitude", "longitude"}
