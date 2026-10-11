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
  fetchServiceState: mocks.fetchServiceState,
  isServiceConfigured: () => true,
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
