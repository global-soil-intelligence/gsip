import 'fake-indexeddb/auto'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enqueue } from '../src/queue'
import type { QueueRecord } from '../src/types'

const mocks = vi.hoisted(() => ({ submitQueued: vi.fn(async () => undefined) }))

vi.mock('../src/supabase', () => ({
  createGsipClient: () => ({ hosted: true }),
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
  beforeEach(() => {
    mocks.submitQueued.mockClear()
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
      expect(mocks.submitQueued).toHaveBeenCalledWith({ hosted: true }, record),
    )
    expect(await screen.findByText(/1 observation synced/i)).toBeDefined()
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
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.submit(
      screen
        .getByRole('button', { name: /queue observation/i })
        .closest('form')!,
    )

    expect(await screen.findByText(/choose jpeg photos/i)).toBeDefined()
  })
})
