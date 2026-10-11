/**
 * WP-6e: what the capture client states about how an observation was made. These are claims:
 * the server records them but never lets them raise a provenance tier (SPEC I10). Only evidence
 * the server derives itself (the photos' own capture metadata) can do that.
 */
export type IngestPath = 'web' | 'app'
export type CaptureMethod = 'camera' | 'file' | 'unknown'
export type LocationSource = 'device_gps' | 'manual_pin' | 'unknown'

export type ProvenanceClaims = {
  captureMethod: CaptureMethod
  ingestPath: IngestPath
  locationSource: LocationSource
}

const INGEST_PATHS: ReadonlySet<string> = new Set(['web', 'app'])
const CAPTURE_METHODS: ReadonlySet<string> = new Set([
  'camera',
  'file',
  'unknown',
])
const LOCATION_SOURCES: ReadonlySet<string> = new Set([
  'device_gps',
  'manual_pin',
  'unknown',
])
// A file timestamp this far ahead of the device clock is not a capture time.
const FUTURE_TOLERANCE_MS = 5 * 60_000

type CapacitorScope = {
  Capacitor?: { isNativePlatform?: () => boolean }
}

/** 'app' only inside the native phone app (WP-APP-1); every browser, installed or not, is 'web'. */
export function ingestPath(
  scope: CapacitorScope = globalThis as CapacitorScope,
): IngestPath {
  try {
    return scope.Capacitor?.isNativePlatform?.() === true ? 'app' : 'web'
  } catch {
    return 'web'
  }
}

/**
 * How the required photos reached the app. A file created after this page loaded was taken with
 * the camera during this visit; an older one was picked from storage. A missing or implausible
 * timestamp is unknown. The observation's claim is the weakest across its photos.
 */
export function captureMethod(
  files: ReadonlyArray<File | null | undefined>,
  pageLoadedAt: number,
  now: number,
): CaptureMethod {
  if (!files.length) return 'unknown'
  let method: CaptureMethod = 'camera'
  for (const file of files) {
    const modified = file?.lastModified
    if (
      typeof modified !== 'number' ||
      !Number.isFinite(modified) ||
      modified > now + FUTURE_TOLERANCE_MS
    )
      return 'unknown'
    if (modified < pageLoadedAt) method = 'file'
  }
  return method
}

/**
 * The claim columns to send. Records queued by older builds carry no claims and get the server
 * defaults; a value outside the known sets (a corrupted record) is left to the server default
 * rather than letting the database refuse the whole observation.
 */
export function claimColumns(claims: Partial<ProvenanceClaims> | undefined): {
  capture_method?: CaptureMethod
  ingest_path?: IngestPath
  location_source?: LocationSource
} {
  if (!claims) return {}
  return {
    ...(claims.captureMethod && CAPTURE_METHODS.has(claims.captureMethod)
      ? { capture_method: claims.captureMethod }
      : {}),
    ...(claims.ingestPath && INGEST_PATHS.has(claims.ingestPath)
      ? { ingest_path: claims.ingestPath }
      : {}),
    ...(claims.locationSource && LOCATION_SOURCES.has(claims.locationSource)
      ? { location_source: claims.locationSource }
      : {}),
  }
}
