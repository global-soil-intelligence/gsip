import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import type { GsipClient } from '../src/supabase'
import type { MySoilEntry } from '../src/mySoil'
import { record } from './libraryFixtures'

const mocks = vi.hoisted(() => ({
  create: vi.fn(),
  gate: vi.fn(async () => 'open'),
  send: vi.fn(async () => undefined),
  latest: vi.fn(async () => null),
  rights: vi.fn<(...args: unknown[]) => Promise<string>>(
    async () => 'requested',
  ),
  soil: vi.fn<() => Promise<MySoilEntry[] | null>>(async () => null),
  native: false,
}))
vi.mock('../src/supabase', async (load) => ({
  ...(await load<typeof import('../src/supabase')>()),
  createGsipClient: mocks.create,
  fetchServiceState: mocks.gate,
  submitQueued: mocks.send,
  latestDeletionRequest: mocks.latest,
  requestDeletion: mocks.rights,
}))
vi.mock('../src/mySoil', () => ({ mySoil: mocks.soil }))
vi.mock('../src/platform', async (load) => ({
  ...(await load<typeof import('../src/platform')>()),
  isNativeApp: () => mocks.native,
}))

let notify: () => void
let admitted: boolean
let uid: string | null
let anonymous: boolean
let client: GsipClient
let capabilities: ReturnType<typeof vi.fn>
let otp: ReturnType<typeof vi.fn>
beforeEach(() => {
  vi.stubGlobal('indexedDB', new IDBFactory())
  window.history.replaceState(null, '', '/')
  window.localStorage.clear()
  vi.stubEnv('VITE_COLLECTION_MODE', 'invited_private')
  vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
  vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'true')
  vi.stubEnv('VITE_SUPABASE_URL', 'https://supabase.test')
  vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'synthetic-publishable-key')
  admitted = true
  uid = 'owner-a'
  anonymous = false
  mocks.native = false
  mocks.create.mockReset()
  mocks.gate.mockClear()
  mocks.send.mockClear()
  mocks.latest.mockClear()
  mocks.rights.mockReset()
  mocks.rights.mockResolvedValue('requested')
  mocks.soil.mockReset()
  mocks.soil.mockResolvedValue(null)
  capabilities = vi.fn(async () => ({
    data: {
      version: 'gsip-invited-pilot-v1',
      mode: 'invited_private',
      member: admitted,
      capture_open: true,
      library_intake_available: true,
      publication_held: true,
    },
    error: null,
  }))
  otp = vi.fn(async () => ({ error: null }))
  client = {
    auth: {
      getUser: async () => ({
        data: { user: uid ? { id: uid, is_anonymous: anonymous } : null },
        error: null,
      }),
      signInWithOtp: otp,
      onAuthStateChange: (changed: () => void) => {
        notify = changed
        return { data: { subscription: { unsubscribe: () => undefined } } }
      },
    },
    rpc: capabilities,
  } as unknown as GsipClient
  mocks.create.mockReturnValue(client)
})
afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})
async function start() {
  const { App } = await import('../src/App')
  render(<App />)
}
it('keeps ordinary closed landing inert even when service configuration exists', async () => {
  vi.stubEnv('VITE_COLLECTION_MODE', '')
  vi.stubEnv('VITE_CAPTURE_LIVE', 'false')
  vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'false')
  await start()
  expect(mocks.create).not.toHaveBeenCalled()
  expect(mocks.gate).not.toHaveBeenCalled()
  expect(capabilities).not.toHaveBeenCalled()
  expect(screen.queryByLabelText('Email')).toBeNull()
  expect(document.querySelector('form')).toBeNull()
})
it.each(['#your-data', '?view=your-data#access_token=synthetic-callback'])(
  'retains existing-account rights at %s while both gates are closed, with no intake drain',
  async (route) => {
    window.history.replaceState(null, '', `/${route}`)
    vi.stubEnv('VITE_COLLECTION_MODE', '')
    vi.stubEnv('VITE_CAPTURE_LIVE', 'false')
    vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'false')
    const queue = await import('../src/queue')
    await queue.enqueue(record())
    await start()
    expect(
      screen.getByRole('heading', { name: 'Your data and account' }),
    ).toBeDefined()
    expect(
      screen.getByRole('button', { name: /withdraw my contributions/i }),
    ).toBeDefined()
    expect(document.querySelector('form')).toBeNull()
    expect(document.querySelector('input[type=file]')).toBeNull()
    await act(async () => {
      window.dispatchEvent(new Event('online'))
      await Promise.resolve()
    })
    expect(mocks.gate).not.toHaveBeenCalled()
    expect(capabilities).not.toHaveBeenCalled()
    expect(mocks.send).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'invited@example.test' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send magic link' }))
    await waitFor(() =>
      expect(otp).toHaveBeenCalledWith({
        email: 'invited@example.test',
        options: {
          shouldCreateUser: false,
          emailRedirectTo: `${window.location.origin}/?view=your-data#your-data`,
        },
      }),
    )
    fireEvent.click(
      screen.getByRole('button', { name: /withdraw my contributions/i }),
    )
    fireEvent.change(screen.getByLabelText(/to confirm/i), {
      target: { value: 'WITHDRAW' },
    })
    fireEvent.click(screen.getByRole('button', { name: /confirm withdrawal/i }))
    await waitFor(() => expect(mocks.rights).toHaveBeenCalled())
    expect(await queue.queued()).toEqual([])
    expect(mocks.send).not.toHaveBeenCalled()
  },
)
it.each(['missing', 'anonymous', 'revoked'])(
  'shows no collection controls for %s access while retaining rights',
  async (failure) => {
    if (failure === 'missing') uid = null
    if (failure === 'anonymous') anonymous = true
    if (failure === 'revoked') admitted = false
    await start()
    await screen.findByRole('button', { name: /withdraw my contributions/i })
    await act(async () => {
      await Promise.resolve()
    })
    expect(
      screen.queryByRole('button', { name: /queue observation/i }),
    ).toBeNull()
    expect(document.querySelector('input[type=file]')).toBeNull()
    expect(mocks.send).not.toHaveBeenCalled()
  },
)
it('invalidates the capture form immediately on account change and keeps existing queue ownership', async () => {
  await start()
  await screen.findByRole('button', { name: /queue observation/i })
  const queue = await import('../src/queue'),
    original = {
      ...record(),
      collectionMode: 'invited_private' as const,
      ownerUid: 'owner-a',
      heldAt: '2026-10-16',
    }
  await queue.enqueue(original)
  await act(async () => {
    uid = null
    notify()
    await Promise.resolve()
  })
  await waitFor(() =>
    expect(
      screen.queryByRole('button', { name: /queue observation/i }),
    ).toBeNull(),
  )
  expect((await queue.queued())[0]).toMatchObject({
    ownerUid: 'owner-a',
    heldAt: '2026-10-16',
  })
  expect(mocks.send).not.toHaveBeenCalled()
})
it('refuses a pilot artifact on a native surface and ignores its rights fragment', async () => {
  mocks.native = true
  window.location.hash = '#your-data'
  await start()
  expect(mocks.create).not.toHaveBeenCalled()
  expect(screen.queryByLabelText('Email')).toBeNull()
  expect(
    screen.queryByRole('button', { name: /queue observation/i }),
  ).toBeNull()
})

