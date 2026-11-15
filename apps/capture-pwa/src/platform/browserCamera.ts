import { guideFrameAllowed } from '../guideSession'
import { isJpeg, MAX_PHOTO_BYTES } from './camera'
import type { CapturedPhoto } from './types'

/**
 * WP-COLLECT-4B: the browser camera behind the optional framing guide (docs/LIVE_CAMERA_GUIDE.md).
 *
 * One controller owns at most one unresolved camera request, one video track and one unresolved
 * encoder. It asks for video only, shows the frame as the browser delivers it, and copies one
 * full frame to a JPEG. It imports no auth, queue, storage or network code, enumerates no
 * devices, keeps no device label or identifier, and logs nothing.
 *
 * A snapshot is uncalibrated RGB source evidence. Nothing here corrects colour, crops, rotates,
 * mirrors, scales or sharpens the frame, and the outline the person sees is never drawn into it.
 */

export const CAMERA_JPEG_QUALITY = 0.92
export const CAMERA_PERMISSION_WAIT_MS = 20_000
export const CAMERA_PLAYBACK_WAIT_MS = 10_000
export const CAMERA_PREVIEW_MS = 60_000
export const CAMERA_ENCODE_WAIT_MS = 10_000

/** Video only, rear camera preferred, never a named device. */
export const CAMERA_CONSTRAINTS: MediaStreamConstraints = {
  audio: false,
  video: {
    facingMode: { ideal: 'environment' },
    width: { ideal: 1920, max: 2048 },
    height: { ideal: 1440, max: 2048 },
  },
}

export type Dimensions = { width: number; height: number }

export type CameraStartProblem =
  | 'busy'
  | 'cancelled'
  | 'denied'
  | 'dimensions'
  | 'failed'
  | 'playback'
  | 'refused'
  | 'timeout'
  | 'unavailable'

export type CameraStartResult =
  { ok: true; frame: Dimensions } | { ok: false; problem: CameraStartProblem }

export type CameraLost = 'dimensions' | 'ended' | 'muted' | 'preview_timeout'

export type CameraEncodeProblem =
  'cancelled' | 'failed' | 'not_jpeg' | 'timeout' | 'too_large'

export type CameraEncodeResult =
  | { ok: true; photo: CapturedPhoto; decoded: Dimensions }
  | { ok: false; problem: CameraEncodeProblem }

export type CameraCaptureProblem =
  'busy' | 'dimensions' | 'failed' | 'not_ready' | 'refused'

export type CameraCapture =
  | {
      ok: true
      frame: Dimensions
      takenAt: number
      encoded: Promise<CameraEncodeResult>
      /** Resolves when the browser's encoder has ended, even after a timeout or cancel. */
      settled: Promise<void>
    }
  | { ok: false; problem: CameraCaptureProblem }

/** The video element surface the controller uses; a real HTMLVideoElement satisfies it. */
export type CameraVideo = Pick<
  HTMLVideoElement,
  | 'addEventListener'
  | 'muted'
  | 'pause'
  | 'play'
  | 'playsInline'
  | 'readyState'
  | 'removeEventListener'
  | 'srcObject'
  | 'videoHeight'
  | 'videoWidth'
>

export type CameraCanvas = Pick<
  HTMLCanvasElement,
  'getContext' | 'height' | 'toBlob' | 'width'
>

export type CameraPorts = {
  getUserMedia(constraints: MediaStreamConstraints): Promise<MediaStream>
  createCanvas(): CameraCanvas
  /** Decodes the encoded bytes and reports the decoded size, releasing what it allocated. */
  decode(blob: Blob): Promise<Dimensions>
  now(): number
  setTimeout(run: () => void, ms: number): unknown
  clearTimeout(handle: unknown): void
}

export type CameraStartHooks = {
  /**
   * Runs synchronously when the current request's stream arrives, before it is attached or
   * played. Returning false stops that stream at once and ends the start as `refused`.
   */
  granted?(): boolean
  /**
   * Runs once when the request slot frees: when the browser's own request ends, granted or not,
   * current or obsolete, or at once if the browser throws instead of asking. Until then the slot
   * is taken, whatever `start` has already returned. A `busy` start never took the slot and does
   * not call it.
   */
  requestSettled?(): void
}

