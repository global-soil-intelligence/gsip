"""Capture evidence for photo provenance (SPEC I7, I10; WP-6e).

The QA worker derives evidence from an upload's original bytes before sanitizing strips every
metadata channel, and stores it in `photos.capture_evidence_private`. The evidence is private
and holds no coordinates or timestamps (I7): only booleans, whole-second time differences and a
whole-metre distance. The database derives every provenance tier from it
(`private.photo_tier_from_evidence`), so this module measures and never decides a tier.

The client's claims (ingest path, capture method, location source, client version) are recorded
on the submission but are never an input here, so a claim can never raise a tier (I10).
"""

from __future__ import annotations

import io
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

from PIL import ExifTags, Image

# The database derives tiers only from evidence of this version.
EVIDENCE_VERSION = "exif-v1"
EARTH_RADIUS_M = 6_371_008.8

# Must equal the database allowlist (photos_capture_evidence_allowlist); a test checks both.
EVIDENCE_KEYS = frozenset(
    {
        "evidence_version",
        "exif_age_at_acceptance_s",
        "exif_gps_distance_m",
        "exif_gps_present",
        "exif_time_absolute",
        "exif_time_delta_s",
        "exif_time_present",
    }
)

_EXIF_DATETIME = re.compile(r"^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})$")
_EXIF_DATE = re.compile(r"^(\d{4}):(\d{2}):(\d{2})$")
_EXIF_OFFSET = re.compile(r"^([+-])(\d{2}):(\d{2})$")
_MAX_OFFSET = timedelta(hours=14)


@dataclass(frozen=True)
class CaptureEvidence:
    """What an original upload says about when and where it was taken, without the values.

    - `exif_time_absolute`: the EXIF capture time carries its time zone, or is the GPS fix time.
    - `exif_time_delta_s`: how far that time lies from the claimed capture time (absolute value).
    - `exif_age_at_acceptance_s`: how long before the person accepted the terms for the
      observation the photo was taken (negative if after, which only clock skew explains).
    - `exif_gps_distance_m`: how far the embedded position lies from the claimed point.
    """

    exif_time_present: bool = False
    exif_time_absolute: bool = False
    exif_time_delta_s: int | None = None
    exif_age_at_acceptance_s: int | None = None
    exif_gps_present: bool = False
    exif_gps_distance_m: int | None = None

    def private_json(self) -> dict[str, bool | int | str | None]:
        """The `photos.capture_evidence_private` value: allowlisted keys only."""

        return {
            "evidence_version": EVIDENCE_VERSION,
            "exif_age_at_acceptance_s": self.exif_age_at_acceptance_s,
            "exif_gps_distance_m": self.exif_gps_distance_m,
            "exif_gps_present": self.exif_gps_present,
            "exif_time_absolute": self.exif_time_absolute,
            "exif_time_delta_s": self.exif_time_delta_s,
            "exif_time_present": self.exif_time_present,
        }


def capture_evidence(
    raw: bytes,
    *,
    claimed_at: datetime | None,
    accepted_at: datetime | None,
    latitude: float,
    longitude: float,
) -> CaptureEvidence:
    """Compare an original upload's EXIF capture time and position with the observation's claims.

    `claimed_at` is the claimed capture time and `accepted_at` the moment the person accepted the
    terms for the observation (the grant's acceptance time, which the server bounds to the 30 days
    before it received the grant). Both must be timezone-aware; a naive or missing one is no
    comparison. Total by design: unreadable, hostile or absent metadata is simply no evidence and
    never fails a photo's QA.
    """

    try:
        return _capture_evidence(
            raw,
            claimed_at=_aware(claimed_at),
            accepted_at=_aware(accepted_at),
            latitude=latitude,
            longitude=longitude,
        )
    except Exception:  # noqa: BLE001 - hostile metadata is "no evidence", never a QA failure
        return CaptureEvidence()


def _aware(moment: datetime | None) -> datetime | None:
    return moment if moment is not None and moment.utcoffset() is not None else None


def _seconds(later: datetime, earlier: datetime) -> int:
    return round((later - earlier).total_seconds())


