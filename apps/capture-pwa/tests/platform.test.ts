import type { MediaResult } from '@capacitor/camera'
import { describe, expect, it, vi } from 'vitest'
import { legalLinks } from '../src/legal'
import {
  isNativeApp,
  type NativePlugins,
  noAttestation,
  PhotoRefused,
  selectPlatform,
} from '../src/platform'
import {
  CHOOSE_PHOTO_OPTIONS,
  isJpeg,
  MAX_PHOTO_BYTES,
  nativeCamera,
  photoFromFile,
  queuedPhoto,
  TAKE_PHOTO_OPTIONS,
} from '../src/platform/camera'
import {
  accuracyMetres,
  nativeLocation,
  webLocation,
} from '../src/platform/location'
import { siteLink } from '../src/platform/links'

const JPEG = new Uint8Array([0xff, 0xd8, 0xff, 0xe1, 0x00, 0x10, 0x45, 0x78])
const PNG = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
const NATIVE = { Capacitor: { isNativePlatform: () => true } }
const BROWSER_WRAPPED = { Capacitor: { isNativePlatform: () => false } }

function media(webPath = 'https://localhost/_capacitor_file_/photo.jpg') {
  return { type: 0, saved: false, webPath } as unknown as MediaResult
}

function fakePlugins(overrides: Partial<NativePlugins> = {}): NativePlugins {
  return {
    camera: {
      takePhoto: vi.fn(async () => media()),
      chooseFromGallery: vi.fn(async () => ({ results: [media()] })),
    },
    geolocation: {
      getCurrentPosition: vi.fn(async () => ({
        timestamp: 0,
        coords: {
          latitude: 44.4759,
          longitude: -73.2121,
          accuracy: 4.6,
          altitude: null,
          altitudeAccuracy: null,
          heading: null,
          magneticHeading: null,
          speed: null,
        },
      })),
    } as unknown as NativePlugins['geolocation'],
    ...overrides,
  }
}

function refusal(code: string) {
  return Object.assign(new Error('plugin error'), { code })
}

async function problem(promise: Promise<unknown>) {
  try {
    await promise
  } catch (error) {
    return error instanceof PhotoRefused ? error.problem : 'other'
  }
  return 'none'
}

describe('the platform layer (WP-APP-1)', () => {
  it('selects the native implementations inside the phone app', async () => {
    const plugins = fakePlugins()
    const load = vi.fn(async () => plugins)
    const platform = await selectPlatform(NATIVE, load)

    expect(load).toHaveBeenCalledTimes(1)
    expect(platform.ingestPath).toBe('app')
    expect(platform.camera.kind).toBe('native')
    expect(platform.attestation.name).toBe('none')
    const located = await platform.location.locate()
    expect(plugins.geolocation.getCurrentPosition).toHaveBeenCalledTimes(1)
    expect(located).toMatchObject({ ok: true })
  })

  it('selects the web implementations everywhere else, without loading native code', async () => {
    const load = vi.fn(async () => fakePlugins())
    const getCurrentPosition = vi.fn((success: PositionCallback) =>
      success({
        coords: { accuracy: 12.2, latitude: 1, longitude: 2 },
      } as GeolocationPosition),
    )
    for (const scope of [{}, BROWSER_WRAPPED]) {
      const platform = await selectPlatform(
        {
          ...scope,
          navigator: { geolocation: { getCurrentPosition } as never },
        },
        load,
      )
      expect(platform.ingestPath).toBe('web')
      expect(platform.camera.kind).toBe('web')
      expect(await platform.location.locate()).toEqual({
        ok: true,
        fix: { latitude: 1, longitude: 2, accuracyM: 12, source: 'device_gps' },
      })
    }
    expect(load).not.toHaveBeenCalled()
    expect(isNativeApp({})).toBe(false)
    expect(isNativeApp(NATIVE)).toBe(true)
  })

  it('attests nothing until a server can verify it', async () => {
    expect(await noAttestation.attest('challenge')).toBeNull()
  })
})

