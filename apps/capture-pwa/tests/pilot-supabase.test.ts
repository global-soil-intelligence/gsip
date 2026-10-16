import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import {
  requestDeletion,
  sendSignInLink,
  submitQueued,
  type GsipClient,
} from '../src/supabase'
import { drainQueue } from '../src/sync'
import type { QueueRecord } from '../src/types'
import { record, service } from './libraryFixtures'

beforeEach(() => {
  vi.stubEnv('VITE_COLLECTION_MODE', 'invited_private')
  vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
  vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'true')
  vi.stubGlobal('indexedDB', new IDBFactory())
  window.localStorage.clear()
})
afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})
it('never upgrades an anonymous account or permits first-use account creation', async () => {
  const auth = {
    getSession: vi.fn(async () => ({
      data: { session: { user: { id: 'anon', is_anonymous: true } } },
    })),
    updateUser: vi.fn(async () => ({ error: null })),
    signInWithOtp: vi.fn(async () => ({ error: null })),
    signInAnonymously: vi.fn(),
  }
  await sendSignInLink(
    { auth } as unknown as GsipClient,
    'invited@example.test',
    `${window.location.origin}/#your-data`,
  )
  expect(auth.updateUser).not.toHaveBeenCalled()
  expect(auth.signInAnonymously).not.toHaveBeenCalled()
  expect(auth.signInWithOtp).toHaveBeenCalledWith({
    email: 'invited@example.test',
    options: {
      emailRedirectTo: `${window.location.origin}/#your-data`,
      shouldCreateUser: false,
    },
  })
})
it('refuses an off-origin sign-in return before auth', async () => {
  const auth = { getSession: vi.fn(), signInWithOtp: vi.fn() }
  expect(
    await sendSignInLink(
      { auth } as unknown as GsipClient,
      'invited@example.test',
      'https://other.test/#your-data',
    ),
  ).toBe('failed')
  expect(auth.signInWithOtp).not.toHaveBeenCalled()
})
function queue(initial: QueueRecord) {
  let value: QueueRecord | undefined = initial
  return {
    list: async () => (value ? [value] : []),
    put: async (next: QueueRecord) => {
      value = next
    },
    remove: async () => {
      value = undefined
    },
    value: () => value,
  }
}
it.each([
  'legacy',
  'unowned',
  'wrong-owner',
  'anonymous',
  'expired',
  'revoked',
  'missing-capabilities',
])(
  'holds %s before mutation or anonymous fallback without spending retry attempts',
  async (refusal) => {
    const s = service(),
      initial = record()
    // The marker fences old queue formats; only the server assigns collection scope.
    Object.assign(initial, {
      collectionMode: 'invited_private',
      ownerUid: 'owner-a',
    })
    if (refusal === 'legacy')
      delete (initial as QueueRecord & { collectionMode?: string })
        .collectionMode
    if (refusal === 'unowned') delete initial.ownerUid
    if (refusal === 'wrong-owner') initial.ownerUid = 'owner-b'
    const rpc = s.client.rpc.bind(s.client)
    s.client.rpc = vi.fn(async (name, ...args) =>
      name === 'collection_pilot_capabilities'
        ? {
            data:
              refusal === 'missing-capabilities'
                ? null
                : {
                    version: 'gsip-invited-pilot-v1',
                    mode: 'invited_private',
                    member: refusal !== 'revoked',
                    capture_open: true,
                    library_intake_available: true,
                    publication_held: true,
                  },
            error: null,
          }
        : rpc(name, ...args),
    ) as unknown as typeof s.client.rpc
    Object.assign(s.client.auth, {
      getUser: vi.fn(async () => ({
        data: {
          user:
            refusal === 'expired'
              ? null
              : { id: 'owner-a', is_anonymous: refusal === 'anonymous' },
        },
        error: null,
      })),
    })
    const q = queue(initial)
    await drainQueue(q, (r) => submitQueued(s.client, r))
    expect(q.value()).toBeDefined()
    expect(q.value()?.syncAttempts).toBeUndefined()
    expect(q.value()?.ownerUid).toBe(initial.ownerUid)
    expect(
      s.log.filter(
        (x) =>
          x === 'signin' ||
          x === 'upload' ||
          x === 'prior' ||
          x.startsWith('insert:') ||
          x === 'finalize_submission' ||
          x === 'record_library_intake',
      ),
    ).toEqual([])
  },
)

