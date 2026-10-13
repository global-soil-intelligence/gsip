import 'fake-indexeddb/auto'
import { describe, expect, it } from 'vitest'
import { enqueue, indexedDbQueue, queued } from '../src/queue'
import { drainQueue, MAX_SYNC_ATTEMPTS } from '../src/sync'
import type { QueueRecord } from '../src/types'

const record: QueueRecord = {
  accuracyM: 12,
  attributionName: 'Field contributor',
  capturedAt: '2026-07-22T00:00:00Z',
  deviceModel: 'test device',
  disturbed: false,
  grantId: 'grant',
  landCover: 'cropland',
  latitude: 41.9483,
  longitude: -93.625,
  photos: [
    {
      bytes: new TextEncoder().encode('photo'),
      mimeType: 'image/jpeg',
      objectId: 'photo',
      shotType: 'B',
    },
  ],
  queuedAt: '2026-07-22T00:00:00Z',
  submissionId: 'submission',
  surfaceCondition: 'moist',
  termsVersion: 'terms',
}

describe('offline queue', () => {
  it('retains private data after failure and removes it only after confirmed sync', async () => {
    await enqueue(record)
    let now = Date.parse('2026-07-23T00:00:00Z')
    const failed = await drainQueue(
      indexedDbQueue,
      async () => {
        throw new Error('airplane mode')
      },
      () => now,
    )
    expect(failed).toEqual({
      discarded: 0,
      failed: 1,
      held: 0,
      reconfirm: 0,
      synced: 0,
    })
    expect((await queued())[0]?.photos[0]?.bytes.byteLength).toBe(5)
    expect((await queued())[0]?.latitude).toBe(41.9483)

    const sent: string[] = []
    now += 30_000
    const succeeded = await drainQueue(
      indexedDbQueue,
      async (item) => {
        sent.push(item.submissionId)
      },
      () => now,
    )
    expect(succeeded).toEqual({
      discarded: 0,
      failed: 0,
      held: 0,
      reconfirm: 0,
      synced: 1,
    })
    expect(sent).toEqual(['submission'])
    expect(await queued()).toEqual([])
  })

  it('stops before the next record once the screen that started it has closed', async () => {
    let records = [
      { ...record, submissionId: 'first' },
      { ...record, submissionId: 'second' },
    ]
    let closed = false
    const sent: string[] = []
    const store = {
      list: async () => records,
      put: async () => undefined,
      remove: async (submissionId: string) => {
        records = records.filter((item) => item.submissionId !== submissionId)
      },
    }

    const summary = await drainQueue(
      store,
      async (item) => {
        sent.push(item.submissionId)
        closed = true
      },
      () => Date.parse('2026-07-23T00:00:00Z'),
      () => closed,
    )

    // The record already sent is confirmed and removed; the next one stays queued.
    expect(sent).toEqual(['first'])
    expect(summary.synced).toBe(1)
    expect(records.map((item) => item.submissionId)).toEqual(['second'])
  })

  it('bounds retries and dead-letters a permanently failing record', async () => {
    let stored = record
    let sends = 0
    let now = Date.parse('2026-07-23T00:00:00Z')
    const store = {
      list: async () => [stored],
      put: async (next: QueueRecord) => {
        stored = next
      },
      remove: async () => undefined,
    }

    for (let cycle = 0; cycle < MAX_SYNC_ATTEMPTS + 3; cycle += 1) {
      await drainQueue(
        store,
        async () => {
          sends += 1
          throw new Error('permanent failure')
        },
        () => now,
      )
      now += 24 * 60 * 60 * 1000
    }

    expect(sends).toBe(MAX_SYNC_ATTEMPTS)
    expect(stored.syncAttempts).toBe(MAX_SYNC_ATTEMPTS)
    expect(stored.deadLetteredAt).toBeDefined()
  })
})
