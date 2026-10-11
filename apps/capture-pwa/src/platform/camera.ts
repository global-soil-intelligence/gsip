import type {
  CameraPlugin,
  ChooseFromGalleryOptions,
  MediaResult,
  TakePhotoOptions,
} from '@capacitor/camera'
import { captureMethod } from '../provenance'
import type { QueuedPhoto, ShotType } from '../types'
import { type CapturedPhoto, type NativeCamera, PhotoRefused } from './types'

/** The photo buckets' size limit: a larger photo could never upload, so it is never queued. */
export const MAX_PHOTO_BYTES = 12 * 1024 * 1024

/** Whether the bytes start like a JPEG (SOI marker, then another marker). */
export function isJpeg(bytes: Uint8Array): boolean {
  return (
    bytes.byteLength > 3 &&
    bytes[0] === 0xff &&
    bytes[1] === 0xd8 &&
    bytes[2] === 0xff
  )
}

/** A captured photo in the queue's shape (WP-3), as one shot of an observation. */
export function queuedPhoto(
  photo: CapturedPhoto,
  shotType: ShotType,
  objectId: string = crypto.randomUUID(),
): QueuedPhoto {
  return { bytes: photo.bytes, mimeType: photo.mimeType, objectId, shotType }
}

/**
 * A photo a browser chose through a file input. Its own timestamp gives the capture time, and
 * its age against the page load gives the camera-or-file claim (WP-6e).
 */
export async function photoFromFile(
  file: File,
  pageLoadedAt: number,
  now: number,
): Promise<CapturedPhoto> {
  if (file.type !== 'image/jpeg') throw new PhotoRefused('not_jpeg')
  if (file.size > MAX_PHOTO_BYTES) throw new PhotoRefused('too_large')
  return {
    bytes: new Uint8Array(await file.arrayBuffer()),
    mimeType: 'image/jpeg',
    takenAt: file.lastModified,
    method: captureMethod([file], pageLoadedAt, now),
  }
}

/**
 * Options for the native camera. The camera's own JPEG is kept as far as the platform allows:
 * no editing, no resizing and no rotation (photo QA reads the orientation tag itself), and the
 * photo is never added to the person's library. Quality 92 bounds the size where the platform
 * re-encodes.
 */
export const TAKE_PHOTO_OPTIONS: TakePhotoOptions = {
  correctOrientation: false,
  editable: 'no',
  includeMetadata: false,
  quality: 92,
  saveToGallery: false,
}

/** One saved photo, with its metadata for the creation date. */
export const CHOOSE_PHOTO_OPTIONS: ChooseFromGalleryOptions = {
  allowMultipleSelection: false,
  correctOrientation: false,
  editable: 'no',
  includeMetadata: true,
  quality: 92,
}

// @capacitor/camera error codes (CameraErrorCode).
const CANCELLED = new Set(['OS-PLUG-CAMR-0006', 'OS-PLUG-CAMR-0020'])
const DENIED = new Set(['OS-PLUG-CAMR-0003', 'OS-PLUG-CAMR-0005'])
const NO_CAMERA = 'OS-PLUG-CAMR-0007'

export function errorCode(error: unknown): string | undefined {
  if (typeof error !== 'object' || error === null || !('code' in error))
    return undefined
  return typeof error.code === 'string' ? error.code : undefined
}

function dateMs(iso: string | undefined): number | undefined {
  if (!iso) return undefined
  const parsed = Date.parse(iso)
  return Number.isFinite(parsed) ? parsed : undefined
}

export type NativeCameraOptions = {
  /** Reads a plugin result's `webPath` (a URL the app's web view can fetch). */
  readBytes(webPath: string): Promise<Uint8Array>
  now(): number
}

export async function fetchBytes(webPath: string): Promise<Uint8Array> {
  const response = await fetch(webPath)
  if (!response.ok)
    throw new Error(`Could not read the photo (${response.status})`)
  return new Uint8Array(await response.arrayBuffer())
}

/**
 * The phone app's camera (@capacitor/camera). Its output becomes a queue photo only if it is a
 * JPEG within the size limit; anything else is refused with a reason the person can act on.
 */
export function nativeCamera(
  plugin: Pick<CameraPlugin, 'chooseFromGallery' | 'takePhoto'>,
  options: NativeCameraOptions,
): NativeCamera {
  async function asQueuePhoto(
    media: MediaResult | undefined,
    method: CapturedPhoto['method'],
    takenAt: number | undefined,
  ): Promise<CapturedPhoto> {
    if (!media?.webPath) throw new PhotoRefused('failed')
    const bytes = await options.readBytes(media.webPath)
    if (bytes.byteLength > MAX_PHOTO_BYTES) throw new PhotoRefused('too_large')
    if (!isJpeg(bytes)) throw new PhotoRefused('not_jpeg')
    return { bytes, mimeType: 'image/jpeg', takenAt, method }
  }

  async function settle(
    run: () => Promise<CapturedPhoto | null>,
  ): Promise<CapturedPhoto | null> {
    try {
      return await run()
    } catch (error) {
      if (error instanceof PhotoRefused) throw error
      const code = errorCode(error)
      if (code && CANCELLED.has(code)) return null
      if (code && DENIED.has(code)) throw new PhotoRefused('permission_denied')
      if (code === NO_CAMERA) throw new PhotoRefused('no_camera')
      throw new PhotoRefused('failed')
    }
  }

  return {
    kind: 'native',
    takePhoto: () =>
      settle(async () => {
        const media = await plugin.takePhoto(TAKE_PHOTO_OPTIONS)
        // The camera has just taken it: now is its capture time.
        return asQueuePhoto(media, 'camera', options.now())
      }),
    choosePhoto: () =>
      settle(async () => {
        const { results } = await plugin.chooseFromGallery(CHOOSE_PHOTO_OPTIONS)
        const [media] = results
        if (!media) return null
        return asQueuePhoto(media, 'file', dateMs(media.metadata?.creationDate))
      }),
  }
}