export type CameraEnvironment = {
  isSecureContext?: boolean
  top?: unknown
  self?: unknown
  navigator?: { mediaDevices?: { getUserMedia?: unknown } }
  HTMLCanvasElement?: { prototype: { toBlob?: unknown; getContext?: unknown } }
  HTMLDialogElement?: { prototype: { showModal?: unknown } }
  createImageBitmap?: unknown
}

/**
 * Whether this page may offer the guide at all: a top-level secure context with the media,
 * dialog, canvas and decode methods the guide needs. It asks for no permission and calls no
 * media method.
 */
export function browserCameraSupported(env: CameraEnvironment): boolean {
  return (
    env.isSecureContext === true &&
    env.top !== undefined &&
    env.top === env.self &&
    typeof env.navigator?.mediaDevices?.getUserMedia === 'function' &&
    typeof env.HTMLCanvasElement?.prototype.toBlob === 'function' &&
    typeof env.HTMLCanvasElement?.prototype.getContext === 'function' &&
    typeof env.HTMLDialogElement?.prototype.showModal === 'function' &&
    typeof env.createImageBitmap === 'function'
  )
}

/** The page's own ports. Only call after browserCameraSupported is true. */
export function browserCameraPorts(
  env: Window & typeof globalThis,
): CameraPorts {
  return {
    getUserMedia: (constraints) =>
      env.navigator.mediaDevices.getUserMedia(constraints),
    createCanvas: () => env.document.createElement('canvas'),
    async decode(blob) {
      const bitmap = await env.createImageBitmap(blob)
      try {
        return { width: bitmap.width, height: bitmap.height }
      } finally {
        bitmap.close()
      }
    },
    now: () => env.Date.now(),
    setTimeout: (run, ms) => env.setTimeout(run, ms),
    clearTimeout: (handle) => env.clearTimeout(handle as number),
  }
}

/**
 * Where the whole video image sits inside its box under contain layout, excluding the letterbox.
 * The outline is placed in this rectangle so it lines up with the image the person sees.
 */
export function containRect(
  box: Dimensions,
  frame: Dimensions,
): { left: number; top: number; width: number; height: number } | null {
  if (
    ![box.width, box.height, frame.width, frame.height].every(
      (value) => Number.isFinite(value) && value > 0,
    )
  )
    return null
  const scale = Math.min(box.width / frame.width, box.height / frame.height)
  const width = frame.width * scale
  const height = frame.height * scale
  return {
    left: (box.width - width) / 2,
    top: (box.height - height) / 2,
    width,
    height,
  }
}

/**
 * The size a JPEG declares in its first frame header, read without decoding the image, or null
 * when the bytes hold none. Used to check the encoder's output before any decode buffer exists.
 */
export function jpegDimensions(bytes: Uint8Array): Dimensions | null {
  if (!isJpeg(bytes)) return null
  let offset = 2
  while (offset + 4 <= bytes.byteLength) {
    if (bytes[offset] !== 0xff) return null
    const marker = bytes[offset + 1]!
    if (marker === 0xff) {
      offset += 1
      continue
    }
    // Markers without a length: restart markers, start of image and TEM.
    if ((marker >= 0xd0 && marker <= 0xd8) || marker === 0x01) {
      offset += 2
      continue
    }
    if (marker === 0xd9 || marker === 0xda) return null
    const length = (bytes[offset + 2]! << 8) | bytes[offset + 3]!
    if (length < 2) return null
    const frameHeader =
      marker >= 0xc0 &&
      marker <= 0xcf &&
      marker !== 0xc4 &&
      marker !== 0xc8 &&
      marker !== 0xcc
    if (frameHeader) {
      if (length < 7 || offset + 9 > bytes.byteLength) return null
      const height = (bytes[offset + 5]! << 8) | bytes[offset + 6]!
      const width = (bytes[offset + 7]! << 8) | bytes[offset + 8]!
      return width > 0 && height > 0 ? { width, height } : null
    }
    offset += 2 + length
  }
  return null
}

function startProblem(error: unknown): CameraStartProblem {
  const name =
    typeof error === 'object' && error !== null && 'name' in error
      ? error.name
      : undefined
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'denied'
  if (
    name === 'NotFoundError' ||
    name === 'OverconstrainedError' ||
    name === 'NotReadableError' ||
    name === 'AbortError'
  )
    return 'unavailable'
  return 'failed'
}

function stopTracks(stream: MediaStream): void {
  try {
    for (const track of stream.getTracks()) track.stop()
  } catch {
    // A stream that cannot list its tracks has nothing this controller can stop.
  }
}

