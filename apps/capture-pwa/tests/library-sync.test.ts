import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { submitQueued, type GsipClient } from '../src/supabase'
import { drainQueue } from '../src/sync'
import type { QueueRecord } from '../src/types'
import { request, record, service, uuid } from './libraryFixtures'

function store(initial: QueueRecord) {
  let values = [initial]
  return {
    list: async () => values,
    put: async (next: QueueRecord) => {
      values = [next]
    },
    remove: async () => {
      values = []
    },
    value: () => values[0],
  }
}
beforeEach(() => {
  vi.stubEnv('VITE_CAPTURE_LIVE', 'true')
  vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'true')
  vi.stubGlobal('indexedDB', new IDBFactory())
  window.localStorage.clear()
})
afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})
it('holds a library record in a closed build without RPC or capture mutation', async () => {
  vi.stubEnv('VITE_LIBRARY_INTAKE_LIVE', 'false')
  const s = service(),
    q = store(record())
  await drainQueue(q, (r) => submitQueued(s.client, r))
  expect(s.log).toEqual([])
  expect(q.value()).toBeDefined()
  expect(q.value()?.syncAttempts).toBeUndefined()
})
it.each(['closed', 'unsupported'])(
  'holds %s capabilities before anonymous signin without spending attempts',
  async (mode) => {
    const s = service(),
      q = store(record())
    s.state.uid = ''
    if (mode === 'closed') s.state.available = false
    else s.state.version = 'future'
    await drainQueue(q, (r) => submitQueued(s.client, r))
    expect(s.log).toEqual(['library_intake_capabilities'])
    expect(q.value()?.syncAttempts).toBeUndefined()
  },
)
it('requires a safe receipt after finalize before prior or removal', async () => {
  const s = service(),
    q = store(record())
  s.state.receipt = false
  await drainQueue(q, (r) => submitQueued(s.client, r))
  expect(s.log.indexOf('record_library_intake')).toBeGreaterThan(
    s.log.indexOf('finalize_submission'),
  )
  expect(s.log).not.toContain('prior')
  expect(q.value()).toBeDefined()
})
it('retries lost receipts with exact IDs and bytes without reuploading finalized photos', async () => {
  const s = service(),
    q = store(record())
  s.state.lost = true
  await drainQueue(q, (r) => submitQueued(s.client, r))
  const next = q.value()!
  expect(next.ownerUid).toBe('owner-a')
  expect(next.library?.photosFinalized).toBe(true)
  const uploads = s.log.filter((x) => x === 'upload').length
  await drainQueue(
    q,
    (r) => submitQueued(s.client, r),
    () => Date.parse(next.nextRetryAt!),
  )
  expect(s.intakes).toEqual([request, request])
  expect(s.log.filter((x) => x === 'upload')).toHaveLength(uploads)
  expect(q.value()).toBeUndefined()
})
it('retains intake and photo IDs after partial upload retry', async () => {
  const s = service(),
    q = store(record())
  s.state.failUpload = true
  await drainQueue(q, (r) => submitQueued(s.client, r))
  const next = q.value()!
  expect(next.ownerUid).toBe('owner-a')
  expect(next.library?.request).toEqual(request)
  await drainQueue(
    q,
    (r) => submitQueued(s.client, r),
    () => Date.parse(next.nextRetryAt!),
  )
  expect(s.intakes).toEqual([request])
})
it('holds immutable conflicts without new identities', async () => {
  const s = service(),
    q = store(record())
  s.state.failure = 'LI002'
  await drainQueue(q, (r) => submitQueued(s.client, r))
  expect(q.value()?.libraryConflictAt).toBeDefined()
  expect(q.value()?.syncAttempts).toBeUndefined()
  expect(q.value()?.library?.request).toEqual(request)
})
it('drops withdrawn records and declaration bytes', async () => {
  const s = service(),
    q = store(record())
  s.state.failure = 'WD001'
  const result = await drainQueue(q, (r) => submitQueued(s.client, r))
  expect(result.discarded).toBe(1)
  expect(q.value()).toBeUndefined()
})
it('preserves legacy queues without a capability probe', async () => {
  const s = service(),
    legacy = record()
  delete legacy.library
  await submitQueued(s.client, legacy)
  expect(s.log).not.toContain('library_intake_capabilities')
  expect(s.log).not.toContain('record_library_intake')
  expect(s.log).toContain('prior')
})
it('never silently drops malformed library metadata into legacy capture', async () => {
  const s = service(),
    bad = record()
  bad.library = { ...bad.library!, version: 2 } as never
  const q = store(bad)
  await drainQueue(q, (r) => submitQueued(s.client, r))
  expect(s.log).toEqual([])
  expect(q.value()?.libraryConflictAt).toBeDefined()
})
it('cannot bulk transfer held library ownership', async () => {
  vi.resetModules()
  const queue = await import('../src/queue')
  await queue.enqueue({
    ...record(),
    ownerUid: 'owner-a',
    heldAt: '2026-10-12',
  })
  await queue.releaseHeld('owner-b')
  expect((await queue.queued())[0]).toMatchObject({
    ownerUid: 'owner-a',
    heldAt: '2026-10-12',
  })
})
it('holds missing capability RPC before auth and never interprets it as empty success', async () => {
  const s = service(),
    q = store(record())
  s.client.rpc = vi
    .fn()
    .mockResolvedValue({ data: null, error: { code: 'PGRST202' } })
  await drainQueue(q, (r, checkpoint) => submitQueued(s.client, r, checkpoint))
  expect(s.log).toEqual([])
  expect(s.client.rpc).toHaveBeenCalledOnce()
  expect(q.value()?.syncAttempts).toBeUndefined()
})
it('persists sender ownership before uploads and finalized stage before intake', async () => {
  const s = service(),
    q = store(record()),
    checkpoints: QueueRecord[] = []
  await drainQueue(q, (r, save) =>
    submitQueued(s.client, r, async (next) => {
      checkpoints.push(structuredClone(next))
      await save(next)
    }),
  )
  expect(checkpoints[0].ownerUid).toBe('owner-a')
  expect(checkpoints.some((x) => x.library?.photosFinalized)).toBe(true)
  expect(q.value()).toBeUndefined()
})
it('retains completed photos during a temporary library closure and later retries the same intake', async () => {
  const s = service(),
    q = store(record())
  s.state.lost = true
  await drainQueue(q, (r, save) => submitQueued(s.client, r, save))
  const first = q.value()!,
    uploads = s.log.filter((x) => x === 'upload').length
  s.state.available = false
  await drainQueue(
    q,
    (r, save) => submitQueued(s.client, r, save),
    () => Date.parse(first.nextRetryAt!),
  )
  expect(q.value()?.syncAttempts).toBe(1)
  expect(q.value()?.library?.photosFinalized).toBe(true)
  s.state.available = true
  await drainQueue(
    q,
    (r, save) => submitQueued(s.client, r, save),
    () => Date.parse(first.nextRetryAt!),
  )
  expect(s.intakes).toEqual([request, request])
  expect(s.log.filter((x) => x === 'upload')).toHaveLength(uploads)
})
it('keeps a wrong-ID or authority-bearing receipt retryable without prior invocation', async () => {
  const s = service(),
    original = s.client.rpc.bind(s.client)
  s.client.rpc = vi.fn(async (name, args) =>
    name === 'record_library_intake'
      ? {
          data: {
            intake_id: uuid(8),
            status: 'stored_private_unverified',
            holdout: false,
          },
          error: null,
        }
      : original(name, args),
  ) as unknown as GsipClient['rpc']
  const q = store(record())
  await drainQueue(q, (r, save) => submitQueued(s.client, r, save))
  expect(q.value()).toBeDefined()
  expect(q.value()?.syncAttempts).toBe(1)
  expect(s.log).not.toContain('prior')
})
it('holds a library account switch without mutating capture or transferring IDs', async () => {
  const s = service(),
    r = record()
  r.ownerUid = 'owner-old'
  const q = store(r)
  await drainQueue(q, (r, save) => submitQueued(s.client, r, save))
  expect(q.value()?.ownerUid).toBe('owner-old')
  expect(q.value()?.heldAt).toBeDefined()
  expect(q.value()?.library?.request).toEqual(request)
  expect(s.log.some((x) => x.startsWith('insert:'))).toBe(false)
})
it('a second tab clearing during a drain prevents checkpoints and namespace restoration', async () => {
  vi.resetModules()
  const a = await import('../src/queue')
  await a.enqueue(record())
  vi.resetModules()
  const b = await import('../src/queue')
  await drainQueue(a.indexedDbQueue, async (r, save) => {
    await b.clearQueue()
    r.ownerUid = 'owner-a'
    await save(r)
  })
  expect(await a.queued()).toEqual([])
  expect(await a.savedLibraryDraft()).toBeUndefined()
})
it('does not recreate a held record when clear wins the conditional write race', async () => {
  const s = service(),
    r = record()
  r.ownerUid = 'owner-old'
  const q = store(r)
  const summary = await drainQueue(
    {
      ...q,
      revision: async () => 0,
      isCurrent: async () => true,
      putIfCurrent: async () => {
        await q.remove()
        return false
      },
    },
    (r, save) => submitQueued(s.client, r, save),
  )
  expect(summary.held).toBe(0)
  expect(q.value()).toBeUndefined()
})

it('a late checkpoint cannot resurrect a record another drain already completed', async () => {
  vi.resetModules()
  const q = await import('../src/queue'),
    r = record()
  await q.enqueue(r)
  const revision = await q.queueRevision()
  await q.removeQueued(r.submissionId)
  expect(await q.putIfCurrent(r, revision)).toBe(false)
  expect(await q.queued()).toEqual([])
})
