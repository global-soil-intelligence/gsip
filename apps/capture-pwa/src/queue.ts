import { type DBSchema, type IDBPDatabase, openDB } from 'idb'
import type { LibraryDraft } from './library'
import type { CapturedPhoto } from './platform/types'
import type { QueueRecord, ShotType } from './types'

/** A photo the phone app has taken for an observation not yet queued (WP-APP-1). */
export type DraftPhoto = { photo: CapturedPhoto; shotType: ShotType }

interface CaptureQueueDatabase extends DBSchema {
  submissions: {
    key: string
    value: QueueRecord
  }
  libraryDraft: { key: 'current'; value: LibraryDraft }
  libraryNamespace: {
    key: string
    value: { nodeId: string; ownerUid?: string }
  }
  queueState: { key: 'generation'; value: number }
  draftPhotos: {
    key: ShotType
    value: DraftPhoto
  }
}

let databasePromise: Promise<IDBPDatabase<CaptureQueueDatabase>> | undefined
// Bumped whenever the queue is cleared, so a drain already in progress never writes back a
// record the person just discarded.
let generation = 0

function database() {
  databasePromise ??= openDB<CaptureQueueDatabase>('gsip-capture-v1', 3, {
    upgrade(db, oldVersion) {
      if (oldVersion < 1)
        db.createObjectStore('submissions', { keyPath: 'submissionId' })
      // Version 2 (WP-APP-1): photos taken before the observation is queued.
      if (oldVersion < 2)
        db.createObjectStore('draftPhotos', { keyPath: 'shotType' })
      if (oldVersion < 3) {
        db.createObjectStore('libraryDraft')
        db.createObjectStore('libraryNamespace')
        db.createObjectStore('queueState')
      }
    },
    blocking() {
      // A newer version of the app wants to upgrade the database: step aside.
      void databasePromise?.then((db) => db.close())
      databasePromise = undefined
    },
  })
  return databasePromise
}

export async function enqueue(record: QueueRecord): Promise<void> {
  await (await database()).put('submissions', record)
}

export async function queued(): Promise<QueueRecord[]> {
  return (await database()).getAll('submissions')
}

export async function removeQueued(submissionId: string): Promise<void> {
  await (await database()).delete('submissions', submissionId)
}

/**
 * Discards every observation still queued on this device, and any photos taken for one not yet
 * queued (WP-6d withdrawal and deletion).
 */
export async function clearQueue(): Promise<number> {
  generation += 1
  const db = await database()
  const tx = db.transaction(
    [
      'submissions',
      'draftPhotos',
      'libraryDraft',
      'libraryNamespace',
      'queueState',
    ],
    'readwrite',
  )
  const records = await tx.objectStore('submissions').getAll()
  const revision = (await tx.objectStore('queueState').get('generation')) ?? 0
  await tx.objectStore('queueState').put(revision + 1, 'generation')
  await Promise.all([
    tx.objectStore('submissions').clear(),
    tx.objectStore('draftPhotos').clear(),
    tx.objectStore('libraryDraft').clear(),
    tx.objectStore('libraryNamespace').clear(),
  ])
  await tx.done
  return records.length
}

/**
 * The phone app keeps each photo as soon as it is taken, so a photo survives Android ending the
 * app while the camera is open. Drafts are cleared once the observation is queued, when the
 * person discards them, and with the queue.
 */
export async function saveDraftPhoto(
  shotType: ShotType,
  photo: CapturedPhoto,
  revision?: number,
): Promise<void> {
  const tx = (await database()).transaction(
    ['draftPhotos', 'queueState'],
    'readwrite',
  )
  const current = (await tx.objectStore('queueState').get('generation')) ?? 0
  if (revision === undefined || revision === current)
    await tx.objectStore('draftPhotos').put({ photo, shotType })
  await tx.done
}

export async function draftPhotos(): Promise<
  Partial<Record<ShotType, CapturedPhoto>>
> {
  const drafts = await (await database()).getAll('draftPhotos')
  return Object.fromEntries(
    drafts.map(({ photo, shotType }) => [shotType, photo]),
  )
}

export async function clearDraftPhotos(): Promise<void> {
  generation += 1
  const tx = (await database()).transaction(
    ['draftPhotos', 'libraryDraft', 'queueState'],
    'readwrite',
  )
  const revision = (await tx.objectStore('queueState').get('generation')) ?? 0
  await tx.objectStore('queueState').put(revision + 1, 'generation')
  await Promise.all([
    tx.objectStore('draftPhotos').clear(),
    tx.objectStore('libraryDraft').clear(),
  ])
  await tx.done
}

/** Discards observations held because their account is no longer signed in here. */
export async function discardHeld(): Promise<number> {
  return discardMatching((record) => Boolean(record.heldAt))
}

export async function discardLibraryConflicts(): Promise<number> {
  return discardMatching((record) => Boolean(record.libraryConflictAt))
}

async function discardMatching(
  matches: (record: QueueRecord) => boolean,
): Promise<number> {
  generation += 1
  const tx = (await database()).transaction(
    ['submissions', 'queueState'],
    'readwrite',
  )
  const revision = (await tx.objectStore('queueState').get('generation')) ?? 0
  await tx.objectStore('queueState').put(revision + 1, 'generation')
  const records = (await tx.objectStore('submissions').getAll()).filter(matches)
  for (const record of records)
    await tx.objectStore('submissions').delete(record.submissionId)
  await tx.done
  return records.length
}

