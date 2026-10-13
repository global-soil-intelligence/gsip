import 'fake-indexeddb/auto'
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CLIENT_VERSION } from '../src/provenance'
import { clearDraftPhotos, queued, removeQueued } from '../src/queue'

const JPEG = new Uint8Array([0xff, 0xd8, 0xff, 0xe1, 0x00, 0x10, 0x45, 0x78])
const OUTPUT =
  'file:///data/user/0/com.globalsoilintelligence.app/cache/PIC.jpg'

const mocks = vi.hoisted(() => ({
  deleteFile: vi.fn(async () => undefined),
  getCurrentPosition: vi.fn(),
  submitQueued: vi.fn(async (): Promise<void> => undefined),
  takePhoto: vi.fn(),
}))

vi.mock('@capacitor/camera', () => ({
  Camera: { takePhoto: mocks.takePhoto },
}))
vi.mock('@capacitor/filesystem', () => ({
  Filesystem: { deleteFile: mocks.deleteFile },
}))
vi.mock('@capacitor/geolocation', () => ({
  Geolocation: { getCurrentPosition: mocks.getCurrentPosition },
}))
vi.mock('../src/supabase', () => ({
  createGsipClient: () => ({ hosted: true }),
  existingContributor: async () => null,
  fetchServiceState: async () => 'open',
  isServiceConfigured: () => true,
  recordOwner: async () => undefined,
  sendSignInLink: async () => 'sent',
  latestDeletionRequest: async () => null,
  requestDeletion: async () => 'requested',
  submitQueued: mocks.submitQueued,
}))

import { App } from '../src/App'

type CapacitorWindow = typeof globalThis & {
  Capacitor?: { getPlatform: () => string; isNativePlatform: () => boolean }
}

function runInApp(os: 'android' | 'ios') {
  ;(globalThis as CapacitorWindow).Capacitor = {
    getPlatform: () => os,
    isNativePlatform: () => true,
  }
}

beforeEach(async () => {
  runInApp('ios')
  vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JPEG, { status: 200 })),
  )
  mocks.takePhoto.mockReset()
  mocks.takePhoto.mockResolvedValue({
    type: 0,
    saved: false,
    uri: OUTPUT,
    webPath: 'https://localhost/_capacitor_file_/PIC.jpg',
  })
  mocks.deleteFile.mockClear()
  mocks.getCurrentPosition.mockReset()
  mocks.getCurrentPosition.mockResolvedValue({
    timestamp: 0,
    coords: { latitude: 44.4759, longitude: -73.2121, accuracy: 4.6 },
  })
  mocks.submitQueued.mockReset()
  mocks.submitQueued.mockResolvedValue(undefined)
  for (const record of await queued()) await removeQueued(record.submissionId)
  await clearDraftPhotos()
  Object.defineProperty(window.navigator, 'onLine', {
    configurable: true,
    value: true,
  })
})

