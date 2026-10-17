import 'fake-indexeddb/auto'
import { IDBFactory, IDBObjectStore } from 'fake-indexeddb'
import { openDB } from 'idb'
import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import {
  newLibraryDraft,
  queueLibraryDraft,
  readInstrumentDeclaration,
} from '../src/library'
import type { CapturedPhoto } from '../src/platform/types'
const uuid = '00000000-0000-4000-8000-000000000001'
const photo: CapturedPhoto = {
  bytes: new Uint8Array([255, 216, 255, 1]),
  mimeType: 'image/jpeg',
  method: 'file',
  takenAt: 1,
}
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
it('persists explicit context, stable IDs, attachment bytes and photos across module restart', async () => {
  const a = await queue(),
    draft = {
      ...newLibraryDraft(uuid, 'owner-a'),
      deviceRevision: await a.queueRevision(),
      depthTop: '1.5',
      depthBottom: '4',
      declarationBytes: new Uint8Array([123, 125]),
    }
  await a.saveLibraryDraft(draft, await a.queueRevision())
  await a.saveDraftPhoto('B', photo)
  vi.resetModules()
  const b = await queue()
  const saved = (await b.savedLibraryDraft())!
  expect({ ...saved, declarationBytes: null }).toEqual({
    ...draft,
    declarationBytes: null,
  })
  expect(Array.from(saved.declarationBytes!)).toEqual([123, 125])
  expect(Array.from((await b.draftPhotos()).B!.bytes)).toEqual(
    Array.from(photo.bytes),
  )
  expect(
    queueLibraryDraft((await b.savedLibraryDraft())!).request.context,
  ).toEqual({ depth_top_cm: 1.5, depth_bottom_cm: 4, condition: 'unknown' })
})
it.each(['', '  ', 'NaN', 'Infinity', '-1', '201'])(
  'never invents a depth for missing/invalid top %s',
  (top) => {
    expect(() =>
      queueLibraryDraft({
        ...newLibraryDraft(uuid),
        depthTop: top,
        depthBottom: '5',
      }),
    ).toThrow()
  },
)
it('refuses an oversized declaration before reading', async () => {
  const text = vi.fn()
  await expect(
    readInstrumentDeclaration({ size: 2_000_001, text } as unknown as File),
  ).rejects.toThrow()
  expect(text).not.toHaveBeenCalled()
})
it('refuses authority-bearing records without private echo', async () => {
  await expect(
    readInstrumentDeclaration({
      size: 60,
      text: async () =>
        '{"schema_version":"gsip-library-v1","consent_verified":true}',
    } as File),
  ).rejects.toThrow('private sample')
})
it('allocates a new node on account switch and remembers the prior binding', async () => {
  const q = await queue(),
    first = await q.libraryNodeForOwner('owner-a')
  await q.rememberLibraryOwner(first, 'owner-a')
  expect(await q.libraryNodeForOwner('owner-a')).toBe(first)
  expect(await q.libraryNodeForOwner('owner-b')).not.toBe(first)
  expect(await q.libraryNamespaceOwner(first)).toBe('owner-a')
  await expect(q.rememberLibraryOwner(first, 'owner-b')).rejects.toThrow()
})
it('clears metadata, attachments, namespaces and photos on withdrawal and fences other tabs', async () => {
  const a = await queue(),
    revision = await a.queueRevision(),
    draft = {
      ...newLibraryDraft(uuid),
      deviceRevision: revision,
      declarationBytes: new Uint8Array([7]),
    }
  await a.saveLibraryDraft(draft, revision)
  await a.saveDraftPhoto('B', photo)
  const node = await a.libraryNodeForOwner('owner-a')
  await a.rememberLibraryOwner(node, 'owner-a')
  vi.resetModules()
  const b = await queue()
  await b.clearQueue()
  expect(await a.saveLibraryDraft(draft, revision)).toBe(false)
  expect(await a.savedLibraryDraft()).toBeUndefined()
  expect(await a.draftPhotos()).toEqual({})
  expect(await a.libraryNamespaceOwner(node)).toBeUndefined()
})
it('upgrades version-two data without inventing a library sample', async () => {
  await new Promise<void>((resolve, reject) => {
    const r = indexedDB.open('gsip-capture-v1', 2)
    r.onupgradeneeded = () => {
      r.result.createObjectStore('submissions', { keyPath: 'submissionId' })
      r.result.createObjectStore('draftPhotos', { keyPath: 'shotType' })
    }
    r.onsuccess = () => {
      const db = r.result,
        t = db.transaction('submissions', 'readwrite')
      t.objectStore('submissions').put({ submissionId: uuid, photos: [] })
      t.oncomplete = () => {
        db.close()
        resolve()
      }
    }
    r.onerror = () => reject(r.error)
  })
  const q = await queue()
  expect((await q.queued())[0]).not.toHaveProperty('library')
  expect(await q.savedLibraryDraft()).toBeUndefined()
})