describe('the native camera', () => {
  const now = Date.parse('2026-10-11T12:00:00Z')

  it('turns a camera photo into a JPEG queue photo taken now', async () => {
    const plugins = fakePlugins()
    const readBytes = vi.fn(async () => JPEG)
    const camera = nativeCamera(plugins.camera, { readBytes, now: () => now })
    const photo = await camera.takePhoto()

    expect(readBytes).toHaveBeenCalledWith(
      'https://localhost/_capacitor_file_/photo.jpg',
    )
    expect(photo).toEqual({
      bytes: JPEG,
      mimeType: 'image/jpeg',
      takenAt: now,
      method: 'camera',
    })
    expect(queuedPhoto(photo!, 'B', 'object-1')).toEqual({
      bytes: JPEG,
      mimeType: 'image/jpeg',
      objectId: 'object-1',
      shotType: 'B',
    })
    expect(queuedPhoto(photo!, 'A').objectId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    )
  })

  it('asks the camera for its own JPEG, unedited, unrotated and kept out of the library', async () => {
    const plugins = fakePlugins()
    const camera = nativeCamera(plugins.camera, {
      readBytes: async () => JPEG,
      now: () => now,
    })
    await camera.takePhoto()
    await camera.choosePhoto()
    expect(plugins.camera.takePhoto).toHaveBeenCalledWith(TAKE_PHOTO_OPTIONS)
    expect(TAKE_PHOTO_OPTIONS).toMatchObject({
      correctOrientation: false,
      editable: 'no',
      saveToGallery: false,
    })
    expect(TAKE_PHOTO_OPTIONS).not.toHaveProperty('targetWidth')
    expect(plugins.camera.chooseFromGallery).toHaveBeenCalledWith(
      CHOOSE_PHOTO_OPTIONS,
    )
    expect(CHOOSE_PHOTO_OPTIONS).toMatchObject({
      allowMultipleSelection: false,
      editable: 'no',
    })
  })

  it('marks a saved photo as a file, dated by its creation time', async () => {
    const plugins = fakePlugins({
      camera: {
        takePhoto: vi.fn(),
        chooseFromGallery: vi.fn(async () => ({
          results: [
            {
              ...media(),
              metadata: {
                format: 'jpeg',
                creationDate: '2026-10-01T09:15:00Z',
              },
            } as MediaResult,
          ],
        })),
      },
    })
    const camera = nativeCamera(plugins.camera, {
      readBytes: async () => JPEG,
      now: () => now,
    })
    expect(await camera.choosePhoto()).toMatchObject({
      method: 'file',
      takenAt: Date.parse('2026-10-01T09:15:00Z'),
    })
  })

  it('refuses what could not be queued, with a reason the person can act on', async () => {
    const tooLarge = new Uint8Array(MAX_PHOTO_BYTES + 1)
    tooLarge.set(JPEG)
    const cases: Array<[NativePlugins['camera'], Uint8Array, string]> = [
      [fakePlugins().camera, PNG, 'not_jpeg'],
      [fakePlugins().camera, tooLarge, 'too_large'],
      [
        {
          takePhoto: vi.fn(async () => {
            throw refusal('OS-PLUG-CAMR-0003')
          }),
          chooseFromGallery: vi.fn(),
        },
        JPEG,
        'permission_denied',
      ],
      [
        {
          takePhoto: vi.fn(async () => {
            throw refusal('OS-PLUG-CAMR-0007')
          }),
          chooseFromGallery: vi.fn(),
        },
        JPEG,
        'no_camera',
      ],
      [
        {
          takePhoto: vi.fn(async () => ({ type: 0, saved: false }) as never),
          chooseFromGallery: vi.fn(),
        },
        JPEG,
        'failed',
      ],
      [
        {
          takePhoto: vi.fn(async () => {
            throw new Error('the bridge broke')
          }),
          chooseFromGallery: vi.fn(),
        },
        JPEG,
        'failed',
      ],
    ]
    for (const [plugin, bytes, expected] of cases) {
      const camera = nativeCamera(plugin, {
        readBytes: async () => bytes,
        now: () => now,
      })
      expect(await problem(camera.takePhoto())).toBe(expected)
    }
  })

  it('treats a cancelled camera or picker as no photo, not an error', async () => {
    const camera = nativeCamera(
      {
        takePhoto: vi.fn(async () => {
          throw refusal('OS-PLUG-CAMR-0006')
        }),
        chooseFromGallery: vi.fn(async () => {
          throw refusal('OS-PLUG-CAMR-0020')
        }),
      },
      { readBytes: async () => JPEG, now: () => now },
    )
    expect(await camera.takePhoto()).toBeNull()
    expect(await camera.choosePhoto()).toBeNull()
    const empty = nativeCamera(
      {
        takePhoto: vi.fn(),
        chooseFromGallery: vi.fn(async () => ({ results: [] })),
      },
      { readBytes: async () => JPEG, now: () => now },
    )
    expect(await empty.choosePhoto()).toBeNull()
  })

  it('recognizes JPEG bytes', () => {
    expect(isJpeg(JPEG)).toBe(true)
    expect(isJpeg(PNG)).toBe(false)
    expect(isJpeg(new Uint8Array([0xff, 0xd8]))).toBe(false)
  })
})

