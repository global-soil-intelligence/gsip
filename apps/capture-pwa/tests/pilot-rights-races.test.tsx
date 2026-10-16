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
import { record } from './libraryFixtures'

const mocks = vi.hoisted(() => ({
  request: vi.fn<(...args: unknown[]) => Promise<string>>(
    async () => 'requested',
  ),
}))
vi.mock('../src/supabase', async (load) => ({
  ...(await load<typeof import('../src/supabase')>()),
  requestDeletion: mocks.request,
  latestDeletionRequest: async () => null,
}))
beforeEach(() => {
  vi.stubGlobal('indexedDB', new IDBFactory())
  mocks.request.mockReset()
  vi.resetModules()
})

it('clears the confirmed deleted account before its own SDK sign-out invalidates the view', async () => {
  const actual =
    await vi.importActual<typeof import('../src/supabase')>('../src/supabase')
  mocks.request.mockImplementation(
    actual.requestDeletion as (...args: unknown[]) => Promise<string>,
  )
  const { YourData } = await import('../src/YourData'),
    queue = await import('../src/queue')
  let notify!: (event: string) => void
  const signOut = vi.fn(async () => {
    expect(await queue.queued()).toEqual([])
    notify('SIGNED_OUT')
    return { error: null }
  })
  const query = {
    select: () => query,
    eq: () => query,
    maybeSingle: async () => ({ data: { id: 'contributor-a' }, error: null }),
    insert: async () => ({ error: null }),
  }
  const client = {
    auth: {
      getSession: async () => ({
        data: { session: { user: { id: 'owner-a' } } },
        error: null,
      }),
      onAuthStateChange: (fn: (event: string) => void) => {
        notify = fn
        return { data: { subscription: { unsubscribe: () => undefined } } }
      },
      signOut,
    },
    from: () => query,
  } as unknown as GsipClient
  await queue.enqueue({ ...record(), ownerUid: 'owner-a' })
  const cleared = vi.fn(async () => undefined)
  render(<YourData client={client} onQueueCleared={cleared} />)
  fireEvent.click(screen.getByRole('button', { name: /delete my account/i }))
  fireEvent.change(screen.getByLabelText(/to confirm/i), {
    target: { value: 'DELETE' },
  })
  fireEvent.click(
    screen.getByRole('button', { name: /confirm account deletion/i }),
  )
  await waitFor(() => expect(signOut).toHaveBeenCalledOnce())
  expect(cleared).toHaveBeenCalledOnce()
  expect(await queue.queued()).toEqual([])
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
it.each(['account-change', 'unmount'])(
  'ignores a late confirmed rights reply after %s and preserves the next account queue',
  async (change) => {
    const { YourData } = await import('../src/YourData'),
      queue = await import('../src/queue')
    let notify!: (event: string) => void, release!: () => void
    const pending = new Promise<void>((resolve) => {
      release = resolve
    })
    mocks.request.mockImplementation(async () => {
      await pending
      return 'requested'
    })
    const client = {
      auth: {
        onAuthStateChange: (fn: (event: string) => void) => {
          notify = fn
          return { data: { subscription: { unsubscribe: () => undefined } } }
        },
      },
    } as unknown as GsipClient
    const cleared = vi.fn(async () => undefined)
    await queue.enqueue({ ...record(), ownerUid: 'owner-a' })
    const view = render(<YourData client={client} onQueueCleared={cleared} />)
    fireEvent.click(
      screen.getByRole('button', { name: /withdraw my contributions/i }),
    )
    fireEvent.change(screen.getByLabelText(/to confirm/i), {
      target: { value: 'WITHDRAW' },
    })
    fireEvent.click(screen.getByRole('button', { name: /confirm withdrawal/i }))
    await waitFor(() => expect(mocks.request).toHaveBeenCalledOnce())
    const current = (
      mocks.request.mock.calls as unknown[][]
    )[0]?.[2] as () => boolean
    expect(current()).toBe(true)
    await act(async () => {
      if (change === 'account-change') notify('SIGNED_IN')
      else view.unmount()
      await queue.clearQueue()
      await queue.enqueue({ ...record(), ownerUid: 'owner-b' })
      release()
      await pending
    })
    expect(current()).toBe(false)
    expect((await queue.queued())[0].ownerUid).toBe('owner-b')
    expect(cleared).not.toHaveBeenCalled()
    expect(screen.queryByText(/withdrawal requested on/i)).toBeNull()
  },
)