it('serializes first-owner reservation when Web Locks are absent', async () => {
  const q = await queue(),
    revision = await q.queueRevision()
  const owners = await Promise.all([
    q.bindLibraryOwner(uuid, 'owner-a', revision),
    q.bindLibraryOwner(uuid, 'owner-b', revision),
  ])
  expect(owners[0]).toBe(owners[1])
  expect(await q.libraryNamespaceOwner(uuid)).toBe(owners[0])
})
it('does not restore namespace ownership after a clear invalidates its revision', async () => {
  const q = await queue(),
    revision = await q.queueRevision()
  await q.clearQueue()
  await expect(q.bindLibraryOwner(uuid, 'owner-a', revision)).rejects.toThrow()
  expect(await q.libraryNamespaceOwner(uuid)).toBeUndefined()
})

it.each([undefined, -1, 0.5, NaN, Infinity, Number.MAX_SAFE_INTEGER])(
  'refuses missing or invalid original draft revision %s without rebinding',
  async (deviceRevision) => {
    const q = await queue(),
      revision = await q.queueRevision()
    expect(
      await q.saveLibraryDraft(
        { ...newLibraryDraft(uuid), deviceRevision },
        revision,
      ),
    ).toBe(false)
    expect(await q.savedLibraryDraft()).toBeUndefined()
  },
)

it('requires original explicit draft revision to match the argument and current fence', async () => {
  const q = await queue(),
    revision = await q.queueRevision()
  expect(
    await q.saveLibraryDraft(
      { ...newLibraryDraft(uuid), deviceRevision: revision + 1 },
      revision,
    ),
  ).toBe(false)
  expect(await q.savedLibraryDraft()).toBeUndefined()
})

it('refuses namespace mutation when its original library-start intent is already cancelled', async () => {
  const q = await queue(),
    revision = await q.queueRevision()
  await expect(
    q.libraryNodeForOwner('owner-a', revision, () => false),
  ).rejects.toThrow('Private draft was discarded.')
  const db = await openDB('gsip-capture-v1')
  expect(await db.get('libraryNamespace', 'current')).toBeUndefined()
  db.close()
})

it.each([
  [false, 'before-read'],
  [true, 'before-read'],
  [false, 'after-put'],
  [true, 'after-put'],
] as const)(
  'preserves namespace state (existing=%s) if library start cancels %s',
  async (existing, cancellation) => {
    const q = await queue(),
      revision = await q.queueRevision()
    const prior = existing
      ? await q.libraryNodeForOwner('owner-a', revision)
      : undefined
    let allowed = true
    if (cancellation === 'after-put') {
      const put = IDBObjectStore.prototype.put
      vi.spyOn(IDBObjectStore.prototype, 'put').mockImplementation(function (
        this: IDBObjectStore,
        ...args
      ) {
        const request = put.apply(this, args)
        if (this.name === 'libraryNamespace') allowed = false
        return request
      })
    }
    const pending = q.libraryNodeForOwner('owner-b', revision, () => allowed)
    if (cancellation === 'before-read') allowed = false
    await expect(pending).rejects.toThrow('Private draft was discarded.')
    const db = await openDB('gsip-capture-v1')
    expect(await db.get('libraryNamespace', 'current')).toEqual(
      prior ? { nodeId: prior, ownerUid: 'owner-a' } : undefined,
    )
    db.close()
  },
)
