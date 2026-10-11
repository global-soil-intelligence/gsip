import type { MediaResult } from '@capacitor/camera'
import { describe, expect, it, vi } from 'vitest'
import { legalLinks } from '../src/legal'
import {
  isNativeApp,
  type NativeOs,
  type NativePlugins,
  nativeOs,
  noAttestation,
  PhotoRefused,
  selectPlatform,
} from '../src/platform'
import {
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
const OUTPUT =
  'file:///data/user/0/com.globalsoilintelligence.app/cache/PIC.jpg'
const NOW = Date.parse('2026-10-11T12:00:00Z')

function app(os: NativeOs) {
  return {
    Capacitor: { getPlatform: () => os, isNativePlatform: () => true },
  }
}

function media(webPath = 'https://localhost/_capacitor_file_/PIC.jpg') {
  return { type: 0, saved: false, uri: OUTPUT, webPath } as MediaResult
}

function position(accuracy = 4.6, latitude = 44.4759, longitude = -73.2121) {
  return { timestamp: 0, coords: { accuracy, latitude, longitude } } as never
}

function fakePlugins(os: NativeOs): NativePlugins {
  return {
    camera: { takePhoto: vi.fn(async () => media()) },
    files: { deleteFile: vi.fn(async () => undefined) },
    geolocation:
      os === 'ios'
        ? { getCurrentPosition: vi.fn(async () => position()) }
        : undefined,
  }
}

function browserGeolocation(accuracy = 12.2) {
  const getCurrentPosition = vi.fn((success: PositionCallback) =>
    success({
      coords: { accuracy, latitude: 1, longitude: 2 },
    } as GeolocationPosition),
  )
  return { getCurrentPosition } as unknown as Geolocation
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
  it('selects the native camera and Core Location in the iPhone app', async () => {
    const plugins = fakePlugins('ios')
    const load = vi.fn(async () => plugins)
    const platform = await selectPlatform(app('ios'), load)

    expect(load).toHaveBeenCalledWith('ios')
    expect(platform.ingestPath).toBe('app')
    expect(platform.camera.kind).toBe('native')
    expect(platform.attestation.name).toBe('none')
    expect(await platform.location.locate()).toMatchObject({ ok: true })
    expect(plugins.geolocation?.getCurrentPosition).toHaveBeenCalledTimes(1)
  })

  it('uses the web view’s location in the Android app, so no Google location SDK ships', async () => {
    const plugins = fakePlugins('android')
    const load = vi.fn(async () => plugins)
    const geolocation = browserGeolocation()
    const platform = await selectPlatform(
      { ...app('android'), navigator: { geolocation } },
      load,
    )

    expect(load).toHaveBeenCalledWith('android')
    expect(plugins.geolocation).toBeUndefined()
    expect(platform.ingestPath).toBe('app')
    expect(platform.camera.kind).toBe('native')
    expect(await platform.location.locate()).toEqual({
      ok: true,
      fix: { latitude: 1, longitude: 2, accuracyM: 12, source: 'device_gps' },
    })
    expect(geolocation.getCurrentPosition).toHaveBeenCalledTimes(1)
  })

  it('selects the web implementations everywhere else, without loading native code', async () => {
    const load = vi.fn(async () => fakePlugins('android'))
    const geolocation = browserGeolocation()
    for (const scope of [
      {},
      { Capacitor: { isNativePlatform: () => false } },
    ]) {
      const platform = await selectPlatform(
        { ...scope, navigator: { geolocation } },
        load,
      )
      expect(platform.ingestPath).toBe('web')
      expect(platform.camera.kind).toBe('web')
      expect(await platform.location.locate()).toMatchObject({ ok: true })
    }
    expect(load).not.toHaveBeenCalled()
    expect(isNativeApp({})).toBe(false)
    expect(isNativeApp(app('ios'))).toBe(true)
    expect(nativeOs(app('ios'))).toBe('ios')
    expect(nativeOs({})).toBe('android')
  })

  it('attests nothing until a server can verify it', async () => {
    expect(await noAttestation.attest('challenge')).toBeNull()
  })
})

