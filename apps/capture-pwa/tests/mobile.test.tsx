import 'fake-indexeddb/auto'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from '../src/App'
import { enqueue, queued, removeQueued } from '../src/queue'
import { drainQueue } from '../src/sync'
import { connectEmail, type GsipClient } from '../src/supabase'
import type { QueueRecord } from '../src/types'
const record: QueueRecord = {
  submissionId: 'draft-1',
  grantId: 'grant-1',
  latitude: 40,
  longitude: -79,
  accuracyM: null,
  attributionName: 'Field observer',
  capturedAt: '2026-09-14T12:00:00Z',
  queuedAt: '2026-09-14T12:00:00Z',
  deviceModel: 'test',
  disturbed: false,
  landCover: 'forest',
  surfaceCondition: 'dry',
  termsVersion: 'v1',
  draft: true,
  photos: [],
}
beforeEach(async () => {
  for (const row of await queued()) await removeQueued(row.submissionId)
})
afterEach(cleanup)
describe('mobile journeys', () => {
  it('explains the prediction hold and lab pairing without presenting invented estimates', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Learn' }))
    expect(
      screen.getByText(/Image predictions are not available yet/),
    ).toBeDefined()
    expect(screen.getByText(/Keep the observation reference/)).toBeDefined()
  })
  it('closes capture when the release flag is off', async () => {
    vi.stubEnv('VITE_CAPTURE_LIVE', 'false')
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Capture' }))
    expect(screen.getByText('Capture is not open yet.')).toBeDefined()
    expect(
      screen.queryByRole('button', { name: /queue observation/i }),
    ).toBeNull()
  })
  it('retains drafts across app remounts and resumes their fields', async () => {
    await enqueue(record)
    const view = render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'My observations' }))
    await screen.findByRole('button', { name: 'Resume draft' })
    expect(screen.getByText(record.submissionId)).toBeDefined()
    view.unmount()
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'My observations' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Resume draft' }))
    expect((screen.getByLabelText('Latitude') as HTMLInputElement).value).toBe(
      '40',
    )
    expect(
      (screen.getByLabelText('Land cover') as HTMLSelectElement).value,
    ).toBe('forest')
  })
  it('never uploads a draft even while online', async () => {
    const send = vi.fn()
    await drainQueue(
      { list: async () => [record], put: vi.fn(), remove: vi.fn() },
      send,
    )
    expect(send).not.toHaveBeenCalled()
  })
  it('saves an incomplete draft without pretending it was submitted', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Capture' }))
    fireEvent.change(screen.getByLabelText('Land cover'), {
      target: { value: 'grassland' },
    })
    fireEvent.click(
      screen.getByRole('button', { name: 'Save draft on this device' }),
    )
    await waitFor(async () => expect((await queued())[0]?.draft).toBe(true))
    expect(await screen.findByText(/Draft saved on this device/)).toBeDefined()
  })
  it('links an email to the anonymous identity rather than creating another user', async () => {
    const updateUser = vi.fn(async () => ({ error: null }))
    const signInWithOtp = vi.fn()
    const client = {
      auth: {
        getSession: async () => ({
          data: { session: { user: { is_anonymous: true } } },
        }),
        updateUser,
        signInWithOtp,
      },
    } as unknown as GsipClient
    expect(await connectEmail(client, 'field@example.org')).toBe('email_change')
    expect(updateUser).toHaveBeenCalledWith(
      { email: 'field@example.org' },
      expect.any(Object),
    )
    expect(signInWithOtp).not.toHaveBeenCalled()
  })
})
