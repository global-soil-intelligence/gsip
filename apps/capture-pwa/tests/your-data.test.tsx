import 'fake-indexeddb/auto'
import {
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
  latestDeletionRequest: vi.fn(async (): Promise<unknown> => null),
  requestDeletion: vi.fn(async (): Promise<string> => 'requested'),
  submitQueued: vi.fn(async (): Promise<void> => undefined),
}))

vi.mock('../src/supabase', () => ({
  createGsipClient: () => ({ hosted: true }),
  fetchServiceState: async () => 'open',
  isServiceConfigured: () => true,
  recordOwner: async () => undefined,
  sendSignInLink: async () => 'sent',
  latestDeletionRequest: mocks.latestDeletionRequest,
  requestDeletion: mocks.requestDeletion,
  submitQueued: mocks.submitQueued,
}))

import { App } from '../src/App'

const record: QueueRecord = {
  accuracyM: 7,
  attributionName: 'Anonymous soil contributor',
  capturedAt: '2026-10-01T00:00:00Z',
  deviceModel: 'test device',
  disturbed: false,
  grantId: 'rights-grant',
  landCover: 'cropland',
  latitude: 40.446,
  longitude: -79.982,
  photos: [],
  queuedAt: '2026-10-01T00:00:00Z',
  submissionId: 'rights-submission',
  surfaceCondition: 'moist',
  termsVersion: '2026-07-22-v1',
}

function setOnline(value: boolean) {
  Object.defineProperty(window.navigator, 'onLine', {
    configurable: true,
    value,
  })
}

beforeEach(async () => {
  vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
  mocks.latestDeletionRequest.mockReset()
  mocks.latestDeletionRequest.mockResolvedValue(null)
  mocks.requestDeletion.mockReset()
  mocks.requestDeletion.mockResolvedValue('requested')
  mocks.submitQueued.mockReset()
  for (const queuedRecord of await queued())
    await removeQueued(queuedRecord.submissionId)
  // Offline keeps queued records on the device, so the tests can see them.
  setOnline(false)
})

afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
  setOnline(true)
})

function choose(action: RegExp) {
  fireEvent.click(screen.getByRole('button', { name: action }))
}

function type(value: string) {
  fireEvent.change(screen.getByLabelText(/to confirm/i), {
    target: { value },
  })
}

function confirmButton() {
  return screen.getByRole('button', {
    name: /confirm (withdrawal|account deletion)/i,
  }) as HTMLButtonElement
}

describe('your data', () => {
  it('files a withdrawal only once the confirmation word is typed', async () => {
    await enqueue(record)
    render(<App />)
    choose(/withdraw my contributions/i)

    expect(confirmButton().disabled).toBe(true)
    type('withdra')
    fireEvent.click(confirmButton())
    expect(mocks.requestDeletion).not.toHaveBeenCalled()

    type(' withdraw ')
    expect(confirmButton().disabled).toBe(false)
    fireEvent.click(confirmButton())

    expect(
      await screen.findAllByText(/withdrawal requested on/i),
    ).not.toHaveLength(0)
    expect(mocks.requestDeletion).toHaveBeenCalledWith(
      { hosted: true },
      'withdraw_contributions',
    )
    expect(
      screen.getByText(/1 observation queued on this device was discarded/i),
    ).toBeDefined()
    expect(await queued()).toEqual([])
  })

  it('needs DELETE, not WITHDRAW, to delete the account', () => {
    render(<App />)
    choose(/delete my account/i)

    type('WITHDRAW')
    expect(confirmButton().disabled).toBe(true)
    type('DELETE')
    expect(confirmButton().disabled).toBe(false)
  })

  it('files nothing when cancelled', () => {
    render(<App />)
    choose(/delete my account/i)
    type('DELETE')
    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))

    expect(mocks.requestDeletion).not.toHaveBeenCalled()
    expect(
      screen.getByRole('button', { name: /delete my account/i }),
    ).toBeDefined()
  })

  it('shows the status of the latest request', async () => {
    mocks.latestDeletionRequest.mockResolvedValue({
      completedAt: '2026-10-09T03:17:00Z',
      kind: 'withdraw_contributions',
      requestedAt: '2026-10-08T12:00:00Z',
      status: 'completed',
    })
    render(<App />)

    expect(await screen.findByText(/withdrawal completed on/i)).toBeDefined()
  })

  it('keeps the queue and explains when a request is already in progress', async () => {
    mocks.requestDeletion.mockResolvedValue('already_open')
    await enqueue(record)
    render(<App />)
    choose(/delete my account/i)
    type('DELETE')
    fireEvent.click(confirmButton())

    expect(
      await screen.findByText(/a request is already in progress/i),
    ).toBeDefined()
    expect(await queued()).toHaveLength(1)
  })

  it('says so when the request cannot be sent', async () => {
    mocks.requestDeletion.mockRejectedValue(new Error('offline'))
    render(<App />)
    choose(/withdraw my contributions/i)
    type('WITHDRAW')
    fireEvent.click(confirmButton())

    expect(await screen.findByText(/could not be sent/i)).toBeDefined()
  })
})

