import 'fake-indexeddb/auto'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { clearQueue, enqueue } from '../src/queue'
import { TERMS_VERSION } from '../src/terms'

const mocks = vi.hoisted(() => ({
  schedule: vi.fn(async () => true),
  clear: vi.fn(async () => true),
  permission: vi.fn(async (): Promise<'granted' | 'denied'> => 'granted'),
  auth: vi.fn(),
  unsubscribe: vi.fn(),
  client: { hosted: true, auth: { onAuthStateChange: vi.fn() } },
}))
vi.mock('../src/platform', async (original) => ({
  ...(await original<typeof import('../src/platform')>()),
  isNativeApp: () => true,
  selectPlatform: async () => ({
    ingestPath: 'app',
    camera: { kind: 'native', takePhoto: vi.fn() },
    location: { locate: vi.fn() },
    attestation: { name: 'none', attest: vi.fn() },
  }),
}))
vi.mock('../src/platform/notifications', () => ({
  selectReminderNotifications: () => ({
    supported: true,
    schedule: mocks.schedule,
    clear: mocks.clear,
    checkPermission: async () => 'granted',
    requestPermission: mocks.permission,
    onTap: async () => async () => undefined,
  }),
}))
vi.mock('../src/supabase', () => ({
  createGsipClient: () => mocks.client,
  isServiceConfigured: () => true,
  fetchServiceState: async () => 'open',
  existingContributor: async () => null,
  latestDeletionRequest: async () => null,
  recordOwner: async () => 'fictional-owner',
  submitQueued: vi.fn(),
  requestDeletion: vi.fn(),
  sendSignInLink: vi.fn(),
}))
import { App } from '../src/App'
beforeEach(async () => {
  await clearQueue()
  vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
  Object.defineProperty(navigator, 'onLine', {
    configurable: true,
    value: false,
  })
  vi.stubGlobal('navigator', navigator)
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: {
      request: async (_name: string, run: () => Promise<unknown>) => run(),
    },
  })
  mocks.schedule.mockClear()
  mocks.clear.mockClear()
  mocks.permission.mockReset()
  mocks.permission.mockResolvedValue('granted')
  mocks.unsubscribe.mockClear()
  mocks.client.auth.onAuthStateChange.mockImplementation((callback) => {
    mocks.auth.mockImplementation(callback)
    callback('INITIAL_SESSION', { user: { id: 'fictional-owner' } })
    return { data: { subscription: { unsubscribe: mocks.unsubscribe } } }
  })
  await enqueue({
    accuracyM: null,
    attributionName: 'Synthetic contributor',
    capturedAt: new Date().toISOString(),
    deviceModel: 'fictional device',
    disturbed: false,
    grantId: 'fictional-grant',
    landCover: 'bare',
    latitude: 0,
    longitude: 0,
    photos: [],
    ownerUid: 'fictional-owner',
    queuedAt: new Date().toISOString(),
    submissionId: 'fictional-submission',
    surfaceCondition: 'dry',
    termsVersion: TERMS_VERSION,
  })
})
afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  Reflect.deleteProperty(navigator, 'locks')
})
it('existing sign-out callback fences a pending permission dialog without creating an auth/session path', async () => {
  let resolve!: (permission: 'granted') => void, entered!: () => void
  const began = new Promise<void>((done) => {
    entered = done
  })
  mocks.permission.mockImplementation(() => {
    entered()
    return new Promise((done) => {
      resolve = done
    })
  })
  render(<App />)
  const enable = await screen.findByRole('button', {
    name: 'Enable sync reminders',
  })
  await waitFor(() =>
    expect((enable as HTMLButtonElement).disabled).toBe(false),
  )
  fireEvent.click(enable)
  await began
  mocks.auth('SIGNED_OUT', null)
  resolve('granted')
  await waitFor(() => expect(mocks.clear).toHaveBeenCalled())
  expect(mocks.schedule).not.toHaveBeenCalled()
  expect(await screen.findByText('Sync reminders are off.')).toBeDefined()
})
it('existing account changes clear the reminder and never transfer explicit intent', async () => {
  render(<App />)
  const enable = await screen.findByRole('button', {
    name: 'Enable sync reminders',
  })
  await waitFor(() =>
    expect((enable as HTMLButtonElement).disabled).toBe(false),
  )
  fireEvent.click(enable)
  await waitFor(() => expect(mocks.schedule).toHaveBeenCalledTimes(1))
  const cleared = mocks.clear.mock.calls.length
  mocks.auth('SIGNED_IN', { user: { id: 'different-fictional-owner' } })
  await waitFor(() =>
    expect(mocks.clear.mock.calls.length).toBeGreaterThan(cleared),
  )
  expect(mocks.schedule).toHaveBeenCalledTimes(1)
  cleanup()
  expect(mocks.unsubscribe).toHaveBeenCalledTimes(1)
})
it('an unsubscribed auth callback does not read a stale session or restart device reminders', async () => {
  render(<App />)
  const stale = mocks.auth.getMockImplementation()!
  cleanup()
  const readSession = vi.fn(() => {
    throw new Error('fictional-private-canary')
  })
  const session = Object.defineProperty({}, 'user', { get: readSession })
  stale('SIGNED_IN', session)
  expect(readSession).not.toHaveBeenCalled()
})
