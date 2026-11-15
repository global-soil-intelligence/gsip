import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { GsipClient } from '../src/supabase'

/**
 * WP-COLLECT-4B2: the framing guide inside the app. The camera is a synthetic stream, the canvas
 * returns synthetic JPEG bytes and the account is a mock: no sensor, network or real record.
 */

const mocks = vi.hoisted(() => ({
  create: vi.fn(),
  gate: vi.fn(async () => 'open'),
  send: vi.fn(async () => undefined),
  rights: vi.fn(async () => 'requested'),
  native: false,
  /** Makes the next guide commit succeed in storage and then fail to report it. */
  loseCommitResult: false,
  revisionReads: 0,
}))
/** Wraps the real queue module for one test: fresh per test, so no connection is shared. */
function wrapQueue() {
  vi.doMock('../src/queue', async () => {
    const real =
      await vi.importActual<typeof import('../src/queue')>('../src/queue')
    return {
      ...real,
      queueRevision: async () => {
        mocks.revisionReads += 1
        return real.queueRevision()
      },
      enqueueGuideObservation: async (
        ...args: Parameters<typeof real.enqueueGuideObservation>
      ) => {
        const result = await real.enqueueGuideObservation(...args)
        if (mocks.loseCommitResult) {
          mocks.loseCommitResult = false
          throw new Error('synthetic lost result')
        }
        return result
      },
    }
  })
}
vi.mock('../src/supabase', async (load) => ({
  ...(await load<typeof import('../src/supabase')>()),
  createGsipClient: mocks.create,
  fetchServiceState: mocks.gate,
  submitQueued: mocks.send,
  latestDeletionRequest: vi.fn(async () => null),
  requestDeletion: mocks.rights,
}))
vi.mock('../src/mySoil', () => ({ mySoil: vi.fn(async () => null) }))
vi.mock('../src/platform', async (load) => ({
  ...(await load<typeof import('../src/platform')>()),
  isNativeApp: () => mocks.native,
}))

const WIDTH = 1280
const HEIGHT = 960

function jpeg(tag: number): Uint8Array<ArrayBuffer> {
  return new Uint8Array([
    0xff,
    0xd8,
    0xff,
    0xe0,
    0x00,
    0x04,
    tag,
    0x46,
    0xff,
    0xc0,
    0x00,
    0x0b,
    0x08,
    HEIGHT >> 8,
    HEIGHT & 0xff,
    WIDTH >> 8,
    WIDTH & 0xff,
    0x01,
    0x01,
    0x11,
    0x00,
    0xff,
    0xd9,
  ])
}

class Track extends EventTarget {
  kind = 'video'
  readyState = 'live'
  muted = false
  stop() {
    this.readyState = 'ended'
  }
}

let notify: () => void
let admitted: boolean
let uid: string | null
let media: ReturnType<typeof vi.fn>
let tracks: Track[]
let frames: number
let draws: number
let visibility: DocumentVisibilityState

beforeEach(() => {
  vi.resetModules()
  vi.stubGlobal('indexedDB', new IDBFactory())
  window.history.replaceState(null, '', '/')
  vi.stubEnv('VITE_COLLECTION_MODE', 'invited_private')
  vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
  vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'true')
  vi.stubEnv('VITE_SUPABASE_URL', 'https://supabase.test')
  vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'synthetic-publishable-key')
  admitted = true
  uid = 'owner-a'
  mocks.native = false
  mocks.create.mockReset()
  mocks.send.mockClear()
  mocks.loseCommitResult = false
  mocks.revisionReads = 0
  mocks.create.mockReturnValue({
    auth: {
      getUser: async () => ({
        data: { user: uid ? { id: uid, is_anonymous: false } : null },
        error: null,
      }),
      signInWithOtp: vi.fn(async () => ({ error: null })),
      onAuthStateChange: (changed: () => void) => {
        notify = changed
        return { data: { subscription: { unsubscribe: () => undefined } } }
      },
    },
    rpc: vi.fn(async () => ({
      data: {
        version: 'gsip-invited-pilot-v1',
        mode: 'invited_private',
        member: admitted,
        capture_open: true,
        library_intake_available: true,
        publication_held: true,
      },
      error: null,
    })),
  } as unknown as GsipClient)

  // The page pieces jsdom lacks, all synthetic.
  tracks = []
  frames = 0
  draws = 0
  visibility = 'visible'
  media = vi.fn(async () => {
    const track = new Track()
    tracks.push(track)
    return { getTracks: () => [track] } as unknown as MediaStream
  })
  vi.stubGlobal('isSecureContext', true)
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: media },
  })
  Object.defineProperty(navigator, 'onLine', {
    configurable: true,
    value: false,
  })
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    get: () => visibility,
  })
  vi.stubGlobal(
    'createImageBitmap',
    vi.fn(async () => ({ width: WIDTH, height: HEIGHT, close() {} })),
  )
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '')
  }
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open')
  }
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
    () => ({ width: 400, height: 300, left: 0, top: 0 }) as DOMRect,
  )
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {})
  Object.defineProperty(HTMLMediaElement.prototype, 'readyState', {
    configurable: true,
    get: () => 4,
  })
  Object.defineProperty(HTMLVideoElement.prototype, 'videoWidth', {
    configurable: true,
    get: () => WIDTH,
  })
  Object.defineProperty(HTMLVideoElement.prototype, 'videoHeight', {
    configurable: true,
    get: () => HEIGHT,
  })
  Object.defineProperty(HTMLMediaElement.prototype, 'srcObject', {
    configurable: true,
    writable: true,
    value: null,
  })
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
    drawImage: () => (draws += 1),
  } as unknown as CanvasRenderingContext2D)
  vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation(
    (done: BlobCallback) =>
      done(new Blob([jpeg((frames += 1))], { type: 'image/jpeg' })),
  )
  URL.createObjectURL = vi.fn(() => 'blob:synthetic')
  URL.revokeObjectURL = vi.fn()
})