afterEach(() => {
  cleanup()
  delete (globalThis as CapacitorWindow).Capacitor
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

async function takeButton(shot: 'A' | 'B') {
  const button = await screen.findByRole('button', {
    name: new RegExp(`^(Re)?[Tt]ake photo ${shot}$`),
  })
  await waitFor(() => expect(button.hasAttribute('disabled')).toBe(false))
  return button
}

async function take(shot: 'A' | 'B') {
  fireEvent.click(await takeButton(shot))
  expect(await screen.findByText(`Photo ${shot} ready`)).toBeDefined()
}

function describeAndSubmit() {
  fireEvent.change(screen.getByLabelText('Land cover'), {
    target: { value: 'cropland' },
  })
  fireEvent.change(screen.getByLabelText('Surface condition'), {
    target: { value: 'moist' },
  })
  fireEvent.click(screen.getByRole('checkbox', { name: /sampling rules/i }))
  fireEvent.click(screen.getByRole('checkbox', { name: /I own these photos/i }))
  fireEvent.submit(
    screen.getByRole('button', { name: /queue observation/i }).closest('form')!,
  )
}

function typeLocation() {
  fireEvent.change(screen.getByLabelText('Latitude'), {
    target: { value: '44.4759' },
  })
  fireEvent.change(screen.getByLabelText('Longitude'), {
    target: { value: '-73.2121' },
  })
}

async function queuedRecord(): Promise<Record<string, unknown>> {
  await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(1))
  const [, record] = mocks.submitQueued.mock.calls[0] as unknown as [
    unknown,
    Record<string, unknown>,
  ]
  return record
}

describe('the phone app (WP-APP-1)', () => {
  it('captures with the native camera and Core Location and sends them as the app', async () => {
    const { container } = render(<App />)
    // No camera-capture inputs inside the app: the native camera takes the photos.
    expect(container.querySelectorAll('input[capture]')).toHaveLength(0)
    await take('A')
    await take('B')
    fireEvent.click(
      screen.getByRole('button', { name: /use my current location/i }),
    )
    expect(await screen.findByText(/accuracy ±5 m/i)).toBeDefined()
    describeAndSubmit()

    const record = await queuedRecord()
    expect(record).toMatchObject({
      accuracyM: 5,
      claims: {
        captureMethod: 'camera',
        clientVersion: CLIENT_VERSION,
        ingestPath: 'app',
        locationSource: 'device_gps',
      },
      latitude: 44.4759,
      longitude: -73.2121,
    })
    // The queue stores the photos through IndexedDB, so compare their bytes by value.
    const photos = record.photos as Array<{
      bytes: Uint8Array
      mimeType: string
      shotType: string
    }>
    expect(
      photos.map(({ bytes, mimeType, shotType }) => ({
        bytes: Array.from(bytes),
        mimeType,
        shotType,
      })),
    ).toEqual([
      { bytes: Array.from(JPEG), mimeType: 'image/jpeg', shotType: 'A' },
      { bytes: Array.from(JPEG), mimeType: 'image/jpeg', shotType: 'B' },
    ])
    expect(mocks.takePhoto).toHaveBeenCalledWith(
      expect.objectContaining({ saveToGallery: false }),
    )
    // The plugin's own copy of each photo is deleted once read.
    expect(mocks.deleteFile).toHaveBeenCalledWith({ path: OUTPUT })
    expect(mocks.deleteFile).toHaveBeenCalledTimes(2)
  })

  it('dates the observation by shot B, the moment the camera returned it', async () => {
    const now = Date.now()
    const tookA = now - 10 * 60_000
    const tookB = now - 4 * 60_000
    render(<App />)
    const clock = vi.spyOn(Date, 'now').mockReturnValue(tookA)
    await take('A')
    clock.mockReturnValue(tookB)
    await take('B')
    clock.mockRestore()
    typeLocation()
    describeAndSubmit()
    expect((await queuedRecord()).capturedAt).toBe(
      new Date(tookB).toISOString(),
    )
  })

  it('uses the web view’s location in the Android app', async () => {
    runInApp('android')
    Object.defineProperty(window.navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition: (success: PositionCallback) =>
          success({
            coords: { accuracy: 8.2, latitude: 44.48, longitude: -73.21 },
          } as GeolocationPosition),
      },
    })
    render(<App />)
    await takeButton('A')
    fireEvent.click(
      screen.getByRole('button', { name: /use my current location/i }),
    )
    expect(await screen.findByText(/accuracy ±8 m/i)).toBeDefined()
    expect(mocks.getCurrentPosition).not.toHaveBeenCalled()
  })

  it('takes a saved photo through the system picker, claimed as a file', async () => {
    render(<App />)
    await takeButton('A')
    const saved = new File([JPEG], 'soil.jpg', {
      type: 'image/jpeg',
      lastModified: Date.parse('2026-01-01T00:00:00Z'),
    })
    for (const shot of ['A', 'B']) {
      fireEvent.change(screen.getByLabelText(`Use a saved photo for ${shot}`), {
        target: { files: [saved] },
      })
      expect(await screen.findByText(`Photo ${shot} ready`)).toBeDefined()
    }
    typeLocation()
    describeAndSubmit()
    expect(await queuedRecord()).toMatchObject({
      claims: expect.objectContaining({
        captureMethod: 'file',
        ingestPath: 'app',
        locationSource: 'manual_pin',
      }),
    })
    expect(mocks.takePhoto).not.toHaveBeenCalled()
  })

  it('requires photos A and B before queueing', async () => {
    render(<App />)
    await take('A')
    typeLocation()
    describeAndSubmit()
    expect(
      await screen.findByText('Add photos A and B before continuing.'),
    ).toBeDefined()
    expect(mocks.submitQueued).not.toHaveBeenCalled()
  })

  it('keeps taken photos across a restart until they are queued or discarded', async () => {
    render(<App />)
    await take('A')
    cleanup()

    render(<App />)
    expect(await screen.findByText('Photo A ready')).toBeDefined()
    expect(screen.getByText('No photo B yet')).toBeDefined()
    fireEvent.click(
      screen.getByRole('button', { name: 'Discard these photos' }),
    )
    expect(await screen.findByText('No photo A yet')).toBeDefined()
    cleanup()

    render(<App />)
    await takeButton('A')
    await waitFor(() =>
      expect(screen.getByText('No photo A yet')).toBeDefined(),
    )
  })

  it('never locks up on a camera call that does not return', async () => {
    mocks.takePhoto.mockReturnValueOnce(new Promise(() => undefined))
    render(<App />)
    fireEvent.click(await takeButton('A'))
    expect(await screen.findByText(/opening the camera/i)).toBeDefined()
    // The person can simply try again, and the stalled call can never overwrite the result.
    await take('A')
  })

  it('says what to do when the camera is refused', async () => {
    mocks.takePhoto.mockRejectedValue(
      Object.assign(new Error('denied'), { code: 'OS-PLUG-CAMR-0003' }),
    )
    render(<App />)
    fireEvent.click(await takeButton('A'))
    expect(
      await screen.findByText(/camera access is off for GSIP/i),
    ).toBeDefined()
    expect(screen.queryByText('Photo A ready')).toBeNull()
  })

  it('links to the public site and leaves e-mail sign-in for a later version', () => {
    render(<App />)
    expect(
      screen
        .getByRole('link', { name: 'GSIP public map' })
        .getAttribute('href'),
    ).toBe('https://globalsoilintelligence.com/map/')
    expect(
      screen
        .getByRole('link', { name: /printable A6 card/i })
        .getAttribute('href'),
    ).toBe(
      'https://globalsoilintelligence.com/reference-card/gsip-reference-card-v1-color.pdf',
    )
    expect(screen.queryByRole('button', { name: /magic link/i })).toBeNull()
    expect(screen.getByText(/later version of the app/i)).toBeDefined()
  })
})