describe('your data accessibility and edge cases', () => {
  it('moves focus to the confirmation field and back to the action', () => {
    render(<App />)
    choose(/delete my account/i)
    const field = screen.getByLabelText(/type delete to confirm/i)
    expect(document.activeElement).toBe(field)
    expect(field.getAttribute('aria-describedby')).toMatch(/rights-consequence/)

    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
    expect(document.activeElement).toBe(
      screen.getByRole('button', { name: /delete my account/i }),
    )
  })

  it('says a device with no account has nothing stored, and clears its queue', async () => {
    mocks.requestDeletion.mockResolvedValue('no_account')
    await enqueue(record)
    render(<App />)
    choose(/withdraw my contributions/i)
    type('WITHDRAW')
    fireEvent.click(confirmButton())

    expect(await screen.findByText(/this device has no account/i)).toBeDefined()
    expect(await queued()).toEqual([])
  })
})

describe('observations made under another account', () => {
  it('are kept, not sent, until the person discards them', async () => {
    await enqueue({
      ...record,
      heldAt: '2026-10-10T00:00:00Z',
      ownerUid: 'deleted-account',
    })
    render(<App />)

    expect(
      await screen.findByText(/no longer signed in on this device/i),
    ).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: /^discard it$/i }))
    await waitFor(async () => expect(await queued()).toEqual([]))
    expect(mocks.submitQueued).not.toHaveBeenCalled()
  })
})

describe('sampling rules', () => {
  function fillObservation() {
    const jpeg = new File(['jpeg'], 'soil.jpg', { type: 'image/jpeg' })
    fireEvent.change(screen.getByLabelText(/A · Context/i), {
      target: { files: [jpeg] },
    })
    fireEvent.change(screen.getByLabelText(/B · Fresh face/i), {
      target: { files: [jpeg] },
    })
    fireEvent.change(screen.getByLabelText('Latitude'), {
      target: { value: '44.4759' },
    })
    fireEvent.change(screen.getByLabelText('Longitude'), {
      target: { value: '-73.2121' },
    })
    fireEvent.change(screen.getByLabelText('Land cover'), {
      target: { value: 'cropland' },
    })
    fireEvent.change(screen.getByLabelText('Surface condition'), {
      target: { value: 'moist' },
    })
    fireEvent.click(
      screen.getByRole('checkbox', { name: /I own these photos/i }),
    )
  }

  function submit() {
    fireEvent.submit(
      screen
        .getByRole('button', { name: /queue observation/i })
        .closest('form')!,
    )
  }

  it('must be confirmed before an observation is queued', async () => {
    render(<App />)
    fillObservation()
    submit()

    expect(
      await screen.findByText(/confirm the sampling rules before queueing/i),
    ).toBeDefined()
    expect(await queued()).toEqual([])

    fireEvent.click(screen.getByRole('checkbox', { name: /sampling rules/i }))
    submit()
    await waitFor(async () => expect(await queued()).toHaveLength(1))
  })

  it('links the rules, terms and privacy notice', () => {
    render(<App />)
    for (const name of [
      /sampling rules/i,
      /contribution terms/i,
      /privacy notice/i,
    ]) {
      const [link] = screen.getAllByRole('link', { name })
      expect(link.getAttribute('href')).toMatch(/^https:\/\//)
    }
  })
})