afterEach(() => {
  cleanup()
  vi.doUnmock('../src/queue')
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  window.history.replaceState(null, '', '/')
})

async function start() {
  const { App } = await import('../src/App')
  render(<App />)
  return import('../src/queue')
}

const enterButton = () =>
  screen.queryByRole('button', { name: 'Use the optional framing guide' })

/** The entry button, once the page's own drafts have finished restoring. */
async function offered() {
  const name = 'Use the optional framing guide'
  const button = (await screen.findByRole('button', {
    name,
  })) as HTMLButtonElement
  await waitFor(() => expect(button.disabled).toBe(false))
  return button
}

async function enter() {
  const q = await start()
  fireEvent.click(await offered())
  await screen.findByRole('button', { name: 'Take photo A with the guide' })
  return q
}

async function take(shot: 'A' | 'B' | 'C', retake = false) {
  fireEvent.click(
    screen.getByRole('button', {
      name: `${retake ? 'Retake' : 'Take'} photo ${shot} with the guide`,
    }),
  )
  fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
  fireEvent.click(
    await screen.findByRole('button', { name: `Take photo ${shot}` }),
  )
  fireEvent.click(await screen.findByRole('button', { name: 'Use photo' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
}

function fillObservation() {
  for (const [label, value] of [
    ['Latitude', '1'],
    ['Longitude', '1'],
    ['Land cover', 'bare'],
    ['Surface condition', 'dry'],
  ])
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  fireEvent.click(screen.getByRole('checkbox', { name: /sampling rules/i }))
  fireEvent.click(screen.getByRole('checkbox', { name: /I own these photos/i }))
}

function submitObservation() {
  fireEvent.submit(
    screen.getByRole('button', { name: /queue observation/i }).closest('form')!,
  )
}

const status = () =>
  document.querySelector('.status-card h2')?.textContent ?? ''

describe('who is offered the guide', () => {
  it('offers it to an admitted invited account and calls no media method', async () => {
    await start()
    expect(await offered()).toBeTruthy()
    expect(media).not.toHaveBeenCalled()
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it.each([
    [
      'the ordinary closed page',
      () => {
        vi.stubEnv('VITE_COLLECTION_MODE', '')
        vi.stubEnv('VITE_CAPTURE_LIVE', 'false')
        vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'false')
      },
    ],
    [
      'ordinary open capture outside the pilot',
      () => vi.stubEnv('VITE_COLLECTION_MODE', ''),
    ],
    ['the phone app', () => (mocks.native = true)],
    [
      'the rights view',
      () => window.history.replaceState(null, '', '/#your-data'),
    ],
    [
      'a build without library intake',
      () => vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'false'),
    ],
    ['an account that is not admitted', () => (admitted = false)],
    ['a signed-out visitor', () => (uid = null)],
    ['an insecure page', () => vi.stubGlobal('isSecureContext', false)],
    [
      'a browser without camera access',
      () =>
        Object.defineProperty(navigator, 'mediaDevices', {
          configurable: true,
          value: undefined,
        }),
    ],
    [
      'a browser without an image decoder',
      () => vi.stubGlobal('createImageBitmap', undefined),
    ],
  ])(
    'does not offer it on %s, and calls no media method',
    async (_name, arrange) => {
      arrange()
      await start()
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 150))
      })
      expect(enterButton()).toBeNull()
      expect(media).not.toHaveBeenCalled()
    },
  )
})

