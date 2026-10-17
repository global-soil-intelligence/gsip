import 'fake-indexeddb/auto'
import { IDBFactory, IDBObjectStore } from 'fake-indexeddb'
import { openDB } from 'idb'
import {
  MAX_LIBRARY_INTAKE_BYTES,
  parseInstrumentDeclaration,
} from '@gsip/schema'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  type LibraryDraft,
  newLibraryDraft,
  queueLibraryDraft,
} from '../src/library'
import { enqueue, indexedDbQueue, queued } from '../src/queue'
import { drainQueue, MAX_SYNC_ATTEMPTS } from '../src/sync'
import type { QueueRecord } from '../src/types'
import corpus from '../../../packages/schema/tests/fixtures/library-intake-conformance.json'

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

describe('owner-bound guide handoff', () => {
  const ownerUid = 'synthetic-owner'
  const photo = {
    bytes: new Uint8Array([255, 216, 255, 1]),
    mimeType: 'image/jpeg' as const,
    method: 'file' as const,
    takenAt: 1,
  }
  const guideRecord = (): QueueRecord => ({
    ...record,
    latitude: 0,
    longitude: 0,
    ownerUid,
    collectionMode: 'invited_private',
    photos: ['A', 'B'].map((shotType, index) => ({
      bytes: new Uint8Array([255, 216, 255, index]),
      mimeType: 'image/jpeg',
      objectId: `synthetic-photo-${index}`,
      shotType: shotType as 'A' | 'B',
    })),
  })
  const context = (revision: number) => ({
    ownerUid,
    revision,
    allowed: () => true,
    originalContextCurrent: () => true,
  })
  const draft = (deviceRevision: number) => ({
    ...newLibraryDraft('00000000-0000-4000-8000-000000000001', ownerUid),
    deviceRevision,
    depthTop: '1.5',
    depthBottom: '5',
  })
  async function queue() {
    return import('../src/queue')
  }
  beforeEach(() => {
    vi.stubGlobal('indexedDB', new IDBFactory())
    vi.resetModules()
  })
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('inserts only one snapshot, advances the fence, and preserves other queued observations', async () => {
    const q = await queue(),
      revision = await q.queueRevision()
    await q.enqueue({ ...guideRecord(), submissionId: 'unrelated' })
    const pending = guideRecord()
    expect(await q.enqueueGuideObservation(pending, context(revision))).toEqual(
      {
        status: 'committed',
        revision: revision + 1,
      },
    )
    expect(await q.queueRevision()).toBe(revision + 1)
    expect((await q.queued()).map((item) => item.submissionId).sort()).toEqual([
      'submission',
      'unrelated',
    ])
    expect(await q.draftPhotos()).toEqual({})
    expect(await q.savedLibraryDraft()).toBeUndefined()
    expect(
      await q.enqueueGuideObservation(pending, {
        ...context(revision),
        originalContextCurrent: () => false,
      }),
    ).toEqual({ status: 'reconciled', revision: revision + 1 })
    expect(await q.queueRevision()).toBe(revision + 1)
  })

  it.each(['A', 'B', 'C'] as const)(
    'holds if any persisted picker slot %s wins the transaction order',
    async (shot) => {
      const q = await queue(),
        revision = await q.queueRevision()
      const writes = await Promise.all([
        q.saveDraftPhoto(shot, photo, revision),
        q.enqueueGuideObservation(guideRecord(), context(revision)),
      ])
      expect(writes).toEqual([true, { status: 'held', revision }])
      expect((await q.draftPhotos())[shot]).toEqual(structuredClone(photo))
      expect(await q.queued()).toEqual([])
      expect(await q.queueRevision()).toBe(revision)
    },
  )

  it('refuses old late photo writes observably, while a fresh successor-revision draft survives reconciliation', async () => {
    const q = await queue(),
      revision = await q.queueRevision(),
      pending = guideRecord()
    const [commit, stale] = await Promise.all([
      q.enqueueGuideObservation(pending, context(revision)),
      q.saveDraftPhoto('C', photo, revision),
    ])
    expect(commit).toEqual({ status: 'committed', revision: revision + 1 })
    expect(stale).toBe(false)
    expect(await q.saveDraftPhoto('A', photo, revision + 1)).toBe(true)
    expect(
      (await q.enqueueGuideObservation(pending, context(revision))).status,
    ).toBe('reconciled')
    expect((await q.draftPhotos()).A).toEqual(structuredClone(photo))
  })

  it('consumes only exact owned library context, then reconciles before checking consumed or newer drafts', async () => {
    const q = await queue(),
      revision = await q.queueRevision(),
      saved = draft(revision)
    expect(await q.saveLibraryDraft(saved, revision)).toBe(true)
    const pending = {
      ...guideRecord(),
      submissionId: saved.submissionId,
      library: queueLibraryDraft(saved),
    }
    expect(await q.enqueueGuideObservation(pending, context(revision))).toEqual(
      { status: 'committed', revision: revision + 1 },
    )
    expect(await q.savedLibraryDraft()).toBeUndefined()
    const progressed: QueueRecord = {
      ...pending,
      syncAttempts: 3,
      nextRetryAt: 'synthetic-retry',
      heldAt: 'synthetic-hold',
      reconfirmedAt: 'synthetic-reconfirmation',
      reconfirmedTermsVersion: 'new-terms',
      library: { ...pending.library, photosFinalized: true },
    }
    await q.enqueue(progressed)
    const next = draft(revision + 1)
    expect(await q.saveLibraryDraft(next, revision + 1)).toBe(true)
    expect(
      await q.enqueueGuideObservation(pending, {
        ...context(revision),
        originalContextCurrent: () => false,
      }),
    ).toEqual({ status: 'reconciled', revision: revision + 1 })
    expect(await q.queued()).toEqual(structuredClone([progressed]))
    expect(await q.savedLibraryDraft()).toEqual(next)
    expect(await q.queueRevision()).toBe(revision + 1)
  })

  it('holds changed library context before commit and refuses old context writes after commit', async () => {
    const q = await queue(),
      revision = await q.queueRevision(),
      saved = draft(revision)
    const pending = {
      ...guideRecord(),
      submissionId: saved.submissionId,
      library: queueLibraryDraft(saved),
    }
    await q.saveLibraryDraft(saved, revision)
    const newer = { ...saved, depthBottom: '6' }
    const [savedNewer, held] = await Promise.all([
      q.saveLibraryDraft(newer, revision),
      q.enqueueGuideObservation(pending, context(revision)),
    ])
    expect(savedNewer).toBe(true)
    expect(held).toEqual({ status: 'held', revision })
    expect(await q.savedLibraryDraft()).toEqual(newer)
    await q.saveLibraryDraft(saved, revision)
    const [committed, refused] = await Promise.all([
      q.enqueueGuideObservation(pending, context(revision)),
      q.saveLibraryDraft(newer, revision),
    ])
    expect(committed.status).toBe('committed')
    expect(refused).toBe(false)
    expect(await q.savedLibraryDraft()).toBeUndefined()
  })

  it('requires no hidden library draft when the snapshot has no opt-in', async () => {
    const q = await queue(),
      revision = await q.queueRevision(),
      saved = draft(revision)
    await q.saveLibraryDraft(saved, revision)
    expect(
      await q.enqueueGuideObservation(guideRecord(), context(revision)),
    ).toEqual({ status: 'held', revision })
    expect(await q.savedLibraryDraft()).toEqual(saved)
    expect(await q.queued()).toEqual([])
  })

  it.each([
    'missing-owner',
    'foreign-owner',
    'missing-revision',
    'foreign-revision',
    'blank-depth',
    'changed-id',
  ])('holds %s saved library context without deleting it', async (problem) => {
    const q = await queue(),
      revision = await q.queueRevision(),
      original = draft(revision)
    const pending = {
      ...guideRecord(),
      submissionId: original.submissionId,
      library: queueLibraryDraft(original),
    }
    const saved: LibraryDraft = { ...original }
    if (problem === 'missing-owner') saved.ownerUid = undefined
    if (problem === 'foreign-owner') saved.ownerUid = 'other-owner'
    if (problem === 'missing-revision') saved.deviceRevision = undefined
    if (problem === 'foreign-revision') saved.deviceRevision = revision + 1
    if (problem === 'blank-depth') saved.depthTop = ''
    if (problem === 'changed-id') saved.sampleId = crypto.randomUUID()
    // Simulate a legacy/foreign row without allowing the current strict writer to create it.
    const db = await openDB('gsip-capture-v1')
    await db.put('libraryDraft', saved, 'current')
    db.close()
    expect(await q.enqueueGuideObservation(pending, context(revision))).toEqual(
      { status: 'held', revision },
    )
    expect(await q.savedLibraryDraft()).toEqual(saved)
    expect(await q.queued()).toEqual([])
    expect(await q.queueRevision()).toBe(revision)
  })

  it.each([
    'exact',
    'different-bytes',
    'duplicate-key',
    'malformed-utf8',
    'object-mismatch',
    'wrong-byte-type',
    'oversize-raw',
  ])(
    'validates strict declaration and exact original bytes: %s',
    async (problem) => {
      const q = await queue(),
        revision = await q.queueRevision()
      const raw = JSON.stringify({
        measurement_id: '00000000-0000-4000-8000-000000000002',
        measurement: JSON.parse(corpus.instrument_cases[0]!.raw),
      })
      const original = {
        ...draft(revision),
        instrument: parseInstrumentDeclaration(raw),
        declarationBytes: new TextEncoder().encode(raw),
      }
      const pending = {
        ...guideRecord(),
        submissionId: original.submissionId,
        library: queueLibraryDraft(original),
      }
      const saved = structuredClone(original)
      if (problem === 'different-bytes')
        saved.declarationBytes = new TextEncoder().encode(` ${raw}`)
      if (problem === 'duplicate-key') {
        const duplicate = raw.replace(
          '{',
          '{"measurement_id":"00000000-0000-4000-8000-000000000002",',
        )
        saved.declarationBytes = new TextEncoder().encode(duplicate)
        pending.library.declarationBytes = saved.declarationBytes
      }
      if (problem === 'malformed-utf8') {
        saved.declarationBytes = new Uint8Array([255])
        pending.library.declarationBytes = saved.declarationBytes
      }
      if (problem === 'object-mismatch') {
        saved.instrument.measurement_id = '00000000-0000-4000-8000-000000000003'
        pending.library = queueLibraryDraft(saved)
      }
      if (problem === 'wrong-byte-type') {
        saved.declarationBytes = new Int8Array(
          saved.declarationBytes,
        ) as unknown as typeof saved.declarationBytes
        pending.library.declarationBytes = saved.declarationBytes
      }
      if (problem === 'oversize-raw') {
        const bytes = new Uint8Array(MAX_LIBRARY_INTAKE_BYTES + 1).fill(32)
        // UTF-8 decoding normally strips the BOM: the original-byte cap must apply before it.
        bytes.set([0xef, 0xbb, 0xbf])
        bytes.set(new TextEncoder().encode(raw), 3)
        saved.declarationBytes = bytes
        pending.library.declarationBytes = bytes
      }
      await q.saveLibraryDraft(saved, revision)
      const outcome = await q.enqueueGuideObservation(
        pending,
        context(revision),
      )
      expect(outcome.status).toBe(problem === 'exact' ? 'committed' : 'held')
      const remaining = await q.savedLibraryDraft()
      if (problem === 'exact') expect(remaining).toBeUndefined()
      else {
        expect(remaining).toBeDefined()
        const { declarationBytes: actualBytes, ...actualContext } = remaining!
        const { declarationBytes: expectedBytes, ...expectedContext } = saved
        expect(actualContext).toEqual(expectedContext)
        expect(Object.prototype.toString.call(actualBytes)).toBe(
          Object.prototype.toString.call(expectedBytes),
        )
        expect(actualBytes?.byteLength).toBe(expectedBytes.byteLength)
        // Check every byte without a generic matcher's millions of per-property assertions.
        expect(
          actualBytes?.every((byte, index) => byte === expectedBytes[index]),
        ).toBe(true)
      }
      expect((await q.queued()).length).toBe(problem === 'exact' ? 1 : 0)
      expect(await q.queueRevision()).toBe(
        revision + (problem === 'exact' ? 1 : 0),
      )
    },
  )

  it.each([
    'ownerless',
    'legacy',
    'missing-A',
    'duplicate-shot',
    'empty-photo',
    'not-jpeg',
  ])('refuses invalid guide snapshot %s', async (problem) => {
    const q = await queue(),
      revision = await q.queueRevision(),
      pending = guideRecord()
    if (problem === 'ownerless') pending.ownerUid = ''
    if (problem === 'legacy') delete pending.collectionMode
    if (problem === 'missing-A')
      pending.photos = pending.photos.filter((photo) => photo.shotType !== 'A')
    if (problem === 'duplicate-shot')
      pending.photos.push(structuredClone(pending.photos[0]!))
    if (problem === 'empty-photo') pending.photos[0]!.bytes = new Uint8Array()
    if (problem === 'not-jpeg')
      pending.photos[0]!.bytes = new Uint8Array([1, 2, 3, 4])
    expect(
      (
        await q.enqueueGuideObservation(pending, {
          ...context(revision),
          ownerUid: pending.ownerUid!,
        })
      ).status,
    ).toBe('held')
    expect(await q.queued()).toEqual([])
    expect(await q.queueRevision()).toBe(revision)
  })

  it.each(['ownerless', 'legacy'])(
    'never reconciles a %s record as an admitted guide',
    async (problem) => {
      const q = await queue(),
        revision = await q.queueRevision(),
        pending = guideRecord()
      if (problem === 'ownerless') pending.ownerUid = ''
      if (problem === 'legacy') delete pending.collectionMode
      await q.enqueue(pending)
      expect(
        (
          await q.enqueueGuideObservation(pending, {
            ...context(revision),
            ownerUid: pending.ownerUid!,
          })
        ).status,
      ).toBe('held')
      expect(await q.queued()).toEqual(structuredClone([pending]))
    },
  )

  it('owns a defensive snapshot of original values and revision across its first await', async () => {
    const q = await queue(),
      revision = await q.queueRevision(),
      pending = guideRecord(),
      original = structuredClone(pending)
    const attemptContext = context(revision)
    const outcome = q.enqueueGuideObservation(pending, attemptContext)
    pending.photos[0]!.bytes[0] = 0
    pending.grantId = 'changed-after-call'
    attemptContext.revision += 1
    expect((await outcome).status).toBe('committed')
    expect(await q.queued()).toEqual([original])
    expect(await q.queueRevision()).toBe(revision + 1)
  })

  it.each(['owner', 'submission', 'acceptance', 'photo', 'context'])(
    'never overwrites an immutable %s conflict',
    async (field) => {
      const q = await queue(),
        revision = await q.queueRevision(),
        pending = guideRecord()
      const existing = structuredClone(pending)
      if (field === 'owner') existing.ownerUid = 'other-owner'
      if (field === 'submission') existing.grantId = 'other-grant'
      if (field === 'acceptance') existing.termsVersion = 'other-terms'
      if (field === 'photo') existing.photos[0]!.bytes[0] = 0
      if (field === 'context') existing.landCover = 'grassland'
      await q.enqueue(existing)
      expect(
        await q.enqueueGuideObservation(pending, context(revision)),
      ).toEqual({ status: 'held', revision })
      expect(await q.queued()).toEqual([existing])
      expect(await q.queueRevision()).toBe(revision)
    },
  )

  it('holds a stale original session for new insertion, even at the same revision', async () => {
    const q = await queue(),
      revision = await q.queueRevision()
    expect(
      (
        await q.enqueueGuideObservation(guideRecord(), {
          ...context(revision),
          originalContextCurrent: () => false,
        })
      ).status,
    ).toBe('held')
    await q.clearDraftPhotos()
    expect(
      (await q.enqueueGuideObservation(guideRecord(), context(revision)))
        .status,
    ).toBe('held')
    expect(await q.queued()).toEqual([])
  })

  it('rechecks admission after awaits and refuses cancelled photo/library writer intents', async () => {
    const q = await queue(),
      revision = await q.queueRevision()
    let allowed = true
    const pending = q.enqueueGuideObservation(guideRecord(), {
      ...context(revision),
      allowed: () => allowed,
    })
    allowed = false
    expect((await pending).status).toBe('held')
    let writerCurrent = true
    const writes = [
      q.saveDraftPhoto('A', photo, revision, () => writerCurrent),
      q.saveLibraryDraft(draft(revision), revision, () => writerCurrent),
    ]
    writerCurrent = false
    expect(await Promise.all(writes)).toEqual([false, false])
    expect(await q.queued()).toEqual([])
    expect(await q.draftPhotos()).toEqual({})
    expect(await q.savedLibraryDraft()).toBeUndefined()
  })

  it('rights clear serializes in both orders without restoring the observation or drafts', async () => {
    const q = await queue(),
      revision = await q.queueRevision()
    const [clearedFirst, held] = await Promise.all([
      q.clearQueue(),
      q.enqueueGuideObservation(guideRecord(), context(revision)),
    ])
    expect(clearedFirst).toBe(0)
    expect(held.status).toBe('held')
    const fresh = await q.queueRevision()
    const [committed, clearedAfter] = await Promise.all([
      q.enqueueGuideObservation(guideRecord(), context(fresh)),
      q.clearQueue(),
    ])
    expect(committed.status).toBe('committed')
    expect(clearedAfter).toBe(1)
    expect(await q.queued()).toEqual([])
    expect(await q.draftPhotos()).toEqual({})
  })

  it('rolls back insertion, exact context consume and revision advance if the transaction aborts', async () => {
    const q = await queue(),
      revision = await q.queueRevision(),
      saved = draft(revision)
    await q.saveLibraryDraft(saved, revision)
    const pending = {
      ...guideRecord(),
      submissionId: saved.submissionId,
      library: queueLibraryDraft(saved),
    }
    const put = IDBObjectStore.prototype.put
    vi.spyOn(IDBObjectStore.prototype, 'put').mockImplementation(function (
      this: IDBObjectStore,
      ...args
    ) {
      const request = put.apply(this, args)
      if (this.name === 'queueState') this.transaction.abort()
      return request
    })
    await expect(
      q.enqueueGuideObservation(pending, context(revision)),
    ).rejects.toThrow()
    vi.restoreAllMocks()
    expect(await q.queued()).toEqual([])
    expect(await q.savedLibraryDraft()).toEqual(saved)
    expect(await q.queueRevision()).toBe(revision)
  })
})
