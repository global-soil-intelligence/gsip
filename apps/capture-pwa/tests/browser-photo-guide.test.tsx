import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  BrowserPhotoGuide,
  type BrowserPhotoGuideProps,
  type GuideView,
} from '../src/BrowserPhotoGuide'
import source from '../src/BrowserPhotoGuide.tsx?raw'

const photo = {
  bytes: new Uint8Array([0xff, 0xd8, 0xff, 0xd9]),
  mimeType: 'image/jpeg' as const,
  method: 'camera' as const,
  takenAt: 1,
}

function handlers() {
  return {
    onVideo: vi.fn(),
    onStart: vi.fn(),
    onShutter: vi.fn(),
    onUse: vi.fn(),
    onRetake: vi.fn(),
    onCancel: vi.fn(),
    onFallback: vi.fn(),
  }
}

function show(view: GuideView, extra: Partial<BrowserPhotoGuideProps> = {}) {
  const calls = handlers()
  const utils = render(
    <BrowserPhotoGuide
      shot="A"
      shotLabel="Soil surface from above"
      view={view}
      {...calls}
      {...extra}
    />,
  )
  return { calls, ...utils }
}

let box = { width: 400, height: 800 }

beforeEach(() => {
  box = { width: 400, height: 800 }
  // jsdom has no modal dialog or layout; give it the two methods the window uses.
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '')
  }
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open')
  }
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
    () => ({ ...box, left: 0, top: 0 }) as DOMRect,
  )
  URL.createObjectURL = vi.fn(() => 'blob:review')
  URL.revokeObjectURL = vi.fn()
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('BrowserPhotoGuide', () => {
  it('is a labelled modal that starts with the camera off', () => {
    const { calls } = show({ kind: 'ready' })
    const dialog = screen.getByRole('dialog', {
      name: 'Framing guide: photo A',
    })
    expect(dialog).toHaveProperty('open', true)
    expect(screen.getByText('Soil surface from above')).toBeTruthy()
    expect(screen.getByRole('status').textContent).toBe('The camera is off.')
    expect(calls.onStart).not.toHaveBeenCalled()
    expect(calls.onVideo).toHaveBeenCalledWith(expect.any(HTMLVideoElement))
    expect(screen.queryByTestId('guide-outline')).toBeNull()
  })

  it('starts the camera only when Start camera is pressed', () => {
    const { calls } = show({ kind: 'ready' })
    fireEvent.click(screen.getByRole('button', { name: 'Start camera' }))
    expect(calls.onStart).toHaveBeenCalledTimes(1)
    expect(calls.onShutter).not.toHaveBeenCalled()
  })

  it('says the photos are not saved, the outline is not in the photo, and detail may be lower', () => {
    show({ kind: 'ready' })
    const notes = screen.getByRole('list').textContent ?? ''
    expect(notes).toContain('not saved until you queue')
    expect(notes).toContain('not part of the photo and measures nothing')
    expect(notes).toContain('less detail')
  })

  it('offers only Cancel while the browser is asking', () => {
    const { calls } = show({ kind: 'requesting' })
    expect(
      screen.getAllByRole('button').map((button) => button.textContent),
    ).toEqual(['Cancel'])
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(calls.onCancel).toHaveBeenCalledTimes(1)
  })

  it('places the outline on the image, not the letterbox', () => {
    show({ kind: 'preview', frame: { width: 1600, height: 1200 } })
    const outline = screen.getByTestId('guide-outline')
    expect(outline.style.left).toBe('0px')
    expect(outline.style.top).toBe('250px')
    expect(outline.style.width).toBe('400px')
    expect(outline.style.height).toBe('300px')
    expect(outline.getAttribute('aria-hidden')).toBe('true')
    expect(screen.getByRole('button', { name: 'Take photo A' })).toHaveProperty(
      'disabled',
      false,
    )
  })

  it('moves the outline when the window is rotated', () => {
    show({ kind: 'preview', frame: { width: 1600, height: 1200 } })
    box = { width: 800, height: 400 }
    fireEvent(window, new Event('resize'))
    const outline = screen.getByTestId('guide-outline')
    expect(parseFloat(outline.style.left)).toBeCloseTo((800 - 1600 / 3) / 2, 6)
    expect(outline.style.top).toBe('0px')
    expect(outline.style.height).toBe('400px')
  })

  it('keeps the shutter off until the preview has been measured', () => {
    box = { width: 0, height: 0 }
    const { calls } = show({
      kind: 'preview',
      frame: { width: 1600, height: 1200 },
    })
    const shutter = screen.getByRole('button', { name: 'Take photo A' })
    expect(shutter).toHaveProperty('disabled', true)
    fireEvent.click(shutter)
    expect(calls.onShutter).not.toHaveBeenCalled()
  })

  it('keeps the video muted, inline, unmirrored and hidden unless previewing', () => {
    const { container, rerender } = show({ kind: 'ready' })
    const video = container.querySelector('video')!
    expect(video.hidden).toBe(true)
    expect(video.muted).toBe(true)
    expect(video.playsInline).toBe(true)
    expect(video.hasAttribute('controls')).toBe(false)
    expect(video.style.transform).toBe('')
    rerender(
      <BrowserPhotoGuide
        shot="A"
        shotLabel="Soil surface from above"
        view={{ kind: 'preview', frame: { width: 1280, height: 720 } }}
        {...handlers()}
      />,
    )
    expect(container.querySelector('video')).toBe(video)
    expect(video.hidden).toBe(false)
  })

  it('shows the video while the camera starts, so a browser will play it', () => {
    const { container } = show({ kind: 'requesting' })
    expect(container.querySelector('video')!.hidden).toBe(false)
  })

  it('never detaches the video when its owner re-renders with new handlers', () => {
    const first = handlers()
    const { rerender } = render(
      <BrowserPhotoGuide
        shot="A"
        shotLabel="x"
        view={{ kind: 'requesting' }}
        {...first}
      />,
    )
    const second = handlers()
    rerender(
      <BrowserPhotoGuide
        shot="A"
        shotLabel="x"
        view={{ kind: 'preview', frame: { width: 1280, height: 720 } }}
        {...second}
      />,
    )
    expect(first.onVideo).toHaveBeenCalledTimes(1)
    expect(second.onVideo).not.toHaveBeenCalled()
    cleanup()
    expect(second.onVideo.mock.calls).toEqual([[null]])
  })

  it('reopens and reports a cancel if the browser closes the window itself', () => {
    const { calls } = show({
      kind: 'preview',
      frame: { width: 1280, height: 720 },
    })
    const dialog = screen.getByRole('dialog', {
      hidden: true,
    }) as HTMLDialogElement
    dialog.close()
    dialog.dispatchEvent(new Event('close'))
    expect(dialog.open).toBe(true)
    expect(calls.onCancel).toHaveBeenCalledTimes(1)
  })

  it('reports one cancel when the browser sends an unpreventable cancel then closes', () => {
    const { calls } = show({ kind: 'ready' })
    const dialog = screen.getByRole('dialog') as HTMLDialogElement
    dialog.dispatchEvent(new Event('cancel', { cancelable: false }))
    expect(calls.onCancel).not.toHaveBeenCalled()
    dialog.close()
    dialog.dispatchEvent(new Event('close'))
    expect(calls.onCancel).toHaveBeenCalledTimes(1)
    expect(dialog.open).toBe(true)
  })

  it('ignores a close event left over from a development remount', () => {
    const calls = handlers()
    render(
      <StrictMode>
        <BrowserPhotoGuide
          shot="A"
          shotLabel="x"
          view={{ kind: 'ready' }}
          {...calls}
        />
      </StrictMode>,
    )
    const dialog = screen.getByRole('dialog') as HTMLDialogElement
    expect(dialog.open).toBe(true)
    // A real browser delivers the first unmount's close event after the remount.
    dialog.dispatchEvent(new Event('close'))
    expect(calls.onCancel).not.toHaveBeenCalled()
  })

  it('does not report a cancel when its owner removes it', () => {
    const { calls, unmount } = show({ kind: 'ready' })
    unmount()
    expect(calls.onCancel).not.toHaveBeenCalled()
  })

  it('disables the shutter while a photo is being prepared', () => {
    const { calls } = show({ kind: 'encoding' })
    const shutter = screen.getByRole('button', { name: 'Take photo A' })
    expect(shutter).toHaveProperty('disabled', true)
    fireEvent.click(shutter)
    expect(calls.onShutter).not.toHaveBeenCalled()
  })

  it('reviews the photo without the outline and releases its preview', () => {
    const { calls, unmount } = show({ kind: 'review', photo })
    expect(
      screen.getByAltText('Photo A as taken, before you choose it'),
    ).toHaveProperty('src', 'blob:review')
    expect(screen.queryByTestId('guide-outline')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Use photo' }))
    fireEvent.click(screen.getByRole('button', { name: 'Retake' }))
    expect(calls.onUse).toHaveBeenCalledTimes(1)
    expect(calls.onRetake).toHaveBeenCalledTimes(1)
    unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:review')
  })

  it('shows a problem with the picker as the way forward', () => {
    const { calls } = show({
      kind: 'problem',
      message: 'The camera was not allowed.',
      retry: false,
    })
    expect(screen.getByRole('status').textContent).toBe(
      'The camera was not allowed.',
    )
    expect(screen.queryByRole('button', { name: /Start camera/ })).toBeNull()
    fireEvent.click(
      screen.getByRole('button', { name: 'Use the camera or gallery instead' }),
    )
    expect(calls.onFallback).toHaveBeenCalledTimes(1)
    expect(calls.onStart).not.toHaveBeenCalled()
  })

  it('offers another start only when the owner allows a retry', () => {
    const { calls } = show({
      kind: 'problem',
      message: 'The camera stopped.',
      retry: true,
    })
    fireEvent.click(screen.getByRole('button', { name: 'Start camera again' }))
    expect(calls.onStart).toHaveBeenCalledTimes(1)
  })

  it('treats Escape as Cancel and leaves closing to its owner', () => {
    const { calls } = show({ kind: 'ready' })
    const dialog = screen.getByRole('dialog')
    const escape = new Event('cancel', { cancelable: true })
    dialog.dispatchEvent(escape)
    expect(escape.defaultPrevented).toBe(true)
    expect(calls.onCancel).toHaveBeenCalledTimes(1)
    expect(dialog).toHaveProperty('open', true)
  })

  it('returns focus to where it came from and releases the video on close', () => {
    const opener = document.createElement('button')
    document.body.append(opener)
    opener.focus()
    const { calls, unmount } = show({ kind: 'ready' })
    unmount()
    expect(document.activeElement).toBe(opener)
    expect(calls.onVideo.mock.lastCall?.[0]).toBeNull()
    opener.remove()
  })

  it('imports no account, storage, queue or network code and calls no media method', () => {
    expect(source).not.toMatch(
      /supabase|indexedDB|localStorage|fetch\(|getUserMedia|mediaDevices|enumerateDevices|console\./,
    )
    const imports = [...source.matchAll(/from '([^']+)'/g)].map(
      (match) => match[1],
    )
    expect(imports.sort()).toEqual(
      [
        './platform/browserCamera',
        './platform/types',
        './types',
        'react',
      ].sort(),
    )
  })
})
