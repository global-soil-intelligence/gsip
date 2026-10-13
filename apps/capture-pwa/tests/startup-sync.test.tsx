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
import { enqueue, queued, removeQueued } from '../src/queue'
import type { QueueRecord } from '../src/types'

const mocks = vi.hoisted(() => ({
  fetchServiceState: vi.fn(
    async (): Promise<'open' | 'closed' | 'unknown'> => 'open',
  ),
  submitQueued: vi.fn(async (): Promise<void> => undefined),
}))

vi.mock('../src/supabase', () => ({
  createGsipClient: () => ({ hosted: true }),
  existingContributor: async () => null,
  fetchServiceState: mocks.fetchServiceState,
  isServiceConfigured: () => true,
  recordOwner: async () => undefined,
  sendSignInLink: async () => 'sent',
  latestDeletionRequest: async () => null,
  requestDeletion: async () => 'requested',
  submitQueued: mocks.submitQueued,
}))

import { App } from '../src/App'

const record: QueueRecord = {
  accuracyM: 7,
  attributionName: 'Startup contributor',
  capturedAt: '2026-07-23T00:00:00Z',
  deviceModel: 'test device',
  disturbed: false,
  grantId: 'startup-grant',
  landCover: 'cropland',
  latitude: 40.446,
  longitude: -79.982,
  photos: [],
  queuedAt: '2026-07-23T00:00:00Z',
  submissionId: 'startup-submission',
  surfaceCondition: 'moist',
  termsVersion: '2026-07-22-v1',
}

describe('capture retry behavior', () => {
  beforeEach(async () => {
    vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
    mocks.fetchServiceState.mockReset()
    mocks.fetchServiceState.mockResolvedValue('open')
    mocks.submitQueued.mockReset()
    mocks.submitQueued.mockResolvedValue(undefined)
    for (const queuedRecord of await queued()) {
      await removeQueued(queuedRecord.submissionId)
    }
    Object.defineProperty(window.navigator, 'onLine', {
      configurable: true,
      value: true,
    })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
  })

  it('syncs a queued observation when the app opens already online', async () => {
    await enqueue(record)
    render(<App />)

    await waitFor(() =>
      expect(mocks.submitQueued).toHaveBeenCalledWith({ hosted: true }, record),
    )
    expect(await screen.findByText(/1 observation synced/i)).toBeDefined()
  })

  it('pauses sync and keeps the observation queued while the database closes capture', async () => {
    mocks.fetchServiceState.mockResolvedValue('closed')
    await enqueue(record)
    render(<App />)

    expect(await screen.findAllByText(/capture is paused/i)).not.toHaveLength(0)
    expect(screen.getByText('1 queued')).toBeDefined()
    expect(mocks.submitQueued).not.toHaveBeenCalled()
  })

  it('resumes without a reload once the database reopens capture', async () => {
    mocks.fetchServiceState
      .mockResolvedValueOnce('closed')
      .mockResolvedValueOnce('closed')
      .mockResolvedValue('open')
    await enqueue(record)
    render(<App />)
    expect(await screen.findAllByText(/capture is paused/i)).not.toHaveLength(0)
    expect(mocks.submitQueued).not.toHaveBeenCalled()

    act(() => {
      window.dispatchEvent(new Event('online'))
    })
    await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(1))
  })

  it('still syncs when the capture state cannot be read', async () => {
    mocks.fetchServiceState.mockResolvedValue('unknown')
    await enqueue(record)
    render(<App />)

    await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(1))
  })

  it('stays idle when the online queue is empty', async () => {
    render(<App />)

    await waitFor(() =>
      expect(
        screen.getByText(/ready for your first observation/i),
      ).toBeDefined(),
    )
    expect(
      screen.queryByText(/securely syncing queued observations/i),
    ).toBeNull()
    expect(mocks.submitQueued).not.toHaveBeenCalled()
  })

  it('coalesces concurrent sync triggers into one send per record', async () => {
    let release: (() => void) | undefined
    mocks.submitQueued.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          release = resolve
        }),
    )
    await enqueue(record)
    render(<App />)
    await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(1))

    act(() => {
      window.dispatchEvent(new Event('online'))
      window.dispatchEvent(new Event('online'))
    })
    expect(mocks.submitQueued).toHaveBeenCalledTimes(1)

    act(() => release?.())
    expect(await screen.findByText(/1 observation synced/i)).toBeDefined()
  })

  it('runs exactly one follow-up drain for triggers that arrive mid-drain', async () => {
    let release: (() => void) | undefined
    mocks.submitQueued.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          release = resolve
        }),
    )
    await enqueue(record)
    render(<App />)
    await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(1))

    // Queued after the running drain listed its records, so only a follow-up drain can send it.
    const second = { ...record, submissionId: 'mid-drain-submission' }
    await enqueue(second)
    act(() => {
      for (let trigger = 0; trigger < 3; trigger += 1)
        window.dispatchEvent(new Event('online'))
    })
    act(() => release?.())

    await waitFor(() =>
      expect(mocks.submitQueued).toHaveBeenLastCalledWith(
        { hosted: true },
        second,
      ),
    )
    expect(mocks.submitQueued).toHaveBeenCalledTimes(2)
    // Startup read, first drain, one follow-up: three triggers did not cause three drains.
    await waitFor(() =>
      expect(screen.getByText(/1 observation synced/i)).toBeDefined(),
    )
    expect(mocks.fetchServiceState).toHaveBeenCalledTimes(3)
  })

  it('sends nothing more once the app has closed', async () => {
    let release: (() => void) | undefined
    mocks.submitQueued.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          release = resolve
        }),
    )
    await enqueue(record)
    const { unmount } = render(<App />)
    await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(1))

    // A trigger mid-drain schedules a follow-up drain. The app then closes, and a record queued
    // afterwards is for whichever screen opens next to send, never the closed one.
    act(() => {
      window.dispatchEvent(new Event('online'))
    })
    unmount()
    const later = { ...record, submissionId: 'queued-after-closing' }
    await enqueue(later)
    await act(async () => release?.())

    await waitFor(async () =>
      expect((await queued()).map((item) => item.submissionId)).toEqual([
        later.submissionId,
      ]),
    )
    // Room for the follow-up drain the closed screen must not run.
    await new Promise((resolve) => setTimeout(resolve, 150))
    expect(mocks.submitQueued).toHaveBeenCalledTimes(1)
    expect((await queued()).map((item) => item.submissionId)).toEqual([
      later.submissionId,
    ])
  })

  it('shows a recovery action for a dead-lettered observation', async () => {
    await enqueue({
      ...record,
      deadLetteredAt: '2026-07-23T01:00:00Z',
      syncAttempts: 5,
    })
    render(<App />)

    expect(
      await screen.findByRole('button', {
        name: /retry failed observations/i,
      }),
    ).toBeDefined()
    expect(screen.getByText(/1 needs attention/i)).toBeDefined()
    expect(mocks.submitQueued).not.toHaveBeenCalled()
  })

  it('rejects a non-JPEG gallery file with a visible recovery message', async () => {
    render(<App />)
    const png = new File(['png'], 'soil.png', { type: 'image/png' })
    fireEvent.change(screen.getByLabelText(/A · Context/i), {
      target: { files: [png] },
    })
    fireEvent.change(screen.getByLabelText(/B · Fresh face/i), {
      target: { files: [png] },
    })
    fireEvent.change(screen.getByLabelText('Latitude'), {
      target: { value: '40.446' },
    })
    fireEvent.change(screen.getByLabelText('Longitude'), {
      target: { value: '-79.982' },
    })
    fireEvent.change(screen.getByLabelText('Land cover'), {
      target: { value: 'cropland' },
    })
    fireEvent.change(screen.getByLabelText('Surface condition'), {
      target: { value: 'moist' },
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /sampling rules/i }))
    fireEvent.click(
      screen.getByRole('checkbox', { name: /I own these photos/i }),
    )
    fireEvent.submit(
      screen
        .getByRole('button', { name: /queue observation/i })
        .closest('form')!,
    )

    expect(await screen.findByText(/choose jpeg photos/i)).toBeDefined()
  })
})

