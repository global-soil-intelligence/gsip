import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CapturedPhoto } from '../src/platform/types'
import type { QueueRecord } from '../src/types'

const photo: CapturedPhoto = {
  bytes: new Uint8Array([0xff, 0xd8, 0xff, 0xe1]),
  mimeType: 'image/jpeg',
  method: 'camera',
  takenAt: Date.parse('2026-10-11T12:00:00Z'),
}

const record = {
  accuracyM: 5,
  attributionName: 'Field contributor',
  capturedAt: '2026-07-22T00:00:00Z',
  deviceModel: 'test device',
  disturbed: false,
  grantId: 'grant',
  landCover: 'cropland',
  latitude: 41.9483,
  longitude: -93.625,
  photos: [],
  queuedAt: '2026-07-22T00:00:00Z',
  submissionId: 'queued-before-the-upgrade',
  surfaceCondition: 'moist',
  termsVersion: 'terms',
} satisfies QueueRecord

/** A fresh browser profile, and a fresh copy of the queue module that has opened nothing yet. */
async function freshQueue() {
  vi.stubGlobal('indexedDB', new IDBFactory())
  vi.resetModules()
  return import('../src/queue')
}

/** The queue database exactly as the version 1 app left it. */
async function versionOneDatabase(records: QueueRecord[]) {
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.open('gsip-capture-v1', 1)
    request.onupgradeneeded = () =>
      request.result.createObjectStore('submissions', {
        keyPath: 'submissionId',
      })
    request.onsuccess = () => {
      const db = request.result
      const write = db.transaction('submissions', 'readwrite')
      for (const queued of records) write.objectStore('submissions').put(queued)
      write.oncomplete = () => {
        db.close()
        resolve()
      }
      write.onerror = () => reject(write.error)
    }
    request.onerror = () => reject(request.error)
  })
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('photos kept before an observation is queued (WP-APP-1)', () => {
  it('upgrades the version 1 queue without losing what it holds', async () => {
    const queue = await freshQueue()
    await versionOneDatabase([record])

    expect((await queue.queued()).map((queued) => queued.submissionId)).toEqual(
      [record.submissionId],
    )
    await queue.saveDraftPhoto('A', photo)
    expect(Object.keys(await queue.draftPhotos())).toEqual(['A'])
  })

  it('keeps one photo per shot until cleared', async () => {
    const queue = await freshQueue()
    await queue.saveDraftPhoto('A', photo)
    await queue.saveDraftPhoto('A', { ...photo, method: 'file' })
    await queue.saveDraftPhoto('B', photo)
    const drafts = await queue.draftPhotos()
    expect(Object.keys(drafts).sort()).toEqual(['A', 'B'])
    expect(drafts.A?.method).toBe('file')
    expect(Array.from(drafts.B?.bytes ?? [])).toEqual(Array.from(photo.bytes))

    await queue.clearDraftPhotos()
    expect(await queue.draftPhotos()).toEqual({})
  })

  it('discards them with the queue when the person withdraws or deletes', async () => {
    const queue = await freshQueue()
    await queue.enqueue(record)
    await queue.saveDraftPhoto('C', photo)
    expect(await queue.clearQueue()).toBe(1)
    expect(await queue.draftPhotos()).toEqual({})
  })
})