describe('entering the guide', () => {
  it('replaces the picker with guide slots and still opens no camera', async () => {
    await enter()
    expect(document.querySelector('.photo-grid input[type="file"]')).toBeNull()
    expect(status()).toContain('not saved until you queue')
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo A with the guide' }),
    )
    expect(
      await screen.findByRole('dialog', { name: 'Framing guide: photo A' }),
    ).toBeTruthy()
    expect(media).not.toHaveBeenCalled()
  })

  it('refuses while a picker photo is chosen, and deletes nothing', async () => {
    const q = await start()
    await offered()
    fireEvent.change(screen.getByLabelText(/A · Context/), {
      target: { files: [new File([jpeg(9)], 'a.jpg', { type: 'image/jpeg' })] },
    })
    await waitFor(async () =>
      expect(Object.keys(await q.draftPhotos())).toEqual(['A']),
    )
    fireEvent.click(await offered())
    await waitFor(() =>
      expect(status()).toContain('starts with an empty observation'),
    )
    expect(
      screen.queryByRole('button', { name: 'Take photo A with the guide' }),
    ).toBeNull()
    expect(Object.keys(await q.draftPhotos())).toEqual(['A'])
  })

  it('refuses when another tab saved a draft photo this page never showed', async () => {
    const q = await start()
    await offered()
    await q.saveDraftPhoto(
      'B',
      { bytes: jpeg(8), mimeType: 'image/jpeg', method: 'file' },
      await q.queueRevision(),
      () => true,
    )
    fireEvent.click(await offered())
    await waitFor(() =>
      expect(status()).toContain('starts with an empty observation'),
    )
    expect(Object.keys(await q.draftPhotos())).toEqual(['B'])
  })
})

describe('taking photos', () => {
  it('asks for video only, once, on the Start press, and stops the camera before review', async () => {
    await enter()
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo A with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    const shutter = await screen.findByRole('button', { name: 'Take photo A' })
    expect(media).toHaveBeenCalledTimes(1)
    expect(media.mock.calls[0]![0]).toMatchObject({ audio: false })
    expect(tracks[0]!.readyState).toBe('live')
    fireEvent.click(shutter)
    await screen.findByRole('button', { name: 'Use photo' })
    expect(tracks[0]!.readyState).toBe('ended')
    expect(draws).toBe(1)
    expect(media).toHaveBeenCalledTimes(1)
  })

  it('keeps guide photos out of every store until the observation is queued', async () => {
    const q = await enter()
    await take('A')
    await take('B')
    expect(await q.draftPhotos()).toEqual({})
    expect(await q.queued()).toEqual([])
    expect(screen.getByAltText('Guide photo A, not saved yet')).toBeTruthy()
    expect(
      screen.getByText('Photo B chosen, not saved until queued'),
    ).toBeTruthy()
  })

  it('needs a new explicit start for a retake and keeps the earlier photo if it is cancelled', async () => {
    await enter()
    await take('A')
    fireEvent.click(
      screen.getByRole('button', { name: 'Retake photo A with the guide' }),
    )
    await screen.findByRole('button', { name: 'Start camera' })
    expect(media).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(screen.getByAltText('Guide photo A, not saved yet')).toBeTruthy()
  })

  it('does not ask again after a refusal, and offers the picker', async () => {
    media.mockRejectedValueOnce(
      Object.assign(new Error('x'), { name: 'NotAllowedError' }),
    )
    await enter()
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo A with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    await waitFor(() =>
      expect(
        within(screen.getByRole('dialog')).getByRole('status').textContent,
      ).toContain('not allowed'),
    )
    expect(screen.queryByRole('button', { name: /Start camera/ })).toBeNull()
    expect(
      within(screen.getByRole('dialog')).getByRole('button', {
        name: 'Use the camera or gallery instead',
      }),
    ).toBeTruthy()
    expect(media).toHaveBeenCalledTimes(1)
  })

  it('takes no frame when access is lost before the shutter', async () => {
    await enter()
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo A with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    const shutter = await screen.findByRole('button', { name: 'Take photo A' })
    admitted = false
    fireEvent.click(shutter)
    await waitFor(() => expect(tracks[0]!.readyState).toBe('ended'))
    expect(draws).toBe(0)
    expect(screen.queryByRole('button', { name: 'Use photo' })).toBeNull()
  })

  it('stops the camera when the window is cancelled', async () => {
    await enter()
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo A with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    await screen.findByRole('button', { name: 'Take photo A' })
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(tracks[0]!.readyState).toBe('ended')
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })
})