function admittedService() {
  const s = service()
  const admission = { member: true }
  const rpc = s.client.rpc.bind(s.client)
  s.client.rpc = vi.fn(async (name, ...args) =>
    name === 'collection_pilot_capabilities'
      ? {
          data: {
            version: 'gsip-invited-pilot-v1',
            mode: 'invited_private',
            member: admission.member,
            capture_open: true,
            library_intake_available: true,
            publication_held: true,
          },
          error: null,
        }
      : rpc(name, ...args),
  ) as unknown as typeof s.client.rpc
  Object.assign(s.client.auth, {
    getUser: async () => ({
      data: { user: { id: s.state.uid, is_anonymous: false } },
      error: null,
    }),
  })
  const initial = {
    ...record(),
    collectionMode: 'invited_private' as const,
    ownerUid: 'owner-a',
  }
  return { ...s, admission, initial }
}
it('rechecks revocation before the next photo write and preserves completed stages without attempts', async () => {
  const s = admittedService(),
    q = queue(s.initial)
  const from = s.client.storage.from.bind(s.client.storage)
  s.client.storage.from = ((...args: Parameters<typeof from>) => {
    const bucket = from(...args),
      upload = bucket.upload.bind(bucket)
    bucket.upload = async (...values) => {
      const result = await upload(...values)
      s.admission.member = false
      return result
    }
    return bucket
  }) as typeof s.client.storage.from
  await drainQueue(q, (r, checkpoint) => submitQueued(s.client, r, checkpoint))
  expect(s.log.filter((entry) => entry === 'upload')).toHaveLength(1)
  expect(s.log).not.toContain('insert:photos')
  expect(s.log).not.toContain('finalize_submission')
  expect(q.value()?.syncAttempts).toBeUndefined()
  expect(q.value()?.ownerUid).toBe('owner-a')
})
it('holds an account switch between writes without rebinding or spending attempts', async () => {
  const s = admittedService(),
    q = queue(s.initial)
  const from = s.client.storage.from.bind(s.client.storage)
  s.client.storage.from = ((...args: Parameters<typeof from>) => {
    const bucket = from(...args),
      upload = bucket.upload.bind(bucket)
    bucket.upload = async (...values) => {
      const result = await upload(...values)
      s.state.uid = 'owner-b'
      return result
    }
    return bucket
  }) as typeof s.client.storage.from
  await drainQueue(q, (r, checkpoint) => submitQueued(s.client, r, checkpoint))
  expect(q.value()?.heldAt).toBeDefined()
  expect(q.value()?.ownerUid).toBe('owner-a')
  expect(q.value()?.syncAttempts).toBeUndefined()
  expect(s.log).not.toContain('insert:photos')
})
it('retries a lost private receipt with the exact context and finalized photo checkpoint', async () => {
  const s = admittedService(),
    q = queue(s.initial)
  s.state.lost = true
  await drainQueue(q, (r, checkpoint) => submitQueued(s.client, r, checkpoint))
  const next = q.value()!,
    uploads = s.log.filter((entry) => entry === 'upload').length
  expect(next.library?.photosFinalized).toBe(true)
  await drainQueue(
    q,
    (r, checkpoint) => submitQueued(s.client, r, checkpoint),
    () => Date.parse(next.nextRetryAt!),
  )
  expect(s.intakes).toHaveLength(2)
  expect(s.intakes[1]).toEqual(s.intakes[0])
  expect(s.log.filter((entry) => entry === 'upload')).toHaveLength(uploads)
  expect(q.value()).toBeUndefined()
})
it('keeps an in-flight failure unmodified when auth invalidates the drain', async () => {
  const s = admittedService(),
    q = queue(s.initial)
  let current = true
  s.client.storage.from = (() => ({
    upload: async () => {
      current = false
      return {
        data: null,
        error: { message: 'Synthetic failure', statusCode: '503' },
      }
    },
  })) as unknown as typeof s.client.storage.from
  await drainQueue(
    q,
    (r, checkpoint) => submitQueued(s.client, r, checkpoint, () => current),
    Date.now,
    () => !current,
  )
  expect(q.value()?.syncAttempts).toBeUndefined()
  expect(q.value()?.ownerUid).toBe('owner-a')
})
it('treats a withdrawal refusal as terminal even while invitation checks stay open', async () => {
  const s = admittedService(),
    q = queue(s.initial)
  s.state.failure = 'WD001'
  const result = await drainQueue(q, (r, checkpoint) =>
    submitQueued(s.client, r, checkpoint),
  )
  expect(result.discarded).toBe(1)
  expect(q.value()).toBeUndefined()
})
it('never transfers pilot or legacy held queues through the pilot retry action', async () => {
  vi.resetModules()
  const local = await import('../src/queue')
  await local.enqueue({
    ...record(),
    collectionMode: 'invited_private',
    ownerUid: 'owner-a',
    heldAt: '2026-10-16',
  })
  await local.releaseHeld('owner-b', true)
  expect((await local.queued())[0]).toMatchObject({
    ownerUid: 'owner-a',
    heldAt: '2026-10-16',
  })
  await local.releaseHeld('owner-a', true)
  expect((await local.queued())[0].heldAt).toBeUndefined()
  await local.enqueue({
    ...record(),
    ownerUid: 'owner-a',
    heldAt: '2026-10-16',
  })
  await local.releaseHeld('owner-a', true)
  expect((await local.queued())[0]).toMatchObject({
    ownerUid: 'owner-a',
    heldAt: '2026-10-16',
  })
})