describe('browser photos', () => {
  it('keep their timestamp and are claimed by their age against the page load', async () => {
    const loaded = Date.parse('2026-10-11T12:00:00Z')
    const fresh = new File([JPEG], 'a.jpg', {
      type: 'image/jpeg',
      lastModified: loaded + 60_000,
    })
    const old = new File([JPEG], 'b.jpg', {
      type: 'image/jpeg',
      lastModified: loaded - 86_400_000,
    })
    expect(await photoFromFile(fresh, loaded, loaded + 120_000)).toMatchObject({
      method: 'camera',
      mimeType: 'image/jpeg',
      takenAt: loaded + 60_000,
    })
    expect((await photoFromFile(old, loaded, loaded + 120_000)).method).toBe(
      'file',
    )
    expect(
      await problem(
        photoFromFile(
          new File([PNG], 'c.png', { type: 'image/png' }),
          loaded,
          loaded,
        ),
      ),
    ).toBe('not_jpeg')
    const huge = new File([new Uint8Array(MAX_PHOTO_BYTES + 1)], 'd.jpg', {
      type: 'image/jpeg',
    })
    expect(await problem(photoFromFile(huge, loaded, loaded))).toBe('too_large')
  })
})

describe('location', () => {
  it('maps the device fix to the point, whole-metre accuracy and the device source', async () => {
    const plugins = fakePlugins()
    expect(await nativeLocation(plugins.geolocation).locate()).toEqual({
      ok: true,
      fix: {
        latitude: 44.4759,
        longitude: -73.2121,
        accuracyM: 5,
        source: 'device_gps',
      },
    })
    expect(plugins.geolocation.getCurrentPosition).toHaveBeenCalledWith({
      enableHighAccuracy: true,
      maximumAge: 30_000,
      timeout: 15_000,
    })
    expect(accuracyMetres(4.4)).toBe(4)
    for (const unusable of [Number.NaN, -1, Number.POSITIVE_INFINITY, null]) {
      expect(accuracyMetres(unusable)).toBeNull()
    }
  })

  it('explains why there is no fix', async () => {
    const failing = (code: string) =>
      nativeLocation({
        getCurrentPosition: vi.fn(async () => {
          throw refusal(code)
        }),
      }).locate()
    expect(await failing('OS-PLUG-GLOC-0003')).toEqual({
      ok: false,
      problem: 'denied',
    })
    expect(await failing('OS-PLUG-GLOC-0007')).toEqual({
      ok: false,
      problem: 'off',
    })
    expect(await failing('OS-PLUG-GLOC-0010')).toEqual({
      ok: false,
      problem: 'timeout',
    })
    expect(await failing('OS-PLUG-GLOC-0002')).toEqual({
      ok: false,
      problem: 'unavailable',
    })

    const web = (code: number) =>
      webLocation(
        () =>
          ({
            getCurrentPosition: (
              _success: PositionCallback,
              failure: PositionErrorCallback,
            ) => failure({ code } as GeolocationPositionError),
          }) as unknown as Geolocation,
      ).locate()
    expect(await web(1)).toEqual({ ok: false, problem: 'denied' })
    expect(await web(2)).toEqual({ ok: false, problem: 'unavailable' })
    expect(await web(3)).toEqual({ ok: false, problem: 'timeout' })
    expect(await webLocation(() => undefined).locate()).toEqual({
      ok: false,
      problem: 'unavailable',
    })
  })

  it('never records an impossible point', async () => {
    const impossible = nativeLocation({
      getCurrentPosition: vi.fn(async () => ({
        timestamp: 0,
        coords: { latitude: 91, longitude: 0, accuracy: 3 },
      })) as never,
    })
    expect(await impossible.locate()).toEqual({
      ok: false,
      problem: 'unavailable',
    })
  })
})

describe('links from the phone app', () => {
  it('point at the public site, since the app is not on it', () => {
    expect(siteLink('../map/', true)).toBe(
      'https://globalsoilintelligence.com/map/',
    )
    expect(
      siteLink('../reference-card/gsip-reference-card-v1-color.pdf', true),
    ).toBe(
      'https://globalsoilintelligence.com/reference-card/gsip-reference-card-v1-color.pdf',
    )
    expect(siteLink('../map/', false)).toBe('../map/')
  })

  it('resolve same-site legal documents against the site, and keep absolute ones', () => {
    vi.stubEnv('VITE_TERMS_URL', '/legal/terms/')
    vi.stubEnv('VITE_PRIVACY_URL', 'https://example.org/privacy')
    try {
      const app = legalLinks(true)
      expect(app.terms).toBe('https://globalsoilintelligence.com/legal/terms/')
      expect(app.privacy).toBe('https://example.org/privacy')
      expect(legalLinks(false).terms).toBe('/legal/terms/')
    } finally {
      vi.unstubAllEnvs()
    }
  })
})
