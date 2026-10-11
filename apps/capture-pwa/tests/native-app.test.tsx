import 'fake-indexeddb/auto'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CLIENT_VERSION } from '../src/provenance'
import { queued, removeQueued } from '../src/queue'

const JPEG = new Uint8Array([0xff, 0xd8, 0xff, 0xe1, 0x00, 0x10, 0x45, 0x78])

const mocks = vi.hoisted(() => ({
  chooseFromGallery: vi.fn(),
  getCurrentPosition: vi.fn(),
  submitQueued: vi.fn(async (): Promise<void> => undefined),
  takePhoto: vi.fn(),
}))

vi.mock('@capacitor/camera', () => ({
  Camera: {
    chooseFromGallery: mocks.chooseFromGallery,
    takePhoto: mocks.takePhoto,
  },
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
  Capacitor?: { isNativePlatform: () => boolean }
}

beforeEach(async () => {
  ;(globalThis as CapacitorWindow).Capacitor = { isNativePlatform: () => true }
  vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JPEG, { status: 200 })),
  )
  mocks.takePhoto.mockReset()
  mocks.takePhoto.mockResolvedValue({
    type: 0,
    saved: false,
    webPath: 'https://localhost/_capacitor_file_/shot.jpg',
  })
  mocks.chooseFromGallery.mockReset()
  mocks.getCurrentPosition.mockReset()
  mocks.getCurrentPosition.mockResolvedValue({
    timestamp: 0,
    coords: { latitude: 44.4759, longitude: -73.2121, accuracy: 4.6 },
  })
  mocks.submitQueued.mockReset()
  mocks.submitQueued.mockResolvedValue(undefined)
  for (const record of await queued()) await removeQueued(record.submissionId)
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
})

async function take(shot: 'A' | 'B') {
  const button = await screen.findByRole('button', {
    name: `Take photo ${shot}`,
  })
  await waitFor(() => expect(button.hasAttribute('disabled')).toBe(false))
  fireEvent.click(button)
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

describe('the phone app (WP-APP-1)', () => {
  it('captures with the native camera and location and sends them as the app', async () => {
    const { container } = render(<App />)
    // No browser file inputs inside the app: the native camera takes the photos.
    expect(container.querySelectorAll('input[type="file"]')).toHaveLength(0)
    await take('A')
    await take('B')
    fireEvent.click(
      screen.getByRole('button', { name: /use my current location/i }),
    )
    expect(await screen.findByText(/accuracy ±5 m/i)).toBeDefined()
    describeAndSubmit()

    await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(1))
    const [, record] = mocks.submitQueued.mock.calls[0] as unknown as [
      unknown,
      Record<string, unknown>,
    ]
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
  })

  it('requires photos A and B before queueing', async () => {
    render(<App />)
    await take('A')
    fireEvent.change(screen.getByLabelText('Latitude'), {
      target: { value: '44.4759' },
    })
    fireEvent.change(screen.getByLabelText('Longitude'), {
      target: { value: '-73.2121' },
    })
    describeAndSubmit()
    expect(
      await screen.findByText('Add photos A and B before continuing.'),
    ).toBeDefined()
    expect(mocks.submitQueued).not.toHaveBeenCalled()
  })

  it('says what to do when the camera is refused', async () => {
    mocks.takePhoto.mockRejectedValue(
      Object.assign(new Error('denied'), { code: 'OS-PLUG-CAMR-0003' }),
    )
    render(<App />)
    const button = await screen.findByRole('button', { name: 'Take photo A' })
    await waitFor(() => expect(button.hasAttribute('disabled')).toBe(false))
    fireEvent.click(button)
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
