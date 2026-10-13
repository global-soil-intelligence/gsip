import { afterEach, describe, expect, it, vi } from 'vitest'
import { drainQueue, type QueueStore, type SyncSummary } from '../src/sync'
import type { QueueRecord } from '../src/types'

const EMPTY: SyncSummary = {
  discarded: 0,
  failed: 0,
  held: 0,
  reconfirm: 0,
  synced: 0,
}

// Entirely synthetic, including the unused position; no contributor data is needed.
const record: QueueRecord = {
  accuracyM: null,
  attributionName: 'Anonymous soil contributor',
  capturedAt: '2026-10-11T00:00:00Z',
  deviceModel: 'synthetic device',
  disturbed: false,
  grantId: 'synthetic-grant',
  landCover: 'cropland',
  latitude: 0,
  longitude: 0,
  photos: [],
  queuedAt: '2026-10-11T00:00:00Z',
  submissionId: 'synthetic-submission',
  surfaceCondition: 'moist',
  termsVersion: 'synthetic-terms',
}

type Grant = (lock: Lock | null) => SyncSummary | Promise<SyncSummary>

/** A shared origin's lock manager, available to each simulated tab. */
function lockManager(initiallyHeld = false) {
  let held = initiallyHeld
  return {
    request: vi.fn(async (name: string, options: LockOptions, grant: Grant) => {
      if (held && options.ifAvailable) return grant(null)
      held = true
      try {
        return await grant({ name, mode: 'exclusive' })
      } finally {
        held = false
      }
    }),
  }
}

function deferred() {
  let resolve: () => void = () => undefined
  const promise = new Promise<void>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

function queue() {
  let records = [record]
  return {
    generation: vi.fn(() => 0),
    list: vi.fn(async () => records.slice()),
    put: vi.fn(async () => undefined),
    remove: vi.fn(async (submissionId: string) => {
      records = records.filter((item) => item.submissionId !== submissionId)
    }),
  } satisfies QueueStore
}

afterEach(() => vi.unstubAllGlobals())

describe('the queue drain across tabs (WP-3b)', () => {
  it('lets only one tab send a shared queued observation while its lock is held', async () => {
    const locks = lockManager()
    vi.stubGlobal('navigator', { locks })
    const store = queue()
    const started = deferred()
    const release = deferred()
    const sendFromFirstTab = vi.fn(async () => {
      started.resolve()
      await release.promise
    })
    const sendFromSecondTab = vi.fn(async () => undefined)
    const first = drainQueue(store, sendFromFirstTab)
    await started.promise

    try {
      const second = await drainQueue(store, sendFromSecondTab)
      expect(second).toEqual(EMPTY)
      expect(sendFromFirstTab).toHaveBeenCalledTimes(1)
      expect(sendFromSecondTab).not.toHaveBeenCalled()
      expect(store.list).toHaveBeenCalledTimes(1)
      expect(locks.request).toHaveBeenNthCalledWith(
        2,
        'gsip-sync',
        { ifAvailable: true },
        expect.any(Function),
      )
    } finally {
      release.resolve()
      await first
    }
    expect(store.remove).toHaveBeenCalledTimes(1)
    expect(await store.list()).toEqual([])
  })

  it('returns without touching the queue when another context owns the lock', async () => {
    vi.stubGlobal('navigator', { locks: lockManager(true) })
    const store = queue()
    const send = vi.fn(async () => undefined)

    expect(await drainQueue(store, send)).toEqual(EMPTY)
    expect(store.generation).not.toHaveBeenCalled()
    expect(store.list).not.toHaveBeenCalled()
    expect(store.put).not.toHaveBeenCalled()
    expect(store.remove).not.toHaveBeenCalled()
    expect(send).not.toHaveBeenCalled()
  })

  it.each([{}, undefined])(
    'keeps the existing drain without Web Locks (%s)',
    async (navigator) => {
      vi.stubGlobal('navigator', navigator)
      const store = queue()
      const send = vi.fn(async () => undefined)

      expect(await drainQueue(store, send)).toEqual({ ...EMPTY, synced: 1 })
      expect(send).toHaveBeenCalledTimes(1)
      expect(store.remove).toHaveBeenCalledWith(record.submissionId)
    },
  )

  it('releases the lock after a queue exception so another drain can acquire it', async () => {
    const locks = lockManager()
    vi.stubGlobal('navigator', { locks })
    const store = queue()
    store.list.mockRejectedValueOnce(new Error('queue unavailable'))

    await expect(drainQueue(store, async () => undefined)).rejects.toThrow(
      'queue unavailable',
    )
    const send = vi.fn(async () => undefined)
    expect(await drainQueue(store, send)).toEqual({ ...EMPTY, synced: 1 })
    expect(send).toHaveBeenCalledTimes(1)
    expect(locks.request).toHaveBeenCalledTimes(2)
  })
})
