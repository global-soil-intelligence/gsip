const FUTURE_TOLERANCE_MS = 5 * 60_000
const OLDEST_PLAUSIBLE_MS = 366 * 24 * 60 * 60_000

/** Capture is open only in builds made with VITE_CAPTURE_LIVE=true (WP-6b launch gate). */
export function isCaptureLive(): boolean {
  return import.meta.env.VITE_CAPTURE_LIVE === 'true'
}

/**
 * The capture time of shot B as the device recorded it. A camera capture's file timestamp is
 * the moment of capture; a submit-time timestamp would skew the precipitation context for
 * every observation that waited in the offline queue. Implausible timestamps fall back to now.
 */
export function captureTime(file: File | null, now: number): string {
  const modified = file?.lastModified
  if (
    typeof modified === 'number' &&
    Number.isFinite(modified) &&
    modified <= now + FUTURE_TOLERANCE_MS &&
    modified >= now - OLDEST_PLAUSIBLE_MS
  ) {
    return new Date(Math.min(modified, now)).toISOString()
  }
  return new Date(now).toISOString()
}
