import type { CameraPlugin } from '@capacitor/camera'
import type { GeolocationPlugin } from '@capacitor/geolocation'
import { ingestPath } from '../provenance'
import { fetchBytes, nativeCamera } from './camera'
import { nativeLocation, webLocation } from './location'
import type { AttestationProvider, Platform } from './types'

export * from './types'

type CapacitorScope = {
  Capacitor?: { isNativePlatform?: () => boolean }
  navigator?: { geolocation?: Geolocation }
}

/** No server verifier exists yet, so nothing is attested and nothing is sent (SPEC I10). */
export const noAttestation: AttestationProvider = {
  name: 'none',
  attest: async () => null,
}

/** Whether this page runs inside the native phone app rather than a browser. */
export function isNativeApp(
  scope: CapacitorScope = globalThis as CapacitorScope,
): boolean {
  return ingestPath(scope) === 'app'
}

export type NativePlugins = {
  camera: Pick<CameraPlugin, 'chooseFromGallery' | 'takePhoto'>
  geolocation: Pick<GeolocationPlugin, 'getCurrentPosition'>
}

/** Imported only inside the app, so websites never download the native plugins' code. */
export async function loadNativePlugins(): Promise<NativePlugins> {
  const [{ Camera }, { Geolocation }] = await Promise.all([
    import('@capacitor/camera'),
    import('@capacitor/geolocation'),
  ])
  return { camera: Camera, geolocation: Geolocation }
}

/** Browsers: the form's file inputs and the Geolocation API. */
export function webPlatform(
  scope: CapacitorScope = globalThis as CapacitorScope,
): Platform {
  return {
    ingestPath: 'web',
    camera: { kind: 'web' },
    location: webLocation(() => scope.navigator?.geolocation),
    attestation: noAttestation,
  }
}

/** The phone app: the native camera and location plugins. */
export async function nativePlatform(
  load: () => Promise<NativePlugins> = loadNativePlugins,
  now: () => number = Date.now,
): Promise<Platform> {
  const plugins = await load()
  return {
    ingestPath: 'app',
    camera: nativeCamera(plugins.camera, { readBytes: fetchBytes, now }),
    location: nativeLocation(plugins.geolocation),
    attestation: noAttestation,
  }
}

/** Native implementations inside the phone app, web ones everywhere else. */
export async function selectPlatform(
  scope: CapacitorScope = globalThis as CapacitorScope,
  load: () => Promise<NativePlugins> = loadNativePlugins,
): Promise<Platform> {
  return isNativeApp(scope) ? nativePlatform(load) : webPlatform(scope)
}
