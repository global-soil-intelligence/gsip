import { describe, expect, it, vi } from 'vitest'
import {
  BrowserCamera,
  browserCameraSupported,
  CAMERA_CONSTRAINTS,
  CAMERA_ENCODE_WAIT_MS,
  CAMERA_JPEG_QUALITY,
  CAMERA_PERMISSION_WAIT_MS,
  CAMERA_PLAYBACK_WAIT_MS,
  CAMERA_PREVIEW_MS,
  containRect,
  jpegDimensions,
  type CameraCanvas,
  type CameraPorts,
  type CameraVideo,
} from '../src/platform/browserCamera'
import { MAX_PHOTO_BYTES } from '../src/platform/camera'
import design from '../../../docs/browser-camera-design.json'
import source from '../src/platform/browserCamera.ts?raw'

/** The smallest byte string with a JPEG start and one baseline frame header of this size. */
function jpeg(
  width: number,
  height: number,
  extra = 0,
): Uint8Array<ArrayBuffer> {
  const head = [0xff, 0xd8, 0xff, 0xe0, 0x00, 0x04, 0x4a, 0x46]
  const frame = [
    0xff,
    0xc0,
    0x00,
    0x0b,
    0x08,
    height >> 8,
    height & 0xff,
    width >> 8,
    width & 0xff,
    0x01,
    0x01,
    0x11,
    0x00,
  ]
  const bytes = new Uint8Array(head.length + frame.length + extra + 2)
  bytes.set(head)
  bytes.set(frame, head.length)
  bytes.set([0xff, 0xd9], bytes.length - 2)
  return bytes
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

const tick = () => new Promise<void>((resolve) => setTimeout(resolve, 0))

/** An event target that counts the listeners still attached. */
class Counted extends EventTarget {
  listeners = 0
  override addEventListener(
    ...args: Parameters<EventTarget['addEventListener']>
  ) {
    this.listeners += 1
    super.addEventListener(...args)
  }
  override removeEventListener(
    ...args: Parameters<EventTarget['removeEventListener']>
  ) {
    this.listeners -= 1
    super.removeEventListener(...args)
  }
}

class FakeTrack extends Counted {
  kind = 'video'
  readyState: 'live' | 'ended' = 'live'
  muted = false
  stops = 0
  stop() {
    this.stops += 1
    this.readyState = 'ended'
  }
}

function fakeStream(tracks: FakeTrack[] = [new FakeTrack()]) {
  return {
    tracks,
    stream: { getTracks: () => tracks } as unknown as MediaStream,
  }
}

class FakeVideo extends Counted {
  muted = false
  playsInline = false
  readyState = 0
  videoWidth = 0
  videoHeight = 0
  srcObject: unknown = null
  paused = 0
  playResult: Promise<void> = Promise.resolve()
  play() {
    return this.playResult
  }
  pause() {
    this.paused += 1
  }
  frame(width: number, height: number) {
    this.readyState = 4
    this.videoWidth = width
    this.videoHeight = height
    this.dispatchEvent(new Event('loadeddata'))
  }
}

type Harness = ReturnType<typeof harness>

function harness() {
  const timers = new Map<number, { run: () => void; ms: number }>()
  let nextTimer = 1
  const requests: Array<ReturnType<typeof deferred<MediaStream>>> = []
  const constraints: MediaStreamConstraints[] = []
  const draws: unknown[][] = []
  const blobCalls: Array<{
    type: string | undefined
    quality: unknown
    done: (blob: Blob | null) => void
  }> = []
  const canvases: Array<{ width: number; height: number }> = []
  let context: object | null = {
    drawImage: (...args: unknown[]) => draws.push(args),
  }
  let decode = (blob: Blob): Promise<{ width: number; height: number }> =>
    blob.arrayBuffer().then((buffer) => jpegDimensions(new Uint8Array(buffer))!)
  const ports: CameraPorts = {
    getUserMedia(value) {
      constraints.push(value)
      const request = deferred<MediaStream>()
      requests.push(request)
      return request.promise
    },
    createCanvas() {
      const canvas = {
        width: 0,
        height: 0,
        getContext: () => context,
        toBlob: (
          done: (blob: Blob | null) => void,
          type?: string,
          quality?: unknown,
        ) => blobCalls.push({ type, quality, done }),
      }
      canvases.push(canvas)
      return canvas as unknown as CameraCanvas
    },
    decode: (blob) => decode(blob),
    now: () => 1_700_000_000_000,
    setTimeout(run, ms) {
      timers.set(nextTimer, { run, ms })
      return nextTimer++
    },
    clearTimeout(handle) {
      timers.delete(handle as number)
    },
  }
  return {
    ports,
    camera: new BrowserCamera(ports),
    video: new FakeVideo(),
    requests,
    constraints,
    draws,
    blobCalls,
    canvases,
    timers,
    fire(ms: number) {
      const found = [...timers].find(([, timer]) => timer.ms === ms)
      if (!found) throw new Error(`no ${ms} ms timer`)
      timers.delete(found[0])
      found[1].run()
    },
    setContext(value: object | null) {
      context = value
    },
    setDecode(value: typeof decode) {
      decode = value
    },
  }
}

async function preview(h: Harness, width = 1280, height = 960) {
  const started = h.camera.start(h.video as unknown as CameraVideo)
  const media = fakeStream()
  h.requests.at(-1)!.resolve(media.stream)
  await tick()
  h.video.frame(width, height)
  const result = await started
  return { result, ...media }
}

describe('design limits', () => {
  it('uses the limits the reviewed design records', () => {
    expect(CAMERA_JPEG_QUALITY).toBe(design.limits.jpeg_quality)
    expect(CAMERA_PERMISSION_WAIT_MS).toBe(design.limits.permission_wait_ms)
    expect(CAMERA_PLAYBACK_WAIT_MS).toBe(design.limits.playback_wait_ms)
    expect(CAMERA_PREVIEW_MS).toBe(design.limits.preview_ms)
    expect(CAMERA_ENCODE_WAIT_MS).toBe(design.limits.encode_wait_ms)
    expect(MAX_PHOTO_BYTES).toBe(design.limits.max_photo_bytes)
  })

  it('asks for video only, rear camera preferred, no named device', () => {
    expect(CAMERA_CONSTRAINTS.audio).toBe(false)
    expect(CAMERA_CONSTRAINTS.video).toEqual({
      facingMode: { ideal: 'environment' },
      width: { ideal: 1920, max: design.limits.max_frame_edge },
      height: { ideal: 1440, max: design.limits.max_frame_edge },
    })
    expect(JSON.stringify(CAMERA_CONSTRAINTS)).not.toMatch(/deviceId|groupId/)
  })
})

describe('what the controller may touch', () => {
  it('names no device, records nothing and imports no account, storage or network code', () => {
    expect(source).not.toMatch(
      /enumerateDevices|deviceId|groupId|\.label|getSettings|getCapabilities|console\.|MediaRecorder|RTCPeer|fetch\(|indexedDB|localStorage|supabase/,
    )
    const imports = [...source.matchAll(/from '([^']+)'/g)].map(
      (match) => match[1],
    )
    expect(imports.sort()).toEqual(['../guideSession', './camera', './types'])
  })
})

describe('browserCameraSupported', () => {
  const self = {}
  const full = {
    isSecureContext: true,
    top: self,
    self,
    navigator: { mediaDevices: { getUserMedia() {} } },
    HTMLCanvasElement: { prototype: { toBlob() {}, getContext() {} } },
    HTMLDialogElement: { prototype: { showModal() {} } },
    createImageBitmap() {},
  }

  it('accepts a top-level secure page with every method', () => {
    expect(browserCameraSupported(full)).toBe(true)
  })

  it.each([
    ['an insecure page', { isSecureContext: false }],
    ['a framed page', { top: {} }],
    ['no media devices', { navigator: {} }],
    [
      'no canvas export',
      { HTMLCanvasElement: { prototype: { getContext() {} } } },
    ],
    ['no modal dialog', { HTMLDialogElement: { prototype: {} } }],
    ['no image decoder', { createImageBitmap: undefined }],
  ])('refuses %s', (_name, change) => {
    expect(browserCameraSupported({ ...full, ...change })).toBe(false)
  })

  it('calls no media method while deciding', () => {
    let calls = 0
    browserCameraSupported({
      ...full,
      navigator: { mediaDevices: { getUserMedia: () => (calls += 1) } },
    })
    expect(calls).toBe(0)
  })
})

describe('containRect', () => {
  it('centres a wide frame in a tall box and a tall frame in a wide box', () => {
    expect(
      containRect({ width: 400, height: 800 }, { width: 1600, height: 1200 }),
    ).toEqual({
      left: 0,
      top: 250,
      width: 400,
      height: 300,
    })
    expect(
      containRect({ width: 800, height: 400 }, { width: 1200, height: 1600 }),
    ).toEqual({
      left: 250,
      top: 0,
      width: 300,
      height: 400,
    })
  })

  it('has no rectangle for an empty box or frame', () => {
    expect(
      containRect({ width: 0, height: 10 }, { width: 4, height: 3 }),
    ).toBeNull()
    expect(
      containRect({ width: 10, height: 10 }, { width: 0, height: 0 }),
    ).toBeNull()
  })
})

describe('jpegDimensions', () => {
  it('reads the frame header and refuses bytes without one', () => {
    expect(jpegDimensions(jpeg(1280, 960))).toEqual({
      width: 1280,
      height: 960,
    })
    expect(jpegDimensions(new Uint8Array([0x89, 0x50, 0x4e, 0x47]))).toBeNull()
    expect(jpegDimensions(new Uint8Array([0xff, 0xd8, 0xff, 0xd9]))).toBeNull()
    expect(jpegDimensions(jpeg(1280, 960).slice(0, 14))).toBeNull()
  })

  const soi = [0xff, 0xd8]
  const sof = (marker: number) => [
    0xff,
    marker,
    0x00,
    0x0b,
    0x08,
    0x02,
    0xd0,
    0x05,
    0x00,
    0x01,
    0x01,
    0x11,
    0x00,
  ]
  const dht = [0xff, 0xc4, 0x00, 0x04, 0x00, 0x00]

  it.each([
    [
      'fill bytes before a marker',
      [...soi, 0xff, 0xff, 0xff, ...sof(0xc0).slice(1)],
    ],
    ['restart and TEM markers', [...soi, 0xff, 0xd0, 0xff, 0x01, ...sof(0xc0)]],
    ['a progressive frame', [...soi, ...sof(0xc2)]],
    ['a Huffman table before the frame', [...soi, ...dht, ...sof(0xc0)]],
  ])('reads the size past %s', (_name, bytes) => {
    expect(jpegDimensions(new Uint8Array(bytes))).toEqual({
      width: 1280,
      height: 720,
    })
  })

  it.each([
    [
      'a segment shorter than its own length field',
      [...soi, 0xff, 0xe0, 0x00, 0x01, ...sof(0xc0)],
    ],
    ['a Huffman table alone', [...soi, ...dht]],
    [
      'scan data before any frame',
      [...soi, 0xff, 0xda, 0x00, 0x02, ...sof(0xc0)],
    ],
    [
      'a zero-sized frame',
      [...soi, 0xff, 0xc0, 0x00, 0x0b, 0x08, 0, 0, 0, 0, 1, 1, 0x11, 0],
    ],
  ])('has no size for %s', (_name, bytes) => {
    expect(jpegDimensions(new Uint8Array(bytes))).toBeNull()
  })
})

describe('start', () => {
  it('makes no media call until start, then exactly one', async () => {
    const h = harness()
    expect(h.requests).toHaveLength(0)
    const { result, tracks } = await preview(h)
    expect(result).toEqual({ ok: true, frame: { width: 1280, height: 960 } })
    expect(h.requests).toHaveLength(1)
    expect(h.constraints[0]).toBe(CAMERA_CONSTRAINTS)
    expect(h.video.muted).toBe(true)
    expect(h.video.playsInline).toBe(true)
    expect(tracks[0]!.stops).toBe(0)
    expect(h.camera.state()).toEqual({
      pendingRequest: false,
      pendingEncoder: false,
      liveTracks: 1,
      previewing: true,
    })
  })

  it('refuses a second start while one is unresolved or live', async () => {
    const h = harness()
    const first = h.camera.start(h.video as unknown as CameraVideo)
    expect(await h.camera.start(h.video as unknown as CameraVideo)).toEqual({
      ok: false,
      problem: 'busy',
    })
    expect(h.requests).toHaveLength(1)
    h.requests[0]!.resolve(fakeStream().stream)
    await tick()
    h.video.frame(1280, 960)
    await first
    expect(await h.camera.start(h.video as unknown as CameraVideo)).toEqual({
      ok: false,
      problem: 'busy',
    })
    expect(h.requests).toHaveLength(1)
  })

  it.each([
    ['NotAllowedError', 'denied'],
    ['SecurityError', 'denied'],
    ['NotFoundError', 'unavailable'],
    ['OverconstrainedError', 'unavailable'],
    ['NotReadableError', 'unavailable'],
    ['TypeError', 'failed'],
  ])('reports %s as %s and frees the slot', async (name, problem) => {
    const h = harness()
    const started = h.camera.start(h.video as unknown as CameraVideo)
    h.requests[0]!.reject(Object.assign(new Error('private detail'), { name }))
    expect(await started).toEqual({ ok: false, problem })
    expect(h.camera.state().pendingRequest).toBe(false)
  })

  it('keeps the slot after an ignored prompt and stops the stream that arrives late', async () => {
    const h = harness()
    const started = h.camera.start(h.video as unknown as CameraVideo)
    h.fire(CAMERA_PERMISSION_WAIT_MS)
    expect(await started).toEqual({ ok: false, problem: 'timeout' })
    expect(h.camera.state().pendingRequest).toBe(true)
    expect(await h.camera.start(h.video as unknown as CameraVideo)).toEqual({
      ok: false,
      problem: 'busy',
    })
    expect(h.requests).toHaveLength(1)
    const late = fakeStream()
    h.requests[0]!.resolve(late.stream)
    await tick()
    expect(late.tracks[0]!.stops).toBe(1)
    expect(h.video.srcObject).toBeNull()
    expect(h.camera.state()).toMatchObject({
      pendingRequest: false,
      liveTracks: 0,
    })
  })

  it('stops only its own late stream after cancel, never the replacement', async () => {
    const h = harness()
    const first = h.camera.start(h.video as unknown as CameraVideo)
    h.camera.stop()
    expect(await first).toEqual({ ok: false, problem: 'cancelled' })
    const late = fakeStream()
    h.requests[0]!.resolve(late.stream)
    await tick()
    expect(late.tracks[0]!.stops).toBe(1)
    const second = await preview(h)
    expect(second.result.ok).toBe(true)
    expect(second.tracks[0]!.stops).toBe(0)
    expect(late.tracks[0]!.stops).toBe(1)
  })

  it.each([
    [
      'an audio track',
      () => [Object.assign(new FakeTrack(), { kind: 'audio' })],
    ],
    ['two tracks', () => [new FakeTrack(), new FakeTrack()]],
    ['no track', () => []],
    [
      'an ended track',
      () => [Object.assign(new FakeTrack(), { readyState: 'ended' })],
    ],
  ])(
    'refuses a stream with %s and stops everything in it',
    async (_name, make) => {
      const h = harness()
      const started = h.camera.start(h.video as unknown as CameraVideo)
      const media = fakeStream(make() as FakeTrack[])
      h.requests[0]!.resolve(media.stream)
      expect(await started).toEqual({ ok: false, problem: 'failed' })
      expect(h.video.srcObject).toBeNull()
      for (const track of media.tracks) expect(track.readyState).toBe('ended')
      expect(h.camera.state().liveTracks).toBe(0)
    },
  )

  it('stops the camera when playback is refused', async () => {
    const h = harness()
    h.video.playResult = Promise.reject(new Error('blocked'))
    const started = h.camera.start(h.video as unknown as CameraVideo)
    const media = fakeStream()
    h.requests[0]!.resolve(media.stream)
    expect(await started).toEqual({ ok: false, problem: 'playback' })
    expect(media.tracks[0]!.stops).toBe(1)
    expect(h.video.srcObject).toBeNull()
  })

  it('stops the camera when no frame arrives in time', async () => {
    const h = harness()
    const started = h.camera.start(h.video as unknown as CameraVideo)
    const media = fakeStream()
    h.requests[0]!.resolve(media.stream)
    await tick()
    h.fire(CAMERA_PLAYBACK_WAIT_MS)
    expect(await started).toEqual({ ok: false, problem: 'timeout' })
    expect(media.tracks[0]!.stops).toBe(1)
    expect(media.tracks[0]!.listeners).toBe(0)
    expect(h.video.listeners).toBe(0)
    expect(h.timers.size).toBe(0)
  })

  it('stops a stream when stop lands just as it arrives', async () => {
    const h = harness()
    const started = h.camera.start(h.video as unknown as CameraVideo)
    const media = fakeStream()
    // Registered after the controller's own handler, so it runs in the gap before start resumes.
    void h.requests[0]!.promise.then(() => h.camera.stop())
    h.requests[0]!.resolve(media.stream)
    expect(await started).toEqual({ ok: false, problem: 'cancelled' })
    expect(media.tracks[0]!.stops).toBe(1)
    expect(h.video.srcObject).toBeNull()
    expect(h.camera.state()).toMatchObject({
      liveTracks: 0,
      pendingRequest: false,
    })
    expect((await preview(h)).result.ok).toBe(true)
  })

  it.each([
    [
      'an ignored prompt',
      (h: Harness) => h.fire(CAMERA_PERMISSION_WAIT_MS),
      'timeout',
    ],
    ['cancel', (h: Harness) => h.camera.stop(), 'cancelled'],
  ])(
    'ignores a refusal that arrives after %s and frees the slot',
    async (_n, end, problem) => {
      const h = harness()
      let settled = 0
      const started = h.camera.start(h.video as unknown as CameraVideo, {
        requestSettled: () => (settled += 1),
      })
      end(h)
      expect(await started).toEqual({ ok: false, problem })
      expect(settled).toBe(0)
      expect(h.camera.state().pendingRequest).toBe(true)
      h.requests[0]!.reject(
        Object.assign(new Error('x'), { name: 'NotAllowedError' }),
      )
      await tick()
      expect(settled).toBe(1)
      expect(h.camera.state().pendingRequest).toBe(false)
      expect(h.timers.size).toBe(0)
    },
  )

  it('frees the slot when the browser throws instead of asking', async () => {
    const h = harness()
    h.ports.getUserMedia = () => {
      throw Object.assign(new Error('x'), { name: 'NotFoundError' })
    }
    let settled = 0
    expect(
      await h.camera.start(h.video as unknown as CameraVideo, {
        requestSettled: () => (settled += 1),
      }),
    ).toEqual({ ok: false, problem: 'unavailable' })
    expect(settled).toBe(1)
    expect(h.camera.state().pendingRequest).toBe(false)
  })

  it('does not report a slot settling for a start that never took it', async () => {
    const h = harness()
    await preview(h)
    let settled = 0
    expect(
      await h.camera.start(h.video as unknown as CameraVideo, {
        requestSettled: () => (settled += 1),
      }),
    ).toEqual({ ok: false, problem: 'busy' })
    expect(settled).toBe(0)
  })

  it.each([
    [
      'refused',
      (h: Harness) =>
        h.requests[0]!.reject(
          Object.assign(new Error('x'), { name: 'NotAllowedError' }),
        ),
      'denied',
    ],
    [
      'granted',
      (h: Harness) => h.requests[0]!.resolve(fakeStream([]).stream),
      'failed',
    ],
  ])(
    "finishes a %s start even when the caller's hook throws",
    async (_n, end, problem) => {
      const h = harness()
      const started = h.camera.start(h.video as unknown as CameraVideo, {
        requestSettled: () => {
          throw new Error('caller bug')
        },
      })
      end(h)
      expect(await started).toEqual({ ok: false, problem })
      expect(h.camera.state().pendingRequest).toBe(false)
    },
  )

  it('keeps a second start cancellable when a hook starts it', async () => {
    const h = harness()
    let second: Promise<unknown> | null = null
    const first = h.camera.start(h.video as unknown as CameraVideo, {
      requestSettled: () => {
        second = h.camera.start(h.video as unknown as CameraVideo)
      },
    })
    h.requests[0]!.reject(
      Object.assign(new Error('x'), { name: 'NotAllowedError' }),
    )
    expect(await first).toEqual({ ok: false, problem: 'denied' })
    expect(h.requests).toHaveLength(2)
    h.camera.stop()
    expect(await second).toEqual({ ok: false, problem: 'cancelled' })
  })

  it('refuses a stream whose track starts muted', async () => {
    const h = harness()
    const started = h.camera.start(h.video as unknown as CameraVideo)
    const media = fakeStream([Object.assign(new FakeTrack(), { muted: true })])
    h.requests[0]!.resolve(media.stream)
    expect(await started).toEqual({ ok: false, problem: 'failed' })
    expect(media.tracks[0]!.stops).toBe(1)
    expect(media.tracks[0]!.listeners).toBe(0)
  })

  it('stops cleanly when cancelled while waiting for the first frame', async () => {
    const h = harness()
    const lost: string[] = []
    h.camera.onLost((value) => lost.push(value))
    const started = h.camera.start(h.video as unknown as CameraVideo)
    const media = fakeStream()
    h.requests[0]!.resolve(media.stream)
    await tick()
    h.camera.stop()
    expect(await started).toEqual({ ok: false, problem: 'cancelled' })
    expect(media.tracks[0]!.stops).toBe(1)
    expect(media.tracks[0]!.listeners).toBe(0)
    expect(h.video.listeners).toBe(0)
    expect(h.timers.size).toBe(0)
    expect(lost).toEqual([])
  })

  it.each(['ended', 'mute'])(
    'reports a track that fires %s before the preview once, as a failed start',
    async (event) => {
      const h = harness()
      const lost: string[] = []
      h.camera.onLost((value) => lost.push(value))
      const started = h.camera.start(h.video as unknown as CameraVideo)
      const media = fakeStream()
      h.requests[0]!.resolve(media.stream)
      await tick()
      media.tracks[0]!.dispatchEvent(new Event(event))
      expect(await started).toEqual({ ok: false, problem: 'failed' })
      expect(lost).toEqual([])
      expect(media.tracks[0]!.stops).toBe(1)
      expect(h.video.listeners).toBe(0)
    },
  )

  it('lets the caller refuse the stream before it is attached', async () => {
    const h = harness()
    const order: string[] = []
    const started = h.camera.start(h.video as unknown as CameraVideo, {
      granted: () => {
        order.push(`granted attached=${h.video.srcObject !== null}`)
        return false
      },
      requestSettled: () => order.push('settled'),
    })
    const media = fakeStream()
    h.requests[0]!.resolve(media.stream)
    expect(await started).toEqual({ ok: false, problem: 'refused' })
    expect(order).toEqual(['settled', 'granted attached=false'])
    expect(media.tracks[0]!.stops).toBe(1)
    expect(h.video.srcObject).toBeNull()
    expect(media.tracks[0]!.listeners).toBe(0)
  })

  it('reports the request settled exactly once on a normal start', async () => {
    const h = harness()
    let settled = 0
    let granted = 0
    const started = h.camera.start(h.video as unknown as CameraVideo, {
      granted: () => (granted += 1) > 0,
      requestSettled: () => (settled += 1),
    })
    h.requests[0]!.resolve(fakeStream().stream)
    await tick()
    h.video.frame(1280, 960)
    expect((await started).ok).toBe(true)
    expect([settled, granted]).toEqual([1, 1])
  })

  it.each([
    [1279, 720],
    [1280, 719],
    [2049, 1152],
    [2048, 2049],
  ])('returns to the picker for a %i by %i feed', async (width, height) => {
    const h = harness()
    const { result, tracks } = await preview(h, width, height)
    expect(result).toEqual({ ok: false, problem: 'dimensions' })
    expect(tracks[0]!.stops).toBe(1)
  })

  it.each([
    [1280, 720],
    [720, 1280],
    [2048, 2048],
  ])('accepts a %i by %i feed at the limits', async (width, height) => {
    const h = harness()
    const { result } = await preview(h, width, height)
    expect(width * height).toBeLessThanOrEqual(design.limits.max_frame_pixels)
    expect(result.ok).toBe(true)
  })
})

describe('preview lifetime', () => {
  it.each([
    ['ended', 'ended'],
    ['mute', 'muted'],
  ])('stops and reports when the track fires %s', async (event, reason) => {
    const h = harness()
    const lost: string[] = []
    h.camera.onLost((value) => lost.push(value))
    const { tracks } = await preview(h)
    tracks[0]!.dispatchEvent(new Event(event))
    expect(lost).toEqual([reason])
    expect(tracks[0]!.stops).toBe(1)
    expect(h.video.srcObject).toBeNull()
    expect(h.video.paused).toBe(1)
    expect(h.camera.state()).toMatchObject({ liveTracks: 0, previewing: false })
    tracks[0]!.dispatchEvent(new Event(event))
    expect(lost).toHaveLength(1)
  })

  it('stops a preview left open for a minute', async () => {
    const h = harness()
    const lost: string[] = []
    h.camera.onLost((value) => lost.push(value))
    const { tracks } = await preview(h)
    h.fire(CAMERA_PREVIEW_MS)
    expect(lost).toEqual(['preview_timeout'])
    expect(tracks[0]!.stops).toBe(1)
  })

  it('reports a new frame size and stops when it leaves the limits', async () => {
    const h = harness()
    const sizes: unknown[] = []
    const lost: string[] = []
    h.camera.onGeometry((frame) => sizes.push(frame))
    h.camera.onLost((value) => lost.push(value))
    const { tracks } = await preview(h)
    h.video.videoWidth = 960
    h.video.videoHeight = 1280
    h.video.dispatchEvent(new Event('resize'))
    expect(sizes).toEqual([{ width: 960, height: 1280 }])
    h.video.videoWidth = 640
    h.video.videoHeight = 480
    h.video.dispatchEvent(new Event('resize'))
    expect(lost).toEqual(['dimensions'])
    expect(tracks[0]!.stops).toBe(1)
  })

  it('stop cleans up by itself and leaves no timer or listener behind', async () => {
    const h = harness()
    const lost: string[] = []
    h.camera.onLost((value) => lost.push(value))
    const { tracks } = await preview(h)
    h.camera.stop()
    expect(tracks[0]!.stops).toBe(1)
    expect(h.video.srcObject).toBeNull()
    expect(h.timers.size).toBe(0)
    expect(tracks[0]!.listeners).toBe(0)
    expect(h.video.listeners).toBe(0)
    tracks[0]!.dispatchEvent(new Event('ended'))
    h.video.dispatchEvent(new Event('resize'))
    expect(lost).toEqual([])
  })
})

describe('capture', () => {
  it('copies the whole frame at its own size, stops the camera, then encodes once', async () => {
    const h = harness()
    const { tracks } = await preview(h, 1600, 1200)
    const order: string[] = []
    const shot = h.camera.capture((frame) => {
      order.push(
        `admit ${frame.width}x${frame.height} live=${tracks[0]!.readyState}`,
      )
      return true
    })
    if (!shot.ok) throw new Error(shot.problem)
    expect(order).toEqual(['admit 1600x1200 live=live'])
    expect(shot.frame).toEqual({ width: 1600, height: 1200 })
    expect(shot.takenAt).toBe(1_700_000_000_000)
    expect(h.draws).toEqual([[h.video, 0, 0, 1600, 1200]])
    expect(tracks[0]!.stops).toBe(1)
    expect(h.video.srcObject).toBeNull()
    expect(h.blobCalls).toHaveLength(1)
    expect(h.blobCalls[0]).toMatchObject({ type: 'image/jpeg', quality: 0.92 })
    expect(h.camera.state()).toMatchObject({
      pendingEncoder: true,
      liveTracks: 0,
    })
    const bytes = jpeg(1600, 1200)
    h.blobCalls[0]!.done(new Blob([bytes], { type: 'image/jpeg' }))
    const result = await shot.encoded
    if (!result.ok) throw new Error(result.problem)
    expect(result.decoded).toEqual({ width: 1600, height: 1200 })
    expect(result.photo).toEqual({
      bytes,
      mimeType: 'image/jpeg',
      method: 'camera',
      takenAt: 1_700_000_000_000,
    })
    expect(h.blobCalls).toHaveLength(1)
    expect(h.canvases).toEqual([
      expect.objectContaining({ width: 0, height: 0 }),
    ])
    expect(h.camera.state().pendingEncoder).toBe(false)
  })

  it('leaves the preview running when the caller does not admit the frame', async () => {
    const h = harness()
    const { tracks } = await preview(h)
    expect(h.camera.capture(() => false)).toEqual({
      ok: false,
      problem: 'refused',
    })
    expect(tracks[0]!.stops).toBe(0)
    expect(h.draws).toHaveLength(0)
    expect(h.canvases).toHaveLength(0)
    expect(h.camera.state().previewing).toBe(true)
  })

  it('refuses before a preview, and when the frame is not ready', async () => {
    const h = harness()
    expect(h.camera.capture(() => true)).toEqual({
      ok: false,
      problem: 'not_ready',
    })
    await preview(h)
    h.video.readyState = 1
    expect(h.camera.capture(() => true)).toEqual({
      ok: false,
      problem: 'not_ready',
    })
    expect(h.draws).toHaveLength(0)
  })

  it('allocates nothing for a frame outside the limits', async () => {
    const h = harness()
    const { tracks } = await preview(h)
    h.video.videoWidth = 4000
    h.video.videoHeight = 3000
    let admitted = 0
    expect(h.camera.capture(() => (admitted += 1) > 0)).toEqual({
      ok: false,
      problem: 'dimensions',
    })
    expect(admitted).toBe(0)
    expect(h.canvases).toHaveLength(0)
    expect(tracks[0]!.stops).toBe(1)
  })

  it.each([
    ['no canvas context', (h: Harness) => h.setContext(null)],
    [
      'a failed copy',
      (h: Harness) =>
        h.setContext({
          drawImage() {
            throw new Error('allocation')
          },
        }),
    ],
  ])('stops the camera on %s', async (_name, arrange) => {
    const h = harness()
    const { tracks } = await preview(h)
    arrange(h)
    expect(h.camera.capture(() => true)).toEqual({
      ok: false,
      problem: 'failed',
    })
    expect(tracks[0]!.stops).toBe(1)
    expect(h.blobCalls).toHaveLength(0)
    expect(h.camera.state().pendingEncoder).toBe(false)
  })

  async function encodeWith(blob: Blob | null, arrange?: (h: Harness) => void) {
    const h = harness()
    await preview(h)
    arrange?.(h)
    const shot = h.camera.capture(() => true)
    if (!shot.ok) throw new Error(shot.problem)
    h.blobCalls[0]!.done(blob)
    return { h, result: await shot.encoded }
  }

  it.each([
    ['a null result', null, 'failed'],
    ['an empty result', new Blob([], { type: 'image/jpeg' }), 'failed'],
    [
      'a PNG fallback',
      new Blob([jpeg(1280, 960)], { type: 'image/png' }),
      'not_jpeg',
    ],
    [
      'JPEG-labelled bytes that are not JPEG',
      new Blob([new Uint8Array([0x89, 0x50, 0x4e, 0x47, 1, 2])], {
        type: 'image/jpeg',
      }),
      'not_jpeg',
    ],
    [
      'a JPEG of another size',
      new Blob([jpeg(960, 1280)], { type: 'image/jpeg' }),
      'failed',
    ],
    [
      'a JPEG over the photo limit',
      new Blob([jpeg(1280, 960, MAX_PHOTO_BYTES)], { type: 'image/jpeg' }),
      'too_large',
    ],
  ])('refuses %s without a second attempt', async (_name, blob, problem) => {
    const { h, result } = await encodeWith(blob)
    expect(result).toEqual({ ok: false, problem })
    expect(h.blobCalls).toHaveLength(1)
    expect(h.camera.state().pendingEncoder).toBe(false)
  })

  it('does not decode bytes whose header already disagrees with the frame', async () => {
    let decodes = 0
    const { result } = await encodeWith(
      new Blob([jpeg(4000, 3000)], { type: 'image/jpeg' }),
      (h) =>
        h.setDecode(async () => {
          decodes += 1
          return { width: 4000, height: 3000 }
        }),
    )
    expect(result).toEqual({ ok: false, problem: 'failed' })
    expect(decodes).toBe(0)
  })

  it.each([
    ['a decode failure', () => Promise.reject(new Error('decode'))],
    [
      'a decoded size that differs',
      () => Promise.resolve({ width: 640, height: 480 }),
    ],
  ])('refuses %s', async (_name, decode) => {
    const { result } = await encodeWith(
      new Blob([jpeg(1280, 960)], { type: 'image/jpeg' }),
      (h) => h.setDecode(decode),
    )
    expect(result).toEqual({ ok: false, problem: 'failed' })
  })

  it('keeps the encoder slot after a timeout until the browser settles', async () => {
    const h = harness()
    await preview(h)
    const shot = h.camera.capture(() => true)
    if (!shot.ok) throw new Error(shot.problem)
    h.fire(CAMERA_ENCODE_WAIT_MS)
    expect(await shot.encoded).toEqual({ ok: false, problem: 'timeout' })
    expect(h.camera.state().pendingEncoder).toBe(true)
    expect(await h.camera.start(h.video as unknown as CameraVideo)).toEqual({
      ok: false,
      problem: 'busy',
    })
    expect(h.requests).toHaveLength(1)
    h.blobCalls[0]!.done(new Blob([jpeg(1280, 960)], { type: 'image/jpeg' }))
    await tick()
    expect(h.camera.state().pendingEncoder).toBe(false)
    expect((await preview(h)).result.ok).toBe(true)
  })

  it('discards a result that settles after cancel', async () => {
    const h = harness()
    await preview(h)
    const shot = h.camera.capture(() => true)
    if (!shot.ok) throw new Error(shot.problem)
    h.camera.stop()
    h.blobCalls[0]!.done(new Blob([jpeg(1280, 960)], { type: 'image/jpeg' }))
    expect(await shot.encoded).toEqual({ ok: false, problem: 'cancelled' })
    expect(h.camera.state().pendingEncoder).toBe(false)
  })

  it('accepts a JPEG of exactly the photo limit', async () => {
    const base = jpeg(1280, 960).byteLength
    const { result } = await encodeWith(
      new Blob([jpeg(1280, 960, MAX_PHOTO_BYTES - base)], {
        type: 'image/jpeg',
      }),
    )
    expect(result.ok && result.photo.bytes.byteLength).toBe(MAX_PHOTO_BYTES)
  })

  it('refuses when the caller stops the camera while deciding', async () => {
    const h = harness()
    await preview(h)
    expect(
      h.camera.capture(() => {
        h.camera.stop()
        return true
      }),
    ).toEqual({ ok: false, problem: 'refused' })
    expect(h.draws).toHaveLength(0)
    expect(h.blobCalls).toHaveLength(0)
  })

  it('reports when the encoder has ended, and reads nothing from an obsolete result', async () => {
    const h = harness()
    let decodes = 0
    h.setDecode(async () => {
      decodes += 1
      return { width: 1280, height: 960 }
    })
    await preview(h)
    const shot = h.camera.capture(() => true)
    if (!shot.ok) throw new Error(shot.problem)
    let free = false
    void shot.settled.then(() => (free = true))
    h.fire(CAMERA_ENCODE_WAIT_MS)
    await shot.encoded
    await tick()
    expect(free).toBe(false)
    const blob = new Blob([jpeg(1280, 960)], { type: 'image/jpeg' })
    const read = vi.spyOn(blob, 'arrayBuffer')
    h.blobCalls[0]!.done(blob)
    await tick()
    expect(free).toBe(true)
    expect(read).not.toHaveBeenCalled()
    expect(decodes).toBe(0)
  })

  it('cannot capture twice from one preview', async () => {
    const h = harness()
    await preview(h)
    expect(h.camera.capture(() => true).ok).toBe(true)
    expect(h.camera.capture(() => true)).toEqual({
      ok: false,
      problem: 'not_ready',
    })
    expect(h.blobCalls).toHaveLength(1)
  })
})