describe('queueing', () => {
  it('commits one private observation, advances the revision once and clears only the guide', async () => {
    const q = await enter()
    const before = await q.queueRevision()
    await take('A')
    await take('B')
    fillObservation()
    submitObservation()
    await waitFor(async () => expect(await q.queued()).toHaveLength(1))
    const [record] = await q.queued()
    expect(record).toMatchObject({
      collectionMode: 'invited_private',
      ownerUid: 'owner-a',
      claims: { captureMethod: 'camera', ingestPath: 'web' },
    })
    expect(record!.photos.map((photo) => photo.shotType)).toEqual(['A', 'B'])
    expect(Array.from(record!.photos[0]!.bytes)).toEqual(Array.from(jpeg(1)))
    expect(Array.from(record!.photos[1]!.bytes)).toEqual(Array.from(jpeg(2)))
    expect(record!.library).toBeUndefined()
    expect(await q.queueRevision()).toBe(before + 1)
    expect(await q.draftPhotos()).toEqual({})
    await waitFor(() => expect(enterButton()).not.toBeNull())
    expect(
      document.querySelector('.photo-grid input[type="file"]'),
    ).not.toBeNull()
  })

  it('does not refill the next observation after a successful queue', async () => {
    const q = await enter()
    await take('A')
    await take('B')
    fillObservation()
    submitObservation()
    await waitFor(async () => expect(await q.queued()).toHaveLength(1))
    fireEvent.click(await offered())
    await screen.findByRole('button', { name: 'Take photo A with the guide' })
    expect(screen.queryByAltText('Guide photo A, not saved yet')).toBeNull()
    fillObservation()
    submitObservation()
    await waitFor(() => expect(status()).toContain('Add photos A and B'))
    expect(await q.queued()).toHaveLength(1)
  })

  it('queues once when the button is pressed twice', async () => {
    const q = await enter()
    await take('A')
    await take('B')
    fillObservation()
    submitObservation()
    submitObservation()
    await waitFor(async () => expect(await q.queued()).toHaveLength(1))
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 100))
    })
    expect(await q.queued()).toHaveLength(1)
  })

  it("needs photo B, the sampling rules and the person's own acceptance", async () => {
    const q = await enter()
    await take('A')
    fillObservation()
    submitObservation()
    await waitFor(() => expect(status()).toContain('Add photos A and B'))
    await take('B')
    fireEvent.click(
      screen.getByRole('checkbox', { name: /I own these photos/i }),
    )
    submitObservation()
    await waitFor(() =>
      expect(status()).toContain('Accept the contribution terms'),
    )
    expect(await q.queued()).toEqual([])
    expect(screen.getByAltText('Guide photo A, not saved yet')).toBeTruthy()
  })

  it('commits an opted-in private sample with the photos and consumes exactly that draft', async () => {
    const q = await enter()
    await take('A')
    await take('B')
    fireEvent.click(
      await screen.findByRole('checkbox', {
        name: /add a private library sample/i,
      }),
    )
    fireEvent.change(await screen.findByLabelText('Depth top (cm)'), {
      target: { value: '0' },
    })
    fireEvent.change(screen.getByLabelText('Depth bottom (cm)'), {
      target: { value: '5' },
    })
    await waitFor(async () =>
      expect((await q.savedLibraryDraft())?.depthBottom).toBe('5'),
    )
    const draft = (await q.savedLibraryDraft())!
    expect(await q.draftPhotos()).toEqual({})
    fillObservation()
    await waitFor(() =>
      expect(
        (
          screen.getByRole('button', {
            name: /queue observation/i,
          }) as HTMLButtonElement
        ).disabled,
      ).toBe(false),
    )
    submitObservation()
    await waitFor(async () => expect(await q.queued()).toHaveLength(1))
    const [record] = await q.queued()
    expect(record!.submissionId).toBe(draft.submissionId)
    expect(record!.library?.request.sample_id).toBe(draft.sampleId)
    expect(record!.photos).toHaveLength(2)
    expect(await q.savedLibraryDraft()).toBeUndefined()
    expect(await q.draftPhotos()).toEqual({})
  })

  it('holds a private sample with blank depths and invents none', async () => {
    const q = await enter()
    await take('A')
    await take('B')
    fireEvent.click(
      await screen.findByRole('checkbox', {
        name: /add a private library sample/i,
      }),
    )
    await screen.findByLabelText('Depth top (cm)')
    await waitFor(async () => expect(await q.savedLibraryDraft()).toBeDefined())
    fillObservation()
    await waitFor(() =>
      expect(
        (
          screen.getByRole('button', {
            name: /queue observation/i,
          }) as HTMLButtonElement
        ).disabled,
      ).toBe(false),
    )
    submitObservation()
    await waitFor(() => expect(status()).toContain('valid sample depth bounds'))
    expect(await q.queued()).toEqual([])
    expect(screen.getByAltText('Guide photo A, not saved yet')).toBeTruthy()
  })

  it('holds without deleting when a picker photo is saved before the commit', async () => {
    const q = await enter()
    await take('A')
    await take('B')
    await q.saveDraftPhoto(
      'C',
      { bytes: jpeg(7), mimeType: 'image/jpeg', method: 'file' },
      await q.queueRevision(),
      () => true,
    )
    fillObservation()
    submitObservation()
    await waitFor(() => expect(status()).toContain('Nothing was queued yet'))
    expect(await q.queued()).toEqual([])
    expect(Object.keys(await q.draftPhotos())).toEqual(['C'])
  })
})