describe('the native camera', () => {
  function camera(
    plugin: NativePlugins['camera'],
    bytes: Uint8Array = JPEG,
    discard = vi.fn(async () => undefined),
  ) {
    return nativeCamera(plugin, {
      readBytes: async () => bytes,
      discard,
      now: () => NOW,
    })
  }

  it('turns a camera photo into a JPEG queue photo taken now, and deletes the plugin’s copy', async () => {
    const plugin = { takePhoto: vi.fn(async () => media()) }
    const readBytes = vi.fn(async () => JPEG)
    const discard = vi.fn(async () => undefined)
    const photo = await nativeCamera(plugin, {
      readBytes,
      discard,
      now: () => NOW,
    }).takePhoto()

    expect(readBytes).toHaveBeenCalledWith(
      'https://localhost/_capacitor_file_/PIC.jpg',
    )
    expect(photo).toEqual({
      bytes: JPEG,
      mimeType: 'image/jpeg',
      takenAt: NOW,
      method: 'camera',
    })
    expect(discard).toHaveBeenCalledWith(OUTPUT)
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
    const plugin = { takePhoto: vi.fn(async () => media()) }
    await camera(plugin).takePhoto()
    expect(plugin.takePhoto).toHaveBeenCalledWith(TAKE_PHOTO_OPTIONS)
    expect(TAKE_PHOTO_OPTIONS).toMatchObject({
      correctOrientation: false,
      editable: 'no',
      saveToGallery: false,
    })
    expect(TAKE_PHOTO_OPTIONS).not.toHaveProperty('targetWidth')
  })

  it('refuses what could not be queued, with a reason, and still deletes the copy', async () => {
    const tooLarge = new Uint8Array(MAX_PHOTO_BYTES + 1)
    tooLarge.set(JPEG)
    const cases: Array<[NativePlugins['camera'], Uint8Array, string]> = [
      [{ takePhoto: vi.fn(async () => media()) }, PNG, 'not_jpeg'],
      [{ takePhoto: vi.fn(async () => media()) }, tooLarge, 'too_large'],
      [
        {
          takePhoto: vi.fn(async () => {
            throw refusal('OS-PLUG-CAMR-0003')
          }),
        },
        JPEG,
        'permission_denied',
      ],
      [
        {
          takePhoto: vi.fn(async () => {
            throw refusal('OS-PLUG-CAMR-0007')
          }),
        },
        JPEG,
        'no_camera',
      ],
      [
        {
          takePhoto: vi.fn(
            async () => ({ type: 0, saved: false, uri: OUTPUT }) as never,
          ),
        },
        JPEG,
        'failed',
      ],
      [
        {
          takePhoto: vi.fn(async () => {
            throw new Error('the bridge broke')
          }),
        },
        JPEG,
        'failed',
      ],
    ]
    for (const [plugin, bytes, expected] of cases) {
      const discard = vi.fn(async () => undefined)
      expect(await problem(camera(plugin, bytes, discard).takePhoto())).toBe(
        expected,
      )
      if (expected === 'not_jpeg' || expected === 'too_large')
        expect(discard).toHaveBeenCalledWith(OUTPUT)
    }
    const unreadable = nativeCamera(
      { takePhoto: vi.fn(async () => media()) },
      {
        readBytes: async () => {
          throw new Error('gone')
        },
        discard: async () => undefined,
        now: () => NOW,
      },
    )
    expect(await problem(unreadable.takePhoto())).toBe('failed')
  })

  it('keeps the photo when deleting the plugin’s copy fails', async () => {
    const photo = await camera(
      { takePhoto: vi.fn(async () => media()) },
      JPEG,
      vi.fn(async () => {
        throw new Error('already gone')
      }),
    ).takePhoto()
    expect(photo?.method).toBe('camera')
  })

  it('treats a cancelled camera as no photo, not an error', async () => {
    const cancelled = camera({
      takePhoto: vi.fn(async () => {
        throw refusal('OS-PLUG-CAMR-0006')
      }),
    })
    expect(await cancelled.takePhoto()).toBeNull()
  })

  it('recognizes JPEG bytes', () => {
    expect(isJpeg(JPEG)).toBe(true)
    expect(isJpeg(PNG)).toBe(false)
    expect(isJpeg(new Uint8Array([0xff, 0xd8]))).toBe(false)
  })
})

describe('photos chosen through a file input', () => {
  it('keep their timestamp and are claimed by their age against the page load', async () => {
    const loaded = NOW
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
    const plugin = { getCurrentPosition: vi.fn(async () => position()) }
    expect(await nativeLocation(plugin).locate()).toEqual({
      ok: true,
      fix: {
        latitude: 44.4759,
        longitude: -73.2121,
        accuracyM: 5,
        source: 'device_gps',
      },
    })
    expect(plugin.getCurrentPosition).toHaveBeenCalledWith({
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
    const problems: Record<string, string> = {
      'OS-PLUG-GLOC-0003': 'denied',
      'OS-PLUG-GLOC-0008': 'denied',
      'OS-PLUG-GLOC-0007': 'off',
      'OS-PLUG-GLOC-0009': 'off',
      'OS-PLUG-GLOC-0017': 'off',
      'OS-PLUG-GLOC-0010': 'timeout',
      'OS-PLUG-GLOC-0002': 'unavailable',
    }
    for (const [code, expected] of Object.entries(problems)) {
      expect(await failing(code), code).toEqual({
        ok: false,
        problem: expected,
      })
    }

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
      getCurrentPosition: vi.fn(async () => position(3, 91, 0)),
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
      const inApp = legalLinks(true)
      expect(inApp.terms).toBe(
        'https://globalsoilintelligence.com/legal/terms/',
      )
      expect(inApp.privacy).toBe('https://example.org/privacy')
      expect(legalLinks(false).terms).toBe('/legal/terms/')
    } finally {
      vi.unstubAllEnvs()
    }
  })
})