it('a later saved shot B supersedes a pending camera result for the same shot', async () => {
  const { draftPhotos } = await import('../src/queue')
  let finish: ((value: unknown) => void) | undefined
  mocks.takePhoto.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve
      }),
  )
  render(<App />)
  fireEvent.click(await takeButton('B'))
  await waitFor(() => expect(mocks.takePhoto).toHaveBeenCalledOnce())
  const selected = new File([JPEG], 'newer.jpg', {
    type: 'image/jpeg',
    lastModified: 1,
  })
  fireEvent.change(screen.getByLabelText('Use a saved photo for B'), {
    target: { files: [selected] },
  })
  await waitFor(async () =>
    expect((await draftPhotos()).B?.method).toBe('file'),
  )
  finish!({
    type: 0,
    saved: false,
    uri: OUTPUT,
    webPath: 'https://localhost/_capacitor_file_/PIC.jpg',
  })
  await waitFor(() => expect(mocks.deleteFile).toHaveBeenCalledOnce())
  await waitFor(async () =>
    expect((await draftPhotos()).B?.method).toBe('file'),
  )
})

it('a later camera shot B supersedes a pending saved-file read for the same shot', async () => {
  const { draftPhotos } = await import('../src/queue')
  let finish: ((value: ArrayBuffer) => void) | undefined
  const selected = new File([JPEG], 'older.jpg', {
    type: 'image/jpeg',
    lastModified: 1,
  })
  const read = vi.spyOn(selected, 'arrayBuffer').mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve
      }),
  )
  render(<App />)
  await takeButton('B')
  fireEvent.change(screen.getByLabelText('Use a saved photo for B'), {
    target: { files: [selected] },
  })
  await waitFor(() => expect(read).toHaveBeenCalledOnce())
  await take('B')
  await waitFor(async () =>
    expect((await draftPhotos()).B?.method).toBe('camera'),
  )
  await act(async () => {
    finish!(JPEG.buffer)
  })
  await waitFor(async () =>
    expect((await draftPhotos()).B?.method).toBe('camera'),
  )
})