it('never renders a prior account delayed My Soil result after an identity switch', async () => {
  let release!: (entries: MySoilEntry[]) => void
  const pending = new Promise<MySoilEntry[]>((resolve) => {
    release = resolve
  })
  const old: MySoilEntry = {
    id: 'owner-a-observation',
    capturedAt: '1999-01-01T00:00:00Z',
    status: 'passed',
    shots: { A: 'passed', B: 'passed', C: 'missing' },
    likelyPublicArea: null,
  }
  const next: MySoilEntry = {
    ...old,
    id: 'owner-b-observation',
    capturedAt: '2026-10-16T00:00:00Z',
    status: 'checking',
  }
  mocks.soil.mockImplementationOnce(() => pending).mockResolvedValue([next])
  await start()
  await screen.findByRole('button', { name: /queue observation/i })
  await act(async () => {
    uid = 'owner-b'
    notify()
    await Promise.resolve()
  })
  await screen.findByText('Being checked')
  await act(async () => {
    release([old])
    await pending
  })
  expect(screen.queryByText('Passed the quality checks')).toBeNull()
  expect(screen.queryByText(/1999/)).toBeNull()
  expect(screen.getByText('Being checked')).toBeDefined()
})

it('retains the cleanup-pending warning through sign-out and clears it after successful local retry', async () => {
  const queue = await import('../src/queue')
  const clear = vi
    .spyOn(queue, 'clearQueue')
    .mockRejectedValue(new Error('Synthetic cleanup failure'))
  mocks.rights.mockImplementation(async (...args) => {
    const beforeSignOut = args[3] as () => Promise<void>
    try {
      await beforeSignOut()
    } catch {
      /* The confirmed server request still signs out. */
    }
    uid = null
    notify()
    return 'requested_cleanup_pending'
  })
  await start()
  fireEvent.click(screen.getByRole('button', { name: /delete my account/i }))
  fireEvent.change(screen.getByLabelText(/to confirm/i), {
    target: { value: 'DELETE' },
  })
  fireEvent.click(
    screen.getByRole('button', { name: /confirm account deletion/i }),
  )
  await screen.findByText(
    /a confirmed server request is recorded.*local cleanup is still pending/i,
  )
  expect(screen.queryByText(/request could not be sent/i)).toBeNull()
  clear.mockRestore()
  mocks.rights.mockResolvedValue('no_account')
  fireEvent.click(
    screen.getByRole('button', { name: /withdraw my contributions/i }),
  )
  fireEvent.change(screen.getByLabelText(/to confirm/i), {
    target: { value: 'WITHDRAW' },
  })
  fireEvent.click(screen.getByRole('button', { name: /confirm withdrawal/i }))
  await screen.findByText(/no account is currently signed in/i)
  expect(
    screen.queryByText(
      /a confirmed server request is recorded.*local cleanup is still pending/i,
    ),
  ).toBeNull()
})

