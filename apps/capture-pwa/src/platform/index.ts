import type { CameraPlugin } from '@capacitor/camera'
import type { FilesystemPlugin } from '@capacitor/filesystem'
import type { GeolocationPlugin } from '@capacitor/geolocation'
import { ingestPath } from '../provenance'
import { fetchBytes, nativeCamera } from './camera'
import { nativeLocation, webLocation } from './location'
import type { AttestationProvider, Platform } from './types'

export * from './types'

type CapacitorScope = {
  Capacitor?: {
    getPlatform?: () => string
    isNativePlatform?: () => boolean
  }
  navigator?: { geolocation?: Geolocation }
}

export type NativeOs = 'android' | 'ios'

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

/** The phone's system inside the app; anything but iOS is treated as Android. */
export function nativeOs(
  scope: CapacitorScope = globalThis as CapacitorScope,
): NativeOs {
  return scope.Capacitor?.getPlatform?.() === 'ios' ? 'ios' : 'android'
}

export type NativePlugins = {
  camera: Pick<CameraPlugin, 'takePhoto'>
  files: Pick<FilesystemPlugin, 'deleteFile'>
  /** iOS only. Android uses the web view's location API and never loads this plugin. */
  geolocation?: Pick<GeolocationPlugin, 'getCurrentPosition'>
}

/**
 * The native plugins, imported only inside the app (websites never run them), and the
 * geolocation plugin only on iOS, the one platform whose app includes it.
 */
export async function loadNativePlugins(os: NativeOs): Promise<NativePlugins> {
  const [{ Camera }, { Filesystem }, geolocation] = await Promise.all([
    import('@capacitor/camera'),
    import('@capacitor/filesystem'),
    os === 'ios'
      ? import('@capacitor/geolocation').then((module) => module.Geolocation)
      : Promise.resolve(undefined),
  ])
  return { camera: Camera, files: Filesystem, geolocation }
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

/**
 * The phone app: the native camera, and the geolocation plugin on iOS or the web view's location
 * API on Android.
 */
export async function nativePlatform(
  scope: CapacitorScope = globalThis as CapacitorScope,
  load: (os: NativeOs) => Promise<NativePlugins> = loadNativePlugins,
  now: () => number = () => Date.now(),
): Promise<Platform> {
  const plugins = await load(nativeOs(scope))
  return {
    ingestPath: 'app',
    camera: nativeCamera(plugins.camera, {
      readBytes: fetchBytes,
      discard: (uri) => plugins.files.deleteFile({ path: uri }),
      now,
    }),
    location: plugins.geolocation
      ? nativeLocation(plugins.geolocation)
      : webLocation(() => scope.navigator?.geolocation),
    attestation: noAttestation,
  }
}

/** Native implementations inside the phone app, web ones everywhere else. */
export async function selectPlatform(
  scope: CapacitorScope = globalThis as CapacitorScope,
  load: (os: NativeOs) => Promise<NativePlugins> = loadNativePlugins,
): Promise<Platform> {
  return isNativeApp(scope) ? nativePlatform(scope, load) : webPlatform(scope)
}