const videoEvents = [
  'loadeddata',
  'loadedmetadata',
  'resize',
  'playing',
] as const

type Live = {
  stream: MediaStream
  track: MediaStreamTrack
  video: CameraVideo
  release: () => void
}

/**
 * At most one of these exists per page. `stop` is the one cleanup path: it runs on cancel, on
 * every invalidation and before any capture's bytes are encoded, and never waits for an event.
 */
export class BrowserCamera {
  private readonly ports: CameraPorts
  private generation = 0
  private requestPending = false
  private encoderPending = false
  private live: Live | null = null
  private previewing = false
  private previewTimer: unknown = null
  private canvas: CameraCanvas | null = null
  private lost: ((reason: CameraLost) => void) | null = null
  private geometry: ((frame: Dimensions) => void) | null = null
  private abortStart: ((problem: CameraStartProblem) => void) | null = null

  constructor(ports: CameraPorts) {
    this.ports = ports
  }

  state() {
    return {
      pendingRequest: this.requestPending,
      pendingEncoder: this.encoderPending,
      liveTracks: this.live ? 1 : 0,
      previewing: this.previewing,
    }
  }

  /** Called when the camera stops by itself; the controller has already cleaned up. */
  onLost(listener: ((reason: CameraLost) => void) | null): void {
    this.lost = listener
  }

  /** Called when the preview's frame size changes, so the outline can be placed again. */
  onGeometry(listener: ((frame: Dimensions) => void) | null): void {
    this.geometry = listener
  }

  /**
   * Opens the camera into `video`. Call only from the person's explicit Start action. A wait
   * that times out does not cancel the browser's own request: its slot stays taken, and a stream
   * that arrives late is stopped by the handler attached here, never by a later request.
   */
  async start(
    video: CameraVideo,
    hooks: CameraStartHooks = {},
  ): Promise<CameraStartResult> {
    if (this.requestPending || this.encoderPending || this.live)
      return { ok: false, problem: 'busy' }
    const generation = ++this.generation
    this.requestPending = true
    // The caller's hook cannot break the controller: its errors are dropped, never logged.
    const requestSettled = () => {
      try {
        hooks.requestSettled?.()
      } catch {
        // Nothing to do: the slot is already free.
      }
    }
    let request: Promise<MediaStream>
    try {
      request = this.ports.getUserMedia(CAMERA_CONSTRAINTS)
    } catch (error) {
      this.requestPending = false
      requestSettled()
      return { ok: false, problem: startProblem(error) }
    }
    let abort: ((problem: CameraStartProblem) => void) | null = null
    // A hook may start again; only this start's own handle is ever cleared here.
    const clearAbort = () => {
      if (this.abortStart === abort) this.abortStart = null
    }
    const granted = await new Promise<
      { stream: MediaStream } | { problem: CameraStartProblem }
    >((resolve) => {
      const timer = this.ports.setTimeout(() => {
        if (this.generation === generation) this.generation += 1
        resolve({ problem: 'timeout' })
      }, CAMERA_PERMISSION_WAIT_MS)
      abort = (problem) => {
        this.ports.clearTimeout(timer)
        resolve({ problem })
      }
      this.abortStart = abort
      request.then(
        (stream) => {
          this.requestPending = false
          this.ports.clearTimeout(timer)
          if (this.generation !== generation) {
            stopTracks(stream)
            resolve({ problem: 'cancelled' })
          } else resolve({ stream })
          requestSettled()
        },
        (error: unknown) => {
          this.requestPending = false
          this.ports.clearTimeout(timer)
          resolve({
            problem:
              this.generation === generation
                ? startProblem(error)
                : 'cancelled',
          })
          requestSettled()
        },
      )
    })
    clearAbort()
    if ('problem' in granted) return { ok: false, problem: granted.problem }
    const stream = granted.stream
    // A stop can land between the stream arriving and this continuation.
    if (this.generation !== generation) {
      stopTracks(stream)
      return { ok: false, problem: 'cancelled' }
    }
    let admitted: boolean
    try {
      admitted = hooks.granted?.() ?? true
    } catch {
      admitted = false
    }
    if (!admitted || this.generation !== generation) {
      stopTracks(stream)
      return { ok: false, problem: admitted ? 'cancelled' : 'refused' }
    }
    let tracks: MediaStreamTrack[]
    try {
      tracks = stream.getTracks()
    } catch {
      return { ok: false, problem: 'failed' }
    }
    const track = tracks[0]
    if (
      tracks.length !== 1 ||
      !track ||
      track.kind !== 'video' ||
      track.readyState !== 'live'
    ) {
      stopTracks(stream)
      return { ok: false, problem: 'failed' }
    }
    const fail = (problem: CameraStartProblem): CameraStartResult => {
      if (this.generation === generation) this.stop()
      return { ok: false, problem }
    }
    const onEnded = () => this.lose(generation, 'ended')
    const onMute = () => this.lose(generation, 'muted')
    const onVideo = () => this.frameChanged(generation)
    track.addEventListener('ended', onEnded)
    track.addEventListener('mute', onMute)
    for (const name of videoEvents) video.addEventListener(name, onVideo)
    this.live = {
      stream,
      track,
      video,
      release: () => {
        track.removeEventListener('ended', onEnded)
        track.removeEventListener('mute', onMute)
        for (const name of videoEvents) video.removeEventListener(name, onVideo)
      },
    }
    if (track.muted) return fail('failed')

    const playable = await new Promise<CameraStartProblem | null>((resolve) => {
      const timer = this.ports.setTimeout(
        () => settle('timeout'),
        CAMERA_PLAYBACK_WAIT_MS,
      )
      const settle = (problem: CameraStartProblem | null) => {
        this.ports.clearTimeout(timer)
        for (const name of videoEvents) video.removeEventListener(name, ready)
        resolve(problem)
      }
      const ready = () => {
        if (this.generation !== generation) settle('cancelled')
        else if (
          video.readyState >= 2 &&
          video.videoWidth > 0 &&
          video.videoHeight > 0
        )
          settle(null)
      }
      abort = (problem) => settle(problem)
      this.abortStart = abort
      for (const name of videoEvents) video.addEventListener(name, ready)
      try {
        video.muted = true
        video.playsInline = true
        video.srcObject = stream
        Promise.resolve(video.play()).then(ready, () => {
          settle(this.generation === generation ? 'playback' : 'cancelled')
        })
      } catch {
        settle('playback')
      }
    })
    clearAbort()
    if (this.generation !== generation)
      return { ok: false, problem: playable ?? 'cancelled' }
    if (playable) return fail(playable)
    const frame = { width: video.videoWidth, height: video.videoHeight }
    if (!guideFrameAllowed(frame.width, frame.height)) return fail('dimensions')
    this.previewing = true
    this.previewTimer = this.ports.setTimeout(
      () => this.lose(generation, 'preview_timeout'),
      CAMERA_PREVIEW_MS,
    )
    return { ok: true, frame }
  }

