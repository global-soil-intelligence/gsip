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
  submitQueued: vi.fn(async (): Promise<void> => undefined),
}))

vi.mock('../src/supabase', () => ({
  createGsipClient: () => ({
    hosted: true,
    auth: { getSession: async () => ({ data: { session: null } }) },
  }),
  observationHistory: async () => [],
  isServiceConfigured: () => true,
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

  afterEach(() => cleanup())

  it('syncs a queued observation when the app opens already online', async () => {
    await enqueue(record)
    render(<App />)

    await waitFor(() =>
      expect(mocks.submitQueued).toHaveBeenCalledWith(
        expect.objectContaining({ hosted: true }),
        record,
      ),
    )
    expect(await screen.findByText(/1 observation synced/i)).toBeDefined()
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

  it('shows a recovery action for a dead-lettered observation', async () => {
    await enqueue({
      ...record,
      deadLetteredAt: '2026-07-23T01:00:00Z',
      syncAttempts: 5,
    })
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'My observations' }))
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
    fireEvent.click(screen.getByRole('button', { name: 'Capture' }))
    const png = new File(['png'], 'soil.png', { type: 'image/png' })
    fireEvent.change(screen.getByLabelText(/A · Context/i), {
      target: { files: [png] },
    })
    expect(await screen.findByText(/choose jpeg photos/i)).toBeDefined()
  })
})