it.each(['account-change', 'rights-clear'])(
  'a late admission response cannot queue after %s or overwrite the next owner queue',
  async (change) => {
    await start()
    await screen.findByRole('button', { name: /queue observation/i })
    await act(async () => {
      await Promise.resolve()
    })
    for (const shot of ['A', 'B'])
      fireEvent.change(screen.getByLabelText(new RegExp(`${shot} ·`)), {
        target: {
          files: [
            new File(['synthetic-jpeg'], `${shot}.jpg`, { type: 'image/jpeg' }),
          ],
        },
      })
    await screen.findByAltText('Saved draft photo B')
    fireEvent.change(screen.getByLabelText('Latitude'), {
      target: { value: '1' },
    })
    fireEvent.change(screen.getByLabelText('Longitude'), {
      target: { value: '1' },
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /sampling rules/i }))
    fireEvent.click(screen.getByRole('checkbox', { name: /I am at least 18/i }))
    let release!: () => void,
      began!: () => void,
      calls = 0
    const pending = new Promise<void>((resolve) => {
      release = resolve
    })
    const entered = new Promise<void>((resolve) => {
      began = resolve
    })
    capabilities.mockImplementation(async () => {
      calls += 1
      if (calls === 2) {
        began()
        await pending
      }
      return {
        data: {
          version: 'gsip-invited-pilot-v1',
          mode: 'invited_private',
          member: true,
          capture_open: true,
          library_intake_available: true,
          publication_held: true,
        },
        error: null,
      }
    })
    fireEvent.submit(
      screen
        .getByRole('button', { name: /queue observation/i })
        .closest('form')!,
    )
    await entered
    const queue = await import('../src/queue')
    await act(async () => {
      if (change === 'account-change') {
        uid = 'owner-b'
        notify()
      }
      await queue.clearQueue()
      await queue.enqueue({
        ...record(),
        ownerUid: 'owner-b',
        collectionMode: 'invited_private',
        submissionId: 'next-owner-queued',
        heldAt: '2026-10-16',
      })
      release()
      await Promise.resolve()
    })
    await waitFor(async () => expect(await queue.queued()).toHaveLength(1))
    expect((await queue.queued())[0]).toMatchObject({
      ownerUid: 'owner-b',
      submissionId: 'next-owner-queued',
    })
    expect(mocks.send).not.toHaveBeenCalled()
  },
)