describe('leaving and losing the guide', () => {
  it('goes back to the picker at once when nothing was chosen', async () => {
    await enter()
    fireEvent.click(
      screen.getByRole('button', { name: 'Use the camera or gallery instead' }),
    )
    await waitFor(() => expect(enterButton()).not.toBeNull())
    expect(
      document.querySelector('.photo-grid input[type="file"]'),
    ).not.toBeNull()
  })

  it('asks before discarding chosen photos, and keeps them when asked to', async () => {
    await enter()
    await take('A')
    fireEvent.click(
      screen.getByRole('button', { name: 'Use the camera or gallery instead' }),
    )
    fireEvent.click(
      await screen.findByRole('button', { name: 'Keep guide photos' }),
    )
    expect(screen.getByAltText('Guide photo A, not saved yet')).toBeTruthy()
    fireEvent.click(
      screen.getByRole('button', { name: 'Use the camera or gallery instead' }),
    )
    fireEvent.click(
      await screen.findByRole('button', { name: 'Discard guide photos' }),
    )
    await waitFor(() => expect(enterButton()).not.toBeNull())
    expect(screen.queryByAltText('Guide photo A, not saved yet')).toBeNull()
  })

  it('stops the camera and hides the photos when the page is hidden, and never restarts by itself', async () => {
    await enter()
    await take('A')
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo B with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    await screen.findByRole('button', { name: 'Take photo B' })
    visibility = 'hidden'
    fireEvent(document, new Event('visibilitychange'))
    expect(tracks[1]!.readyState).toBe('ended')
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(screen.queryByAltText('Guide photo A, not saved yet')).toBeNull()
    visibility = 'visible'
    fireEvent(document, new Event('visibilitychange'))
    fireEvent(window, new Event('focus'))
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 150))
    })
    expect(media).toHaveBeenCalledTimes(2)
    expect(screen.queryByAltText('Guide photo A, not saved yet')).toBeNull()
    fireEvent.click(
      screen.getByRole('button', {
        name: 'Check access and show guide photos',
      }),
    )
    expect(
      await screen.findByAltText('Guide photo A, not saved yet'),
    ).toBeTruthy()
    expect(media).toHaveBeenCalledTimes(2)
  })

  it('discards held photos if the account is no longer admitted on return', async () => {
    await enter()
    await take('A')
    fireEvent(window, new Event('pagehide'))
    admitted = false
    fireEvent.click(
      await screen.findByRole('button', {
        name: 'Check access and show guide photos',
      }),
    )
    await waitFor(() =>
      expect(status()).toContain('guide photos were discarded'),
    )
    expect(
      screen.queryByRole('button', { name: 'Take photo A with the guide' }),
    ).toBeNull()
  })

  it('discards the guide when the sign-in changes', async () => {
    await enter()
    await take('A')
    act(() => notify())
    await waitFor(() =>
      expect(status()).toContain('guide photos were discarded'),
    )
    expect(screen.queryByAltText('Guide photo A, not saved yet')).toBeNull()
  })

  it('discards the guide when the device queue changes underneath it', async () => {
    const q = await enter()
    await take('A')
    await q.clearQueue()
    await waitFor(
      () => expect(status()).toContain('guide photos were discarded'),
      {
        timeout: 4_000,
      },
    )
    expect(screen.queryByAltText('Guide photo A, not saved yet')).toBeNull()
  })
})