  /**
   * Copies the current full frame, stops the camera, then encodes one JPEG. `admit` runs
   * synchronously after the frame is validated and before it is copied, so the caller can bind
   * the frame to its session; returning false leaves the preview running. There is no await
   * between validation and the copy.
   */
  capture(admit: (frame: Dimensions) => boolean): CameraCapture {
    const live = this.live
    if (!live || !this.previewing) return { ok: false, problem: 'not_ready' }
    if (this.encoderPending) return { ok: false, problem: 'busy' }
    const { video } = live
    const frame = { width: video.videoWidth, height: video.videoHeight }
    if (
      video.readyState < 2 ||
      live.track.readyState !== 'live' ||
      live.track.muted
    )
      return { ok: false, problem: 'not_ready' }
    if (!guideFrameAllowed(frame.width, frame.height)) {
      this.stop()
      return { ok: false, problem: 'dimensions' }
    }
    if (!admit(frame)) return { ok: false, problem: 'refused' }
    // The caller may have stopped the camera while deciding.
    if (this.live !== live || !this.previewing)
      return { ok: false, problem: 'refused' }
    const takenAt = this.ports.now()
    let canvas: CameraCanvas
    try {
      canvas = this.canvas ?? this.ports.createCanvas()
      this.canvas = canvas
      canvas.width = frame.width
      canvas.height = frame.height
      const context = canvas.getContext('2d')
      if (!context) throw new Error('no canvas context')
      // The whole frame at its own size: no crop, flip, rotation, scale or filter.
      context.drawImage(
        video as HTMLVideoElement,
        0,
        0,
        frame.width,
        frame.height,
      )
    } catch {
      this.releaseCanvas()
      this.stop()
      return { ok: false, problem: 'failed' }
    }
    // The frame is copied: no stream stays live while it is encoded or reviewed.
    this.stop()
    const generation = this.generation
    this.encoderPending = true
    let freed!: () => void
    const settled = new Promise<void>((resolve) => {
      freed = resolve
    })
    const encoded = new Promise<CameraEncodeResult>((resolve) => {
      let done = false
      const finish = (result: CameraEncodeResult) => {
        if (done) return
        done = true
        this.ports.clearTimeout(timer)
        resolve(result)
      }
      const timer = this.ports.setTimeout(
        () => finish({ ok: false, problem: 'timeout' }),
        CAMERA_ENCODE_WAIT_MS,
      )
      const slotFreed = (result: CameraEncodeResult) => {
        // The slot frees only when the browser's own work has ended, timed out or not.
        this.encoderPending = false
        this.releaseCanvas()
        freed()
        finish(
          this.generation === generation
            ? result
            : { ok: false, problem: 'cancelled' },
        )
      }
      const check = async (blob: Blob | null): Promise<CameraEncodeResult> => {
        if (!blob || blob.size === 0) return { ok: false, problem: 'failed' }
        if (blob.type !== 'image/jpeg')
          return { ok: false, problem: 'not_jpeg' }
        if (blob.size > MAX_PHOTO_BYTES)
          return { ok: false, problem: 'too_large' }
        const bytes = new Uint8Array(await blob.arrayBuffer())
        if (!isJpeg(bytes)) return { ok: false, problem: 'not_jpeg' }
        const declared = jpegDimensions(bytes)
        if (
          !declared ||
          declared.width !== frame.width ||
          declared.height !== frame.height
        )
          return { ok: false, problem: 'failed' }
        const decoded = await this.ports.decode(blob)
        if (decoded.width !== frame.width || decoded.height !== frame.height)
          return { ok: false, problem: 'failed' }
        return {
          ok: true,
          decoded,
          photo: { bytes, mimeType: 'image/jpeg', method: 'camera', takenAt },
        }
      }
      try {
        canvas.toBlob(
          (blob) => {
            // An obsolete result is dropped unread.
            if (done || this.generation !== generation)
              return slotFreed({ ok: false, problem: 'cancelled' })
            check(blob).then(slotFreed, () =>
              slotFreed({ ok: false, problem: 'failed' }),
            )
          },
          'image/jpeg',
          CAMERA_JPEG_QUALITY,
        )
      } catch {
        slotFreed({ ok: false, problem: 'failed' })
      }
    })
    return { ok: true, frame, takenAt, encoded, settled }
  }

