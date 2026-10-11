import type { CaptureMethod, IngestPath, LocationSource } from '../provenance'

/**
 * WP-APP-1 platform layer: what the capture app needs from the device, with one implementation
 * for the phone app (Capacitor plugins) and one for browsers. Everything here is a claim the
 * server records but never trusts to raise a provenance tier (SPEC I10).
 */

/** A photo ready for the queue, before it is given a shot and an object id. */
export type CapturedPhoto = {
  bytes: Uint8Array
  mimeType: 'image/jpeg'
  /** When it was taken (milliseconds since the epoch), when the platform can tell. */
  takenAt?: number
  /** How it reached the app. */
  method: CaptureMethod
}

export type PhotoProblem =
  'failed' | 'no_camera' | 'not_jpeg' | 'permission_denied' | 'too_large'

/** A photo the app cannot queue, and why; the person can retake or choose another. */
export class PhotoRefused extends Error {
  constructor(readonly problem: PhotoProblem) {
    super(`Photo refused: ${problem}`)
    this.name = 'PhotoRefused'
  }
}

export type NativeCamera = {
  readonly kind: 'native'
  /** Opens the device camera. Null when the person cancels. */
  takePhoto(): Promise<CapturedPhoto | null>
  /** Opens the system photo picker, which needs no permission. Null when the person cancels. */
  choosePhoto(): Promise<CapturedPhoto | null>
}

/** Browsers take photos through the form's own file inputs (`capture="environment"`). */
export type WebCamera = { readonly kind: 'web' }

export type CameraProvider = NativeCamera | WebCamera

export type DeviceFix = {
  latitude: number
  longitude: number
  /** Horizontal accuracy in whole metres, or null when the device reported none. */
  accuracyM: number | null
  source: LocationSource
}

export type LocationProblem = 'denied' | 'off' | 'timeout' | 'unavailable'

export type LocationResult =
  { ok: true; fix: DeviceFix } | { ok: false; problem: LocationProblem }

export type LocationProvider = {
  /** One fix, asking for permission (while the app is in use) the first time. */
  locate(): Promise<LocationResult>
}

/**
 * Device attestation, reserved for provenance tier 2 (SPEC I10). No server verifier exists yet,
 * so the only provider is `none` and nothing is ever sent. A Play Integrity or App Attest
 * provider takes its place once the server can verify what it returns.
 */
export type AttestationProvider = {
  readonly name: 'none'
  attest(challenge: string): Promise<null>
}

export type Platform = {
  ingestPath: IngestPath
  camera: CameraProvider
  location: LocationProvider
  attestation: AttestationProvider
}