def _capture_evidence(
    raw: bytes,
    *,
    claimed_at: datetime | None,
    accepted_at: datetime | None,
    latitude: float,
    longitude: float,
) -> CaptureEvidence:
    with Image.open(io.BytesIO(raw)) as image:
        exif = image.getexif()
        exif_ifd = dict(exif.get_ifd(ExifTags.IFD.Exif))
        gps_ifd = dict(exif.get_ifd(ExifTags.IFD.GPSInfo))

    local_time = _exif_datetime(exif_ifd.get(ExifTags.Base.DateTimeOriginal))
    gps_time = _gps_datetime(gps_ifd)
    absolute = _with_offset(local_time, exif_ifd.get(ExifTags.Base.OffsetTimeOriginal)) or gps_time
    position = _gps_position(gps_ifd)
    return CaptureEvidence(
        exif_time_present=local_time is not None or gps_time is not None,
        exif_time_absolute=absolute is not None,
        exif_time_delta_s=(
            abs(_seconds(absolute, claimed_at))
            if absolute is not None and claimed_at is not None
            else None
        ),
        exif_age_at_acceptance_s=(
            _seconds(accepted_at, absolute)
            if absolute is not None and accepted_at is not None
            else None
        ),
        exif_gps_present=position is not None,
        exif_gps_distance_m=(
            round(_haversine_m(position[0], position[1], latitude, longitude))
            if position is not None
            else None
        ),
    )


def _text(value: object) -> str | None:
    if isinstance(value, bytes):
        try:
            value = value.decode("ascii")
        except UnicodeDecodeError:
            return None
    if not isinstance(value, str):
        return None
    return value.strip().rstrip("\x00").strip()


def _number(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type] # IFDRational, int and float all convert
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return number if math.isfinite(number) else None


def _exif_datetime(value: object) -> datetime | None:
    """An EXIF "YYYY:MM:DD HH:MM:SS" wall-clock time, without its zone."""

    text = _text(value)
    match = _EXIF_DATETIME.match(text) if text else None
    if not match:
        return None
    year, month, day, hour, minute, second = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def _with_offset(local_time: datetime | None, offset: object) -> datetime | None:
    """Anchor a wall-clock time with its EXIF offset ("+HH:MM"); without one it stays local."""

    text = _text(offset)
    match = _EXIF_OFFSET.match(text) if text else None
    if local_time is None or not match:
        return None
    sign, hours, minutes = match.groups()
    if int(minutes) >= 60:
        return None
    delta = timedelta(hours=int(hours), minutes=int(minutes))
    if delta > _MAX_OFFSET:
        return None
    return local_time.replace(tzinfo=timezone(-delta if sign == "-" else delta))


def _gps_datetime(gps: dict[int, object]) -> datetime | None:
    """The GPS fix time, which EXIF records in UTC."""

    date_text = _text(gps.get(ExifTags.GPS.GPSDateStamp))
    stamp = gps.get(ExifTags.GPS.GPSTimeStamp)
    date_match = _EXIF_DATE.match(date_text) if date_text else None
    if not date_match or not isinstance(stamp, tuple) or len(stamp) != 3:
        return None
    hours, minutes, seconds = (_number(part) for part in stamp)
    if (
        hours is None
        or minutes is None
        or seconds is None
        or not (0 <= hours < 24 and 0 <= minutes < 60 and 0 <= seconds < 61)
        or hours != int(hours)
        or minutes != int(minutes)
    ):
        return None
    year, month, day = (int(part) for part in date_match.groups())
    try:
        midnight = datetime(year, month, day, tzinfo=UTC)
    except ValueError:
        return None
    return midnight + timedelta(hours=hours, minutes=minutes, seconds=seconds)


def _degrees(value: object, reference: object, positive: str, negative: str) -> float | None:
    ref = _text(reference)
    if not isinstance(value, tuple) or len(value) != 3 or ref not in {positive, negative}:
        return None
    degrees, minutes, seconds = (_number(part) for part in value)
    if (
        degrees is None
        or minutes is None
        or seconds is None
        or degrees < 0
        or not 0 <= minutes < 60
        or not 0 <= seconds < 60
    ):
        return None
    total = degrees + minutes / 60 + seconds / 3600
    return -total if ref == negative else total


def _gps_position(gps: dict[int, object]) -> tuple[float, float] | None:
    latitude = _degrees(
        gps.get(ExifTags.GPS.GPSLatitude), gps.get(ExifTags.GPS.GPSLatitudeRef), "N", "S"
    )
    longitude = _degrees(
        gps.get(ExifTags.GPS.GPSLongitude), gps.get(ExifTags.GPS.GPSLongitudeRef), "E", "W"
    )
    if latitude is None or longitude is None:
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    if latitude == 0 and longitude == 0:
        return (
            None  # devices without a fix write zeros; that is no position, not the Gulf of Guinea
        )
    return latitude, longitude


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))
