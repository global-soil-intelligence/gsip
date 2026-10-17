import { type DBSchema, type IDBPDatabase, openDB } from 'idb'
import {
  MAX_LIBRARY_INTAKE_BYTES,
  parseInstrumentDeclaration,
} from '@gsip/schema'
import { type LibraryDraft, queueLibraryDraft } from './library'
import { isJpeg, MAX_PHOTO_BYTES } from './platform/camera'
import type { CapturedPhoto } from './platform/types'
import type { QueueRecord, ShotType } from './types'
import { acceptanceExpired, TERMS_VERSION } from './terms'
import {
  initialReminderState,
  type SyncReminderState,
  type ReminderContext,
} from './syncReminder'

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
  syncReminder: { key: 'current'; value: SyncReminderState }
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
  databasePromise ??= openDB<CaptureQueueDatabase>('gsip-capture-v1', 4, {
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
      // APP-2B: additive private reminder intent; queue/draft/library stores are unchanged.
      if (oldVersion < 4) db.createObjectStore('syncReminder')
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
export async function clearQueue(
  allowed: () => boolean = () => true,
): Promise<number> {
  if (!allowed()) return 0
  generation += 1
  const db = await database()
  const tx = db.transaction(
    [
      'submissions',
      'draftPhotos',
      'libraryDraft',
      'libraryNamespace',
      'queueState',
      'syncReminder',
    ],
    'readwrite',
  )
  const records = await tx.objectStore('submissions').getAll()
  const revision = (await tx.objectStore('queueState').get('generation')) ?? 0
  const reminder = checkedReminderState(
    await tx.objectStore('syncReminder').get('current'),
  )
  if (!allowed()) {
    await tx.done
    return 0
  }
  // Queue every write synchronously after the last identity check, within one transaction.
  await Promise.all([
    tx.objectStore('queueState').put(revision + 1, 'generation'),
    tx.objectStore('syncReminder').put(
      {
        ...reminder,
        enabled: false,
        epoch: reminder.epoch + 1,
        cleanupPending: true,
        cycleOpen: false,
        consumed: false,
      },
      'current',
    ),
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
  allowed: () => boolean = () => true,
): Promise<boolean> {
  const snapshot = structuredClone(photo)
  const tx = (await database()).transaction(
    ['draftPhotos', 'queueState'],
    'readwrite',
  )
  void tx.done.catch(() => undefined)
  const current = (await tx.objectStore('queueState').get('generation')) ?? 0
  const permitted =
    (revision === undefined || revision === current) && allowed()
  if (permitted) {
    await tx.objectStore('draftPhotos').put({ photo: snapshot, shotType })
    if (!allowed()) {
      tx.abort()
      await tx.done.catch(() => undefined)
      return false
    }
  }
  await tx.done
  return permitted && allowed()
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
export async function releaseHeld(
  currentUid?: string,
  pilot = false,
): Promise<void> {
  await updateQueued((record) => {
    if (!record.heldAt) return record
    if (pilot || record.collectionMode === 'invited_private')
      return record.collectionMode === 'invited_private' &&
        currentUid &&
        record.ownerUid === currentUid
        ? { ...record, heldAt: undefined }
        : record
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
  allowed: () => boolean = () => true,
): Promise<boolean> {
  const tx = (await database()).transaction(
    ['submissions', 'queueState'],
    'readwrite',
  )
  const current = (await tx.objectStore('queueState').get('generation')) ?? 0
  const exists =
    !existingOnly ||
    Boolean(await tx.objectStore('submissions').get(record.submissionId))
  const permitted = current === revision && exists && allowed()
  if (permitted) await tx.objectStore('submissions').put(record)
  await tx.done
  return permitted
}

export async function savedLibraryDraft(): Promise<LibraryDraft | undefined> {
  return (await database()).get('libraryDraft', 'current')
}

export async function saveLibraryDraft(
  draft: LibraryDraft,
  revision: number,
  allowed: () => boolean = () => true,
): Promise<boolean> {
  const snapshot = structuredClone(draft)
  const tx = (await database()).transaction(
    ['libraryDraft', 'queueState'],
    'readwrite',
  )
  void tx.done.catch(() => undefined)
  const current = (await tx.objectStore('queueState').get('generation')) ?? 0
  const permitted =
    validRevision(snapshot.deviceRevision) &&
    snapshot.deviceRevision === revision &&
    current === revision &&
    allowed()
  if (permitted) {
    await tx.objectStore('libraryDraft').put(snapshot, 'current')
    if (!allowed()) {
      tx.abort()
      await tx.done.catch(() => undefined)
      return false
    }
  }
  await tx.done
  return permitted && allowed()
}

function validRevision(revision: unknown): revision is number {
  return (
    typeof revision === 'number' &&
    Number.isSafeInteger(revision) &&
    revision >= 0 &&
    revision < Number.MAX_SAFE_INTEGER
  )
}

/** IndexedDB may return a typed array from another realm; reject every other view kind. */
function isUint8Array(value: unknown): value is Uint8Array {
  return (
    ArrayBuffer.isView(value) &&
    Object.prototype.toString.call(value) === '[object Uint8Array]'
  )
}

export type GuideEnqueueContext = {
  ownerUid: string
  revision: number
  /** Current same-owner authentication, rights and invited admission, including after awaits. */
  allowed: () => boolean
  /** Original session, observation and shot intents. Required only for a NEW insertion. */
  originalContextCurrent: () => boolean
}

export type GuideEnqueueResult = {
  status: 'committed' | 'reconciled' | 'held'
  revision: number
}

/** Exact private values, independent of JSON key order and typed-array serialization. */
function sameValue(left: unknown, right: unknown): boolean {
  if (Object.is(left, right)) return true
  if (left instanceof Uint8Array || right instanceof Uint8Array)
    return (
      left instanceof Uint8Array &&
      right instanceof Uint8Array &&
      left.length === right.length &&
      left.every((byte, index) => byte === right[index])
    )
  if (!left || !right || typeof left !== 'object' || typeof right !== 'object')
    return false
  if (Array.isArray(left) !== Array.isArray(right)) return false
  const leftFields = Object.keys(left)
  const rightFields = Object.keys(right)
  return (
    leftFields.length === rightFields.length &&
    leftFields.every(
      (key) =>
        Object.hasOwn(right, key) &&
        sameValue(
          (left as Record<string, unknown>)[key],
          (right as Record<string, unknown>)[key],
        ),
    )
  )
}

/** Sync and personal reconfirmation may advance after the original snapshot was committed. */
function immutableQueueValues(record: QueueRecord): unknown {
  const value = { ...record }
  for (const field of [
    'deadLetteredAt',
    'heldAt',
    'nextRetryAt',
    'libraryConflictAt',
    'reconfirmedAt',
    'reconfirmedTermsVersion',
    'syncAttempts',
    'termsExpiredAt',
  ] as const)
    delete value[field]
  if (value.library) {
    value.library = { ...value.library }
    delete value.library.photosFinalized
  }
  return value
}

function matchesGuideLibrary(
  saved: LibraryDraft | undefined,
  snapshot: QueueRecord,
  context: GuideEnqueueContext,
): boolean {
  if (!snapshot.library) return saved === undefined
  if (
    !saved ||
    saved.ownerUid !== context.ownerUid ||
    !validRevision(saved.deviceRevision) ||
    saved.deviceRevision !== context.revision ||
    saved.submissionId !== snapshot.submissionId ||
    (saved.declarationBytes !== null &&
      (!isUint8Array(saved.declarationBytes) ||
        saved.declarationBytes.byteLength > MAX_LIBRARY_INTAKE_BYTES))
  )
    return false
  try {
    const library = queueLibraryDraft(saved)
    // Raw declaration bytes are independently parsed; an object cannot substitute for them.
    if (library.declarationBytes === null) {
      if (saved.instrument !== null) return false
    } else if (
      !sameValue(
        parseInstrumentDeclaration(
          new TextDecoder('utf-8', { fatal: true }).decode(
            library.declarationBytes,
          ),
        ),
        saved.instrument,
      )
    )
      return false
    return sameValue(library, snapshot.library)
  } catch {
    return false
  }
}

/**
 * Commit one RAM-only invited guide observation using the existing four stores. This is a local
 * durable result, never a hosted receipt. A frozen identity can reconcile uncertain completion
 * after its original session/revision expired, without consuming another draft or replacing sync
 * progress. New work must still own its original session and all empty photo slots.
 */
export async function enqueueGuideObservation(
  record: QueueRecord,
  originalContext: GuideEnqueueContext,
): Promise<GuideEnqueueResult> {
  const snapshot = structuredClone(record)
  const context = { ...originalContext }
  const held = (revision: number): GuideEnqueueResult => ({
    status: 'held',
    revision,
  })
  if (
    !context.ownerUid ||
    snapshot.ownerUid !== context.ownerUid ||
    snapshot.collectionMode !== 'invited_private' ||
    !context.allowed()
  )
    return held(context.revision)
  const db = await database()
  if (!context.allowed()) return held(context.revision)
  const tx = db.transaction(
    ['submissions', 'queueState', 'draftPhotos', 'libraryDraft'],
    'readwrite',
  )
  // Attach immediately: a failing request and transaction completion can reject together.
  void tx.done.catch(() => undefined)
  let revision = context.revision
  const finishHeld = async () => {
    await tx.done
    return held(revision)
  }
  try {
    const submissions = tx.objectStore('submissions')
    const existing = await submissions.get(snapshot.submissionId)
    if (!context.allowed()) return await finishHeld()
    revision = (await tx.objectStore('queueState').get('generation')) ?? 0
    if (!context.allowed()) return await finishHeld()
    if (existing) {
      const matches =
        existing.collectionMode === 'invited_private' &&
        existing.ownerUid === context.ownerUid &&
        snapshot.ownerUid === context.ownerUid &&
        sameValue(
          immutableQueueValues(existing),
          immutableQueueValues(snapshot),
        )
      await tx.done
      return matches && context.allowed()
        ? { status: 'reconciled', revision }
        : held(revision)
    }
    if (
      !validRevision(revision) ||
      !validRevision(context.revision) ||
      revision !== context.revision ||
      !context.originalContextCurrent() ||
      !['A', 'B'].every((shot) =>
        snapshot.photos.some((photo) => photo.shotType === shot),
      ) ||
      snapshot.photos.length > 3 ||
      new Set(snapshot.photos.map((photo) => photo.shotType)).size !==
        snapshot.photos.length ||
      snapshot.photos.some(
        (photo) =>
          photo.mimeType !== 'image/jpeg' ||
          photo.bytes.byteLength > MAX_PHOTO_BYTES ||
          !isJpeg(photo.bytes) ||
          !['A', 'B', 'C'].includes(photo.shotType),
      )
    )
      return await finishHeld()
    const photos = await tx.objectStore('draftPhotos').getAll()
    if (!context.allowed()) return await finishHeld()
    const libraryStore = tx.objectStore('libraryDraft')
    const library = await libraryStore.get('current')
    if (
      !context.allowed() ||
      !context.originalContextCurrent() ||
      photos.length !== 0 ||
      !matchesGuideLibrary(library, snapshot, context)
    )
      return await finishHeld()
    const successor = revision + 1
    // No awaits between the final predicates and submission of every atomic mutation.
    const writes: Promise<unknown>[] = []
    const schedule = (request: Promise<unknown>) => {
      void request.catch(() => undefined)
      writes.push(request)
    }
    schedule(submissions.add(snapshot))
    if (snapshot.library) schedule(libraryStore.delete('current'))
    schedule(tx.objectStore('queueState').put(successor, 'generation'))
    await Promise.all(writes)
    if (!context.allowed() || !context.originalContextCurrent()) {
      tx.abort()
      await tx.done.catch(() => undefined)
      return held(revision)
    }
    await tx.done
    generation += 1
    return context.allowed()
      ? { status: 'committed', revision: successor }
      : held(successor)
  } catch (error) {
    try {
      tx.abort()
    } catch {
      // A storage abort may already have ended this transaction.
    }
    await tx.done.catch(() => undefined)
    throw error
  }
}

export async function libraryNodeForOwner(
  ownerUid?: string,
  revision?: number,
  allowed: () => boolean = () => true,
): Promise<string> {
  const refused = () => new Error('Private draft was discarded.')
  if (!allowed()) throw refused()
  const db = await database()
  if (!allowed()) throw refused()
  const tx = db.transaction(['libraryNamespace', 'queueState'], 'readwrite')
  void tx.done.catch(() => undefined)
  try {
    const current = (await tx.objectStore('queueState').get('generation')) ?? 0
    if (!allowed() || (revision !== undefined && current !== revision))
      throw refused()
    const store = tx.objectStore('libraryNamespace')
    let saved = await store.get('current')
    if (!allowed()) throw refused()
    if (!saved || saved.ownerUid !== ownerUid) {
      saved = { nodeId: crypto.randomUUID(), ownerUid }
      await store.put(saved, 'current')
      if (!allowed()) throw refused()
    }
    await tx.done
    if (!allowed()) throw refused()
    return saved.nodeId
  } catch (error) {
    try {
      tx.abort()
    } catch {
      // An already completed transaction cannot be aborted.
    }
    await tx.done.catch(() => undefined)
    throw error
  }
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

/** No credentials/session object or queue bytes are accepted into reminder intent. */
function checkedReminderState(saved: unknown): SyncReminderState {
  if (!saved || typeof saved !== 'object') return initialReminderState()
  const value = saved as SyncReminderState
  if (
    !(
      value.owner === null ||
      (typeof value.owner === 'string' &&
        value.owner.length > 0 &&
        value.owner.length <= 128)
    ) ||
    !Number.isSafeInteger(value.epoch) ||
    value.epoch < 0 ||
    value.epoch >= Number.MAX_SAFE_INTEGER ||
    !Number.isSafeInteger(value.revision) ||
    value.revision < 0 ||
    [
      'enabled',
      'cycleOpen',
      'consumed',
      'allowed',
      'blocked',
      'cleanupPending',
    ].some((key) => typeof value[key as keyof SyncReminderState] !== 'boolean')
  )
    return initialReminderState()
  return {
    owner: value.owner,
    enabled: value.enabled,
    epoch: value.epoch,
    revision: value.revision,
    cycleOpen: value.cycleOpen,
    consumed: value.consumed,
    allowed: value.allowed,
    blocked: value.blocked,
    cleanupPending: value.cleanupPending,
  }
}
export const indexedDbReminderStore = {
  async read(): Promise<SyncReminderState> {
    return checkedReminderState(
      await (await database()).get('syncReminder', 'current'),
    )
  },
  async update(
    change: (state: SyncReminderState) => SyncReminderState,
  ): Promise<SyncReminderState> {
    const tx = (await database()).transaction('syncReminder', 'readwrite')
    const before = checkedReminderState(await tx.store.get('current'))
    const changed = change(before)
    // A lifetime fence can turn an already admitted read into a no-op. Do not submit a stale write.
    const next = changed === before ? before : checkedReminderState(changed)
    if (changed !== before) await tx.store.put(next, 'current')
    await tx.done
    return next
  },
}

/** Atomic local queue/revision snapshot. Raw records never cross the notification seam. */
export async function queueReminderContext(
  owner: string | null,
  captureLive: boolean,
  gate: ReminderContext['gate'],
  libraryLive: boolean,
): Promise<ReminderContext> {
  const tx = (await database()).transaction(['submissions', 'queueState'])
  const [records, revision] = await Promise.all([
    tx.objectStore('submissions').getAll(),
    tx.objectStore('queueState').get('generation'),
  ])
  await tx.done
  return {
    owner,
    captureLive,
    gate,
    revision: revision ?? 0,
    hasWork: records.length > 0,
    blocked: records.some(
      (record) =>
        !owner ||
        record.ownerUid !== owner ||
        Boolean(
          record.heldAt ||
          record.deadLetteredAt ||
          record.termsExpiredAt ||
          record.libraryConflictAt,
        ) ||
        Boolean(record.library && !libraryLive) ||
        (!(
          record.reconfirmedTermsVersion === TERMS_VERSION &&
          record.reconfirmedAt
        ) &&
          record.termsVersion !== TERMS_VERSION) ||
        acceptanceExpired(
          record.reconfirmedTermsVersion === TERMS_VERSION &&
            record.reconfirmedAt
            ? record.reconfirmedAt
            : (record.acceptedAt ?? record.queuedAt),
          Date.now(),
        ),
    ),
  }
}
