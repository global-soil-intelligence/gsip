import { type DBSchema, type IDBPDatabase, openDB } from 'idb'
import type { CapturedPhoto } from './platform/types'
import type { QueueRecord, ShotType } from './types'

/** A photo the phone app has taken for an observation not yet queued (WP-APP-1). */
export type DraftPhoto = { photo: CapturedPhoto; shotType: ShotType }

interface CaptureQueueDatabase extends DBSchema {
  submissions: {
    key: string
    value: QueueRecord
  }
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
  databasePromise ??= openDB<CaptureQueueDatabase>('gsip-capture-v1', 2, {
    upgrade(db, oldVersion) {
      if (oldVersion < 1)
        db.createObjectStore('submissions', { keyPath: 'submissionId' })
      // Version 2 (WP-APP-1): photos taken before the observation is queued.
      if (oldVersion < 2)
        db.createObjectStore('draftPhotos', { keyPath: 'shotType' })
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
  const records = await queued()
  await (await database()).clear('submissions')
  await clearDraftPhotos()
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
): Promise<void> {
  await (await database()).put('draftPhotos', { photo, shotType })
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
  await (await database()).clear('draftPhotos')
}

/** Discards observations held because their account is no longer signed in here. */
export async function discardHeld(): Promise<number> {
  const held = (await queued()).filter((record) => record.heldAt)
  for (const record of held) await removeQueued(record.submissionId)
  return held.length
}

/** The person chose to send held observations from the account signed in on this device now. */
export async function releaseHeld(): Promise<void> {
  for (const record of await queued()) {
    if (!record.heldAt) continue
    await enqueue({ ...record, heldAt: undefined, ownerUid: undefined })
  }
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
  for (const record of await queued()) {
    if (!record.termsExpiredAt) continue
    await enqueue({
      ...record,
      nextRetryAt: undefined,
      reconfirmedAt,
      reconfirmedTermsVersion,
      termsExpiredAt: undefined,
    })
    count += 1
  }
  return count
}

export async function retryDeadLettered(): Promise<void> {
  for (const record of await queued()) {
    if (!record.deadLetteredAt) continue
    await enqueue({
      ...record,
      deadLetteredAt: undefined,
      nextRetryAt: undefined,
      syncAttempts: 0,
    })
  }
}

export const indexedDbQueue = {
  generation: () => generation,
  list: queued,
  put: enqueue,
  remove: removeQueued,
}