it.each(['contributors', 'contribution_grants', 'submissions', 'photos'])(
  'holds auth-denied %s SELECTs without consuming retry attempts',
  async (table) => {
    const s = admittedService(),
      q = queue(s.initial),
      from = s.client.from.bind(s.client)
    s.client.from = ((name: Parameters<typeof from>[0]) => {
      const query = from(name) as unknown as {
        maybeSingle: () => Promise<unknown>
      }
      if (name === table)
        query.maybeSingle = async () => ({
          data: null,
          error: { code: 'PGRST301', message: 'Synthetic expired session' },
        })
      return query
    }) as unknown as typeof s.client.from
    await drainQueue(q, (r, checkpoint) =>
      submitQueued(s.client, r, checkpoint),
    )
    expect(q.value()).toBeDefined()
    expect(q.value()?.syncAttempts).toBeUndefined()
    expect(q.value()?.nextRetryAt).toBeUndefined()
  },
)
it('pins the confirmed account while a contributor lookup is pending', async () => {
  let uid = 'owner-a',
    release!: () => void
  const pending = new Promise<void>((resolve) => {
      release = resolve
    }),
    insert = vi.fn()
  const query = {
    select: () => query,
    eq: () => query,
    maybeSingle: async () => {
      await pending
      return { data: { id: 'contributor-a' }, error: null }
    },
    insert,
  }
  const client = {
    auth: {
      getSession: async () => ({
        data: { session: { user: { id: uid } } },
        error: null,
      }),
    },
    from: () => query,
  } as unknown as GsipClient
  const outcome = requestDeletion(client, 'delete_account')
  await Promise.resolve()
  uid = 'owner-b'
  release()
  await expect(outcome).rejects.toThrow(/account/i)
  expect(insert).not.toHaveBeenCalled()
})