describe('provenance claims and the terms window (WP-6e)', () => {
  beforeEach(async () => {
    vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
    mocks.fetchServiceState.mockReset()
    mocks.fetchServiceState.mockResolvedValue('open')
    mocks.submitQueued.mockReset()
    mocks.submitQueued.mockResolvedValue(undefined)
    for (const queuedRecord of await queued()) {
      await removeQueued(queuedRecord.submissionId)
    }
    Object.defineProperty(window.navigator, 'onLine', {
      configurable: true,
      value: true,
    })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
  })

  function choosePhotos(lastModified: number) {
    const jpeg = new File(['jpeg'], 'soil.jpg', {
      type: 'image/jpeg',
      lastModified,
    })
    fireEvent.change(screen.getByLabelText(/A · Context/i), {
      target: { files: [jpeg] },
    })
    fireEvent.change(screen.getByLabelText(/B · Fresh face/i), {
      target: { files: [jpeg] },
    })
  }

  function describeAndSubmit() {
    fireEvent.change(screen.getByLabelText('Land cover'), {
      target: { value: 'cropland' },
    })
    fireEvent.change(screen.getByLabelText('Surface condition'), {
      target: { value: 'moist' },
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /sampling rules/i }))
    fireEvent.click(
      screen.getByRole('checkbox', { name: /I own these photos/i }),
    )
    fireEvent.submit(
      screen
        .getByRole('button', { name: /queue observation/i })
        .closest('form')!,
    )
  }

  it('queues a typed location and gallery photos as such', async () => {
    render(<App />)
    choosePhotos(Date.parse('2020-01-01T00:00:00Z'))
    fireEvent.change(screen.getByLabelText('Latitude'), {
      target: { value: '44.4759' },
    })
    fireEvent.change(screen.getByLabelText('Longitude'), {
      target: { value: '-73.2121' },
    })
    describeAndSubmit()

    await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(1))
    expect(mocks.submitQueued).toHaveBeenCalledWith(
      { hosted: true },
      expect.objectContaining({
        accuracyM: null,
        claims: {
          captureMethod: 'file',
          clientVersion: CLIENT_VERSION,
          ingestPath: 'web',
          locationSource: 'manual_pin',
        },
      }),
    )
  })

  it('dates the observation by shot B, not shot A (SPEC section 5)', async () => {
    const now = Date.now()
    const shotA = now - 20 * 60_000
    const shotB = now - 5 * 60_000
    render(<App />)
    fireEvent.change(screen.getByLabelText(/A · Context/i), {
      target: {
        files: [
          new File(['jpeg'], 'a.jpg', {
            type: 'image/jpeg',
            lastModified: shotA,
          }),
        ],
      },
    })
    fireEvent.change(screen.getByLabelText(/B · Fresh face/i), {
      target: {
        files: [
          new File(['jpeg'], 'b.jpg', {
            type: 'image/jpeg',
            lastModified: shotB,
          }),
        ],
      },
    })
    fireEvent.change(screen.getByLabelText('Latitude'), {
      target: { value: '44.4759' },
    })
    fireEvent.change(screen.getByLabelText('Longitude'), {
      target: { value: '-73.2121' },
    })
    describeAndSubmit()

    await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(1))
    expect(mocks.submitQueued).toHaveBeenCalledWith(
      { hosted: true },
      expect.objectContaining({ capturedAt: new Date(shotB).toISOString() }),
    )
  })

  it('queues the device location and fresh camera photos as such, until a coordinate is typed', async () => {
    Object.defineProperty(window.navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition: (success: PositionCallback) =>
          success({
            coords: { accuracy: 6.4, latitude: 44.4759, longitude: -73.2121 },
          } as GeolocationPosition),
      },
    })
    render(<App />)
    choosePhotos(Date.now())
    fireEvent.click(
      screen.getByRole('button', { name: /use my current location/i }),
    )
    expect(await screen.findByText(/accuracy ±6 m/i)).toBeDefined()
    describeAndSubmit()

    await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(1))
    expect(mocks.submitQueued).toHaveBeenLastCalledWith(
      { hosted: true },
      expect.objectContaining({
        accuracyM: 6,
        claims: {
          captureMethod: 'camera',
          clientVersion: CLIENT_VERSION,
          ingestPath: 'web',
          locationSource: 'device_gps',
        },
      }),
    )

    // A coordinate typed after the device fix is a manual location with no GPS accuracy.
    choosePhotos(Date.now())
    fireEvent.click(
      screen.getByRole('button', { name: /use my current location/i }),
    )
    fireEvent.change(screen.getByLabelText('Longitude'), {
      target: { value: '-73.2200' },
    })
    expect(screen.queryByText(/accuracy ±6 m/i)).toBeNull()
    describeAndSubmit()

    await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(2))
    expect(mocks.submitQueued).toHaveBeenLastCalledWith(
      { hosted: true },
      expect.objectContaining({
        accuracyM: null,
        claims: expect.objectContaining({ locationSource: 'manual_pin' }),
      }),
    )
  })

  it('asks for the terms again before sending an observation that waited too long', async () => {
    await enqueue({
      ...record,
      acceptedAt: '2026-01-01T00:00:00Z',
      termsExpiredAt: '2026-02-01T00:00:00Z',
      termsVersion: 'an-older-version',
    })
    render(<App />)

    const accept = await screen.findByRole('button', {
      name: /accept the terms again and send/i,
    })
    expect(screen.getByText(/waited more than 30 days/i)).toBeDefined()
    expect(mocks.submitQueued).not.toHaveBeenCalled()

    const before = Date.now()
    fireEvent.click(accept)
    await waitFor(() => expect(mocks.submitQueued).toHaveBeenCalledTimes(1))
    const [, sent] = mocks.submitQueued.mock.calls[0] as unknown as [
      unknown,
      QueueRecord,
    ]
    expect(sent.termsExpiredAt).toBeUndefined()
    expect(sent.reconfirmedTermsVersion).toBe('2026-07-22-v1')
    expect(Date.parse(sent.reconfirmedAt ?? '')).toBeGreaterThanOrEqual(
      before - 1000,
    )
    // The original acceptance is kept: it is always offered to the server first.
    expect(sent.acceptedAt).toBe('2026-01-01T00:00:00Z')
    expect(sent.termsVersion).toBe('an-older-version')
    // Nothing else about the observation changes.
    expect(sent.grantId).toBe(record.grantId)
    expect(sent.capturedAt).toBe(record.capturedAt)
  })
})
