import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import { openDB } from 'idb'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { TERMS_VERSION } from '../src/terms'
import type { QueueRecord } from '../src/types'

const record = (): QueueRecord => ({
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
beforeEach(() => {
  vi.resetModules()
  vi.stubGlobal('indexedDB', new IDBFactory())
})
afterEach(() => {
  vi.unstubAllGlobals()
})
for (const version of [1, 2, 3]) {
  it(`additive reminder upgrade preserves version ${version} submission/draft/library bytes`, async () => {
    const legacy = await openDB('gsip-capture-v1', version, {
      upgrade(db) {
        db.createObjectStore('submissions', { keyPath: 'submissionId' })
        if (version >= 2)
          db.createObjectStore('draftPhotos', { keyPath: 'shotType' })
        if (version >= 3) {
          db.createObjectStore('libraryDraft')
          db.createObjectStore('libraryNamespace')
          db.createObjectStore('queueState')
        }
      },
    })
    const original = record()
    await legacy.put('submissions', original)
    if (version >= 2)
      await legacy.put('draftPhotos', {
        shotType: 'A',
        photo: {
          bytes: new Uint8Array([1, 2]),
          mimeType: 'image/jpeg',
          method: 'file',
        },
      })
    if (version >= 3) {
      await legacy.put(
        'libraryDraft',
        { syntheticMarker: 'legacy-library-draft' },
        'current',
      )
      await legacy.put(
        'libraryNamespace',
        { nodeId: 'fictional-node', ownerUid: 'fictional-owner' },
        'current',
      )
      await legacy.put('queueState', 12, 'generation')
    }
    legacy.close()
    const queue = await import('../src/queue')
    expect(await queue.queued()).toEqual([original])
    if (version >= 2)
      expect(Array.from((await queue.draftPhotos()).A?.bytes ?? [])).toEqual([
        1, 2,
      ])
    if (version >= 3) {
      expect(await queue.queueRevision()).toBe(12)
      expect(await queue.savedLibraryDraft()).toEqual({
        syntheticMarker: 'legacy-library-draft',
      })
      expect(await queue.libraryNodeForOwner('fictional-owner')).toBe(
        'fictional-node',
      )
    }
    expect((await queue.indexedDbReminderStore.read()).enabled).toBe(false)
    // Mutating reminder intent never deletes user content.
    await queue.indexedDbReminderStore.update((state) => ({
      ...state,
      owner: 'fictional-owner',
      enabled: true,
    }))
    await queue.indexedDbReminderStore.update((state) => ({
      ...state,
      enabled: false,
      cleanupPending: true,
    }))
    expect(await queue.queued()).toEqual([original])
    if (version >= 2)
      expect(Array.from((await queue.draftPhotos()).A?.bytes ?? [])).toEqual([
        1, 2,
      ])
  })
}
it('clearQueue atomically disables intent and fences stale OS completion without storing sessions', async () => {
  const queue = await import('../src/queue')
  await queue.enqueue(record())
  const before = await queue.indexedDbReminderStore.update((state) => ({
    ...state,
    owner: 'fictional-owner',
    enabled: true,
    consumed: true,
    cycleOpen: true,
  }))
  expect(await queue.clearQueue()).toBe(1)
  const state = await queue.indexedDbReminderStore.read()
  expect(state.enabled).toBe(false)
  expect(state.cleanupPending).toBe(true)
  expect(state.epoch).toBeGreaterThan(before.epoch)
  expect(state.cycleOpen).toBe(false)
  expect(await queue.queued()).toEqual([])
  expect(Object.keys(state).sort()).toEqual(
    [
      'allowed',
      'blocked',
      'cleanupPending',
      'consumed',
      'cycleOpen',
      'enabled',
      'epoch',
      'owner',
      'revision',
    ].sort(),
  )
})
it('fresh owner/revision/hold snapshot exposes booleans only and refuses foreign or unresolved work', async () => {
  const queue = await import('../src/queue')
  await queue.enqueue(record())
  expect(
    await queue.queueReminderContext('fictional-owner', true, 'open', false),
  ).toMatchObject({ hasWork: true, blocked: false })
  expect(
    await queue.queueReminderContext(null, true, 'open', false),
  ).toMatchObject({ blocked: true })
  expect(
    await queue.queueReminderContext(
      'foreign-fictional-owner',
      true,
      'open',
      false,
    ),
  ).toMatchObject({ blocked: true })
  for (const field of [
    'heldAt',
    'deadLetteredAt',
    'termsExpiredAt',
    'libraryConflictAt',
  ] as const) {
    await queue.enqueue({ ...record(), [field]: 'fictional-hold' })
    expect(
      (await queue.queueReminderContext('fictional-owner', true, 'open', false))
        .blocked,
    ).toBe(true)
  }
  await queue.enqueue({ ...record(), termsVersion: 'old-terms' })
  expect(
    (await queue.queueReminderContext('fictional-owner', true, 'open', false))
      .blocked,
  ).toBe(true)
  await queue.enqueue({ ...record(), acceptedAt: '2000-01-01T00:00:00Z' })
  expect(
    (await queue.queueReminderContext('fictional-owner', true, 'open', false))
      .blocked,
  ).toBe(true)
  await queue.enqueue({
    ...record(),
    termsVersion: 'old-terms',
    reconfirmedAt: new Date().toISOString(),
    reconfirmedTermsVersion: TERMS_VERSION,
  })
  expect(
    (await queue.queueReminderContext('fictional-owner', true, 'open', false))
      .blocked,
  ).toBe(false)
  const value = await queue.queueReminderContext(
    'fictional-owner',
    true,
    'open',
    false,
  )
  expect(Object.keys(value).sort()).toEqual(
    ['owner', 'captureLive', 'gate', 'revision', 'hasWork', 'blocked'].sort(),
  )
  expect(JSON.stringify(value)).not.toContain('fictional-submission')
})
it('an unchanged reminder mutation submits no IndexedDB write after a lifecycle fence', async () => {
  const queue = await import('../src/queue')
  await queue.indexedDbReminderStore.update((state) => ({
    ...state,
    owner: 'fictional-owner',
  }))
  const before = await queue.indexedDbReminderStore.read()
  const writes = vi.spyOn(IDBObjectStore.prototype, 'put')
  const after = await queue.indexedDbReminderStore.update((state) => state)
  expect(writes).not.toHaveBeenCalled()
  expect(after).toEqual(before)
  writes.mockRestore()
})