  /**
   * Stops every track, detaches the video and drops listeners and timers, now. Work still
   * unresolved in the browser becomes obsolete: its slot stays taken until it settles, and its
   * late result is discarded.
   */
  stop(): void {
    this.end('cancelled')
  }

  private end(problem: CameraStartProblem): void {
    this.generation += 1
    this.previewing = false
    if (this.previewTimer !== null) {
      this.ports.clearTimeout(this.previewTimer)
      this.previewTimer = null
    }
    const live = this.live
    this.live = null
    if (live) {
      live.release()
      stopTracks(live.stream)
      try {
        live.video.pause()
        live.video.srcObject = null
      } catch {
        // The element may already be gone; the tracks are stopped either way.
      }
    }
    const abort = this.abortStart
    this.abortStart = null
    abort?.(problem)
  }

  private lose(generation: number, reason: CameraLost): void {
    if (this.generation !== generation) return
    // Before the preview exists the loss is the start's own outcome, reported once.
    if (!this.previewing) return this.end('failed')
    this.stop()
    this.lost?.(reason)
  }

  private frameChanged(generation: number): void {
    if (this.generation !== generation || !this.previewing || !this.live) return
    const { video } = this.live
    const frame = { width: video.videoWidth, height: video.videoHeight }
    if (!guideFrameAllowed(frame.width, frame.height))
      this.lose(generation, 'dimensions')
    else this.geometry?.(frame)
  }

  private releaseCanvas(): void {
    const canvas = this.canvas
    this.canvas = null
    if (!canvas) return
    try {
      canvas.width = 0
      canvas.height = 0
    } catch {
      // Nothing else holds the canvas; it is collected with the controller.
    }
  }
}
