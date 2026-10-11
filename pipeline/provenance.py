"""Capture evidence and photo provenance tiers (SPEC I7, I10; WP-6e).

The QA worker derives evidence from an upload's original bytes before sanitizing strips every
metadata channel. The evidence is private and holds no coordinates or timestamps (I7): only
booleans, a time difference and a distance. It is the only input that can raise a field photo
above tier 0. The client's claims (ingest path, capture method, location source) are recorded on
the submission but are never an input here, so a claim can never raise a tier (I10).

Tier 1 ("corroborated") means the file's own capture metadata agreed with the claimed time and
place. Capture metadata can be forged, so tier 1 is corroboration, not proof; tiers 2 (attested
capture) and 3 (lab-verified) are reserved for later work packages.
"""

from __future__ import annotations

import io
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

from PIL import ExifTags, Image

EVIDENCE_VERSION = "exif-v1"
# A camera writes its capture time within seconds of the file timestamp the client reports. Half
# an hour absorbs clock drift but never a mis-set time zone, which is off by an hour or more.
TIME_TOLERANCE_S = 1800
# The QA gate's GPS accuracy ceiling (pipeline.qa.MAX_GPS_ACCURACY_M).
GPS_TOLERANCE_M = 250.0
EARTH_RADIUS_M = 6_371_008.8

TIER_SYNTHETIC = -1
TIER_UNATTESTED = 0
TIER_CORROBORATED = 1

# Must equal the database allowlist (photos_capture_evidence_allowlist); a test checks both.
EVIDENCE_KEYS = frozenset(
    {
        "evidence_version",
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
    """What an original upload says about when and where it was taken, without the values."""

    exif_time_present: bool = False
    exif_time_absolute: bool = False
    exif_time_delta_s: int | None = None
    exif_gps_present: bool = False
    exif_gps_distance_m: int | None = None

    @property
    def tier(self) -> int:
        """1 when the capture time is absolute and agrees with the claim, and any EXIF position
        lies near the claimed point; otherwise 0. Never above 1: higher tiers need attestation
        or a laboratory result."""

        time_agrees = (
            self.exif_time_absolute
            and self.exif_time_delta_s is not None
            and self.exif_time_delta_s <= TIME_TOLERANCE_S
        )
        place_agrees = not self.exif_gps_present or (
            self.exif_gps_distance_m is not None and self.exif_gps_distance_m <= GPS_TOLERANCE_M
        )
        return TIER_CORROBORATED if time_agrees and place_agrees else TIER_UNATTESTED

    def private_json(self) -> dict[str, bool | int | str | None]:
        """The `photos.capture_evidence_private` value: allowlisted keys only."""

        return {
            "evidence_version": EVIDENCE_VERSION,
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
    latitude: float,
    longitude: float,
) -> CaptureEvidence:
    """Compare an original upload's EXIF capture time and position with the claimed ones.

    Total by design: unreadable, hostile or absent metadata is simply no evidence (tier 0) and
    never fails a photo's QA. `claimed_at` must be timezone-aware; a naive or missing claim
    cannot be compared and corroborates nothing.
    """

    try:
        with Image.open(io.BytesIO(raw)) as image:
            exif = image.getexif()
            exif_ifd = dict(exif.get_ifd(ExifTags.IFD.Exif))
            gps_ifd = dict(exif.get_ifd(ExifTags.IFD.GPSInfo))
    except Exception:  # noqa: BLE001 - any metadata failure is "no evidence", never an error
        return CaptureEvidence()

    local_time = _exif_datetime(exif_ifd.get(ExifTags.Base.DateTimeOriginal))
    gps_time = _gps_datetime(gps_ifd)
    absolute = _with_offset(local_time, exif_ifd.get(ExifTags.Base.OffsetTimeOriginal)) or gps_time
    claim = claimed_at if claimed_at is not None and claimed_at.utcoffset() is not None else None
    delta = (
        round(abs((absolute - claim).total_seconds()))
        if absolute is not None and claim is not None
        else None
    )

    position = _gps_position(gps_ifd)
    distance = (
        round(_haversine_m(position[0], position[1], latitude, longitude))
        if position is not None
        else None
    )
    return CaptureEvidence(
        exif_time_present=local_time is not None or gps_time is not None,
        exif_time_absolute=absolute is not None,
        exif_time_delta_s=delta,
        exif_gps_present=position is not None,
        exif_gps_distance_m=distance,
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
