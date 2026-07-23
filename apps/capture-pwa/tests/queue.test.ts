import 'fake-indexeddb/auto'
import { describe, expect, it } from 'vitest'
import { enqueue, indexedDbQueue, queued } from '../src/queue'
import { drainQueue } from '../src/sync'
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
    const failed = await drainQueue(indexedDbQueue, async () => {
      throw new Error('airplane mode')
    })
    expect(failed).toEqual({ failed: 1, synced: 0 })
    expect((await queued())[0]?.photos[0]?.bytes.byteLength).toBe(5)
    expect((await queued())[0]?.latitude).toBe(41.9483)

    const sent: string[] = []
    const succeeded = await drainQueue(indexedDbQueue, async (item) => {
      sent.push(item.submissionId)
    })
    expect(succeeded).toEqual({ failed: 0, synced: 1 })
    expect(sent).toEqual(['submission'])
    expect(await queued()).toEqual([])
  })
})
