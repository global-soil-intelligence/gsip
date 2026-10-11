import type { GeolocationPlugin } from '@capacitor/geolocation'
import { errorCode } from './camera'
import type { LocationProblem, LocationProvider, LocationResult } from './types'

// A fresh, precise fix; a cached one up to 30 s old is the same place.
const POSITION_OPTIONS = {
  enableHighAccuracy: true,
  maximumAge: 30_000,
  timeout: 15_000,
} as const

/** The device's reported accuracy as whole metres, or null when it reported none usable. */
export function accuracyMetres(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0
    ? Math.round(value)
    : null
}

/** A position as the capture form records it: the point, its accuracy, and that the device found it. */
export function deviceFix(coords: {
  accuracy?: number | null
  latitude: number
  longitude: number
}): LocationResult {
  const { latitude, longitude } = coords
  if (
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude) ||
    Math.abs(latitude) > 90 ||
    Math.abs(longitude) > 180
  ) {
    return { ok: false, problem: 'unavailable' }
  }
  return {
    ok: true,
    fix: {
      latitude,
      longitude,
      accuracyM: accuracyMetres(coords.accuracy),
      source: 'device_gps',
    },
  }
}

/** Browsers: the Geolocation API, read when asked so a page can supply it late. */
export function webLocation(
  geolocation: () => Geolocation | undefined,
): LocationProvider {
  return {
    locate: () =>
      new Promise<LocationResult>((resolve) => {
        const api = geolocation()
        if (!api) {
          resolve({ ok: false, problem: 'unavailable' })
          return
        }
        api.getCurrentPosition(
          (position) => resolve(deviceFix(position.coords)),
          (error) =>
            resolve({
              ok: false,
              problem:
                error.code === 1
                  ? 'denied'
                  : error.code === 3
                    ? 'timeout'
                    : 'unavailable',
            }),
          POSITION_OPTIONS,
        )
      }),
  }
}

// @capacitor/geolocation error codes.
const DENIED = new Set([
  'OS-PLUG-GLOC-0003', // permission denied
  'OS-PLUG-GLOC-0008', // restricted (iOS)
])
const OFF = new Set([
  'OS-PLUG-GLOC-0007', // location services are off
  'OS-PLUG-GLOC-0009', // the person declined turning location on (Android)
  'OS-PLUG-GLOC-0017', // network and location both off (Android)
])
const TIMEOUT = 'OS-PLUG-GLOC-0010'

function nativeProblem(error: unknown): LocationProblem {
  const code = errorCode(error)
  if (code && DENIED.has(code)) return 'denied'
  if (code && OFF.has(code)) return 'off'
  if (code === TIMEOUT) return 'timeout'
  return 'unavailable'
}

/**
 * The iPhone app: @capacitor/geolocation over Core Location, which asks only for location while
 * the app is in use. The Android app uses the web view's own location API instead (see
 * capacitor.config.ts), which asks for the same foreground permissions.
 */
export function nativeLocation(
  plugin: Pick<GeolocationPlugin, 'getCurrentPosition'>,
): LocationProvider {
  return {
    async locate() {
      try {
        const position = await plugin.getCurrentPosition(POSITION_OPTIONS)
        return deviceFix(position.coords)
      } catch (error) {
        return { ok: false, problem: nativeProblem(error) }
      }
    },
  }
}
