import { type DBSchema, type IDBPDatabase, openDB } from 'idb'
import type { QueueRecord } from './types'

interface CaptureQueueDatabase extends DBSchema {
  submissions: {
    key: string
    value: QueueRecord
  }
}

let databasePromise: Promise<IDBPDatabase<CaptureQueueDatabase>> | undefined
// Bumped whenever the queue is cleared, so a drain already in progress never writes back a
// record the person just discarded.
let generation = 0

function database() {
  databasePromise ??= openDB<CaptureQueueDatabase>('gsip-capture-v1', 1, {
    upgrade(db) {
      db.createObjectStore('submissions', { keyPath: 'submissionId' })
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

/** Discards every observation still queued on this device (WP-6d withdrawal and deletion). */
export async function clearQueue(): Promise<number> {
  generation += 1
  const records = await queued()
  await (await database()).clear('submissions')
  return records.length
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
 * to sync (I9). Each keeps its own grant identifier, which the server has not recorded yet.
 */
export async function reconfirmTerms(
  acceptedAt: string,
  termsVersion: string,
): Promise<number> {
  let count = 0
  for (const record of await queued()) {
    if (!record.termsExpiredAt) continue
    await enqueue({
      ...record,
      acceptedAt,
      nextRetryAt: undefined,
      termsExpiredAt: undefined,
      termsVersion,
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