describe('review findings', () => {
  const pause = (ms: number) =>
    act(async () => {
      await new Promise((resolve) => setTimeout(resolve, ms))
    })

  it('frees the session when the frame cannot be copied, so the guide still works', async () => {
    const q = await enter()
    await take('A')
    await take('B')
    vi.mocked(HTMLCanvasElement.prototype.getContext).mockReturnValueOnce(null)
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo C with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Take photo C' }))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Start camera again' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Take photo C' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Use photo' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    fillObservation()
    submitObservation()
    await waitFor(async () => expect(await q.queued()).toHaveLength(1))
    expect((await q.queued())[0]!.photos).toHaveLength(3)
  })

  it('never turns the camera on for a window that was cancelled and reopened', async () => {
    await enter()
    let release!: () => void
    const slow = new Promise<void>((resolve) => {
      release = resolve
    })
    const client = mocks.create.mock.results[0]!.value as {
      auth: { getUser: () => Promise<unknown> }
    }
    const getUser = client.auth.getUser
    client.auth.getUser = async () => {
      await slow
      return getUser()
    }
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo A with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo A with the guide' }),
    )
    await screen.findByRole('button', { name: 'Start camera' })
    client.auth.getUser = getUser
    release()
    await pause(150)
    expect(media).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Start camera' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Start camera' }))
    await screen.findByRole('button', { name: 'Take photo A' })
    expect(media).toHaveBeenCalledTimes(1)
  })

  it('stops a stream that arrives after the window was cancelled', async () => {
    let grant!: (stream: MediaStream) => void
    media.mockImplementationOnce(
      () =>
        new Promise<MediaStream>((resolve) => {
          grant = resolve
        }),
    )
    await enter()
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo A with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    await waitFor(() => expect(media).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    const late = new Track()
    grant({ getTracks: () => [late] } as unknown as MediaStream)
    await pause(50)
    expect(late.readyState).toBe('ended')
    await take('A')
    expect(media).toHaveBeenCalledTimes(2)
  })

  it('keeps the guide when the sign-in library repeats the same owner, and checks access again', async () => {
    await enter()
    await take('A')
    act(() =>
      (notify as unknown as (event: string, session: unknown) => void)(
        'SIGNED_IN',
        { user: { id: 'owner-a' } },
      ),
    )
    await pause(100)
    expect(screen.getByAltText('Guide photo A, not saved yet')).toBeTruthy()
    admitted = false
    act(() =>
      (notify as unknown as (event: string, session: unknown) => void)(
        'TOKEN_REFRESHED',
        { user: { id: 'owner-a' } },
      ),
    )
    await waitFor(() =>
      expect(status()).toContain('guide photos were discarded'),
    )
  })

  it('discards the guide when the sign-in event names another owner', async () => {
    await enter()
    await take('A')
    act(() =>
      (notify as unknown as (event: string, session: unknown) => void)(
        'SIGNED_IN',
        { user: { id: 'owner-b' } },
      ),
    )
    await waitFor(() =>
      expect(status()).toContain('guide photos were discarded'),
    )
  })

  it('discards the guide when access is lost, found by the periodic check', async () => {
    await enter()
    await take('A')
    admitted = false
    await waitFor(
      () => expect(status()).toContain('guide photos were discarded'),
      {
        timeout: 8_000,
      },
    )
  }, 12_000)

  it('ends the guide and stops the camera before a rights request', async () => {
    await enter()
    await take('A')
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo B with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    await screen.findByRole('button', { name: 'Take photo B' })
    fireEvent.click(
      screen.getByRole('button', { name: /withdraw my contributions/i }),
    )
    fireEvent.change(screen.getByLabelText(/to confirm/i), {
      target: { value: 'WITHDRAW' },
    })
    fireEvent.click(screen.getByRole('button', { name: /confirm withdrawal/i }))
    await waitFor(() => expect(tracks[1]!.readyState).toBe('ended'))
    await waitFor(() =>
      expect(
        screen.queryByRole('button', { name: 'Take photo A with the guide' }),
      ).toBeNull(),
    )
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('ends the guide when the page moves to the rights view', async () => {
    await enter()
    await take('A')
    act(() => {
      window.history.replaceState(null, '', '/#your-data')
      window.dispatchEvent(new Event('hashchange'))
    })
    await waitFor(() =>
      expect(
        screen.queryByRole('button', { name: 'Take photo A with the guide' }),
      ).toBeNull(),
    )
    expect(media).toHaveBeenCalledTimes(1)
  })

  it('stops the camera when the app is closed', async () => {
    await enter()
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo A with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    await screen.findByRole('button', { name: 'Take photo A' })
    cleanup()
    expect(tracks[0]!.readyState).toBe('ended')
  })

  it('reports a camera that stops by itself and needs a new start', async () => {
    await enter()
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo A with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    await screen.findByRole('button', { name: 'Take photo A' })
    act(() => {
      tracks[0]!.dispatchEvent(new Event('ended'))
    })
    expect(
      await screen.findByRole('button', { name: 'Start camera again' }),
    ).toBeTruthy()
    expect(media).toHaveBeenCalledTimes(1)
  })

  it('waits for a picker photo that is still being read before entering', async () => {
    const q = await start()
    const entry = await offered()
    let finish!: (buffer: ArrayBuffer) => void
    const file = new File([jpeg(9)], 'a.jpg', { type: 'image/jpeg' })
    file.arrayBuffer = () =>
      new Promise<ArrayBuffer>((resolve) => {
        finish = resolve
      })
    fireEvent.change(screen.getByLabelText(/A · Context/), {
      target: { files: [file] },
    })
    await waitFor(() => expect(finish).toBeDefined())
    fireEvent.click(entry)
    await waitFor(() => expect(status()).toContain('cannot start yet'))
    expect(
      screen.queryByRole('button', { name: 'Take photo A with the guide' }),
    ).toBeNull()
    finish(jpeg(9).buffer)
    await waitFor(async () =>
      expect(Object.keys(await q.draftPhotos())).toEqual(['A']),
    )
  })

  it('keeps the entry button off until the drafts have been restored', async () => {
    const { App } = await import('../src/App')
    render(<App />)
    const entry = (await screen.findByRole('button', {
      name: 'Use the optional framing guide',
    })) as HTMLButtonElement
    const disabledAtFirst = entry.disabled
    await waitFor(() => expect(entry.disabled).toBe(false))
    expect(disabledAtFirst).toBe(true)
  })

  it('refuses a photo that would take the guide past its memory bound', async () => {
    const big = (tag: number) => {
      const bytes = new Uint8Array(9 * 1024 * 1024)
      bytes.set(jpeg(tag))
      return bytes
    }
    vi.mocked(HTMLCanvasElement.prototype.toBlob).mockImplementation(
      (done: BlobCallback) =>
        done(new Blob([big((frames += 1))], { type: 'image/jpeg' })),
    )
    await enter()
    await take('A')
    await take('B')
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo C with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Take photo C' }))
    await waitFor(() =>
      expect(
        within(screen.getByRole('dialog')).getByRole('status').textContent,
      ).toContain('could not be prepared'),
    )
    expect(screen.queryByRole('button', { name: 'Use photo' })).toBeNull()
  }, 20_000)

  it('finishes with the same observation when the first commit result is lost', async () => {
    wrapQueue()
    const q = await enter()
    const before = await q.queueRevision()
    await take('A')
    await take('B')
    fillObservation()
    mocks.loseCommitResult = true
    submitObservation()
    await waitFor(() =>
      expect(status()).toContain('could not be saved on this device'),
    )
    expect(await q.queued()).toHaveLength(1)
    const [first] = await q.queued()
    // The frozen observation cannot be edited: its photos are shown but cannot be retaken.
    expect(
      (
        screen.getByRole('button', {
          name: 'Retake photo A with the guide',
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true)
    submitObservation()
    await waitFor(() => expect(enterButton()).not.toBeNull())
    const after = await q.queued()
    expect(after).toHaveLength(1)
    expect(after[0]!.submissionId).toBe(first!.submissionId)
    expect(after[0]!.grantId).toBe(first!.grantId)
    expect(await q.queueRevision()).toBe(before + 1)
  })

  it('leaves a draft another tab starts after the commit alone', async () => {
    const q = await enter()
    await take('A')
    await take('B')
    fillObservation()
    submitObservation()
    await waitFor(async () => expect(await q.queued()).toHaveLength(1))
    await q.saveDraftPhoto(
      'A',
      { bytes: jpeg(5), mimeType: 'image/jpeg', method: 'file' },
      await q.queueRevision(),
      () => true,
    )
    await pause(300)
    expect(Object.keys(await q.draftPhotos())).toEqual(['A'])
  })

  it('hides the draft discard button while the guide is on', async () => {
    await start()
    const entry = await offered()
    expect(
      screen.getByRole('button', {
        name: 'Discard draft photos and private sample',
      }),
    ).toBeTruthy()
    fireEvent.click(entry)
    await screen.findByRole('button', { name: 'Take photo A with the guide' })
    expect(
      screen.queryByRole('button', {
        name: 'Discard draft photos and private sample',
      }),
    ).toBeNull()
  })

  it('turns the camera off when the account cannot be confirmed, and keeps chosen photos for a later check', async () => {
    await enter()
    await take('A')
    fireEvent.click(
      screen.getByRole('button', { name: 'Take photo B with the guide' }),
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Start camera' }))
    const shutter = await screen.findByRole('button', { name: 'Take photo B' })
    const client = mocks.create.mock.results[0]!.value as {
      auth: { getUser: () => Promise<unknown> }
    }
    const getUser = client.auth.getUser
    client.auth.getUser = async () => {
      throw new Error('offline')
    }
    fireEvent.click(shutter)
    await waitFor(() => expect(tracks[1]!.readyState).toBe('ended'))
    expect(draws).toBe(1)
    expect(screen.queryByRole('button', { name: 'Use photo' })).toBeNull()
    client.auth.getUser = getUser
    fireEvent(window, new Event('focus'))
    fireEvent.click(
      await screen.findByRole('button', {
        name: 'Check access and show guide photos',
      }),
    )
    expect(
      await screen.findByAltText('Guide photo A, not saved yet'),
    ).toBeTruthy()
    expect(media).toHaveBeenCalledTimes(2)
  })

  it('stays held and resumable after a check with no answer and a repeated sign-in event', async () => {
    await enter()
    await take('A')
    const client = mocks.create.mock.results[0]!.value as {
      auth: { getUser: () => Promise<unknown> }
    }
    const getUser = client.auth.getUser
    client.auth.getUser = async () => {
      throw new Error('offline')
    }
    fireEvent(window, new Event('focus'))
    await waitFor(() => expect(status()).toContain('could not be confirmed'))
    client.auth.getUser = getUser
    act(() =>
      (notify as unknown as (event: string, session: unknown) => void)(
        'SIGNED_IN',
        { user: { id: 'owner-a' } },
      ),
    )
    fireEvent.click(
      await screen.findByRole('button', {
        name: 'Check access and show guide photos',
      }),
    )
    expect(
      await screen.findByAltText('Guide photo A, not saved yet'),
    ).toBeTruthy()
    expect(status()).not.toContain('discarded')
  })

  it('finds out by itself when a held guide can be confirmed again', async () => {
    await enter()
    await take('A')
    const client = mocks.create.mock.results[0]!.value as {
      auth: { getUser: () => Promise<unknown> }
    }
    const getUser = client.auth.getUser
    client.auth.getUser = async () => {
      throw new Error('offline')
    }
    fireEvent(window, new Event('focus'))
    await waitFor(() => expect(status()).toContain('could not be confirmed'))
    client.auth.getUser = getUser
    // No focus and no sign-in event: only the guide's own check brings the form back.
    const resume = await screen.findByRole(
      'button',
      { name: 'Check access and show guide photos' },
      { timeout: 9_000 },
    )
    expect(screen.queryByAltText('Guide photo A, not saved yet')).toBeNull()
    fireEvent.click(resume)
    expect(
      await screen.findByAltText('Guide photo A, not saved yet'),
    ).toBeTruthy()
  }, 15_000)

  it('leaves a held guide and its discard confirmation alone on each periodic check', async () => {
    await enter()
    await take('A')
    fireEvent(window, new Event('pagehide'))
    fireEvent.click(
      await screen.findByRole('button', {
        name: 'Use the camera or gallery instead',
      }),
    )
    const keep = await screen.findByRole('button', {
      name: 'Keep guide photos',
    })
    await pause(5_600)
    expect(keep.isConnected).toBe(true)
    expect(
      screen.getByRole('button', {
        name: 'Check access and show guide photos',
      }),
    ).toBeTruthy()
    expect(screen.queryByAltText('Guide photo A, not saved yet')).toBeNull()
  }, 12_000)

  it('reads the device revision on a timer only while a guide is on', async () => {
    wrapQueue()
    await start()
    await offered()
    await pause(300)
    const idle = mocks.revisionReads
    await pause(1_300)
    expect(mocks.revisionReads).toBe(idle)
    fireEvent.click(await offered())
    await screen.findByRole('button', { name: 'Take photo A with the guide' })
    const entered = mocks.revisionReads
    await pause(1_300)
    expect(mocks.revisionReads).toBeGreaterThan(entered)
  }, 10_000)
})
