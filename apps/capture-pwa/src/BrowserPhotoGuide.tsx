import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { containRect, type Dimensions } from './platform/browserCamera'
import type { CapturedPhoto } from './platform/types'
import type { ShotType } from './types'

/**
 * WP-COLLECT-4B: the optional framing guide's window (docs/LIVE_CAMERA_GUIDE.md).
 *
 * It shows what its owner tells it and reports what the person presses. It opens no camera,
 * reads no account, stores nothing and sends nothing. The outline is an SVG laid over the
 * preview; it is never part of a photo.
 */

export type GuideView =
  | { kind: 'ready' }
  | { kind: 'requesting' }
  | { kind: 'preview'; frame: Dimensions }
  | { kind: 'encoding' }
  | { kind: 'review'; photo: CapturedPhoto }
  | { kind: 'problem'; message: string; retry: boolean }

export type BrowserPhotoGuideProps = {
  shot: ShotType
  /** What this shot should show, in the form's own words. */
  shotLabel: string
  view: GuideView
  /** The video element the camera plays into; null once, when the window is removed. */
  onVideo(video: HTMLVideoElement | null): void
  onStart(): void
  onShutter(): void
  onUse(): void
  onRetake(): void
  /** Cancel or Escape. The owner confirms before discarding photos already chosen. */
  onCancel(): void
  /** Leave the guide for the camera or gallery picker. */
  onFallback(): void
}

const STATUS: Record<GuideView['kind'], string> = {
  ready: 'The camera is off.',
  requesting: 'Waiting for the camera. Allow it if your browser asks.',
  preview: 'The camera is on. Fit the soil inside the outline.',
  encoding: 'Preparing the photo.',
  review: 'The camera is off. Check the photo.',
  problem: '',
}

function useReviewUrl(photo: CapturedPhoto | null): string | null {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!photo || typeof URL.createObjectURL !== 'function') {
      setUrl(null)
      return
    }
    const next = URL.createObjectURL(
      new Blob([photo.bytes as Uint8Array<ArrayBuffer>], {
        type: photo.mimeType,
      }),
    )
    setUrl(next)
    return () => URL.revokeObjectURL(next)
  }, [photo])
  return url
}

export function BrowserPhotoGuide({
  shot,
  shotLabel,
  view,
  onVideo,
  onStart,
  onShutter,
  onUse,
  onRetake,
  onCancel,
  onFallback,
}: BrowserPhotoGuideProps) {
  const dialog = useRef<HTMLDialogElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  const cancel = useRef(onCancel)
  cancel.current = onCancel
  // One stable ref callback: a re-render never detaches a playing video from its owner.
  const video = useRef(onVideo)
  video.current = onVideo
  const [attachVideo] = useState(
    () => (element: HTMLVideoElement | null) => video.current(element),
  )
  const [box, setBox] = useState<Dimensions | null>(null)
  // Read while rendering: the first button takes focus before any effect runs.
  const [previous] = useState(() =>
    document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null,
  )
  const frame = view.kind === 'preview' ? view.frame : null
  const reviewUrl = useReviewUrl(view.kind === 'review' ? view.photo : null)

  // A modal window: focus moves in, Escape cancels, and focus returns where it came from.
  useLayoutEffect(() => {
    const element = dialog.current
    if (!element) return
    const onEscape = (event: Event) => {
      // A cancel the page cannot prevent is followed by a close, which reports it once.
      if (!event.cancelable) return
      event.preventDefault()
      cancel.current()
    }
    // A browser may close the window itself on a repeated Escape. Only the owner removes it,
    // so it reopens and the owner hears a cancel.
    let removed = false
    const onClose = () => {
      // An open window means this event is left over from an earlier close.
      if (removed || element.open) return
      element.showModal()
      cancel.current()
    }
    element.addEventListener('cancel', onEscape)
    element.addEventListener('close', onClose)
    if (!element.open) element.showModal()
    return () => {
      removed = true
      element.removeEventListener('cancel', onEscape)
      element.removeEventListener('close', onClose)
      if (element.open) element.close()
      if (previous?.isConnected) previous.focus()
    }
  }, [previous])

  // Rotation and resizing move the image inside its box; measure again before the shutter works.
  useLayoutEffect(() => {
    const element = stage.current
    if (!element) return
    const measure = () => {
      const rect = element.getBoundingClientRect()
      setBox(
        rect.width > 0 && rect.height > 0
          ? { width: rect.width, height: rect.height }
          : null,
      )
    }
    measure()
    window.addEventListener('resize', measure)
    window.addEventListener('orientationchange', measure)
    const observer =
      typeof ResizeObserver === 'function' ? new ResizeObserver(measure) : null
    observer?.observe(element)
    return () => {
      window.removeEventListener('resize', measure)
      window.removeEventListener('orientationchange', measure)
      observer?.disconnect()
    }
  }, [view.kind])

  const outline = box && frame ? containRect(box, frame) : null
  const title = `Framing guide: photo ${shot}`

  return (
    <dialog
      ref={dialog}
      className="guide-dialog"
      aria-labelledby="guide-title"
      aria-describedby="guide-notes"
    >
      <h2 id="guide-title">{title}</h2>
      <p className="guide-shot">{shotLabel}</p>
      <div
        ref={stage}
        className="guide-stage"
        data-view={view.kind}
        data-testid="guide-stage"
      >
        <video
          ref={attachVideo}
          className="guide-video"
          // Shown while the camera starts too: some browsers play only a visible video.
          hidden={view.kind !== 'preview' && view.kind !== 'requesting'}
          muted
          playsInline
          aria-label={`Live camera preview for photo ${shot}`}
        />
        {outline && (
          <svg
            className="guide-outline"
            data-testid="guide-outline"
            aria-hidden="true"
            focusable="false"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            style={{
              left: outline.left,
              top: outline.top,
              width: outline.width,
              height: outline.height,
            }}
          >
            <rect
              x="12"
              y="12"
              width="76"
              height="76"
              rx="4"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        )}
        {view.kind === 'review' && reviewUrl && (
          <img
            className="guide-review"
            src={reviewUrl}
            alt={`Photo ${shot} as taken, before you choose it`}
          />
        )}
      </div>
      <p className="guide-status" role="status" aria-live="polite">
        {view.kind === 'problem' ? view.message : STATUS[view.kind]}
      </p>
      <div className="guide-actions">
        {(view.kind === 'ready' || (view.kind === 'problem' && view.retry)) && (
          <button type="button" autoFocus onClick={onStart}>
            {view.kind === 'ready' ? 'Start camera' : 'Start camera again'}
          </button>
        )}
        {(view.kind === 'preview' || view.kind === 'encoding') && (
          <button
            type="button"
            autoFocus
            disabled={view.kind !== 'preview' || !outline}
            onClick={onShutter}
          >
            Take photo {shot}
          </button>
        )}
        {view.kind === 'review' && (
          <>
            <button type="button" autoFocus onClick={onUse}>
              Use photo
            </button>
            <button type="button" onClick={onRetake}>
              Retake
            </button>
          </>
        )}
        {(view.kind === 'ready' || view.kind === 'problem') && (
          <button type="button" onClick={onFallback}>
            Use the camera or gallery instead
          </button>
        )}
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
      <ul id="guide-notes" className="guide-notes">
        <li>Guide photos are not saved until you queue the observation.</li>
        <li>
          The outline only helps you frame the soil. It is not part of the photo
          and measures nothing.
        </li>
        <li>
          A guide photo can show less detail than your phone’s own camera. For
          full resolution, use the camera or gallery instead.
        </li>
      </ul>
    </dialog>
  )
}
