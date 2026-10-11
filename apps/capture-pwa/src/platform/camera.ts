import type { CameraPlugin, TakePhotoOptions } from '@capacitor/camera'
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
 * A photo chosen through a file input, on the website or in the app. Its own timestamp gives the
 * capture time, and its age against the page load gives the camera-or-file claim (WP-6e).
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
 * Options for the native camera: no editing, no resizing, no rotation (photo QA reads the
 * orientation tag itself), and never added to the person's library. With @capacitor/camera 8.2,
 * Android returns the camera app's own file untouched, so its EXIF capture time reaches photo QA
 * as evidence (WP-6e tier 1). iOS re-encodes the image at this quality and drops EXIF, exactly as
 * Safari's file input does, so iPhone captures stay at tier 0 until a capture path that keeps
 * metadata exists (WP-APP-2).
 */
export const TAKE_PHOTO_OPTIONS: TakePhotoOptions = {
  correctOrientation: false,
  editable: 'no',
  includeMetadata: false,
  quality: 92,
  saveToGallery: false,
}

// @capacitor/camera error codes (CameraErrorCode).
const CANCELLED = 'OS-PLUG-CAMR-0006'
const DENIED = 'OS-PLUG-CAMR-0003'
const NO_CAMERA = 'OS-PLUG-CAMR-0007'

export function errorCode(error: unknown): string | undefined {
  if (typeof error !== 'object' || error === null || !('code' in error))
    return undefined
  return typeof error.code === 'string' ? error.code : undefined
}

export type NativeCameraOptions = {
  /** Reads a plugin result's `webPath` (a URL the app's web view can fetch). */
  readBytes(webPath: string): Promise<Uint8Array>
  /** Deletes the plugin's output file (its `uri`) once read. */
  discard(uri: string): Promise<void>
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
 * JPEG within the size limit; anything else is refused with a reason the person can act on. The
 * plugin's own copy, which can carry the camera's GPS tags, is deleted as soon as it is read: the
 * queue keeps the bytes until the observation syncs.
 */
export function nativeCamera(
  plugin: Pick<CameraPlugin, 'takePhoto'>,
  options: NativeCameraOptions,
): NativeCamera {
  return {
    kind: 'native',
    async takePhoto() {
      let media: Awaited<ReturnType<CameraPlugin['takePhoto']>>
      try {
        media = await plugin.takePhoto(TAKE_PHOTO_OPTIONS)
      } catch (error) {
        const code = errorCode(error)
        if (code === CANCELLED) return null
        if (code === DENIED) throw new PhotoRefused('permission_denied')
        if (code === NO_CAMERA) throw new PhotoRefused('no_camera')
        throw new PhotoRefused('failed')
      }
      // The camera has just taken it: now is its capture time.
      const takenAt = options.now()
      try {
        if (!media.webPath) throw new PhotoRefused('failed')
        const bytes = await options
          .readBytes(media.webPath)
          .catch((): never => {
            throw new PhotoRefused('failed')
          })
        if (bytes.byteLength > MAX_PHOTO_BYTES)
          throw new PhotoRefused('too_large')
        if (!isJpeg(bytes)) throw new PhotoRefused('not_jpeg')
        return { bytes, mimeType: 'image/jpeg', takenAt, method: 'camera' }
      } finally {
        if (media.uri) await options.discard(media.uri).catch(() => undefined)
      }
    },
  }
}