/** Library samples can only return to their original account; older captures keep their behavior. */
export async function releaseHeld(currentUid?: string): Promise<void> {
  await updateQueued((record) => {
    if (!record.heldAt) return record
    if (record.library)
      return currentUid && record.ownerUid === currentUid
        ? { ...record, heldAt: undefined }
        : record
    return { ...record, heldAt: undefined, ownerUid: undefined }
  })
}

/**
 * The person accepted the current contribution terms again for observations that waited too long
 * to sync (I9). Each keeps its own grant identifier, which the server has not recorded yet, and its
 * original acceptance, which is still offered first (see submitQueued).
 */
export async function reconfirmTerms(
  reconfirmedAt: string,
  reconfirmedTermsVersion: string,
): Promise<number> {
  let count = 0
  await updateQueued((record) => {
    if (!record.termsExpiredAt) return record
    count += 1
    return {
      ...record,
      nextRetryAt: undefined,
      reconfirmedAt,
      reconfirmedTermsVersion,
      termsExpiredAt: undefined,
    }
  })
  return count
}

export async function retryDeadLettered(): Promise<void> {
  await updateQueued((record) =>
    record.deadLetteredAt
      ? {
          ...record,
          deadLetteredAt: undefined,
          nextRetryAt: undefined,
          syncAttempts: 0,
        }
      : record,
  )
}

export const indexedDbQueue = {
  generation: () => generation,
  revision: queueRevision,
  putIfCurrent,
  isCurrent: async (revision: number) => (await queueRevision()) === revision,
  list: queued,
  put: enqueue,
  remove: removeQueued,
}

/** Persistent across tabs and restarts, unlike the local fast generation counter. */
export async function queueRevision(): Promise<number> {
  return (await (await database()).get('queueState', 'generation')) ?? 0
}

export async function putIfCurrent(
  record: QueueRecord,
  revision: number,
  existingOnly = true,
): Promise<boolean> {
  const tx = (await database()).transaction(
    ['submissions', 'queueState'],
    'readwrite',
  )
  const current = (await tx.objectStore('queueState').get('generation')) ?? 0
  const exists =
    !existingOnly ||
    Boolean(await tx.objectStore('submissions').get(record.submissionId))
  if (current === revision && exists)
    await tx.objectStore('submissions').put(record)
  await tx.done
  return current === revision && exists
}

export async function savedLibraryDraft(): Promise<LibraryDraft | undefined> {
  return (await database()).get('libraryDraft', 'current')
}

export async function saveLibraryDraft(
  draft: LibraryDraft,
  revision: number,
): Promise<boolean> {
  const tx = (await database()).transaction(
    ['libraryDraft', 'queueState'],
    'readwrite',
  )
  const current = (await tx.objectStore('queueState').get('generation')) ?? 0
  if (current === revision)
    await tx.objectStore('libraryDraft').put(draft, 'current')
  await tx.done
  return current === revision
}

export async function libraryNodeForOwner(
  ownerUid?: string,
  revision?: number,
): Promise<string> {
  const tx = (await database()).transaction(
    ['libraryNamespace', 'queueState'],
    'readwrite',
  )
  const current = (await tx.objectStore('queueState').get('generation')) ?? 0
  if (revision !== undefined && current !== revision) {
    await tx.done
    throw new Error('Private draft was discarded.')
  }
  const store = tx.objectStore('libraryNamespace')
  let saved = await store.get('current')
  if (!saved || saved.ownerUid !== ownerUid) {
    saved = { nodeId: crypto.randomUUID(), ownerUid }
    await store.put(saved, 'current')
  }
  await tx.done
  return saved.nodeId
}

/** Persist the first sender binding before any capture mutation; do not transfer a known node. */
export async function bindLibraryOwner(
  nodeId: string,
  ownerUid: string,
  revision?: number,
): Promise<string> {
  const tx = (await database()).transaction(
    ['libraryNamespace', 'queueState'],
    'readwrite',
  )
  const current = (await tx.objectStore('queueState').get('generation')) ?? 0
  if (revision !== undefined && current !== revision) {
    await tx.done
    throw new Error('Private draft was discarded.')
  }
  const store = tx.objectStore('libraryNamespace')
  const known = await store.get(nodeId)
  const binding = known?.ownerUid ?? ownerUid
  if (!known?.ownerUid) await store.put({ nodeId, ownerUid: binding }, nodeId)
  const saved = await store.get('current')
  if (saved?.nodeId === nodeId && !saved.ownerUid)
    await store.put({ nodeId, ownerUid: binding }, 'current')
  await tx.done
  return binding
}

export async function rememberLibraryOwner(
  nodeId: string,
  ownerUid: string,
  revision?: number,
): Promise<void> {
  if ((await bindLibraryOwner(nodeId, ownerUid, revision)) !== ownerUid)
    throw new Error('Private namespace belongs to its original account.')
}

export async function clearLibraryDraft(): Promise<void> {
  const tx = (await database()).transaction(
    ['libraryDraft', 'queueState'],
    'readwrite',
  )
  const revision = (await tx.objectStore('queueState').get('generation')) ?? 0
  await tx.objectStore('queueState').put(revision + 1, 'generation')
  await tx.objectStore('libraryDraft').clear()
  await tx.done
}

export async function libraryNamespaceOwner(
  nodeId: string,
): Promise<string | undefined> {
  return (await (await database()).get('libraryNamespace', nodeId))?.ownerUid
}

async function updateQueued(
  update: (record: QueueRecord) => QueueRecord,
): Promise<void> {
  const tx = (await database()).transaction('submissions', 'readwrite')
  for (const record of await tx.store.getAll()) {
    const next = update(record)
    if (next !== record) await tx.store.put(next)
  }
  await tx.done
}
